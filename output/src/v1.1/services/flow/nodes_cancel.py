"""③ 4-6절 동기 요청 `S-C`(구독 해지) — 노드 11개.

담당자 — `S-C1`은 계약 대상 밖, `S-C10`은 `R-10`, 나머지 9개는 `R-9`임.

`S-C5`가 **사람 확인 지점**이며 되돌릴 수 없는 `S-C10`(`C-12`)보다 앞 단계임.
`S-C10`은 응답을 닫은 뒤 도는 후처리라 어느 마감선에도 들어가지 않음(③ 4-6절 · `J-20`).
"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from common.budget import compute_deadline_at
from common.checkpointer import build_idempotency_key
from common.state import LunchPickState, PgCancelStatus, TriggerKind

from ..payment_service.agents import r9_cancel_schedule as r9, r10_pg_stop as r10
from ._common import (
    LandingReason,
    base_record_fields,
    call_context_of,
    check_deadline,
    halt_to_landing,
    merged,
    note_failure,
    now_ms,
    record_step,
)
from .context import FlowContext
from .gates import build_interrupt_payload, evaluate_human_gate

__all__ = ["NODE_FUNCTIONS"]


async def node_S_C1_user_entry(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """단말 구간이라 API 예산 밖임(계약 대상 밖)."""
    record_step(context.recorder, "S-C1", base_record_fields("S-C1", state, context))
    return {}


async def node_S_C2_accept_cancel_request(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """진입 노드 — 확인 앞 구간의 마감선을 넣음."""
    trigger = TriggerKind.SYNC_CANCEL
    deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    payload = r9.accept_cancel_request(
        cancel_request_id=str(context.input_of("cancel_request_id", context.request_id)),
        member_id=str(context.input_of("member_id", "")),
        requested_at=int(context.input_of("requested_at", now_ms())),
        deadline_at=int(deadline_at),
        trigger_kind=trigger.value,
    )
    record_step(
        context.recorder,
        "S-C2",
        base_record_fields("S-C2", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-C2", **payload}],
    }


async def node_S_C3_check_cancel_precondition(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 조건 — 구독 활성·남은 기간·복귀 제안 소진 여부 → `K-24`.

    **안전 종료** — 구독 상태를 못 읽으면 해지를 예약하지 않음(③ 4-6절).
    PG 결제 ID는 `S-S10`이 적재한 값을 여기서 읽어 `S-C10`으로 실어 보냄.
    """
    verdict = check_deadline("S-C3", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-C3", base_record_fields("S-C3", state, context))
        return verdict.update
    frame = _fragment_of(state, "S-C2")
    result = r9.check_cancel_precondition(
        cancel_request_id=str(frame.get("cancel_request_id", "")),
        member_id=str(frame.get("member_id", "")),
        remaining_days=context.source_of("remaining_days"),
        scheduled_downgrade_on=context.source_of("scheduled_downgrade_on"),
        winback_offer_used=context.source_of("winback_offer_used"),
        retention_notice=str(context.source_of("retention_notice", "")),
        pg_payment_id=context.source_of("pg_payment_id"),
    )
    record_step(context.recorder, "S-C3", base_record_fields("S-C3", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if not result["precheck_passed"]:
        update = merged(update, halt_to_landing("S-C3", LandingReason.PRECHECK_FAILED, result))
    return update


async def node_S_C4_show_winback_offer(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """복귀 유도 제안 표시. 실패하면 부분 결과로 계속 — 제안 없이 해지 흐름 진행(③ 4-6절)."""
    verdict = check_deadline("S-C4", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-C4", base_record_fields("S-C4", state, context))
        return verdict.update
    precheck = dict(state.get("precheck_result") or {})
    payload = r9.build_winback_offer(
        winback_offer_used=bool(precheck.get("winback_offer_used", True))
    )
    record_step(context.recorder, "S-C4", base_record_fields("S-C4", state, context))
    return {"partial_context": [{"step_id": "S-C4", **payload}]}


async def node_S_C5_human_confirm(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """**사람 확인 지점** — 해지 확인 모달 통과(`V-10` 2번 · ⑥ `B-13` · `O-C9`).

    되묻기 3으로 정한 형태 — 노드 앞에서 멈추고 확인 대기 상태를 남김.
    다시 들어오는 자리도 `S-C5`임(멈춘 자리와 같은 단계 식별자).
    """
    precheck = dict(state.get("precheck_result") or {})
    shown = r9.build_confirm_prompt(
        remaining_days=int(precheck.get("remaining_days") or 0),
        retention_notice=str(precheck.get("retention_notice", "")),
    )
    answer = interrupt(build_interrupt_payload("S-C5", shown))
    confirmed = bool((answer or {}).get("confirmed"))
    evidence = {
        "cancel_confirm_id": (answer or {}).get("cancel_confirm_id", ""),
        "confirmed_at": (answer or {}).get("confirmed_at", now_ms()),
        "approver_ref": (answer or {}).get("approver_ref", ""),
        "displayed_retention_notice": shown["displayed_retention_notice"],
        "displayed_remaining_days": shown["displayed_remaining_days"],
        "shown_items": shown["shown_items"],
        "subject": str(precheck.get("cancel_request_id", "")),
        "approval_expires_at": (answer or {}).get("approval_expires_at"),
    }
    record_step(
        context.recorder,
        "S-C5",
        base_record_fields(
            "S-C5",
            state,
            context,
            **{
                "승인 ID 해시": None,
                "표시한 고지·안내 항목 목록": shown["shown_items"],
                "승인 시각": evidence["confirmed_at"],
                "만료 여부": False,
                "미승인 종료 사유": None if confirmed else "미확인",
            },
        ),
    )
    if not confirmed or not evidence["cancel_confirm_id"]:
        return halt_to_landing("S-C5", LandingReason.APPROVAL_ABSENT)
    return {"approval_evidence": evidence}


async def node_S_C6_collect_cancel_reason(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """해지 사유 수집(선택형 4종). 확인 뒤 구간의 마감선을 새로 넣음(③ 6절 2번).

    사유는 필수가 아님 — 없으면 그대로 예약을 진행함(③ 4-6절).
    """
    trigger = TriggerKind.SYNC_CANCEL
    deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    payload = r9.collect_cancel_reason(
        cancel_reason_code=context.input_of("cancel_reason_code")
    )
    record_step(
        context.recorder,
        "S-C6",
        base_record_fields("S-C6", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-C6", "K-26": payload}],
    }


async def node_S_C7_register_cancel_schedule(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """**해지 예약 등록** — ③ 11절 `S-C` 재개 경계 단계임.

    중복 방지 키 = `회원 + 전환 예정일` 조합 키. 같은 키가 다시 오면 바깥을 다시 바꾸지 않음.
    """
    verdict = check_deadline("S-C7", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-C7", base_record_fields("S-C7", state, context))
        return verdict.update

    precheck = dict(state.get("precheck_result") or {})
    evidence = dict(state.get("approval_evidence") or {})
    member_id = str(precheck.get("member_id") or "unknown")
    scheduled_on = str(precheck.get("scheduled_downgrade_on") or "unknown")
    cancel_idempotency_key = build_idempotency_key(
        "member_and_scheduled_downgrade_on", member_id, scheduled_on
    )
    decision = evaluate_human_gate(
        "R-9",
        context,
        state,
        idempotency_key=cancel_idempotency_key,
        guards_met={"confirm_modal_passed": bool(evidence.get("cancel_confirm_id"))},
    )
    record_step(
        context.recorder,
        "S-C7",
        base_record_fields(
            "S-C7",
            state,
            context,
            **{
                "도구명": "R-9",
                "입력 요약": {"member_id": member_id},
                "결과": "허용" if decision.allowed else decision.reason,
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    if not decision.allowed:
        return halt_to_landing("S-C7", LandingReason.APPROVAL_ABSENT, {"reason": decision.reason})
    if not await context.idempotency.claim(cancel_idempotency_key):
        return note_failure("S-C7", LandingReason.IDEMPOTENCY_REPLAYED, {"member_id": member_id})

    try:
        schedule = r9.register_cancel_schedule(
            cancel_schedule_id=str(context.input_of("cancel_schedule_id", context.request_id)),
            scheduled_downgrade_on=scheduled_on,
            remaining_days=int(precheck.get("remaining_days") or 0),
            retention_notice=str(precheck.get("retention_notice", "")),
            cancel_idempotency_key=cancel_idempotency_key,
            cancel_confirm_id=str(evidence.get("cancel_confirm_id") or ""),
            confirmed_at=str(evidence.get("confirmed_at") or ""),
        )
    except (PermissionError, ValueError) as exc:
        return halt_to_landing("S-C7", LandingReason.APPROVAL_ABSENT, {"detail": str(exc)})

    stop_request = r9.build_pg_stop_request(
        pg_payment_id=precheck.get("pg_payment_id"),
        cancel_schedule_id=schedule["cancel_schedule_id"],
        pg_cancel_idempotency_key=build_idempotency_key(
            "pg_payment_and_stop",
            str(precheck.get("pg_payment_id") or "unknown"),
            schedule["cancel_schedule_id"],
        ),
    )
    return {
        "cancel_schedule": schedule,
        "resume_cursor": {
            "boundary_step": "S-C7",
            "resume_unit": "member_and_scheduled_downgrade_on",
            "idempotency_key": cancel_idempotency_key,
        },
        "partial_context": [{"step_id": "S-C7", "K-36": stop_request}],
    }


async def node_S_C8_audit_cancel(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """해지 예약 감사 기록(`V-10` 29번). 규제 필수 기록이라 승인 문을 두지 않음."""
    verdict = check_deadline("S-C8", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-C8", base_record_fields("S-C8", state, context))
        return verdict.update
    schedule = dict(state.get("cancel_schedule") or {})
    payload = r9.build_cancel_audit(
        cancel_schedule_id=str(schedule.get("cancel_schedule_id", "")),
        cancel_reason_code=(_fragment_value(state, "K-26") or {}).get("cancel_reason_code"),
        cancel_idempotency_key=str(schedule.get("cancel_idempotency_key", "")),
    )
    record_step(
        context.recorder,
        "S-C8",
        base_record_fields(
            "S-C8",
            state,
            context,
            **{
                "도구명": "S-6",
                "입력 요약": {"cancel_schedule_id": payload["cancel_schedule_id"]},
                "결과": "기록",
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    return {"partial_context": [{"step_id": "S-C8", "audit": payload}]}


async def node_S_C9_show_cancel_result(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """해지 예약 완료 표시 → `K-27`. 출력측 검사·가리기를 지남(⑥ `O-C11`)."""
    verdict = check_deadline("S-C9", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-C9", base_record_fields("S-C9", state, context))
        return verdict.update
    schedule = dict(state.get("cancel_schedule") or {})
    payload = r9.build_cancel_response(
        cancel_schedule_id=str(schedule.get("cancel_schedule_id", "")),
        cancel_state=str(schedule.get("cancel_state", "")),
        scheduled_downgrade_on=str(schedule.get("scheduled_downgrade_on", "")),
        remaining_days=int(schedule.get("remaining_days") or 0),
        retention_notice=str(schedule.get("retention_notice", "")),
        cancel_idempotency_key=str(schedule.get("cancel_idempotency_key", "")),
    )
    payload = dict(context.hooks.redactor.redact("S-C9", payload))
    record_step(context.recorder, "S-C9", base_record_fields("S-C9", state, context))
    return {"partial_context": [{"step_id": "S-C9", "K-27": payload}]}


async def node_S_C10_stop_pg(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`R-10` PG 정기 결제 중지 — **되돌릴 수 없는 도구이며 승인 문(`S-C5`) 뒤에 있음.**

    응답 후 후처리라 마감선 밖임. 실패해도 **해지 예약을 되돌리지 않음**(③ 4-6절 · ⑥ `B-23`) —
    `pg_cancel_status = 실패`로 두고 재시도 큐 + 사람 확인 대상으로 표시함.
    """
    stop_request = _fragment_value(state, "K-36") or {}
    schedule = dict(state.get("cancel_schedule") or {})
    idempotency_key = str(stop_request.get("pg_cancel_idempotency_key") or "")
    decision = evaluate_human_gate(
        "C-12",
        context,
        state,
        idempotency_key=idempotency_key,
        guards_met={"reservation_commit_success": bool(schedule.get("cancel_schedule_id"))},
    )
    if not decision.allowed:
        record_step(
            context.recorder,
            "S-C10",
            base_record_fields(
                "S-C10",
                state,
                context,
                **_pg_record_fields(
                    result_enum="차단",
                    status=PgCancelStatus.FAILED.value,
                    attempts=0,
                    error_type=None,
                    commit_ok=bool(schedule.get("cancel_schedule_id")),
                ),
            ),
        )
        return merged(
            {"pg_cancel_status": PgCancelStatus.FAILED},
            note_failure("S-C10", LandingReason.TOOL_DENIED, {"reason": decision.reason}),
        )

    try:
        result = await r10.stop_recurring_payment(
            pg_payment_id=stop_request.get("pg_payment_id"),
            cancel_schedule_id=stop_request.get("cancel_schedule_id"),
            pg_cancel_idempotency_key=idempotency_key,
            tool=context.tool("C-12"),
            call_context=call_context_of(
                state,
                context,
                completed_steps=("S-C5", "S-C7"),
                approval_evidence=state.get("approval_evidence"),
            ),
        )
    except (PermissionError, ValueError) as exc:
        record_step(
            context.recorder,
            "S-C10",
            base_record_fields(
                "S-C10",
                state,
                context,
                **_pg_record_fields(
                    result_enum="미호출",
                    status=PgCancelStatus.FAILED.value,
                    attempts=0,
                    error_type=None,
                    commit_ok=bool(schedule.get("cancel_schedule_id")),
                ),
            ),
        )
        return merged(
            {"pg_cancel_status": PgCancelStatus.FAILED},
            note_failure("S-C10", LandingReason.TOOL_DENIED, {"detail": str(exc)}),
        )

    output = dict(result.output)
    status = str(output.get("pg_cancel_status") or PgCancelStatus.PENDING.value)
    record_step(
        context.recorder,
        "S-C10",
        base_record_fields(
            "S-C10",
            state,
            context,
            **_pg_record_fields(
                result_enum=status,
                status=status,
                attempts=result.attempts,
                error_type=result.error_class.value if result.error_class else None,
                commit_ok=bool(schedule.get("cancel_schedule_id")),
            ),
        ),
    )
    update: dict[str, Any] = {"pg_cancel_status": PgCancelStatus(status)}
    if not result.ok:
        # 예약은 그대로 두고 실패만 남김 — 착지로 보내지 않음(사용자 응답은 이미 나갔음).
        update = merged(
            update, note_failure("S-C10", LandingReason.PG_UNRESOLVED, {"status": status})
        )
    return update


async def node_S_C11_landing_cancel_accepted(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1-2절이 `S-C`에 고른 값 1개(`사람 확인`)대로 만듦.

    **여기서 상한을 다시 쓰지 않음** — 외부 호출 0건 · 모델 호출 0건 · 비용 0원임.
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    payload = r9.build_cancel_landing(fallback_reason=reason)
    record_step(context.recorder, "S-C11", base_record_fields("S-C11", state, context))
    return {
        "fallback_reason": reason,
        "partial_context": [{"step_id": "S-C11", "landing": payload}],
    }


def _pg_record_fields(
    *, result_enum: str, status: str, attempts: int, error_type: str | None, commit_ok: bool
) -> dict[str, Any]:
    return {
        "도구명": "C-12",
        "멱등성 키 해시": None,
        "결과 열거값": result_enum,
        "pg_cancel_status": status,
        "error.type": error_type,
        "소요시간": None,
        "재시도 횟수": attempts,
        "예약 커밋 성공 여부": commit_ok,
        "입력 요약": {"commit_ok": commit_ok},
        "결과": result_enum,
        "동의 시각·버전": None,
        "호출자": "S-C10",
    }


def _fragment_of(state: LunchPickState, step_id: str) -> dict[str, Any]:
    for fragment in reversed(list(state.get("partial_context") or ())):
        if fragment.get("step_id") == step_id:
            return dict(fragment)
    return {}


def _fragment_value(state: LunchPickState, key: str) -> Any:
    for fragment in reversed(list(state.get("partial_context") or ())):
        if key in fragment:
            return fragment[key]
    return None


NODE_FUNCTIONS: dict[str, Any] = {
    "S-C1": node_S_C1_user_entry,
    "S-C2": node_S_C2_accept_cancel_request,
    "S-C3": node_S_C3_check_cancel_precondition,
    "S-C4": node_S_C4_show_winback_offer,
    "S-C5": node_S_C5_human_confirm,
    "S-C6": node_S_C6_collect_cancel_reason,
    "S-C7": node_S_C7_register_cancel_schedule,
    "S-C8": node_S_C8_audit_cancel,
    "S-C9": node_S_C9_show_cancel_result,
    "S-C10": node_S_C10_stop_pg,
    "S-C11": node_S_C11_landing_cancel_accepted,
}
