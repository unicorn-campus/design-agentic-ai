from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from .analytics_view import AnalyticsViewConnector
from .crm import CrmConnector
from .errors import ApprovalRequired
from .idempotency import IdempotencyStore
from .llm_api import LlmApiConnector
from .official_search import OfficialSearchConnector
from .resilience import ConnectorGuards, RetryPolicy, execute_with_resilience
from .schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
    ApprovalProof,
    CrmRequest,
    CrmResponse,
    LlmRequest,
    LlmResponse,
    SearchRequest,
    SearchResponse,
    SurveyRequest,
    SurveyResponse,
    ToolDefinition,
)
from .survey import SurveyConnector


ResponseGuard = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class InvocationPolicy:
    timeout_ms: int
    retry: RetryPolicy
    guards: ConnectorGuards


class ExternalTools:
    def __init__(
        self,
        *,
        llm: LlmApiConnector,
        analytics: AnalyticsViewConnector,
        search: OfficialSearchConnector,
        crm: CrmConnector,
        survey: SurveyConnector,
        idempotency: IdempotencyStore,
        response_guard: ResponseGuard,
    ) -> None:
        self.llm = llm
        self.analytics = analytics
        self.search = search
        self.crm = crm
        self.survey = survey
        self.idempotency = idempotency
        self.response_guard = response_guard

    async def call_llm(
        self,
        request: LlmRequest,
        *,
        stage_id: str,
        policy: InvocationPolicy,
        acting_user_ref: str | None = None,
    ) -> LlmResponse:
        response = await execute_with_resilience(
            lambda: self.llm.invoke(request, acting_user_ref=acting_user_ref),
            timeout_ms=policy.timeout_ms,
            retry=policy.retry,
            guards=policy.guards,
        )
        return LlmResponse.model_validate(
            self.response_guard(stage_id, response.model_dump(mode="json"))
        )

    async def query_analytics(
        self,
        request: AnalyticsRequest,
        *,
        stage_id: str,
        policy: InvocationPolicy,
        acting_user_ref: str | None = None,
    ) -> AnalyticsResponse:
        response = await execute_with_resilience(
            lambda: self.analytics.query(request, acting_user_ref=acting_user_ref),
            timeout_ms=policy.timeout_ms,
            retry=policy.retry,
            guards=policy.guards,
        )
        return AnalyticsResponse.model_validate(
            self.response_guard(stage_id, response.model_dump(mode="json"))
        )

    async def search_official(
        self,
        request: SearchRequest,
        *,
        stage_id: str,
        policy: InvocationPolicy,
        acting_user_ref: str | None = None,
    ) -> SearchResponse:
        response = await execute_with_resilience(
            lambda: self.search.search(request, acting_user_ref=acting_user_ref),
            timeout_ms=policy.timeout_ms,
            retry=policy.retry,
            guards=policy.guards,
        )
        return SearchResponse.model_validate(
            self.response_guard(stage_id, response.model_dump(mode="json"))
        )

    async def save_crm(
        self,
        request: CrmRequest,
        *,
        proof: ApprovalProof | None,
        policy: InvocationPolicy,
        acting_user_ref: str | None = None,
    ) -> CrmResponse:
        self._require_approval(
            proof,
            "S-E6",
            request.approval_id,
            "R-H3 상담 후처리 검토·감사자",
        )
        cached = self.idempotency.get(request.idempotency_key)
        if cached is not None:
            return CrmResponse.model_validate(cached)
        response = await execute_with_resilience(
            lambda: self.crm.save(request, acting_user_ref=acting_user_ref),
            timeout_ms=policy.timeout_ms,
            retry=policy.retry,
            guards=policy.guards,
        )
        self.idempotency.put(request.idempotency_key, response.model_dump(mode="json"))
        return response

    async def send_survey(
        self,
        request: SurveyRequest,
        *,
        proof: ApprovalProof | None,
        policy: InvocationPolicy,
        acting_user_ref: str | None = None,
    ) -> SurveyResponse:
        self._require_approval(
            proof,
            "S-E7",
            proof.approval_id if proof else None,
            "R-H4 설문 수신 동의 통제자",
        )
        cached = self.idempotency.get(request.idempotency_key)
        if cached is not None:
            return SurveyResponse.model_validate(cached)
        response = await execute_with_resilience(
            lambda: self.survey.send(request, acting_user_ref=acting_user_ref),
            timeout_ms=policy.timeout_ms,
            retry=policy.retry,
            guards=policy.guards,
            irreversible=True,
        )
        self.idempotency.put(request.idempotency_key, response.model_dump(mode="json"))
        return response

    @staticmethod
    def _require_approval(
        proof: ApprovalProof | None,
        subject: str,
        expected_approval_id: str | None,
        expected_approver_role: str,
    ) -> None:
        if proof is None:
            raise ApprovalRequired("승인 표시가 없어 기본 거부함")
        if proof.subject != subject or proof.approval_id != expected_approval_id:
            raise ApprovalRequired("승인 대상 또는 승인 ID가 다름")
        if proof.approver_role != expected_approver_role:
            raise ApprovalRequired("승인자 역할이 다름")


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema()


TOOL_DEFINITIONS = (
    ToolDefinition(
        name="상용 LLM API",
        side_effect="읽기",
        use_when="문의 해석, SQL 후보, 근거 작성, 요약 초안이 필요할 때 사용함",
        connector_id="C-A1",
        approval_required=False,
        input_schema=_schema(LlmRequest),
        output_schema=_schema(LlmResponse),
    ),
    ToolDefinition(
        name="상담·거래 분석 뷰",
        side_effect="읽기",
        use_when="검사 완료 SQL로 허용된 상담·거래 결과를 조회할 때 사용함",
        connector_id="C-A2",
        approval_required=False,
        input_schema=_schema(AnalyticsRequest),
        output_schema=_schema(AnalyticsResponse),
    ),
    ToolDefinition(
        name="공식 웹·영상",
        side_effect="읽기",
        use_when="비식별 검색어로 공식 외부 근거를 확인할 때 사용함",
        connector_id="C-A3",
        approval_required=False,
        input_schema=_schema(SearchRequest),
        output_schema=_schema(SearchResponse),
    ),
    ToolDefinition(
        name="CRM",
        side_effect="쓰기(되돌림 가능)",
        use_when="사람이 승인한 마스킹 상담 요약을 멱등 저장할 때 사용함",
        connector_id="C-A4",
        approval_required=True,
        input_schema=_schema(CrmRequest),
        output_schema=_schema(CrmResponse),
    ),
    ToolDefinition(
        name="설문 시스템",
        side_effect="쓰기(되돌림 불가)",
        use_when=(
            "수신 동의와 사람 승인이 있는 고객에게 "
            "설문 링크를 한 번 발송할 때 사용함"
        ),
        connector_id="C-A5",
        approval_required=True,
        input_schema=_schema(SurveyRequest),
        output_schema=_schema(SurveyResponse),
    ),
)
