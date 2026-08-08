"""③ 4-9절 동기 요청 `S-I`(취향 인사이트 조회) — 노드 14개. 구획 2개(타임라인 · 인사이트).

담당자 — `S-I1`은 계약 대상 밖, 나머지 13개는 `R-14`임. **쓰기 0건**이라 ③ 11절이 재개를
`재개 안 함`으로 판정함(부작용 0건).
"""

from __future__ import annotations

from typing import Any

from common.budget import compute_deadline_at
from common.state import LunchPickState, TriggerKind

from ..recommendation_history_service.agents import r14_history_insight as r14
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

__all__ = ["NODE_FUNCTIONS"]


async def node_S_I1_user_entry(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """단말 구간이라 API 예산 밖임(계약 대상 밖)."""
    record_step(context.recorder, "S-I1", base_record_fields("S-I1", state, context))
    return {}


async def node_S_I2_accept_timeline_request(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """타임라인 구획 진입 노드 — 이 구획의 마감선을 넣음."""
    trigger = TriggerKind.SYNC_INSIGHT
    deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    payload = r14.accept_timeline_request(
        history_request_id=str(context.input_of("history_request_id", context.request_id)),
        member_id=str(context.input_of("member_id", "")),
        requested_at=int(context.input_of("requested_at", now_ms())),
        deadline_at=int(deadline_at),
        trigger_kind=trigger.value,
    )
    record_step(
        context.recorder,
        "S-I2",
        base_record_fields("S-I2", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-I2", **payload}],
    }


async def node_S_I3_decide_allowed_period(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 조건 — 구독 상태로 조회 기간 판정 → `K-32`.

    **안전 종료** — 구독 상태를 못 읽으면 좁은 쪽(무료 30일)으로 판정하지 않고 중단(⑥ `B-29`).
    """
    verdict = check_deadline("S-I3", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I3", base_record_fields("S-I3", state, context))
        return verdict.update
    result = r14.decide_allowed_period(
        member_id=str(context.input_of("member_id", "")),
        subscription_state=context.source_of("subscription_state"),
        today=str(context.input_of("today", "")),
        free_period_from=str(context.input_of("free_period_from", "")),
    )
    record_step(context.recorder, "S-I3", base_record_fields("S-I3", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if result["subscription_state"]:
        update["subscription_state"] = result["subscription_state"]
    if not result["precheck_passed"]:
        update = merged(update, halt_to_landing("S-I3", LandingReason.PRECHECK_FAILED, result))
    return update


async def node_S_I4_collect_timeline(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """기간 내 기록 조회. 실패하면 부분 결과로 계속 — 최근 구간만 표시 + 낮춘 사유."""
    verdict = check_deadline("S-I4", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I4", base_record_fields("S-I4", state, context))
        return verdict.update
    rows = context.source_of("meal_history_rows")
    payload = r14.collect_timeline(meal_history_rows=rows)
    record_step(context.recorder, "S-I4", base_record_fields("S-I4", state, context))
    return merged(
        {"partial_context": [{"step_id": "S-I4", **payload}]},
        {} if rows is not None else note_failure("S-I4", LandingReason.STEP_EXHAUSTED),
    )


async def node_S_I5_send_timeline(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """달력 뷰 타임라인 응답. 기록 0건이면 첫 기록 안내를 냄."""
    verdict = check_deadline("S-I5", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I5", base_record_fields("S-I5", state, context))
        return verdict.update
    payload = r14.build_timeline_response(
        timeline=(_fragment_value(state, "timeline") or ())
    )
    payload = dict(context.hooks.redactor.redact("S-I5", payload))
    record_step(context.recorder, "S-I5", base_record_fields("S-I5", state, context))
    return {"partial_context": [{"step_id": "S-I5", "timeline_response": payload}]}


async def node_S_I6_accept_insight_request(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """인사이트 구획 진입 노드 — 이 구획의 마감선을 새로 넣음."""
    trigger = TriggerKind.SYNC_INSIGHT
    deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    payload = r14.accept_insight_request(
        insight_request_id=str(context.input_of("insight_request_id", context.request_id)),
        member_id=str(context.input_of("member_id", "")),
        requested_at=int(context.input_of("requested_at", now_ms())),
        deadline_at=int(deadline_at),
    )
    record_step(
        context.recorder,
        "S-I6",
        base_record_fields("S-I6", state, context, deadline_at=int(deadline_at)),
    )
    return {
        "trigger_kind": trigger,
        "deadline_at": int(deadline_at),
        "partial_context": [{"step_id": "S-I6", **payload}],
    }


async def node_S_I7_check_min_records(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """사전 조건 — 최소 기록 10건 판정. **안전 종료** — 미달이면 안내만 함(③ 4-9절)."""
    verdict = check_deadline("S-I7", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I7", base_record_fields("S-I7", state, context))
        return verdict.update
    count = int(
        _fragment_value(state, "source_record_count")
        or context.source_of("source_record_count", 0)
    )
    result = r14.check_min_record_count(source_record_count=count)
    record_step(context.recorder, "S-I7", base_record_fields("S-I7", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if not result["precheck_passed"]:
        update = merged(
            update, halt_to_landing("S-I7", LandingReason.RECORD_COUNT_BELOW_MIN, result)
        )
    return update


async def node_S_I8_collect_statistics(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """통계 데이터 조회 → `K-33`. 실패하면 부분 결과로 계속 — 조회된 지표만 집계."""
    verdict = check_deadline("S-I8", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I8", base_record_fields("S-I8", state, context))
        return verdict.update
    payload = r14.collect_statistics(
        category_distribution=context.source_of("category_distribution", ()),
        satisfaction_trend=context.source_of("satisfaction_trend", ()),
        visit_frequency=context.source_of("visit_frequency", ()),
        source_record_count=int(
            (state.get("precheck_result") or {}).get("source_record_count", 0)
        ),
    )
    record_step(context.recorder, "S-I8", base_record_fields("S-I8", state, context))
    return {"partial_context": [{"step_id": "S-I8", "K-33": payload}]}


async def node_S_I9_aggregate_insight(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """인사이트 집계 → `K-34`. 요약 문장은 집계 템플릿으로 만듦(모델 호출 0건)."""
    verdict = check_deadline("S-I9", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I9", base_record_fields("S-I9", state, context))
        return verdict.update
    k33 = _fragment_value(state, "K-33") or {}
    payload = r14.aggregate_insight(
        category_distribution=k33.get("category_distribution", ()),
        satisfaction_trend=k33.get("satisfaction_trend", ()),
        weekly_pattern=context.source_of("weekly_pattern", ()),
        accuracy_gain_formula_available=bool(
            context.source_of("accuracy_gain_formula_available", False)
        ),
    )
    record_step(context.recorder, "S-I9", base_record_fields("S-I9", state, context))
    return {"insight_aggregate": payload}


async def node_S_I10_check_consistency(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """**통계 일치 검사** → `K-35`(`V-10` 11번 · ⑥ `B-24` · `O-C5`).

    집계(`S-I9`)와 검사(`S-I10`)를 갈라 둔 이유는 집계가 스스로를 검사하지 못하게 하려는 것임.
    불일치 항목은 **비노출**이며 자동 노출을 하지 않음.
    """
    verdict = check_deadline("S-I10", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I10", base_record_fields("S-I10", state, context))
        return verdict.update
    aggregate = dict(state.get("insight_aggregate") or {})
    k33 = _fragment_value(state, "K-33") or {}
    result = r14.check_consistency(
        insight_top_categories=aggregate.get("insight_top_categories", ()),
        satisfaction_change=float(aggregate.get("satisfaction_change") or 0.0),
        weekly_pattern_summary=aggregate.get("weekly_pattern_summary"),
        accuracy_gain_rate=aggregate.get("accuracy_gain_rate"),
        category_distribution=k33.get("category_distribution", ()),
        satisfaction_trend=k33.get("satisfaction_trend", ()),
    )
    record_step(
        context.recorder,
        "S-I10",
        base_record_fields(
            "S-I10",
            state,
            context,
            **{
                "대조한 항목 수": len(result["displayable_items"]) + len(result["hidden_item_codes"]),
                "불일치 항목 수와 이름": result["hidden_item_codes"],
                "비노출 처리 건수": len(result["hidden_item_codes"]),
                "향상률 칸을 비운 사유": "[확인필요: 추천 정확도 향상률 산출식·원천]"
                if aggregate.get("accuracy_gain_rate") is None
                else None,
                "fallback_reason": result["mismatch_reason"],
            },
        ),
    )
    update: dict[str, Any] = {"consistency_check": result}
    if not result["consistency_passed"]:
        update = merged(
            update, note_failure("S-I10", LandingReason.CONSISTENCY_MISMATCH, result)
        )
    return update


async def node_S_I11_send_insight(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """인사이트 대시보드 표시 — **일치 항목만** 나감."""
    verdict = check_deadline("S-I11", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I11", base_record_fields("S-I11", state, context))
        return verdict.update
    payload = r14.build_insight_response(
        timeline=(_fragment_value(state, "timeline") or ()),
        insight_aggregate=state.get("insight_aggregate") or {},
        displayable_items=(state.get("consistency_check") or {}).get("displayable_items", ()),
    )
    payload = dict(context.hooks.redactor.redact("S-I11", payload))
    record_step(context.recorder, "S-I11", base_record_fields("S-I11", state, context))
    return {"partial_context": [{"step_id": "S-I11", "insight_response": payload}]}


async def node_S_I12_decide_milestone(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """마일스톤 표시 판정 — 누적 30건 이상 시 축하 + 향상률(없으면 문구만)."""
    verdict = check_deadline("S-I12", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I12", base_record_fields("S-I12", state, context))
        return verdict.update
    payload = r14.decide_milestone(
        source_record_count=int(
            (state.get("precheck_result") or {}).get("source_record_count", 0)
        ),
        accuracy_gain_rate=(state.get("insight_aggregate") or {}).get("accuracy_gain_rate"),
    )
    payload = dict(context.hooks.redactor.redact("S-I12", payload))
    record_step(context.recorder, "S-I12", base_record_fields("S-I12", state, context))
    return {"partial_context": [{"step_id": "S-I12", **payload}]}


async def node_S_I13_decide_memory_limit_notice(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """기억 제한 안내 표시 — 여기서 안내하면 `S-N1`(구독 전파 이벤트)이 걸림(③ 4-9절)."""
    verdict = check_deadline("S-I13", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-I13", base_record_fields("S-I13", state, context))
        return verdict.update
    payload = r14.decide_memory_limit_notice(
        subscription_state=state.get("subscription_state"),
        expiring_record_count=int(context.source_of("expiring_record_count", 0)),
    )
    record_step(context.recorder, "S-I13", base_record_fields("S-I13", state, context))
    return {"partial_context": [{"step_id": "S-I13", **payload}]}


async def node_S_I14_landing_timeline_only(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1-2절이 `S-I`에 고른 값 1개(`부분 결과로 계속`)대로 만듦.

    **여기서 상한을 다시 쓰지 않음** — 재조회 0건 · 모델 호출 0건 · 비용 0원임
    (타임라인은 `S-I5`에서 이미 응답됐음).
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    payload = r14.build_timeline_only_response(
        timeline=(_fragment_value(state, "timeline") or ()), fallback_reason=reason
    )
    record_step(context.recorder, "S-I14", base_record_fields("S-I14", state, context))
    return {
        "fallback_reason": reason,
        "partial_context": [{"step_id": "S-I14", "landing": payload}],
    }


def _fragment_value(state: LunchPickState, key: str) -> Any:
    for fragment in reversed(list(state.get("partial_context") or ())):
        if key in fragment:
            return fragment[key]
    return None


NODE_FUNCTIONS: dict[str, Any] = {
    "S-I1": node_S_I1_user_entry,
    "S-I2": node_S_I2_accept_timeline_request,
    "S-I3": node_S_I3_decide_allowed_period,
    "S-I4": node_S_I4_collect_timeline,
    "S-I5": node_S_I5_send_timeline,
    "S-I6": node_S_I6_accept_insight_request,
    "S-I7": node_S_I7_check_min_records,
    "S-I8": node_S_I8_collect_statistics,
    "S-I9": node_S_I9_aggregate_insight,
    "S-I10": node_S_I10_check_consistency,
    "S-I11": node_S_I11_send_insight,
    "S-I12": node_S_I12_decide_milestone,
    "S-I13": node_S_I13_decide_memory_limit_notice,
    "S-I14": node_S_I14_landing_timeline_only,
}
