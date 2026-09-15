"""Indexer 그래프 State와 CLI 결과가 공유하는 계약."""

import operator
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict, Field


def merge_dict(left: dict, right: dict) -> dict:
    """나중에 들어온 값을 우선하여 사전을 병합함."""

    return {**left, **right}


def merge_timings(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    """루프로 반복된 노드의 실행 시간을 누적함."""

    merged = dict(left)
    for key, value in right.items():
        merged[key] = merged.get(key, 0) + value
    return merged


class IndexerState(TypedDict, total=False):
    """9개 노드 사이에 전달되는 Indexer State."""

    input_path: str
    output_path: str
    doc: Literal["D1", "D2", "D3", "all"]
    segment: int | None
    backend: Literal["sentence-transformers", "smoke"]
    dry_run: bool
    full_reindex: bool
    thread_id: str
    profiles: dict[str, Any]
    schema: dict[str, Any]
    force_fail_node: str | None
    sources: list[str]
    documents: list[Document]
    reports: Annotated[list[dict], operator.add]
    fingerprints: Annotated[dict[str, str], merge_dict]
    pseudonymized: bool
    validation: dict[str, Any]
    warnings: Annotated[list[str], operator.add]
    chunks: Annotated[list[Document], operator.add]
    reviews: Annotated[list[dict], operator.add]
    exceptions: Annotated[list[dict], operator.add]
    skipped: Annotated[list[dict], operator.add]
    input_units: int
    pending_ids: list[str]
    vectors_path: str
    newly_embedded: int
    skipped_by_hash: int
    ok_ids: Annotated[list[str], operator.add]
    failed: Annotated[list[dict], operator.add]
    count_before: int
    count_after: int
    accounting_ok: bool
    embedding_dimension: int
    llm_calls: Annotated[int, operator.add]
    timings: Annotated[dict[str, int], merge_timings]
    status: Literal["ok", "dry_run", "error"]
    exit_code: int


class IndexRequest(BaseModel):
    """CLI 입력을 응용 계층에 전달하는 값 객체."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_path: Path
    output_path: Path
    doc: Literal["D1", "D2", "D3", "all"] = "all"
    segment: int | None = Field(default=None, ge=1, le=6)
    thread_id: str
    full_reindex: bool = False
    dry_run: bool = False
    backend: Literal["sentence-transformers", "smoke"] = "sentence-transformers"


class ExtractSummary(BaseModel):
    document_count: int = 0
    by_doc_type: dict[str, int] = Field(default_factory=dict)
    consultation_mismatch: int = 0
    pseudonymized: bool = False


class ChunkSummary(BaseModel):
    input_units: int = 0
    skipped: int = 0
    chunk_count: int = 0
    review_count: int = 0
    exception_count: int = 0
    by_doc: dict[str, int] = Field(default_factory=dict)


class IndexSummary(BaseModel):
    collection_count: int = 0
    newly_embedded: int = 0
    skipped_by_hash: int = 0
    failed: list[dict] = Field(default_factory=list)
    embedding_dimension: int = 0


class IndexTimings(BaseModel):
    extract_ms: int = 0
    chunk_ms: int = 0
    embed_ms: int = 0
    upsert_ms: int = 0
    total_ms: int = 0


class IndexResult(BaseModel):
    """CLI JSON과 그래프 State가 공유하는 최종 결과."""

    sources: int = 0
    extract: ExtractSummary = Field(default_factory=ExtractSummary)
    chunk: ChunkSummary = Field(default_factory=ChunkSummary)
    index: IndexSummary = Field(default_factory=IndexSummary)
    timings: IndexTimings = Field(default_factory=IndexTimings)
    status: Literal["ok", "dry_run", "error"]
    exit_code: int
    thread_id: str


def build_index_result(state: IndexerState) -> IndexResult:
    """State를 CLI·저장 공통 결과 모델로 변환함."""

    documents = state.get("documents", [])
    chunks = state.get("chunks", [])
    by_doc_type: dict[str, int] = {}
    by_doc: dict[str, int] = {}
    for document in documents:
        doc_type = str(document.metadata.get("doc_type", "unknown"))
        by_doc_type[doc_type] = by_doc_type.get(doc_type, 0) + 1
    for chunk in chunks:
        doc_key = str(chunk.metadata.get("doc_key") or chunk.metadata.get("doc_type", "unknown"))
        by_doc[doc_key] = by_doc.get(doc_key, 0) + 1

    timings = state.get("timings", {})
    total_ms = timings.get("total_ms", sum(value for key, value in timings.items() if key != "total_ms"))
    return IndexResult(
        sources=len(state.get("sources", [])),
        extract=ExtractSummary(
            document_count=len(documents),
            by_doc_type=by_doc_type,
            consultation_mismatch=int(state.get("validation", {}).get("consultation_mismatch", 0)),
            pseudonymized=state.get("pseudonymized", False),
        ),
        chunk=ChunkSummary(
            input_units=state.get("input_units", 0),
            skipped=len(state.get("skipped", [])),
            chunk_count=len(chunks),
            review_count=len(state.get("reviews", [])),
            exception_count=len(state.get("exceptions", [])),
            by_doc=by_doc,
        ),
        index=IndexSummary(
            collection_count=state.get("count_after", 0),
            newly_embedded=state.get("newly_embedded", 0),
            skipped_by_hash=state.get("skipped_by_hash", 0),
            failed=state.get("failed", []),
            embedding_dimension=state.get("embedding_dimension", 0),
        ),
        timings=IndexTimings(
            extract_ms=timings.get("extract", 0),
            chunk_ms=timings.get("chunk", 0),
            embed_ms=timings.get("embed", 0),
            upsert_ms=timings.get("upsert", 0),
            total_ms=total_ms,
        ),
        status=state.get("status", "ok"),
        exit_code=state.get("exit_code", 0),
        thread_id=state.get("thread_id", ""),
    )
