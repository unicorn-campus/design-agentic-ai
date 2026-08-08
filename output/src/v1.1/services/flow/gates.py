"""승인 문을 **어느 노드 앞에 둘지**만 정하는 자리.

승인 문 구현체는 `05-guardrail.md`가 만든 `common.guardrail.ToolGuard`이며 여기서 다시 만들지 않음.
사람이 멈춰 서는 지점(`S-S7` · `S-C5`)은 흐름 프레임워크의 중단 기능으로 만듦 —
되묻기 3으로 정한 형태는 **노드 앞에서 멈춤**(확인 대기 상태를 남기고 응답을 닫음)임.

되돌릴 수 없는 도구를 부르는 노드 3개는 전부 승인 문 **뒤에** 놓임 —
`S-S9`(`C-9`) · `S-C10`(`C-12`) · `S-X4`(`R-11`). `S-B7`(`R-4`)은 ③에 사전 승인 노드가 없어
⑥이 준 제한 장치 5개를 문으로 씀(③ 12절 2번 판정).
"""

from __future__ import annotations

from typing import Any, Mapping

from common.budget import now_ms
from common.guardrail.tool_guard import ApprovalEvidence, ToolDecision
from common.state import LunchPickState

from .context import FlowContext

__all__ = [
    "evidence_from_state",
    "evaluate_human_gate",
    "evaluate_write_gate",
    "build_interrupt_payload",
]


def evidence_from_state(
    state: LunchPickState, *, tool_id: str
) -> ApprovalEvidence | None:
    """③ 6절 16번 `approval_evidence`를 ⑥ 승인 표시 그릇으로 옮김.

    **참·거짓 한 값이 아님** — 누가 · 언제 · 무엇을 · 보여 준 고지 항목 · 만료 시각을 담음.
    """
    raw = dict(state.get("approval_evidence") or {})
    approval_id = raw.get("user_approval_id") or raw.get("cancel_confirm_id")
    approved_at = raw.get("approved_at") or raw.get("confirmed_at")
    if not approval_id or approved_at is None:
        return None
    shown = tuple(str(item) for item in raw.get("shown_items", ()) or ())
    return ApprovalEvidence(
        approval_id=str(approval_id),
        approver_ref=str(raw.get("approver_ref", "")),
        approved_at_ms=int(approved_at),
        subject=f"{tool_id}:{raw.get('subject', '')}",
        shown_items=shown,
        expires_at_ms=raw.get("approval_expires_at"),
    )


def evaluate_human_gate(
    tool_id: str,
    context: FlowContext,
    state: LunchPickState,
    *,
    idempotency_key: str,
    guards_met: Mapping[str, bool] | None = None,
) -> ToolDecision:
    """되돌릴 수 없는 도구를 부르기 **직전에** 부름. 표시가 없으면 바깥 호출이 0건임."""
    return context.tool_guard.evaluate(
        tool_id,
        request_id=context.request_id,
        now_ms=now_ms(),
        evidence=evidence_from_state(state, tool_id=tool_id),
        guards_met=dict(guards_met or {}),
        idempotency_key=idempotency_key,
    )


def evaluate_write_gate(
    tool_id: str,
    context: FlowContext,
    *,
    idempotency_key: str,
    guards_met: Mapping[str, bool],
) -> ToolDecision:
    """사람이 낄 자리가 없어 **제한 장치로 대체**된 쓰기 도구용(⑥ 3-1절 `guarded`)."""
    return context.tool_guard.evaluate(
        tool_id,
        request_id=context.request_id,
        now_ms=now_ms(),
        guards_met=dict(guards_met),
        idempotency_key=idempotency_key,
    )


def build_interrupt_payload(
    step_id: str, shown: Mapping[str, Any]
) -> dict[str, Any]:
    """멈출 때 사람에게 보이는 값. **멈춘 자리와 다시 들어오는 자리가 같은 단계 식별자**를 씀."""
    return {
        "step_id": step_id,
        "resume_step_id": step_id,
        "shown": dict(shown),
        "asked_at_ms": now_ms(),
    }
