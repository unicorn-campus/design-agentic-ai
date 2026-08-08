"""필수 시험 1 — 반복 상한을 넘기면 **착지 노드로 감.** 두 노드 사이를 무한히 왕복하지 않음.

세 루프(`L-1` · `L-2` · `L-3`) 전부를 봄. 상한 값은 설정에서만 옴 — 시험이 값을 코드에 박지 않음.
"""

from __future__ import annotations

import pytest

from common.state import LunchPickState, TriggerKind

from services.flow import graphs
from services.flow.branches import LANDING_ROUTE, loop_verdict, make_loop_branch
from services.flow.signals import LandingReason
from services.flow.steps import LANDING_STEP_BY_TRIGGER, LOOPS


@pytest.mark.parametrize("loop_id", sorted(LOOPS))
def test_loop_lands_on_the_last_slack_before_the_cap(loop_id, settings_with_loops) -> None:
    """상한에 **닿기 전 마지막 여유**에서 갈라짐. 넘긴 뒤에 가면 착지가 실행되지 않음."""
    loop = LOOPS[loop_id]
    max_iter = settings_with_loops.max_iter(loop_id)

    below: LunchPickState = {"iteration_count": max_iter - 2}
    at_slack: LunchPickState = {"iteration_count": max_iter - 1}

    assert loop_verdict(loop, below, settings_with_loops).continue_loop is True
    verdict = loop_verdict(loop, at_slack, settings_with_loops)
    assert verdict.continue_loop is False
    assert verdict.reason is LandingReason.LOOP_LIMIT_REACHED


@pytest.mark.parametrize("loop_id", sorted(LOOPS))
def test_loop_branch_routes_to_landing_when_cap_is_reached(loop_id, settings_with_loops) -> None:
    loop = LOOPS[loop_id]
    branch = make_loop_branch(
        loop_id,
        settings_with_loops,
        continue_step=loop.counter_entry_step,
        exit_step="__exit__",
        should_repeat=lambda _state: True,
    )
    max_iter = settings_with_loops.max_iter(loop_id)
    assert branch({"iteration_count": max_iter - 2}) == loop.counter_entry_step
    assert branch({"iteration_count": max_iter - 1}) == LANDING_ROUTE


@pytest.mark.parametrize("loop_id", sorted(LOOPS))
def test_loop_lands_when_the_cap_value_is_missing(loop_id, settings) -> None:
    """③이 `[확인필요]`로 남긴 상한 — **상한 없이 돌리지 않고** 착지로 감."""
    verdict = loop_verdict(LOOPS[loop_id], {"iteration_count": 0}, settings)
    assert verdict.continue_loop is False
    assert verdict.reason is LandingReason.LOOP_LIMIT_UNSET


def test_every_loop_has_a_counter_and_a_landing_node() -> None:
    for loop in LOOPS.values():
        assert loop.counter_entry_step in loop.span
        assert loop.exit_step in loop.span
        assert LANDING_STEP_BY_TRIGGER[loop.trigger_kind] not in loop.span


@pytest.mark.parametrize(
    "trigger_kind",
    [
        TriggerKind.SYNC_RECOMMEND,
        TriggerKind.BATCH_PREFERENCE_LEARNING,
        TriggerKind.BATCH_CANCEL_EXPIRY,
    ],
)
def test_flow_step_cap_is_a_last_line_of_defence(trigger_kind, settings_with_loops) -> None:
    """흐름 전체 단계 상한이 노드 수보다 커야 하고, 루프 상한의 곱을 반영해야 함."""
    cap = graphs.flow_step_cap(trigger_kind, settings_with_loops)
    node_count = len(graphs.STEPS_BY_TRIGGER[trigger_kind])
    assert cap > node_count
    assert cap == node_count * _loop_factor(trigger_kind, settings_with_loops) + (
        graphs.FLOW_STEP_CAP_HEADROOM
    )


async def test_recommend_loop_reaches_the_landing_node_and_stops(
    make_context, settings_with_loops, sink
) -> None:
    """실제로 돌려 착지 노드가 실행되는 것을 봄 — 무한 왕복이 아님."""
    context = make_context(
        settings=settings_with_loops,
        inputs={"member_id": "m1", "origin_lat": 37.5, "origin_lng": 127.0},
    )
    graph = graphs.build_graph(TriggerKind.SYNC_RECOMMEND, context)
    # 착지 신호를 만드는 가장 짧은 경로 — 사전 조건 미통과(동의 없음).
    result = await graph.ainvoke(
        {}, {"recursion_limit": graphs.flow_step_cap(TriggerKind.SYNC_RECOMMEND, settings_with_loops)}
    )
    assert result["fallback_reason"] == LandingReason.PRECHECK_FAILED.value
    landed_steps = [record.step_id for record in sink.records]
    assert LANDING_STEP_BY_TRIGGER[TriggerKind.SYNC_RECOMMEND] in landed_steps


def _loop_factor(trigger_kind, settings) -> int:
    factor = 1
    for loop in LOOPS.values():
        if loop.trigger_kind is trigger_kind:
            factor *= max(1, settings.max_iter(loop.loop_id))
    return factor
