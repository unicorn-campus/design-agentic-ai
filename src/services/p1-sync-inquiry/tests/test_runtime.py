from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from p1_sync_inquiry.operations import (
    S_R4_TABLE,
    InquiryOperations,
    derive_customer_ref,
    validate_read_statement,
)
from p1_sync_inquiry.runtime import build_approval_payload

SRC_ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (SRC_ROOT / "common" / ".env.example", SRC_ROOT / "tools" / ".env.example")
SECRETS = {
    "HELP_DESK_LLM_API_KEY": "local-unused",
    "HELP_DESK_CHECKPOINT_ENCRYPTION_KEY": "test-encryption-key",
    "HELP_DESK_MASKING_SALT": "test-masking-salt",
}
VALID_STATEMENT = (
    "SELECT masked_customer_id, transaction_status FROM masked_transaction_analysis_v"
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    for env_file in ENV_FILES:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if value and not line.startswith("#"):
                monkeypatch.setenv(key, value)
    for key, value in SECRETS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("HELP_DESK_CHECKPOINT_URI", str(tmp_path / "checkpoint.sqlite"))

    from p1_sync_inquiry.api import create_runtime_app

    return TestClient(create_runtime_app())


def inquiry(request_id: str, text: str) -> dict[str, str]:
    return {
        "request_id": request_id,
        "auth_session_ref": f"session-{request_id}",
        "inquiry_text": text,
        "channel": "web",
    }


def test_read_statement_keeps_allowed_view_and_adds_row_limit() -> None:
    result = validate_read_statement(VALID_STATEMENT, 100)

    assert S_R4_TABLE in result
    assert "LIMIT 100" in result.upper()


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM masked_transaction_analysis_v",
        "SELECT * FROM masked_transaction_analysis_v",
        "SELECT masked_customer_id FROM other_view",
        "SELECT secret_column FROM masked_transaction_analysis_v",
    ],
)
def test_read_statement_rejects_unsafe_query(statement: str) -> None:
    with pytest.raises(ValueError):
        validate_read_statement(statement, 100)


def test_customer_ref_hides_session_reference_and_is_stable() -> None:
    first = derive_customer_ref("session-1", "salt")
    second = derive_customer_ref("session-1", "salt")

    assert first == second
    assert "session-1" not in first
    assert first != derive_customer_ref("session-1", "other-salt")


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [([], "high"), (["doc:1"], "high"), (["doc:1", "doc:2"], "low")],
)
def test_risk_level_follows_evidence_count(
    evidence: list[str], expected: str
) -> None:
    import asyncio

    operations = InquiryOperations(
        tools=None,  # type: ignore[arg-type]
        input_guard=None,  # type: ignore[arg-type]
        masker=None,  # type: ignore[arg-type]
        masking_salt="salt",
        policies={},
        max_rows=100,
    )
    result = asyncio.run(operations.route_risk({"evidence_refs": evidence}))

    assert result["risk_result"]["level"] == expected


@pytest.mark.parametrize(
    ("approval", "draft", "expected_type", "expected_status"),
    [
        ({"decision": "승인"}, {"answer": "본문"}, "answer", "completed"),
        ({"decision": "반려"}, {"answer": "본문"}, "handoff", "failed"),
        ({"decision": "승인"}, {}, "handoff", "completed"),
    ],
)
def test_deliver_answer_branches(
    approval: dict[str, str],
    draft: dict[str, str],
    expected_type: str,
    expected_status: str,
) -> None:
    import asyncio

    operations = InquiryOperations(
        tools=None,  # type: ignore[arg-type]
        input_guard=None,  # type: ignore[arg-type]
        masker=None,  # type: ignore[arg-type]
        masking_salt="salt",
        policies={},
        max_rows=100,
    )
    result = asyncio.run(
        operations.deliver_answer(
            {"request_id": "req-1", "approval_result": approval, "answer_draft": draft}
        )
    )

    assert result["result_type"] == expected_type
    assert result["request_status"] == expected_status


def test_approval_payload_carries_both_approval_id_and_result() -> None:
    payload = build_approval_payload(
        "req-1", {"decision": "승인", "reviewer_ref": "reviewer-1"}
    )

    assert payload["approval_id"] == "req-1:S-R9"
    assert payload["approval_result"]["decision"] == "승인"


def test_ready_reports_ok_once_workflow_is_assembled(client: TestClient) -> None:
    with client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json() == {"status": "ok"}


def test_low_risk_inquiry_returns_answer_with_evidence(client: TestClient) -> None:
    with client:
        response = client.post(
            "/v1/inquiries", json=inquiry("req-1", "연회비 면제 조건이 궁금합니다")
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result_type"] == "answer"
    assert body["request_status"] == "completed"
    assert body["answer"]["evidence_refs"]


def test_handoff_inquiry_waits_for_person_then_resumes(client: TestClient) -> None:
    with client:
        first = client.post(
            "/v1/inquiries", json=inquiry("req-2", "카드를 분실했어요 상담사 연결해 주세요")
        )
        assert first.json() == {
            "result_type": "pending_approval",
            "request_status": "pending",
        }

        second = client.post(
            "/v1/inquiries/req-2/decisions",
            json={
                "decision": "승인",
                "reviewer_ref": "reviewer-1",
                "revised_answer": {"answer": "상담사가 안내드립니다"},
            },
        )

    assert second.status_code == 200
    assert second.json()["request_status"] == "completed"


def test_rejected_decision_hands_the_inquiry_over(client: TestClient) -> None:
    with client:
        client.post(
            "/v1/inquiries", json=inquiry("req-3", "지난달 결제 건수 알려주세요")
        )
        response = client.post(
            "/v1/inquiries/req-3/decisions",
            json={"decision": "반려", "reviewer_ref": "reviewer-1"},
        )

    assert response.json()["result_type"] == "handoff"
    assert response.json()["request_status"] == "failed"


def test_unknown_request_cannot_be_resumed(client: TestClient) -> None:
    with client:
        response = client.post(
            "/v1/inquiries/req-none/decisions",
            json={"decision": "승인", "reviewer_ref": "reviewer-1"},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "approval_not_found"
