"""외부 저장소·모델 어댑터의 계약과 게시 안전성을 검증함."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from threading import Thread

import pytest

from app.domain.models import PreparedChunk
from app.infrastructure.artifact_store import JsonArtifactStore
from app.infrastructure.embedder import HuggingFaceEmbedder
from app.infrastructure.index_repository import GenerationIndexRepository
from app.infrastructure.file_lock import CrossPlatformFileLock, LockUnavailableError
from app.infrastructure.locked_runner import LockedPipelineRunner
from app.infrastructure.lexical_index import LexicalIndexBuilder, _card_dictionary_words


def _hash(value) -> str:
    """메타데이터 비교에 사용할 안정적인 JSON 지문을 생성함."""
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class _Array(list):
    """모델 출력의 tolist 계약을 최소 형태로 재현함."""

    def tolist(self):
        """내부 항목을 일반 list로 복사하여 반환함."""
        return list(self)


class _EmbeddingModel:
    """입력 길이·벡터 차원·정규화 요청을 관찰하는 가짜 임베딩 모델임."""

    max_seq_length = 255

    def get_embedding_dimension(self):
        """시험에서 기대하는 2차원 벡터 크기를 반환함."""
        return 2

    def encode(self, texts, **kwargs):
        """정규화 옵션을 검사하고 길이가 같은 비정규 벡터를 반환함."""
        assert kwargs["normalize_embeddings"] is True
        return _Array([[2.0, 0.0] for _ in texts])


def test_embedder_pins_revision_sets_length_and_validates_shape():
    """임베더가 고정 revision·오프라인 모드·800토큰 상한을 적용하고 벡터를 정규화함을 보증함."""
    calls = []

    def factory(name, **kwargs):
        """모델 생성 인자를 기록하고 가짜 모델을 반환함."""
        calls.append((name, kwargs))
        return _EmbeddingModel()

    embedder = HuggingFaceEmbedder(
        "nlpai-lab/KURE-v2",
        revision="revision-sha",
        max_seq_length=800,
        model_factory=factory,
    )
    assert embedder.embed(["질문", "문서"]) == [[1.0, 0.0], [1.0, 0.0]]
    assert embedder.dimension == 2
    assert embedder._model.max_seq_length == 800
    assert calls[0][1]["revision"] == "revision-sha"
    assert calls[0][1]["local_files_only"] is True
    assert embedder.contract["max_seq_length"] == 800
    assert embedder.contract["normalization"] == "float-l2-after-encode-v1"


def test_embedder_omits_device_when_auto_and_records_selected_device():
    """auto이면 장치 인자를 넘기지 않고, 계약에는 라이브러리가 실제로 고른 장치를 기록함을 보증함."""
    calls = []

    class _AutoModel(_EmbeddingModel):
        """자동 선택 결과로 cuda:0을 가진 가짜 모델임."""

        device = "cuda:0"

    def factory(name, **kwargs):
        """모델 생성 인자를 기록하고 가짜 모델을 반환함."""
        calls.append(kwargs)
        return _AutoModel()

    auto = HuggingFaceEmbedder("m", revision="r", max_seq_length=8, device="auto", model_factory=factory)
    auto._load()
    assert "device" not in calls[0]
    assert auto.contract["device"] == "cuda:0"

    fixed = HuggingFaceEmbedder("m", revision="r", max_seq_length=8, device="cpu", model_factory=factory)
    fixed._load()
    assert calls[1]["device"] == "cpu"


def test_embedder_rejects_unexpected_model_dimension():
    """설정한 차원과 실제 모델 차원이 다르면 임베딩 결과를 거부함을 보증함."""
    embedder = HuggingFaceEmbedder(
        "nlpai-lab/KURE-v2",
        revision="revision-sha",
        max_seq_length=800,
        expected_dimension=768,
        model_factory=lambda *_args, **_kwargs: _EmbeddingModel(),
    )
    with pytest.raises(ValueError, match="expected=768, actual=2"):
        embedder.embed(["문서"])


def test_artifact_store_blocks_traversal_and_round_trips_json(tmp_path: Path):
    """JSON 아티팩트는 왕복 저장되며 기준 경로를 벗어나는 참조는 거부됨을 보증함."""
    store = JsonArtifactStore(tmp_path / "artifacts")
    reference = store.save("run-1", "prepared-chunks", {"ok": True})
    assert store.load(reference) == {"ok": True}
    with pytest.raises(ValueError):
        store.save("../escape", "chunks", {})
    with pytest.raises(ValueError):
        store.load("../outside.json")


def test_file_lock_rejects_another_thread_and_releases_automatically(tmp_path: Path):
    """다른 스레드의 동시 잠금을 막고 문맥 종료 뒤 잠금을 다시 얻을 수 있음을 보증함."""
    path = tmp_path / ".writer.lock"
    errors = []
    with CrossPlatformFileLock(path):
        def contend():
            """별도 스레드에서 같은 경로 잠금 획득을 시도함."""
            try:
                with CrossPlatformFileLock(path):
                    pass
            except Exception as error:  # 스레드 안의 예외를 주 스레드에서 검증하기 위해 보관함.
                errors.append(error)

        thread = Thread(target=contend)
        thread.start()
        thread.join()
    assert len(errors) == 1 and isinstance(errors[0], LockUnavailableError)
    assert path.is_file()
    with CrossPlatformFileLock(path):
        pass


def test_locked_runner_holds_same_reentrant_lock_for_inner_runner(tmp_path: Path):
    """바깥 실행기와 안쪽 실행기가 같은 재진입 잠금을 공유해 교착되지 않음을 보증함."""
    path = tmp_path / ".writer.lock"

    class Runner:
        """같은 잠금을 다시 얻는 내부 실행기를 재현함."""

        def run(self, initial_state, thread_id):
            """잠금 안에서 입력 상태에 실행 표시를 더해 반환함."""
            del thread_id
            with CrossPlatformFileLock(path):
                return {**initial_state, "locked": True}

    runner = LockedPipelineRunner(Runner(), path)
    assert runner.run({"value": 1}, "thread-1") == {"value": 1, "locked": True}


def test_card_dictionary_reads_all_card_pairs_from_merged_chunk():
    """여러 카드가 합쳐진 청크에서도 모든 카드명이 사용자 사전에 포함됨을 보증함."""
    records = [
        {
            "metadata": {
                "doc_key": "D2",
                "card_id": "D2-C001",
                "card_name": "대표 카드",
                "card_id_all": '["D2-C001", "D2-C003"]',
                "card_name_all": '["생활 포인트 카드", "무할 카드"]',
            }
        }
    ]
    assert _card_dictionary_words(records) == (
        ("무할 카드", "NNP", 0.0),
        ("생활 포인트 카드", "NNP", 0.0),
    )


class _Tokenizer:
    """본문 전체를 토큰 하나로 취급하는 BM25 시험용 형태소 분석기임."""

    signature = "kiwi:test"
    user_dictionary_sha256 = ""

    def __init__(self, *_args, **_kwargs):
        """실제 형태소 분석기 설정을 사용하지 않는 빈 초기화를 수행함."""
        pass

    def tokenize_many(self, texts):
        """각 본문을 토큰 하나가 든 목록으로 변환함."""
        return [[text] for text in texts]


class _BM25:
    """색인 문서 수와 저장 호출만 재현하는 시험용 BM25 구현임."""

    def __init__(self, **_kwargs):
        """색인될 행을 기록할 빈 목록을 준비함."""
        self.rows = []

    def index(self, rows, **_kwargs):
        """입력 행과 검증에 쓰일 문서 수를 기록함."""
        self.rows = rows
        self.scores = {"num_docs": len(rows)}

    def save(self, path, **_kwargs):
        """게시 파일의 존재를 검증할 수 있도록 가짜 색인 JSON을 저장함."""
        path.mkdir(parents=True, exist_ok=True)
        (path / "fake.json").write_text(json.dumps(self.rows, ensure_ascii=False), encoding="utf-8")


def _chunk() -> PreparedChunk:
    """벡터·BM25 동시 게시 시험에 사용할 혜택 청크를 생성함."""
    metadata = {
        "source": "D2.pdf",
        "doc_key": "D2",
        "doc_type": "benefit_guide",
        "access_level": "public",
        "card_id": "D2-C001",
        "card_name": "생활 포인트 카드",
    }
    text = "생활 포인트 적립 안내"
    return PreparedChunk(
        chunk_id="D2-C001-0000",
        text=text,
        metadata=metadata,
        token_count=8,
        text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        metadata_hash=_hash(metadata),
    )


def _build_and_publish(
    repository: GenerationIndexRepository,
    generation: str,
    chunks: list[PreparedChunk],
    manifest: dict,
):
    """텍스트 색인을 먼저 완성한 뒤 같은 stage를 검증해 게시함."""

    stage = repository.build_text_index(generation, chunks, manifest)
    return repository.publish(generation, chunks, manifest, stage)


def test_repository_publishes_vector_and_bm25_with_one_active_pointer(tmp_path: Path):
    """벡터와 BM25가 검증된 뒤 하나의 활성 세대 포인터로 함께 전환됨을 보증함."""
    pytest.importorskip("chromadb")
    lexical = LexicalIndexBuilder(
        tokenizer_factory=_Tokenizer,
        bm25_factory=lambda **kwargs: _BM25(**kwargs),
    )
    repository = GenerationIndexRepository(tmp_path / "data", lexical_builder=lexical)
    chunk = _chunk()
    repository.begin("gen-test", "sentence-transformers:test:prompt-policy-v2")
    repository.upsert("gen-test", [chunk], [[1.0, 0.0]])

    stage = repository.build_text_index(
        "gen-test",
        [chunk],
        {"embedding_signature": "sentence-transformers:test:prompt-policy-v2"},
    )
    assert not repository.active_pointer_path.exists()
    publication = repository.publish(
        "gen-test",
        [chunk],
        {"embedding_signature": "sentence-transformers:test:prompt-policy-v2"},
        stage,
    )

    active = json.loads((tmp_path / "data" / "active_generation.json").read_text(encoding="utf-8"))
    assert active["generation"] == "gen-test"
    assert Path(publication.chroma_path).is_dir()
    assert Path(publication.search_index_root, "active_index.json").is_file()
    snapshot = repository.load_active()
    assert snapshot is not None and snapshot.chunks == (chunk,)
    assert repository.get_vectors([chunk.chunk_id])[chunk.chunk_id] == [1.0, 0.0]


def test_repository_does_not_switch_active_generation_on_validation_failure(tmp_path: Path):
    """벡터가 없는 불완전 세대는 활성 포인터를 만들지 않음을 보증함."""
    pytest.importorskip("chromadb")
    lexical = LexicalIndexBuilder(
        tokenizer_factory=_Tokenizer,
        bm25_factory=lambda **kwargs: _BM25(**kwargs),
    )
    repository = GenerationIndexRepository(tmp_path / "data", lexical_builder=lexical)
    repository.begin("gen-incomplete", "sentence-transformers:test:prompt-policy-v2")
    with pytest.raises(ValueError):
        repository.build_text_index("gen-incomplete", [_chunk()], {})
    assert not repository.active_pointer_path.exists()


def test_repository_does_not_publish_when_bm25_count_is_inconsistent(tmp_path: Path):
    """BM25 문서 수가 청크 수와 다르면 새 세대를 게시하지 않음을 보증함."""
    pytest.importorskip("chromadb")

    class InvalidCountBM25(_BM25):
        """실제 입력과 다른 문서 수를 보고하는 실패 재현용 BM25 구현임."""

        def index(self, rows, **kwargs):
            """행을 색인한 뒤 검증용 문서 수를 잘못된 값으로 바꿈."""
            super().index(rows, **kwargs)
            self.scores = {"num_docs": 0}

    repository = GenerationIndexRepository(
        tmp_path / "data",
        lexical_builder=LexicalIndexBuilder(
            tokenizer_factory=_Tokenizer,
            bm25_factory=lambda **kwargs: InvalidCountBM25(**kwargs),
        ),
    )
    chunk = _chunk()
    repository.begin("gen-invalid-bm25", "sentence-transformers:test:prompt-policy-v2")
    repository.upsert("gen-invalid-bm25", [chunk], [[1.0, 0.0]])

    with pytest.raises(ValueError, match="BM25 색인 문서 수"):
        repository.build_text_index("gen-invalid-bm25", [chunk], {})
    assert not repository.active_pointer_path.exists()


def test_repository_begin_recovers_directory_without_state_file(tmp_path: Path):
    """디렉터리 생성 직후 중단된 세대도 같은 입력으로 다시 준비할 수 있음을 보증함."""
    pytest.importorskip("chromadb")
    data_root = tmp_path / "data"
    generation_dir = data_root / "generations" / "gen-interrupted"
    generation_dir.mkdir(parents=True)
    repository = GenerationIndexRepository(data_root)

    repository.begin("gen-interrupted", "sentence-transformers:test:prompt-policy-v2")

    state = json.loads((generation_dir / "generation_state.json").read_text(encoding="utf-8"))
    assert state["generation"] == "gen-interrupted"
    assert state["status"] == "building"


def test_text_index_build_failure_is_private_and_retry_replaces_partial_files(tmp_path: Path):
    """BM25 저장 중 실패한 파일은 노출되지 않으며 같은 세대 재시도가 새 묶음으로 완성됨을 보증함."""
    pytest.importorskip("chromadb")

    class FailOnceBM25(_BM25):
        """첫 저장만 부분 파일을 남긴 뒤 실패하는 BM25 구현임."""

        should_fail = True

        def save(self, path, **kwargs):
            """첫 호출에서 부분 파일을 만든 뒤 예외를 발생시키고 다음 호출은 정상 저장함."""
            path.mkdir(parents=True, exist_ok=True)
            if type(self).should_fail:
                type(self).should_fail = False
                (path / "partial.json").write_text("partial", encoding="utf-8")
                raise OSError("simulated save failure")
            super().save(path, **kwargs)

    data_root = tmp_path / "data"
    stable = GenerationIndexRepository(
        data_root,
        lexical_builder=LexicalIndexBuilder(
            tokenizer_factory=_Tokenizer,
            bm25_factory=lambda **kwargs: _BM25(**kwargs),
        ),
    )
    chunk = _chunk()
    stable.begin("gen-stable", "sentence-transformers:test:prompt-policy-v2")
    stable.upsert("gen-stable", [chunk], [[1.0, 0.0]])
    _build_and_publish(stable, "gen-stable", [chunk], {})

    retrying = GenerationIndexRepository(
        data_root,
        lexical_builder=LexicalIndexBuilder(
            tokenizer_factory=_Tokenizer,
            bm25_factory=lambda **kwargs: FailOnceBM25(**kwargs),
        ),
    )
    retrying.begin("gen-retry", "sentence-transformers:test:prompt-policy-v2")
    retrying.upsert("gen-retry", [chunk], [[1.0, 0.0]])
    with pytest.raises(OSError, match="simulated save failure"):
        retrying.build_text_index("gen-retry", [chunk], {})

    active = json.loads(retrying.active_pointer_path.read_text(encoding="utf-8"))
    assert active["generation"] == "gen-stable"
    assert not (data_root / "generations" / "gen-retry" / "search_indexes").exists()

    stage = retrying.build_text_index("gen-retry", [chunk], {})
    retrying.publish("gen-retry", [chunk], {}, stage)
    active = json.loads(retrying.active_pointer_path.read_text(encoding="utf-8"))
    assert active["generation"] == "gen-retry"


def test_publish_rejects_text_index_changed_after_checkpoint(tmp_path: Path):
    """체크포인트 이후 BM25 파일이 바뀌면 전역 활성 포인터를 만들지 않음을 보증함."""
    pytest.importorskip("chromadb")
    repository = GenerationIndexRepository(
        tmp_path / "data",
        lexical_builder=LexicalIndexBuilder(
            tokenizer_factory=_Tokenizer,
            bm25_factory=lambda **kwargs: _BM25(**kwargs),
        ),
    )
    chunk = _chunk()
    repository.begin("gen-tampered", "sentence-transformers:test:prompt-policy-v2")
    repository.upsert("gen-tampered", [chunk], [[1.0, 0.0]])
    stage = repository.build_text_index("gen-tampered", [chunk], {})
    bm25_file = (
        tmp_path
        / "data"
        / "generations"
        / "gen-tampered"
        / "search_indexes"
        / "generations"
        / "gen-tampered"
        / "bm25"
        / "fake.json"
    )
    bm25_file.write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="stage"):
        repository.publish("gen-tampered", [chunk], {}, stage)
    assert not repository.active_pointer_path.exists()


def test_text_index_retry_reuses_completed_stage(tmp_path: Path):
    """완성된 같은 입력을 재시도하면 created_at과 stage 해시가 바뀌지 않음을 보증함."""
    pytest.importorskip("chromadb")
    repository = GenerationIndexRepository(
        tmp_path / "data",
        lexical_builder=LexicalIndexBuilder(
            tokenizer_factory=_Tokenizer,
            bm25_factory=lambda **kwargs: _BM25(**kwargs),
        ),
    )
    chunk = _chunk()
    repository.begin("gen-resume", "sentence-transformers:test:prompt-policy-v2")
    repository.upsert("gen-resume", [chunk], [[1.0, 0.0]])

    first = repository.build_text_index("gen-resume", [chunk], {})
    second = repository.build_text_index("gen-resume", [chunk], {})

    assert second == first


def test_lexical_builder_recovers_when_promotion_stops_after_previous_move(
    tmp_path: Path,
    monkeypatch,
):
    """기존 루트를 옮긴 직후 승격이 중단되어도 다음 실행이 최종 루트를 다시 완성함을 보증함."""
    import app.infrastructure.lexical_index as lexical_module

    builder = LexicalIndexBuilder(
        tokenizer_factory=_Tokenizer,
        bm25_factory=lambda **kwargs: _BM25(**kwargs),
    )
    search_root = tmp_path / "search_indexes"
    chunk = _chunk()
    builder.build(
        search_root=search_root,
        generation="gen-promotion",
        chunks=[chunk],
        collection="card_docs",
        embedding_signature="sentence-transformers:test:prompt-policy-v2",
        manifest={"revision": 1},
    )

    real_replace = lexical_module.os.replace

    def interrupt_stage_promotion(source, destination):
        """임시 검색 루트를 최종 경로로 옮기는 한 지점에서만 중단을 재현함."""
        source_path = Path(source)
        destination_path = Path(destination)
        if source_path.name.startswith(".search_indexes-stage-") and destination_path == search_root:
            raise OSError("simulated promotion interruption")
        return real_replace(source, destination)

    monkeypatch.setattr(lexical_module.os, "replace", interrupt_stage_promotion)
    with pytest.raises(OSError, match="simulated promotion interruption"):
        builder.build(
            search_root=search_root,
            generation="gen-promotion",
            chunks=[chunk],
            collection="card_docs",
            embedding_signature="sentence-transformers:test:prompt-policy-v2",
            manifest={"revision": 2},
        )
    assert not search_root.exists()

    monkeypatch.setattr(lexical_module.os, "replace", real_replace)
    builder.build(
        search_root=search_root,
        generation="gen-promotion",
        chunks=[chunk],
        collection="card_docs",
        embedding_signature="sentence-transformers:test:prompt-policy-v2",
        manifest={"revision": 2},
    )
    _pointer, manifest, stage = builder.verify(
        search_root=search_root,
        generation="gen-promotion",
    )
    assert manifest["revision"] == 2
    assert stage["chunk_count"] == 1


def test_repository_rejects_stale_publisher(tmp_path: Path):
    """더 최신 세대가 활성화된 뒤 도착한 이전 게시자가 포인터를 되돌리지 못함을 보증함."""
    pytest.importorskip("chromadb")

    def repository():
        """같은 데이터 경로를 바라보는 독립 저장소 인스턴스를 생성함."""
        return GenerationIndexRepository(
            tmp_path / "data",
            lexical_builder=LexicalIndexBuilder(
                tokenizer_factory=_Tokenizer,
                bm25_factory=lambda **kwargs: _BM25(**kwargs),
            ),
        )

    older = repository()
    newer = repository()
    chunk = _chunk()
    older.begin("gen-older", "sentence-transformers:test:prompt-policy-v2")
    newer.begin("gen-newer", "sentence-transformers:test:prompt-policy-v2")
    older.upsert("gen-older", [chunk], [[1.0, 0.0]])
    newer.upsert("gen-newer", [chunk], [[1.0, 0.0]])
    older_stage = older.build_text_index("gen-older", [chunk], {})
    newer_stage = newer.build_text_index("gen-newer", [chunk], {})
    newer.publish("gen-newer", [chunk], {}, newer_stage)

    with pytest.raises(RuntimeError, match="활성 세대가 바뀌었습니다"):
        older.publish("gen-older", [chunk], {}, older_stage)

    active = json.loads((tmp_path / "data" / "active_generation.json").read_text(encoding="utf-8"))
    assert active["generation"] == "gen-newer"


def test_published_format_is_readable_by_existing_retriever(tmp_path: Path):
    """게시 형식을 기존 Retriever가 BM25·벡터 양쪽에서 그대로 읽을 수 있음을 보증함."""
    pytest.importorskip("chromadb")
    pytest.importorskip("bm25s")
    pytest.importorskip("kiwipiepy")
    signature = "sentence-transformers:nlpai-lab/KURE-v2:prompt-policy-v2"
    repository = GenerationIndexRepository(tmp_path / "data")
    chunk = _chunk()
    vector = [1.0, *([0.0] * 767)]
    repository.begin("gen-compatible", signature)
    repository.upsert("gen-compatible", [chunk], [vector])
    publication = _build_and_publish(repository, "gen-compatible", [chunk], {})

    lab_root = Path(__file__).resolve().parents[3]
    retriever_root = lab_root / "retriever" / "vector-retriever"
    retriever_python = retriever_root / ".venv" / "Scripts" / "python.exe"
    if not retriever_python.is_file():
        pytest.skip("기존 Retriever 가상환경이 없습니다.")
    script = r"""
import sys
from pathlib import Path
from app.domain.search_filter import MetadataFilter
from app.infrastructure.bm25_index import BM25Index
from app.infrastructure.chroma_store import ChromaVectorStore
from app.infrastructure.corpus_store import VersionedCorpusStore
from app.infrastructure.korean_tokenizer import KoreanTokenizer

search_root, chroma_path, signature = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
corpus = VersionedCorpusStore(search_root)
snapshot = corpus.load_active()
assert snapshot is not None and len(snapshot.records) == 1
bm25 = BM25Index(corpus, KoreanTokenizer())
bm25.warm()
scores = bm25.keyword_search("생활 포인트", allowed_access_levels=frozenset({"public"}), k=5)
assert "D2-C001-0000" in scores
vectors = ChromaVectorStore(chroma_path, "card_docs", signature)
assert vectors.describe()["dimension"] == 768
hits = vectors.search(
    [1.0] + [0.0] * 767,
    1,
    MetadataFilter.from_parts(equalities={"card_id": "D2-C001"}),
)
assert hits and hits[0].chunk_id == "D2-C001-0000"
print("retriever-compatible")
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(retriever_root)
    result = subprocess.run(
        [
            str(retriever_python),
            "-c",
            script,
            publication.search_index_root,
            publication.chroma_path,
            signature,
        ],
        cwd=retriever_root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "retriever-compatible" in result.stdout
