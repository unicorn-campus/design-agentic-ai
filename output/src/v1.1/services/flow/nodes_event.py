"""③ 4-3절 이벤트 `S-E` — 노드 8개. 구획 2개(③ 11절 재개 경계와 같은 구획임).

담당자 — 구획 1(`S-E1` ~ `S-E4`)과 착지(`S-E8`)는 `R-5`, 구획 2(`S-E5` ~ `S-E7`)는 `R-6`임.
"""

from __future__ import annotations

from typing import Any

from common.budget import compute_deadline_at
from common.checkpointer import build_idempotency_key
from common.state import LunchPickState, TriggerKind

from ..member_service.agents import r6_onboarding_profile as r6
from ..recommendation_history_service.agents import r5_learning_transfer as r5
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


async def node_S_E1_receive_feedback_signal(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구획 1 진입 노드 — 마감선(가시성 타임아웃)을 넣음."""
    trigger = TriggerKind.EVENT_PIPELINE
    deadline_at = state.get("deadline_at") or compute_deadline_at(
        trigger, now_ms(), context.settings
    )
    payload = r5.receive_feedback_signal(
        meal_record_id=str(context.input_of("meal_record_id", "")),
        member_id=str(context.input_of("member_id", "")),
        feedback_submitted_at=int(context.input_of("feedback_submitted_at", now_ms())),
    )
    record_step(
        context.recorder,
        "S-E1",
        base_record_fields("S-E1", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-E1", **payload}],
    }


async def node_S_E2_check_undo_window(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 조건 — 30초 실행취소 창 경과 확인. 창 안이면 전달 보류(⑥ `B-8`)."""
    verdict = check_deadline("S-E2", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-E2", base_record_fields("S-E2", state, context))
        return verdict.update
    result = r5.check_undo_window(
        undo_window_elapsed=bool(context.input_of("undo_window_elapsed", False))
    )
    record_step(context.recorder, "S-E2", base_record_fields("S-E2", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if not result["precheck_passed"]:
        update = merged(update, halt_to_landing("S-E2", LandingReason.PRECHECK_FAILED, result))
    return update


async def node_S_E3_transfer_learning_data(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """③ 11절 구획 1의 **재개 경계 단계**임. 중복 방지 키 = `기록 + 회원` 조합 키."""
    verdict = check_deadline("S-E3", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-E3", base_record_fields("S-E3", state, context))
        return verdict.update

    frame = _fragment_of(state, "S-E1")
    idempotency_key = build_idempotency_key(
        "record_and_member",
        str(frame.get("meal_record_id") or "unknown"),
        str(frame.get("member_id") or "unknown"),
    )
    decision = evaluate_write_gate(
        "R-5",
        context,
        idempotency_key=idempotency_key,
        guards_met={"idempotency_key": True, "undo_window_elapsed": True},
    )
    record_step(
        context.recorder,
        "S-E3",
        base_record_fields(
            "S-E3",
            state,
            context,
            **{
                "도구명": "R-5",
                "입력 요약": {"meal_record_id": frame.get("meal_record_id")},
                "결과": "허용" if decision.allowed else decision.reason,
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    if not decision.allowed:
        return halt_to_landing("S-E3", LandingReason.TOOL_DENIED, {"reason": decision.reason})
    if not await context.idempotency.claim(idempotency_key):
        return note_failure("S-E3", LandingReason.IDEMPOTENCY_REPLAYED)

    payload = r5.build_transfer(
        transfer_id=str(context.input_of("transfer_id", context.request_id)),
        member_id=str(frame.get("member_id", "")),
        meal_record_id=str(frame.get("meal_record_id", "")),
        satisfaction=str(context.input_of("satisfaction", "")),
        context_snapshot=context.source_of("context_snapshot", {"source": "S-E3"}),
        idempotency_key=idempotency_key,
        feedback_keyword=context.input_of("feedback_keyword"),
    )
    return {
        "resume_cursor": {
            "boundary_step": "S-E3",
            "resume_unit": "record_and_member",
            "idempotency_key": idempotency_key,
        },
        "partial_context": [{"step_id": "S-E3", "K-15": payload}],
    }


async def node_S_E4_acknowledge(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """수신 확인 회신 · 감사 로그 적재(`V-10` 29번 · 규제 필수 기록)."""
    verdict = check_deadline("S-E4", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-E4", base_record_fields("S-E4", state, context))
        return verdict.update
    k15 = _fragment_value(state, "K-15") or {}
    payload = r5.build_receipt(
        transfer_id=str(k15.get("transfer_id", "")),
        idempotency_key=str(k15.get("idempotency_key", "")),
    )
    record_step(
        context.recorder,
        "S-E4",
        base_record_fields(
            "S-E4",
            state,
            context,
            **{
                "도구명": "S-6",
                "입력 요약": {"transfer_id": payload["transfer_id"]},
                "결과": "회신",
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    return {"partial_context": [{"step_id": "S-E4", **payload}]}


async def node_S_E5_check_swipe_count(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """구획 2 진입 노드 겸 사전 조건 확인 — 최소 7장 스와이프 완료 확인.

    **안전 종료** — 미달이면 온보딩 계속 안내(③ 4-3절).
    """
    trigger = TriggerKind.EVENT_PIPELINE
    deadline_at = state.get("deadline_at") or compute_deadline_at(
        trigger, now_ms(), context.settings
    )
    result = r6.check_swipe_count(
        swipe_count=int(context.input_of("swipe_count", 0)),
        health_consent=bool(context.input_of("health_consent", False)),
        diet_value_present=bool(context.input_of("diet_value_present", False)),
    )
    record_step(
        context.recorder,
        "S-E5",
        base_record_fields("S-E5", state, context, deadline_at=int(deadline_at)),
    )
    update: dict[str, Any] = {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "precheck_result": result,
    }
    if not result["precheck_passed"]:
        update = merged(update, halt_to_landing("S-E5", LandingReason.PRECHECK_FAILED, result))
    return update


async def node_S_E6_create_initial_profile(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """③ 11절 구획 2의 **재개 경계 단계**임. 중복 방지 키 = `회원 + 온보딩 회차` 조합 키."""
    verdict = check_deadline("S-E6", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-E6", base_record_fields("S-E6", state, context))
        return verdict.update

    member_id = str(context.input_of("member_id", ""))
    onboarding_round = int(context.input_of("onboarding_round", 1))
    idempotency_key = build_idempotency_key(
        "member_and_onboarding_round", member_id or "unknown", str(onboarding_round)
    )
    decision = evaluate_write_gate(
        "R-6",
        context,
        idempotency_key=idempotency_key,
        guards_met={"idempotency_key": True, "min_card_count": True},
    )
    record_step(
        context.recorder,
        "S-E6",
        base_record_fields(
            "S-E6",
            state,
            context,
            **{
                "도구명": "R-6",
                "입력 요약": {"member_id": member_id},
                "결과": "허용" if decision.allowed else decision.reason,
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    if not decision.allowed:
        return halt_to_landing("S-E6", LandingReason.TOOL_DENIED, {"reason": decision.reason})
    if not await context.idempotency.claim(idempotency_key):
        return note_failure("S-E6", LandingReason.IDEMPOTENCY_REPLAYED)

    payload = r6.build_initial_profile(
        member_id=member_id,
        onboarding_round=onboarding_round,
        swipe_results=context.input_of("swipe_results", ()),
        swipe_count=int(context.input_of("swipe_count", 0)),
        health_consent=bool(context.input_of("health_consent", False)),
        idempotency_key=idempotency_key,
    )
    return {
        "resume_cursor": {
            "boundary_step": "S-E6",
            "resume_unit": "member_and_onboarding_round",
            "idempotency_key": idempotency_key,
        },
        "partial_context": [{"step_id": "S-E6", "K-16": payload}],
    }


async def node_S_E7_reply_onboarding(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """온보딩 완료 응답 · 취향 요약 카드 전달. 출력측 검사·가리기를 지남."""
    verdict = check_deadline("S-E7", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-E7", base_record_fields("S-E7", state, context))
        return verdict.update
    k16 = _fragment_value(state, "K-16") or {}
    payload = r6.build_onboarding_reply(
        member_id=str(k16.get("member_id", "")),
        onboarding_round=int(k16.get("onboarding_round", 0)),
        initial_preference_vector=k16.get("initial_preference_vector", ()),
        top_categories=k16.get("top_categories", ()),
        swipe_count=int(k16.get("swipe_count", 0)),
        idempotency_key=str(k16.get("idempotency_key", "")),
    )
    payload = dict(context.hooks.redactor.redact("S-E7", payload))
    record_step(context.recorder, "S-E7", base_record_fields("S-E7", state, context))
    return {
        "preference_vector_ref": str(k16.get("idempotency_key", "")),
        "partial_context": [{"step_id": "S-E7", "K-16": payload}],
    }


async def node_S_E8_landing_undelivered_queue(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1절이 이벤트에 고른 값 1개(`사람 확인`)대로 만듦.

    **여기서 상한을 다시 쓰지 않음** — 모델 호출 0건 · 재시도 0건 · 쓰기 1건임.
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    k15 = _fragment_value(state, "K-15") or {}
    payload = r5.build_undelivered_entry(
        transfer_id=str(k15.get("transfer_id", "")), fallback_reason=reason
    )
    record_step(
        context.recorder,
        "S-E8",
        base_record_fields(
            "S-E8",
            state,
            context,
            **{
                "fallback_reason": reason,
                "캐시 나이(초)": None,
                "착지 사유": reason,
                "도구명": "S-6",
                "입력 요약": {"transfer_id": payload["transfer_id"]},
                "결과": "미전달 큐 적재",
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    return {
        "fallback_reason": reason,
        "partial_context": [{"step_id": "S-E8", "landing": payload}],
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
    "S-E1": node_S_E1_receive_feedback_signal,
    "S-E2": node_S_E2_check_undo_window,
    "S-E3": node_S_E3_transfer_learning_data,
    "S-E4": node_S_E4_acknowledge,
    "S-E5": node_S_E5_check_swipe_count,
    "S-E6": node_S_E6_create_initial_profile,
    "S-E7": node_S_E7_reply_onboarding,
    "S-E8": node_S_E8_landing_undelivered_queue,
}
