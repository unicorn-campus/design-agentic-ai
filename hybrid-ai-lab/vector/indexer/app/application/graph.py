"""Indexer 8노드 StateGraph 조립과 응용 유스케이스의 경계."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from pathlib import Path
# monotonic()은 시스템 시간이 바뀌어도 뒤로 가지 않아 실행 시간 측정에 사용함.
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
    "apply_profile",
    "validate_metadata",
    "chunk",
    "embed",
    "upsert",
    "finalize_index",
)
DEFAULT_RECURSION_LIMIT = 25


class MissingNodeDependencyError(RuntimeError):
    """주입되지 않은 노드 서비스를 호출했음을 나타냄."""


class ForcedNodeError(RuntimeError):
    """체크포인트 재개 시험을 위한 강제 중단임."""


def execution_config(thread_id: str, recursion_limit: int = DEFAULT_RECURSION_LIMIT) -> dict[str, Any]:
    """동결된 thread_id·recursion_limit 실행 설정을 만듦."""

    return {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}


# SQLite 저널 모드는 데이터를 바꾸는 동안 이전 상태를 어떻게 기록할지 정하는 방식임.
# WAL(Write-Ahead Logging)은 변경 내용을 별도 -wal 파일에 먼저 기록해, 한 번의 쓰기와 여러 읽기를 함께 허용함.
# 다른 모드는 DELETE(기본값, 저널 파일 삭제), TRUNCATE(파일 길이를 0으로 만듦),
# PERSIST(파일은 남기고 무효 표시), MEMORY(메모리에만 보관), OFF(저널을 쓰지 않음)임.
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
    # 받은 것: chunks·full_reindex·embedding_backend
    # 하는 일: 증분 대상만 임베딩하고 벡터를 파일에 저장함
    # 넘기는 것: pending_ids·vectors_path·failed
    return _run_node(resources, "embed", state)


def _upsert(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: pending_ids·vectors_path·chunks
    # 하는 일: 벡터와 메타데이터를 저장소에 upsert함
    # 넘기는 것: ok_ids·failed·count_before
    return _run_node(resources, "upsert", state)


def _finalize_index(resources: Any, state: IndexerState) -> dict[str, Any]:
    # 받은 것: ok_ids·failed·reviews·count_before
    # 하는 일: 저장 건수·임베딩 정보를 검증하고 index_manifest.json을 저장한 뒤 종료 코드를 정함
    # 넘기는 것: count_after·accounting_ok·embedding_dimension·status·exit_code
    update = _run_node(resources, "finalize_index", state)
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
    """8개 노드와 조건부 종료를 가진 재사용 가능한 빌더를 만듦."""

    builder = StateGraph(IndexerState)
    nodes = {
        "select_sources": _select_sources,
        "extract": _extract,
        "apply_profile": _apply_profile,
        "validate_metadata": _validate_metadata,
        "chunk": _chunk,
        "embed": _embed,
        "upsert": _upsert,
        "finalize_index": _finalize_index,
    }
    retry_attempts = {"embed": 3, "upsert": 3, "finalize_index": 2}
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
    builder.add_edge("extract", "apply_profile")
    builder.add_edge("apply_profile", "validate_metadata")
    builder.add_conditional_edges("validate_metadata", _after_validation, {"continue": "chunk", "end": END})
    builder.add_conditional_edges("chunk", _after_chunk, {"continue": "embed", "end": END})
    builder.add_edge("embed", "upsert")
    builder.add_edge("upsert", "finalize_index")
    builder.add_edge("finalize_index", END)
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
    """Indexer 8개 노드의 실제 처리 구현체 묶음.

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
        [3] apply_profile: 원문 파일별 담당 부서·공개 등급 등을 문서 메타데이터에 적용
          │
          ▼
        [4] validate_metadata ── 유효하지 않은 문서 존재 ─▶ END(error)
          │
          ▼
        [5] chunk ── dry_run 또는 error ──────────────────▶ END
          │
          ▼
        [6] embed
          │
          ▼
        [7] upsert
          │
          ▼
        [8] finalize_index
          │
          ▼
        END

    각 노드의 목적:
        1. select_sources: 요청한 문서 종류·구간에 맞는 원본 파일을 선택함.
        2. extract: PDF와 상담 텍스트를 읽어 본문·메타데이터를 가진 Document로 변환함.
        3. apply_profile: 원본별 담당 부서·공개 등급 등의 메타데이터 프로필을 적용함.
        4. validate_metadata: 필수 메타데이터와 가명화 상태를 검사하고 검증 결과를 저장함.
        5. chunk: 문서를 검색에 적합한 크기로 나누고 검토·예외 대상을 기록함.
        6. embed: 변경된 청크만 골라 임베딩 벡터를 생성함.
        7. upsert: 청크 본문·메타데이터·임베딩 벡터를 Chroma에 저장하거나 갱신함.
        8. finalize_index: 저장 건수와 임베딩 정보를 검증하고 index_manifest.json을 저장함.

    종료 분기와 상태·종료 코드 판정은 각 `_run_*` 구현이 아닌 그래프 래퍼가 담당함.
    """

    settings: Any
    pdf_reader: Any
    file_store: Any
    embedder: Any
    vector_store: Any
    _runs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def run_node(self, name: str, state: IndexerState) -> dict[str, Any]:
        # 예: name이 "select_sources"이면 f"_run_{name}"은 "_run_select_sources"라는 함수 이름을 만듦.
        # getattr는 self 안에서 그 이름의 함수를 찾아 handler 변수에 저장함.
        handler = getattr(self, f"_run_{name}")
        # handler(state)는 self._run_select_sources(state)처럼 현재 상태를 함수에 전달해 실행하고 결과를 반환함.
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
                )
                documents.extend(extracted)
                reports.append({"source": path.name, "consultations": len(extracted), "warnings": []})
        return {
            "documents": documents,
            "reports": reports,
            "fingerprints": fingerprints,
        }

    def _run_apply_profile(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: apply_profile
        # 목적: 원문 파일별 담당 부서·공개 등급 등을 문서 메타데이터에 적용.
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

        # 문자열로 받은 출력 경로를 파일·폴더 작업에 쓰는 Path 객체로 바꿈.
        output = Path(state["output_path"])

        # 결과 파일을 쓰기 전에 원문 폴더를 덮어쓰거나, 원문 아래에 결과가 섞이는 일을 막음.
        # ensure_output_outside_input()은 두 경로를 비교해 출력 경로가 원문과 같거나 그 안이면 오류로 중단함.
        self.file_store.ensure_output_outside_input(Path(state["input_path"]), output)

        enums = state.get("schema", {}).get("enums")
        validation = validate_documents(state["documents"], enums)

        # documents.jsonl: 추출·가명화·프로필 적용이 끝난 문서를 확인하거나 재사용하기 위한 파일임.
        #     문서 한 건을 한 줄에 저장하며 각 줄은 id, page_content, metadata로 구성됨.
        # manifest.json: 어떤 원본으로 몇 건의 문서를 만들었는지 추적하고 원본 변경 여부를 확인하기 위한 파일임.
        #     원본 파일별 SHA-256 해시인 inputs_sha256과 전체 문서 수인 document_count로 구성됨.
        # report.json: PDF·상담 파일을 추출하면서 수집한 처리 결과와 경고를 확인하기 위한 파일임.
        #     reports 목록 안에 원본별 페이지·문자·제거 줄·표·상담 건수·경고 등의 추출 보고서가 들어감.
        # validation.json: 문서별 메타데이터와 개인정보 검증의 성공·실패 내용을 확인하기 위한 파일임.
        #     checked·valid·invalid 건수와 문서별 source·errors를 가진 rows 목록으로 구성됨.
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
        """검증을 마친 문서를 검색과 임베딩에 사용할 작은 청크로 만드는 노드임.

        처리 순서:
        1. 문서를 D1 조항, D2 혜택, D3 상담 한 건 단위로 먼저 정리함.
        2. 각 입력 단위를 문서 종류별 규칙과 제한 시간에 따라 여러 청크로 나눔.
        3. 전체 청크에 중복되지 않는 ID를 다시 부여하고 크기 예외를 정리함.
        4. 청크·검토 대상·예외·처리 통계를 파일로 저장함.
        5. 다음 embed 노드가 사용할 청크와 보고 정보를 상태에 반환함.
        """

        # 노드명: chunk
        # 목적: 문서를 검색과 임베딩에 적합한 크기의 청크로 분할.
        # 처리: 입력 단위를 준비·분할하고 ID를 부여한 뒤 청크·검토·예외 보고 파일과 상태값을 반환함.
        from app.domain.chunking import Chunk, assign_storage_ids, chunk_units, prepare_units

        units, skipped = prepare_units(state["documents"])
        collected, reviews = [], []
        for index, unit in enumerate(units):
            chunks, unit_reviews = run_with_timeout(
                chunk_units,  # 제한 시간 안에 실행할 대상 함수
                [unit],  # 현재 입력 단위 1개를 chunk_units의 units 목록으로 전달
                doc=state["doc"],  # 처리할 문서 종류: D1·D2·D3 또는 전체(all)
                max_chars=int(self.settings.CHUNK_MAX_CHARS),  # D1(약관)·D2(혜택) 청크 하나의 최대 글자 수
                overlap=int(self.settings.CHUNK_OVERLAP),  # D1에서 앞 청크 내용을 다음 청크에 겹칠 글자 수
                d2_overlap=int(self.settings.CHUNK_D2_OVERLAP),  # D2에서 겹칠 글자 수
                turns_per_chunk=int(self.settings.CHUNK_TURNS_PER_CHUNK),  # D3(상담) 청크 하나에 넣을 대화 턴 수
                overlap_turns=int(self.settings.CHUNK_OVERLAP_TURNS),  # D3에서 다음 청크에 겹칠 대화 턴 수
                max_tokens=int(self.settings.MAX_INPUT_TOKENS),  # 토큰 계산기를 사용할 때 허용할 최대 토큰 수
                timeout_seconds=float(_setting(self, "TIMEOUT_CHUNK_PER_DOC", 30)),  # 입력 단위 하나의 제한 시간(초)
                operation=f"청킹 입력 단위 {index + 1}",  # 시간 초과·오류 메시지에 표시할 작업 이름
            )
            reviews.extend(unit_reviews)

            # chunk_units가 만든 Chunk 객체를 모으며, 모든 입력 단위의 처리가 끝난 뒤 ID를 한 번만 부여함.
            collected.extend(chunks)

        # 각 청크마다 고유한 청크 ID 부여:
        # 개별 입력 단위 안에서 만든 초기 순번을 저장 직전에 문서별 전체 순번으로 다시 부여함.
        # D1·D2는 입력 단위마다 번호가 0부터 시작하므로 전체 결과에서 ID가 겹치지 않게 연속 번호를 매김.
        # 예: 첫 조항의 D1_0000·D1_0001과 다음 조항의 D1_0000을 D1_0000·D1_0001·D1_0002로 바꿈.
        # D3는 서로 다른 상담의 0000이 충돌하지 않도록 "D3_상담ID_청크번호" 형식에 record_id를 유지함.
        counters = {"D1": 0, "D2": 0}
        reassigned = []
        for item in collected:
            key = str(item.metadata.get("doc_key"))
            if key in counters:  # 약관, 혜택
                chunk_id = f"{key}_{counters[key]:04d}"
                counters[key] += 1
            else: # 상담
                chunk_id = f"D3_{item.metadata['record_id']}_{item.metadata['chunk_index']:04d}"
            reassigned.append(Chunk(item.text, chunk_id, item.metadata))

        # ID 중복과 글자 수를 검사한 뒤 저장에 사용할 Document 객체로 변환함.
        chunks = assign_storage_ids(reassigned)

        # 최종 ID를 사용하여 최대 길이를 초과했지만 저장한 청크의 ID와 사유를 정리함.
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

        # 현재 그래프 실행의 thread_id를 꺼내, 실행별 임시 정보를 구분하는 self._runs의 key로 사용함.
        thread_id = state["thread_id"]

        # setdefault(key, 기본값)는 key가 있으면 기존 값을 그대로 반환하고, 없으면 기본값을 저장한 뒤 반환함.
        # 예: self._runs가 비어 있고 thread_id가 "job-1"이면 {"job-1": {}}를 만들고 그 빈 사전을 run에 넣음.
        # 이미 "job-1"의 실행 정보가 있으면 새 빈 사전으로 덮어쓰지 않고 기존 사전을 run에 넣음.
        run = self._runs.setdefault(thread_id, {})

        # 전체 재색인이면 vector 저장소 clear
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

        # plan_incremental의 목적: 현재 청크 중 새로 임베딩할 것과 건너뛸 것을 결정하는 실행 계획을 만듦.
        # 주요 작업 1: 임베딩 서명·청킹 설정이 바뀌었거나 full_reindex=True이면 전체 청크를 재처리 대상으로 지정함.
        # 주요 작업 2: 설정이 같으면 이전 manifest와 본문·메타데이터 해시를 비교하여 변경된 청크만 골라냄.
        # 반환값은 다음 항목을 담은 딕셔너리임.
        # - pending_ids: 새로 임베딩해야 하는 청크 ID 목록
        # - skipped_ids: 이전과 동일하여 임베딩을 생략할 청크 ID 목록
        # - hashes: 다음 실행의 변경 여부 비교에 사용할 청크별 본문과 메타데이터 해시
        # - full_reindex: 이번 실행이 전체 재임베딩으로 승격되었는지 나타내는 값
        plan = plan_incremental(
            state["chunks"],
            manifest,
            # 임베딩 방식을 구분하는 값임. 기본 KURE-v2는
            # "sentence-transformers:nlpai-lab/KURE-v2:prompt-policy-v2"가 됨.
            # load_resources()가 create_embedder()를 호출할 때 HuggingFaceEmbedder.__init__()에서 설정함.
            embedding_signature=self.embedder.signature,
            chunk_params=chunk_params,
            full_reindex=state.get("full_reindex", False),
        )

        by_id = {str(chunk.id): chunk for chunk in state["chunks"]}
        pending, vectors, failed = [], [], []
        batch_size = int(self.settings.EMBED_BATCH_SIZE)

        # 목적: 새로 임베딩할 청크가 있을 때만 무거운 실모델을 불러와 불필요한 적재 시간과 메모리 사용을 막음.
        # _load가 없는 smoke 임베더이거나 pending_ids가 비어 있으면 모델 적재를 수행하지 않음.
        loader = getattr(self.embedder, "_load", None)  # getattr(): _load 속성이 없으면 기본값 None을 반환함.
        if plan["pending_ids"] and callable(loader):
            # loader는 embedder.py의 HuggingFaceEmbedder._load()를 가리킴.
            # 최초 호출 시 SentenceTransformer 모델을 적재하고 임베딩 차원을 저장하며, 이후에는 적재된 모델을 재사용함.
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

        # 저장하기 전 벡터 저장소의 전체 건수를 구하여 작업 후 건수 검증에 사용함.
        count_before = self.vector_store.count()

        # 기존 청크 ID를 set으로 만들어 새 ID 추가와 기존 ID 갱신을 구분할 때 빠르게 확인함.
        existing_ids = set(self.vector_store.get_all().get("ids", []))

        # embed 노드가 새 벡터를 만든 청크 ID만 이번 저장 대상으로 가져옴.
        pending_ids = state.get("pending_ids", [])

        # 저장할 대상이 없으면 벡터 파일을 읽거나 저장소를 호출하지 않고 현재 건수만 반환함.
        if not pending_ids:
            return {"ok_ids": [], "failed": [], "count_before": count_before}

        # embed 노드가 NumPy의 .npy 형식으로 저장한 벡터 배열을 복원하고 저장소 입력용 파이썬 리스트로 바꿈.
        # np.load를 사용하면 벡터의 배열 구조와 숫자 자료형을 유지하면서 .npy 파일을 효율적으로 읽을 수 있음.
        # numpy는 많은 숫자로 이루어진 벡터 배열을 빠르게 처리하고 .npy 파일로 정확히 저장·복원하는 라이브러리임.
        # np는 numpy를 짧게 부르는 관례적인 별칭임. 예: numpy.load(...) 대신 np.load(...) 사용.
        vectors = np.load(state["vectors_path"]).tolist()

        # 청크 ID로 본문과 메타데이터를 바로 찾을 수 있도록 {청크 ID: Document} 조회표를 만듦.
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

    def _run_finalize_index(self, state: IndexerState) -> dict[str, Any]:
        # 노드명: finalize_index
        # 목적: 벡터 저장 결과를 검증하고 다음 실행에서 사용할 색인 정보를 최종 확정함.
        # 처리: 실제·예상 건수와 임베딩 차원을 확인하고 전체 실행 정보를 index_manifest.json에 저장함.
        run = self._runs.get(state["thread_id"], {})
        plan = run.get("plan", {})

        count_after = self.vector_store.count()
        expected = int(run.get("expected_count", state.get("count_before", 0)))

        dimension = int(getattr(self.embedder, "dimension", 0))

        # 다음 실행에서 증분 색인 여부를 판단하고 현재 색인 구성을 확인할 수 있도록 실행 정보를 저장함.
        # - format_version: 이 manifest 파일 구조의 버전
        # - collection: 벡터를 저장한 Chroma 컬렉션 이름
        # - embedding_backend: 임베딩을 수행한 구현 종류(예: sentence-transformers, smoke)
        # - embed_model: 사용한 임베딩 모델 이름(예: nlpai-lab/KURE-v2)
        # - embedding_signature: 임베딩 구현·모델·프롬프트 정책을 합친 고유 식별값
        # - embedding_dimension: 청크 하나를 변환한 임베딩 벡터의 차원 수
        # - chunk_params: 최대 글자 수, 겹침 범위 등 청킹에 사용한 설정값
        # - inputs_sha256: 원본 파일별 SHA-256으로, 원본 변경 여부를 확인하는 값
        # - chunks: 청크별 본문·메타데이터 해시로, 다시 임베딩할 청크를 판정하는 값
        # - counts: collection은 저장소의 전체 건수, indexed는 이번 실행에서 저장에 성공한 건수
        manifest = {
            "format_version": 1,
            "collection": self.settings.CHROMA_COLLECTION,
            "embedding_backend": state["embedding_backend"],
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
            "accounting_ok": count_after == expected,
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
    """기본 구현체를 조립하되 시험에서는 모든 포트를 교체 가능하게 함.

    반환 자원은 Settings(실행 설정), PdfReader(PDF→문서 변환), FileStore(파일 입출력),
    Embedder(텍스트→숫자 벡터 변환), VectorStore(벡터 저장·조회) 묶음임.
    """

    from app.infrastructure.chroma_store import create_vector_store
    from app.infrastructure.embedder import create_embedder
    from app.infrastructure.file_store import FileStore
    from app.infrastructure.pdf_reader import PdfReader
    from app.settings import load_settings

    loaded = settings or load_settings()
    actual_embedder = embedder or create_embedder(
        request.embedding_backend,
        loaded.EMBED_MODEL,
        batch_size=int(loaded.EMBED_BATCH_SIZE),
    )
    path = Path(loaded.CHROMA_PATH)
    if request.embedding_backend == "smoke":
        path = Path(request.output_path) / "chroma_smoke"
    actual_store = vector_store or create_vector_store(
        embedding_backend=request.embedding_backend,
        path=path,
        collection=loaded.CHROMA_COLLECTION,
        signature=actual_embedder.signature,
    )
    return IndexerResources(
        settings=loaded,  # Settings: 모델·경로·시간 제한 등 실행 설정
        pdf_reader=pdf_reader or PdfReader(),  # PdfReader: PDF를 Document 목록으로 변환
        file_store=file_store or FileStore(),  # FileStore: 원문·JSON·벡터 파일을 읽고 씀
        embedder=actual_embedder,  # SmokeEmbedder/HuggingFaceEmbedder: 텍스트를 숫자 벡터로 변환
        vector_store=actual_store,  # ChromaVectorStore/MemoryVectorStore: 벡터를 저장하고 조회
    )


def _indexer_initial_state(request: IndexRequest, profiles: dict, schema: dict) -> IndexerState:
    return {
        "input_path": str(request.input_path),
        "output_path": str(request.output_path),
        "doc": request.doc,
        "segment": request.segment,
        "embedding_backend": request.embedding_backend,
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

    # 아래에서 실행 자원·설정·체크포인트를 준비하고, 인덱싱 그래프를 실행한 결과를 만듦.
    # monotonic()은 계속 증가하는 초 단위 값임. 예: 시작 100.250, 종료 102.875면 경과 시간은 2.625초임.
    started = monotonic()

    # 호출자가 실행 자원을 주지 않으면, 요청 설정에 맞는 실제 자원을 준비함.
    # 실제 자원은 Settings(설정), PdfReader(PDF 읽기), FileStore(파일 처리),
    # Embedder(텍스트를 숫자 벡터로 변환), VectorStore(벡터 저장·조회) 묶음임.
    actual = resources or load_resources(request)

    # 문서 프로필과 메타데이터 규칙 파일이 있는 설정 폴더를 찾음.
    config_dir = Path(__file__).resolve().parents[2] / "config"
    # 원문 파일별 담당 부서·공개 등급 등의 프로필을 읽음.
    profiles = json.loads((config_dir / "document_profiles.json").read_text(encoding="utf-8"))

    # 메타데이터에 허용되는 값과 필수 항목 규칙을 읽음.
    schema = json.loads((config_dir / "metadata_schema.json").read_text(encoding="utf-8"))

    # 요청·프로필·규칙을 묶어 그래프가 사용할 첫 상태를 만듦.
    initial = _indexer_initial_state(request, profiles, schema)

    # 중단된 실행을 이어 할 수 있도록 SQLite 체크포인트 저장소를 준비함.
    checkpoint = Path(__file__).resolve().parents[2] / "data" / "checkpoints" / "indexer.sqlite"
    saver = open_sqlite_checkpointer(checkpoint)

    # 기존 체크포인트가 있으면 이어서 실행하고, 없으면 처음 상태부터 실행함.
    try:
        # 8개 노드와 SQLite 체크포인트 저장소를 연결한 실행용 그래프를 만듦.
        graph = build_graph(actual, saver)
        # 현재 실행을 구분할 thread_id와 그래프의 최대 반복 횟수 설정을 만듦.
        config = execution_config(request.thread_id, int(actual.settings.RECURSION_LIMIT))
        # 같은 thread_id로 저장된 이전 실행 상태가 있는지 체크포인트에서 찾음.
        existing = saver.get_tuple(config)
        # 이전 상태가 있으면 None으로 재개하고, 없으면 initial 상태로 새 실행을 시작함.
        final_state = graph.invoke(None if existing else initial, config)
    finally:
        saver.conn.close()

    # 모든 노드 시간에 전체 실행 시간을 더해 최종 결과에 기록함.
    final_state["timings"] = {
        **final_state.get("timings", {}),
        "total_ms": max(0, round((monotonic() - started) * 1000)),
    }

    # 그래프 상태를 CLI가 돌려줄 간결한 결과 객체로 바꿈.
    return build_index_result(final_state)
