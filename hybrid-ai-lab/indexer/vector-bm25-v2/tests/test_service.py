"""Application 업무 흐름을 외부 모델·DB 없이 검증함."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.application.indexing_service import IndexingService, IndexingWorkflow
from app.application.models import IndexRequest, IndexingError
from app.domain.models import (
    IndexSnapshot,
    LoadedDocument,
    PreparedChunk,
    Publication,
    RawChunk,
    SourceRef,
    SplitPolicy,
)
from app.infrastructure.graph import LangGraphPipeline


def digest(value: str) -> str:
    """시험 데이터의 안정적인 SHA-256 지문을 생성함."""
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass
class Backend:
    """가짜 포트들이 공유하는 세대별 저장 상태를 메모리에 보관함."""
    artifacts: dict[str, object] = field(default_factory=dict)
    staging_chunks: dict[str, dict[str, PreparedChunk]] = field(default_factory=dict)
    staging_vectors: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    text_index_stages: dict[str, dict[str, object]] = field(default_factory=dict)
    active: IndexSnapshot | None = None
    active_vectors: dict[str, list[float]] = field(default_factory=dict)
    active_generation: str | None = None


class Artifacts:
    """체크포인트 외부의 큰 상태를 복사하여 보관하는 시험용 아티팩트 저장소임."""

    def __init__(self, backend: Backend) -> None:
        """공유 메모리 저장 상태를 주입받음."""
        self.backend = backend

    def save(self, run_id, name, value):
        """실행과 이름으로 만든 참조에 값의 복사본을 저장함."""
        reference = f"{run_id}/{name}"
        self.backend.artifacts[reference] = deepcopy(value)
        return reference

    def load(self, reference):
        """저장된 값이 호출자에게서 변형되지 않도록 복사본을 반환함."""
        return deepcopy(self.backend.artifacts[reference])


class Sources:
    """문서 종류와 상담 구간 조건을 적용하는 시험용 원천 탐색기임."""

    def __init__(self, refs: list[SourceRef]) -> None:
        """탐색 후보와 호출 횟수 기록을 초기화함."""
        self.refs = refs
        self.calls = 0

    def discover(self, input_path, doc, segment):
        """전체 후보에서 요청 문서 종류와 상담 구간에 맞는 원천만 반환함."""
        del input_path
        self.calls += 1
        return [
            ref
            for ref in self.refs
            if (doc == "all" or ref.doc_key == doc)
            and not (
                segment is not None
                and ref.doc_key == "D3"
                and f"S{int(segment):02d}" not in ref.source
            )
        ]


class Loader:
    """원천 지문을 본문으로 바꾸어 변경 여부를 쉽게 확인하는 시험용 로더임."""

    def __init__(self, metadata_version: str = "v1") -> None:
        """생성할 메타데이터 버전과 호출 횟수를 초기화함."""
        self.metadata_version = metadata_version
        self.calls = 0

    def load(self, source):
        """원천 하나를 지문 기반 본문과 버전 메타데이터가 있는 문서로 변환함."""
        self.calls += 1
        return [
            LoadedDocument(
                document_id=f"doc-{source.source}",
                source=source.source,
                doc_key=source.doc_key,
                text=f"text:{source.sha256}",
                metadata={"source": source.source, "doc_key": source.doc_key, "version": self.metadata_version},
            )
        ]


class Splitter:
    """문서 전체를 청크 하나로 반환하여 응용 흐름만 격리하는 시험용 분할기임."""

    def __init__(self) -> None:
        """분할 호출 횟수를 0으로 초기화함."""
        self.calls = 0

    def split(self, document, policy):
        """정책 값과 무관하게 문서 전체 좌표를 가진 청크 하나를 반환함."""
        del policy
        self.calls += 1
        return [RawChunk(document=document, text=document.text, start=0, end=len(document.text), ordinal=0)]


class TokenCounter:
    """문자 수를 토큰 수로 간주하는 결정적인 시험용 계산기임."""

    signature = "tokens-v1"
    max_tokens = 8192

    def count(self, text):
        """본문 문자 수를 토큰 수로 반환함."""
        return len(text)


class Processor:
    """청크 본문과 메타데이터의 해시를 만드는 시험용 정제기임."""

    def __init__(self) -> None:
        """정제 호출 횟수를 0으로 초기화함."""
        self.calls = 0

    def process(self, chunk):
        """검색에 저장할 청크 ID·본문·메타데이터 해시를 결정적으로 생성함."""
        self.calls += 1
        metadata = dict(chunk.document.metadata)
        metadata_hash = digest(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
        return PreparedChunk(
            chunk_id=f"{chunk.document.source}:{chunk.ordinal}",
            text=chunk.text,
            metadata=metadata,
            token_count=len(chunk.text),
            text_hash=digest(chunk.text),
            metadata_hash=metadata_hash,
        )


class Embedder:
    """본문 길이로 재현 가능한 2차원 벡터를 만드는 시험용 임베더임."""

    signature = "embed-v1"
    dimension = 2

    def __init__(self) -> None:
        """배치별 임베딩 입력을 기록할 목록을 준비함."""
        self.calls: list[list[str]] = []

    def embed(self, texts):
        """재임베딩 여부를 검증할 수 있도록 입력을 기록하고 가짜 벡터를 반환함."""
        self.calls.append(list(texts))
        return [[float(len(text)), 1.0] for text in texts]


class Repository:
    """준비 세대와 활성 세대의 전환을 메모리에서 재현하는 시험용 저장소임."""

    def __init__(self, backend: Backend) -> None:
        """공유 저장 상태와 포트별 호출 횟수·게시 실패 설정을 초기화함."""
        self.backend = backend
        self.begin_calls = 0
        self.upsert_calls = 0
        self.build_text_index_calls = 0
        self.publish_calls = 0
        self.vector_reads = 0
        self.fail_publish = False

    def load_active(self):
        """현재 활성 세대의 스냅샷을 반환하며 없으면 None을 반환함."""
        return self.backend.active

    def get_vectors(self, chunk_ids):
        """요청 ID 중 활성 세대에 존재하는 벡터만 반환함."""
        self.vector_reads += 1
        return {
            chunk_id: self.backend.active_vectors[chunk_id]
            for chunk_id in chunk_ids
            if chunk_id in self.backend.active_vectors
        }

    def begin(self, generation, embedding_signature):
        """대상 세대의 청크·벡터 준비 영역을 중복 생성 없이 마련함."""
        del embedding_signature
        self.begin_calls += 1
        self.backend.staging_chunks.setdefault(generation, {})
        self.backend.staging_vectors.setdefault(generation, {})

    def upsert(self, generation, chunks, vectors):
        """대상 세대에 같은 ID를 덮어쓸 수 있도록 청크와 벡터를 저장함."""
        self.upsert_calls += 1
        for chunk, vector in zip(chunks, vectors, strict=True):
            self.backend.staging_chunks[generation][chunk.chunk_id] = chunk
            self.backend.staging_vectors[generation][chunk.chunk_id] = list(vector)

    def build_text_index(self, generation, chunks, manifest):
        """키워드 검색용 BM25 준비 단계의 검증 증거를 결정적으로 생성함."""
        self.build_text_index_calls += 1
        manifest_sha256 = digest(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
        corpus_sha256 = digest("\n".join(chunk.text for chunk in chunks))
        stage = {
            "generation": generation,
            "chunk_count": len(chunks),
            "manifest_sha256": manifest_sha256,
            "corpus_sha256": corpus_sha256,
        }
        self.backend.text_index_stages[generation] = stage
        return dict(stage)

    def publish(self, generation, chunks, manifest, text_index_stage):
        """준비 세대를 활성 스냅샷으로 한 번에 바꾸거나 설정된 게시 장애를 발생시킴."""
        self.publish_calls += 1
        if self.fail_publish:
            raise RuntimeError("publish failed")
        assert text_index_stage == self.backend.text_index_stages[generation]
        stored = dict(manifest)
        publication = Publication(
            generation=generation,
            chroma_path=f"chroma/{generation}",
            search_index_root=f"search/{generation}",
            collection="card_docs",
            chunk_count=len(chunks),
        )
        stored["publication"] = {
            "generation": publication.generation,
            "chroma_path": publication.chroma_path,
            "search_index_root": publication.search_index_root,
            "collection": publication.collection,
            "chunk_count": publication.chunk_count,
        }
        self.backend.active = IndexSnapshot(chunks=tuple(chunks), manifest=stored)
        self.backend.active_vectors = dict(self.backend.staging_vectors[generation])
        self.backend.active_generation = generation
        return publication


def components(
    directory: str,
    backend: Backend,
    *,
    thread_id: str,
    source_hash: str = "source-v1",
    profile_signature: str = "profile-v1",
    metadata_version: str = "v1",
    embedding_contract: dict | None = None,
    progress=None,
):
    """외부 모델·DB 없이 인덱싱 흐름을 실행할 서비스와 가짜 포트를 조립함.

    인자: directory는 체크포인트와 출력 경로로 사용할 임시 디렉터리임.
    반환값: 서비스·요청·주요 가짜 포트를 호출 순서대로 담은 tuple임.
    부수효과: directory 아래에 SQLite 체크포인트 파일이 생성될 수 있음.
    """
    source_port = Sources([SourceRef("D1.pdf", "D1.pdf", "D1", source_hash)])
    loader = Loader(metadata_version)
    splitter = Splitter()
    processor = Processor()
    embedder = Embedder()
    repository = Repository(backend)
    workflow = IndexingWorkflow(
        sources=source_port,
        loader=loader,
        splitter=splitter,
        token_counter=TokenCounter(),
        processor=processor,
        embedder=embedder,
        repository=repository,
        artifacts=Artifacts(backend),
        policies={"D1": SplitPolicy()},
        default_policy=SplitPolicy(),
        policy_signature="policy-800-200",
        profile_signature=profile_signature,
        embedding_contract=embedding_contract,
        embed_batch_size=1,
        upsert_batch_size=1,
    )
    runner = LangGraphPipeline(workflow, Path(directory) / "checkpoint.sqlite", progress=progress)
    service = IndexingService(
        runner,
        policy_signature=workflow.policy_signature,
        profile_signature=workflow.profile_signature,
        embedding_signature=embedder.signature,
        embedding_dimension=embedder.dimension,
    )
    request = IndexRequest(
        input_path=Path(directory),
        output_path=Path(directory) / "out",
        thread_id=thread_id,
    )
    return service, request, source_port, loader, splitter, processor, embedder, repository


def test_unchanged_sources_finish_without_loading_splitting_embedding_or_publish() -> None:
    """원천과 정책이 같으면 로딩 이후 작업과 새 세대 게시를 모두 생략함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[0].run(first[1])

        second = components(directory, backend, thread_id="second")
        result = second[0].run(second[1])

        assert result.no_op is True
        assert second[3].calls == 0
        assert second[4].calls == 0
        assert second[5].calls == 0
        assert second[6].calls == []
        assert second[7].begin_calls == 0
        assert second[7].upsert_calls == 0
        assert second[7].build_text_index_calls == 0
        assert second[7].publish_calls == 0


def test_workflow_records_the_seven_checkpointable_node_names() -> None:
    """정상 실행의 시간 지표가 합의한 일곱 노드 이름으로 기록됨을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        value = components(directory, backend, thread_id="node-names")

        result = value[0].run(value[1])

        assert set(result.timings) == {
            "discover_docs",
            "load_split_clean",
            "prepare_embed",
            "embed",
            "upsert",
            "build_text_index",
            "publish",
            "total_ms",
        }


class ProgressRecorder:
    """노드 완료 알림을 순서대로 모으는 가짜 진행 알림 포트임."""

    def __init__(self) -> None:
        """받은 알림을 (노드, 노드 초, 누적 초) 순서로 담을 빈 목록을 만듦."""
        self.events: list[tuple[str, float, float]] = []

    def node_completed(self, node: str, node_seconds: float, total_seconds: float) -> None:
        """알림 한 건을 받은 순서대로 기록함."""
        self.events.append((node, node_seconds, total_seconds))


def test_each_completed_node_reports_its_time_and_running_total() -> None:
    """노드가 끝날 때마다 실행 순서대로 노드 시간과 줄어들지 않는 누적 시간을 알림을 보증함."""
    with TemporaryDirectory() as directory:
        recorder = ProgressRecorder()
        value = components(directory, Backend(), thread_id="progress", progress=recorder)

        value[0].run(value[1])

        assert [node for node, _, _ in recorder.events] == [
            "discover_docs",
            "load_split_clean",
            "prepare_embed",
            "embed",
            "upsert",
            "build_text_index",
            "publish",
        ]
        totals = [total for _, _, total in recorder.events]
        assert totals == sorted(totals)
        assert all(0 <= node_seconds <= total for _, node_seconds, total in recorder.events)


def test_metadata_only_change_reuses_vector_without_embedding() -> None:
    """본문이 같고 메타데이터만 바뀌면 기존 벡터를 재사용해 새 메타데이터를 게시함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[0].run(first[1])
        original_vector = dict(backend.active_vectors)

        second = components(
            directory,
            backend,
            thread_id="metadata-change",
            profile_signature="profile-v2",
            metadata_version="v2",
        )
        result = second[0].run(second[1])

        assert result.no_op is False
        assert result.index.newly_embedded == 0
        assert result.index.skipped_by_hash == 1
        assert second[6].calls == []
        assert second[7].vector_reads == 1
        assert backend.active_vectors == original_vector
        assert backend.active.chunks[0].metadata["version"] == "v2"


def test_embedding_contract_change_reembeds_even_when_legacy_signature_is_same() -> None:
    """모델 서명이 같아도 임베딩 계약의 revision이 바뀌면 다시 임베딩함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first", embedding_contract={"revision": "r1"})
        first[0].run(first[1])

        second = components(directory, backend, thread_id="contract-v2", embedding_contract={"revision": "r2"})
        result = second[0].run(second[1])

        assert result.index.newly_embedded == 1
        assert len(second[6].calls) == 1


class RenamedProcessor(Processor):
    """같은 본문에 다른 기본 청크 ID를 부여하는 시험용 정제기임."""

    def process(self, chunk):
        """상위 정제 결과를 유지하고 청크의 기본 ID만 변경함."""
        prepared = super().process(chunk)
        return PreparedChunk(
            "renamed-base",
            prepared.text,
            prepared.metadata,
            prepared.token_count,
            prepared.text_hash,
            prepared.metadata_hash,
        )


def test_same_text_reuses_old_vector_when_chunk_id_changes() -> None:
    """청크 ID가 달라도 본문 해시가 같으면 기존 벡터를 재사용함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[0].run(first[1])
        original_vector = next(iter(backend.active_vectors.values()))

        second = components(
            directory,
            backend,
            thread_id="renamed-id",
            profile_signature="profile-v2",
        )
        second[0].runner.workflow.processor = RenamedProcessor()
        result = second[0].run(second[1])

        assert result.index.newly_embedded == 0
        assert second[6].calls == []
        assert list(backend.active_vectors.values()) == [original_vector]
        assert backend.active.chunks[0].chunk_id == "renamed-base_0000"


def test_content_based_ids_survive_different_text_inserted_before_them() -> None:
    """앞에 새 청크가 삽입되어도 기존 본문 기반 ID가 바뀌지 않음을 보증함."""

    def chunk(base: str, text: str) -> PreparedChunk:
        """ID 안정성 비교에 필요한 최소 준비 청크를 생성함."""
        return PreparedChunk(base, text, {"source": "D1.pdf"}, len(text), digest(text), "old")

    original = IndexingWorkflow._finalize_document_chunks(
        [chunk("doc_alpha", "alpha"), chunk("doc_beta", "beta")]
    )
    inserted = IndexingWorkflow._finalize_document_chunks(
        [chunk("doc_new", "new"), chunk("doc_alpha", "alpha"), chunk("doc_beta", "beta")]
    )

    assert [item.chunk_id for item in original] == ["doc_alpha_0000", "doc_beta_0000"]
    assert [item.chunk_id for item in inserted[1:]] == ["doc_alpha_0000", "doc_beta_0000"]
    assert [item.metadata["chunk_index"] for item in inserted] == [0, 1, 2]


def test_identical_text_uses_document_local_duplicate_suffixes() -> None:
    """같은 문서의 동일 본문은 충돌 없이 문서 내부 중복 순번을 받음을 보증함."""
    repeated = PreparedChunk("doc_same", "same", {}, 1, digest("same"), "old")
    result = IndexingWorkflow._finalize_document_chunks([repeated, repeated])

    assert [item.chunk_id for item in result] == ["doc_same_0000", "doc_same_0001"]
    assert [item.metadata["chunk_id"] for item in result] == ["doc_same_0000", "doc_same_0001"]


def test_publish_failure_keeps_previous_active_generation() -> None:
    """새 세대 게시가 실패하면 이전 활성 세대를 계속 가리킴을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[0].run(first[1])
        active_before = backend.active_generation

        second = components(directory, backend, thread_id="changed", source_hash="source-v2")
        second[7].fail_publish = True
        with pytest.raises(RuntimeError, match="publish failed"):
            second[0].run(second[1])

        assert backend.active_generation == active_before


def test_full_refresh_removes_deleted_source_without_reembedding_unchanged_source() -> None:
    """전체 갱신에서 사라진 원천은 제거하고 남은 같은 본문의 벡터는 재사용함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[2].refs = [
            SourceRef("D1.pdf", "D1.pdf", "D1", "d1-v1"),
            SourceRef("D2.pdf", "D2.pdf", "D2", "d2-v1"),
        ]
        first[0].run(first[1])

        second = components(directory, backend, thread_id="remove-d2")
        second[2].refs = [SourceRef("D1.pdf", "D1.pdf", "D1", "d1-v1")]
        result = second[0].run(second[1])

        assert result.index.collection_count == 1
        assert result.index.newly_embedded == 0
        assert {chunk.metadata["source"] for chunk in backend.active.chunks} == {"D1.pdf"}


def test_partial_doc_refresh_preserves_unselected_sources() -> None:
    """문서 종류 일부만 갱신할 때 선택하지 않은 원천과 지문을 보존함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[2].refs = [
            SourceRef("D1.pdf", "D1.pdf", "D1", "d1-v1"),
            SourceRef("D2.pdf", "D2.pdf", "D2", "d2-v1"),
        ]
        first[0].run(first[1])

        second = components(directory, backend, thread_id="partial-d1", source_hash="ignored")
        second[2].refs = [
            SourceRef("D1.pdf", "D1.pdf", "D1", "d1-v2"),
            SourceRef("D2.pdf", "D2.pdf", "D2", "d2-v1"),
        ]
        request = second[1].model_copy(update={"doc": "D1"})
        result = second[0].run(request)

        assert result.index.collection_count == 2
        assert {chunk.metadata["source"] for chunk in backend.active.chunks} == {"D1.pdf", "D2.pdf"}
        assert backend.active.manifest["inputs_sha256"] == {"D1.pdf": "d1-v2", "D2.pdf": "d2-v1"}


def test_doc_all_with_segment_preserves_other_consultation_segments() -> None:
    """상담 구간 하나만 갱신할 때 다른 문서와 상담 구간은 유지됨을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[2].refs = [
            SourceRef("D1.pdf", "D1.pdf", "D1", "d1-v1"),
            SourceRef("D3_S01.txt", "D3_S01.txt", "D3", "s1-v1"),
            SourceRef("D3_S02.txt", "D3_S02.txt", "D3", "s2-v1"),
        ]
        first[0].run(first[1])

        second = components(directory, backend, thread_id="partial-segment")
        second[2].refs = [
            SourceRef("D1.pdf", "D1.pdf", "D1", "d1-v1"),
            SourceRef("D3_S01.txt", "D3_S01.txt", "D3", "s1-v2"),
            SourceRef("D3_S02.txt", "D3_S02.txt", "D3", "s2-v1"),
        ]
        request = second[1].model_copy(update={"doc": "all", "segment": 1})
        result = second[0].run(request)

        assert result.index.collection_count == 3
        assert {chunk.metadata["source"] for chunk in backend.active.chunks} == {
            "D1.pdf",
            "D3_S01.txt",
            "D3_S02.txt",
        }
        assert backend.active.manifest["inputs_sha256"] == {
            "D1.pdf": "d1-v1",
            "D3_S01.txt": "s1-v2",
            "D3_S02.txt": "s2-v1",
        }


def test_partial_refresh_rejects_global_policy_change() -> None:
    """전역 청킹 정책 변경을 일부 문서에만 적용하지 못하도록 전체 실행을 요구함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[0].run(first[1])

        second = components(directory, backend, thread_id="partial-policy")
        second[0].runner.workflow.policy_signature = "policy-v2"
        second[0].policy_signature = "policy-v2"
        request = second[1].model_copy(update={"doc": "D1"})
        with pytest.raises(IndexingError, match="전체 실행"):
            second[0].run(request)


def test_zero_sources_fails_without_replacing_active_generation() -> None:
    """탐색된 원천이 없으면 오류를 내고 기존 활성 세대를 보존함을 보증함."""
    with TemporaryDirectory() as directory:
        backend = Backend()
        first = components(directory, backend, thread_id="first")
        first[0].run(first[1])
        active_before = backend.active_generation

        second = components(directory, backend, thread_id="empty")
        second[2].refs = []
        with pytest.raises(IndexingError, match="원천 문서가 없습니다"):
            second[0].run(second[1])

        assert backend.active_generation == active_before

