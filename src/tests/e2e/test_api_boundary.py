from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from help_desk_api import GuardrailBoundary
from help_desk_guardrails import SensitiveDataMasker, load_policy
from help_desk_workflow.contracts import InquiryResult
from p1_sync_inquiry.api import create_app as create_inquiry_app
from p2_knowledge_improvement_batch.api import create_internal_app as create_faq_app
from p3_conversation_closed_event.api import create_internal_app as create_crm_app
from p3_conversation_closed_event.subscriber import ConsultationClosedSubscriber


def boundary() -> GuardrailBoundary:
    return GuardrailBoundary(
        load_policy(),
        SensitiveDataMasker("test-only-salt", lambda value: "encrypted-test-value"),
    )


async def ready() -> bool:
    return True


async def inquiry_runner(payload, deadline):
    assert payload["request_id"] == "req-1"
    assert deadline.remaining_ms() > 0
    return {
        "result_type": "answer",
        "answer": {"message": "승인된 근거 답변"},
        "request_status": "completed",
    }


async def resume_runner(request_id, decision):
    assert request_id == "req-1"
    assert decision["decision"] == "approve"
    return {
        "result_type": "answer",
        "answer": {"message": "승인된 답변"},
        "request_status": "completed",
    }


def inquiry_payload() -> dict[str, str]:
    return {
        "request_id": "req-1",
        "auth_session_ref": "session-1",
        "inquiry_text": "해외 결제 차단 이유를 알려주세요",
        "channel": "web",
    }


def test_inquiry_json_response_uses_workflow_schema() -> None:
    app = create_inquiry_app(inquiry_runner, resume_runner, boundary(), ready, 615_000)
    response = TestClient(app).post("/v1/inquiries", json=inquiry_payload())
    assert response.status_code == 200
    assert set(response.json()) == {"result_type", "answer", "request_status"}
    assert set(response.json()) <= set(InquiryResult.model_fields)


def test_inquiry_sse_has_one_guarded_final_event() -> None:
    app = create_inquiry_app(inquiry_runner, resume_runner, boundary(), ready, 615_000)
    response = TestClient(app).post(
        "/v1/inquiries",
        json=inquiry_payload(),
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.count("event: final") == 1
    data = response.text.split("data: ", 1)[1].strip()
    assert set(json.loads(data)) <= set(InquiryResult.model_fields)


def test_deadline_landing_uses_truncated_event_marker() -> None:
    async def truncated_runner(payload, deadline):
        del deadline
        return {
            "result_type": "safe_stop",
            "handoff_ref": payload["request_id"],
            "request_status": "failed",
        }

    app = create_inquiry_app(truncated_runner, resume_runner, boundary(), ready, 615_000)
    response = TestClient(app).post(
        "/v1/inquiries",
        json=inquiry_payload(),
        headers={"Accept": "text/event-stream"},
    )
    assert response.headers["x-result-completeness"] == "truncated"
    assert response.text.startswith("event: truncated")


def test_resume_route_returns_same_workflow_schema() -> None:
    app = create_inquiry_app(inquiry_runner, resume_runner, boundary(), ready, 615_000)
    response = TestClient(app).post(
        "/v1/inquiries/req-1/decisions",
        json={"decision": "approve", "reviewer_ref": "reviewer-1"},
    )
    assert response.status_code == 200
    assert set(response.json()) <= set(InquiryResult.model_fields)


def test_error_response_does_not_expose_internal_details() -> None:
    async def failing_runner(payload, deadline):
        del payload, deadline
        raise RuntimeError("/private/path SELECT secret model-name")

    app = create_inquiry_app(failing_runner, resume_runner, boundary(), ready, 615_000)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/v1/inquiries",
        json=inquiry_payload(),
    )
    assert response.status_code == 500
    text = response.text
    assert "/private/path" not in text
    assert "SELECT" not in text
    assert "model-name" not in text


def test_health_routes_separate_liveness_and_readiness() -> None:
    app = create_inquiry_app(inquiry_runner, resume_runner, boundary(), ready, 615_000)
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


def test_internal_faq_decision_route() -> None:
    async def decide(candidate_id, payload):
        assert candidate_id == payload["candidate_id"]
        return {
            "approval_id": "approval-1",
            "decision_status": "approved",
            "resume_stage": "S-B10",
        }

    app = create_faq_app(decide, boundary(), ready)
    response = TestClient(app).post(
        "/internal/faq-candidates/candidate-1/decisions",
        json={"decision": "approve", "reviewer_ref": "reviewer-1"},
    )
    assert response.status_code == 200
    assert set(response.json()) == {"approval_id", "decision_status", "resume_stage"}


def test_internal_crm_review_route() -> None:
    async def decide(review_id, payload):
        assert review_id == payload["review_id"]
        return {
            "approval_id": "approval-2",
            "decision_status": "approved",
            "resume_stage": "S-E6",
        }

    app = create_crm_app(decide, boundary(), ready)
    response = TestClient(app).post(
        "/internal/crm-record-reviews/review-1/decisions",
        json={"decision": "approve", "reviewer_ref": "reviewer-1"},
    )
    assert response.status_code == 200
    assert set(response.json()) == {"approval_id", "decision_status", "resume_stage"}


def test_event_trigger_is_subscriber_not_public_route() -> None:
    async def run_event(payload):
        return {
            "accepted": True,
            "duplicate": False,
            "processing_ref": payload["event_id"],
        }

    subscriber = ConsultationClosedSubscriber(run_event, boundary())
    result = __import__("asyncio").run(subscriber.handle({
        "event_id": "event-1",
        "consultation_ref": "consultation-1",
        "ended_at": datetime.now(UTC).isoformat(),
        "transcript": "마스킹 대상 없는 상담",
        "survey_consent_ref": "consent-1",
    }))
    assert result.model_dump() == {
        "accepted": True,
        "duplicate": False,
        "processing_ref": "event-1",
    }


def test_only_sync_workflow_has_public_http_entry() -> None:
    inquiry_app = create_inquiry_app(inquiry_runner, resume_runner, boundary(), ready, 615_000)
    faq_app = create_faq_app(None, boundary(), ready)
    crm_app = create_crm_app(None, boundary(), ready)
    public = {route.path for route in inquiry_app.routes if route.path.startswith("/v1/")}
    faq_public = {route.path for route in faq_app.routes if route.path.startswith("/v1/")}
    crm_public = {route.path for route in crm_app.routes if route.path.startswith("/v1/")}
    assert public == {"/v1/inquiries", "/v1/inquiries/{request_id}/decisions"}
    assert faq_public == set()
    assert crm_public == set()
