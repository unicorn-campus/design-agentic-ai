"""S-R1 ~ S-R9 단계 로직. 각 단계는 상태를 읽고 바뀐 값과 다음 노드(route)만 돌려줌.

단계 순서·분기는 설계서 ① 흐름 유형을 따르고, 실행 엔진(LangGraph)은 infrastructure가 맡음.
기술은 모두 포트로만 부르므로 이 파일은 가짜 포트로 시험할 수 있음.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from typing import Any, Callable, Mapping, Sequence

from app.domain.access import access_levels_for
from app.domain.actions import (
    ACTION_FINISH,
    ACTION_SEARCH,
    ACTION_TRANSFORM,
    ActionChoice,
    allowed_actions,
    default_action,
    validate_choice,
)
from app.domain.budget import (
    C_01,
    C_02,
    C_03,
    C_04,
    S_R1,
    S_R2,
    S_R3,
    S_R4,
    S_R5,
    S_R6,
    S_R7,
    S_R8,
    S_R9,
    BudgetPolicy,
    can_start,
    remaining_budget,
)
from app.domain.fusion import equal_weight_merge, rank_keys, rrf_merge, weighted_hybrid
from app.domain.grading import GradeThresholds, build_signals, evidence_worthy, grade
from app.domain.keywords import select_common_domain_terms, select_rare_terms
from app.domain.models import (
    GRADE_CORRECT,
    GRADE_INCORRECT,
    GRADE_UNCERTAIN,
    QTYPE_CHITCHAT,
    QTYPE_COMPLEX,
    SUB_INSUFFICIENT,
    SUB_PENDING,
    SUB_SATISFIED,
    SUB_UNCERTAIN,
    Candidate,
    SubQuestion,
)
from app.domain.plan_rules import PlanDecision, apply_plan_rules, fallback_simple
from app.domain.transform_rules import (
    ALLOWED_TECHNIQUES,
    CLARIFY,
    KEEP,
    TECHNIQUE_GUIDE,
    TransformDecision,
    apply_transform_rules,
    mixed_target_clarify,
)
from app.domain.verification import verify_answer

from .models import (
    MAX_QUERY_CHARS,
    STATUS_ANSWER_FAILED,
    STATUS_ANSWERED,
    STATUS_ERROR,
    STATUS_NEEDS_CONFIRMATION,
    STATUS_NO_RETRIEVAL,
    STATUS_RETRIEVED,
    TOP_K_RANGE,
    ActionInput,
    AnswerInput,
    ConnectorError,
    IndexUnavailableError,
    PlanInput,
    TransformInput,
)
from .ports import AuditLogPort, ClockPort, IndexProviderPort, LanguageModelPort, RerankerPort
from .state import (
    NODE_END,
    NODE_S_R1,
    NODE_S_R2,
    NODE_S_R3,
    NODE_S_R4,
    NODE_S_R5,
    NODE_S_R6,
    NODE_S_R7,
    NODE_S_R8,
    NODE_S_R9,
    EvidenceItem,
    RetrieverState,
)

# 노드 이름 → 단계ID(시간 측정·감사 로그 키)
NODE_STEP_IDS: dict[str, str] = {
    NODE_S_R1: S_R1, NODE_S_R2: S_R2, NODE_S_R3: S_R3, NODE_S_R4: S_R4, NODE_S_R5: S_R5,
    NODE_S_R6: S_R6, NODE_S_R7: S_R7, NODE_S_R8: S_R8, NODE_S_R9: S_R9,
}

# 응답 상태 중 근거 목록을 함께 돌려주는 상태. 잡담·오류는 근거가 없음.
_STATUSES_WITH_EVIDENCE = frozenset(
    {STATUS_ANSWERED, STATUS_RETRIEVED, STATUS_NEEDS_CONFIRMATION, STATUS_ANSWER_FAILED}
)


@dataclass(frozen=True)
class StepConfig:
    """단계 로직이 쓰는 설계값 묶음. 설정에서 읽어 bootstrap이 주입함."""

    budget: BudgetPolicy = BudgetPolicy()
    thresholds: GradeThresholds = GradeThresholds()
    vector_weight: float = 0.6  # 하이브리드 벡터 비중(설계 ⑥-6, 결정 필요 — 재검증 대상)
    keyword_weight: float = 0.4  # 하이브리드 BM25 비중
    keyword_max_df_ratio: float = 0.1  # 핵심어 '드묾' 기준: 전체 조각의 10% 이하에 나오는 낱말(설계 가정)
    domain_term_min_df_ratio: float = 0.2  # 업무 어휘 기준: 전체 조각의 20% 이상에 나오는 명사(잡담 오분류 막기, 설계 가정)
    prompt_chunk_count: int = 5  # C-03에 넘기는 결과 조각 수(설계 가정)
    prompt_chunk_chars: int = 1200  # C-03에 넘기는 조각당 글자 수 상한(설계 가정)


@dataclass(frozen=True)
class _QueryResult:
    """질의 1개의 검색 결과(S-R4 ② ~ ⑤). 여러 질의를 합칠 때 재료로 씀."""

    order: list[str]  # 최종 순위(리랭크 순, 실패면 융합 순) 상위 top_k
    main_scores: dict[str, float]  # 주 점수(리랭크, 실패면 융합 점수)
    candidates: dict[str, Candidate]
    vector_ids: list[str]  # 벡터 검색기 순위
    keyword_ids: list[str]  # BM25 검색기 순위


class RetrieverSteps:
    """문서 검색 워크플로우의 9개 단계를 구현함.

    색인 공급·리랭커·LLM·감사 로그·시계 포트를 생성자로 주입받음. 구현체 생성은 하지 않으며 조립은 app/bootstrap.py가 맡음.
    LLM은 '다음에 무엇을 할지'만 고르고, 권한·상한·채점·검증은 이 클래스의 규칙이 강제함(설계 ① 패턴 적용).
    """

    def __init__(
        self,
        *,
        index_provider: IndexProviderPort,
        reranker: RerankerPort,
        llm: LanguageModelPort,
        audit_log: AuditLogPort,
        clock: ClockPort,
        config: StepConfig | None = None,
    ) -> None:
        """포트와 설계값을 보관함. 부수효과 없음."""

        self.index_provider = index_provider
        self.reranker = reranker
        self.llm = llm
        self.audit_log = audit_log
        self.clock = clock
        self.config = config or StepConfig()
        self._handlers: dict[str, Callable[[RetrieverState], dict[str, Any]]] = {
            NODE_S_R1: self.s_r1, NODE_S_R2: self.s_r2, NODE_S_R3: self.s_r3,
            NODE_S_R4: self.s_r4, NODE_S_R5: self.s_r5, NODE_S_R6: self.s_r6,
            NODE_S_R7: self.s_r7, NODE_S_R8: self.s_r8, NODE_S_R9: self.s_r9,
        }

    # ------------------------------------------------------------ 실행 엔진 연결용

    def node(self, name: str) -> Callable[[RetrieverState], dict[str, Any]]:
        """노드 이름에 맞는 단계 함수를 시간 측정 래퍼로 감싸 반환함.

        반환값: 상태를 받아 바뀐 값 dict를 돌려주는 함수. 단계별 소요 시간을 timings에 더하고 남은 시간 예산을 갱신함.
        예외: 모르는 노드 이름이면 KeyError를 발생시킴.
        """

        handler = self._handlers[name]
        step_id = NODE_STEP_IDS[name]

        def run(state: RetrieverState) -> dict[str, Any]:
            """단계를 실행하고 소요 시간을 timings에 더함."""

            started = self.clock.now()
            updates = handler(state)
            duration = self.clock.now() - started
            timings = dict(state.get("timings") or {})
            timings[step_id] = round(timings.get(step_id, 0.0) + duration, 4)
            updates["timings"] = timings
            if "response" in updates:
                # S-R9는 응답을 만든 뒤에야 자기 소요 시간을 알 수 있으므로 응답의 시간표를 마지막에 다시 채움
                updates["response"]["timings"] = timings
                updates["response"]["timings"]["total"] = round(self._elapsed(state), 4)
            return updates

        return run

    @staticmethod
    def route(state: RetrieverState) -> str:
        """각 단계가 정한 다음 노드 이름을 돌려줌. 실행 엔진의 조건부 연결에 씀."""

        return str(state.get("route") or NODE_S_R9)

    # ------------------------------------------------------------ 공통 도우미

    def _elapsed(self, state: Mapping[str, Any]) -> float:
        """요청 시작부터 지금까지 쓴 시간(초)."""

        return self.clock.now() - float(state.get("started_at", self.clock.now()))

    def _can_start(self, state: Mapping[str, Any], step_id: str) -> bool:
        """설계 ⑥-10: 단계 시작 직전에 남은 시간 예산이 시작 기준 이상인지 확인함."""

        return can_start(
            self.config.budget,
            elapsed_seconds=self._elapsed(state),
            step_id=step_id,
            generate_answer=bool(state.get("generate_answer")),
        )

    def _budget_left(self, state: Mapping[str, Any], step_id: str) -> float:
        """감사 로그·오류 로그용 남은 시간 예산(초)."""

        return round(
            remaining_budget(
                self.config.budget,
                elapsed_seconds=self._elapsed(state),
                step_id=step_id,
                generate_answer=bool(state.get("generate_answer")),
            ),
            3,
        )

    def _llm_exhausted(self, state: Mapping[str, Any]) -> bool:
        """요청당 LLM 호출 상한(16회)에 닿았는지 확인함(가드레일 ①)."""

        return int(state.get("llm_calls", 0)) >= self.config.budget.max_llm_calls

    def _call_llm(
        self,
        state: Mapping[str, Any],
        *,
        step_id: str,
        connector_id: str,
        call: Callable[[], Any],
        fallback: str,
        warnings: list[str],
    ) -> tuple[Any | None, int]:
        """LLM 커넥터를 1회 부르고 실패하면 None을 돌려줌(재시도 0회).

        목적: 모든 커넥터 실패를 '그 단계의 대체 경로'로 이어 가게 하고, 오류 로그 규칙(설계 ③)을 한 곳에서 지킴.
        반환값: (응답 또는 None, 갱신된 LLM 호출 수). 실패해도 호출 1회로 셈.
        부수효과: 실패 시 감사 로그에 커넥터 오류 1건을 남기고 warnings에 사유를 더함.
        """

        calls = int(state.get("llm_calls", 0)) + 1
        try:
            return call(), calls
        except ConnectorError as error:
            warnings.append(f"{connector_id} 실패({error.kind}) → {fallback}")
            self.audit_log.write(
                {
                    "type": "connector_error",
                    "request_id": state.get("request_id"),
                    "step": step_id,
                    "connector": connector_id,
                    "kind": error.kind,
                    "status_code": error.status_code,
                    "elapsed_seconds": error.elapsed_seconds,
                    "time_budget_left_s": self._budget_left(state, step_id),
                    "fallback": fallback,
                }
            )
            return None, calls

    @staticmethod
    def _error(code: str, message: str, warnings: Sequence[str] = ()) -> dict[str, Any]:
        """오류 응답으로 가는 상태 변경값을 만듦."""

        return {
            "status": STATUS_ERROR,
            "error_code": code,
            "error_message": message,
            "finish_reason": f"오류: {code}",
            "warnings": list(warnings),
            "route": NODE_S_R9,
        }

    @staticmethod
    def _replace_sub(subs: Sequence[SubQuestion], qid: str, **changes: Any) -> list[SubQuestion]:
        """하위 질문 목록에서 qid 하나만 바꾼 새 목록을 반환함(상태를 제자리에서 고치지 않음)."""

        return [replace(sq, **changes) if sq.qid == qid else sq for sq in subs]

    @staticmethod
    def _find_sub(subs: Sequence[SubQuestion], qid: str) -> SubQuestion | None:
        """qid에 맞는 하위 질문을 찾음."""

        return next((sq for sq in subs if sq.qid == qid), None)

    @staticmethod
    def _trace(state: Mapping[str, Any], entry: dict[str, Any]) -> list[dict[str, Any]]:
        """행동 기록에 한 건을 더한 새 목록을 반환함(감사 로그 재료)."""

        return [*list(state.get("trace") or []), entry]

    # ------------------------------------------------------------ S-R1 요청 접수·검색 준비 확인

    def s_r1(self, state: RetrieverState) -> dict[str, Any]:
        """잘못된 요청과 쓸 수 없는 색인을 검색 전에 거름.

        방법: 질문·옵션 범위 → 역할 → 열람 등급 → 이번 요청이 쓸 세대 순서로 확인함.
        세대는 요청이 끝날 때까지 바꾸지 않음(조각ID가 세대마다 달라 근거와 색인이 어긋나지 않게 함).
        """

        warnings = list(state.get("warnings") or [])
        query = state.get("query")
        if not isinstance(query, str) or not query.strip():
            return self._error("invalid_input", "질문이 비어 있습니다.", warnings)
        if len(query) > MAX_QUERY_CHARS:
            return self._error("invalid_input", f"질문은 {MAX_QUERY_CHARS}자 이하여야 합니다.", warnings)
        top_k = state.get("top_k")
        # bool은 int의 하위 타입이라 True가 1로 통과하지 않도록 따로 막음
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not TOP_K_RANGE[0] <= top_k <= TOP_K_RANGE[1]:
            return self._error("invalid_input", f"반환 수는 {TOP_K_RANGE[0]} ~ {TOP_K_RANGE[1]} 사이 정수여야 합니다.", warnings)
        if not isinstance(state.get("generate_answer"), bool):
            return self._error("invalid_input", "답변 생성 여부는 참·거짓이어야 합니다.", warnings)
        role = state.get("role")
        if role is None or not str(role).strip():
            return self._error("role_missing", "로그인 정보에 역할이 없습니다.", warnings)
        try:
            access_levels = access_levels_for(role)
        except ValueError:
            return self._error("invalid_role", "허용되지 않은 역할입니다.", warnings)
        try:
            lease = self.index_provider.acquire()
        except IndexUnavailableError as error:
            return self._error("index_unavailable", error.message, warnings)
        warnings.extend(lease.warnings)
        return {
            "query": query.strip(),
            "access_levels": list(access_levels),
            "index": lease.index,
            "generation": lease.index.generation_id(),
            "status": "running",
            "llm_calls": 0,
            "turn": 0,
            "warnings": warnings,
            "trace": self._trace(state, {"step": S_R1, "generation": lease.index.generation_id()}),
            "route": NODE_S_R2,
        }

    # ------------------------------------------------------------ S-R2 질문 분석·계획(B-1)

    def s_r2(self, state: RetrieverState) -> dict[str, Any]:
        """질문 유형을 정하고 검색 대상 질문을 확정함.

        방법: C-01이 유형·하위 질문을 내고 서버 규칙(형식·개수·조건 보존)이 확정함.
        C-01 실패·시간 부족·호출 상한이면 C-01 없이 단순 질문(원 질문 1개)으로 진행함(대체 경로).
        """

        warnings = list(state.get("warnings") or [])
        query = str(state["query"])
        index = state["index"]
        llm_calls = int(state.get("llm_calls", 0))
        decision: PlanDecision
        if not self._can_start(state, S_R2):
            decision = fallback_simple("남은 시간 예산 부족 → C-01 없이 단순 질문으로 처리")
        elif self._llm_exhausted(state):
            decision = fallback_simple("LLM 호출 상한 → C-01 없이 단순 질문으로 처리")
        else:
            payload = PlanInput(
                user_question=query,
                max_sub_questions=self.config.budget.max_sub_questions,
                today=str(state.get("today") or "") or None,
            )
            result, llm_calls = self._call_llm(
                state, step_id=S_R2, connector_id=C_01, call=lambda: self.llm.analyze_question(payload),
                fallback="단순 질문으로 처리", warnings=warnings,
            )
            if result is None:
                decision = fallback_simple("C-01 응답 없음 → 단순 질문으로 처리")
            else:
                decision = apply_plan_rules(
                    question=query,
                    question_type=result.question_type,
                    sub_questions=result.sub_questions,
                    chitchat_reply=result.chitchat_reply,
                    max_sub_questions=self.config.budget.max_sub_questions,
                    condition_terms_of=lambda text: set(index.condition_terms(text)),
                    domain_terms_of=lambda text: self._domain_terms(index, text),
                )
        warnings.extend(decision.warnings)
        trace = self._trace(state, {"step": S_R2, "question_type": decision.question_type,
                                    "sub_questions": len(decision.sub_question_texts) or 1})
        base: dict[str, Any] = {"question_type": decision.question_type, "llm_calls": llm_calls,
                                "warnings": warnings, "trace": trace}
        if decision.question_type == QTYPE_CHITCHAT:
            return {**base, "status": STATUS_NO_RETRIEVAL, "chitchat_reply": decision.chitchat_reply,
                    "sub_questions": [], "finish_reason": "인사·잡담 — 검색 불필요", "route": NODE_S_R9}
        if decision.question_type == QTYPE_COMPLEX:
            # 분해 시에는 하위 질문만 검색하고 원 질문은 답변·기록용으로만 보관함(이론 11장, 사용자 결정)
            subs = [SubQuestion(f"q{i}", text, "decomposed") for i, text in enumerate(decision.sub_question_texts, 1)]
        else:
            subs = [SubQuestion("q0", query, "original")]
        return {**base, "sub_questions": subs, "evidence": {}, "evidence_rankings": {}, "grade_signals": {},
                "qid_candidates": {}, "transform_history": [], "search_fail_streak": 0, "rewrite_count": 0,
                "route": NODE_S_R3}

    def _domain_terms(self, index: Any, text: str) -> set[str]:
        """업무 낱말 = 상품명·숫자·코드(조건 낱말) + 색인 조각의 일정 비율 이상에 나오는 명사.

        목적: C-01이 업무 질문을 잡담으로 잘못 보면 검색 없이 끝나므로, 잡담 판정일 때만 한 번 더 확인함.
        """

        common = select_common_domain_terms(
            index.document_frequency(index.keyword_candidates(text)),
            num_docs=index.num_docs(), min_df_ratio=self.config.domain_term_min_df_ratio,
        )
        return set(index.condition_terms(text)) | set(common)

    # ------------------------------------------------------------ S-R3 다음 행동 선택(B-2·B-2a)

    def s_r3(self, state: RetrieverState) -> dict[str, Any]:
        """근거가 모였는지 판단해 다음 한 걸음(검색·질문 변환·수집 종료)을 고름.

        방법: 회전 수를 1 늘린 뒤 상한(7번째 진입·LLM 16회·시간 부족·검색 연속 실패 2회)이면 LLM 없이 수집 종료함.
        아니면 규칙이 만든 허용 행동 목록 안에서 C-02가 고르고, 목록 밖·없는 ID·응답 오류면 규칙 기본 행동으로 대신함.
        """

        warnings = list(state.get("warnings") or [])
        subs: list[SubQuestion] = list(state.get("sub_questions") or [])
        turn = int(state.get("turn", 0)) + 1
        llm_calls = int(state.get("llm_calls", 0))
        budget = self.config.budget
        stop_reason = ""
        if turn > budget.max_turns:
            stop_reason = f"회전 상한 {budget.max_turns}회 도달"
        elif self._llm_exhausted(state):
            stop_reason = f"LLM 호출 상한 {budget.max_llm_calls}회 도달"
        elif not self._can_start(state, S_R3):
            stop_reason = "남은 시간 예산 부족"
        elif int(state.get("search_fail_streak", 0)) >= budget.max_search_fail_streak:
            stop_reason = f"검색 연속 실패 {budget.max_search_fail_streak}회"

        choice: ActionChoice
        if stop_reason:
            choice = ActionChoice(ACTION_FINISH, "", stop_reason, by_rule=True)
        else:
            allowed = allowed_actions(subs)
            if allowed == [ACTION_FINISH]:
                # 고를 수 있는 행동이 수집 종료 하나뿐이면 LLM 답이 정해져 있으므로 부르지 않음(호출 절약)
                choice = ActionChoice(ACTION_FINISH, "", "모든 질문의 검색·변환 기회를 다 씀", by_rule=True)
            else:
                payload = ActionInput(
                    allowed_actions=tuple(allowed),
                    sub_question_states=tuple(
                        {"id": sq.qid, "question": sq.text, "grade": sq.status,
                         "evidence_count": sq.evidence_count, "transform_count": sq.transform_count}
                        for sq in subs
                    ),
                    remaining_turns=budget.max_turns - turn,
                    original_question=str(state["query"]),
                )
                result, llm_calls = self._call_llm(
                    state, step_id=S_R3, connector_id=C_02, call=lambda: self.llm.choose_action(payload),
                    fallback="규칙 기본 행동", warnings=warnings,
                )
                if result is None:
                    choice = default_action(subs, "C-02 응답 없음 → 규칙 기본 행동")
                else:
                    validated = validate_choice(
                        subs, action=result.action, target_qid=result.target_sub_question_id, reason=result.reason
                    )
                    if validated is None:
                        warnings.append(f"C-02 선택 거부(허용 목록 밖): {result.action}/{result.target_sub_question_id}")
                        choice = default_action(subs, "C-02 선택이 허용 범위 밖 → 규칙 기본 행동")
                    else:
                        choice = validated

        trace = self._trace(state, {"step": S_R3, "turn": turn, "action": choice.action, "target": choice.target_qid,
                                    "reason": choice.reason, "by_rule": choice.by_rule})
        base: dict[str, Any] = {"turn": turn, "llm_calls": llm_calls, "warnings": warnings, "trace": trace}
        if choice.action == ACTION_SEARCH:
            target = self._find_sub(subs, choice.target_qid)
            assert target is not None  # validate_choice·default_action이 있는 ID만 돌려줌
            return {**base, "next_action": "search", "current_qid": target.qid, "search_queries": [target.text],
                    "search_technique": "original", "route": NODE_S_R4}
        if choice.action == ACTION_TRANSFORM:
            return {**base, "next_action": "transform", "current_qid": choice.target_qid, "route": NODE_S_R6}
        return {**base, "next_action": "finish", **self._finish_collection(state, subs, choice.reason)}

    def _finish_collection(self, state: Mapping[str, Any], subs: list[SubQuestion], reason: str) -> dict[str, Any]:
        """수집 종료 후 B-2a 판정: 근거 0건 → 확인 필요 / 답변 끔 → 검색 결과 / 답변 켬 → 답변 생성."""

        closed = []
        for sq in subs:
            if sq.status == SUB_PENDING:
                closed.append(replace(sq, status=SUB_INSUFFICIENT, note=f"검색하지 못하고 수집 종료({reason})"))
            elif sq.status == SUB_UNCERTAIN:
                closed.append(replace(sq, status=SUB_INSUFFICIENT, note=f"불확실 결과만 있어 근거 부족({reason})"))
            else:
                closed.append(sq)
        if not state.get("evidence"):
            return {"sub_questions": closed, "status": STATUS_NEEDS_CONFIRMATION,
                    "finish_reason": f"근거 0건 — {reason}", "route": NODE_S_R9}
        if not state.get("generate_answer"):
            return {"sub_questions": closed, "status": STATUS_RETRIEVED,
                    "finish_reason": f"수집 종료 — {reason}", "route": NODE_S_R9}
        return {"sub_questions": closed, "finish_reason": f"수집 종료 — {reason}", "route": NODE_S_R7}

    # ------------------------------------------------------------ S-R4 문서 검색(search_docs)

    def s_r4(self, state: RetrieverState) -> dict[str, Any]:
        """낱말이 같은 문서와 뜻이 가까운 문서를 함께 찾아 볼 수 있는 조각 중 상위 top_k개를 추림.

        방법: 질의마다 벡터 40 + BM25 40 → 정규화 가중합 10 → 리랭크 top_k. 질의가 여럿이면
        Multi-Query는 같은 가중치 합, 그 밖(원 질문 + 변환 질의, 분해 질의)은 RRF로 합침.
        권한 필터는 검색기 안에서 순위 전에 붙고, 여기서 한 번 더 확인함(권한은 LLM이 바꿀 수 없음).
        """

        warnings = list(state.get("warnings") or [])
        if not self._can_start(state, S_R4):
            warnings.append("S-R4 남은 시간 예산 부족 → 수집 종료")
            return {"warnings": warnings, "route": NODE_S_R3}
        index = state["index"]
        top_k = int(state["top_k"])
        access = list(state["access_levels"])
        technique = str(state.get("search_technique") or "original")
        queries = [q for q in (state.get("search_queries") or []) if str(q).strip()]
        k_candidates = top_k * 2 * 4  # 반환 수 × 2(리랭킹 후보) × 4(하이브리드 후보) = 40 (설계 ⑥-4·⑥-5)
        k_fused = top_k * 2  # 리랭커에 넘길 융합 후보 10개(설계 ⑥-6)

        results: list[_QueryResult] = []
        reranked_all = True
        for query in queries:
            result = self._search_one(index, query, access, k_candidates, k_fused, top_k, warnings)
            if result is None:
                continue
            reranked_all = reranked_all and all(c.rerank_score is not None for c in result.candidates.values())
            results.append(result)

        fail_streak = 0 if results else int(state.get("search_fail_streak", 0)) + 1
        candidates, vector_ids, keyword_ids = self._merge_queries(results, technique, top_k)
        qid = str(state.get("current_qid") or "")
        qid_candidates = dict(state.get("qid_candidates") or {})
        qid_candidates[qid] = candidates
        trace = self._trace(state, {"step": S_R4, "qid": qid, "technique": technique, "queries": len(queries),
                                    "results": len(candidates), "reranked": bool(results) and reranked_all})
        return {"candidates": candidates, "vector_top_ids": vector_ids, "keyword_top_ids": keyword_ids,
                "qid_candidates": qid_candidates, "search_fail_streak": fail_streak, "warnings": warnings,
                "trace": trace, "route": NODE_S_R5}

    def _search_one(
        self, index: Any, query: str, access: list[str], k_candidates: int, k_fused: int, top_k: int,
        warnings: list[str],
    ) -> _QueryResult | None:
        """질의 1개를 검색함. 두 검색기가 모두 실패하면 None(검색 실패)을 돌려줌."""

        vector_hits = keyword_hits = None
        try:
            vector_hits = index.vector_search(query, access_levels=access, k=k_candidates)
        except Exception as error:  # 한쪽이 실패해도 남은 쪽으로 계속함(S-R4 예외 처리)
            warnings.append(f"벡터 검색 실패 → BM25만 사용: {type(error).__name__}")
        try:
            keyword_hits = index.keyword_search(query, access_levels=access, k=k_candidates)
        except Exception as error:
            warnings.append(f"BM25 검색 실패 → 벡터만 사용: {type(error).__name__}")
        if vector_hits is None and keyword_hits is None:
            warnings.append("벡터·BM25 모두 실패 → 결과 0건")
            return None
        vector_scores = {hit.chunk_id: float(hit.score) for hit in vector_hits or []}
        keyword_scores = {hit.chunk_id: float(hit.score) for hit in keyword_hits or []}
        fused = weighted_hybrid(vector_scores, keyword_scores, vector_weight=self.config.vector_weight,
                                keyword_weight=self.config.keyword_weight)
        fused_ids = rank_keys(fused, (vector_scores, keyword_scores))[:k_fused]
        chunks = index.get_chunks(fused_ids)
        allowed = set(access)
        leaked = [cid for cid in fused_ids if cid in chunks and chunks[cid].access_level not in allowed]
        if leaked:
            warnings.append(f"권한 밖 조각 {len(leaked)}건을 결과에서 제외")
        fused_ids = [cid for cid in fused_ids if cid in chunks and chunks[cid].access_level in allowed]

        rerank: dict[str, float] | None = None
        if fused_ids:
            try:
                # 순위 매기기는 임베딩·BM25와 같은 index_text로 읽힘. D2 84건은 본문(text)에 카드명이 없고 머리말에만
                # 있어서, text로 읽히면 어느 카드 조각인지 모름(실측: '모아생활 카드의 주요 혜택은?' 정답 조각
                # text 0.063 → index_text 0.917). 표시·인용 대조는 text만 씀(색인 계약 9)
                scores = self.reranker.score(query, [chunks[cid].index_text for cid in fused_ids])
                rerank = {cid: float(score) for cid, score in zip(fused_ids, scores, strict=True)}
            except Exception as error:
                warnings.append(f"리랭커 실패 → 융합 결과 사용: {type(error).__name__}")
        if rerank is not None:
            order = rank_keys(rerank, (fused,))[:top_k]
            main = {cid: rerank[cid] for cid in order}
        else:
            order = fused_ids[:top_k]
            main = {cid: fused[cid] for cid in order}
        candidates = {
            cid: Candidate(chunks[cid], vector_scores.get(cid), keyword_scores.get(cid), fused[cid],
                           None if rerank is None else rerank[cid])
            for cid in order
        }
        return _QueryResult(order, main, candidates, list(vector_scores), list(keyword_scores))

    def search_once(self, query: str, *, access_levels: Sequence[str], top_k: int = 5) -> list[Candidate]:
        """평가·진단용: 질의 1개를 S-R4와 같은 방식(벡터 + BM25 → 융합 → 리랭크)으로 검색해 상위 top_k를 반환함.

        목적: 채점 관문(S-R5)·LLM과 떼어 검색 품질만 따로 잴 수 있게 함(평가셋 Hit@5 등).
        반환값: 최종 순위 순서의 후보 목록. 두 검색기가 모두 실패하면 빈 목록임.
        예외: 쓸 수 있는 색인 세대가 없으면 IndexUnavailableError를 발생시킴.
        부수효과: 없음(읽기 전용). 감사 로그를 남기지 않음.
        """

        index = self.index_provider.acquire().index
        result = self._search_one(index, query, list(access_levels), top_k * 2 * 4, top_k * 2, top_k, [])
        return [] if result is None else [result.candidates[cid] for cid in result.order]

    @staticmethod
    def _merge_queries(
        results: Sequence[_QueryResult], technique: str, top_k: int
    ) -> tuple[list[Candidate], list[str], list[str]]:
        """질의별 결과를 하나의 순위로 합침(S-R4 ⑥). 검색기별 순위도 RRF로 합쳐 채점의 겹침 신호에 씀."""

        if not results:
            return [], [], []
        if len(results) == 1:
            only = results[0]
            return [only.candidates[cid] for cid in only.order], only.vector_ids, only.keyword_ids
        if technique == "multi":
            merged = equal_weight_merge([r.main_scores for r in results])
        else:
            merged = rrf_merge([r.order for r in results])
        final_ids = rank_keys(merged)[:top_k]
        candidates: list[Candidate] = []
        for cid in final_ids:
            # 같은 조각이 여러 질의에 나오면 리랭크 점수가 가장 높은 질의의 기록을 씀
            options = [r.candidates[cid] for r in results if cid in r.candidates]
            options.sort(key=lambda c: -1.0 if c.rerank_score is None else -c.rerank_score)
            candidates.append(options[0])
        vector_ids = rank_keys(rrf_merge([r.vector_ids for r in results]))
        keyword_ids = rank_keys(rrf_merge([r.keyword_ids for r in results]))
        return candidates, vector_ids, keyword_ids

    # ------------------------------------------------------------ S-R5 검색 결과 채점(grade_results)

    def s_r5(self, state: RetrieverState) -> dict[str, Any]:
        """LLM 없이 점수 규칙으로 정확·불확실·부정확을 판정하고 정확한 결과만 근거 묶음에 넣음.

        방법: 질문 핵심어(드문 명사·숫자·코드)를 고르고 판정 근거를 계산해 규칙으로 판정함(설계 ⑥-8).
        채점은 결정적 관문이라 에이전트가 고르지 않고 S-R4 다음에 항상 실행됨.
        """

        warnings = list(state.get("warnings") or [])
        subs: list[SubQuestion] = list(state.get("sub_questions") or [])
        qid = str(state.get("current_qid") or "")
        sub = self._find_sub(subs, qid)
        candidates = state.get("candidates")
        if sub is None or candidates is None:
            return self._error("broken_state", "채점할 질문 또는 검색 후보가 없습니다.", warnings)
        candidates = list(candidates)
        index = state["index"]
        signals = None
        if not self._can_start(state, S_R5):
            warnings.append("S-R5 남은 시간 예산 부족 → 불확실로 보고 진행")
            verdict = GRADE_UNCERTAIN
        else:
            try:
                # 핵심어 = 상품명(카드명·별칭 통일)·숫자·코드 중 드문 낱말(S-R5 ④ '핵심어(코드·상품명)', 사용자 결정
                # 2026-10-03). '주요'·'얼마' 같은 일반 명사는 결과에 없어도 관련성과 무관해 넣지 않음
                conditions = index.condition_terms(sub.text)
                key_terms = [term for term in index.keyword_candidates(sub.text) if term in conditions]
                keywords = select_rare_terms(
                    index.document_frequency(key_terms),
                    num_docs=index.num_docs(), max_df_ratio=self.config.keyword_max_df_ratio,
                )
                signals = build_signals(
                    candidates, keywords=keywords, result_terms=index.chunk_terms(c.chunk_id for c in candidates),
                    vector_top_ids=list(state.get("vector_top_ids") or []),
                    keyword_top_ids=list(state.get("keyword_top_ids") or []),
                    top_k=int(state["top_k"]), thresholds=self.config.thresholds,
                )
                verdict = grade(signals, self.config.thresholds)
            except Exception as error:  # 계산 실패는 불확실로 보고 진행(부분결과, S-R5 예외 처리)
                warnings.append(f"채점 계산 실패 → 불확실: {type(error).__name__}")
                verdict = GRADE_UNCERTAIN

        evidence: dict[str, EvidenceItem] = {k: {"candidate": v["candidate"], "qids": list(v["qids"])}
                                             for k, v in (state.get("evidence") or {}).items()}
        rankings = dict(state.get("evidence_rankings") or {})
        if verdict == GRADE_CORRECT:
            # 하한 미만 조각(다른 카드 등)은 근거·답변 재료에서 뺌(사용자 결정 2026-10-03)
            candidates = evidence_worthy(candidates, self.config.thresholds)
            for candidate in candidates:
                item = evidence.get(candidate.chunk_id)
                if item is None:
                    evidence[candidate.chunk_id] = {"candidate": candidate, "qids": [qid]}
                elif qid not in item["qids"]:
                    item["qids"].append(qid)  # 이미 넣은 조각은 다시 세지 않고 찾은 질문만 더함
            rankings[qid] = [c.chunk_id for c in candidates]
            subs = self._replace_sub(subs, qid, status=SUB_SATISFIED, evidence_count=len(candidates), note="")
        elif verdict == GRADE_INCORRECT:
            why = "검색 결과 0건" if not candidates else "주 점수가 하한 미달"
            subs = self._replace_sub(subs, qid, status=SUB_INSUFFICIENT, note=f"근거 부족 — {why}")
        elif sub.transform_count == 0:
            subs = self._replace_sub(subs, qid, status=SUB_UNCERTAIN, note="불확실 — 질문 변환 대상")
        else:
            # 재검색 후에도 불확실이면 LLM 판정을 더하지 않고 근거 부족으로 끝냄(설계 ⑥-1 사용자 결정)
            subs = self._replace_sub(subs, qid, status=SUB_INSUFFICIENT, note="질문 변환 후에도 불확실 — 근거 부족")

        grade_signals = dict(state.get("grade_signals") or {})
        grade_signals[qid] = {"grade": verdict, **(signals.as_dict() if signals else {})}
        trace = self._trace(state, {"step": S_R5, "qid": qid, "grade": verdict,
                                    "signals": grade_signals[qid]})
        return {"grade": verdict, "grade_signals": grade_signals, "sub_questions": subs, "evidence": evidence,
                "evidence_rankings": rankings, "warnings": warnings, "trace": trace, "route": NODE_S_R3}

    # ------------------------------------------------------------ S-R6 질문 변환(transform_query, B-3)

    def s_r6(self, state: RetrieverState) -> dict[str, Any]:
        """애매하게 찾아진 질문을 실패 원인에 맞는 기법으로 다듬어 한 번 더 찾게 하거나 사용자에게 되물음.

        방법: '대상명 없음 + 대상 섞임'이면 C-03 없이 clarify. 아니면 C-03이 기법·질의를 내고 금지 규칙이 확정함.
        C-03 실패·시간 부족·호출 상한이면 keep(원 질문 결과 유지). 어느 경우든 그 질문은 다시 변환하지 않음.
        """

        warnings = list(state.get("warnings") or [])
        subs: list[SubQuestion] = list(state.get("sub_questions") or [])
        qid = str(state.get("current_qid") or "")
        sub = self._find_sub(subs, qid)
        if sub is None:
            return self._error("broken_state", "변환할 질문이 없습니다.", warnings)
        index = state["index"]
        llm_calls = int(state.get("llm_calls", 0))
        history = list(state.get("transform_history") or [])
        candidates: list[Candidate] = list((state.get("qid_candidates") or {}).get(qid, []))
        decision: TransformDecision
        if not self._can_start(state, S_R6):
            decision = TransformDecision(KEEP, reason="남은 시간 예산 부족 → keep")
        elif self._llm_exhausted(state):
            decision = TransformDecision(KEEP, reason="LLM 호출 상한 → keep")
        else:
            forced = mixed_target_clarify(
                question_has_target=bool(index.target_terms(sub.text) or index.target_terms(str(state["query"]))),
                result_card_ids=[c.chunk.source.card_id or "" for c in candidates],
                result_card_names=[c.chunk.source.card_name or "" for c in candidates],
            )
            if forced:
                decision = apply_transform_rules(
                    technique=CLARIFY, queries=(), include_original=False, clarify_question="", reason="서버 규칙",
                    target_question=sub.text, previous_queries=(), tokens_of=index.tokens, forced_clarify=forced,
                )
            else:
                payload = TransformInput(
                    original_question=str(state["query"]),
                    target_sub_question=sub.text,
                    result_chunks=tuple(
                        {"chunk_id": c.chunk_id, "title": c.chunk.source.title,
                         "text": c.chunk.text[: self.config.prompt_chunk_chars]}
                        for c in candidates[: self.config.prompt_chunk_count]
                    ),
                    grading_evidence=dict((state.get("grade_signals") or {}).get(qid, {})),
                    previous_attempts=tuple(
                        {"technique": h["technique"], "queries": h["queries"]} for h in history
                    ),
                    technique_guide=TECHNIQUE_GUIDE,
                    allowed_techniques=ALLOWED_TECHNIQUES,
                )
                result, llm_calls = self._call_llm(
                    state, step_id=S_R6, connector_id=C_03, call=lambda: self.llm.transform_query(payload),
                    fallback="keep(원 질문 결과 유지)", warnings=warnings,
                )
                if result is None:
                    decision = TransformDecision(KEEP, reason="C-03 응답 없음 → keep")
                else:
                    decision = apply_transform_rules(
                        technique=result.technique, queries=result.queries,
                        include_original=result.include_original_query, clarify_question=result.clarify_question,
                        reason=result.reason, target_question=sub.text,
                        previous_queries=[q for h in history for q in h["queries"]],
                        tokens_of=index.tokens, forced_clarify=None,
                    )
        warnings.extend(decision.warnings)
        history.append({"qid": qid, "technique": decision.technique, "queries": list(decision.queries),
                        "include_original": decision.include_original, "reason": decision.reason})
        subs = self._replace_sub(subs, qid, transform_count=1)
        trace = self._trace(state, {"step": S_R6, "qid": qid, "technique": decision.technique,
                                    "queries": len(decision.queries), "reason": decision.reason})
        base: dict[str, Any] = {"llm_calls": llm_calls, "transform_history": history, "warnings": warnings,
                                "trace": trace}
        if decision.technique == KEEP:
            subs = self._replace_sub(subs, qid, status=SUB_INSUFFICIENT, note="질문 변환 없음(keep) — 근거 부족")
            return {**base, "sub_questions": subs, "route": NODE_S_R3}
        if decision.technique == CLARIFY:
            subs = self._replace_sub(subs, qid, status=SUB_INSUFFICIENT, note="대상이 불분명해 확인 질문으로 되물음")
            return {**base, "sub_questions": subs, "clarify_question": decision.clarify_question,
                    "status": STATUS_NEEDS_CONFIRMATION, "finish_reason": "대상 확인 필요(clarify)",
                    "route": NODE_S_R9}
        queries = ([sub.text] if decision.include_original else []) + list(decision.queries)
        return {**base, "sub_questions": subs, "search_queries": queries, "search_technique": decision.technique,
                "route": NODE_S_R4}

    # ------------------------------------------------------------ S-R7 답변 생성(옵션, B-5)

    def s_r7(self, state: RetrieverState) -> dict[str, Any]:
        """모은 근거만으로 문장마다 출처가 달린 답을 만듦.

        방법: 근거 묶음을 C-04에 넘기고, 재작성이면 직전 검증 실패 사유를 함께 넘김.
        시간 부족·호출 상한·C-04 실패면 답변 없이 근거 목록만 반환함(답변 생성 실패).
        """

        warnings = list(state.get("warnings") or [])
        rewrite_count = int(state.get("rewrite_count", 0))
        llm_calls = int(state.get("llm_calls", 0))
        if not self._can_start(state, S_R7) or self._llm_exhausted(state):
            reason = "남은 시간 예산 부족" if not self._can_start(state, S_R7) else "LLM 호출 상한"
            return {"status": STATUS_ANSWER_FAILED, "finish_reason": f"답변 생성 못 함 — {reason}",
                    "warnings": warnings, "route": NODE_S_R9}
        subs: list[SubQuestion] = list(state.get("sub_questions") or [])
        payload = AnswerInput(
            original_question=str(state["query"]),
            sub_questions=tuple({"id": sq.qid, "question": sq.text, "satisfied": sq.status == SUB_SATISFIED}
                                for sq in subs),
            evidence_chunks=tuple(
                {"chunk_id": c.chunk_id, "title": c.chunk.source.title, "text": c.chunk.text}
                for c in self._ordered_evidence(state)
            ),
            rewrite_reason="\n".join(state.get("verify_failures") or []) if rewrite_count else "",
            attempt_no=rewrite_count + 1,
        )
        result, llm_calls = self._call_llm(
            state, step_id=S_R7, connector_id=C_04, call=lambda: self.llm.generate_answer(payload),
            fallback="근거 목록만 반환", warnings=warnings,
        )
        trace = self._trace(state, {"step": S_R7, "attempt": rewrite_count + 1, "ok": result is not None})
        if result is None:
            return {"llm_calls": llm_calls, "status": STATUS_ANSWER_FAILED, "finish_reason": "답변 생성 실패(C-04)",
                    "warnings": warnings, "trace": trace, "route": NODE_S_R9}
        known = {sq.qid for sq in subs}
        return {"llm_calls": llm_calls, "answer_draft": list(result.sentences),
                "answer_unresolved": [q for q in result.unresolved_sub_questions if q in known],
                "confirmation_note": result.needs_confirmation_note, "warnings": warnings, "trace": trace,
                "route": NODE_S_R8}

    # ------------------------------------------------------------ S-R8 근거 검증(verify_evidence, B-4)

    def s_r8(self, state: RetrieverState) -> dict[str, Any]:
        """답의 인용이 근거 본문(text)과 글자 그대로 맞는지 규칙으로 확인함.

        방법: 통과 → 답변 완료. 실패이고 재작성 2회 미만·시간 여유 있음 → 사유를 주고 S-R7. 그 밖 → 확인 필요.
        검증하지 못한 답은 틀린 인용을 담을 수 있어 부분결과로 내보내지 않음.
        """

        warnings = list(state.get("warnings") or [])
        rewrite_count = int(state.get("rewrite_count", 0))
        evidence_texts = {cid: item["candidate"].chunk.text for cid, item in (state.get("evidence") or {}).items()}
        try:
            failures = verify_answer(list(state.get("answer_draft") or []), evidence_texts)
        except Exception as error:  # 검증 오류는 안전 종료(S-R8 예외 처리)
            warnings.append(f"근거 검증 오류 → 확인 필요: {type(error).__name__}")
            return {"status": STATUS_NEEDS_CONFIRMATION, "finish_reason": "근거 검증 오류", "warnings": warnings,
                    "route": NODE_S_R9}
        trace = self._trace(state, {"step": S_R8, "passed": not failures, "failures": len(failures),
                                    "rewrite_count": rewrite_count})
        if not failures:
            return {"status": STATUS_ANSWERED, "verify_failures": [], "finish_reason": "근거 검증 통과",
                    "trace": trace, "route": NODE_S_R9}
        if rewrite_count < self.config.budget.max_rewrites and self._can_start(state, S_R8):
            return {"rewrite_count": rewrite_count + 1, "verify_failures": failures, "trace": trace,
                    "route": NODE_S_R7}
        why = "재작성 소진" if rewrite_count >= self.config.budget.max_rewrites else "남은 시간 예산 부족"
        return {"status": STATUS_NEEDS_CONFIRMATION, "verify_failures": failures,
                "finish_reason": f"근거 검증 실패 — {why}", "trace": trace, "route": NODE_S_R9}

    # ------------------------------------------------------------ S-R9 결과 응답

    def _ordered_evidence(self, state: Mapping[str, Any]) -> list[Candidate]:
        """근거 목록을 정렬함. 하위 질문이 여럿이면 질문별 순위를 RRF로 합침(점수 분포가 달라 점수로 더하지 않음)."""

        evidence: Mapping[str, EvidenceItem] = state.get("evidence") or {}
        rankings = [ids for ids in (state.get("evidence_rankings") or {}).values() if ids]
        if not evidence:
            return []
        if len(rankings) == 1:
            order = [cid for cid in rankings[0] if cid in evidence]
        else:
            order = [cid for cid in rank_keys(rrf_merge(rankings)) if cid in evidence]
        order += [cid for cid in evidence if cid not in order]
        return [evidence[cid]["candidate"] for cid in order]

    def s_r9(self, state: RetrieverState) -> dict[str, Any]:
        """화면이 바로 보여 줄 수 있게 상태·답·근거·출처를 한 번에 담고, 판단 과정을 감사 로그로 남김.

        반환값: response 키에 SearchResponse 모양의 dict를 담아 돌려주고 실행을 끝냄(route = 끝).
        부수효과: 감사 로그 1건(질문 원문 대신 해시와 앞 20자만).
        """

        status = str(state.get("status") or STATUS_ERROR)
        if status == "running":
            status = STATUS_ERROR  # 정상 흐름에서는 생기지 않음. 상태를 정하지 못한 채 끝나면 오류로 봄
        evidence: Mapping[str, EvidenceItem] = state.get("evidence") or {}
        evidence_out: list[dict[str, Any]] = []
        if status in _STATUSES_WITH_EVIDENCE:
            for rank, candidate in enumerate(self._ordered_evidence(state), start=1):
                source = candidate.chunk.source
                evidence_out.append({
                    "rank": rank, "chunk_id": candidate.chunk_id, "text": candidate.chunk.text,
                    "source": source.source, "doc_key": source.doc_key, "page": source.page,
                    "page_end": source.page_end, "clause_no": source.clause_no, "card_id": source.card_id,
                    "card_name": source.card_name, "benefit_id": source.benefit_id,
                    "section_label": source.section_label,
                    "sub_question_ids": list(evidence[candidate.chunk_id]["qids"]),
                    "scores": {"vector": candidate.vector_score, "bm25": candidate.bm25_score,
                               "fused": candidate.fused_score, "rerank": candidate.rerank_score},
                })

        subs: list[SubQuestion] = list(state.get("sub_questions") or [])
        unresolved = [
            {"sub_question_id": sq.qid, "question": sq.text, "reason": sq.note or "근거를 찾지 못함"}
            for sq in subs if sq.status != SUB_SATISFIED
        ]
        answer = None
        if status == STATUS_ANSWERED:
            answer = [{"text": s.text, "citations": [{"chunk_id": c.chunk_id, "quote": c.quote} for c in s.citations]}
                      for s in state.get("answer_draft") or []]
            listed = {item["sub_question_id"] for item in unresolved}
            for qid in state.get("answer_unresolved") or []:
                sub = self._find_sub(subs, qid)
                if sub is not None and qid not in listed:
                    unresolved.append({"sub_question_id": qid, "question": sub.text,
                                       "reason": "근거는 있으나 답변에서 확인하지 못함"})

        response = {
            "request_id": state.get("request_id"),
            "status": status,
            "message": self._message(state, status, unresolved),
            "answer": answer,
            "evidence": evidence_out,
            "unresolved": unresolved if status != STATUS_NO_RETRIEVAL and status != STATUS_ERROR else [],
            "clarify_question": str(state.get("clarify_question") or ""),
            "question_type": state.get("question_type"),
            "generation": state.get("generation"),
            "llm_calls": int(state.get("llm_calls", 0)),
            "timings": dict(state.get("timings") or {}),
            "warnings": list(state.get("warnings") or []),
            "finish_reason": str(state.get("finish_reason") or ""),
            "error_code": state.get("error_code"),
        }
        self._write_audit(state, response)
        return {"status": status, "response": response, "route": NODE_END}

    @staticmethod
    def _message(state: Mapping[str, Any], status: str, unresolved: Sequence[Mapping[str, Any]]) -> str:
        """응답 상태별 안내문을 만듦. 문서 내용은 담지 않음."""

        if status == STATUS_NO_RETRIEVAL:
            return str(state.get("chitchat_reply") or "")
        if status == STATUS_ERROR:
            return str(state.get("error_message") or "요청을 처리하지 못했습니다.")
        if status == STATUS_ANSWER_FAILED:
            return "답변을 만들지 못해 찾은 근거 목록만 제공합니다."
        if status == STATUS_NEEDS_CONFIRMATION:
            note = str(state.get("confirmation_note") or "")
            if state.get("clarify_question"):
                return "질문 대상을 확인할 수 없어 되묻습니다."
            if state.get("verify_failures"):
                return "답변의 인용을 근거 원문과 맞추지 못해 확인이 필요합니다. 찾은 근거 목록을 참고하세요."
            if note:
                return note
            names = ", ".join(item["question"] for item in unresolved) or "질문"
            return f"근거를 찾지 못해 확인이 필요합니다: {names}"
        if unresolved:
            return f"일부 질문은 근거를 찾지 못했습니다: {', '.join(item['question'] for item in unresolved)}"
        return ""

    def _write_audit(self, state: Mapping[str, Any], response: Mapping[str, Any]) -> None:
        """감사 로그 1건을 남김. 질문 원문은 남기지 않고 해시와 앞 20자만 기록함(설계 ③ 로그 규칙)."""

        query = str(state.get("query") or "")
        self.audit_log.write({
            "type": "request",
            "request_id": state.get("request_id"),
            "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest()[:16],
            "query_head": query[:20],
            "role": state.get("role"),
            "generation": state.get("generation"),
            "status": response["status"],
            "finish_reason": response["finish_reason"],
            "question_type": state.get("question_type"),
            "turns": int(state.get("turn", 0)),
            "llm_calls": int(state.get("llm_calls", 0)),
            "rewrite_count": int(state.get("rewrite_count", 0)),
            "trace": list(state.get("trace") or []),
            "grade_signals": dict(state.get("grade_signals") or {}),
            "transform_history": list(state.get("transform_history") or []),
            "verify_failures": list(state.get("verify_failures") or []),
            "evidence_ids": [item["chunk_id"] for item in response["evidence"]],
            "warnings": list(state.get("warnings") or []),
            "timings": dict(state.get("timings") or {}),
        })
