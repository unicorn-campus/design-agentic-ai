"""Retriever CLI·API·그래프가 공유하는 State와 결과 계약."""

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


Mode = Literal["vector", "hybrid", "hybrid_rerank"]
TransformMode = Literal["off", "auto"]
Role = Literal["agent", "auditor"]
Status = Literal[
    "ok",
    "needs_check",
    "halted_by_limit",
    "dry_run",
    "prompt_only",
    "error",
]


def merge_timings(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    """루프로 반복된 노드의 실행 시간을 누적함."""

    merged = dict(left)
    for key, value in right.items():
        merged[key] = merged.get(key, 0) + value
    return merged


class RetrieverRequest(BaseModel):
    """표현 계층에서 응용 계층으로 전달하는 값 객체."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)
    mode: Mode = "hybrid_rerank"
    transform: TransformMode = "off"
    role: Role = "agent"
    thread_id: str
    dry_run: bool = False
    prompt_only: bool = False
    max_llm_calls: int = Field(default=8, ge=1)


class Hit(BaseModel):
    chunk_id: str
    score: float
    vector_score: float | None = None
    rerank_score: float | None = None
    access_level: str
    source: str
    location: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: int
    quote: str


class AnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conclusion: str
    caution: str
    evidence: list[EvidenceDraft]


class Evidence(BaseModel):
    location: str
    quote: str
    quote_verified: bool
    location_verified: bool
    chunk_id: str | None
    source: dict[str, Any]


class Verification(BaseModel):
    automatic_valid: bool
    branch: Literal["needs_check"] | None = None
    schema_errors: list[str] = Field(default_factory=list)
    invalid_refs: list[Any] = Field(default_factory=list)
    quote_failures: list[dict[str, Any]] = Field(default_factory=list)
    location_failures: list[dict[str, Any]] = Field(default_factory=list)
    verified_quote_count: int = 0
    semantic_review_required: bool = False


class Answer(BaseModel):
    conclusion: str
    caution: str
    evidence: list[Evidence]
    sources: list[str]
    verification: Verification


class RouteDecision(BaseModel):
    action: Literal["clarify", "keep", "transform"]
    technique: Literal["rewrite", "multi", "hyde", "stepback", "decomposition"] | None
    queries: list[str]
    reason: str
    clarification: str


class RetrieverState(TypedDict, total=False):
    """11개 노드와 검증 루프 사이에 전달되는 Retriever State."""

    query: str
    role: Role
    mode: Mode
    top_k: int
    dry_run: bool
    prompt_only: bool
    max_llm_calls: int
    thread_id: str
    force_fail_node: str | None
    index_info: dict[str, Any]
    transform_mode: TransformMode
    vector_hits: list[Hit]
    bm25_scores: dict[str, float]
    candidates: list[Hit]
    baseline_hits: list[Hit]
    hits: list[Hit]
    gate_score: float | None
    transform_gate_score: float | None
    route_action: Literal["off", "gate_pass", "keep", "clarify", "transform"]
    technique: str | None
    transformed_queries: list[str]
    transformed_hit_groups: list[list[Hit]]
    merge_weights: dict[str, float]
    coverage_applied: bool
    route_reason: str
    route_error: str
    clarification: str
    transform_cache_hit: bool
    prompt: str
    raw_answer: dict[str, Any]
    answer: dict[str, Any]
    repair_hints: Annotated[list[str], operator.add]
    repair_count: Annotated[int, operator.add]
    warnings: Annotated[list[str], operator.add]
    llm_calls: Annotated[int, operator.add]
    timings: Annotated[dict[str, int], merge_timings]
    status: Status
    exit_code: int


class RouteInfo(BaseModel):
    action: Literal["off", "gate_pass", "keep", "clarify", "transform"]
    technique: str | None = None
    transformed_queries: list[str] = Field(default_factory=list)
    merge_weights: dict[str, float] = Field(default_factory=dict)
    coverage_applied: bool = False
    gate_score: float | None = None
    reason: str = ""
    error: str = ""
    clarification: str = ""
    cache_hit: bool = False


class SearchResult(BaseModel):
    query: str
    mode: Mode
    transform: TransformMode
    role: Role
    top_k: int
    hits: list[Hit] = Field(default_factory=list)
    answer: Answer | None = None
    prompt: str | None = None
    route: RouteInfo
    timings: dict[str, int] = Field(default_factory=dict)
    llm_calls: int = 0
    status: Status
    thread_id: str


class HealthResult(BaseModel):
    status: str
    index_connected: bool
    collection_count: int
    embedding_dimension: int
    llm_provider: str
    models: dict[str, str]


def build_search_result(state: RetrieverState) -> SearchResult:
    """State를 CLI·POST·SSE final 공통 결과 모델로 변환함."""

    answer = state.get("answer")
    return SearchResult(
        query=state.get("query", ""),
        mode=state.get("mode", "hybrid_rerank"),
        transform=state.get("transform_mode", "off"),
        role=state.get("role", "agent"),
        top_k=state.get("top_k", 0),
        hits=[item if isinstance(item, Hit) else Hit.model_validate(item) for item in state.get("hits", [])],
        answer=None if not answer else Answer.model_validate(answer),
        prompt=state.get("prompt") or None,
        route=RouteInfo(
            action=state.get("route_action", "off"),
            technique=state.get("technique"),
            transformed_queries=state.get("transformed_queries", []),
            merge_weights=state.get("merge_weights", {}),
            coverage_applied=state.get("coverage_applied", False),
            gate_score=state.get("gate_score"),
            reason=state.get("route_reason", ""),
            error=state.get("route_error", ""),
            clarification=state.get("clarification", ""),
            cache_hit=state.get("transform_cache_hit", False),
        ),
        timings=state.get("timings", {}),
        llm_calls=state.get("llm_calls", 0),
        status=state.get("status", "ok"),
        thread_id=state.get("thread_id", ""),
    )
