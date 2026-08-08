"""③ 4-7절 이벤트 `S-N`(기억 제한 도달 · 구독 활성화 전파) — 노드 10개. 구획 2개.

담당자 — 구획 1(`S-N1` ~ `S-N3`)은 `R-15`, `S-N4`는 `R-13`,
구획 2의 `S-N5` · `S-N8` · `S-N9` · 착지 `S-N10`은 `R-13`, `S-N6` · `S-N7`은 `R-16`임.
`S-N6`이 ③ 11절 구획 2의 재개 경계 단계임.
"""

from __future__ import annotations

from typing import Any

from common.budget import compute_deadline_at
from common.checkpointer import build_idempotency_key
from common.state import LunchPickState, SubscriptionState, TriggerKind

from ..member_service.agents import r13_subscription_state as r13
from ..recommendation_history_service.agents import (
    r15_memory_limit_notice as r15,
    r16_retention_policy as r16,
)
from ._common import (
    LandingReason,
    base_record_fields,
    check_deadline,
    halt_to_landing,
    merged,
    note_failure,
    now_ms,
    record_step,
)
from .context import FlowContext
from .gates import evaluate_write_gate

__all__ = ["NODE_FUNCTIONS"]


async def node_S_N1_receive_memory_limit_signal(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구획 1 진입 노드 — 마감선(가시성 타임아웃)을 넣음."""
    trigger = TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION
    deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    payload = r15.receive_memory_limit_signal(
        memory_limit_signal_id=str(context.input_of("memory_limit_signal_id", context.request_id)),
        member_id=str(context.input_of("member_id", "")),
        detected_at=int(context.input_of("detected_at", now_ms())),
        trigger_kind=trigger.value,
    )
    record_step(
        context.recorder,
        "S-N1",
        base_record_fields("S-N1", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-N1", **payload}],
    }


async def node_S_N2_check_free_plan(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 조건 — 구독 상태 무료 + 누적·만료 예정 기록 수 집계 → `K-28` 앞자리.

    **안전 종료** — 프리미엄이면 안내를 보내지 않음(③ 4-7절).
    """
    verdict = check_deadline("S-N2", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-N2", base_record_fields("S-N2", state, context))
        return verdict.update
    result = r15.check_free_plan_and_count(
        member_id=str(context.input_of("member_id", "")),
        subscription_state=context.source_of("subscription_state"),
        total_record_count=context.source_of("total_record_count"),
        expiring_record_count=context.source_of("expiring_record_count"),
    )
    record_step(context.recorder, "S-N2", base_record_fields("S-N2", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if not result["precheck_passed"]:
        update = merged(update, halt_to_landing("S-N2", LandingReason.PRECHECK_FAILED, result))
    return update


async def node_S_N3_deliver_notice(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """기억 제한 도달 알림 전달 → `K-28`. ③ 11절 구획 1의 재개 경계 단계임.

    중복 방지 키 = `회원 + 만료 예정 기준일` 조합 키. 발송 커넥터(`C-10`)는 계약에 0건임.
    """
    verdict = check_deadline("S-N3", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-N3", base_record_fields("S-N3", state, context))
        return verdict.update
    precheck = dict(state.get("precheck_result") or {})
    member_id = str(precheck.get("member_id") or "unknown")
    idempotency_key = build_idempotency_key(
        "member_and_expiring_baseline",
        member_id,
        str(context.input_of("expiring_baseline_on", "unknown")),
    )
    decision = evaluate_write_gate(
        "R-15",
        context,
        idempotency_key=idempotency_key,
        guards_met={"precondition_free_plan": True, "no_send_connector": True},
    )
    record_step(
        context.recorder,
        "S-N3",
        base_record_fields(
            "S-N3",
            state,
            context,
            **_audit_fields("R-15", "허용" if decision.allowed else decision.reason),
        ),
    )
    if not decision.allowed:
        return halt_to_landing("S-N3", LandingReason.TOOL_DENIED, {"reason": decision.reason})
    if not await context.idempotency.claim(idempotency_key):
        return note_failure("S-N3", LandingReason.IDEMPOTENCY_REPLAYED, {"member_id": member_id})

    payload = r15.build_notice(
        memory_limit_notice_id=str(context.input_of("memory_limit_notice_id", context.request_id)),
        member_id=member_id,
        total_record_count=int(precheck.get("total_record_count") or 0),
        expiring_record_count=int(precheck.get("expiring_record_count") or 0),
        notice_idempotency_key=idempotency_key,
        accuracy_gain_rate=context.source_of("accuracy_gain_rate"),
    )
    return {
        "resume_cursor": {
            "boundary_step": "S-N3",
            "resume_unit": "member_and_expiring_baseline",
            "idempotency_key": idempotency_key,
        },
        "partial_context": [{"step_id": "S-N3", "K-28": payload}],
    }


async def node_S_N4_show_subscription_notice(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구독 안내 표시. 부분 결과로 계속 — 향상률 없이 누적 수만 표시(⑥ `B-25` · `O-C10`)."""
    verdict = check_deadline("S-N4", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-N4", base_record_fields("S-N4", state, context))
        return verdict.update
    k28 = _fragment_value(state, "K-28") or {}
    payload = r13.build_subscription_notice(
        total_record_count=int(k28.get("total_record_count") or 0),
        expiring_record_count=int(k28.get("expiring_record_count") or 0),
        accuracy_gain_rate=k28.get("accuracy_gain_rate"),
    )
    payload = dict(context.hooks.redactor.redact("S-N4", payload))
    record_step(context.recorder, "S-N4", base_record_fields("S-N4", state, context))
    return {"partial_context": [{"step_id": "S-N4", **payload}]}


async def node_S_N5_apply_subscription_state(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구획 2 진입 노드 — 구독 상태 갱신(멱등 처리) → `K-29`.

    **사람 확인** — 결제는 완료·상태는 미갱신 불일치는 자동으로 넘기지 않음(③ 4-7절).
    """
    trigger = TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION
    deadline_at = state.get("deadline_at") or compute_deadline_at(
        trigger, now_ms(), context.settings
    )
    payment_id = str(context.input_of("payment_id", ""))
    idempotency_key = build_idempotency_key("payment_id", payment_id or "unknown")
    decision = evaluate_write_gate(
        "R-13", context, idempotency_key=idempotency_key, guards_met={"idempotency_key": True}
    )
    record_step(
        context.recorder,
        "S-N5",
        base_record_fields(
            "S-N5",
            state,
            context,
            deadline_at=int(deadline_at),
            **_audit_fields("R-13", "허용" if decision.allowed else decision.reason),
        ),
    )
    base: dict[str, Any] = {"trigger_kind": trigger, "deadline_at": int(deadline_at)}
    if not decision.allowed:
        return merged(
            base, halt_to_landing("S-N5", LandingReason.TOOL_DENIED, {"reason": decision.reason})
        )
    try:
        payload = r13.apply_subscription_state(
            member_id=str(context.input_of("member_id", "")),
            plan_type=SubscriptionState.PREMIUM.value,
            applied_at=now_ms(),
            payment_id=payment_id,
            retention_policy="무제한",
            state_idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        return merged(
            base, halt_to_landing("S-N5", LandingReason.PRECHECK_FAILED, {"detail": str(exc)})
        )
    return merged(
        base,
        {
            "subscription_state": SubscriptionState.PREMIUM,
            "partial_context": [{"step_id": "S-N5", "K-29": payload}],
        },
    )


async def node_S_N6_release_retention(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`R-16` 이력 보관 기간 해제 — 무제한. ③ 11절 구획 2의 **재개 경계 단계**임.

    **사람 확인** — 돈을 받고 기능을 못 준 상태라 자동 무시 금지(`V-10` 25번).
    """
    verdict = check_deadline("S-N6", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-N6", base_record_fields("S-N6", state, context))
        return verdict.update
    k29 = _fragment_value(state, "K-29") or {}
    idempotency_key = str(k29.get("state_idempotency_key") or "")
    decision = evaluate_write_gate(
        "R-16",
        context,
        idempotency_key=idempotency_key,
        guards_met={"no_delete_tool": True, "baseline_filled": True},
    )
    record_step(
        context.recorder,
        "S-N6",
        base_record_fields(
            "S-N6",
            state,
            context,
            **_audit_fields("R-16", "허용" if decision.allowed else decision.reason),
        ),
    )
    if not decision.allowed:
        return halt_to_landing("S-N6", LandingReason.TOOL_DENIED, {"reason": decision.reason})
    if not await context.idempotency.claim(idempotency_key or "unknown"):
        return note_failure("S-N6", LandingReason.IDEMPOTENCY_REPLAYED)
    try:
        payload = r16.apply_retention_policy(
            member_id=str(k29.get("member_id", "")),
            retention_policy="무제한",
            idempotency_key=idempotency_key,
            applied_at=now_ms(),
        )
    except ValueError as exc:
        return halt_to_landing("S-N6", LandingReason.TOOL_DENIED, {"detail": str(exc)})
    return {
        "resume_cursor": {
            "boundary_step": "S-N6",
            "resume_unit": "payment_id",
            "idempotency_key": idempotency_key,
        },
        "partial_context": [{"step_id": "S-N6", "retention": payload}],
    }


async def node_S_N7_reply_retention(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """이력 보관 해제 완료 회신. 확인되지 않으면 회신하지 않음(④ `R-16` 중단 조건 ⓓ)."""
    verdict = check_deadline("S-N7", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-N7", base_record_fields("S-N7", state, context))
        return verdict.update
    retention = _fragment_value(state, "retention") or {}
    try:
        payload = r16.build_retention_reply(
            member_id=str(retention.get("member_id", "")),
            retention_policy=str(retention.get("retention_policy", "")),
            applied_at=int(retention.get("applied_at") or now_ms()),
            retention_result=str(retention.get("retention_result", "")),
        )
    except ValueError as exc:
        record_step(context.recorder, "S-N7", base_record_fields("S-N7", state, context))
        return halt_to_landing("S-N7", LandingReason.PRECHECK_FAILED, {"detail": str(exc)})
    record_step(context.recorder, "S-N7", base_record_fields("S-N7", state, context))
    return {"partial_context": [{"step_id": "S-N7", "retention_reply": payload}]}


async def node_S_N8_audit_state_change(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구독 상태 변경 감사 기록(`V-10` 29번). 규제 필수 기록이라 승인 문을 두지 않음."""
    verdict = check_deadline("S-N8", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-N8", base_record_fields("S-N8", state, context))
        return verdict.update
    k29 = _fragment_value(state, "K-29") or {}
    payload = r13.build_state_audit(
        member_id=str(k29.get("member_id", "")),
        plan_type=str(k29.get("plan_type", "")),
        applied_at=int(k29.get("applied_at") or now_ms()),
        state_idempotency_key=str(k29.get("state_idempotency_key", "")),
    )
    record_step(
        context.recorder,
        "S-N8",
        base_record_fields("S-N8", state, context, **_audit_fields("S-6", "기록")),
    )
    return {"partial_context": [{"step_id": "S-N8", "audit": payload}]}


async def node_S_N9_show_activation(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """프리미엄 활성화 완료 표시. 보관 해제 회신이 없으면 완료 표시를 하지 않음."""
    verdict = check_deadline("S-N9", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-N9", base_record_fields("S-N9", state, context))
        return verdict.update
    k29 = _fragment_value(state, "K-29") or {}
    reply = _fragment_value(state, "retention_reply") or {}
    try:
        payload = r13.build_activation_notice(
            member_id=str(k29.get("member_id", "")),
            plan_type=str(k29.get("plan_type", "")),
            retention_applied=bool(reply),
        )
    except ValueError as exc:
        record_step(context.recorder, "S-N9", base_record_fields("S-N9", state, context))
        return halt_to_landing("S-N9", LandingReason.PRECHECK_FAILED, {"detail": str(exc)})
    payload = dict(context.hooks.redactor.redact("S-N9", payload))
    record_step(context.recorder, "S-N9", base_record_fields("S-N9", state, context))
    return {"partial_context": [{"step_id": "S-N9", "activation": payload}]}


async def node_S_N10_landing_undelivered_queue(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1-2절이 `S-N`에 고른 값 1개(`사람 확인`)대로 만듦.

    **여기서 상한을 다시 쓰지 않음** — 모델 호출 0건 · 재시도 0건임.
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    payload = r13.build_undelivered_entry(
        member_id=str(context.input_of("member_id", "")), fallback_reason=reason
    )
    record_step(
        context.recorder,
        "S-N10",
        base_record_fields(
            "S-N10", state, context, **_audit_fields("S-6", "미전달 큐 적재")
        ),
    )
    return {
        "fallback_reason": reason,
        "partial_context": [{"step_id": "S-N10", "landing": payload}],
    }


def _audit_fields(tool: str, result: str) -> dict[str, Any]:
    return {
        "도구명": tool,
        "입력 요약": {"result": result},
        "결과": result,
        "소요시간": None,
        "동의 시각·버전": None,
        "멱등성 키 해시": None,
    }


def _fragment_value(state: LunchPickState, key: str) -> Any:
    for fragment in reversed(list(state.get("partial_context") or ())):
        if key in fragment:
            return fragment[key]
    return None


NODE_FUNCTIONS: dict[str, Any] = {
    "S-N1": node_S_N1_receive_memory_limit_signal,
    "S-N2": node_S_N2_check_free_plan,
    "S-N3": node_S_N3_deliver_notice,
    "S-N4": node_S_N4_show_subscription_notice,
    "S-N5": node_S_N5_apply_subscription_state,
    "S-N6": node_S_N6_release_retention,
    "S-N7": node_S_N7_reply_retention,
    "S-N8": node_S_N8_audit_state_change,
    "S-N9": node_S_N9_show_activation,
    "S-N10": node_S_N10_landing_undelivered_queue,
}
