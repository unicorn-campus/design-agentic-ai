from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from help_desk_guardrails.approval import ApprovalGate, ApprovalGrant
from langgraph.types import interrupt


class CustomerAnswerApprover:
    def __init__(self, gate: ApprovalGate) -> None:
        self._gate = gate

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = interrupt({"stage_id": "S-R9", "approval_request": payload})
        if not isinstance(result, dict):
            raise TypeError("S-R9 재진입 값이 object가 아님")
        approval_id = str(result.get("approval_id", ""))
        self._gate.authorize(
            "AP-W1-R9",
            ApprovalGrant(
                approver="R-H1 고객 답변 승인자",
                approved_at=datetime.now(UTC),
                subject="AP-W1-R9",
                approval_id=approval_id,
                idempotency_key=f"{approval_id}:S-R9",
            ),
        )
        return result
