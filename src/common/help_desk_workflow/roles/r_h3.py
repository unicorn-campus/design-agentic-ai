from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from help_desk_guardrails.approval import ApprovalGate, ApprovalGrant
from langgraph.types import interrupt


class ConsultationPostprocessor:
    def __init__(self, gate: ApprovalGate) -> None:
        self._gate = gate

    def _authorize(self, point_id: str, approval_id: str) -> None:
        self._gate.authorize(
            point_id,
            ApprovalGrant(
                approver="R-H3 상담 후처리 검토·감사자",
                approved_at=datetime.now(UTC),
                subject=point_id,
                approval_id=approval_id,
                idempotency_key=f"{approval_id}:{point_id}",
            ),
        )

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = interrupt({"stage_id": "S-E5", "approval_request": payload})
        if not isinstance(result, dict):
            raise TypeError("S-E5 재진입 값이 object가 아님")
        self._authorize("AP-W3-E5", str(result.get("approval_id", "")))
        return result

    def crm_payload(self, review_decision: dict[str, Any]) -> dict[str, Any]:
        if not review_decision.get("approval_id"):
            raise PermissionError("S-E5 승인 ID가 없어 CRM 저장을 거부함")
        self._authorize("AP-W3-E6", str(review_decision["approval_id"]))
        return review_decision
