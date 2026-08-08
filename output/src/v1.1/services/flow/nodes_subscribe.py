"""③ 4-5절 동기 요청 `S-S`(구독 전환) — 노드 13개. 구획 2개(플랜 조회 · 결제).

담당자 — `S-S1`은 계약 대상 밖, `S-S2` ~ `S-S4`는 `R-12`, `S-S9`는 `R-8`, 나머지 8개는 `R-7`임.

`S-S7`이 **사람 확인 지점**이며 되돌릴 수 없는 `S-S9`(`C-9`)보다 **앞 단계**임 —
승인과 외부 호출을 갈라 둔 이유는 중단 지점이 있는 단계가 재개 때 처음부터 다시 실행되기 때문임
(③ 4-5절 · context7 MCP로 확인함 · 2026-08-08).
"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from common.budget import compute_deadline_at
from common.checkpointer import build_idempotency_key
from common.state import PAYMENT_RESULT_PENDING, LunchPickState, TriggerKind

from ..member_service.agents import r12_plan_view as r12
from ..payment_service.agents import r7_payment_request as r7, r8_pg_register as r8
from ._common import (
    LandingReason,
    base_record_fields,
    call_context_of,
    check_deadline,
    connector_failure_update,
    halt_to_landing,
    merged,
    note_failure,
    now_ms,
    record_step,
)
from .context import FlowContext
from .gates import build_interrupt_payload, evaluate_human_gate, evaluate_write_gate

__all__ = ["NODE_FUNCTIONS"]


async def node_S_S1_user_entry(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """단말 구간이라 API 예산 밖임(계약 대상 밖)."""
    record_step(context.recorder, "S-S1", base_record_fields("S-S1", state, context))
    return {}


async def node_S_S2_accept_plan_view(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """플랜 조회 구획 진입 노드 — 이 구획의 마감선을 넣음(③ 6절 2번 · 구간마다 새로 잡힘)."""
    trigger = TriggerKind.SYNC_SUBSCRIBE
    deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    payload = r12.accept_plan_view_request(
        plan_view_request_id=str(context.input_of("plan_view_request_id", context.request_id)),
        member_id=str(context.input_of("member_id", "")),
        requested_at=int(context.input_of("requested_at", now_ms())),
        deadline_at=int(deadline_at),
        trigger_kind=trigger.value,
    )
    record_step(
        context.recorder,
        "S-S2",
        base_record_fields("S-S2", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-S2", **payload}],
    }


async def node_S_S3_check_subscription(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 조건 — 구독 상태·중복 구독 여부. **안전 종료** — 이미 프리미엄이면 결제 진입 차단."""
    verdict = check_deadline("S-S3", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-S3", base_record_fields("S-S3", state, context))
        return verdict.update
    result = r12.check_subscription_state(
        member_id=str(context.input_of("member_id", "")),
        current_plan=context.source_of("current_plan"),
        subscription_state=context.source_of("subscription_state"),
        duplicate_subscription=bool(context.source_of("duplicate_subscription", False)),
        next_billing_date=context.source_of("next_billing_date"),
    )
    record_step(context.recorder, "S-S3", base_record_fields("S-S3", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if result["subscription_state"]:
        update["subscription_state"] = result["subscription_state"]
    if not result["precheck_passed"]:
        reason = (
            LandingReason.ALREADY_PREMIUM
            if result["subscription_state"] == "프리미엄" or result["duplicate_subscription"]
            else LandingReason.PRECHECK_FAILED
        )
        update = merged(update, halt_to_landing("S-S3", reason, result))
    return update


async def node_S_S4_show_plans(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """플랜 비교표·가격 표시. 실패하면 **부분 결과로 계속** — 캐시된 가격 + 낮춘 사유(③ 4-5절)."""
    verdict = check_deadline("S-S4", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-S4", base_record_fields("S-S4", state, context))
        return verdict.update
    precheck = dict(state.get("precheck_result") or {})
    live_monthly = context.source_of("price_monthly_krw")
    cached_monthly = context.source_of("cached_price_monthly_krw")
    try:
        payload = r12.build_plan_view(
            plan_comparison=context.source_of("plan_comparison", ()),
            price_monthly_krw=live_monthly if live_monthly is not None else cached_monthly,
            price_yearly_monthly_krw=context.source_of("price_yearly_monthly_krw")
            or context.source_of("cached_price_yearly_monthly_krw"),
            current_plan=str(precheck.get("current_plan", "")),
            price_source="실시간" if live_monthly is not None else "캐시",
            next_billing_date=precheck.get("next_billing_date"),
            fallback_notice=None if live_monthly is not None else "캐시된 가격을 보여 줌",
        )
    except ValueError as exc:
        record_step(context.recorder, "S-S4", base_record_fields("S-S4", state, context))
        return halt_to_landing("S-S4", LandingReason.PRECHECK_FAILED, {"detail": str(exc)})
    payload = dict(context.hooks.redactor.redact("S-S4", payload))
    record_step(context.recorder, "S-S4", base_record_fields("S-S4", state, context))
    return {"partial_context": [{"step_id": "S-S4", "K-17_view": payload}]}


async def node_S_S5_accept_payment_request(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """결제 구획 진입 노드 — 이 구획의 마감선을 새로 넣음."""
    trigger = TriggerKind.SYNC_SUBSCRIBE
    deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    payload = r7.accept_payment_request(
        payment_request_id=str(context.input_of("payment_request_id", context.request_id)),
        member_id=str(context.input_of("member_id", "")),
        plan_type=str(context.input_of("plan_type", "")),
        billing_cycle=str(context.input_of("billing_cycle", "")),
        amount_krw=int(context.input_of("amount_krw", 0)),
        requested_at=int(context.input_of("requested_at", now_ms())),
        deadline_at=int(deadline_at),
    )
    record_step(
        context.recorder,
        "S-S5",
        base_record_fields("S-S5", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-S5", "K-18": payload}],
    }


async def node_S_S6_build_disclosure(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 고지 구성 — 고지 없이 승인 화면을 띄우지 않음(`V-10` 31번 · ⑥ `B-21`)."""
    verdict = check_deadline("S-S6", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-S6", base_record_fields("S-S6", state, context))
        return verdict.update
    try:
        record = r7.build_disclosure(
            disclosure_id=str(context.input_of("disclosure_id", context.request_id)),
            auto_renewal_notice=str(context.source_of("auto_renewal_notice", "")),
            cancel_method_notice=str(context.source_of("cancel_method_notice", "")),
            disclosed_at=now_ms(),
        )
    except ValueError as exc:
        record_step(context.recorder, "S-S6", base_record_fields("S-S6", state, context))
        return halt_to_landing("S-S6", LandingReason.DISCLOSURE_MISSING, {"detail": str(exc)})
    record = dict(context.hooks.redactor.redact("S-S6", record))
    record_step(context.recorder, "S-S6", base_record_fields("S-S6", state, context))
    return {"disclosure_record": record}


async def node_S_S7_human_approval(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """**사람 확인 지점** — 금액·주기·고지를 다시 보여 주고 명시 승인을 받음(`V-10` 1번).

    되묻기 3으로 정한 형태 — **노드 앞에서 멈춤.** 확인 대기 상태를 남기고 응답을 닫음.
    다시 들어오는 자리도 `S-S7`임(멈춘 자리와 같은 단계 식별자).
    사람이 화면을 보는 시간은 어떤 마감선에도 들어가지 않음(③ 6절).
    """
    k18 = _fragment_value(state, "K-18") or {}
    disclosure = dict(state.get("disclosure_record") or {})
    shown = r7.build_approval_prompt(
        amount_krw=int(k18.get("amount_krw", 0)),
        billing_cycle=str(k18.get("billing_cycle", "")),
        disclosure_id=str(disclosure.get("disclosure_id", "")),
        auto_renewal_notice=str(disclosure.get("auto_renewal_notice", "")),
        cancel_method_notice=str(disclosure.get("cancel_method_notice", "")),
    )
    answer = interrupt(build_interrupt_payload("S-S7", shown))
    approved = bool((answer or {}).get("approved"))
    evidence = {
        "user_approval_id": (answer or {}).get("user_approval_id", ""),
        "approved_at": (answer or {}).get("approved_at", now_ms()),
        "approver_ref": (answer or {}).get("approver_ref", ""),
        "displayed_amount_krw": shown["displayed_amount_krw"],
        "displayed_billing_cycle": shown["displayed_billing_cycle"],
        "disclosure_id": shown["disclosure_id"],
        "approval_expires_at": (answer or {}).get("approval_expires_at"),
        "shown_items": shown["shown_items"],
        "subject": str(k18.get("payment_request_id", "")),
    }
    record_step(
        context.recorder,
        "S-S7",
        base_record_fields(
            "S-S7",
            state,
            context,
            **{
                "승인 ID 해시": None,
                "표시한 고지·안내 항목 목록": shown["shown_items"],
                "승인 시각": evidence["approved_at"],
                "만료 여부": False,
                "미승인 종료 사유": None if approved else "미승인",
            },
        ),
    )
    if not approved or not evidence["user_approval_id"]:
        return halt_to_landing("S-S7", LandingReason.APPROVAL_ABSENT)
    return {"approval_evidence": evidence}


async def node_S_S8_verify_and_key(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """결제 정보 검증 · 멱등 키 부여 → `K-21`.

    ③ 10-2절 설계 규칙 — 여기서 DB 커넥션을 반환하고 `S-S10`에서 다시 얻음(PG 왕복 동안 안 잡음).
    """
    verdict = check_deadline("S-S8", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-S8", base_record_fields("S-S8", state, context))
        return verdict.update
    k18 = _fragment_value(state, "K-18") or {}
    evidence = dict(state.get("approval_evidence") or {})
    idempotency_key = build_idempotency_key(
        "member_plan_and_payment_idempotency",
        str(k18.get("member_id") or "unknown"),
        str(k18.get("plan_type") or "unknown"),
        str(k18.get("payment_request_id") or "unknown"),
    )
    try:
        payload = r7.verify_and_key(
            payment_token=str(context.input_of("payment_token", "")),
            amount_krw=int(k18.get("amount_krw", 0)),
            billing_cycle=str(k18.get("billing_cycle", "")),
            idempotency_key=idempotency_key,
            user_approval_id=str(evidence.get("user_approval_id", "")),
            displayed_amount_krw=int(evidence.get("displayed_amount_krw", -1)),
            displayed_billing_cycle=str(evidence.get("displayed_billing_cycle", "")),
        )
    except ValueError as exc:
        record_step(context.recorder, "S-S8", base_record_fields("S-S8", state, context))
        return halt_to_landing("S-S8", LandingReason.APPROVAL_ABSENT, {"detail": str(exc)})
    record_step(context.recorder, "S-S8", base_record_fields("S-S8", state, context))
    return {
        "payment_idempotency_key": idempotency_key,
        "partial_context": [{"step_id": "S-S8", "K-21": payload}],
    }


async def node_S_S9_register_pg(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`R-8` PG 정기 결제 등록 — **되돌릴 수 없는 도구를 부르는 노드이며 승인 문 뒤에 있음.**

    자동 재시도 0회는 ③ 8-3절 소유 값이며 설정에서 커넥터 계층이 읽음.
    응답을 못 받으면 `확인 중`으로 두고 사람 확인으로 올림(③ 8-1-2절 · ⑥ `B-31`).
    """
    k21 = _fragment_value(state, "K-21") or {}
    idempotency_key = str(state.get("payment_idempotency_key") or "")
    decision = evaluate_human_gate(
        "C-9",
        context,
        state,
        idempotency_key=idempotency_key,
        guards_met={"pg_auto_retry_zero": context.settings.retry_count("S-S9") == 0},
    )
    if not decision.allowed:
        record_step(
            context.recorder,
            "S-S9",
            base_record_fields(
                "S-S9",
                state,
                context,
                **{
                    "도구명": "C-9",
                    "멱등성 키 해시": None,
                    "결과 열거값": "차단",
                    "pg_cancel_status": None,
                    "error.type": None,
                    "소요시간": None,
                    "재시도 횟수": 0,
                    "예약 커밋 성공 여부": None,
                    "입력 요약": {"reason": decision.reason},
                    "결과": "차단",
                    "동의 시각·버전": None,
                    "호출자": "S-S9",
                },
            ),
        )
        return halt_to_landing(
            "S-S9", LandingReason.APPROVAL_ABSENT, {"reason": decision.reason}
        )

    result = await r8.register_recurring_payment(
        payment_token=str(k21.get("payment_token", "")),
        amount_krw=int(k21.get("amount_krw", 0)),
        billing_cycle=str(k21.get("billing_cycle", "")),
        idempotency_key=idempotency_key,
        user_approval_id=str(k21.get("user_approval_id", "")),
        tool=context.tool("C-9"),
        call_context=call_context_of(
            state,
            context,
            completed_steps=("S-S7", "S-S8"),
            approval_evidence=state.get("approval_evidence"),
        ),
    )
    output = dict(result.output)
    payment_result = str(output.get("payment_result") or PAYMENT_RESULT_PENDING)
    record_step(
        context.recorder,
        "S-S9",
        base_record_fields(
            "S-S9",
            state,
            context,
            **{
                "도구명": "C-9",
                "멱등성 키 해시": None,
                "결과 열거값": payment_result,
                "pg_cancel_status": None,
                "error.type": result.error_class.value if result.error_class else None,
                "소요시간": None,
                "재시도 횟수": result.attempts,
                "예약 커밋 성공 여부": None,
                "입력 요약": {"amount_krw": k21.get("amount_krw")},
                "결과": payment_result,
                "동의 시각·버전": None,
                "호출자": "S-S9",
            },
        ),
    )
    update: dict[str, Any] = {
        "resume_cursor": {
            "boundary_step": "S-S9",
            "resume_unit": "member_plan_and_payment_idempotency",
            "idempotency_key": idempotency_key,
        },
        "partial_context": [{"step_id": "S-S9", "K-22": output}],
    }
    if not result.ok:
        return merged(
            update,
            connector_failure_update(
                "S-S9", result, to_landing=True, reason=LandingReason.PG_UNRESOLVED
            ),
        )
    return update


async def node_S_S10_store_payment(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """결제 ID·다음 결제일 적재. PG는 성공·기록은 실패면 사람 확인 대조 대상임."""
    verdict = check_deadline("S-S10", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-S10", base_record_fields("S-S10", state, context))
        return verdict.update
    k22 = _fragment_value(state, "K-22") or {}
    idempotency_key = str(state.get("payment_idempotency_key") or "")
    decision = evaluate_write_gate(
        "R-7",
        context,
        idempotency_key=idempotency_key,
        guards_met={
            "idempotency_key": bool(idempotency_key),
            "pg_success_received": str(k22.get("payment_result", "")) not in {"", PAYMENT_RESULT_PENDING},
        },
    )
    record_step(
        context.recorder,
        "S-S10",
        base_record_fields(
            "S-S10",
            state,
            context,
            **{
                "도구명": "R-7",
                "입력 요약": {"payment_result": k22.get("payment_result")},
                "결과": "허용" if decision.allowed else decision.reason,
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    if not decision.allowed:
        return merged(
            {"payment_result": {"payment_result": PAYMENT_RESULT_PENDING, "unresolved": True}},
            halt_to_landing("S-S10", LandingReason.PG_UNRESOLVED, {"reason": decision.reason}),
        )
    stored = r7.record_payment_result(
        payment_result=str(k22.get("payment_result", PAYMENT_RESULT_PENDING)),
        pg_response_at=int(k22.get("pg_response_at") or now_ms()),
        idempotency_key=idempotency_key,
        payment_id=k22.get("payment_id"),
        next_billing_date=k22.get("next_billing_date"),
    )
    update: dict[str, Any] = {"payment_result": stored}
    if stored["unresolved"]:
        update = merged(update, note_failure("S-S10", LandingReason.PG_UNRESOLVED, stored))
    return update


async def node_S_S11_audit_payment(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """결제 승인·호출 감사 기록. 규제 필수 기록이라 승인 문을 두지 않음(⑥ 3-2절 15번)."""
    verdict = check_deadline("S-S11", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-S11", base_record_fields("S-S11", state, context))
        return verdict.update
    k18 = _fragment_value(state, "K-18") or {}
    payload = r7.build_payment_audit(
        payment_request_id=str(k18.get("payment_request_id", "")),
        payment_result=str((state.get("payment_result") or {}).get("payment_result", "")),
        user_approval_id=str((state.get("approval_evidence") or {}).get("user_approval_id", "")),
    )
    record_step(
        context.recorder,
        "S-S11",
        base_record_fields(
            "S-S11",
            state,
            context,
            **{
                "도구명": "S-6",
                "입력 요약": {"payment_request_id": payload["payment_request_id"]},
                "결과": payload["payment_result"],
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    return {"partial_context": [{"step_id": "S-S11", "audit": payload}]}


async def node_S_S12_show_payment_result(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """결제 완료 표시 · 청약철회 안내 → `K-23`. 출력측 검사·가리기를 지남(⑥ `O-C11`)."""
    verdict = check_deadline("S-S12", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-S12", base_record_fields("S-S12", state, context))
        return verdict.update
    stored = dict(state.get("payment_result") or {})
    payload = r7.build_payment_response(
        payment_result=str(stored.get("payment_result", PAYMENT_RESULT_PENDING)),
        subscription_started_on=context.input_of("subscription_started_on"),
        next_billing_date=stored.get("next_billing_date"),
        withdrawal_notice=(state.get("disclosure_record") or {}).get("auto_renewal_notice"),
    )
    payload = dict(context.hooks.redactor.redact("S-S12", payload))
    record_step(context.recorder, "S-S12", base_record_fields("S-S12", state, context))
    return {"partial_context": [{"step_id": "S-S12", "K-23": payload}]}


async def node_S_S13_landing_payment_failed(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1-2절이 결제 구간에 고른 값 1개(`사람 확인`)대로 만듦.

    **여기서 상한을 다시 쓰지 않음** — 외부 호출 0건 · 모델 호출 0건 · 비용 0원임.
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    payload = r7.build_payment_landing(
        fallback_reason=reason,
        user_retry_count=int(context.input_of("user_retry_count", 0)),
    )
    record_step(context.recorder, "S-S13", base_record_fields("S-S13", state, context))
    return {
        "fallback_reason": reason,
        "payment_result": {"payment_result": payload["payment_result"], "unresolved": True},
        "partial_context": [{"step_id": "S-S13", "landing": payload}],
    }


def _fragment_value(state: LunchPickState, key: str) -> Any:
    for fragment in reversed(list(state.get("partial_context") or ())):
        if key in fragment:
            return fragment[key]
    return None


NODE_FUNCTIONS: dict[str, Any] = {
    "S-S1": node_S_S1_user_entry,
    "S-S2": node_S_S2_accept_plan_view,
    "S-S3": node_S_S3_check_subscription,
    "S-S4": node_S_S4_show_plans,
    "S-S5": node_S_S5_accept_payment_request,
    "S-S6": node_S_S6_build_disclosure,
    "S-S7": node_S_S7_human_approval,
    "S-S8": node_S_S8_verify_and_key,
    "S-S9": node_S_S9_register_pg,
    "S-S10": node_S_S10_store_payment,
    "S-S11": node_S_S11_audit_payment,
    "S-S12": node_S_S12_show_payment_result,
    "S-S13": node_S_S13_landing_payment_failed,
}
