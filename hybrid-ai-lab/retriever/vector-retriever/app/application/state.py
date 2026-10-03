"""요청 1건의 실행 상태(부록 A 상태 필드)와 단계 노드 이름을 정의함."""

from __future__ import annotations

from typing import Any, TypedDict

from app.domain.models import Candidate, SubQuestion
from app.domain.verification import AnswerSentence

# 그래프 노드 이름 = 단계ID를 소문자·밑줄로 바꾼 값. route 필드에 이 값을 넣어 다음 단계를 고름.
NODE_S_R1, NODE_S_R2, NODE_S_R3 = "s_r1", "s_r2", "s_r3"
NODE_S_R4, NODE_S_R5, NODE_S_R6 = "s_r4", "s_r5", "s_r6"
NODE_S_R7, NODE_S_R8, NODE_S_R9 = "s_r7", "s_r8", "s_r9"
NODE_END = "__end__"
ALL_NODES = (NODE_S_R1, NODE_S_R2, NODE_S_R3, NODE_S_R4, NODE_S_R5, NODE_S_R6, NODE_S_R7, NODE_S_R8, NODE_S_R9)

# 노드별로 갈 수 있는 다음 노드(설계 ① 흐름 유형). 그래프 조립과 시험이 같은 표를 씀.
ROUTES: dict[str, tuple[str, ...]] = {
    NODE_S_R1: (NODE_S_R2, NODE_S_R9),
    NODE_S_R2: (NODE_S_R3, NODE_S_R9),
    NODE_S_R3: (NODE_S_R4, NODE_S_R6, NODE_S_R7, NODE_S_R9),
    NODE_S_R4: (NODE_S_R5, NODE_S_R3),
    NODE_S_R5: (NODE_S_R3, NODE_S_R9),
    NODE_S_R6: (NODE_S_R4, NODE_S_R3, NODE_S_R9),
    NODE_S_R7: (NODE_S_R8, NODE_S_R9),
    NODE_S_R8: (NODE_S_R7, NODE_S_R9),
    NODE_S_R9: (NODE_END,),
}


class EvidenceItem(TypedDict):
    """근거 묶음의 조각 1건. 같은 조각을 여러 하위 질문이 찾아도 한 번만 셈."""

    candidate: Candidate
    qids: list[str]


class RetrieverState(TypedDict, total=False):
    """S-R1 ~ S-R9가 읽고 쓰는 상태. 노드는 바뀐 키만 돌려주고 나머지는 그대로 이어짐.

    체크포인트를 쓰지 않으므로(재개방안 해당없음) 색인 객체 같은 직렬화 불가 값도 담음.
    """

    # 요청·권한(S-R1)
    request_id: str
    started_at: float  # ClockPort.now() 기준 시작 시각
    query: Any  # 원 질문. 검사 전이라 문자열이 아닐 수 있음
    role: str | None
    access_levels: list[str]
    generate_answer: Any
    top_k: Any
    today: str
    generation: str | None
    index: Any  # SearchIndexPort — 요청 동안 고정된 세대
    time_budget_left_s: float
    # 질문 분석(S-R2)
    question_type: str
    sub_questions: list[SubQuestion]
    chitchat_reply: str
    # 근거 수집 반복(L-1, S-R3 ~ S-R6)
    turn: int
    llm_calls: int
    next_action: str  # search·transform·finish
    current_qid: str
    search_queries: list[str]
    search_technique: str  # original·rewrite·multi·hyde·stepback·decomposition
    candidates: list[Candidate]
    vector_top_ids: list[str]
    keyword_top_ids: list[str]
    qid_candidates: dict[str, list[Candidate]]  # 하위 질문별 마지막 검색 결과(C-03 입력용)
    grade: str
    grade_signals: dict[str, dict[str, Any]]  # 하위 질문ID → 판정 근거
    evidence: dict[str, EvidenceItem]  # 조각ID → 근거(삽입 순서 유지)
    evidence_rankings: dict[str, list[str]]  # 하위 질문ID → 근거 조각ID 순위
    transform_history: list[dict[str, Any]]
    search_fail_streak: int
    # 답변·검증 반복(L-2, S-R7 ~ S-R8)
    answer_draft: list[AnswerSentence]
    answer_unresolved: list[str]
    confirmation_note: str
    verify_failures: list[str]
    rewrite_count: int
    clarify_question: str
    # 종료(S-R9)
    status: str
    finish_reason: str
    error_code: str | None
    error_message: str
    route: str  # 다음 노드 이름
    timings: dict[str, float]
    trace: list[dict[str, Any]]
    warnings: list[str]
    response: dict[str, Any]
