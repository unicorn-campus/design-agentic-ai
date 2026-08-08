"""노드 모듈이 함께 쓰는 조각. 새 값을 정하는 코드가 없음 — 모양만 맞춤."""

from __future__ import annotations

from typing import Any, Mapping

from common.budget import now_ms
from common.state import LunchPickState
from toolkit.runner import CallContext, ConnectorResult

from .context import FlowContext
from .node import check_deadline, merged
from .observe import record_step
from .signals import LandingReason, halt_to_landing, note_failure

__all__ = [
    "base_record_fields",
    "call_context_of",
    "connector_failure_update",
    "check_deadline",
    "merged",
    "record_step",
    "halt_to_landing",
    "note_failure",
    "LandingReason",
    "now_ms",
]


def base_record_fields(
    step_id: str,
    state: LunchPickState,
    context: FlowContext,
    **extra: Any,
) -> dict[str, Any]:
    """⑥ 기록 항목 이름 후보를 한 벌 만듦. 실제로 남는 것은 ⑥이 그 단계에 적어 준 이름뿐임."""
    fields: dict[str, Any] = {
        "request_id": context.request_id,
        "trigger_kind": str(state.get("trigger_kind", "")),
        "deadline_at": state.get("deadline_at"),
        "접수 시각": now_ms(),
        "구획 식별자": context.input_of("section", ""),
        "호출자": step_id,
    }
    fields.update(extra)
    return fields


def call_context_of(
    state: LunchPickState,
    context: FlowContext,
    *,
    completed_steps: tuple[str, ...],
    approval_evidence: Mapping[str, Any] | None = None,
) -> CallContext:
    """커넥터에 넘길 호출 사정. 마감선은 상태에서 읽고 여기서 만들지 않음."""
    return CallContext(
        deadline_at=int(state.get("deadline_at") or 0),
        completed_steps=completed_steps,
        approval_evidence=dict(approval_evidence or {}),
        request_id=context.request_id or None,
    )


def connector_failure_update(
    step_id: str,
    result: ConnectorResult,
    *,
    to_landing: bool,
    reason: LandingReason = LandingReason.STEP_EXHAUSTED,
) -> dict[str, Any]:
    """커넥터가 실패했을 때 상태에 남길 값.

    ③ 「초과 시 처리」가 `부분 결과로 계속`인 단계는 기록만 남기고 지나가고,
    `안전 종료` · `사람 확인`인 단계는 착지로 감. **여기서 재시도를 걸지 않음.**
    """
    detail = {
        "error_class": result.error_class.value if result.error_class else None,
        "attempts": result.attempts,
        "unresolved": result.unresolved,
        "escalate_to_human": result.escalate_to_human,
    }
    if to_landing:
        return halt_to_landing(step_id, reason, detail)
    return note_failure(step_id, reason, detail)
