"""LangGraph 워크플로우 시나리오 시험임. 설계서 ① 분기·④ 상한·⑥-10 시간 예산이 그대로 도는지 확인함.

실제 RetrieverSteps + LangGraphWorkflow + RetrieverService를 쓰고 기술만 가짜 포트로 바꿈.
기대값은 모두 설계서 기준임 — 구현이 다르면 시험을 고치지 않고 시험이 실패하게 둠.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import pytest

from app.application.models import (
    STATUS_ANSWER_FAILED,
    STATUS_ANSWERED,
    STATUS_ERROR,
    STATUS_NEEDS_CONFIRMATION,
    STATUS_NO_RETRIEVAL,
    STATUS_RETRIEVED,
    ActionOutput,
    AnswerOutput,
    IndexUnavailableError,
    PlanOutput,
    SearchRequest,
    SearchResponse,
    TransformOutput,
)
from app.application.services import RetrieverService
from app.application.state import ALL_NODES, NODE_END, NODE_S_R3, NODE_S_R5, NODE_S_R6, NODE_S_R7, NODE_S_R8, ROUTES
from app.application.steps import RetrieverSteps, StepConfig
from app.domain.actions import ACTION_FINISH, ACTION_SEARCH, ACTION_TRANSFORM
from app.domain.budget import C_01, C_02, C_03, C_04, BudgetPolicy
from app.domain.models import QTYPE_CHITCHAT, QTYPE_COMPLEX, QTYPE_SIMPLE
from app.domain.transform_rules import CLARIFY
from app.domain.verification import AnswerSentence, Citation
from app.infrastructure.graph import DEFAULT_RECURSION_LIMIT, LangGraphWorkflow

from tests.fakes import (
    FakeAuditLog,
    FakeClock,
    FakeIndex,
    FakeIndexProvider,
    FakeLLM,
    FakeReranker,
    connector_error,
    make_corpus,
)

Q_FEE = "연회비 면제 조건"
Q_SKY = "스카이카드 마일리지"
Q_SHOP = "쇼핑카드 할인"
Q_MIXED = "스카이카드 마일리지 와 쇼핑카드 할인"

# 워크플로우 시험은 설계서 계산 예(총 30초, C-03 1.2초)로 시간 예산 착지를 검증함(운영 기본값과 같음)
DESIGN_BUDGET = BudgetPolicy(total_seconds=30.0, connector_worst_seconds={C_01: 2.5, C_02: 1.5, C_03: 1.2, C_04: 2.5})


# ---------------------------------------------------------------- 조립 도우미


@dataclass
class Harness:
    """시험 1건이 쓰는 조립 결과임. 가짜 포트를 그대로 들고 있어 호출 기록을 바로 확인함."""

    service: RetrieverService
    steps: RetrieverSteps
    workflow: LangGraphWorkflow
    index: FakeIndex
    provider: FakeIndexProvider
    reranker: FakeReranker
    llm: FakeLLM
    audit: FakeAuditLog
    clock: FakeClock


def build(
    *,
    index: FakeIndex | None = None,
    reranker: FakeReranker | None = None,
    llm: FakeLLM | None = None,
    provider: FakeIndexProvider | None = None,
    clock: FakeClock | None = None,
    config: StepConfig | None = None,
) -> Harness:
    """단계·그래프·서비스를 가짜 포트로 조립함. bootstrap.py와 같은 순서로 묶되 기술만 대역으로 바꿈."""

    clock = clock or FakeClock()
    corpus = make_corpus()
    index = index if index is not None else FakeIndex(corpus=corpus)
    index.clock = index.clock or clock
    reranker = reranker or FakeReranker(corpus=corpus)
    llm = llm or FakeLLM()
    llm.clock = llm.clock or clock
    provider = provider if provider is not None else FakeIndexProvider(index=index)
    provider.clock = provider.clock or clock
    audit = FakeAuditLog()
    steps = RetrieverSteps(index_provider=provider, reranker=reranker, llm=llm, audit_log=audit,
                           clock=clock, config=config or StepConfig(budget=DESIGN_BUDGET))
    workflow = LangGraphWorkflow(steps)
    service = RetrieverService(workflow=workflow, index_provider=provider, clock=clock, audit_log=audit)
    return Harness(service, steps, workflow, index, provider, reranker, llm, audit, clock)


def run(h: Harness, query: str, *, role: str | None = "agent", generate_answer: bool = False,
        top_k: int = 5) -> SearchResponse:
    """요청 1건을 실행함. 예상하지 못한 내부 오류는 감사 로그를 보여 주며 바로 실패시킴."""

    response = h.service.execute(
        SearchRequest(query=query, generate_answer=generate_answer, top_k=top_k), role
    )
    if response.error_code == "internal_error":
        raise AssertionError(f"예상하지 못한 내부 오류: {h.audit.of_type('internal_error')}")
    return response


def last_request_log(h: Harness) -> dict[str, Any]:
    """마지막 요청 감사 레코드를 반환함."""

    records = h.audit.of_type("request")
    assert records, "요청 감사 레코드가 없음"
    return dict(records[-1])


def trace_of(log: dict[str, Any], step_id: str) -> list[dict[str, Any]]:
    """감사 레코드의 행동 기록에서 단계ID가 맞는 항목만 고름."""

    return [entry for entry in log["trace"] if entry.get("step") == step_id]


def simple_correct() -> Harness:
    """단순 질문 1건이 '정확' 판정을 받는 기본 조립임(여러 시험이 출발점으로 씀)."""

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_FEE: [("d1c1", 0.9), ("d2a1", 0.4)]})
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.92, "d2a1": 0.3})
    llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색")])
    return build(index=index, reranker=reranker, llm=llm)


# ---------------------------------------------------------------- 분기표 자체 점검


def test_분기표가_모든_단계를_덮고_되돌아가는_선_3곳을_가짐() -> None:
    """설계 ① 흐름 유형 표와 ROUTES가 어긋나면 그래프 조립이 틀어지므로 표부터 확인함."""

    assert set(ROUTES) == set(ALL_NODES)
    known = set(ALL_NODES) | {NODE_END}
    for node, targets in ROUTES.items():
        assert targets, f"{node}에 다음 노드가 없음"
        assert set(targets) <= known, f"{node}의 다음 노드가 표 밖임: {targets}"
    # 설계 ④: 되돌아가는 선 3곳(S-R5 → S-R3 · S-R6 keep → S-R3 · S-R8 → S-R7)
    assert NODE_S_R3 in ROUTES[NODE_S_R5]
    assert NODE_S_R3 in ROUTES[NODE_S_R6]
    assert NODE_S_R7 in ROUTES[NODE_S_R8]
    assert DEFAULT_RECURSION_LIMIT >= 34  # 최장 경로 34걸음(graph.py 계산 근거)


def test_걸음_수_상한을_넘으면_RuntimeError로_바꿔_올림() -> None:
    """포트 계약: 비정상 반복은 LangGraph 예외가 아니라 RuntimeError로 올림(호출자가 엔진을 몰라도 되게 함)."""

    h = simple_correct()
    too_low = LangGraphWorkflow(h.steps, recursion_limit=2)  # 정상 경로도 못 끝낼 상한
    with pytest.raises(RuntimeError, match="걸음 수"):
        too_low.run(h.service.initial_state(SearchRequest(query=Q_FEE), "agent"))


def test_분기표_밖_다음_노드를_내놓으면_실행이_바로_실패함() -> None:
    """path map을 ROUTES로 좁힌 이유를 확인함 — 설계 표와 코드가 어긋나면 조용히 흐르지 않고 터짐.

    단계 로직을 고치지 않고 시험에서만 핸들러를 바꿔 '표 밖 route'를 흉내 냄(그래프 조립은 그 뒤에 함).
    """

    h = simple_correct()
    original = h.steps.s_r1
    h.steps._handlers["s_r1"] = lambda state: {**original(state), "route": NODE_S_R7}
    workflow = LangGraphWorkflow(h.steps)
    with pytest.raises((KeyError, ValueError)):
        workflow.run(h.service.initial_state(SearchRequest(query=Q_FEE), "agent"))


# ---------------------------------------------------------------- ① S-R1 오류


def test_01_입력_역할_색인_오류를_코드별로_구분함() -> None:
    """설계 부록 B: S-R1 입력·권한·세대 오류는 모두 status=error이며 오류 코드로만 구분함."""

    h = build()
    for bad_query in ("", "   ", "가" * 501):
        response = run(h, bad_query)
        assert (response.status, response.error_code) == (STATUS_ERROR, "invalid_input")
    for bad_top_k in (0, 11):
        response = run(h, Q_FEE, top_k=bad_top_k)
        assert (response.status, response.error_code) == (STATUS_ERROR, "invalid_input")

    response = run(h, Q_FEE, role=None)
    assert (response.status, response.error_code) == (STATUS_ERROR, "role_missing")
    response = run(h, Q_FEE, role="stranger")
    assert (response.status, response.error_code) == (STATUS_ERROR, "invalid_role")

    # 거른 요청은 검색도 LLM도 쓰지 않음
    assert h.index.vector_queries == [] and h.llm.calls == []

    broken = build(provider=FakeIndexProvider(index=None, error=IndexUnavailableError("쓸 수 있는 세대 없음")))
    response = run(broken, Q_FEE)
    assert (response.status, response.error_code) == (STATUS_ERROR, "index_unavailable")
    assert response.evidence == [] and broken.llm.calls == []


# ---------------------------------------------------------------- ② 잡담


def test_02_잡담은_검색_없이_no_retrieval로_끝남() -> None:
    """설계 B-1: 인사·잡담은 검색 비용을 쓰지 않고 S-R2에서 바로 S-R9로 감."""

    llm = FakeLLM(plan=[PlanOutput(QTYPE_CHITCHAT, (), "안녕하세요. 무엇을 찾아 드릴까요?", "인사")])
    h = build(llm=llm)
    response = run(h, "안녕하세요 반갑습니다")

    assert response.status == STATUS_NO_RETRIEVAL
    assert response.message == "안녕하세요. 무엇을 찾아 드릴까요?"
    assert response.evidence == [] and response.unresolved == []
    assert h.index.vector_queries == [] and h.index.keyword_queries == []
    assert h.llm.calls == [C_01] and response.llm_calls == 1


# ---------------------------------------------------------------- ③ 단순 + 정확 + 답변 끔


def test_03_단순_정확_답변끔은_retrieved로_끝남() -> None:
    """설계 B-2a: 답변 생성을 끄면 근거 목록만 돌려주고 C-04는 부르지 않음."""

    h = simple_correct()
    response = run(h, Q_FEE)

    assert response.status == STATUS_RETRIEVED
    assert response.answer is None
    assert [item.chunk_id for item in response.evidence] == ["d1c1", "d2a1"]
    assert response.evidence[0].scores.rerank == 0.92
    assert response.evidence[0].clause_no == "제5조"
    assert h.llm.calls == [C_01, C_02]  # 2회전은 고를 행동이 수집 종료뿐이라 C-02를 부르지 않음
    assert C_04 not in h.llm.calls
    log = last_request_log(h)
    assert log["turns"] == 2
    assert trace_of(log, "S-R5")[0]["grade"] == "correct"


# ---------------------------------------------------------------- ④ 복합(하위 질문 2개)


def test_04_복합질문은_원_질문을_검색하지_않고_근거를_RRF로_합침() -> None:
    """설계 ④·S-R9 ②: 분해 시 하위 질문만 검색하고, 질문별 순위를 RRF로 합쳐 근거를 정렬함."""

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={
        Q_SKY: [("d2a1", 0.9), ("d1c1", 0.4)],
        Q_SHOP: [("d2b1", 0.9), ("d1c1", 0.4)],
    })
    reranker = FakeReranker(corpus=corpus, scores={"d2a1": 0.92, "d2b1": 0.91, "d1c1": 0.5})
    llm = FakeLLM(
        plan=[PlanOutput(QTYPE_COMPLEX, (Q_SKY, Q_SHOP), "", "두 카드를 함께 물음")],
        action=[ActionOutput(ACTION_SEARCH, "q1", "q1 검색"), ActionOutput(ACTION_SEARCH, "q2", "q2 검색")],
    )
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, Q_MIXED)

    assert response.status == STATUS_RETRIEVED
    assert response.question_type == QTYPE_COMPLEX
    # 원 질문은 답변·기록용으로만 보관하고 검색하지 않음
    assert h.index.vector_queries == [Q_SKY, Q_SHOP]
    assert Q_MIXED not in h.index.keyword_queries
    # RRF: d1c1은 두 질문에서 2위(2/62) → 1위. d2a1·d2b1은 1/61 동점이라 조각ID 오름차순
    assert [item.chunk_id for item in response.evidence] == ["d1c1", "d2a1", "d2b1"]
    found_by = {item.chunk_id: set(item.sub_question_ids) for item in response.evidence}
    assert found_by["d1c1"] == {"q1", "q2"}
    assert found_by["d2a1"] == {"q1"} and found_by["d2b1"] == {"q2"}
    assert response.unresolved == []


# ---------------------------------------------------------------- ⑤ 불확실 → 변환 → 정확


def test_05_불확실하면_C03_변환으로_재검색해_정확까지_감() -> None:
    """설계 B-3·L-1: 불확실은 변환 1회 기회를 쓰고, 재검색이 정확이면 근거로 들어감."""

    rewritten = "연회비 면제 기준 실적"
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={
        Q_FEE: [("d1c1", 0.9), ("d2a1", 0.4)],
        rewritten: [("d1c1", 0.95)],
    })
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.5, "d2a1": 0.3},
                            by_query={rewritten: {"d1c1": 0.95}})
    llm = FakeLLM(
        action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색"),
                ActionOutput(ACTION_TRANSFORM, "q0", "핵심어 보강 필요")],
        transform=[TransformOutput("rewrite", (rewritten,), False, "", "점수 상한 미달")],
    )
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, Q_FEE)

    assert response.status == STATUS_RETRIEVED
    assert [item.chunk_id for item in response.evidence] == ["d1c1"]
    assert h.index.vector_queries == [Q_FEE, rewritten]
    assert h.llm.calls == [C_01, C_02, C_02, C_03]
    log = last_request_log(h)
    grades = [entry["grade"] for entry in trace_of(log, "S-R5")]
    assert grades == ["uncertain", "correct"]
    assert log["transform_history"][0]["technique"] == "rewrite"


# ---------------------------------------------------------------- ⑥ 변환 후에도 불확실


def test_06_변환_후에도_불확실하면_근거_부족으로_끝남() -> None:
    """설계 ⑥-1 사용자 결정: 재검색 후 불확실은 LLM 판정을 더하지 않고 근거 부족으로 끝냄."""

    rewritten = "연회비 면제 기준 실적"
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_FEE: [("d1c1", 0.9)], rewritten: [("d1c1", 0.9)]})
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.5})
    llm = FakeLLM(
        action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색"),
                ActionOutput(ACTION_TRANSFORM, "q0", "핵심어 보강 필요")],
        transform=[TransformOutput("rewrite", (rewritten,), False, "", "점수 상한 미달")],
    )
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, Q_FEE)

    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert response.evidence == []
    assert len(response.unresolved) == 1
    assert "질문 변환 후에도 불확실" in response.unresolved[0].reason
    log = last_request_log(h)
    assert [entry["grade"] for entry in trace_of(log, "S-R5")] == ["uncertain", "uncertain"]
    # 변환은 하위 질문 1개당 1회 — C-03은 한 번만 불림
    assert h.llm.count(C_03) == 1


# ---------------------------------------------------------------- ⑦ C-03 clarify


def test_07_C03_clarify는_확인_질문과_함께_needs_confirmation으로_끝남() -> None:
    """설계 B-3: 다듬어도 대상이 불분명하면 사용자에게 되묻고 S-R9로 감."""

    question = "스카이카드 연회비 면제 조건"
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={question: [("d2a1", 0.9)]})
    reranker = FakeReranker(corpus=corpus, scores={"d2a1": 0.5})
    llm = FakeLLM(
        action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색"),
                ActionOutput(ACTION_TRANSFORM, "q0", "대상 불명")],
        transform=[TransformOutput(CLARIFY, (), False, "연회비 면제 기준을 어느 해로 보시나요?", "대상 불명")],
    )
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, question)

    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert response.clarify_question == "연회비 면제 기준을 어느 해로 보시나요?"
    assert response.message == "질문 대상을 확인할 수 없어 되묻습니다."
    assert h.llm.count(C_03) == 1


# ---------------------------------------------------------------- ⑧ 대상명 없음 + 카드 섞임


def test_08_대상명_없고_카드가_섞이면_C03_없이_clarify로_끝남() -> None:
    """설계 ⑥-3 서버 규칙: '대상명 없음 + 대상 섞임'은 LLM을 부르지 않고 바로 되물음."""

    question = "마일리지 할인"
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={question: [("d2a1", 0.9), ("d2b1", 0.6)]})
    reranker = FakeReranker(corpus=corpus, scores={"d2a1": 0.5, "d2b1": 0.45})
    llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색"),
                          ActionOutput(ACTION_TRANSFORM, "q0", "대상 불명")])
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, question)

    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert C_03 not in h.llm.calls  # 규칙이 먼저 판정하므로 커넥터 호출을 절약함
    assert "스카이카드" in response.clarify_question and "쇼핑카드" in response.clarify_question


# ---------------------------------------------------------------- ⑨ 답변 켬 + 검증 통과


def test_09_답변_켬_검증_통과는_answered로_끝남() -> None:
    """설계 B-4: 인용이 근거 본문(text)과 글자 그대로 맞으면 답변 완료임."""

    h = simple_correct()
    h.llm._scripts[C_04] = [AnswerOutput(
        (AnswerSentence("연회비는 전년도 실적 300만원 이상이면 면제됩니다.",
                        (Citation("d1c1", "전년도 실적 300만원 이상"),)),),
        (), "",
    )]
    response = run(h, Q_FEE, generate_answer=True)

    assert response.status == STATUS_ANSWERED
    assert response.answer is not None and len(response.answer) == 1
    assert response.answer[0].citations[0].chunk_id == "d1c1"
    assert response.unresolved == []
    assert h.llm.calls == [C_01, C_02, C_04]
    log = last_request_log(h)
    assert trace_of(log, "S-R8")[0]["passed"] is True


# ---------------------------------------------------------------- ⑩ 인용 불일치 → 재작성 소진


def test_10_인용_불일치는_재작성_2회_뒤_needs_confirmation으로_끝남() -> None:
    """설계 ④·B-4: 답변 시도는 최초 1 + 재작성 2 = 3회이며, 소진하면 답을 내보내지 않음.

    인용문은 index_text에만 있는 '[카드: …]' 머리말임 — 대조 기준이 text라서 매번 실패해야 함(색인 계약 9).
    """

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_SKY: [("d2a1", 0.9), ("d1c1", 0.4)]})
    reranker = FakeReranker(corpus=corpus, scores={"d2a1": 0.92, "d1c1": 0.5})
    llm = FakeLLM(
        action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색")],
        answer=[AnswerOutput(
            (AnswerSentence("스카이카드는 1000원당 2마일을 적립합니다.",
                            (Citation("d2a1", "[카드: 스카이카드]"),)),),
            (), "",
        )],
    )
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, Q_SKY, generate_answer=True)

    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert response.answer is None
    assert response.evidence, "답을 못 내도 찾은 근거 목록은 돌려줌"
    assert "인용" in response.message
    assert h.llm.count(C_04) == 3
    assert [payload.attempt_no for payload in h.llm.payloads_of(C_04)] == [1, 2, 3]
    assert h.llm.payloads_of(C_04)[0].rewrite_reason == ""
    assert h.llm.payloads_of(C_04)[1].rewrite_reason  # 2번째 시도부터 실패 사유를 줌
    log = last_request_log(h)
    assert log["rewrite_count"] == 2
    assert "재작성 소진" in response.finish_reason


# ---------------------------------------------------------------- ⑪ C-04 실패


def test_11_C04_실패는_answer_failed로_근거만_돌려줌() -> None:
    """설계 ④ L-2 대체 경로: 답을 못 만들면 답 없이 근거 목록(출처·본문)만 반환함."""

    h = simple_correct()
    h.llm._scripts[C_04] = [connector_error(C_04, "timeout")]
    response = run(h, Q_FEE, generate_answer=True)

    assert response.status == STATUS_ANSWER_FAILED
    assert response.answer is None
    assert [item.chunk_id for item in response.evidence] == ["d1c1", "d2a1"]
    assert response.message == "답변을 만들지 못해 찾은 근거 목록만 제공합니다."
    assert any("C-04 실패(timeout)" in warning for warning in response.warnings)
    assert h.audit.of_type("connector_error")[0]["connector"] == C_04


# ---------------------------------------------------------------- ⑫ C-01 실패


def test_12_C01_실패는_단순_질문으로_처리함() -> None:
    """설계 ③ C-01 대체 경로: 질문 분석을 못 하면 원 질문 1개로 검색함(실패 호출도 1회로 셈)."""

    h = simple_correct()
    h.llm._scripts[C_01] = [connector_error(C_01, "format")]
    response = run(h, Q_FEE)

    assert response.status == STATUS_RETRIEVED
    assert response.question_type == QTYPE_SIMPLE
    assert any("C-01 실패(format)" in warning for warning in response.warnings)
    assert any("단순 질문으로 처리" in warning for warning in response.warnings)
    assert response.llm_calls == 2  # 실패한 C-01 1회 + C-02 1회
    assert h.index.vector_queries == [Q_FEE]


# ---------------------------------------------------------------- ⑬ C-02 목록 밖 행동


def test_13_C02가_목록_밖_행동을_고르면_규칙_기본_행동으로_대신함() -> None:
    """설계 S-R3 ④: 허용 목록 밖 행동은 거부하고 규칙이 첫 미검색 질문을 검색함."""

    h = simple_correct()
    # 1회전에는 q0이 pending이라 질문 변환이 허용 목록에 없음
    h.llm._scripts[C_02] = [ActionOutput(ACTION_TRANSFORM, "q0", "바로 변환하고 싶음")]
    response = run(h, Q_FEE)

    assert response.status == STATUS_RETRIEVED
    assert any("C-02 선택 거부(허용 목록 밖)" in warning for warning in response.warnings)
    assert C_03 not in h.llm.calls  # 규칙 기본 행동에는 질문 변환이 없음
    first_turn = trace_of(last_request_log(h), "S-R3")[0]
    assert first_turn["action"] == ACTION_SEARCH and first_turn["by_rule"] is True
    assert h.index.vector_queries == [Q_FEE]


# ---------------------------------------------------------------- ⑭ 회전 상한


def _three_subs_uncertain() -> Harness:
    """하위 질문 3개가 검색·변환을 모두 써도 불확실에 머무는 조립임(회전을 최대로 돌림)."""

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, default_hits=[("d1c1", 0.9)])
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.5})
    llm = FakeLLM(
        plan=[PlanOutput(QTYPE_COMPLEX, (Q_SKY, Q_SHOP, "연회비 면제"), "", "세 가지를 함께 물음")],
        action=[ActionOutput(ACTION_SEARCH, "q1", ""), ActionOutput(ACTION_SEARCH, "q2", ""),
                ActionOutput(ACTION_SEARCH, "q3", ""), ActionOutput(ACTION_TRANSFORM, "q1", ""),
                ActionOutput(ACTION_TRANSFORM, "q2", ""), ActionOutput(ACTION_TRANSFORM, "q3", "")],
        transform=[TransformOutput("rewrite", ("질의 변환 하나",), False, "", ""),
                   TransformOutput("rewrite", ("질의 변환 둘",), False, "", ""),
                   TransformOutput("rewrite", ("질의 변환 셋",), False, "", "")],
    )
    return build(index=index, reranker=reranker, llm=llm)


def test_14_회전_상한_도달_시_7번째_S_R3_진입은_LLM_없이_끝남() -> None:
    """설계 ④: 회전 수는 S-R3 진입 횟수로 세고, 7번째 진입은 LLM 없이 규칙이 수집 종료함."""

    h = _three_subs_uncertain()
    response = run(h, "스카이카드 마일리지 와 쇼핑카드 할인 과 연회비 면제")

    log = last_request_log(h)
    assert log["turns"] == 7
    assert h.llm.count(C_02) == 6  # 7번째 진입에서는 C-02를 부르지 않음
    last_turn = trace_of(log, "S-R3")[-1]
    assert last_turn["turn"] == 7
    assert last_turn["by_rule"] is True
    assert "회전 상한 6회 도달" in last_turn["reason"]
    assert response.status == STATUS_NEEDS_CONFIRMATION  # 근거 0건
    assert "회전 상한 6회 도달" in response.finish_reason


# ---------------------------------------------------------------- ⑮ LLM 호출 상한


def test_15_LLM_호출_상한에_닿으면_S_R3가_LLM_없이_수집_종료함() -> None:
    """설계 ④·③: 요청당 LLM 호출 상한(기본 16회)에 닿으면 상한을 넘기지 않고 착지함."""

    assert BudgetPolicy().max_llm_calls == 16  # 설계 본문 값

    # 최장 회전을 다 돌려도 상한을 넘지 않음
    worst = _three_subs_uncertain()
    worst_response = run(worst, "스카이카드 마일리지 와 쇼핑카드 할인 과 연회비 면제")
    assert worst_response.llm_calls <= 16
    assert worst_response.llm_calls == 10  # C-01 1 + C-02 6 + C-03 3

    # 상한 분기 자체는 값에만 의존하므로 낮은 상한으로 그 경로를 확인함
    capped = simple_correct()
    capped.steps.config = StepConfig(budget=BudgetPolicy(max_llm_calls=2))
    response = run(capped, Q_FEE)
    assert response.llm_calls == 2
    assert capped.llm.calls == [C_01, C_02]
    assert "LLM 호출 상한 2회 도달" in response.finish_reason
    assert response.status == STATUS_RETRIEVED  # 이미 모은 근거로 부분결과를 돌려줌


# ---------------------------------------------------------------- ⑯ 남은 시간 예산 착지


def test_16a_S_R2_시간_부족이면_C01_없이_단순_질문으로_감() -> None:
    """설계 ⑥-10 착지표: S-R2가 시작 기준에 못 미치면 대체 경로(단순 질문)로 감."""

    clock = FakeClock()
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_FEE: [("d1c1", 0.9)]}, clock=clock)
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.92})
    llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "")], clock=clock)
    provider = FakeIndexProvider(index=index, clock=clock, cost_s=22.0)  # 30 − 22 − 1.5 − 5.2 = 1.3 < 1.5
    h = build(index=index, reranker=reranker, llm=llm, provider=provider, clock=clock)
    response = run(h, Q_FEE)

    assert C_01 not in h.llm.calls
    assert response.question_type == QTYPE_SIMPLE
    assert any("남은 시간 예산 부족" in warning for warning in response.warnings)
    assert response.status == STATUS_RETRIEVED  # S-R3 이후는 아직 시작 기준을 넘김


def test_16b_L1_시간_부족이면_검색_없이_수집_종료함() -> None:
    """설계 ⑥-10 착지표: S-R3 ~ S-R6은 부분결과(수집 종료 → B-2a)로 착지함."""

    clock = FakeClock()
    index = FakeIndex(hits={Q_FEE: [("d1c1", 0.9)]}, clock=clock)
    provider = FakeIndexProvider(index=index, clock=clock, cost_s=25.0)  # 30 − 25 − 1.5 − 2.7 = 0.8 < 1.5
    h = build(index=index, provider=provider, clock=clock)
    response = run(h, Q_FEE)

    assert h.index.vector_queries == []
    assert h.llm.calls == []  # C-01도 C-02도 부르지 않음
    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert "남은 시간 예산 부족" in response.finish_reason


def test_16c_S_R7_시간_부족이면_answer_failed로_근거만_돌려줌() -> None:
    """설계 ⑥-10 착지표: S-R7·S-R8은 답 없이 근거 목록만 돌려줌(답변 생성 실패)."""

    clock = FakeClock()
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_SKY: [("d2a1", 0.9), ("d1c1", 0.4)]}, clock=clock)
    reranker = FakeReranker(corpus=corpus, scores={"d2a1": 0.92, "d1c1": 0.5})
    llm = FakeLLM(
        plan=[PlanOutput(QTYPE_COMPLEX, (Q_SKY, Q_SHOP), "", "두 카드")],
        action=[ActionOutput(ACTION_SEARCH, "q1", ""), ActionOutput(ACTION_FINISH, "", "충분함")],
        clock=clock, costs={C_02: 12.5},  # 2회전 뒤 경과 25초 → 30 − 25 − 1.5 − 2.5 = 1.0 < 1.5
    )
    h = build(index=index, reranker=reranker, llm=llm, clock=clock)
    response = run(h, Q_MIXED, generate_answer=True)

    assert response.status == STATUS_ANSWER_FAILED
    assert C_04 not in h.llm.calls
    assert [item.chunk_id for item in response.evidence] == ["d2a1", "d1c1"]
    assert "남은 시간 예산 부족" in response.finish_reason


def test_16d_S_R8_시간_부족이면_재작성을_멈추고_needs_confirmation으로_끝남() -> None:
    """설계 B-4: 재작성 기회가 남아도 시간 예산이 모자라면 검증 못 한 답을 내보내지 않음."""

    clock = FakeClock()
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_SKY: [("d2a1", 0.9)]}, clock=clock)
    reranker = FakeReranker(corpus=corpus, scores={"d2a1": 0.92})
    llm = FakeLLM(
        action=[ActionOutput(ACTION_SEARCH, "q0", "")],
        answer=[AnswerOutput(
            (AnswerSentence("스카이카드 적립 안내입니다.", (Citation("d2a1", "[카드: 스카이카드]"),)),), (), ""
        )],
        clock=clock, costs={C_04: 20.0},  # 2번째 시도 뒤 경과 40초 → 재작성 기회는 남았지만 시간이 없음
    )
    h = build(index=index, reranker=reranker, llm=llm, clock=clock)
    response = run(h, Q_SKY, generate_answer=True)

    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert h.llm.count(C_04) == 2  # 상한 3회를 다 쓰지 않고 멈춤
    assert last_request_log(h)["rewrite_count"] == 1
    assert "남은 시간 예산 부족" in response.finish_reason


# ---------------------------------------------------------------- ⑰ 검색 연속 실패


def test_17_검색_연속_실패_2회면_즉시_수집_종료함() -> None:
    """설계 ④: 같은 유형 검색 실패가 2회 연속이면 남은 질문을 검색하지 않고 바로 끝냄."""

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, default_hits=[("d1c1", 0.9)],
                      vector_error=RuntimeError("벡터 저장소 장애"), keyword_error=RuntimeError("BM25 장애"))
    llm = FakeLLM(
        plan=[PlanOutput(QTYPE_COMPLEX, (Q_SKY, Q_SHOP, "연회비 면제"), "", "세 가지")],
        action=[ActionOutput(ACTION_SEARCH, "q1", ""), ActionOutput(ACTION_SEARCH, "q2", ""),
                ActionOutput(ACTION_SEARCH, "q3", "")],
    )
    h = build(index=index, llm=llm)
    response = run(h, "스카이카드 마일리지 와 쇼핑카드 할인 과 연회비 면제")

    assert h.index.vector_queries == [Q_SKY, Q_SHOP]  # q3는 검색하지 않음
    assert h.llm.count(C_02) == 2
    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert "검색 연속 실패 2회" in response.finish_reason
    assert any("벡터·BM25 모두 실패" in warning for warning in response.warnings)
    assert last_request_log(h)["turns"] == 3


# ---------------------------------------------------------------- ⑱ 권한


def test_18_agent_역할에는_restricted_조각이_결과에_없음() -> None:
    """설계 ⑥-7·가드레일 ②: 권한은 LLM이 바꿀 수 없고, 색인이 흘려도 응용 계층이 한 번 더 거름."""

    question = "상담 이력 민원"
    corpus = make_corpus()

    def harness() -> Harness:
        """권한 밖 조각까지 돌려주는 색인으로 조립함(역할만 바꿔 두 번 실행하려고 함수로 둠)."""

        index = FakeIndex(corpus=corpus, hits={question: [("d3c1", 0.95), ("d1c1", 0.4)]}, leaky=True)
        reranker = FakeReranker(corpus=corpus, scores={"d3c1": 0.9, "d1c1": 0.4})
        llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "")])
        return build(index=index, reranker=reranker, llm=llm)

    agent = harness()
    agent_response = run(agent, question, role="agent")
    assert "d3c1" not in [item.chunk_id for item in agent_response.evidence]
    assert "d3c1" not in agent_response.model_dump_json()
    assert any("권한 밖 조각 1건을 결과에서 제외" in warning for warning in agent_response.warnings)

    auditor = harness()
    auditor_response = run(auditor, question, role="auditor")
    assert "d3c1" in [item.chunk_id for item in auditor_response.evidence]
    assert auditor_response.status == STATUS_RETRIEVED


# ---------------------------------------------------------------- ⑲ 리랭커 실패


def test_19_리랭커_실패면_정확_판정이_나오지_않음() -> None:
    """설계 ⑥-8 사용자 결정: 리랭크가 실패하면 점수로 상한을 잴 수 없어 최대 불확실임."""

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_FEE: [("d1c1", 0.99), ("d2a1", 0.4)]})
    reranker = FakeReranker(corpus=corpus, error=RuntimeError("리랭커 모델 장애"))
    llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "")])
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, Q_FEE)

    log = last_request_log(h)
    signals = log["grade_signals"]["q0"]
    assert signals["grade"] == "uncertain"
    assert signals["reranked"] is False
    assert signals["main_score"] is None and signals["score_band"] == "unknown"
    assert all(entry["grade"] != "correct" for entry in trace_of(log, "S-R5"))
    assert response.status == STATUS_NEEDS_CONFIRMATION
    assert any("리랭커 실패 → 융합 결과 사용" in warning for warning in response.warnings)


# ---------------------------------------------------------------- ⑳ 감사 로그


def test_20_감사_로그에_질문_원문이_남지_않음() -> None:
    """설계 ③ 로그 규칙: 질문은 해시 16자와 앞 20자만 남김."""

    question = "연회비 면제 조건 을 자세히 알려 주세요"
    assert len(question) > 20
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={question: [("d1c1", 0.9), ("d2a1", 0.4)]})
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.92, "d2a1": 0.3})
    llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색")])
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, question)

    assert response.status == STATUS_RETRIEVED
    log = last_request_log(h)
    assert log["query_head"] == question[:20]
    assert len(log["query_sha256"]) == 16
    for record in h.audit.records:
        dumped = json.dumps(record, ensure_ascii=False, default=str)
        assert question not in dumped, f"질문 원문이 감사 로그에 남음: {record['type']}"


# ---------------------------------------------------------------- ㉑ 핵심어 = 상품명·숫자·코드(사용자 결정)


def test_21_상품명_핵심어가_결과에_없으면_불확실이고_일반명사는_핵심어가_아님() -> None:
    """S-R5 ④ '핵심어(코드·상품명)': 다른 카드 조각만 나오면 불확실 → 변환 대상, 일반 명사 누락은 판정을 막지 않음."""

    corpus = make_corpus()
    q_other = "스카이카드 마일리지 주요 혜택"
    index = FakeIndex(corpus=corpus, hits={
        Q_SKY: [("d2b1", 0.9)],  # 스카이카드를 물었는데 쇼핑카드 조각만 나옴
        q_other: [("d2a1", 0.9)],  # '주요'·'혜택'은 결과에 없지만 상품명 스카이카드는 있음
    })
    reranker = FakeReranker(corpus=corpus, scores={"d2b1": 0.95, "d2a1": 0.95})

    def fresh() -> Harness:
        """요청마다 C-02 대본을 처음부터 쓰도록 새로 조립함."""

        llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색"), ActionOutput(ACTION_FINISH, "", "종료")])
        return build(index=index, reranker=reranker, llm=llm)

    h = fresh()
    run(h, Q_SKY)
    signals = last_request_log(h)["grade_signals"]["q0"]
    assert signals["grade"] == "uncertain"
    assert signals["missing_keywords"] == ["스카이카드"]

    h = fresh()
    response = run(h, q_other)
    signals = last_request_log(h)["grade_signals"]["q0"]
    assert signals["keywords"] == ["스카이카드"]  # '주요'·'혜택'·'마일리지'는 상품명·숫자·코드가 아님
    assert signals["grade"] == "correct"
    assert response.status == STATUS_RETRIEVED


# ---------------------------------------------------------------- ㉒ 대상 = 카드, 1위가 카드일 때만 섞임(사용자 결정)


def test_22_약관이_1위면_카드가_섞여도_되묻지_않고_질문_변환으로_감() -> None:
    """설계 ⑥-3 '대상명 없음 + 대상 섞임'의 대상은 카드임. 1위가 약관이면 카드 질문이 아니라 C-03으로 다시 찾음."""

    question = "마일리지 할인 조건"
    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={question: [("d1c1", 0.9), ("d2a1", 0.6), ("d2b1", 0.5)]})
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.5, "d2a1": 0.45, "d2b1": 0.4})
    llm = FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색"),
                          ActionOutput(ACTION_TRANSFORM, "q0", "불확실 — 변환")])
    h = build(index=index, reranker=reranker, llm=llm)
    response = run(h, question)

    assert C_03 in h.llm.calls  # 규칙이 되묻지 않았으므로 질문 변환 LLM이 불림
    assert response.clarify_question == ""
    assert not any("대상 섞임" in warning for warning in response.warnings)



# ---------------------------------------------------------------- ㉓ ~ ㉕ 개선안 1 · 2 · 3 (사용자 결정 2026-10-03)


def _one_search_llm() -> FakeLLM:
    """원 질문을 한 번 검색하고 끝내는 C-02 대본."""

    return FakeLLM(action=[ActionOutput(ACTION_SEARCH, "q0", "원 질문 검색"), ActionOutput(ACTION_FINISH, "", "종료")])


def test_23_겹침이_0이어도_1위가_0_9_이상이면_정확으로_근거를_돌려줌() -> None:
    """개선안 1: 벡터·BM25 상위가 하나도 안 겹쳐도 리랭크 1위가 면제 기준 이상이면 검색기 합의로 봄."""

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_SKY: [("d2a1", 0.9)]}, keyword_hits={Q_SKY: [("d1c1", 5.0)]})
    high = build(index=index, reranker=FakeReranker(corpus=corpus, scores={"d2a1": 0.95, "d1c1": 0.2}),
                 llm=_one_search_llm())
    response = run(high, Q_SKY)
    signals = last_request_log(high)["grade_signals"]["q0"]
    assert signals["retriever_overlap"] == 0 and signals["grade"] == "correct"
    assert response.status == STATUS_RETRIEVED

    below = build(index=index, reranker=FakeReranker(corpus=corpus, scores={"d2a1": 0.85, "d1c1": 0.2}),
                  llm=_one_search_llm())
    run(below, Q_SKY)
    assert last_request_log(below)["grade_signals"]["q0"]["grade"] == "uncertain"  # 0.85 < 0.9면 그대로 불확실


def test_24_정확이어도_리랭크_하한_미만_조각은_근거에_넣지_않음() -> None:
    """개선안 2: 정확 판정 결과 중 리랭크 0.3 미만(다른 카드 등)은 근거 목록·답변 재료에서 빠짐."""

    corpus = make_corpus()
    index = FakeIndex(corpus=corpus, hits={Q_FEE: [("d1c1", 0.9), ("d2a1", 0.5), ("d2b1", 0.4)]})
    reranker = FakeReranker(corpus=corpus, scores={"d1c1": 0.92, "d2a1": 0.31, "d2b1": 0.03})
    h = build(index=index, reranker=reranker, llm=_one_search_llm())
    response = run(h, Q_FEE)

    assert response.status == STATUS_RETRIEVED
    assert [item.chunk_id for item in response.evidence] == ["d1c1", "d2a1"]  # 0.03은 빠짐, 0.31은 남음
    assert last_request_log(h)["grade_signals"]["q0"]["result_count"] == 3  # 채점은 상위 3건 전부로 함


def test_25_잡담_판정이어도_업무_낱말이_있으면_검색함() -> None:
    """개선안 3: C-01이 잡담이라 해도 조각 20% 이상에 나오는 업무 명사가 있으면 단순 질문으로 검색함."""

    corpus = make_corpus()
    chitchat = [PlanOutput(QTYPE_CHITCHAT, (), "안녕하세요!", "인사로 판단")]
    business = build(index=FakeIndex(corpus=corpus, hits={Q_FEE: [("d1c1", 0.9)]}, df={"연회비": 2}),
                     reranker=FakeReranker(corpus=corpus, scores={"d1c1": 0.92}),
                     llm=FakeLLM(plan=chitchat, action=[ActionOutput(ACTION_SEARCH, "q0", "")]))
    response = run(business, Q_FEE)
    assert response.question_type == QTYPE_SIMPLE
    assert business.index.vector_queries == [Q_FEE]
    assert any("업무 낱말" in warning for warning in response.warnings)

    greeting = "안녕 반가워"
    small_talk = build(index=FakeIndex(corpus=corpus, df={"안녕": 0}), llm=FakeLLM(plan=chitchat))
    response = run(small_talk, greeting)
    assert response.status == STATUS_NO_RETRIEVAL  # 업무 낱말이 없으면 그대로 검색 없이 응답
    assert small_talk.index.vector_queries == []
