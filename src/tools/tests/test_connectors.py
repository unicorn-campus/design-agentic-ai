from __future__ import annotations

import asyncio
from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError

from help_desk_tools.analytics_view import HttpAnalyticsViewConnector, MockAnalyticsViewConnector
from help_desk_tools.auth import AuthenticationManager
from help_desk_tools.crm import HttpCrmConnector, MockCrmConnector
from help_desk_tools.errors import ApprovalRequired, ConnectorError, ErrorCategory
from help_desk_tools.idempotency import MemoryIdempotencyStore, build_idempotency_key
from help_desk_tools.llm_api import HttpLlmApiConnector, MockLlmApiConnector
from help_desk_tools.official_search import HttpOfficialSearchConnector, MockOfficialSearchConnector
from help_desk_tools.resilience import ConnectorGuards, RetryPolicy
from help_desk_tools.schemas import (
    AnalyticsRequest,
    AnalyticsResponse,
    ApprovalProof,
    CrmRequest,
    CrmResponse,
    LlmRequest,
    LlmResponse,
    LlmUsage,
    SearchRequest,
    SearchResponse,
    SurveyRequest,
    SurveyResponse,
)
from help_desk_tools.survey import HttpSurveyConnector, MockSurveyConnector
from help_desk_tools.tools import ExternalTools, InvocationPolicy, TOOL_DEFINITIONS


class _CredentialProvider:
    def __init__(self) -> None:
        self.refreshes = 0
        self.expiring = False

    async def should_refresh(self, acting_user_ref: str | None) -> bool:
        return self.expiring

    async def refresh(self, acting_user_ref: str | None) -> None:
        self.refreshes += 1
        self.expiring = False

    async def headers(self, acting_user_ref: str | None) -> dict[str, str]:
        return {"X-Test-Credential": "sensitive-value"}


def _policy(retry_count: int = 0) -> InvocationPolicy:
    return InvocationPolicy(
        timeout_ms=100,
        retry=RetryPolicy(
            retry_count=retry_count,
            delays_ms=(0,) * retry_count,
            jitter_ratio=0,
        ),
        guards=ConnectorGuards(),
    )


def _tools(*, crm=None, survey=None) -> ExternalTools:
    return ExternalTools(
        llm=MockLlmApiConnector(
            LlmResponse(id="call-1", output_text="data only", usage=LlmUsage(total_tokens=1))
        ),
        analytics=MockAnalyticsViewConnector(
            AnalyticsResponse(query_id="query-1", rows=[], row_count=0)
        ),
        search=MockOfficialSearchConnector(SearchResponse(results=[])),
        crm=crm or MockCrmConnector(CrmResponse(record_id="record-1", status="saved")),
        survey=survey or MockSurveyConnector(SurveyResponse(send_id="send-1", status="sent")),
        idempotency=MemoryIdempotencyStore(timedelta(hours=24)),
        response_guard=lambda stage_id, value: value,
    )


def test_tool_inventory_matches_design() -> None:
    assert len(TOOL_DEFINITIONS) == 5
    assert {item.side_effect for item in TOOL_DEFINITIONS} == {
        "읽기",
        "쓰기(되돌림 가능)",
        "쓰기(되돌림 불가)",
    }
    assert sum(item.side_effect == "쓰기(되돌림 불가)" for item in TOOL_DEFINITIONS) == 1
    assert all(item.input_schema and item.output_schema for item in TOOL_DEFINITIONS)


def test_external_contract_keys_and_endpoints_match_design() -> None:
    assert set(LlmRequest.model_fields) == {"model", "input", "max_output_tokens"}
    assert set(AnalyticsRequest.model_fields) == {"statement", "parameters", "max_rows"}
    assert set(SearchRequest.model_fields) == {
        "query",
        "source_type",
        "period_days",
        "sort",
        "max_results",
        "include_content",
        "include_transcript",
    }
    assert set(CrmRequest.model_fields) == {
        "consultation_ref",
        "approval_id",
        "summary",
        "idempotency_key",
    }
    assert set(SurveyRequest.model_fields) == {
        "customer_ref",
        "consultation_ref",
        "consent_ref",
        "idempotency_key",
    }
    assert HttpLlmApiConnector.endpoint == "/v1/responses"
    assert HttpAnalyticsViewConnector.method == "POST"
    assert HttpAnalyticsViewConnector.endpoint == "/v1/query"
    assert HttpOfficialSearchConnector.endpoint == "/v1/search"
    assert HttpCrmConnector.method == "PUT"
    assert HttpCrmConnector.endpoint == "/v1/consultations/{consultation_ref}"
    assert HttpSurveyConnector.endpoint == "/v1/surveys/send"


def test_unknown_schema_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyticsRequest(
            statement="SELECT 1",
            parameters={},
            max_rows=1,
            extra_value="blocked",
        )


def test_irreversible_write_without_approval_is_denied() -> None:
    tools = _tools()
    request = SurveyRequest(
        customer_ref="customer-ref",
        consultation_ref="consultation-ref",
        consent_ref="consent-ref",
        idempotency_key="key-1",
    )
    with pytest.raises(ApprovalRequired):
        asyncio.run(tools.send_survey(request, proof=None, policy=_policy()))


def test_irreversible_write_waits_for_result_after_timeout() -> None:
    class SlowSurvey:
        calls = 0

        async def send(self, request, *, acting_user_ref=None):
            self.calls += 1
            await asyncio.sleep(0.01)
            return SurveyResponse(send_id="send-1", status="sent")

    survey = SlowSurvey()
    tools = _tools(survey=survey)
    request = SurveyRequest(
        customer_ref="customer-ref",
        consultation_ref="consultation-ref",
        consent_ref="consent-ref",
        idempotency_key="key-2",
    )
    proof = ApprovalProof(
        approval_id="approval-2",
        approver_role="R-H4 설문 수신 동의 통제자",
        subject="S-E7",
    )
    policy = InvocationPolicy(
        timeout_ms=1,
        retry=RetryPolicy(retry_count=1, delays_ms=(0,), jitter_ratio=0),
        guards=ConnectorGuards(),
    )
    result = asyncio.run(tools.send_survey(request, proof=proof, policy=policy))
    assert result.status == "sent"
    assert survey.calls == 1


def test_write_is_idempotent_and_calls_external_once() -> None:
    crm = MockCrmConnector(CrmResponse(record_id="record-1", status="saved"))
    tools = _tools(crm=crm)
    key = build_idempotency_key("W-3", "event-1", "CRM")
    request = CrmRequest(
        consultation_ref="consultation-ref",
        approval_id="approval-1",
        summary={"reason": "masked"},
        idempotency_key=key,
    )
    proof = ApprovalProof(
        approval_id="approval-1",
        approver_role="R-H3 상담 후처리 검토·감사자",
        subject="S-E6",
    )
    first = asyncio.run(tools.save_crm(request, proof=proof, policy=_policy()))
    second = asyncio.run(tools.save_crm(request, proof=proof, policy=_policy()))
    assert first == second
    assert crm.calls == 1


class _FailingAnalytics:
    def __init__(self, category: ErrorCategory, failures: int) -> None:
        self.category = category
        self.failures = failures
        self.calls = 0

    async def query(self, request, *, acting_user_ref=None):
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectorError(self.category, "sanitized failure")
        return AnalyticsResponse(query_id="query-1", rows=[], row_count=0)


@pytest.mark.parametrize("category", [ErrorCategory.INPUT, ErrorCategory.PERMISSION])
def test_non_retryable_error_has_zero_retries(category: ErrorCategory) -> None:
    connector = _FailingAnalytics(category, failures=1)
    tools = _tools()
    tools.analytics = connector
    request = AnalyticsRequest(statement="SELECT 1", parameters={}, max_rows=1)
    with pytest.raises(ConnectorError):
        asyncio.run(
            tools.query_analytics(request, stage_id="S-R4", policy=_policy(retry_count=2))
        )
    assert connector.calls == 1


def test_transient_error_retries_only_in_connector_layer() -> None:
    connector = _FailingAnalytics(ErrorCategory.TRANSIENT, failures=2)
    tools = _tools()
    tools.analytics = connector
    request = AnalyticsRequest(statement="SELECT 1", parameters={}, max_rows=1)
    result = asyncio.run(
        tools.query_analytics(request, stage_id="S-B2", policy=_policy(retry_count=2))
    )
    assert result.row_count == 0
    assert connector.calls == 3


def test_mock_connectors_do_not_need_real_address() -> None:
    tools = _tools()
    assert tools.llm.calls == 0
    assert tools.search.calls == 0


def test_authentication_rejection_refreshes_once_and_redacts_secret() -> None:
    provider = _CredentialProvider()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, request=request)

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            base_url="https://test.invalid",
            transport=transport,
            timeout=None,
        ) as client:
            connector = HttpAnalyticsViewConnector(client, AuthenticationManager(provider))
            with pytest.raises(ConnectorError) as raised:
                await connector.query(
                    AnalyticsRequest(statement="SELECT 1", parameters={}, max_rows=1)
                )
            assert raised.value.category is ErrorCategory.AUTHENTICATION
            assert "sensitive-value" not in str(raised.value)

    asyncio.run(scenario())
    assert provider.refreshes == 1
    assert attempts == 2


def test_mock_response_is_treated_as_data_and_passes_guard_hook() -> None:
    seen: list[tuple[str, dict]] = []

    def guard(stage_id: str, value: dict) -> dict:
        seen.append((stage_id, value))
        return value

    tools = _tools()
    tools.response_guard = guard
    result = asyncio.run(
        tools.call_llm(
            request=LlmRequest(
                model="configured-model",
                input=[{"role": "user", "content": "data"}],
                max_output_tokens=1,
            ),
            stage_id="S-R2",
            policy=_policy(),
        )
    )
    assert result.output_text == "data only"
    assert seen[0][0] == "S-R2"
