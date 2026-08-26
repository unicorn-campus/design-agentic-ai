from __future__ import annotations

from datetime import UTC, datetime

from help_desk_guardrails.approval import ApprovalGate, ApprovalGrant


class SurveyConsentController:
    def __init__(self, gate: ApprovalGate) -> None:
        self._gate = gate

    def authorize(self, survey_consent_ref: str) -> dict[str, str]:
        if not survey_consent_ref:
            raise PermissionError("설문 수신 동의가 없어 발송을 거부함")
        self._gate.authorize(
            "AP-W3-E7",
            ApprovalGrant(
                approver="R-H4 설문 수신 동의 통제자",
                approved_at=datetime.now(UTC),
                subject="AP-W3-E7",
                approval_id=survey_consent_ref,
                idempotency_key=f"{survey_consent_ref}:AP-W3-E7",
            ),
        )
        return {
            "consent_ref": survey_consent_ref,
            "approver_role": "R-H4 설문 수신 동의 통제자",
        }
