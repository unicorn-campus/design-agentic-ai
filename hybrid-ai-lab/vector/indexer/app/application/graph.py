"""Indexer 9노드 StateGraph 조립과 응용 유스케이스의 경계."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from pathlib import Path
from time import monotonic
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from .runtime import append_node_log, run_with_timeout
from .state import IndexerState, IndexRequest, IndexResult


# --- 그래프 조립(플로니) ---

INDEXER_NODE_NAMES = (
    "select_sources",
    "extract",
    "pseudonymize",
    "apply_profile",
    "validate_metadata",
    "chunk",
    "embed",
    "upsert",
    "verify_count",
)
DEFAULT_RECURSION_LIMIT = 25


class MissingNodeDependencyError(RuntimeError):
    """주입되지 않은 노드 서비스를 호출했음을 나타냄."""


class ForcedNodeError(RuntimeError):
    """체크포인트 재개 시험을 위한 강제 중단임."""


def execution_config(thread_id: str, recursion_limit: int = DEFAULT_RECURSION_LIMIT) -> dict[str, Any]:
    """동결된 thread_id·recursion_limit 실행 설정을 만듦."""

    return {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}


def open_sqlite_checkpointer(path: str | Path) -> SqliteSaver:
    """WAL 모드의 동기 SQLite 체크포인터를 열음."""

    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL")
    return SqliteSaver(connection)


def _lookup(resources: Any, name: str) -> Any:
    if isinstance(resources, Mapping):
        return resources.get(name)
    return getattr(resources, name, None)


def _setting(resources: Any, name: str, default: Any) -> Any:
    settings = _lookup(resources, "settings")
    if settings is None:
        return default
    if isinstance(settings, Mapping):
        return settings.get(name, default)
    values = getattr(settings, "values", None)
    if isinstance(values, Mapping):
        return values.get(name, default)
    return getattr(settings, name, default)


def _handler(resources: Any, node_name: str) -> Callable[[IndexerState], Mapping[str, Any]]:
    run_node = _lookup(resources, "run_node")
    direct = _lookup(resources, node_name)
    if callable(direct):
        return direct
    if callable(run_node):
        return lambda state: run_node(node_name, state)
    raise MissingNodeDependencyError(f"Indexer 노드 서비스가 없음: {node_name}")


def _retryable(resources: Any, node_name: str, exc: Exception) -> bool:
    predicate = _lookup(resources, "is_retryable")
    if callable(predicate):
        return bool(predicate(node_name, exc))
    return exc.__class__.__name__ in {
        "EmbedRetryableError",
        "UpsertRetryableError",
        "VectorStoreRetryableError",
    }


def _run_node(resources: Any, node_name: str, state: IndexerState) -> dict[str, Any]:
    if state.get("force_fail_node") == node_name:
        raise ForcedNodeError(f"강제 중단 노드: {node_name}")
    started = monotonic()
    update = dict(_handler(resources, node_name)(state) or {})
    update.pop("timings", None)
    update["timings"] = {node_name: max(0, round((monotonic() - started) * 1000))}
    return update


def _audited_node(
    resources: Any,
    node_name: str,
    action: Callable[[IndexerState], dict[str, Any]],
) -> Callable[[IndexerState], dict[str, Any]]:
    """노드 완료·실패를 안전한 필드만 담은 JSONL로 기록함."""

    def audited(state: IndexerState) -> dict[str, Any]:
        started = monotonic()
        log_dir = Path(_lookup(resources, "log_dir") or Path(__file__).resolve().parents[2] / "data" / "logs")
        log_path = log_dir / f"{state.get('thread_id', 'unknown')}.jsonl"
        try:
            update = action(state)
        except BaseException as error:
            elapsed = max(0, round((monotonic() - started) * 1000))
            append_node_log(log_path, state.get("thread_id", ""), node_name, "failed", elapsed, type(error).__name__)
            raise
        elapsed = max(0, round((monotonic() - started) * 1000))
        append_node_log(log_path, state.get("thread_id", ""), node_name, "completed", elapsed)
        return update

    return audited


def _select_sources(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: 입력 경로·문서 선택·세그먼트
    # 하는 일: 하위 서비스에서 허용된 원문을 선택하고 0건을 차단함
    # 넘기는 것: sources 또는 정상 END용 error 상태
    update = _run_node(resources, "select_sources", state)
    if not update.get("sources"):
        update.update(status="error", exit_code=1)
    return update


def _extract(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: sources
    # 하는 일: PDF·상담 원문 추출 서비스를 호출함
    # 넘기는 것: documents·reports·fingerprints
    return _run_node(resources, "extract", state)


def _pseudonymize(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: documents
    # 하는 일: 상담 문서의 개인정보 가명화 규칙을 호출함
    # 넘기는 것: 교체된 documents·pseudonymized
    return _run_node(resources, "pseudonymize", state)


def _apply_profile(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: documents·profiles
    # 하는 일: 문서 프로필을 적용하고 금지 키 덮어쓰기를 차단함
    # 넘기는 것: 교체된 documents·warnings
    return _run_node(resources, "apply_profile", state)


def _validate_metadata(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: documents·schema·output_path
    # 하는 일: 메타데이터와 출력 경로를 검증함
    # 넘기는 것: validation·status·exit_code
    update = _run_node(resources, "validate_metadata", state)
    if int(update.get("validation", {}).get("invalid", 0)) > 0:
        update.update(status="error", exit_code=1)
    return update


def _chunk(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: documents·output_path·dry_run
    # 하는 일: 문서를 규칙 단위로 청킹함
    # 넘기는 것: chunks·reviews·exceptions·skipped
    update = _run_node(resources, "chunk", state)
    if state.get("dry_run"):
        update.update(status="dry_run", exit_code=0)
    return update


def _embed(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: chunks·full_reindex·backend
    # 하는 일: 증분 대상만 임베딩하고 벡터를 파일에 저장함
    # 넘기는 것: pending_ids·vectors_path·failed
    return _run_node(resources, "embed", state)


def _upsert(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: pending_ids·vectors_path·chunks
    # 하는 일: 벡터와 메타데이터를 저장소에 upsert함
    # 넘기는 것: ok_ids·failed·count_before
    return _run_node(resources, "upsert", state)


def _verify_count(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: ok_ids·failed·reviews·count_before
    # 하는 일: 저장 건수와 차원을 확인하고 종료 코드를 정함
    # 넘기는 것: count_after·accounting_ok·status·exit_code
    update = _run_node(resources, "verify_count", state)
    failed = [*state.get("failed", []), *update.get("failed", [])]
    reviews = [*state.get("reviews", []), *update.get("reviews", [])]
    if failed:
        update.update(status="ok", exit_code=3)
    elif reviews:
        update.update(status="ok", exit_code=2)
    else:
        update.setdefault("status", "ok")
        update.setdefault("exit_code", 0)
    return update


def _after_validation(state: IndexerState) -> str:
    return "end" if state.get("status") == "error" else "continue"


def _after_chunk(state: IndexerState) -> str:
    return "end" if state.get("status") in {"error", "dry_run"} else "continue"


def create_graph_builder(resources: Any) -> StateGraph:
    """9개 노드와 조건부 종료를 가진 재사용 가능한 빌더를 만듦."""

    builder = StateGraph(IndexerState)
    nodes = {
        "select_sources": _select_sources,
        "extract": _extract,
        "pseudonymize": _pseudonymize,
        "apply_profile": _apply_profile,
        "validate_metadata": _validate_metadata,
        "chunk": _chunk,
        "embed": _embed,
        "upsert": _upsert,
        "verify_count": _verify_count,
    }
    retry_attempts = {"embed": 3, "upsert": 3, "verify_count": 2}
    for name, node in nodes.items():
        retry_policy = None
        if name in retry_attempts:
            retry_policy = RetryPolicy(
                max_attempts=retry_attempts[name],
                retry_on=lambda exc, node_name=name: _retryable(resources, node_name, exc),
            )
        builder.add_node(
            name,
            _audited_node(resources, name, lambda state, node_fn=node: node_fn(resources, state)),
            retry_policy=retry_policy,
        )

    builder.add_edge(START, "select_sources")
    builder.add_conditional_edges("select_sources", _after_validation, {"continue": "extract", "end": END})
    builder.add_edge("extract", "pseudonymize")
    builder.add_edge("pseudonymize", "apply_profile")
    builder.add_edge("apply_profile", "validate_metadata")
    builder.add_conditional_edges("validate_metadata", _after_validation, {"continue": "chunk", "end": END})
    builder.add_conditional_edges("chunk", _after_chunk, {"continue": "embed", "end": END})
    builder.add_edge("embed", "upsert")
    builder.add_edge("upsert", "verify_count")
    builder.add_edge("verify_count", END)
    return builder


def build_graph(resources: Any, checkpointer: SqliteSaver | None = None) -> Any:
    """같은 빌더를 CLI용 SQLite 또는 stream용 None으로 컴파일함."""

    return create_graph_builder(resources).compile(checkpointer=checkpointer)


# --- 응용 함수(스택니) ---
import json
import re
from dataclasses import dataclass, field

from .state import build_index_result


@dataclass
class IndexerResources:
    """Indexer 9개 노드의 실제 처리 구현체 묶음.

    처리 흐름:
        START
          │
          ▼
        [1] select_sources ── 선택 결과 없음 ──────────────▶ END(error)
          │
          ▼
        [2] extract
          │
          ▼
        [3] pseudonymize
          │
          ▼
        [4] apply_profile
          │
          ▼
        [5] validate_metadata ── 유효하지 않은 문서 존재 ─▶ END(error)
          │
          ▼
        [6] chunk ── dry_run 또는 error ──────────────────▶ END
          │
          ▼
        [7] embed
          │
          ▼
        [8] upsert
          │
          ▼
        [9] verify_count
          │
          ▼
        END

    종료 분기와 상태·종료 코드 판정은 각 `_run_*` 구현이 아닌 그래프 래퍼가 담당함.
    """

    settings: Any
    pdf_reader: Any
    file_store: Any
    embedder: Any
    vector_store: Any
    _runs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def run_node(self, name: str, state: IndexerState) -> dict[str, Any]:
        handler = getattr(self, f"_run_{name}")
        return handler(state)

    def _run_select_sources(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: select_sources
        # 목적: 요청 조건에 맞는 인덱싱 원문 파일 선택.
        # 처리: 입력 경로에서 D1·D2 PDF와 D3 상담 파일을 판별하고 문서·세그먼트 조건으로 필터링함.
        source = Path(state["input_path"])
        candidates = [source] if source.is_file() else sorted(source.iterdir())
        selected = []
        segment = state.get("segment")
        for path in candidates:
            if path.is_symlink() or not path.is_file() or "_instructor" in path.parts:
                continue
            is_d1 = path.name.startswith("D1_") and path.suffix.lower() == ".pdf"
            is_d2 = path.name.startswith("D2_") and path.suffix.lower() == ".pdf"
            match = re.fullmatch(r"D3_S(0[1-6])_.*_상담이력_합성\.txt", path.name)
            is_d3 = match is not None
            if state["doc"] == "D1" and not is_d1:
                continue
            if state["doc"] == "D2" and not is_d2:
                continue
            if state["doc"] == "D3" and not is_d3:
                continue
            if state["doc"] == "all" and not (is_d1 or is_d2 or is_d3):
                continue
            if is_d3 and segment is not None and int(match.group(1)) != segment:
                continue
            selected.append(str(path.resolve()))
        return {"sources": selected}

    def _run_extract(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: extract
        # 목적: 선택한 원문을 Document로 변환하고 추적 정보 수집.
        # 처리: 파일 해시를 계산하고 PDF 또는 상담 텍스트를 추출해 documents·reports·fingerprints를 반환함.
        from app.domain.consultations import parse_consultations

        documents, reports, fingerprints = [], [], {}
        for raw_path in state["sources"]:
            path = Path(raw_path)
            fingerprints[path.name] = self.file_store.sha256(path)
            if path.suffix.lower() == ".pdf":
                extracted, report = run_with_timeout(
                    self.pdf_reader.read,
                    path,
                    remove_margins=True,
                    timeout_seconds=float(_setting(self, "TIMEOUT_PDF_PER_FILE", 60)),
                    operation=f"PDF 추출 {path.name}",
                )
                documents.extend(extracted)
                reports.append(report)
            else:
                extracted = parse_consultations(
                    self.file_store.read_text(path),
                    path.name,
                    pseudonymize=True,
                )
                documents.extend(extracted)
                reports.append({"source": path.name, "consultations": len(extracted), "warnings": []})
        return {
            "documents": documents,
            "reports": reports,
            "fingerprints": fingerprints,
        }

    def _run_pseudonymize(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: pseudonymize
        # 목적: 추출된 문서의 개인정보 가명화 보장.
        # 처리: 모든 문서에 가명화 규칙을 적용하고 변경된 documents와 완료 표시를 반환함.
        from app.domain.consultations import pseudonymize_documents

        return {
            "documents": pseudonymize_documents(state["documents"]),
            "pseudonymized": True,
        }

    def _run_apply_profile(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: apply_profile
        # 목적: 원문별 설정 프로필을 문서 메타데이터에 적용.
        # 처리: 문서의 source에 해당하는 프로필을 찾아 각 문서에 적용하고 변경된 documents를 반환함.
        from app.domain.validation import apply_profile

        profiles = state.get("profiles", {})
        documents = [
            apply_profile(document, profiles.get(document.metadata.get("source", ""), {}))
            for document in state["documents"]
        ]
        return {"documents": documents}

    @staticmethod
    def _document_row(document: Any) -> dict[str, Any]:
        return {
            "id": document.id,
            "page_content": document.page_content,
            "metadata": document.metadata,
        }

    def _run_validate_metadata(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: validate_metadata
        # 목적: 출력 경로와 문서 메타데이터 검증 및 중간 산출물 저장.
        # 처리: 경로·메타데이터를 검증하고 문서·manifest·보고서·검증 결과 파일을 저장함.
        from app.domain.validation import validate_documents

        output = Path(state["output_path"])
        self.file_store.ensure_output_outside_input(Path(state["input_path"]), output)
        enums = state.get("schema", {}).get("enums")
        validation = validate_documents(state["documents"], enums)
        self.file_store.save_jsonl(
            output / "documents.jsonl",
            [self._document_row(document) for document in state["documents"]],
        )
        self.file_store.save_json(
            output / "manifest.json",
            {"inputs_sha256": state.get("fingerprints", {}), "document_count": len(state["documents"])},
        )
        self.file_store.save_json(output / "report.json", {"reports": state.get("reports", [])})
        self.file_store.save_json(output / "validation.json", validation)
        return {"validation": validation}

    def _run_chunk(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: chunk
        # 목적: 문서를 검색과 임베딩에 적합한 크기의 청크로 분할.
        # 처리: 입력 단위를 준비·분할하고 ID를 부여한 뒤 청크·검토·예외 보고 파일과 상태값을 반환함.
        from app.domain.chunking import Chunk, assign_storage_ids, chunk_units, prepare_units

        units, skipped = prepare_units(state["documents"])
        collected, reviews = [], []
        for index, unit in enumerate(units):
            chunks, unit_reviews, _unit_exceptions = run_with_timeout(
                chunk_units,
                [unit],
                doc=state["doc"],
                max_chars=int(self.settings.CHUNK_MAX_CHARS),
                overlap=int(self.settings.CHUNK_OVERLAP),
                d2_overlap=int(self.settings.CHUNK_D2_OVERLAP),
                turns_per_chunk=int(self.settings.CHUNK_TURNS_PER_CHUNK),
                overlap_turns=int(self.settings.CHUNK_OVERLAP_TURNS),
                max_tokens=int(self.settings.MAX_INPUT_TOKENS),
                timeout_seconds=float(_setting(self, "TIMEOUT_CHUNK_PER_DOC", 30)),
                operation=f"청킹 입력 단위 {index + 1}",
            )
            reviews.extend(unit_reviews)
            collected.extend(
                Chunk(item.page_content, str(item.id), dict(item.metadata))
                for item in chunks
            )
        counters = {"D1": 0, "D2": 0}
        reassigned = []
        for item in collected:
            key = str(item.metadata.get("doc_key"))
            if key in counters:
                chunk_id = f"{key}_{counters[key]:04d}"
                counters[key] += 1
            else:
                chunk_id = f"D3_{item.metadata['record_id']}_{item.metadata['chunk_index']:04d}"
            reassigned.append(Chunk(item.text, chunk_id, item.metadata))
        chunks = assign_storage_ids(reassigned)
        exceptions = [
            {
                "chunk_id": str(item.id),
                "reason": item.metadata.get("exception_reason"),
            }
            for item in chunks
            if item.metadata.get("size_exception")
        ]
        output = Path(state["output_path"])
        self.file_store.save_jsonl(output / "chunks.jsonl", [self._document_row(item) for item in chunks])
        self.file_store.save_jsonl(output / "review.jsonl", reviews)
        self.file_store.save_jsonl(output / "exceptions.jsonl", exceptions)
        self.file_store.save_json(
            output / "chunk_report.json",
            {
                "input_units": len(units),
                "skipped": len(skipped),
                "chunk_count": len(chunks),
                "review_count": len(reviews),
                "exception_count": len(exceptions),
            },
        )
        return {
            "chunks": chunks,
            "reviews": reviews,
            "exceptions": exceptions,
            "skipped": skipped,
            "input_units": len(units),
        }

    def _run_embed(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: embed
        # 목적: 신규 또는 변경된 청크만 선별해 벡터 생성.
        # 처리: 증분 계획을 세우고 청크를 배치 임베딩한 뒤 벡터 파일과 성공·실패 정보를 저장함.
        import numpy as np

        from app.infrastructure.embedder import plan_incremental

        thread_id = state["thread_id"]
        run = self._runs.setdefault(thread_id, {})
        if state.get("full_reindex", False) and not run.get("reset_done", False):
            # 전체 재적재는 기존 ID가 남지 않도록 임베딩보다 먼저 컬렉션을
            # 비움. 같은 노드가 재시도되어도 성공한 reset은 반복하지 않음.
            self.vector_store.reset()
            run["reset_done"] = True

        output = Path(state["output_path"])
        manifest_path = output / "index_manifest.json"
        manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest_path.exists()
            else None
        )
        chunk_params = {
            "max_chars": int(self.settings.CHUNK_MAX_CHARS),
            "overlap": int(self.settings.CHUNK_OVERLAP),
            "d2_overlap": int(self.settings.CHUNK_D2_OVERLAP),
            "turns_per_chunk": int(self.settings.CHUNK_TURNS_PER_CHUNK),
            "overlap_turns": int(self.settings.CHUNK_OVERLAP_TURNS),
        }
        plan = plan_incremental(
            state["chunks"],
            manifest,
            embedding_signature=self.embedder.signature,
            chunk_params=chunk_params,
            full_reindex=state.get("full_reindex", False),
        )
        by_id = {str(chunk.id): chunk for chunk in state["chunks"]}
        pending, vectors, failed = [], [], []
        batch_size = int(self.settings.EMBED_BATCH_SIZE)
        loader = getattr(self.embedder, "_load", None)
        if plan["pending_ids"] and callable(loader):
            loader()
        for offset in range(0, len(plan["pending_ids"]), batch_size):
            batch_ids = plan["pending_ids"][offset : offset + batch_size]
            texts = [by_id[chunk_id].page_content for chunk_id in batch_ids]
            try:
                batch_vectors = run_with_timeout(
                    self.embedder.embed,
                    texts,
                    kind="passage",
                    timeout_seconds=float(_setting(self, "TIMEOUT_EMBED_BATCH", 120)),
                    operation=f"임베딩 배치 {offset // batch_size + 1}",
                )
            except Exception:
                try:
                    batch_vectors = run_with_timeout(
                        self.embedder.embed,
                        texts,
                        kind="passage",
                        timeout_seconds=float(_setting(self, "TIMEOUT_EMBED_BATCH", 120)),
                        operation=f"임베딩 배치 {offset // batch_size + 1} 재시도",
                    )
                except Exception as error:
                    failed.extend({"chunk_id": chunk_id, "reason": type(error).__name__} for chunk_id in batch_ids)
                    continue
            pending.extend(batch_ids)
            vectors.extend(batch_vectors)
        vector_dir = output / "embeddings"
        vector_dir.mkdir(parents=True, exist_ok=True)
        vectors_path = vector_dir / f"{state['thread_id']}.npy"
        np.save(vectors_path, np.asarray(vectors, dtype=float))
        run.update(
            plan=plan,
            chunk_params=chunk_params,
            pending_ids=pending,
        )
        return {
            "pending_ids": pending,
            "vectors_path": str(vectors_path),
            "newly_embedded": len(pending),
            "skipped_by_hash": len(plan["skipped_ids"]),
            "failed": failed,
        }

    def _run_upsert(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: upsert
        # 목적: 생성된 벡터와 청크 정보를 벡터 저장소에 반영.
        # 처리: 대상 청크를 배치로 upsert하고 성공·실패 ID와 반영 전 건수 및 예상 건수를 기록함.
        import numpy as np

        count_before = self.vector_store.count()
        existing_ids = set(self.vector_store.get_all().get("ids", []))
        pending_ids = state.get("pending_ids", [])
        if not pending_ids:
            return {"ok_ids": [], "failed": [], "count_before": count_before}
        vectors = np.load(state["vectors_path"]).tolist()
        chunks = {str(chunk.id): chunk for chunk in state["chunks"]}
        ok_ids, failed = [], []
        batch_size = int(self.settings.EMBED_BATCH_SIZE)
        for offset in range(0, len(pending_ids), batch_size):
            ids = pending_ids[offset : offset + batch_size]
            batch = [chunks[chunk_id] for chunk_id in ids]
            batch_vectors = vectors[offset : offset + batch_size]
            try:
                run_with_timeout(
                    self.vector_store.upsert,
                    ids,
                    [item.page_content for item in batch],
                    batch_vectors,
                    [item.metadata for item in batch],
                    timeout_seconds=float(_setting(self, "TIMEOUT_EMBED_BATCH", 120)),
                    operation=f"upsert 배치 {offset // batch_size + 1}",
                )
            except Exception:
                try:
                    run_with_timeout(
                        self.vector_store.upsert,
                        ids,
                        [item.page_content for item in batch],
                        batch_vectors,
                        [item.metadata for item in batch],
                        timeout_seconds=float(_setting(self, "TIMEOUT_EMBED_BATCH", 120)),
                        operation=f"upsert 배치 {offset // batch_size + 1} 재시도",
                    )
                except Exception as error:
                    failed.extend({"chunk_id": chunk_id, "reason": type(error).__name__} for chunk_id in ids)
                    continue
            ok_ids.extend(ids)
        self._runs.setdefault(state["thread_id"], {})["expected_count"] = (
            count_before + len(set(ok_ids) - existing_ids)
        )
        return {"ok_ids": ok_ids, "failed": failed, "count_before": count_before}

    def _run_verify_count(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: verify_count
        # 목적: 벡터 저장 결과의 건수와 임베딩 정보를 최종 확인.
        # 처리: 실제·예상 건수를 비교하고 임베딩 정보가 포함된 index_manifest.json을 저장함.
        run = self._runs.get(state["thread_id"], {})
        plan = run.get("plan", {})
        count_after = self.vector_store.count()
        expected = int(run.get("expected_count", state.get("count_before", 0)))
        dimension = int(getattr(self.embedder, "dimension", 0))
        manifest = {
            "format_version": 1,
            "collection": self.settings.CHROMA_COLLECTION,
            "backend": state["backend"],
            "embed_model": self.settings.EMBED_MODEL,
            "embedding_signature": self.embedder.signature,
            "embedding_dimension": dimension,
            "chunk_params": run.get("chunk_params", {}),
            "inputs_sha256": state.get("fingerprints", {}),
            "chunks": plan.get("hashes", {}),
            "counts": {"collection": count_after, "indexed": len(state.get("ok_ids", []))},
        }
        self.file_store.save_json(Path(state["output_path"]) / "index_manifest.json", manifest)
        return {
            "count_after": count_after,
            "accounting_ok": count_after == expected or not state.get("ok_ids"),
            "embedding_dimension": dimension,
        }


def load_resources(
    request: IndexRequest,
    *,
    settings: Any = None,
    pdf_reader: Any = None,
    file_store: Any = None,
    embedder: Any = None,
    vector_store: Any = None,
) -> IndexerResources:
    """기본 구현체를 조립하되 시험에서는 모든 포트를 교체 가능하게 함."""

    from app.infrastructure.chroma_store import create_vector_store
    from app.infrastructure.embedder import create_embedder
    from app.infrastructure.file_store import FileStore
    from app.infrastructure.pdf_reader import PdfReader
    from app.settings import load_settings

    loaded = settings or load_settings()
    actual_embedder = embedder or create_embedder(
        request.backend,
        loaded.EMBED_MODEL,
        batch_size=int(loaded.EMBED_BATCH_SIZE),
    )
    path = Path(loaded.CHROMA_PATH)
    if request.backend == "smoke":
        path = Path(request.output_path) / "chroma_smoke"
    actual_store = vector_store or create_vector_store(
        backend=request.backend,
        path=path,
        collection=loaded.CHROMA_COLLECTION,
        signature=actual_embedder.signature,
    )
    return IndexerResources(
        settings=loaded,
        pdf_reader=pdf_reader or PdfReader(),
        file_store=file_store or FileStore(),
        embedder=actual_embedder,
        vector_store=actual_store,
    )


def _indexer_initial_state(request: IndexRequest, profiles: dict, schema: dict) -> IndexerState:
    return {
        "input_path": str(request.input_path),
        "output_path": str(request.output_path),
        "doc": request.doc,
        "segment": request.segment,
        "backend": request.backend,
        "dry_run": request.dry_run,
        "full_reindex": request.full_reindex,
        "thread_id": request.thread_id,
        "profiles": profiles,
        "schema": schema,
        "force_fail_node": None,
        "llm_calls": 0,
        "status": "ok",
        "exit_code": 0,
    }


def run_indexing(request: IndexRequest, resources: Any = None) -> IndexResult:
    """인덱싱 유스케이스 한 건을 동기 그래프로 실행함."""

    started = monotonic()
    actual = resources or load_resources(request)
    config_dir = Path(__file__).resolve().parents[2] / "config"
    profiles = json.loads((config_dir / "document_profiles.json").read_text(encoding="utf-8"))
    schema = json.loads((config_dir / "metadata_schema.json").read_text(encoding="utf-8"))
    initial = _indexer_initial_state(request, profiles, schema)
    checkpoint = Path(__file__).resolve().parents[2] / "data" / "checkpoints" / "indexer.sqlite"
    saver = open_sqlite_checkpointer(checkpoint)
    try:
        graph = build_graph(actual, saver)
        config = execution_config(request.thread_id, int(actual.settings.RECURSION_LIMIT))
        existing = saver.get_tuple(config)
        final_state = graph.invoke(None if existing else initial, config)
    finally:
        saver.conn.close()
    final_state["timings"] = {
        **final_state.get("timings", {}),
        "total_ms": max(0, round((monotonic() - started) * 1000)),
    }
    return build_index_result(final_state)
