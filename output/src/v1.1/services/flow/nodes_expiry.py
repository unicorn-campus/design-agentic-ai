"""③ 4-8절 스케줄 배치 `S-X`(해지 예약 만료 전환) — 노드 8개.

담당자 — `S-X6`은 `R-16`, 나머지 7개는 `R-11`임.
루프 `L-3`(`S-X3` ~ `S-X7`)의 카운터 갱신 주체는 `S-X3`임(③ 6절 11번).
`S-X4`가 **되돌릴 수 없는 단계**이며 ③ 11절 재개 경계 단계임.
"""

from __future__ import annotations

from typing import Any

from common.budget import compute_deadline_at
from common.checkpointer import build_idempotency_key
from common.state import LunchPickState, SubscriptionState, TriggerKind

from ..payment_service.agents import r11_expiry_downgrade as r11
from ..recommendation_history_service.agents import r16_retention_policy as r16
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

_X_RECORD_KEYS = (
    "전환 대상 건수",
    "판정 불가로 건너뛴 건수",
    "커밋 성공·실패 건수",
    "열람 제한 재적용 실패 건수",
    "배치 상태",
    "실행 창 초과 여부",
)


async def node_S_X1_acquire_lock(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """진입 노드 — 마감선(실행 창)을 넣음. 잠금 실패는 중복 실행이므로 즉시 종료함."""
    trigger = TriggerKind.BATCH_CANCEL_EXPIRY
    deadline_at = state.get("deadline_at") or compute_deadline_at(
        trigger, now_ms(), context.settings
    )
    try:
        payload = r11.acquire_run_lock(
            batch_run_id=str(context.input_of("batch_run_id", context.request_id)),
            run_started_at=int(context.input_of("run_started_at", now_ms())),
            execution_lock_id=str(context.input_of("execution_lock_id", "")),
        )
    except RuntimeError as exc:
        record_step(
            context.recorder,
            "S-X1",
            base_record_fields("S-X1", state, context, **_audit_fields("S-6", "잠금 실패")),
        )
        return merged(
            {"trigger_kind": trigger, "deadline_at": int(deadline_at), "iteration_count": 0},
            halt_to_landing("S-X1", LandingReason.RUN_LOCK_FAILED, {"detail": str(exc)}),
        )
    record_step(
        context.recorder,
        "S-X1",
        base_record_fields(
            "S-X1",
            state,
            context,
            deadline_at=int(deadline_at),
            **_audit_fields("S-6", "잠금 획득"),
        ),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "iteration_count": 0,
        "partial_context": [{"step_id": "S-X1", **payload}],
    }


async def node_S_X2_collect_targets(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """전환 대상 조회 → `K-30`. 실패하면 사람 확인(착지)로 감."""
    verdict = check_deadline("S-X2", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-X2", base_record_fields("S-X2", state, context))
        return verdict.update
    rows = context.source_of("target_rows")
    if rows is None:
        record_step(
            context.recorder,
            "S-X2",
            base_record_fields("S-X2", state, context, **_x_fields(0, 0, "0/0", 0, "실패")),
        )
        return halt_to_landing("S-X2", LandingReason.STEP_EXHAUSTED)
    payload = r11.collect_targets(
        batch_run_id=str(context.input_of("batch_run_id", context.request_id)),
        target_rows=rows,
    )
    record_step(
        context.recorder,
        "S-X2",
        base_record_fields(
            "S-X2", state, context, **_x_fields(payload["target_count"], 0, "0/0", 0, "진행")
        ),
    )
    return {"partial_context": [{"step_id": "S-X2", "K-30": payload}]}


async def node_S_X3_check_transition_precondition(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """루프 진입 노드 — `iteration_count`를 올리는 **단 하나의 자리**.

    사전 조건 — 해지 철회 여부·결제 실패 7일 유예 경과. 판정 불가면 강등하지 않음(⑥ `B-26`).
    """
    verdict = check_deadline("S-X3", state, context)
    iteration = int(state.get("iteration_count") or 0)
    if verdict.blocked:
        record_step(context.recorder, "S-X3", base_record_fields("S-X3", state, context))
        return verdict.update
    k30 = _fragment_value(state, "K-30") or {}
    rows = list(k30.get("target_rows", ()))
    if iteration >= len(rows):
        return {"iteration_count": iteration}
    row = rows[iteration]
    result = r11.check_transition_precondition(
        member_id=str(row.get("member_id", "")),
        scheduled_downgrade_on=row.get("scheduled_downgrade_on"),
        run_on=context.input_of("run_on"),
        cancel_withdrawn=context.source_of("cancel_withdrawn"),
        payment_grace_elapsed=context.source_of("payment_grace_elapsed"),
    )
    record_step(
        context.recorder,
        "S-X3",
        base_record_fields(
            "S-X3",
            state,
            context,
            **_x_fields(
                len(rows), 0 if result["precheck_passed"] else 1, "0/0", 0, "진행"
            ),
        ),
    )
    update: dict[str, Any] = {
        "iteration_count": iteration + 1,
        "precheck_result": {**result, "loop_index": iteration, "target_count": len(rows)},
    }
    if not result["precheck_passed"]:
        update = merged(update, note_failure("S-X3", LandingReason.PRECHECK_FAILED, result))
    return update


async def node_S_X4_commit_downgrade(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구독 상태 무료 전환 커밋 — **되돌릴 수 없는 단계**이며 ③ 11절 재개 경계임.

    ⑥ `R-11`의 제한 장치 6개를 승인 문으로 씀(무인 배치라 사람이 낄 자리가 없음).
    중복 방지 키 = `회원 + 전환 예정일` 조합 키.
    """
    verdict = check_deadline("S-X4", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-X4", base_record_fields("S-X4", state, context))
        return verdict.update
    precheck = dict(state.get("precheck_result") or {})
    if not precheck.get("precheck_passed"):
        record_step(
            context.recorder,
            "S-X4",
            base_record_fields("S-X4", state, context, **_x_fields(0, 1, "0/0", 0, "진행")),
        )
        return note_failure("S-X4", LandingReason.PRECHECK_FAILED, precheck)

    k30 = _fragment_value(state, "K-30") or {}
    rows = list(k30.get("target_rows", ()))
    index = int(precheck.get("loop_index") or 0)
    row = rows[index] if index < len(rows) else {}
    member_id = str(row.get("member_id") or "unknown")
    scheduled_on = str(row.get("scheduled_downgrade_on") or "unknown")
    idempotency_key = build_idempotency_key(
        "member_and_scheduled_downgrade_on", member_id, scheduled_on
    )
    decision = evaluate_write_gate(
        "R-11",
        context,
        idempotency_key=idempotency_key,
        guards_met={
            "precondition_passed": True,
            "idempotency_key": True,
            "run_lock": bool(context.input_of("execution_lock_id", "")),
            "target_count_cap": True,
            "keep_previous_on_failure": True,
            "operator_post_notice": True,
        },
    )
    record_step(
        context.recorder,
        "S-X4",
        base_record_fields(
            "S-X4",
            state,
            context,
            **_x_fields(len(rows), 0, "1/0" if decision.allowed else "0/1", 0, "진행"),
            **_audit_fields("R-11", "허용" if decision.allowed else decision.reason),
        ),
    )
    if not decision.allowed:
        return halt_to_landing("S-X4", LandingReason.TOOL_DENIED, {"reason": decision.reason})
    if not await context.idempotency.claim(idempotency_key):
        return note_failure("S-X4", LandingReason.IDEMPOTENCY_REPLAYED, {"member_id": member_id})

    payload = r11.commit_downgrade(
        member_id=member_id,
        downgrade_idempotency_key=idempotency_key,
        view_cutoff_on=str(context.input_of("view_cutoff_on", scheduled_on)),
        committed_at=now_ms(),
    )
    return {
        "resume_cursor": {
            "boundary_step": "S-X4",
            "resume_unit": "member_and_scheduled_downgrade_on",
            "idempotency_key": idempotency_key,
        },
        "partial_context": [{"step_id": "S-X4", "K-31": payload}],
    }


async def node_S_X5_propagate_state(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구독 상태 갱신 전파 — 무료(루프 내). ③ 6절 15번 갱신 주체임."""
    verdict = check_deadline("S-X5", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-X5", base_record_fields("S-X5", state, context))
        return verdict.update
    k31 = _fragment_value(state, "K-31") or {}
    if not k31:
        record_step(
            context.recorder,
            "S-X5",
            base_record_fields("S-X5", state, context, **_x_fields(0, 1, "0/0", 0, "진행")),
        )
        return {}
    payload = r11.propagate_state(
        member_id=str(k31.get("member_id", "")), plan_type=SubscriptionState.FREE.value
    )
    record_step(
        context.recorder,
        "S-X5",
        base_record_fields(
            "S-X5",
            state,
            context,
            **_x_fields(0, 0, "1/0", 0, "진행"),
            **_audit_fields("R-13", "전파"),
        ),
    )
    return {
        "subscription_state": SubscriptionState.FREE,
        "partial_context": [{"step_id": "S-X5", **payload}],
    }


async def node_S_X6_reapply_retention(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`R-16` 이력 보관 기간 재적용(루프 내).

    **사람 확인** — 열람 제한 실패는 과다 노출이므로 자동 무시 금지(③ 4-8절 · `V-10` 25번).
    """
    verdict = check_deadline("S-X6", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-X6", base_record_fields("S-X6", state, context))
        return verdict.update
    k31 = _fragment_value(state, "K-31") or {}
    if not k31:
        record_step(
            context.recorder,
            "S-X6",
            base_record_fields("S-X6", state, context, **_x_fields(0, 1, "0/0", 0, "진행")),
        )
        return {}
    decision = evaluate_write_gate(
        "R-16",
        context,
        idempotency_key=str(k31.get("downgrade_idempotency_key", "")),
        guards_met={"no_delete_tool": True, "baseline_filled": bool(k31.get("view_cutoff_on"))},
    )
    if not decision.allowed:
        record_step(
            context.recorder,
            "S-X6",
            base_record_fields(
                "S-X6",
                state,
                context,
                **_x_fields(0, 0, "0/0", 1, "진행"),
                **_audit_fields("R-16", decision.reason),
            ),
        )
        return halt_to_landing("S-X6", LandingReason.TOOL_DENIED, {"reason": decision.reason})
    try:
        payload = r16.apply_retention_policy(
            member_id=str(k31.get("member_id", "")),
            retention_policy="30일",
            idempotency_key=str(k31.get("downgrade_idempotency_key", "")),
            applied_at=now_ms(),
            view_cutoff_on=k31.get("view_cutoff_on"),
            retention_days=k31.get("retention_days"),
        )
    except ValueError as exc:
        record_step(
            context.recorder,
            "S-X6",
            base_record_fields(
                "S-X6",
                state,
                context,
                **_x_fields(0, 0, "0/0", 1, "진행"),
                **_audit_fields("R-16", str(exc)),
            ),
        )
        return halt_to_landing("S-X6", LandingReason.TOOL_DENIED, {"detail": str(exc)})
    record_step(
        context.recorder,
        "S-X6",
        base_record_fields(
            "S-X6",
            state,
            context,
            **_x_fields(0, 0, "1/0", 0, "진행"),
            **_audit_fields("R-16", "적용"),
        ),
    )
    return {"partial_context": [{"step_id": "S-X6", "retention": payload}]}


async def node_S_X7_record_transition(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """전환 실행 기록(루프 내). 규제 필수 기록이라 승인 문을 두지 않음."""
    verdict = check_deadline("S-X7", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-X7", base_record_fields("S-X7", state, context))
        return verdict.update
    k31 = _fragment_value(state, "K-31") or {}
    payload = r11.build_transition_audit(
        member_id=str(k31.get("member_id", "")),
        downgrade_idempotency_key=str(k31.get("downgrade_idempotency_key", "")),
        committed_at=int(k31.get("committed_at") or now_ms()),
    )
    record_step(
        context.recorder,
        "S-X7",
        base_record_fields(
            "S-X7",
            state,
            context,
            **_x_fields(0, 0, "1/0", 0, "진행"),
            **_audit_fields("S-6", "기록"),
        ),
    )
    return {"partial_context": [{"step_id": "S-X7", "audit": payload}]}


async def node_S_X8_landing_keep_premium(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1-2절이 `S-X`에 고른 값 1개(`사람 확인`)대로 만듦.

    사용자에게 불리한 자동 강등을 하지 않음. **여기서 상한을 다시 쓰지 않음** — 쓰기 0건임.
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    payload = r11.build_expiry_landing(
        batch_run_id=str(context.input_of("batch_run_id", context.request_id)),
        downgraded_member_count=0,
        skipped_member_ids=[
            str((state.get("precheck_result") or {}).get("member_id", ""))
        ],
        fallback_reason=reason,
    )
    record_step(
        context.recorder,
        "S-X8",
        base_record_fields(
            "S-X8",
            state,
            context,
            **_x_fields(0, len(payload["skipped_member_ids"]), "0/0", 0, "사람 확인"),
            **_audit_fields("S-6", "사람 확인 알림"),
        ),
    )
    return {
        "fallback_reason": reason,
        "partial_context": [{"step_id": "S-X8", "landing": payload}],
    }


def _x_fields(
    targets: int, skipped: int, commits: str, retention_failures: int, status: str
) -> dict[str, Any]:
    return dict(
        zip(
            _X_RECORD_KEYS,
            (targets, skipped, commits, retention_failures, status, False),
            strict=True,
        )
    )


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
    "S-X1": node_S_X1_acquire_lock,
    "S-X2": node_S_X2_collect_targets,
    "S-X3": node_S_X3_check_transition_precondition,
    "S-X4": node_S_X4_commit_downgrade,
    "S-X5": node_S_X5_propagate_state,
    "S-X6": node_S_X6_reapply_retention,
    "S-X7": node_S_X7_record_transition,
    "S-X8": node_S_X8_landing_keep_premium,
}
