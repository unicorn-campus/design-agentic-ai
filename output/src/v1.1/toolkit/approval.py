"""승인 문 자리. **판정하는 모듈은 `05-guardrail.md`가 만듦** — 여기서는 표시를 요구하고 없으면 거부함.

용어 1줄 — **승인 문(승인 게이트)** = 되돌릴 수 없는 일을 하기 전에 사람이 확인한 표시가 있는지
보고, 없으면 아예 부르지 않는 문임. 기본값은 **거부**임.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from .errors import ApprovalMissing, ErrorClass, ErrorReport, PreconditionNotMet
from .schema import SideEffect, ToolSpec

__all__ = [
    "CallBudget",
    "NoOpCallBudget",
    "require_approval",
    "require_preconditions",
]


@runtime_checkable
class CallBudget(Protocol):
    """호출 상한 자리 — 같은 요청에서 이 도구를 몇 번까지 부를 수 있나.

    **실제로 세는 코드는 `05-guardrail.md` 몫임.** 여기는 부르는 자리만 둠.
    """

    def check(self, connector_id: str, request_id: str | None, limit: int | None) -> None: ...

    def note_call(self, connector_id: str, request_id: str | None) -> None: ...


class NoOpCallBudget(CallBudget):
    """자리만 잡아 두는 것. 아무것도 세지 않고 아무것도 막지 않음."""

    def check(self, connector_id: str, request_id: str | None, limit: int | None) -> None:
        return None

    def note_call(self, connector_id: str, request_id: str | None) -> None:
        return None


def _missing_marks(
    marks: tuple[str, ...], evidence: Mapping[str, Any]
) -> tuple[str, ...]:
    return tuple(mark for mark in marks if not evidence.get(mark))


def require_approval(spec: ToolSpec, approval_evidence: Mapping[str, Any]) -> None:
    """승인 표시가 없으면 호출 자체를 거부함. 바깥을 부르기 전에 막으므로 부작용이 0건임."""
    if not spec.approval_marks:
        return
    missing = _missing_marks(spec.approval_marks, approval_evidence)
    if not missing:
        return
    raise ApprovalMissing(
        ErrorReport(
            connector_id=spec.connector_id,
            step_id=spec.step_id,
            error_class=ErrorClass.PERMISSION,
            reason="승인 표시 없음 — 기본 거부",
            offending_keys=missing,
            requested_scopes=spec.requested_scopes,
            attempts=0,
            extra={
                "side_effect": spec.side_effect.value,
                "required_approval_marks": list(spec.approval_marks),
            },
        )
    )


def require_preconditions(
    spec: ToolSpec, completed_steps: tuple[str, ...]
) -> None:
    """⑤ 「커넥터 검증 기준」의 호출 순서를 확인함. 순서가 틀리면 호출하지 않음."""
    if not spec.preconditions:
        return
    done = set(completed_steps)
    missing = tuple(step for step in spec.preconditions if step not in done)
    if not missing:
        return
    reason = (
        "앞선 단계가 끝나지 않았음(순서 필수)"
        if spec.strict_order
        else "앞선 단계가 끝나지 않았음"
    )
    raise PreconditionNotMet(
        ErrorReport(
            connector_id=spec.connector_id,
            step_id=spec.step_id,
            error_class=ErrorClass.PERMISSION,
            reason=reason,
            offending_keys=missing,
            requested_scopes=spec.requested_scopes,
            attempts=0,
            extra={
                "strict_order": spec.strict_order,
                "side_effect": spec.side_effect.value,
            },
        )
    )


IRREVERSIBLE = SideEffect.WRITE_IRREVERSIBLE
