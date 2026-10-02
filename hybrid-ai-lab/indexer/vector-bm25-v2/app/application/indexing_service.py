"""색인 업무 순서와 단계별 상태 전이를 정의함."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import re
from time import monotonic
from typing import Any, Mapping

from app.domain.models import (
    IndexSnapshot,
    PreparedChunk,
    Publication,
    SourceRef,
    SplitPolicy,
)

from .models import (
    ChunkSummary,
    ExtractSummary,
    IndexRequest,
    IndexResult,
    IndexSummary,
    IndexingError,
)
from .ports import (
    ArtifactStorePort,
    ChunkProcessorPort,
    DocumentLoaderPort,
    EmbedderPort,
    IndexRepositoryPort,
    PipelineRunnerPort,
    SourceCatalogPort,
    TextSplitterPort,
    TokenCounterPort,
)
from .state import IndexerState


WORKFLOW_VERSION = "indexing-workflow-v2"


def _stable_hash(value: Any) -> str:
    """키 순서를 고정한 JSON으로 SHA-256 지문을 만듦."""

    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _source_to_dict(source: SourceRef) -> dict[str, Any]:
    """체크포인트에 저장할 수 있도록 원천 참조를 dict로 변환함."""

    return asdict(source)


def _source_from_dict(value: Mapping[str, Any]) -> SourceRef:
    """체크포인트의 dict에서 원천 참조를 복원함."""

    return SourceRef(
        path=str(value["path"]),
        source=str(value["source"]),
        doc_key=str(value["doc_key"]),
        sha256=str(value["sha256"]),
    )


def _chunk_to_dict(chunk: PreparedChunk) -> dict[str, Any]:
    """외부 산출물 저장소에 기록할 수 있도록 청크를 dict로 변환함."""

    return asdict(chunk)


def _chunk_from_dict(value: Mapping[str, Any]) -> PreparedChunk:
    """외부 산출물 값에서 정제 완료 청크를 복원함."""

    return PreparedChunk(
        chunk_id=str(value["chunk_id"]),
        text=str(value["text"]),
        metadata=dict(value.get("metadata", {})),
        token_count=int(value["token_count"]),
        text_hash=str(value["text_hash"]),
        metadata_hash=str(value["metadata_hash"]),
    )


def _publication_to_dict(publication: Publication) -> dict[str, Any]:
    """게시 결과를 체크포인트에 저장 가능한 dict로 변환함."""

    return asdict(publication)


def _request_dict(request: IndexRequest) -> dict[str, Any]:
    """Path를 포함한 요청을 JSON 호환 값으로 직렬화함."""

    return request.model_dump(mode="json")


def _selected_source(request: Mapping[str, Any], source: str, doc_key: str) -> bool:
    """원천이 부분 실행의 문서 유형과 상담 세그먼트 범위에 속하는지 판정함."""

    selected = str(request.get("doc", "all"))
    if selected != "all" and selected != doc_key:
        return False
    segment = request.get("segment")
    if segment is None or doc_key != "D3":
        return True
    marker = re.compile(rf"(?:^|[_-])S0?{int(segment)}(?:[_.-]|$)", re.IGNORECASE)
    return marker.search(source) is not None


class IndexingWorkflow:
    """주입받은 포트로 색인 단계의 업무 규칙을 실행함.

    그래프 구성이나 외부 구현체 생성은 담당하지 않으며, 각 메서드는 체크포인트 상태 갱신값만 반환함.
    """

    def __init__(
        self,
        *,
        sources: SourceCatalogPort,
        loader: DocumentLoaderPort,
        splitter: TextSplitterPort,
        token_counter: TokenCounterPort,
        processor: ChunkProcessorPort,
        embedder: EmbedderPort,
        repository: IndexRepositoryPort,
        artifacts: ArtifactStorePort,
        policies: Mapping[str, SplitPolicy],
        default_policy: SplitPolicy,
        policy_signature: str,
        profile_signature: str,
        embedding_contract: Mapping[str, Any] | None = None,
        embed_batch_size: int = 32,
        upsert_batch_size: int = 32,
    ) -> None:
        """업무 포트와 정책·배치 크기를 주입받아 상태 없는 워크플로를 구성함.

        인자: embed_batch_size와 upsert_batch_size는 각각 한 번에 처리할 청크 수이며 양수여야 함.
        예외: 배치 크기가 0 이하이면 ValueError를 발생시킴.
        부수효과: 없음. 포트 호출은 각 단계 메서드에서 수행함.
        """

        if embed_batch_size <= 0 or upsert_batch_size <= 0:
            raise ValueError("배치 크기는 양수여야 합니다.")
        self.sources = sources
        self.loader = loader
        self.splitter = splitter
        self.token_counter = token_counter
        self.processor = processor
        self.embedder = embedder
        self.repository = repository
        self.artifacts = artifacts
        self.policies = dict(policies)
        self.default_policy = default_policy
        self.policy_signature = policy_signature
        self.profile_signature = profile_signature
        self.embedding_contract = dict(embedding_contract or {})
        self.embed_batch_size = embed_batch_size
        self.upsert_batch_size = upsert_batch_size

    def discover_docs(self, state: IndexerState) -> dict[str, Any]:
        """원천 지문만 읽어 무변경 실행을 조기에 끝낼지 판단함.

        목적: 비싼 문서 추출과 임베딩 전에 변경 여부와 부분 실행 가능성을 확정하기 위함.
        인자: state에는 직렬화된 요청과 실행·계약 서명이 있어야 함.
        반환값: 발견 원천, 전체 원천 지문, 무변경 여부, 기존 게시 정보를 담은 상태 갱신값임.
        예외: 원천이 없거나 변경된 계약으로 부분 실행하면 IndexingError를 발생시킴.
        부수효과: 원천 파일과 활성 세대를 읽지만 변경하지 않음.
        """

        request = state["request"]
        partial = str(request.get("doc", "all")) != "all" or request.get("segment") is not None
        discovered = self.sources.discover(
            str(request["input_path"]),
            str(request.get("doc", "all")),
            request.get("segment"),
        )
        if not discovered:
            raise IndexingError("선택 조건에 맞는 원천 문서가 없습니다.")
        source_rows = [_source_to_dict(source) for source in discovered]
        inputs = {source.source: source.sha256 for source in discovered}
        doc_keys = {source.source: source.doc_key for source in discovered}
        active = self.repository.load_active()
        if active is not None and partial:
            # 부분 실행은 선택하지 않은 기존 청크를 보존하므로 처리 계약 일부만 바꾸면 세대 내 규칙이 섞임.
            changed_contracts: list[str] = []
            if active.manifest.get("policy_signature") != self.policy_signature:
                changed_contracts.append("청킹 정책")
            if active.manifest.get("profile_signature") != self.profile_signature:
                changed_contracts.append("문서 프로필")
            if changed_contracts:
                raise IndexingError(
                    f"부분 실행에서 {'·'.join(changed_contracts)} 변경을 적용할 수 없습니다. "
                    "--doc all과 segment 미지정으로 전체 실행해야 합니다."
                )
        
        # 선택 범위의 원천과 모든 처리 계약이 활성 세대와 같은지 판정함
        no_op = self._is_no_op(active, request, inputs, doc_keys)
        
        state_inputs = dict(inputs)
        state_doc_keys = dict(doc_keys)
        if active is not None and partial:
            # 선택하지 않은 원천의 지문도 유지해야 다음 전체·부분 실행에서 삭제 여부를 정확히 판단 가능함.
            old_inputs = dict(active.manifest.get("inputs_sha256", {}))
            old_doc_keys = dict(active.manifest.get("source_doc_keys", {}))
            state_inputs = {
                source: digest
                for source, digest in old_inputs.items()
                if not _selected_source(request, source, str(old_doc_keys.get(source, "")))
            }
            state_doc_keys = {
                source: doc_key
                for source, doc_key in old_doc_keys.items()
                if source in state_inputs
            }
            state_inputs.update(inputs)
            state_doc_keys.update(doc_keys)
        publication = None
        no_op_update: dict[str, Any] = {}
        if no_op and active is not None:
            value = active.manifest.get("publication")
            publication = dict(value) if isinstance(value, dict) else {
                "generation": active.manifest.get("generation"),
                "chunk_count": len(active.chunks),
            }
            no_op_update = {
                "prepared_count": len(active.chunks),
                "expected_count": len(active.chunks),
                "plan": {
                    "desired_ids": [chunk.chunk_id for chunk in active.chunks],
                    "embed_ids": [],
                    "reused_ids": [chunk.chunk_id for chunk in active.chunks],
                    "deleted_ids": [],
                },
            }
        return {
            "sources": source_rows,
            "inputs_sha256": state_inputs,
            "source_doc_keys": state_doc_keys,
            "no_op": no_op,
            "publication": publication,
            "status": "ok",
            "exit_code": 0,
            **no_op_update,
        }

    def _is_no_op(
        self,
        active: IndexSnapshot | None,
        request: Mapping[str, Any],
        inputs: Mapping[str, str],
        doc_keys: Mapping[str, str],
    ) -> bool:
        """선택 범위의 원천과 모든 처리 계약이 활성 세대와 같은지 판정함."""

        if active is None or bool(request.get("full_reindex")):
            return False
        manifest = active.manifest
        if manifest.get("policy_signature") != self.policy_signature:
            return False
        if manifest.get("profile_signature") != self.profile_signature:
            return False
        if manifest.get("embedding_signature") != self.embedder.signature:
            return False
        if dict(manifest.get("embedding_contract") or {}) != self.embedding_contract:
            return False
        old_inputs = dict(manifest.get("inputs_sha256", {}))
        old_doc_keys = dict(manifest.get("source_doc_keys", {}))
        selected_old = {
            source: digest
            for source, digest in old_inputs.items()
            if _selected_source(request, source, str(old_doc_keys.get(source, "")))
        }
        return selected_old == dict(inputs) and all(
            old_doc_keys.get(source) == doc_keys.get(source) for source in inputs
        )

    def load_split_clean(self, state: IndexerState) -> dict[str, Any]:
        """원문을 메모리에서 로드·분할·정제·개인정보 처리한 뒤 안전한 청크만 저장함.

        목적: 개인정보 처리 전 원문이 체크포인트나 중간 파일에 남지 않게 하기 위함.
        인자: state에는 발견 단계가 확정한 원천 목록과 지문이 있어야 함.
        반환값: 정제 완료 청크의 산출물 참조·건수와 실행 상태를 담은 상태 갱신값임.
        예외: 실행 중 원천 변경, 토큰 상한 초과, 청크 ID 중복 시 IndexingError를 발생시킴.
        부수효과: 원천 파일을 읽고 개인정보 처리가 끝난 청크만 외부 산출물 저장소에 기록함.
        """

        request = state["request"]
        partial = str(request.get("doc", "all")) != "all" or request.get("segment") is not None
        current_sources = self.sources.discover(
            str(request["input_path"]),
            str(request.get("doc", "all")),
            request.get("segment"),
        )
        current_inputs = {source.source: source.sha256 for source in current_sources}
        expected_inputs = {
            source: digest
            for source, digest in state["inputs_sha256"].items()
            if _selected_source(
                request,
                source,
                str(state.get("source_doc_keys", {}).get(source, "")),
            )
        }
        if current_inputs != expected_inputs:
            # 발견 뒤 바뀐 파일을 처리하면 체크포인트의 지문과 실제 게시 내용이 달라져 재개가 안전하지 않음.
            raise IndexingError(
                "원천 문서가 실행 시작 후 변경되었습니다. 현재 thread_id를 폐기하고 새 실행을 시작해야 합니다."
            )
        active = self.repository.load_active()
        active_chunks = list(active.chunks) if active else []
        old_inputs = dict(active.manifest.get("inputs_sha256", {})) if active else {}
        policy_unchanged = bool(
            active
            and active.manifest.get("policy_signature") == self.policy_signature
            and active.manifest.get("profile_signature") == self.profile_signature
        )
        selected_sources = [_source_from_dict(row) for row in state["sources"]]
        prepared: list[PreparedChunk] = []

        if active and partial:
            # 부분 실행은 선택 범위만 교체하므로 나머지 활성 청크를 새 세대에 그대로 포함함.
            prepared.extend(
                chunk
                for chunk in active_chunks
                if not _selected_source(
                    request,
                    str(chunk.metadata.get("source", "")),
                    str(chunk.metadata.get("doc_key", "")),
                )
            )

        active_by_source: dict[str, list[PreparedChunk]] = {}
        for chunk in active_chunks:
            active_by_source.setdefault(str(chunk.metadata.get("source", "")), []).append(chunk)

        for source in selected_sources:
            if (
                not bool(request.get("full_reindex"))
                and policy_unchanged
                and old_inputs.get(source.source) == source.sha256
                and source.source in active_by_source
            ):
                # 원천과 정제 계약이 같으면 개인정보 처리 완료 청크를 재사용해 원문 재처리를 피함.
                prepared.extend(active_by_source[source.source])
                continue
            for document in self.loader.load(source):
                policy = self.policies.get(document.doc_key, self.default_policy)
                document_chunks: list[PreparedChunk] = []
                for raw_chunk in self.splitter.split(document, policy):
                    processed_chunk = self.processor.process(raw_chunk)
                    if processed_chunk is None:
                        continue
                    if processed_chunk.token_count > self.token_counter.max_tokens:
                        raise IndexingError(
                            f"임베딩 입력 한도를 초과한 청크입니다: {processed_chunk.chunk_id} "
                            f"({processed_chunk.token_count}>{self.token_counter.max_tokens})"
                        )
                    document_chunks.append(processed_chunk)
                prepared.extend(self._finalize_document_chunks(document_chunks))

        by_id: dict[str, PreparedChunk] = {}
        for chunk in prepared:
            if chunk.chunk_id in by_id:
                raise IndexingError(f"청크 ID가 중복되었습니다: {chunk.chunk_id}")
            by_id[chunk.chunk_id] = chunk
        ordered = [by_id[key] for key in sorted(by_id)]
        reference = self.artifacts.save(
            state["run_id"],
            "prepared-chunks",
            [_chunk_to_dict(chunk) for chunk in ordered],
        )
        return {
            "prepared_chunks_ref": reference,
            "prepared_count": len(ordered),
            "status": "dry_run" if request.get("dry_run") else "ok",
            "exit_code": 0,
        }

    @staticmethod
    def _finalize_document_chunks(chunks: list[PreparedChunk]) -> list[PreparedChunk]:
        """본문 기반 기본 ID에 문서 안의 동일 본문 발생 순번을 붙임."""

        occurrences: dict[str, int] = {}
        result: list[PreparedChunk] = []
        for chunk_index, chunk in enumerate(chunks):
            duplicate_index = occurrences.get(chunk.chunk_id, 0)
            occurrences[chunk.chunk_id] = duplicate_index + 1
            chunk_id = f"{chunk.chunk_id}_{duplicate_index:04d}"
            metadata = {
                **chunk.metadata,
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
            }
            result.append(
                PreparedChunk(
                    chunk_id=chunk_id,
                    text=chunk.text,
                    metadata=metadata,
                    token_count=chunk.token_count,
                    text_hash=chunk.text_hash,
                    metadata_hash=_stable_hash(metadata),
                )
            )
        return result

    def prepare_embed(self, state: IndexerState) -> dict[str, Any]:
        """임베딩 대상을 계획하고 비활성 벡터 저장 세대를 준비함.

        목적: 메타데이터만 바뀐 청크는 새 세대에 갱신하되 같은 본문의 임베딩 비용을 줄이기 위함.
        인자: state에는 정제 청크 참조와 전체·부분 재색인 요청이 있어야 함.
        반환값: 임베딩·재사용·삭제 대상, 벡터 참조, 배치 커서 초기값을 담은 상태 갱신값임.
        예외: 활성 벡터 조회, 중간 산출물 저장, 대상 세대 준비 실패 예외를 호출자에게 전달함.
        부수효과: 활성 벡터를 읽고 재사용 벡터를 기록한 뒤 대상 세대의 벡터 저장소를 준비함.
        """

        desired = self._load_chunks(state)
        active = self.repository.load_active()
        active_by_id = {chunk.chunk_id: chunk for chunk in active.chunks} if active else {}
        active_id_by_text_hash: dict[str, str] = {}
        for active_chunk in active.chunks if active else ():
            active_id_by_text_hash.setdefault(active_chunk.text_hash, active_chunk.chunk_id)
        embedding_compatible = bool(
            active
            and active.manifest.get("embedding_signature") == self.embedder.signature
            and dict(active.manifest.get("embedding_contract") or {}) == self.embedding_contract
        )
        embed_ids: list[str] = []
        reuse_sources: dict[str, str] = {}
        for chunk in desired:
            previous = active_by_id.get(chunk.chunk_id)
            reusable = embedding_compatible and not bool(state["request"].get("full_reindex"))
            if reusable and previous is not None and previous.text_hash == chunk.text_hash:
                reuse_sources[chunk.chunk_id] = previous.chunk_id
            elif reusable and chunk.text_hash in active_id_by_text_hash:
                # 청크 ID가 달라져도 본문이 같으면 기존 벡터의 의미는 같으므로 재사용 가능함.
                reuse_sources[chunk.chunk_id] = active_id_by_text_hash[chunk.text_hash]
            else:
                embed_ids.append(chunk.chunk_id)

        old_ids = list(dict.fromkeys(reuse_sources.values()))
        old_vectors = self.repository.get_vectors(old_ids) if old_ids else {}
        missing = [
            desired_id
            for desired_id, old_id in reuse_sources.items()
            if old_id not in old_vectors
        ]
        if missing:
            embed_ids.extend(missing)
            for chunk_id in missing:
                reuse_sources.pop(chunk_id, None)
        reused_vectors = {
            desired_id: old_vectors[old_id]
            for desired_id, old_id in reuse_sources.items()
        }
        reused_ids = list(reuse_sources)
        vector_refs: list[str] = []
        if reused_vectors:
            vector_refs.append(self.artifacts.save(state["run_id"], "reused-vectors", reused_vectors))

        desired_ids = [chunk.chunk_id for chunk in desired]
        plan = {
            "desired_ids": desired_ids,
            "embed_ids": embed_ids,
            "reused_ids": reused_ids,
            "reuse_sources": reuse_sources,
            "deleted_ids": sorted(set(active_by_id) - set(desired_ids)),
            "text_hashes": {chunk.chunk_id: chunk.text_hash for chunk in desired},
            "metadata_hashes": {chunk.chunk_id: chunk.metadata_hash for chunk in desired},
        }
        # 계획을 먼저 확정해야 대상 세대 준비가 실패해도 같은 입력으로 안전하게 재계산 가능함.
        self.repository.begin(state["target_generation"], self.embedder.signature)
        return {
            "plan": plan,
            "expected_count": len(desired),
            "vector_refs": vector_refs,
            "embed_cursor": 0,
            "upsert_cursor": 0,
            "completed_ids": [],
        }

    def embed(self, state: IndexerState) -> dict[str, Any]:
        """계획의 다음 청크 묶음을 임베딩하고 벡터 참조와 커서를 갱신함.

        인자: state에는 임베딩 대상 ID, 정제 청크 참조, 현재 커서가 있어야 함.
        반환값: 누적 벡터 산출물 참조와 다음 임베딩 커서를 담은 상태 갱신값임.
        예외: 임베딩 결과 수가 입력 수와 다르면 IndexingError를 발생시킴.
        부수효과: 모델 추론을 수행하고 새 벡터 묶음을 외부 산출물 저장소에 기록함.
        """

        chunks = {chunk.chunk_id: chunk for chunk in self._load_chunks(state)}
        ids = list(state["plan"]["embed_ids"])
        cursor = int(state.get("embed_cursor", 0))
        batch_ids = ids[cursor : cursor + self.embed_batch_size]
        if not batch_ids:
            return {"embed_cursor": len(ids)}
        vectors = self.embedder.embed([chunks[chunk_id].text for chunk_id in batch_ids])
        if len(vectors) != len(batch_ids):
            raise IndexingError("임베딩 결과 수가 입력 청크 수와 다릅니다.")
        reference = self.artifacts.save(
            state["run_id"],
            f"vectors-{cursor:08d}",
            dict(zip(batch_ids, vectors, strict=True)),
        )
        return {
            "vector_refs": [*state.get("vector_refs", []), reference],
            "embed_cursor": cursor + len(batch_ids),
        }

    def upsert(self, state: IndexerState) -> dict[str, Any]:
        """최종 청크 순서의 다음 묶음을 대상 색인 세대에 적재함.

        인자: state에는 전체 대상 ID, 모든 벡터 참조, 현재 적재 커서가 있어야 함.
        반환값: 다음 적재 커서와 누적 완료 청크 ID를 담은 상태 갱신값임.
        예외: 필요한 벡터가 없으면 IndexingError를 발생시키고 저장소 쓰기 예외는 그대로 전달함.
        부수효과: 활성 세대와 분리된 대상 세대의 벡터 저장소를 갱신함.
        """

        chunks = {chunk.chunk_id: chunk for chunk in self._load_chunks(state)}
        desired_ids = list(state["plan"]["desired_ids"])
        cursor = int(state.get("upsert_cursor", 0))
        batch_ids = desired_ids[cursor : cursor + self.upsert_batch_size]
        if not batch_ids:
            return {"upsert_cursor": len(desired_ids)}
        vectors = self._load_vectors(state)
        missing = [chunk_id for chunk_id in batch_ids if chunk_id not in vectors]
        if missing:
            raise IndexingError(f"적재할 벡터가 없습니다: {', '.join(missing)}")
        self.repository.upsert(
            state["target_generation"],
            [chunks[chunk_id] for chunk_id in batch_ids],
            [vectors[chunk_id] for chunk_id in batch_ids],
        )
        return {
            "upsert_cursor": cursor + len(batch_ids),
            "completed_ids": [*state.get("completed_ids", []), *batch_ids],
        }

    def build_text_index(self, state: IndexerState) -> dict[str, Any]:
        """키워드 검색용 BM25 색인을 비활성 세대에 준비함.

        인자: state에는 완료 ID, 기대 건수, 처리 계약과 원천 지문이 모두 있어야 함.
        반환값: BM25 산출물의 세대·건수·해시 검증 증거를 담은 상태 갱신값임.
        예외: 완료 건수가 다르거나 저장소가 유효한 검증 증거를 반환하지 않으면 IndexingError를 발생시킴.
        부수효과: 대상 세대에 BM25 산출물과 매니페스트를 쓰지만 활성 세대는 변경하지 않음.
        """

        chunks = self._load_chunks(state)
        expected = int(state["expected_count"])
        if len(state.get("completed_ids", [])) != expected:
            raise IndexingError("완료한 청크 수와 텍스트 색인 예정 청크 수가 다릅니다.")
        manifest = self._build_manifest(state)
        stage = self.repository.build_text_index(state["target_generation"], chunks, manifest)
        required = {"generation", "chunk_count", "manifest_sha256", "corpus_sha256"}
        if not required.issubset(stage):
            raise IndexingError("텍스트 색인 준비 결과에 필수 검증값이 없습니다.")
        if str(stage["generation"]) != state["target_generation"]:
            raise IndexingError("텍스트 색인 준비 세대가 대상 세대와 다릅니다.")
        if int(stage["chunk_count"]) != expected:
            raise IndexingError("텍스트 색인 준비 결과의 청크 수가 예상 건수와 다릅니다.")
        return {"text_index_stage": dict(stage)}

    def publish(self, state: IndexerState) -> dict[str, Any]:
        """준비된 벡터·BM25 색인을 검증한 뒤 활성 세대를 함께 전환함.

        인자: state에는 완료 ID, 기대 건수, 처리 계약과 텍스트 색인 검증 증거가 있어야 함.
        반환값: 게시 경로·세대·청크 수와 성공 상태를 담은 상태 갱신값임.
        예외: 완료 건수, 준비 증거, 게시 결과 건수가 다르면 IndexingError를 발생시킴.
        부수효과: 준비된 두 색인을 검증하고 활성 세대 포인터를 원자적으로 교체함.
        """

        chunks = self._load_chunks(state)
        expected = int(state["expected_count"])
        if len(state.get("completed_ids", [])) != expected:
            raise IndexingError("완료한 청크 수와 게시 예정 청크 수가 다릅니다.")
        stage = state.get("text_index_stage")
        if not isinstance(stage, dict):
            raise IndexingError("게시할 텍스트 색인 준비 결과가 없습니다.")
        manifest = self._build_manifest(state)
        publication = self.repository.publish(
            state["target_generation"],
            chunks,
            manifest,
            stage,
        )
        if publication.chunk_count != expected:
            raise IndexingError("게시 결과의 청크 수가 예상 건수와 다릅니다.")
        return {
            "publication": _publication_to_dict(publication),
            "status": "ok",
            "exit_code": 0,
        }

    def _build_manifest(self, state: IndexerState) -> dict[str, Any]:
        """텍스트 색인 준비와 게시가 공유할 불변 매니페스트를 생성함."""

        expected = int(state["expected_count"])
        return {
            "format_version": 3,
            "generation": state["target_generation"],
            "inputs_sha256": state["inputs_sha256"],
            "source_doc_keys": state["source_doc_keys"],
            "policy_signature": self.policy_signature,
            "profile_signature": self.profile_signature,
            "embedding_tokenizer_signature": self.token_counter.signature,
            "embedding_signature": self.embedder.signature,
            "embedding_contract": self.embedding_contract,
            "chunk_count": expected,
            "text_hashes": state["plan"]["text_hashes"],
            "metadata_hashes": state["plan"]["metadata_hashes"],
        }

    def _load_chunks(self, state: IndexerState) -> list[PreparedChunk]:
        """상태의 산출물 참조에서 개인정보 처리 완료 청크를 복원함."""

        values = self.artifacts.load(state["prepared_chunks_ref"])
        return [_chunk_from_dict(value) for value in values]

    def _load_vectors(self, state: IndexerState) -> dict[str, list[float]]:
        """여러 배치에 나뉜 벡터 산출물을 청크 ID 기준으로 합침."""

        vectors: dict[str, list[float]] = {}
        for reference in state.get("vector_refs", []):
            loaded = self.artifacts.load(reference)
            vectors.update({str(key): list(value) for key, value in loaded.items()})
        return vectors


class IndexingService:
    """표현 계층에 인덱싱 실행과 결과 요약을 제공함.

    실행 제어는 주입받은 PipelineRunnerPort에 맡기며 그래프나 외부 구현체를 직접 만들지 않음.
    """

    def __init__(
        self,
        runner: PipelineRunnerPort,
        *,
        policy_signature: str,
        profile_signature: str,
        embedding_signature: str,
        embedding_dimension: int,
    ) -> None:
        """실행 포트와 요청 지문·결과 요약에 필요한 계약 정보를 주입받음.

        부수효과: 없음. 실제 실행은 run 호출 시 시작됨.
        """

        self.runner = runner
        self.policy_signature = policy_signature
        self.profile_signature = profile_signature
        self.embedding_signature = embedding_signature
        self.embedding_dimension = embedding_dimension

    def run(self, request: IndexRequest) -> IndexResult:
        """인덱싱 파이프라인을 실행하고 표현 계층용 결과로 요약함.

        인자: request는 검증이 끝난 불변 요청이며 thread_id가 비어 있지 않아야 함.
        반환값: 단계별 건수·시간·게시 세대·종료 상태를 담은 IndexResult임.
        예외: 저장된 요청 지문 불일치와 파이프라인 단계 예외를 호출자에게 전달함.
        부수효과: 실행 포트가 체크포인트, 중간 산출물, 색인 세대를 읽거나 변경함.
        """

        started = monotonic()
        
        initial = self.build_initial_state(request) # 초기화된 State 객체 생성  
        
        final = self.runner.run(dict(initial), request.thread_id)   # WORKFLOW 수행 
        timings = dict(final.get("timings", {}))
        timings["total_ms"] = max(0, round((monotonic() - started) * 1000))
        publication = final.get("publication") or {}
        plan = final.get("plan", {})
        failed = list(final.get("failed", []))
        return IndexResult(
            sources=len(final.get("sources", [])),
            extract=ExtractSummary(
                source_count=len(final.get("sources", [])),
                prepared_count=int(final.get("prepared_count", 0)),
            ),
            chunk=ChunkSummary(
                chunk_count=int(final.get("expected_count", final.get("prepared_count", 0))),
                reused_count=len(plan.get("reused_ids", [])),
                embedded_count=len(plan.get("embed_ids", [])),
            ),
            index=IndexSummary(
                collection_count=int(publication.get("chunk_count", final.get("expected_count", 0))),
                newly_embedded=len(plan.get("embed_ids", [])),
                skipped_by_hash=len(plan.get("reused_ids", [])),
                failed=failed,
                embedding_dimension=self.embedding_dimension,
                generation=publication.get("generation"),
            ),
            timings=timings,
            status=final.get("status", "ok"),
            exit_code=int(final.get("exit_code", 0)),
            thread_id=request.thread_id,
            no_op=bool(final.get("no_op", False)),
        )

    def build_initial_state(self, request: IndexRequest) -> IndexerState:
        """요청과 처리 계약을 묶어 재개 검증이 가능한 초기 상태를 만듦.

        인자: request는 Pydantic 검증을 통과한 IndexRequest임.
        반환값: 직렬화 가능한 요청 지문·세대 식별자·빈 진행 상태를 담은 IndexerState임.
        부수효과: 없음.
        """

        request_value = _request_dict(request)  # input_path, output_path, doc(색인대상문서key), full_reindex, thread_id
        fingerprint_payload = {
            "request": request_value,   # 인덱스 요청 파라미터 객체: 
            "workflow_version": WORKFLOW_VERSION,   # Workflow 버전: indexing-workflow-v2
            "policy_signature": self.policy_signature,  # 문서 정책 지문
            "profile_signature": self.profile_signature,    # 문서 프로파일 지문
            "embedding_signature": self.embedding_signature,    # 임베딩 모델 서명값: sentence-transformers:{model_name}:prompt-policy-v2
        }
        safe_thread = re.sub(r"[^A-Za-z0-9_.-]+", "-", request.thread_id).strip("-") or "run"
        generation_suffix = sha256(request.thread_id.encode("utf-8")).hexdigest()[:8]
        return {
            "request": request_value,
            "request_fingerprint": _stable_hash(fingerprint_payload),
            "workflow_version": WORKFLOW_VERSION,
            "run_id": request.thread_id,
            "thread_id": request.thread_id,
            "target_generation": f"gen-{safe_thread}-{generation_suffix}",  #생성할 index 셋대값
            "policy_signature": self.policy_signature,
            "profile_signature": self.profile_signature,
            "embedding_signature": self.embedding_signature,
            "sources": [],
            "inputs_sha256": {},
            "source_doc_keys": {},
            "vector_refs": [],
            "embed_cursor": 0,
            "upsert_cursor": 0,
            "completed_ids": [],
            "text_index_stage": {},
            "failed": [],
            "no_op": False,
            "publication": None,
            "status": "ok",
            "exit_code": 0,
        }

