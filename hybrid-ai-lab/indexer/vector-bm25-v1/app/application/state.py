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
    """8개 노드 사이에 전달되는 Indexer State."""

    input_path: str  # 색인할 원본 파일 또는 폴더 경로
    output_path: str  # 중간 산출물과 색인 결과를 저장할 폴더 경로
    doc: Literal["D1", "D2", "D3", "all"]  # 처리할 문서 종류(D1·D2·D3 또는 전체)
    segment: int | None  # D3에서 처리할 상담 파일 번호, 전체 처리면 None
    embedding_backend: Literal["sentence-transformers", "smoke"]  # 문장을 숫자 벡터로 바꾸는 임베딩 구현 방식
    dry_run: bool  # 청킹까지만 시험하고 벡터 저장을 생략할지 여부
    full_reindex: bool  # 기존 색인을 비우고 처음부터 다시 만들지 여부
    thread_id: str  # 체크포인트·로그·임시 벡터 파일을 묶는 실행 식별자
    profiles: dict[str, Any]  # 원문별로 적용할 메타데이터 프로필
    schema: dict[str, Any]  # 메타데이터 값 검증에 사용할 규칙
    force_fail_node: str | None  # 시험용으로 일부러 실패시킬 노드 이름
    sources: list[str]  # 선택된 원문 파일 경로 목록
    documents: list[Document]  # 원문에서 추출·가명화하고 프로필을 적용한 문서 목록
    reports: Annotated[list[dict], operator.add]  # 파일별 추출 보고서를 누적한 목록
    fingerprints: Annotated[dict[str, str], merge_dict]  # 원문 파일 이름과 해시값을 합친 목록
    validation: dict[str, Any]  # 메타데이터와 개인정보 검증 결과
    warnings: Annotated[list[str], operator.add]  # 처리 중 발생한 경고를 누적한 목록
    chunks: Annotated[list[Document], operator.add]  # 검색용으로 나눈 청크를 누적한 목록
    reviews: Annotated[list[dict], operator.add]  # 수동 검토가 필요한 청크 정보를 누적한 목록
    exceptions: Annotated[list[dict], operator.add]  # 크기 제한 예외가 생긴 청크 정보를 누적한 목록
    skipped: Annotated[list[dict], operator.add]  # 표지·목차처럼 청킹에서 제외한 항목을 누적한 목록
    input_units: int  # 청킹 대상으로 준비한 입력 단위 수
    pending_ids: list[str]  # 임베딩을 마쳐 벡터 저장소에 반영할 청크 ID 목록
    vectors_path: str  # 만든 임베딩 벡터를 저장한 NumPy 파일 경로
    newly_embedded: int  # 이번 실행에서 새로 임베딩한 청크 수
    skipped_by_hash: int  # 내용 해시가 같아 임베딩을 건너뛴 청크 수
    ok_ids: Annotated[list[str], operator.add]  # 벡터 저장에 성공한 청크 ID를 누적한 목록
    failed: Annotated[list[dict], operator.add]  # 임베딩·저장에 실패한 항목을 누적한 목록
    count_before: int  # 저장 전 벡터 저장소의 문서 수
    count_after: int  # 저장 후 벡터 저장소의 문서 수
    accounting_ok: bool  # 예상한 문서 수와 실제 문서 수가 같은지 여부
    embedding_dimension: int  # 생성한 임베딩 벡터 하나의 숫자 개수
    search_index: dict[str, Any] | None  # 검증 후 활성화한 corpus·BM25S 세대 포인터
    llm_calls: Annotated[int, operator.add]  # 노드별 LLM 호출 횟수를 더한 값
    timings: Annotated[dict[str, int], merge_timings]  # 노드별 실행 시간을 누적한 목록
    status: Literal["ok", "dry_run", "error"]  # 전체 실행의 현재 상태
    exit_code: int  # CLI가 반환할 종료 코드


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
    embedding_backend: Literal["sentence-transformers", "smoke"] = "sentence-transformers"


class ExtractSummary(BaseModel):
    document_count: int = 0
    by_doc_type: dict[str, int] = Field(default_factory=dict)
    consultation_mismatch: int = 0


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
    select_sources_ms: int = 0
    extract_ms: int = 0
    apply_profile_ms: int = 0
    validate_metadata_ms: int = 0
    chunk_ms: int = 0
    embed_ms: int = 0
    upsert_ms: int = 0
    finalize_index_ms: int = 0
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
            select_sources_ms=timings.get("select_sources", 0),
            extract_ms=timings.get("extract", 0),
            apply_profile_ms=timings.get("apply_profile", 0),
            validate_metadata_ms=timings.get("validate_metadata", 0),
            chunk_ms=timings.get("chunk", 0),
            embed_ms=timings.get("embed", 0),
            upsert_ms=timings.get("upsert", 0),
            finalize_index_ms=timings.get("finalize_index", 0),
            total_ms=total_ms,
        ),
        status=state.get("status", "ok"),
        exit_code=state.get("exit_code", 0),
        thread_id=state.get("thread_id", ""),
    )
