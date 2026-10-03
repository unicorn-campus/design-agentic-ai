"""색인 세대 대조·교체와 벡터·BM25 검색이 색인 계약대로 동작하는지 확인하는 시험임.

단위 시험은 가짜 색인 파일과 가짜 검색기로 대조 실패·권한 걸러내기를 재현함.
`integration` 표시가 붙은 시험은 W-1이 실제로 게시한 세대와 로컬 모델을 그대로 씀.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

import pytest

from app.application.models import IndexUnavailableError
from app.domain.models import Chunk, SourceInfo
from app.infrastructure.index_store import (
    POINTER_NAME,
    GenerationIndex,
    LocalIndexProvider,
)
from app.infrastructure.korean_tokenizer import KoreanTokenizer, lexical_policy_fingerprint

GENERATION = "gen-test-0001"
SIGNATURE = "sentence-transformers:nlpai-lab/KURE-v2:prompt-policy-v2"
RULES_SHA = "a" * 64
OVERRIDES_SHA = "b" * 64
FAKE_CONTRACT: dict[str, Any] = {
    "model": "nlpai-lab/KURE-v2",
    "revision": "rev-test",
    "dimension": 4,
    "normalize_embeddings": True,
}

# 실제 색인(읽기 전용): tests → vector-retriever → retriever → hybrid-ai-lab 순으로 올라가 indexer를 찾음.
REAL_DATA_ROOT = Path(__file__).resolve().parents[3] / "indexer" / "vector-bm25" / "data"
REAL_GENERATION = "gen-ch2-20261003-001-17151790"
REAL_CONTRACT: dict[str, Any] = {
    "model": "nlpai-lab/KURE-v2",
    "revision": "3431f86d399d666083890dbb882aced6708873bc",
    "dimension": 768,
    "normalize_embeddings": True,
}
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


# ================================================================ 가짜 색인 만들기


def _sha(payload: bytes) -> str:
    """바이트의 SHA-256 16진 문자열을 반환함."""

    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    """dict를 UTF-8 JSON 파일로 저장함."""

    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def patch_json(path: Path, **changes: Any) -> None:
    """이미 저장된 JSON 파일의 키 몇 개만 바꿔 다시 저장함(대조 실패 재현용)."""

    value = json.loads(path.read_text(encoding="utf-8-sig"))
    value.update(changes)
    _write_json(path, value)


def build_fake_root(tmp_path: Path) -> dict[str, Path]:
    """서명·해시가 모두 맞는 작은 가짜 색인 세대를 만들고 주요 파일 경로를 돌려줌."""

    root = tmp_path / "data"
    generation_dir = root / "generations" / GENERATION
    (generation_dir / "chroma").mkdir(parents=True)
    search_root = generation_dir / "search_indexes"
    inner = search_root / "generations" / GENERATION
    (inner / "bm25").mkdir(parents=True)

    rows = [
        {
            "chunk_id": "D1_aaaa_0000",
            "text": "할부 수수료는 약관에 따릅니다.",
            "metadata": {"access_level": "public", "source": "D1.pdf", "doc_key": "D1", "page": 3},
        },
        {
            "chunk_id": "D3_bbbb_0000",
            "text": "고객: 상담 이력입니다.",
            "metadata": {"access_level": "restricted", "source": "D3_S01.txt", "doc_key": "D3"},
        },
    ]
    corpus = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    card = "한빛 테스트\tNNP\t0.0\n".encode("utf-8")
    alias = "테스트\t한빛테스트\n".encode("utf-8")
    (inner / "corpus.jsonl").write_bytes(corpus)
    (inner / "card_names.dict").write_bytes(card)
    (inner / "card_aliases.tsv").write_bytes(alias)

    relative = f"generations/{GENERATION}"
    manifest = {
        "generation": GENERATION,
        "chunk_count": len(rows),
        "corpus_sha256": _sha(corpus),
        "embedding_signature": SIGNATURE,
        "embedding_contract": dict(FAKE_CONTRACT),
        "embedding_dimension": FAKE_CONTRACT["dimension"],
        "lexical_policy_fingerprint": lexical_policy_fingerprint(
            alias_rules_sha256=RULES_SHA, alias_overrides_sha256=OVERRIDES_SHA
        ),
        "tokenizer_signature": "kiwi:stub",
        "card_dictionary": {"path": f"{relative}/card_names.dict", "sha256": _sha(card), "count": 1},
        "card_aliases": {
            "path": f"{relative}/card_aliases.tsv",
            "sha256": _sha(alias),
            "count": 1,
            "rules_sha256": RULES_SHA,
            "overrides_sha256": OVERRIDES_SHA,
        },
        "vector": {"collection": "card_docs", "embedding_signature": SIGNATURE},
    }
    _write_json(inner / "manifest.json", manifest)
    _write_json(
        search_root / "active_index.json",
        {
            "format_version": 1,
            "generation": GENERATION,
            "manifest": f"{relative}/manifest.json",
            "corpus": f"{relative}/corpus.jsonl",
            "bm25": f"{relative}/bm25",
            "card_dictionary": f"{relative}/card_names.dict",
            "card_dictionary_sha256": _sha(card),
            "card_aliases": f"{relative}/card_aliases.tsv",
            "card_aliases_sha256": _sha(alias),
            "card_aliases_count": 1,
            "corpus_sha256": _sha(corpus),
            "chunk_count": len(rows),
        },
    )
    _write_json(
        generation_dir / "generation_state.json",
        {
            "generation": GENERATION,
            "embedding_signature": SIGNATURE,
            "collection": "card_docs",
            "status": "ready",
        },
    )
    _write_json(
        root / POINTER_NAME,
        {
            "format_version": 1,
            "generation": GENERATION,
            "chroma_path": f"generations/{GENERATION}/chroma",
            "search_index_root": f"generations/{GENERATION}/search_indexes",
            "collection": "card_docs",
            "chunk_count": len(rows),
            "embedding_dimension": FAKE_CONTRACT["dimension"],
            "embedding_signature": SIGNATURE,
        },
    )
    return {
        "root": root,
        "pointer": root / POINTER_NAME,
        "state": generation_dir / "generation_state.json",
        "search_pointer": search_root / "active_index.json",
        "manifest": inner / "manifest.json",
        "corpus": inner / "corpus.jsonl",
    }


def _provider(root: Path, **kwargs: Any) -> LocalIndexProvider:
    """가짜 색인용 관리자를 만듦(임베더는 쓰이지 않으므로 더미를 넣음)."""

    return LocalIndexProvider(
        root,
        embedder=_StubEmbedder(),
        expected_embedding_contract=dict(FAKE_CONTRACT),
        **kwargs,
    )


# ================================================================ 가짜 검색기


class _StubEmbedder:
    """질의를 고정 벡터로 바꾸는 더미 임베더임."""

    def embed(self, text: str) -> list[float]:
        """길이 4의 고정 벡터를 돌려줌."""

        return [1.0, 0.0, 0.0, 0.0]


class _StubTokenizer:
    """정해진 문장만 정해진 낱말로 바꾸는 더미 분석기임."""

    signature = "kiwi:stub"
    card_tokens = frozenset({"한빛테스트"})

    def __init__(self, mapping: dict[str, list[str]]) -> None:
        """문장 → 낱말 목록 대응표를 받음."""

        self._mapping = dict(mapping)

    def tokenize(self, text: str) -> list[str]:
        """대응표에 있으면 그 낱말 목록, 없으면 빈 목록을 돌려줌."""

        return list(self._mapping.get(str(text), []))

    def tokenize_many(self, texts: Any) -> list[list[str]]:
        """여러 문장을 각각 tokenize함."""

        return [self.tokenize(text) for text in texts]

    def keyword_terms(self, text: str) -> list[str]:
        """tokenize 결과에서 중복만 뺀 값을 핵심어로 봄."""

        return list(dict.fromkeys(self.tokenize(text)))


class _StubBm25:
    """토큰ID별 문서 점수표를 들고 있는 더미 BM25임."""

    def __init__(self, vocabulary: dict[str, int], rows: dict[int, list[float]], num_docs: int) -> None:
        """어휘표와 토큰ID → 문서별 점수표를 받음."""

        self.vocab_dict = dict(vocabulary)
        # 실제 bm25s는 어휘 끝의 빈 토큰에 점수 열을 만들지 않아 indptr 길이가 어휘 수와 같음.
        self.scores = {"indptr": [0] * len(vocabulary), "num_docs": num_docs}
        self._rows = dict(rows)
        self._num_docs = num_docs

    def get_scores_from_ids(self, token_ids: list[int]) -> list[float]:
        """토큰ID별 점수를 문서마다 더해 돌려줌."""

        total = [0.0] * self._num_docs
        for token_id in token_ids:
            for row, value in enumerate(self._rows.get(int(token_id), [])):
                total[row] += float(value)
        return total


class _StubCollection:
    """거리순으로 정렬된 결과를 돌려주는 더미 Chroma 컬렉션임."""

    def __init__(self, rows: list[tuple[str, float, str]]) -> None:
        """(조각ID, 코사인 거리, 열람 등급) 목록을 받음."""

        self.metadata = {"embedding_model_signature": SIGNATURE, "hnsw:space": "cosine"}
        self._rows = list(rows)

    def count(self) -> int:
        """저장된 조각 수를 돌려줌."""

        return len(self._rows)

    def query(self, *, query_embeddings: Any, n_results: int, where: dict, include: Any) -> dict:
        """권한 필터를 적용한 뒤 거리가 가까운 순으로 n_results개를 돌려줌."""

        levels = list(where["access_level"]["$in"])
        hits = sorted(
            ((cid, distance) for cid, distance, level in self._rows if level in levels),
            key=lambda item: item[1],
        )[: int(n_results)]
        return {
            "ids": [[cid for cid, _ in hits]],
            "distances": [[distance for _, distance in hits]],
        }


class _StubIndex:
    """세대 교체만 확인할 때 쓰는 최소 색인 대역임."""

    def __init__(self, generation: str) -> None:
        """세대ID만 들고 있음."""

        self._generation = generation

    def generation_id(self) -> str:
        """세대ID를 돌려줌."""

        return self._generation

    def num_docs(self) -> int:
        """조각 수를 돌려줌."""

        return 2


def _stub_generation_index() -> GenerationIndex:
    """가짜 Chroma·BM25·분석기로 조립한 GenerationIndex를 만듦."""

    public = Chunk(
        chunk_id="D1_aaaa_0000",
        text="할부 수수료는 약관에 따릅니다.",
        index_text="할부 수수료는 약관에 따릅니다.",
        access_level="public",
        source=SourceInfo(source="D1.pdf", doc_key="D1", page=3),
    )
    restricted = Chunk(
        chunk_id="D3_bbbb_0000",
        text="고객: 상담 이력입니다.",
        index_text="고객: 상담 이력입니다.",
        access_level="restricted",
        source=SourceInfo(source="D3_S01.txt", doc_key="D3"),
    )
    zero = Chunk(
        chunk_id="D2_cccc_0000",
        text="관련 없는 조각입니다.",
        index_text="[카드: 한빛 테스트]\n관련 없는 조각입니다.",
        access_level="public",
        source=SourceInfo(source="D2.pdf", doc_key="D2", card_name="한빛 테스트"),
    )
    order = (public.chunk_id, zero.chunk_id, restricted.chunk_id)
    tokenizer = _StubTokenizer(
        {
            "할부 수수료": ["할부", "수수료"],
            "없는 낱말": ["모르는낱말"],
            "한빛테스트 3000000원 d2-c018": ["한빛테스트", "3000000원", "d2-c018", "혜택"],
        }
    )
    # 어휘 끝의 ""는 bm25s가 넣는 빈 토큰이며 점수 열이 없어 질의에서 빠져야 함.
    bm25 = _StubBm25(
        vocabulary={"할부": 0, "수수료": 1, "": 2},
        rows={0: [2.5, 0.0, 1.5], 1: [1.0, 0.0, 0.5]},
        num_docs=3,
    )
    collection = _StubCollection(
        [(public.chunk_id, 0.20, "public"), (zero.chunk_id, 0.45, "public"), (restricted.chunk_id, 0.10, "restricted")]
    )
    return GenerationIndex(
        generation=GENERATION,
        collection=collection,
        bm25=bm25,
        chunks={chunk.chunk_id: chunk for chunk in (public, zero, restricted)},
        order=order,
        tokenizer=tokenizer,
        embedder=_StubEmbedder(),
        document_frequency={"할부": 1, "수수료": 2},
        chunk_terms={
            public.chunk_id: frozenset({"할부", "수수료"}),
            zero.chunk_id: frozenset({"한빛테스트", "혜택"}),
            restricted.chunk_id: frozenset({"상담", "이력"}),
        },
    )


# ================================================================ 단위: 대조 실패


def test_서명과_해시가_모두_맞으면_가벼운_대조를_통과함(tmp_path: Path):
    files = build_fake_root(tmp_path)
    pointer = json.loads(files["pointer"].read_text(encoding="utf-8-sig"))
    paths = _provider(files["root"])._verify_files(pointer, GENERATION)
    assert paths["chunk_count"] == 2
    assert paths["collection"] == "card_docs"
    assert paths["embedding_signature"] == SIGNATURE


def test_ready가_아닌_세대는_쓰지_않음(tmp_path: Path):
    files = build_fake_root(tmp_path)
    patch_json(files["state"], status="text_index_ready")
    with pytest.raises(IndexUnavailableError) as error:
        _provider(files["root"]).acquire()
    assert "ready" in str(error.value)


def test_말뭉치_해시가_다르면_세대를_쓰지_않음(tmp_path: Path):
    files = build_fake_root(tmp_path)
    # 말뭉치 내용을 한 글자 바꾸면 포인터·manifest에 적힌 해시와 어긋남.
    files["corpus"].write_bytes(files["corpus"].read_bytes().replace(b"\xeb\x94\xb0", b"\xeb\x93\x9c"))
    with pytest.raises(IndexUnavailableError) as error:
        _provider(files["root"]).acquire()
    assert "말뭉치 해시" in str(error.value)


def test_조각_수가_다르면_세대를_쓰지_않음(tmp_path: Path):
    files = build_fake_root(tmp_path)
    patch_json(files["manifest"], chunk_count=99)
    with pytest.raises(IndexUnavailableError) as error:
        _provider(files["root"]).acquire()
    assert "조각 수" in str(error.value)


def test_색인_루트_밖을_가리키는_경로를_거부함(tmp_path: Path):
    files = build_fake_root(tmp_path)
    outside = tmp_path / "outside" / "search_indexes"
    outside.mkdir(parents=True)
    patch_json(files["pointer"], search_index_root="../outside/search_indexes")
    with pytest.raises(IndexUnavailableError) as error:
        _provider(files["root"]).acquire()
    assert "허용 범위 밖" in str(error.value)


def test_임베딩_revision이_기대값과_다르면_세대를_쓰지_않음(tmp_path: Path):
    files = build_fake_root(tmp_path)
    contract = dict(FAKE_CONTRACT)
    contract["revision"] = "다른revision"
    patch_json(files["manifest"], embedding_contract=contract)
    with pytest.raises(IndexUnavailableError) as error:
        _provider(files["root"]).acquire()
    assert "revision" in str(error.value)


def test_어휘_정책_지문이_다르면_세대를_쓰지_않음(tmp_path: Path):
    files = build_fake_root(tmp_path)
    patch_json(files["manifest"], lexical_policy_fingerprint="0" * 64)
    with pytest.raises(IndexUnavailableError) as error:
        _provider(files["root"]).acquire()
    assert "어휘 정책 지문" in str(error.value)


def test_표시_파일이_없으면_검색을_거부함(tmp_path: Path):
    root = tmp_path / "data"
    root.mkdir()
    with pytest.raises(IndexUnavailableError):
        _provider(root).acquire()


def test_시작_적재_실패는_예외를_올리지_않고_상태에_남김(tmp_path: Path):
    root = tmp_path / "data"
    root.mkdir()
    provider = _provider(root)
    assert provider.load_initial() is False
    status = provider.status()
    assert status["ready"] is False
    assert status["chunk_count"] == 0
    assert "시작 적재 실패" in status["last_error"]


# ================================================================ 단위: 세대 교체


def test_세대가_바뀌면_적재_뒤_다음_요청부터_새_세대를_씀(tmp_path: Path, monkeypatch):
    files = build_fake_root(tmp_path)
    provider = _provider(files["root"])
    monkeypatch.setattr(
        provider, "_load_generation", lambda pointer, generation: _StubIndex(generation)
    )

    first = provider.acquire()
    assert first.index.generation_id() == GENERATION
    assert first.warnings == ()

    patch_json(files["pointer"], generation="gen-test-0002")
    second = provider.acquire()
    # 대조가 끝나기 전이므로 이번 요청은 이전 세대로 처리하고 경고만 남김.
    assert second.index.generation_id() == GENERATION
    assert any("새 세대 적재 중" in warning for warning in second.warnings)

    provider.wait_for_reload()
    third = provider.acquire()
    assert third.index.generation_id() == "gen-test-0002"
    assert provider.status()["generation"] == "gen-test-0002"
    assert provider.status()["loading"] is False


def test_새_세대_대조가_실패하면_이전_세대를_계속_씀(tmp_path: Path, monkeypatch):
    files = build_fake_root(tmp_path)
    provider = _provider(files["root"])

    def loader(pointer: dict, generation: str) -> _StubIndex:
        if generation != GENERATION:
            raise ValueError("임베딩 서명이 다릅니다")
        return _StubIndex(generation)

    monkeypatch.setattr(provider, "_load_generation", loader)
    assert provider.acquire().index.generation_id() == GENERATION

    patch_json(files["pointer"], generation="gen-test-bad")
    provider.acquire()
    provider.wait_for_reload()
    lease = provider.acquire()
    assert lease.index.generation_id() == GENERATION
    assert any("대조 실패" in warning for warning in lease.warnings)
    assert "대조 실패" in provider.status()["last_error"]


# ================================================================ 단위: 검색 동작


def test_벡터_검색은_권한_밖_조각을_순위_전에_거름():
    index = _stub_generation_index()
    found = index.vector_search("할부 수수료", access_levels=("public",), k=5)
    assert [value.chunk_id for value in found] == ["D1_aaaa_0000", "D2_cccc_0000"]
    # 점수는 1 − 코사인 거리임.
    assert found[0].score == pytest.approx(0.80)


def test_벡터_검색은_auditor에게_restricted를_보여_줌():
    index = _stub_generation_index()
    found = index.vector_search("할부 수수료", access_levels=("public", "restricted"), k=1)
    assert [value.chunk_id for value in found] == ["D3_bbbb_0000"]


def test_bm25_검색은_점수_0과_권한_밖_조각을_뺌():
    index = _stub_generation_index()
    found = index.keyword_search("할부 수수료", access_levels=("public",), k=5)
    # 점수 0인 D2 조각과 권한 밖 D3 조각이 모두 빠짐.
    assert [value.chunk_id for value in found] == ["D1_aaaa_0000"]
    assert found[0].score == pytest.approx(3.5)

    both = index.keyword_search("할부 수수료", access_levels=("public", "restricted"), k=5)
    assert [value.chunk_id for value in both] == ["D1_aaaa_0000", "D3_bbbb_0000"]


def test_bm25_검색은_색인에_없는_낱말만_있으면_빈_목록을_줌():
    index = _stub_generation_index()
    assert index.keyword_search("없는 낱말", access_levels=("public",), k=5) == []


def test_권한_목록이_비면_검색하지_않음():
    index = _stub_generation_index()
    assert index.vector_search("할부 수수료", access_levels=(), k=5) == []
    assert index.keyword_search("할부 수수료", access_levels=(), k=5) == []


def test_조각_조회는_본문과_색인용_텍스트를_함께_줌():
    index = _stub_generation_index()
    found = index.get_chunks(["D2_cccc_0000", "없는ID"])
    assert set(found) == {"D2_cccc_0000"}
    chunk = found["D2_cccc_0000"]
    assert chunk.text == "관련 없는 조각입니다."
    assert chunk.index_text.startswith("[카드: 한빛 테스트]")
    assert chunk.source.card_name == "한빛 테스트"


def test_문서_빈도는_입력_순서를_지키고_없는_낱말은_0임():
    index = _stub_generation_index()
    assert index.document_frequency(["수수료", "할부", "모르는낱말"]) == {
        "수수료": 2,
        "할부": 1,
        "모르는낱말": 0,
    }


def test_조각별_낱말은_합집합으로_나옴():
    index = _stub_generation_index()
    assert index.chunk_terms(["D1_aaaa_0000", "D2_cccc_0000", "없는ID"]) == frozenset(
        {"할부", "수수료", "한빛테스트", "혜택"}
    )


def test_대상명과_조건_낱말을_가려냄():
    index = _stub_generation_index()
    text = "한빛테스트 3000000원 d2-c018"
    assert index.target_terms(text) == frozenset({"한빛테스트"})
    assert index.condition_terms(text) == frozenset({"한빛테스트", "3000000원", "d2-c018"})


def test_세대_정보를_그대로_알려_줌():
    index = _stub_generation_index()
    assert index.generation_id() == GENERATION
    assert index.num_docs() == 3


# ================================================================ 통합: 실제 색인·모델


def _real_embedder():
    """실제 KURE-v2 임베더를 로컬 캐시에서 만듦."""

    from app.infrastructure.embedder import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder(
        REAL_CONTRACT["model"],
        revision=REAL_CONTRACT["revision"],
        dimension=REAL_CONTRACT["dimension"],
        max_seq_length=800,
    )


@pytest.fixture(scope="module")
def real_index():
    """실제 사용 중 세대를 한 번 올려 통합 시험에서 함께 씀."""

    if not (REAL_DATA_ROOT / POINTER_NAME).is_file():
        pytest.skip(f"실제 색인이 없습니다: {REAL_DATA_ROOT}")
    provider = LocalIndexProvider(
        REAL_DATA_ROOT,
        embedder=_real_embedder(),
        expected_embedding_contract=dict(REAL_CONTRACT),
    )
    started = time.perf_counter()
    loaded = provider.load_initial()
    elapsed = time.perf_counter() - started
    assert loaded is True, provider.status()["last_error"]
    print(f"\n[실측] 세대 적재 {elapsed * 1000:.0f} ms")
    return provider


@pytest.mark.integration
def test_실제_세대를_올리고_상태를_알려_줌(real_index):
    status = real_index.status()
    pointer = json.loads((REAL_DATA_ROOT / POINTER_NAME).read_text(encoding="utf-8-sig"))
    assert status["ready"] is True
    assert status["loading"] is False
    assert status["last_error"] == ""
    assert status["generation"] == str(pointer["generation"])
    assert status["chunk_count"] == int(pointer["chunk_count"])


@pytest.mark.integration
def test_조립한_분석기_서명이_manifest와_같음():
    if not (REAL_DATA_ROOT / POINTER_NAME).is_file():
        pytest.skip("실제 색인이 없습니다.")
    pointer = json.loads((REAL_DATA_ROOT / POINTER_NAME).read_text(encoding="utf-8-sig"))
    search_root = REAL_DATA_ROOT / str(pointer["search_index_root"])
    search_pointer = json.loads((search_root / "active_index.json").read_text(encoding="utf-8-sig"))
    manifest = json.loads(
        (search_root / str(search_pointer["manifest"])).read_text(encoding="utf-8-sig")
    )
    words = tuple(
        (parts[0], parts[1], float(parts[2]))
        for parts in (
            line.split("\t")
            for line in (search_root / str(search_pointer["card_dictionary"]))
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    )
    aliases = {
        parts[0]: parts[1]
        for parts in (
            line.split("\t")
            for line in (search_root / str(search_pointer["card_aliases"]))
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    }
    assert len(words) == 64
    assert len(aliases) == 189
    tokenizer = KoreanTokenizer(None, additional_user_words=words, aliases=aliases)
    assert tokenizer.signature == manifest["tokenizer_signature"]


@pytest.mark.integration
def test_agent는_restricted_조각을_절대_받지_못함(real_index):
    index = real_index.acquire().index
    question = "2026-02 승인 거래 합계와 생활비 예산 상담 내용을 알려 주세요"
    # 첫 검색에는 임베딩 모델 적재가 섞이므로, 실측 시간은 모델이 올라온 뒤로 잼.
    index.vector_search("준비 질의", access_levels=("public",), k=1)
    started = time.perf_counter()
    agent_vector = index.vector_search(question, access_levels=("public",), k=10)
    vector_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    agent_keyword = index.keyword_search(question, access_levels=("public",), k=10)
    keyword_ms = (time.perf_counter() - started) * 1000
    print(f"\n[실측] 벡터 검색 {vector_ms:.0f} ms · BM25 검색 {keyword_ms:.0f} ms")

    assert agent_vector, "공개 등급 후보가 하나도 없음"
    for found in list(agent_vector) + list(agent_keyword):
        chunk = index.get_chunks([found.chunk_id])[found.chunk_id]
        assert chunk.access_level == "public"
        assert chunk.source.doc_key != "D3"

    auditor_vector = index.vector_search(question, access_levels=("public", "restricted"), k=10)
    levels = {
        index.get_chunks([found.chunk_id])[found.chunk_id].access_level for found in auditor_vector
    }
    assert "restricted" in levels, "auditor인데 상담 이력이 하나도 안 나옴"


@pytest.mark.integration
def test_별칭_질의가_정식_카드_토큰으로_바뀜(real_index):
    index = real_index.acquire().index
    tokens = index.tokens("모아생활 혜택이 뭐예요")
    assert "모아생활" not in tokens
    assert any(token.startswith("한빛") and "모아생활" in token for token in tokens), tokens
    assert index.target_terms("모아생활 혜택이 뭐예요")


@pytest.mark.integration
def test_벡터_점수와_문서_빈도가_색인_규모_안에_있음(real_index):
    index = real_index.acquire().index
    found = index.vector_search("할부 수수료는 어떻게 계산하나요", access_levels=("public",), k=5)
    assert len(found) == 5
    for value in found:
        assert -1.0 <= value.score <= 1.0
    terms = index.keyword_candidates("할부 수수료는 어떻게 계산하나요")
    frequency = index.document_frequency(terms)
    assert list(frequency) == list(dict.fromkeys(terms))
    assert all(0 <= count <= index.num_docs() for count in frequency.values())


@pytest.mark.integration
def test_리랭커_점수가_0과_1_사이임():
    from app.infrastructure.reranker import CrossEncoderReranker

    reranker = CrossEncoderReranker(RERANKER_MODEL, revision=RERANKER_REVISION)
    scores = reranker.score(
        "할부 수수료는 어떻게 계산하나요",
        ["할부 수수료는 이용 금액과 기간에 따라 계산합니다.", "오늘 점심은 무엇을 먹을까요."],
    )
    assert len(scores) == 2
    assert all(0.0 <= value <= 1.0 for value in scores)
    assert scores[0] > scores[1]
    assert reranker.score("질문", []) == []


def _clone_generation(destination: Path, source_generation: str, new_generation: str) -> None:
    """같은 내용의 세대를 다른 세대ID로 복사해 세대 전환을 재현함."""

    source = destination / "generations" / source_generation
    target = destination / "generations" / new_generation
    shutil.copytree(source, target)
    inner_root = target / "search_indexes" / "generations"
    (inner_root / source_generation).rename(inner_root / new_generation)

    patch_json(target / "generation_state.json", generation=new_generation)
    search_pointer_path = target / "search_indexes" / "active_index.json"
    pointer = json.loads(search_pointer_path.read_text(encoding="utf-8-sig"))
    pointer = {
        key: (
            value.replace(f"generations/{source_generation}/", f"generations/{new_generation}/")
            if isinstance(value, str)
            else value
        )
        for key, value in pointer.items()
    }
    pointer["generation"] = new_generation
    _write_json(search_pointer_path, pointer)

    manifest_path = target / "search_indexes" / str(pointer["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest["generation"] = new_generation
    for key in ("card_dictionary", "card_aliases"):
        entry = dict(manifest.get(key) or {})
        if isinstance(entry.get("path"), str):
            entry["path"] = entry["path"].replace(
                f"generations/{source_generation}/", f"generations/{new_generation}/"
            )
        manifest[key] = entry
    _write_json(manifest_path, manifest)


@pytest.mark.integration
def test_실제_세대가_바뀌면_백그라운드_적재_뒤_교체됨(tmp_path: Path):
    if not (REAL_DATA_ROOT / POINTER_NAME).is_file():
        pytest.skip("실제 색인이 없습니다.")
    root = tmp_path / "data"
    (root / "generations").mkdir(parents=True)
    shutil.copytree(
        REAL_DATA_ROOT / "generations" / REAL_GENERATION,
        root / "generations" / REAL_GENERATION,
    )
    source_pointer = json.loads((REAL_DATA_ROOT / POINTER_NAME).read_text(encoding="utf-8-sig"))
    _write_json(root / POINTER_NAME, source_pointer)

    next_generation = "gen-ch2-20261003-002-copy0001"
    _clone_generation(root, REAL_GENERATION, next_generation)

    provider = LocalIndexProvider(
        root,
        embedder=_real_embedder(),
        expected_embedding_contract=dict(REAL_CONTRACT),
    )
    assert provider.load_initial() is True, provider.status()["last_error"]
    assert provider.status()["generation"] == REAL_GENERATION

    _write_json(
        root / POINTER_NAME,
        {
            **source_pointer,
            "generation": next_generation,
            "chroma_path": f"generations/{next_generation}/chroma",
            "search_index_root": f"generations/{next_generation}/search_indexes",
        },
    )
    during = provider.acquire()
    assert during.index.generation_id() == REAL_GENERATION
    assert any("새 세대 적재 중" in warning for warning in during.warnings)

    provider.wait_for_reload()
    after = provider.acquire()
    assert after.index.generation_id() == next_generation, provider.status()["last_error"]
    assert after.warnings == ()
    assert after.index.num_docs() == int(source_pointer["chunk_count"])
