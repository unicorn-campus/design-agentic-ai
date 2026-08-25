from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .policy import GuardrailPolicy


class ApprovalRequired(PermissionError):
    pass


@dataclass(frozen=True)
class ApprovalGrant:
    approver: str
    approved_at: datetime
    subject: str
    approval_id: str
    idempotency_key: str


class ApprovalGate:
    def __init__(self, policy: GuardrailPolicy) -> None:
        self._points = {row.id: row for row in policy.approval_points}
        self._consumed: set[str] = set()

    @property
    def required_count(self) -> int:
        return sum(row.model_extra.get("conclusion") == "승인" for row in self._points.values())

    def authorize(self, point_id: str, grant: ApprovalGrant | None) -> None:
        point = self._points[point_id]
        if point.model_extra.get("conclusion") != "승인":
            return
        if grant is None:
            raise ApprovalRequired("승인 표시가 없어 기본 거부함")
        expected = point.model_extra["approver"]
        if grant.approver != expected or grant.subject != point_id:
            raise ApprovalRequired("승인 주체 또는 대상이 다름")
        if grant.idempotency_key in self._consumed:
            raise ApprovalRequired("이미 사용한 승인 표시임")
        self._consumed.add(grant.idempotency_key)
