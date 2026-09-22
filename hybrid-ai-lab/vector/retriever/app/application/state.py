"""Retriever CLI·API·그래프가 공유하는 State와 결과 계약."""

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


Mode = Literal["vector", "vector_rerank", "hybrid", "hybrid_rerank"]
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
    """기존 시간과 새 노드 실행 시간을 노드명별로 누적함.

    Args:
        left: 현재 State에 저장된 노드별 누적 실행 시간임.
        right: 이번 노드 실행이 반환한 노드별 실행 시간임.

    Returns:
        같은 노드명의 시간은 더하고 서로 다른 노드명은 모두 보존한 새 딕셔너리임.
    """

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
    # LLM이 ref·quote 외의 필드를 생성하면 조용히 버리지 않고 검증 오류로 처리하여
    # 인용 근거의 필드명 오타와 예상하지 못한 응답 구조 변경을 즉시 발견함.
    model_config = ConfigDict(extra="forbid")

    ref: int
    quote: str


class AnswerDraft(BaseModel):
    # LLM이 conclusion·caution·evidence 외의 필드를 생성하면 검증 오류로 처리하여
    # 답변 생성 노드와 후속 근거 검증 노드가 합의한 구조화 출력 계약을 엄격히 유지함.
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
    """검색·질문 변환·검증 노드 사이에 전달되는 Retriever State."""

    query: str  # 사용자가 입력한 원본 검색 질문
    role: Role  # 문서 접근 범위를 결정하는 사용자 역할
    mode: Mode  # vector·vector_rerank·hybrid·hybrid_rerank 중 검색 방식
    top_k: int  # 최종 결과로 반환할 최대 문서 수
    dry_run: bool  # 검색 없이 요청과 인덱스 준비 상태만 확인할지 여부
    prompt_only: bool  # 답변 LLM 호출 전 프롬프트 생성까지만 수행할지 여부
    max_llm_calls: int  # 한 요청에서 허용하는 최대 LLM 호출 횟수
    thread_id: str  # 체크포인트·로그·재개 실행을 연결하는 식별자
    force_fail_node: str | None  # 테스트에서 강제로 실패시킬 노드 이름
    index_info: dict[str, Any]  # 컬렉션명·저장 벡터 수·임베딩 차원·서명 확인 결과
    transform_mode: TransformMode  # 질문 변환 사용 안 함(off) 또는 자동 판정(auto)
    vector_hits: list[Hit]  # 원본 질문의 벡터 검색 결과
    keyword_search_scores_by_chunk_id: dict[str, float]  # 원본 질문의 chunk_id별 키워드 검색 점수
    candidates: list[Hit]  # 벡터와 BM25 점수를 합친 리랭킹 전 후보
    baseline_hits: list[Hit]  # 변환 질문 결과와 비교할 원본 질문 기준 결과
    hits: list[Hit]  # 답변 생성이나 최종 반환에 사용할 검색 결과
    answer_gate_vector_score: float | None  # 최종 답변 가능 여부를 판정하는 선두 결과의 벡터 점수
    transform_gate_vector_score: float | None  # 질문 변환 검토 여부를 판정하는 원본 검색 선두 결과의 벡터 점수
    transform_review_required: bool  # 질문 변환 계획을 추가로 검토해야 하는지 여부
    route_action: Literal["off", "gate_pass", "keep", "clarify", "transform"]  # 질문 변환 판정
    technique: str | None  # 선택된 질문 변환 기법
    transformed_queries: list[str]  # 원본 질문에서 생성한 변환 질문 목록
    transformed_hit_groups: list[list[Hit]]  # 변환 질문별 검색 결과 목록
    rerank_failed: bool  # 리랭킹 실패로 변환 질문 검색 결과를 RRF 병합해야 하는지 여부
    merge_weights: dict[str, float]  # 원본·변환 질문 결과 병합에 사용한 가중치
    decomposition_coverage_applied: bool  # 분해 질문별 결과 보장 규칙을 적용했는지 여부
    route_reason: str  # 질문 변환 판정 사유
    route_error: str  # 질문 변환 과정에서 발생한 오류 설명
    clarification: str  # 사용자에게 추가로 확인할 질문
    transform_cache_hit: bool  # 질문 변환 결과를 캐시에서 찾았는지 여부
    system_prompt: str  # 답변 LLM의 역할·처리·출력·제약조건을 8대 섹션으로 정의한 시스템 프롬프트
    user_prompt: str  # 검색 근거·질문·수정 지침을 XML 입력으로 조립해 LLM에 전달할 사용자 프롬프트
    prompt: str  # 기존 API 응답 호환을 위해 user_prompt와 같은 값을 보관하는 공개 프롬프트
    raw_answer: dict[str, Any]  # LLM이 생성한 현재 검증 전 구조화 답변
    answer: dict[str, Any]  # 인용·위치 검증 결과를 포함한 구조화 답변
    repair_hints: Annotated[list[str], operator.add]  # 답변 재생성에 사용할 수정 지침
    """검증 루프마다 생긴 수정 지침을 잃지 않도록 새 목록을 기존 목록 뒤에 이어 붙임."""
    repair_count: Annotated[int, operator.add]  # 답변 검증에 실패한 누적 횟수
    """검증 실패마다 반환한 1을 기존 값에 더해 수정 루프 상한을 판단하고 무한 반복을 막음."""
    warnings: Annotated[list[str], operator.add]  # 여러 검색 단계에서 발생한 경고 목록
    """앞 단계의 경고를 보존하도록 각 노드가 새로 반환한 경고 목록을 이어 붙임."""
    llm_calls: Annotated[int, operator.add]  # 요청에서 실제로 사용한 LLM 호출 횟수
    """질문 변환·답변 생성 노드가 반환한 이번 호출 증가분을 더해 요청 예산을 계산함."""
    timings: Annotated[dict[str, int], merge_timings]  # 노드별 누적 실행 시간(ms)
    """반복 실행된 같은 노드의 시간도 보존하도록 키별 밀리초를 더해 합침."""
    """누적 필드 병합 원리.

    노드는 State 전체가 아니라 변경할 key만 dict로 반환하며, 반환하지 않은 key의 기존 값은 유지됨.
    `Annotated[T, reducer]`는 원래 자료형 `T`에 LangGraph 병합 함수 `reducer`를 붙이는 표시임.
    `operator.add`는 list를 이어 붙이고 int를 더함. `merge_timings(left, right)`에서 `left`는
    State의 기존 누적 시간이고 `right`는 이번 노드가 반환한 시간임. 같은 노드명의 시간은 더하고
    한쪽에만 있는 노드명은 그대로 보존함.

    일반 필드는 순차 실행에서 새 값으로 교체됨. 같은 실행 단계의 병렬 노드가 같은 일반 key를
    동시에 반환하면 마지막 값을 고르는 대신 충돌 오류가 발생할 수 있음. `repair_count`와
    `llm_calls`에는 누적 총합이 아니라 이번 노드의 증가분만 반환해야 이중 합산되지 않음.
    """
    status: Status  # 현재 실행 결과 상태
    exit_code: int  # 그래프가 기록하는 숫자형 종료 상태로 오류는 1, 그 외는 0


class RouteInfo(BaseModel):
    action: Literal["off", "gate_pass", "keep", "clarify", "transform"]
    technique: str | None = None
    transformed_queries: list[str] = Field(default_factory=list)
    merge_weights: dict[str, float] = Field(default_factory=dict)
    decomposition_coverage_applied: bool = False
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
            decomposition_coverage_applied=state.get("decomposition_coverage_applied", False),
            # 공개 API의 gate_score 이름은 기존 클라이언트 호환을 위해 유지함.
            gate_score=state.get("answer_gate_vector_score"),
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
