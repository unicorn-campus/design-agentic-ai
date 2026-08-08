"""감사 기록 — 되돌릴 수 없는 일이 실행될 때마다 1행.

한 행에 담는 것 — `언제 / 누가(또는 무엇이) / 어떤 도구 / 승인 표시 / 결과 / 중복 방지 키`.
값은 **가리기 매핑을 지난 뒤** 담김. 변경 전후 값에 원문을 남기지 않음(`M-23`).
행을 지우는 함수를 두지 않음 — 만료 삭제 작업 자체는 `08-deploy.md` 몫이며 여기서는
보관 기간 값만 설정으로 넘김.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..guardrail.masking import MaskPath, Masker, get_masker, irreversible_hash
from ..guardrail.rules import RuleBook, get_rulebook
from ..guardrail.tool_guard import ApprovalEvidence
from .exporter import SpanRecord, SpanSink

__all__ = ["AuditRow", "AuditLog"]


@dataclass(frozen=True, slots=True)
class AuditRow:
    """감사 기록 1행. 만들어진 뒤에는 바꿀 수 없음."""

    occurred_at_ms: int
    actor_ref: str
    """누가(또는 무엇이) — 회원ID 해시나 배치 이름. 원문 식별자를 넣지 않음."""
    tool_id: str
    approval: dict[str, Any]
    """승인 표시. 승인 ID는 해시로만 담김."""
    result: str
    idempotency_key_hash: str | None
    before_after: dict[str, Any] = field(default_factory=dict)
    """`M-23`을 지난 값 — 변경 필드명 + 전후 해시."""
    retention_months: int | None = None
    step_id: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "언제": self.occurred_at_ms,
            "누가": self.actor_ref,
            "어떤 도구": self.tool_id,
            "승인 표시": self.approval,
            "결과": self.result,
            "중복 방지 키": self.idempotency_key_hash,
            "변경 전후": self.before_after,
            "보관 기간(개월)": self.retention_months,
        }


class AuditLog:
    """지워지지 않는 장부. 붙이기만 하고 지우거나 고치는 함수를 두지 않음."""

    def __init__(
        self,
        sink: SpanSink | None = None,
        book: RuleBook | None = None,
        masker: Masker | None = None,
    ) -> None:
        self._book = book or get_rulebook()
        self._masker = masker or get_masker(self._book)
        self._sink = sink
        self._rows: list[AuditRow] = []

    @property
    def retention_months(self) -> int:
        """⑥ 11절 보존 정책 표 · ⑤ 7절 보존·삭제에서 읽음. 여기서 정하지 않음."""
        return int(self._book.retention["audit_record_months"])

    def rows(self) -> tuple[AuditRow, ...]:
        return tuple(self._rows)

    def rows_for_tool(self, tool_id: str) -> tuple[AuditRow, ...]:
        return tuple(row for row in self._rows if row.tool_id == tool_id)

    def append(
        self,
        *,
        occurred_at_ms: int,
        actor: str,
        tool_id: str,
        result: str,
        evidence: ApprovalEvidence | None = None,
        idempotency_key: str | None = None,
        before: Mapping[str, Any] | None = None,
        after: Mapping[str, Any] | None = None,
        step_id: str | None = None,
    ) -> AuditRow:
        """1행 붙임. 넘겨받은 값은 여기서 전부 가리기를 지남."""
        approval: dict[str, Any] = {"있음": evidence is not None}
        if evidence is not None:
            approval.update(
                {
                    "승인 ID 해시": evidence.approval_id_hash,
                    "승인 시각": evidence.approved_at_ms,
                    "무엇을": evidence.subject,
                    "표시한 고지·안내 항목 목록": list(evidence.shown_items),
                }
            )
        before_after: dict[str, Any] = {}
        if before is not None:
            before_after["before"] = dict(before)
        if after is not None:
            before_after["after"] = dict(after)
        masked_before_after = self._masker.mask_mapping(before_after, MaskPath.AUDIT)

        row = AuditRow(
            occurred_at_ms=occurred_at_ms,
            actor_ref=self._actor_ref(actor),
            tool_id=tool_id,
            approval=approval,
            result=result,
            idempotency_key_hash=None if idempotency_key is None else irreversible_hash(idempotency_key),
            before_after=masked_before_after,
            retention_months=self.retention_months,
            step_id=step_id,
        )
        self._rows.append(row)
        if self._sink is not None:
            self._sink.emit(
                SpanRecord(
                    name="감사 레코드",
                    step_id=step_id,
                    record_points=("O-8",),
                    attributes=row.as_record(),
                )
            )
        return row

    def _actor_ref(self, actor: str) -> str:
        """회원 식별자면 해시로 바꿈. 배치 이름 등은 그대로 둠."""
        applied, masked = self._masker.mask_value("member_id", actor, MaskPath.AUDIT)
        return str(masked) if applied else actor
