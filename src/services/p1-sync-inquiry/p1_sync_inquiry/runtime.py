"""W-1 조립 루트.

설정에서 시작해 커넥터·도구·담당자·그래프를 한 줄로 엮어 실행 가능한
런타임을 만듦. `api.py`는 이 모듈이 만든 실행기만 호출함.

바깥 호출 상한과 차단기는 ⑥ 가드레일 정책 1벌에서 읽어 워크플로우 1건마다
새로 만듦. 상한이 요청 사이에 새는 것을 막기 위함임.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from help_desk_api import GuardrailBoundary
from help_desk_guardrails import (
    CircuitBreaker,
    GuardrailPolicy,
    InputGuard,
    InvocationLimiter,
    SensitiveDataMasker,
    load_policy,
    retry_delays,
)
from help_desk_runtime.api_contracts import InquiryRequest, InquiryResponse
from help_desk_runtime.budget import RuntimeDeadline
from help_desk_runtime.checkpoint import build_thread_id
from help_desk_runtime.model import ModelClientAdapter
from help_desk_runtime.settings import RuntimeSettings
from help_desk_tools import (
    ConnectorSettings,
    ExternalTools,
    InvocationPolicy,
    MemoryIdempotencyStore,
    MockAnalyticsViewConnector,
    MockCrmConnector,
    MockLlmApiConnector,
    MockOfficialSearchConnector,
    MockSurveyConnector,
    RetryPolicy,
)
from help_desk_tools.resilience import ConnectorGuards
from help_desk_tools.schemas import (
    AnalyticsResponse,
    CrmResponse,
    LlmResponse,
    LlmUsage,
    SearchResponse,
    SearchResult,
    SurveyResponse,
)
from help_desk_workflow import LocalStubModelInvoker, ModelAdapterInvoker
from help_desk_guardrails.approval import ApprovalGate
from help_desk_workflow.contracts import WorkflowDependencies

from .operations import InquiryOperations, derive_customer_ref
from .workflow import (
    WORKFLOW_ID,
    build_customer_inquiry_graph,
    resume_customer_inquiry,
    run_customer_inquiry,
)

WORKFLOW_CONNECTORS = ("C-A1", "C-A2", "C-A3")

#: ③ `max_iter`에서 옮긴 W-1 재시도 상한임.
MAX_ITERATIONS = {"R-1": 1}

#: 재시도는 커넥터 1계층만 둠. 출처는 `src/tools/README.md` 적용 결정 1행.
CONNECTOR_RETRY_COUNT = 1

#: S-R4 조회 행 수 상한 기본값. 설정에 값이 없을 때만 씀. 출처는 ⑤ 정형 접근 경로 1행.
DEFAULT_S_R4_MAX_ROWS = 100

#: 커넥터 대역이 돌려줄 고정 응답. ② 신뢰경계표에서 5종 전부 `Yes(Mock)`으로 확정됨.
MOCK_ANALYTICS = AnalyticsResponse(
    query_id="mock-query-1",
    rows=[
        {
            "masked_customer_id": "cust-a1",
            "transaction_date": "2026-08-20",
            "transaction_status": "declined",
            "decline_reason_code": "LIMIT_EXCEEDED",
        },
        {
            "masked_customer_id": "cust-a1",
            "transaction_date": "2026-08-21",
            "transaction_status": "approved",
            "decline_reason_code": "NONE",
        },
    ],
    row_count=2,
)
MOCK_SEARCH = SearchResponse(
    results=[
        SearchResult(
            title="카드 이용 안내 - 공식 고객센터",
            url="https://example-card.test/guide",
            retrieved_at="2026-08-26T00:00:00+00:00",
            content_excerpt="한도 초과 시 승인이 거절될 수 있음",
        )
    ]
)
MOCK_LLM = LlmResponse(
    id="mock-llm-1",
    output_text="{}",
    usage=LlmUsage(total_tokens=0),
)
MOCK_CRM = CrmResponse(record_id="mock-crm-1", status="saved")
MOCK_SURVEY = SurveyResponse(send_id="mock-survey-1", status="sent")


def build_invocation_policies(
    policy: GuardrailPolicy,
    workflow_id: str,
    jitter_ratio: float,
    timeout_ms: int,
) -> dict[str, InvocationPolicy]:
    """⑥ 정책의 호출 상한·차단기를 커넥터별 호출 규칙으로 바꿈."""
    limits = {
        row.model_extra["target"]: row
        for row in policy.connector_limits
        if row.workflow == workflow_id
    }
    breakers = {
        row.model_extra["target"]: row
        for row in policy.circuit_breakers
        if row.workflow == workflow_id
    }
    policies: dict[str, InvocationPolicy] = {}
    for connector_id in WORKFLOW_CONNECTORS:
        limit = limits[connector_id]
        breaker = breakers[connector_id]
        interval = limit.model_extra["retry_interval"]
        policies[connector_id] = InvocationPolicy(
            timeout_ms=timeout_ms,
            retry=RetryPolicy(
                retry_count=CONNECTOR_RETRY_COUNT,
                # `execute_with_resilience`가 시도마다 지연을 하나씩 꺼내므로
                # 시도 횟수와 같은 수의 지연 값을 만들어 둠.
                delays_ms=retry_delays(interval, CONNECTOR_RETRY_COUNT + 1),
                jitter_ratio=jitter_ratio,
            ),
            guards=ConnectorGuards(
                limiter=InvocationLimiter(
                    concurrent_limit=int(limit.model_extra["concurrent"]),
                    call_limit=int(limit.model_extra["calls"]),
                ),
                circuit_breaker=CircuitBreaker(
                    failure_threshold=int(breaker.model_extra["failures"]),
                    open_seconds=float(breaker.model_extra["open_seconds"]),
                    fallback=str(breaker.model_extra["fallback"]),
                ),
            ),
        )
    return policies


def build_approval_payload(
    request_id: str, decision: dict[str, Any]
) -> dict[str, Any]:
    """사람 결정을 S-R9 재진입 값으로 바꿈.

    R-H1 승인자는 `approval_id`로 승인 표시를 확인하고, S-R10은
    `approval_result`를 보고 전달 여부를 정함. 두 값을 여기서 함께 채움.
    """
    result: dict[str, Any] = {
        "decision": str(decision["decision"]),
        "reviewer_ref": str(decision["reviewer_ref"]),
    }
    revised = decision.get("revised_answer")
    if isinstance(revised, dict) and revised:
        result["revised_answer"] = revised
    return {
        "approval_id": str(decision.get("approval_id") or f"{request_id}:S-R9"),
        "approval_result": result,
    }


class ResponseGuard:
    """바깥 응답을 신뢰하지 않는 데이터로 보고 설계된 시점마다 검사함."""

    STAGE_RULES = {"S-R4": "IN-W1-R4", "S-R6": "IN-W1-R6"}

    def __init__(self, guard: InputGuard) -> None:
        self._guard = guard

    def __call__(self, stage_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rule_id = self.STAGE_RULES.get(stage_id)
        if rule_id is None:
            return payload
        decision = self._guard.inspect(rule_id, payload, "받는 즉시")
        if decision.accepted:
            return payload
        raise ValueError(f"{rule_id} 위반: {', '.join(decision.violations)}")


@dataclass(frozen=True)
class RuntimeContext:
    """요청 1건이 쓰는 상한·도구·담당자 묶음."""

    dependencies: WorkflowDependencies
    graph: Any


class InquiryRuntime:
    """W-1 실행기. API 계층은 `run`과 `resume`만 씀."""

    def __init__(
        self,
        settings: RuntimeSettings,
        connector_settings: ConnectorSettings,
        boundary: GuardrailBoundary,
        checkpointer: Any,
        policy: GuardrailPolicy | None = None,
    ) -> None:
        self._settings = settings
        self._connector_settings = connector_settings
        self._boundary = boundary
        self._checkpointer = checkpointer
        self._policy = policy or load_policy()
        self._salt = settings.masking_salt.get_secret_value()
        self._masker = SensitiveDataMasker(self._salt, policy=self._policy)
        self._input_guard = InputGuard(self._policy)
        self._response_guard = ResponseGuard(self._input_guard)
        self._model_invoke = self._build_model_invoker()
        self._threads: dict[str, str] = {}

    def _build_model_invoker(self) -> Any:
        if self._settings.llm_provider.strip().lower() == "local":
            return LocalStubModelInvoker()
        return ModelAdapterInvoker(ModelClientAdapter(self._settings))

    def _build_tools(self, timeout_ms: int) -> tuple[ExternalTools, Mapping[str, InvocationPolicy]]:
        if self._connector_settings.connector_mode != "mock":
            raise RuntimeError(
                "실물 커넥터 조립은 아직 없음: HELP_DESK_CONNECTOR_MODE=mock으로 실행함"
            )
        tools = ExternalTools(
            llm=MockLlmApiConnector(MOCK_LLM),
            analytics=MockAnalyticsViewConnector(MOCK_ANALYTICS),
            search=MockOfficialSearchConnector(MOCK_SEARCH),
            crm=MockCrmConnector(MOCK_CRM),
            survey=MockSurveyConnector(MOCK_SURVEY),
            idempotency=MemoryIdempotencyStore(
                timedelta(seconds=self._connector_settings.idempotency_ttl_seconds)
            ),
            response_guard=self._response_guard,
        )
        policies = build_invocation_policies(
            self._policy,
            WORKFLOW_ID,
            self._connector_settings.connector_jitter_ratio,
            timeout_ms,
        )
        return tools, policies

    def _context(self, deadline: RuntimeDeadline) -> RuntimeContext:
        timeout_ms = max(1, min(deadline.remaining_ms(), 30_000))
        tools, policies = self._build_tools(timeout_ms)
        operations = InquiryOperations(
            tools=tools,
            input_guard=self._input_guard,
            masker=self._masker,
            masking_salt=self._salt,
            policies=policies,
            max_rows=self._settings.dataset_s_r4_max_rows or DEFAULT_S_R4_MAX_ROWS,
        )
        dependencies = WorkflowDependencies(
            settings=self._settings,
            deadline=deadline,
            operations=operations.as_mapping(),
            model_invoke=self._model_invoke,
            approval_gate=ApprovalGate(self._policy),
            max_iterations=MAX_ITERATIONS,
        )
        return RuntimeContext(
            dependencies=dependencies,
            graph=build_customer_inquiry_graph(dependencies, self._checkpointer),
        )

    async def run(
        self, request: InquiryRequest, deadline: RuntimeDeadline
    ) -> InquiryResponse:
        customer_ref = derive_customer_ref(request["auth_session_ref"], self._salt)
        thread_id = build_thread_id(
            WORKFLOW_ID,
            customer_ref=customer_ref,
            request_id=request["request_id"],
        )
        self._threads[request["request_id"]] = thread_id
        context = self._context(deadline)
        return await run_customer_inquiry(context.graph, request, customer_ref)

    async def resume(
        self, request_id: str, decision: dict[str, Any]
    ) -> InquiryResponse:
        thread_id = self._threads.get(request_id)
        if thread_id is None:
            raise KeyError(f"승인 대기 중인 요청이 없음: {request_id}")
        deadline = RuntimeDeadline.from_budget_ms(self._settings.w1_total_budget_ms)
        context = self._context(deadline)
        return await resume_customer_inquiry(
            context.graph, thread_id, build_approval_payload(request_id, decision)
        )

    async def ready(self) -> bool:
        """조립이 끝났고 체크포인트 저장소에 접근할 수 있으면 준비 완료임."""
        try:
            await self._checkpointer.aget_tuple(
                {"configurable": {"thread_id": "health:ready"}}
            )
        except Exception:  # noqa: BLE001 - 준비 실패 사유는 상태 경로로만 알림
            return False
        return True
