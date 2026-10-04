"""계층 사이를 오가는 요청·응답·오류 모델과 LLM 커넥터 입출력 모델(DTO)을 정의함."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.verification import AnswerSentence

# 응답 상태 6종(부록 B)
STATUS_ANSWERED = "answered"  # 답변 완료 — S-R8 근거 검증 통과
STATUS_RETRIEVED = "retrieved"  # 검색 결과 — 답변 생성 끔 + 근거 있음
STATUS_NO_RETRIEVAL = "no_retrieval"  # 검색 불필요 — 인사·잡담
STATUS_NEEDS_CONFIRMATION = "needs_confirmation"  # 확인 필요 — 근거 0건·clarify·재작성 소진
STATUS_ANSWER_FAILED = "answer_failed"  # 답변 생성 실패 — 근거 목록만
STATUS_ERROR = "error"  # 오류 — 입력·권한·세대 오류, 채점 입력 깨짐

# 오류 코드 → HTTP 상태. 표현 계층이 응답 코드를 고를 때 씀.
ERROR_HTTP_STATUS: dict[str, int] = {
    "invalid_input": 400,  # 질문이 비었거나 500자 초과, 옵션 범위 밖
    "role_missing": 401,  # 로그인 정보(게이트웨이 헤더)에 역할이 없음
    "invalid_role": 403,  # 정의되지 않은 역할
    "index_unavailable": 503,  # 쓸 수 있는 색인 세대가 하나도 없음
    "broken_state": 500,  # 채점 입력이 깨짐 등 흐름 상태 오류
    "internal_error": 500,  # 예상하지 못한 오류
}

MAX_QUERY_CHARS = 500  # 질문 길이 상한(설계 S-R1, 설계 가정)
TOP_K_RANGE = (1, 10)  # 반환 수 허용 범위(설계 S-R1)


class RetrieverError(Exception):
    """계층 공통 오류. 오류 코드·메시지·HTTP 상태를 함께 담음."""

    def __init__(self, code: str, message: str, status_code: int | None = None) -> None:
        """오류 코드에 맞는 HTTP 상태를 기본값으로 채움."""

        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code or ERROR_HTTP_STATUS.get(code, 500)


class IndexUnavailableError(RetrieverError):
    """쓸 수 있는 색인 세대가 하나도 없을 때 발생함(S-R1 → S-R9 오류, 검색 거부)."""

    def __init__(self, message: str) -> None:
        """오류 코드를 index_unavailable로 고정함."""

        super().__init__("index_unavailable", message)


ConnectorErrorKind = Literal["auth", "rate_limit", "timeout", "format", "capacity", "cancelled", "unknown"]


class ConnectorError(Exception):
    """외부 LLM 커넥터 호출 실패. 분류(kind)에 따라 운영 알림 기준이 다름(설계 ③ 오류 분류).

    재시도하지 않음(재시도 0회). 호출한 단계가 각자의 대체 경로로 계속함.
    """

    def __init__(
        self,
        connector_id: str,
        kind: ConnectorErrorKind,
        message: str,
        *,
        status_code: int | None = None,
        elapsed_seconds: float | None = None,
    ) -> None:
        """커넥터ID·분류·HTTP 상태·소요 시간을 담음. 메시지에 API 키·질문 원문을 넣지 않음."""

        super().__init__(message)
        self.connector_id = connector_id
        self.kind = kind
        self.message = message
        self.status_code = status_code
        self.elapsed_seconds = elapsed_seconds


# ---------------------------------------------------------------- 진입 요청·응답(DTO)


class SearchRequest(BaseModel):
    """검색 요청 본문. 역할(role)은 본문이 아니라 서버가 로그인 정보에서 주입함.

    값 범위 검사는 S-R1이 맡아 오류도 표준 응답(status=error)으로 돌려줌. 그래서 여기서는 타입만 받음.
    """

    query: str = Field(description="질문(필수, 500자 이하)")
    generate_answer: bool = Field(default=False, description="답변 생성 여부(기본 끔 — 끄면 근거 목록만 반환)")
    top_k: int = Field(default=5, description="반환 수(1 ~ 10, 기본 5)")
    # 상담 화면에 열려 있는 고객. 주면 상담 이력은 그 회원 것만 검색함(약관 · 혜택은 그대로).
    # 범위를 좁히기만 하므로 본문으로 받아도 권한이 늘지 않음 — 상담 이력 열람 자체는 역할(헤더)이 정함
    member_id: str | None = Field(default=None, description="상담 중인 회원번호(선택, 예: M-1042)")


class CitationOut(BaseModel):
    """답변 문장의 근거 인용."""

    chunk_id: str = Field(description="근거 조각ID(세대가 바뀌면 달라짐 — generation과 함께 읽음)")
    quote: str = Field(description="조각 본문(text)에서 그대로 옮긴 인용문")


class AnswerSentenceOut(BaseModel):
    """검증을 통과한 답변 문장 1개."""

    text: str
    citations: list[CitationOut]


class ScoresOut(BaseModel):
    """근거 조각의 검색 점수. 해당 검색기 후보에 없었으면 null임."""

    vector: float | None = Field(default=None, description="코사인 점수(1 − 거리)")
    bm25: float | None = Field(default=None, description="BM25 원점수")
    fused: float | None = Field(default=None, description="정규화 가중합(벡터 0.6 : BM25 0.4)")
    rerank: float | None = Field(default=None, description="리랭커 점수 0 ~ 1(실패면 null)")


class EvidenceOut(BaseModel):
    """근거 목록의 조각 1건. 출처 정보(설계 ⑥-9)와 본문(text)을 담음."""

    rank: int
    chunk_id: str
    text: str = Field(description="표시·인용 대조용 원래 본문(index_text 아님)")
    source: str
    doc_key: str
    page: int | None = None
    page_end: int | None = None
    clause_no: str | None = None
    card_id: str | None = None
    card_name: str | None = None
    benefit_id: str | None = None
    section_label: str | None = None
    sub_question_ids: list[str] = Field(default_factory=list, description="이 근거를 찾은 하위 질문ID")
    scores: ScoresOut


class UnresolvedOut(BaseModel):
    """확인 못 한 항목 — 어느 질문을 왜 확인하지 못했는지."""

    sub_question_id: str
    question: str
    reason: str


class SearchResponse(BaseModel):
    """결과 응답 1건(S-R9). 화면이 바로 보여 줄 수 있게 상태·답·근거·출처를 한 번에 담음."""

    request_id: str
    status: str = Field(description="answered·retrieved·no_retrieval·needs_confirmation·answer_failed·error")
    message: str = Field(default="", description="잡담 응답문·확인 필요 안내문·오류 안내문")
    answer: list[AnswerSentenceOut] | None = None
    evidence: list[EvidenceOut] = Field(default_factory=list)
    unresolved: list[UnresolvedOut] = Field(default_factory=list)
    clarify_question: str = ""
    question_type: str | None = None
    generation: str | None = Field(default=None, description="이번 요청이 쓴 색인 세대ID")
    llm_calls: int = 0
    timings: dict[str, float] = Field(default_factory=dict, description="단계ID → 소요 시간(초) 합계")
    warnings: list[str] = Field(default_factory=list)
    finish_reason: str = ""
    error_code: str | None = None


# ---------------------------------------------------------------- LLM 커넥터 입출력(C-01 ~ C-04)


@dataclass(frozen=True)
class PlanInput:
    """C-01 질문 분석·계획 입력."""

    user_question: str
    max_sub_questions: int
    today: str | None = None  # 기준일 YYYY-MM-DD(상대 날짜 해석용)


@dataclass(frozen=True)
class PlanOutput:
    """C-01 응답(question_type·sub_questions·chitchat_reply·reason)."""

    question_type: str
    sub_questions: tuple[str, ...]
    chitchat_reply: str
    reason: str


@dataclass(frozen=True)
class ActionInput:
    """C-02 다음 행동 선택 입력."""

    allowed_actions: tuple[str, ...]
    sub_question_states: tuple[dict[str, Any], ...]  # id·question·grade·evidence_count·transform_count
    remaining_turns: int
    original_question: str


@dataclass(frozen=True)
class ActionOutput:
    """C-02 응답(action·target_sub_question_id·reason)."""

    action: str
    target_sub_question_id: str
    reason: str


@dataclass(frozen=True)
class TransformInput:
    """C-03 질문 변환 입력. result_chunks는 권한 통과분 5건 × 1,200자 이내로 잘라 넘김."""

    original_question: str
    target_sub_question: str
    result_chunks: tuple[dict[str, str], ...]  # chunk_id·title·text
    grading_evidence: dict[str, Any]
    previous_attempts: tuple[dict[str, Any], ...]
    technique_guide: tuple[dict[str, str], ...]
    allowed_techniques: tuple[str, ...]


@dataclass(frozen=True)
class TransformOutput:
    """C-03 응답(technique·queries·include_original_query·clarify_question·reason)."""

    technique: str
    queries: tuple[str, ...]
    include_original_query: bool
    clarify_question: str
    reason: str


@dataclass(frozen=True)
class AnswerInput:
    """C-04 답변 생성 입력."""

    original_question: str
    sub_questions: tuple[dict[str, Any], ...]  # id·question·satisfied
    evidence_chunks: tuple[dict[str, str], ...]  # chunk_id·title·text(원래 본문)
    rewrite_reason: str
    attempt_no: int


@dataclass(frozen=True)
class AnswerOutput:
    """C-04 응답(sentences·unresolved_sub_questions·needs_confirmation_note)."""

    sentences: tuple[AnswerSentence, ...]
    unresolved_sub_questions: tuple[str, ...]
    needs_confirmation_note: str


@dataclass(frozen=True)
class IndexLease:
    """S-R1이 이번 요청에 쓸 색인 세대를 받은 결과. 요청이 끝날 때까지 이 세대만 씀."""

    index: Any  # SearchIndexPort 구현체. 순환 import를 피하려고 Any로 둠
    warnings: tuple[str, ...] = field(default_factory=tuple)
