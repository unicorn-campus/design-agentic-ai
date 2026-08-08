"""③ 4-2절 스케줄 배치 `S-B` — 노드 10개. 담당자 — `S-B7`은 `R-4`, 나머지 9개는 `R-3`임.

루프 `L-2`(`S-B4` ~ `S-B7`)의 카운터 필드는 ③ 6절 11번 `iteration_count`이며 갱신 주체는 `S-B4`임.
"""

from __future__ import annotations

from typing import Any

from common.budget import compute_deadline_at
from common.checkpointer import build_idempotency_key
from common.state import LunchPickState, TriggerKind

from ..daily_learning_batch.agents import (
    r3_batch_learning as r3,
    r4_vector_commit as r4,
)
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
from .gates import evaluate_write_gate

__all__ = ["NODE_FUNCTIONS"]


async def node_S_B1_acquire_lock(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """진입 노드 — 마감선(실행 창)을 넣음. 잠금 실패는 중복 실행이므로 즉시 종료함."""
    trigger = TriggerKind.BATCH_PREFERENCE_LEARNING
    deadline_at = state.get("deadline_at") or compute_deadline_at(
        trigger, now_ms(), context.settings
    )
    result = r3.acquire_run_lock(
        batch_run_id=str(context.input_of("batch_run_id", context.request_id)),
        lock_acquired=bool(context.input_of("lock_acquired", True)),
    )
    record_step(
        context.recorder,
        "S-B1",
        base_record_fields(
            "S-B1",
            state,
            context,
            deadline_at=int(deadline_at),
            **{
                "도구명": "S-6",
                "입력 요약": {"batch_run_id": result["batch_run_id"]},
                "결과": "잠금 획득" if result["lock_acquired"] else "잠금 실패",
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    update: dict[str, Any] = {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "iteration_count": 0,
    }
    if not result["lock_acquired"]:
        update = merged(update, halt_to_landing("S-B1", LandingReason.RUN_LOCK_FAILED))
    return update


async def node_S_B2_collect_feedback(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """전일 피드백 데이터 조회 → `K-11`. 실패하면 사람 확인(착지)로 감."""
    verdict = check_deadline("S-B2", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-B2", base_record_fields("S-B2", state, context))
        return verdict.update
    rows = context.source_of("feedback_rows")
    if rows is None:
        record_step(context.recorder, "S-B2", base_record_fields("S-B2", state, context))
        return halt_to_landing("S-B2", LandingReason.STEP_EXHAUSTED)
    payload = r3.collect_feedback(
        batch_run_id=str(context.input_of("batch_run_id", context.request_id)),
        target_date=str(context.input_of("target_date", "")),
        feedback_rows=rows,
        target_member_ids=context.source_of("target_member_ids", ()),
    )
    record_step(context.recorder, "S-B2", base_record_fields("S-B2", state, context))
    return {"partial_context": [{"step_id": "S-B2", "K-11": payload}]}


async def node_S_B3_check_consent(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 조건 확인 — 동의 상태·보존 기간 만료 대상 제외(`V-10` 24번 · ⑥ `B-9`)."""
    verdict = check_deadline("S-B3", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-B3", base_record_fields("S-B3", state, context))
        return verdict.update
    payload = _fragment_value(state, "K-11") or {}
    result = r3.check_consent_and_retention(
        target_member_ids=payload.get("target_member_ids", ()),
        consent_by_member=context.source_of("consent_by_member", {}),
    )
    record_step(context.recorder, "S-B3", base_record_fields("S-B3", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if not result["precheck_passed"]:
        update = merged(update, halt_to_landing("S-B3", LandingReason.PRECHECK_FAILED, result))
    elif result["undecidable_member_ids"]:
        update = merged(update, note_failure("S-B3", LandingReason.PRECHECK_FAILED, result))
    return update


async def node_S_B4_recompute_vector(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """루프 진입 노드 — `iteration_count`를 올리는 **단 하나의 자리**(③ 6절 11번)."""
    verdict = check_deadline("S-B4", state, context)
    iteration = int(state.get("iteration_count") or 0)
    if verdict.blocked:
        record_step(context.recorder, "S-B4", base_record_fields("S-B4", state, context))
        return verdict.update
    members = list((state.get("precheck_result") or {}).get("eligible_member_ids", ()))
    if iteration >= len(members):
        return {"iteration_count": iteration}
    member_id = members[iteration]
    payload = r3.recompute_preference_vector(
        member_id=member_id,
        feedback_rows=context.source_of("feedback_rows", ()),
        current_preference_vector=context.source_of("current_preference_vector", ()),
    )
    record_step(context.recorder, "S-B4", base_record_fields("S-B4", state, context))
    return {
        "iteration_count": iteration + 1,
        "partial_context": [{"step_id": "S-B4", "loop_index": iteration, **payload}],
    }


async def node_S_B5_refresh_embedding(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`C-3` 취향 임베딩 갱신 호출(루프 내) → `K-12`. 재시도는 커넥터 계층 1곳뿐임."""
    verdict = check_deadline("S-B5", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-B5", base_record_fields("S-B5", state, context))
        return verdict.update
    frame = _fragment_of(state, "S-B4") or {}
    result = await r3.refresh_embedding(
        correlation_key=str(frame.get("member_id", "")),
        recent_feedback=frame.get("recent_feedback", ()),
        meal_history_summary=context.source_of("meal_history_summary", ()),
        current_preference_vector=frame.get("current_preference_vector", ()),
        tool=context.tool("C-3"),
        call_context=call_context_of(state, context, completed_steps=("S-B3",)),
    )
    record_step(
        context.recorder,
        "S-B5",
        base_record_fields(
            "S-B5",
            state,
            context,
            **{
                "프롬프트 버전": None,
                "gen_ai.usage.input_tokens": None,
                "gen_ai.usage.output_tokens": None,
                "건당 환산 금액": None,
                "일일 누적 콜 수": None,
                "일일 콜 수": None,
                "일일 환산 금액": None,
                "임계 도달 여부": False,
            },
        ),
    )
    if not result.ok:
        return connector_failure_update("S-B5", result, to_landing=True)
    return {"partial_context": [{"step_id": "S-B5", "K-12": dict(result.output)}]}


async def node_S_B6_judge_quality(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """추천 품질 자가 검증 · 임계 판정(루프 내). 임계 미달이면 커밋을 금지함(⑥ `B-7`)."""
    verdict = check_deadline("S-B6", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-B6", base_record_fields("S-B6", state, context))
        return verdict.update
    k12 = _fragment_value(state, "K-12") or {}
    frame = _fragment_of(state, "S-B4") or {}
    result = r3.judge_quality(
        accept_rate=float(context.source_of("accept_rate", 0.0)),
        satisfaction_rate=float(context.source_of("satisfaction_rate", 0.0)),
        quality_threshold=context.source_of("quality_threshold"),
        candidate_vector=k12.get("candidate_vector", ()),
        current_preference_vector=frame.get("current_preference_vector", ()),
    )
    record_step(context.recorder, "S-B6", base_record_fields("S-B6", state, context))
    return {"partial_context": [{"step_id": "S-B6", "K-13": result}]}


async def node_S_B7_commit_vector(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`R-4` 취향 벡터 커밋 — **되돌림 불가 쓰기**이며 ③ 11절 재개 경계 단계임.

    ③에 커밋 앞 사람 승인 노드가 없어(③ 12절 2번 판정) ⑥ `R-4`의 **제한 장치 5개**를
    승인 문으로 씀. 중복 방지 키가 이미 처리된 건이면 바깥을 다시 바꾸지 않음.
    """
    verdict = check_deadline("S-B7", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-B7", base_record_fields("S-B7", state, context))
        return verdict.update

    k12 = _fragment_value(state, "K-12") or {}
    k13 = _fragment_value(state, "K-13") or {}
    frame = _fragment_of(state, "S-B4") or {}
    member_id = str(frame.get("member_id", ""))
    idempotency_key = build_idempotency_key(
        "member_and_target_date", member_id or "unknown", str(context.input_of("target_date", "0"))
    )
    decision = evaluate_write_gate(
        "R-4",
        context,
        idempotency_key=idempotency_key,
        guards_met={
            "quality_threshold_passed": bool(k13.get("quality_passed")),
            "idempotency_key": True,
            "run_lock": bool(context.input_of("lock_acquired", True)),
            "commit_count_cap": True,
            "operator_post_notice": True,
        },
    )
    record_step(
        context.recorder,
        "S-B7",
        base_record_fields(
            "S-B7",
            state,
            context,
            **{
                "도구명": "R-4",
                "입력 요약": {"member_id": member_id},
                "결과": "허용" if decision.allowed else decision.reason,
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    if not decision.allowed:
        return halt_to_landing(
            "S-B7", LandingReason.TOOL_DENIED, {"reason": decision.reason}
        )
    if not await context.idempotency.claim(idempotency_key):
        return note_failure("S-B7", LandingReason.IDEMPOTENCY_REPLAYED, {"member_id": member_id})

    committed = r4.commit_preference_vector(
        member_id=member_id,
        candidate_vector=k12.get("candidate_vector", ()),
        vector_model_version=str(k12.get("vector_model_version", "")),
        quality_passed=bool(k13.get("quality_passed")),
        target_date=str(context.input_of("target_date", "")),
        idempotency_key=idempotency_key,
        committed_at=now_ms(),
    )
    return {
        "resume_cursor": {
            "boundary_step": "S-B7",
            "resume_unit": "member_and_target_date",
            "idempotency_key": idempotency_key,
            **committed,
        }
    }


async def node_S_B8_build_message(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """학습 반영 메시지 생성. 실제 변경 이력과 어긋나면 ⑥ `B-6`이 비노출로 막음."""
    verdict = check_deadline("S-B8", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-B8", base_record_fields("S-B8", state, context))
        return verdict.update
    cursor = dict(state.get("resume_cursor") or {})
    message = r3.build_learning_message(
        updated_member_count=1 if cursor.get("commit_result") == "커밋" else 0,
        mean_vector_delta=float(_fragment_of(state, "S-B4", {}).get("vector_shift", 0.0)),
    )
    message = dict(context.hooks.redactor.redact("S-B8", dict(message)))
    record_step(context.recorder, "S-B8", base_record_fields("S-B8", state, context))
    return {"partial_context": [{"step_id": "S-B8", **message}]}


async def node_S_B9_record_result(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """배치 실행 결과 기록 · 완료 이벤트 회신 → `K-14`."""
    verdict = check_deadline("S-B9", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-B9", base_record_fields("S-B9", state, context))
        return verdict.update
    cursor = dict(state.get("resume_cursor") or {})
    precheck = dict(state.get("precheck_result") or {})
    result = r3.build_batch_result(
        batch_run_id=str(context.input_of("batch_run_id", context.request_id)),
        updated_member_count=1 if cursor.get("commit_result") == "커밋" else 0,
        mean_vector_delta=float(_fragment_of(state, "S-B4", {}).get("vector_shift", 0.0)),
        batch_status="완료",
        skipped_member_ids=precheck.get("undecidable_member_ids", ()),
        learning_applied_message=_fragment_of(state, "S-B8", {}).get(
            "learning_applied_message"
        ),
    )
    record_step(
        context.recorder,
        "S-B9",
        base_record_fields(
            "S-B9",
            state,
            context,
            **{
                "갱신 사용자 수": result["updated_member_count"],
                "평균 변화량": result["mean_vector_delta"],
                "임계 미달 사용자 수": len(result["skipped_member_ids"]),
                "배치 상태": result["batch_status"],
                "만족 비율": context.source_of("satisfaction_rate"),
                "도구명": "S-6",
                "입력 요약": {"batch_run_id": result["batch_run_id"]},
                "결과": result["batch_status"],
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
                "호출자": "S-B9",
            },
        ),
    )
    return {"partial_context": [{"step_id": "S-B9", "K-14": result}]}


async def node_S_B10_landing_keep_previous(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1절이 스케줄 배치에 고른 값 1개(`사람 확인`)대로 만듦.

    **여기서 상한을 다시 쓰지 않음** — 쓰기 0건 · 모델 호출 0건 · 재시도 0건임.
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    precheck = dict(state.get("precheck_result") or {})
    payload = r3.build_batch_landing(
        batch_run_id=str(context.input_of("batch_run_id", context.request_id)),
        fallback_reason=reason,
        skipped_member_ids=precheck.get("undecidable_member_ids", ()),
    )
    record_step(
        context.recorder,
        "S-B10",
        base_record_fields(
            "S-B10",
            state,
            context,
            **{
                "fallback_reason": reason,
                "캐시 나이(초)": None,
                "착지 사유": reason,
                "도구명": "S-6",
                "입력 요약": {"skipped": len(payload["skipped_member_ids"])},
                "결과": "사람 확인 알림",
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    return {
        "fallback_reason": reason,
        "partial_context": [{"step_id": "S-B10", "landing": payload}],
    }


def _fragment_of(
    state: LunchPickState, step_id: str, default: dict[str, Any] | None = None
) -> dict[str, Any]:
    for fragment in reversed(list(state.get("partial_context") or ())):
        if fragment.get("step_id") == step_id:
            return dict(fragment)
    return dict(default or {})


def _fragment_value(state: LunchPickState, key: str) -> Any:
    for fragment in reversed(list(state.get("partial_context") or ())):
        if key in fragment:
            return fragment[key]
    return None


NODE_FUNCTIONS: dict[str, Any] = {
    "S-B1": node_S_B1_acquire_lock,
    "S-B2": node_S_B2_collect_feedback,
    "S-B3": node_S_B3_check_consent,
    "S-B4": node_S_B4_recompute_vector,
    "S-B5": node_S_B5_refresh_embedding,
    "S-B6": node_S_B6_judge_quality,
    "S-B7": node_S_B7_commit_vector,
    "S-B8": node_S_B8_build_message,
    "S-B9": node_S_B9_record_result,
    "S-B10": node_S_B10_landing_keep_previous,
}
