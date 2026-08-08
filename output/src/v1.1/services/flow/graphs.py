"""흐름 조립 — 노드 8묶음(90개) · 간선 · 조건 분기 · 착지 · 반복 상한 · 흐름 전체 단계 상한.

**상태 타입은 `01`이 만든 `common.state.LunchPickState`를 그대로 씀** — 새로 만들지 않음.
프레임워크 API는 코드 작성 직전에 context7 MCP로 확인함(확인일 2026-08-08 · LangGraph 1.2.10) —
`StateGraph` · `add_node` · `add_edge` · `add_conditional_edges(source, path, path_map)` ·
`compile(checkpointer=...)` · `interrupt()` · `Command(resume=...)` · 설정의 `recursion_limit`.

`07-api-ui.md`가 부를 자리는 `run_flow()` · `resume_flow()` 2개뿐임. API는 여기서 만들지 않음.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from common.checkpointer import build_thread_id, invocation_config
from common.config import Settings, SettingsMissing
from common.state import LunchPickState, TriggerKind

from . import (
    nodes_batch,
    nodes_cancel,
    nodes_event,
    nodes_expiry,
    nodes_insight,
    nodes_propagate,
    nodes_recommend,
    nodes_subscribe,
)
from .branches import LANDING_ROUTE, make_landing_branch, make_loop_branch
from .context import FlowContext
from .signals import LandingReason, landing_reason_of
from .steps import (
    LANDING_STEP_BY_TRIGGER,
    LOOPS,
    STEPS_BY_TRIGGER,
    TERMINAL_STEPS,
)
from .resume import NO_RESUME_TRIGGERS

__all__ = [
    "NODE_FUNCTIONS",
    "FLOW_STEP_CAP_HEADROOM",
    "FlowRun",
    "build_graph",
    "flow_step_cap",
    "run_flow",
    "resume_flow",
]


NODE_FUNCTIONS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    **nodes_recommend.NODE_FUNCTIONS,
    **nodes_batch.NODE_FUNCTIONS,
    **nodes_event.NODE_FUNCTIONS,
    **nodes_subscribe.NODE_FUNCTIONS,
    **nodes_cancel.NODE_FUNCTIONS,
    **nodes_insight.NODE_FUNCTIONS,
    **nodes_expiry.NODE_FUNCTIONS,
    **nodes_propagate.NODE_FUNCTIONS,
}

FLOW_STEP_CAP_HEADROOM = 4
"""되묻기 1로 정한 **여유 걸음 수**임 — 착지 경로와 합류 재실행이 들어갈 자리.

값의 주인은 ③이 아님(③에 흐름 전체 단계 상한 칸이 없음). ③에 열을 추가할 것을 README에 적었음.
"""


def _bind(context: FlowContext, fn: Callable[..., Awaitable[dict[str, Any]]]):
    """노드 함수에 부품 묶음을 붙임. 함수 이름(=단계 식별자)을 그대로 유지함."""

    @functools.wraps(fn)
    async def bound(state: LunchPickState) -> dict[str, Any]:
        return await fn(state, context)

    return bound


def flow_step_cap(trigger_kind: TriggerKind, settings: Settings) -> int:
    """되묻기 1 — 흐름 전체 단계 상한. `노드 수 × 루프별 반복 상한의 곱 + 여유`임.

    루프 상한이 설정에 없으면(③ `[확인필요]`) 곱을 1로 두고 **노드 수 + 여유**만 씀 —
    값을 지어내지 않는 대신 마지막 방어선을 반드시 둠. 이 상한은 노드 수 계산과 별개임.
    """
    node_count = len(STEPS_BY_TRIGGER[trigger_kind])
    factor = 1
    for loop in LOOPS.values():
        if loop.trigger_kind is not trigger_kind:
            continue
        try:
            factor *= max(1, settings.max_iter(loop.loop_id))
        except SettingsMissing:
            factor *= 1
    return node_count * factor + FLOW_STEP_CAP_HEADROOM


# ---------------------------------------------------------------------------
# 트리거별 그래프 조립 — 간선은 ③ 4절 「단계」 순서와 5절 「단계 간 데이터 형식」대로 놓음.
# ---------------------------------------------------------------------------
def _add_nodes(builder: StateGraph, context: FlowContext, steps: tuple[str, ...]) -> None:
    for step_id in steps:
        builder.add_node(step_id, _bind(context, NODE_FUNCTIONS[step_id]))


def _chain(builder: StateGraph, steps: tuple[str, ...], landing: str) -> None:
    """줄줄이 이어지는 구간에 `착지 또는 다음 단계` 분기를 붙임."""
    for current, nxt in zip(steps, steps[1:], strict=False):
        builder.add_conditional_edges(
            current,
            make_landing_branch(nxt),
            {nxt: nxt, LANDING_ROUTE: landing},
        )


def _build_recommend(context: FlowContext) -> StateGraph:
    """③ 4-1절 — 병렬 4단계 · L-1 루프 · 착지 `S-R16`."""
    steps = STEPS_BY_TRIGGER[TriggerKind.SYNC_RECOMMEND]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.SYNC_RECOMMEND]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_edge(START, "S-R1")
    builder.add_conditional_edges(
        "S-R1", make_landing_branch("S-R2"), {"S-R2": "S-R2", LANDING_ROUTE: landing}
    )
    builder.add_conditional_edges(
        "S-R2", make_landing_branch("S-R3"), {"S-R3": "S-R3", LANDING_ROUTE: landing}
    )
    # 병렬 갈래 — 네 노드가 같은 상태 필드를 쓰지 않음(전부 `partial_context` 누적임).
    parallel = ("S-R4", "S-R5", "S-R6", "S-R7")
    builder.add_conditional_edges(
        "S-R3",
        _fanout_or_landing(parallel),
        {**{step: step for step in parallel}, LANDING_ROUTE: landing},
    )
    for parallel_step in ("S-R4", "S-R5", "S-R6", "S-R7"):
        builder.add_edge(parallel_step, "S-R8")  # 합류 — 즉시 진행 + 빠진 값 표기
    _chain(builder, ("S-R8", "S-R9", "S-R10", "S-R11", "S-R12", "S-R13"), landing)

    # L-1 되돌아가는 간선 — 카운터는 `S-R2`가 올림.
    builder.add_conditional_edges(
        "S-R13",
        make_loop_branch(
            "L-1",
            context.settings,
            continue_step="S-R2",
            exit_step="S-R14",
            should_repeat=_alternative_requested,
        ),
        {"S-R2": "S-R2", "S-R14": "S-R14", LANDING_ROUTE: landing},
    )
    builder.add_edge("S-R14", "S-R15")
    builder.add_edge("S-R15", END)
    builder.add_edge(landing, END)
    return builder


def _build_batch(context: FlowContext) -> StateGraph:
    """③ 4-2절 — L-2 루프(`S-B4` ~ `S-B7`) · 착지 `S-B10`."""
    steps = STEPS_BY_TRIGGER[TriggerKind.BATCH_PREFERENCE_LEARNING]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.BATCH_PREFERENCE_LEARNING]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_edge(START, "S-B1")
    _chain(builder, ("S-B1", "S-B2", "S-B3", "S-B4", "S-B5", "S-B6", "S-B7"), landing)
    builder.add_conditional_edges(
        "S-B7",
        make_loop_branch(
            "L-2",
            context.settings,
            continue_step="S-B4",
            exit_step="S-B8",
            should_repeat=_batch_has_next_member,
        ),
        {"S-B4": "S-B4", "S-B8": "S-B8", LANDING_ROUTE: landing},
    )
    _chain(builder, ("S-B8", "S-B9"), landing)
    builder.add_edge("S-B9", END)
    builder.add_edge(landing, END)
    return builder


def _build_event(context: FlowContext) -> StateGraph:
    """③ 4-3절 — 구획 2개(진입 노드 `S-E1` · `S-E5`) · 착지 `S-E8`."""
    steps = STEPS_BY_TRIGGER[TriggerKind.EVENT_PIPELINE]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.EVENT_PIPELINE]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_conditional_edges(
        START,
        _section_router(context, {"구획1": "S-E1", "구획2": "S-E5"}, default="S-E1"),
        {"S-E1": "S-E1", "S-E5": "S-E5"},
    )
    _chain(builder, ("S-E1", "S-E2", "S-E3", "S-E4"), landing)
    builder.add_edge("S-E4", END)
    _chain(builder, ("S-E5", "S-E6", "S-E7"), landing)
    builder.add_edge("S-E7", END)
    builder.add_edge(landing, END)
    return builder


def _build_subscribe(context: FlowContext) -> StateGraph:
    """③ 4-5절 — 구획 2개(플랜 조회 · 결제) · 사람 확인 `S-S7` · 착지 `S-S13`."""
    steps = STEPS_BY_TRIGGER[TriggerKind.SYNC_SUBSCRIBE]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.SYNC_SUBSCRIBE]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_conditional_edges(
        START,
        _section_router(context, {"플랜조회": "S-S1", "결제": "S-S5"}, default="S-S1"),
        {"S-S1": "S-S1", "S-S5": "S-S5"},
    )
    _chain(builder, ("S-S1", "S-S2", "S-S3", "S-S4"), landing)
    builder.add_edge("S-S4", END)
    _chain(
        builder,
        ("S-S5", "S-S6", "S-S7", "S-S8", "S-S9", "S-S10", "S-S11", "S-S12"),
        landing,
    )
    builder.add_edge("S-S12", END)
    builder.add_edge(landing, END)
    return builder


def _build_cancel(context: FlowContext) -> StateGraph:
    """③ 4-6절 — 사람 확인 `S-C5` · 응답 후 후처리 `S-C10` · 착지 `S-C11`."""
    steps = STEPS_BY_TRIGGER[TriggerKind.SYNC_CANCEL]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.SYNC_CANCEL]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_edge(START, "S-C1")
    _chain(
        builder,
        ("S-C1", "S-C2", "S-C3", "S-C4", "S-C5", "S-C6", "S-C7", "S-C8", "S-C9"),
        landing,
    )
    # `S-C10`은 응답을 닫은 뒤 도는 후처리라 착지 분기를 앞에 두지 않음(실패해도 예약 유지).
    builder.add_edge("S-C9", "S-C10")
    builder.add_edge("S-C10", END)
    builder.add_edge(landing, END)
    return builder


def _build_insight(context: FlowContext) -> StateGraph:
    """③ 4-9절 — 구획 2개(타임라인 · 인사이트) · 착지 `S-I14`. 쓰기 0건이라 재개 안 함."""
    steps = STEPS_BY_TRIGGER[TriggerKind.SYNC_INSIGHT]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.SYNC_INSIGHT]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_conditional_edges(
        START,
        _section_router(context, {"타임라인": "S-I1", "인사이트": "S-I6"}, default="S-I1"),
        {"S-I1": "S-I1", "S-I6": "S-I6"},
    )
    _chain(builder, ("S-I1", "S-I2", "S-I3", "S-I4", "S-I5"), landing)
    builder.add_edge("S-I5", END)
    _chain(
        builder,
        ("S-I6", "S-I7", "S-I8", "S-I9", "S-I10", "S-I11", "S-I12", "S-I13"),
        landing,
    )
    builder.add_edge("S-I13", END)
    builder.add_edge(landing, END)
    return builder


def _build_expiry(context: FlowContext) -> StateGraph:
    """③ 4-8절 — L-3 루프(`S-X3` ~ `S-X7`) · 착지 `S-X8`."""
    steps = STEPS_BY_TRIGGER[TriggerKind.BATCH_CANCEL_EXPIRY]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.BATCH_CANCEL_EXPIRY]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_edge(START, "S-X1")
    _chain(builder, ("S-X1", "S-X2", "S-X3", "S-X4", "S-X5", "S-X6", "S-X7"), landing)
    builder.add_conditional_edges(
        "S-X7",
        make_loop_branch(
            "L-3",
            context.settings,
            continue_step="S-X3",
            exit_step=END,
            should_repeat=_expiry_has_next_target,
        ),
        {"S-X3": "S-X3", END: END, LANDING_ROUTE: landing},
    )
    builder.add_edge(landing, END)
    return builder


def _build_propagate(context: FlowContext) -> StateGraph:
    """③ 4-7절 — 구획 2개(진입 노드 `S-N1` · `S-N5`) · 착지 `S-N10`."""
    steps = STEPS_BY_TRIGGER[TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION]
    landing = LANDING_STEP_BY_TRIGGER[TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION]
    builder: StateGraph = StateGraph(LunchPickState)
    _add_nodes(builder, context, steps)

    builder.add_conditional_edges(
        START,
        _section_router(context, {"구획1": "S-N1", "구획2": "S-N5"}, default="S-N1"),
        {"S-N1": "S-N1", "S-N5": "S-N5"},
    )
    _chain(builder, ("S-N1", "S-N2", "S-N3", "S-N4"), landing)
    builder.add_edge("S-N4", END)
    _chain(builder, ("S-N5", "S-N6", "S-N7", "S-N8", "S-N9"), landing)
    builder.add_edge("S-N9", END)
    builder.add_edge(landing, END)
    return builder


_BUILDERS: Mapping[TriggerKind, Callable[[FlowContext], StateGraph]] = {
    TriggerKind.SYNC_RECOMMEND: _build_recommend,
    TriggerKind.BATCH_PREFERENCE_LEARNING: _build_batch,
    TriggerKind.EVENT_PIPELINE: _build_event,
    TriggerKind.SYNC_SUBSCRIBE: _build_subscribe,
    TriggerKind.SYNC_CANCEL: _build_cancel,
    TriggerKind.SYNC_INSIGHT: _build_insight,
    TriggerKind.BATCH_CANCEL_EXPIRY: _build_expiry,
    TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION: _build_propagate,
}


def build_graph(trigger_kind: TriggerKind, context: FlowContext, checkpointer=None):
    """트리거 1종의 그래프를 조립해 돌릴 수 있는 모양으로 돌려줌.

    중간 저장 장치는 `01`이 만든 것을 **받아 씀** — 여기서 만들지 않음.
    """
    builder = _BUILDERS[trigger_kind](context)
    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# 진입 함수 — `07-api-ui.md`가 부를 자리 2개
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FlowRun:
    """흐름 1회의 결과. API가 이 모양만 보고 응답을 만들 수 있게 함."""

    trigger_kind: TriggerKind
    thread_id: str
    state: Mapping[str, Any]
    interrupted: bool
    interrupt_payload: Mapping[str, Any] | None
    landed: bool
    landing_reason: str | None
    step_cap: int

    @property
    def awaiting_human(self) -> bool:
        """확인 대기 상태임 — 응답을 닫고 사람 응답을 기다림(되묻기 3의 형태)."""
        return self.interrupted


async def run_flow(
    trigger_kind: TriggerKind,
    context: FlowContext,
    *,
    member_id: str,
    requested_at,
    checkpointer=None,
    initial_state: Mapping[str, Any] | None = None,
    workflow_name: str | None = None,
) -> FlowRun:
    """흐름을 처음부터 돌림. **인자와 반환 형만 정하고 API는 만들지 않음.**"""
    graph = build_graph(trigger_kind, context, checkpointer=checkpointer)
    thread_id = build_thread_id(
        member_id or "anonymous",
        workflow_name or trigger_kind.name.lower(),
        requested_at,
    )
    return await _invoke(
        graph, trigger_kind, context, thread_id, dict(initial_state or {})
    )


async def resume_flow(
    trigger_kind: TriggerKind,
    context: FlowContext,
    *,
    thread_id: str,
    resume_value: Mapping[str, Any],
    checkpointer,
) -> FlowRun:
    """멈춘 자리에서 다시 들어옴. **중간 저장 장치가 있어야만 됨**(없으면 프레임워크가 막음).

    다시 들어오는 자리는 멈춘 자리와 **같은 단계 식별자**임(`S-S7` · `S-C5`).
    그 단계는 처음부터 다시 실행되므로 앞 단계의 저장소·외부 쓰기가 두 번 일어나지 않도록
    ③ 11절 「재개 경계」의 중복 방지 키를 그 단계마다 걸어 두었음.
    """
    if trigger_kind in NO_RESUME_TRIGGERS:
        raise ValueError(NO_RESUME_TRIGGERS[trigger_kind])
    if checkpointer is None:
        raise ValueError("재개에는 중간 저장 장치가 필요함")
    graph = build_graph(trigger_kind, context, checkpointer=checkpointer)
    return await _invoke(
        graph, trigger_kind, context, thread_id, Command(resume=dict(resume_value))
    )


async def _invoke(graph, trigger_kind, context, thread_id, payload) -> FlowRun:
    cap = flow_step_cap(trigger_kind, context.settings)
    config = invocation_config(thread_id, recursion_limit=cap)
    try:
        result = await graph.ainvoke(payload, config)
    except GraphRecursionError:
        # 흐름 전체 단계 상한에 닿음 — 마지막 방어선임. 사유를 남기고 착지 결과로 돌려줌.
        return FlowRun(
            trigger_kind=trigger_kind,
            thread_id=thread_id,
            state={"fallback_reason": LandingReason.FLOW_STEP_CAP_REACHED.value},
            interrupted=False,
            interrupt_payload=None,
            landed=True,
            landing_reason=LandingReason.FLOW_STEP_CAP_REACHED.value,
            step_cap=cap,
        )

    interrupts = result.get("__interrupt__") or ()
    payload_of_interrupt = (
        dict(interrupts[0].value) if interrupts and isinstance(interrupts[0].value, Mapping) else None
    )
    reason = result.get("fallback_reason") or landing_reason_of(result)
    return FlowRun(
        trigger_kind=trigger_kind,
        thread_id=thread_id,
        state=result,
        interrupted=bool(interrupts),
        interrupt_payload=payload_of_interrupt,
        landed=bool(result.get("fallback_reason")),
        landing_reason=reason,
        step_cap=cap,
    )


# ---------------------------------------------------------------------------
# 분기 판정식 조각 — ④ 「중단 조건」에 없는 새 조건을 더하지 않음
# ---------------------------------------------------------------------------
def _fanout_or_landing(targets: tuple[str, ...]) -> Callable[[LunchPickState], Any]:
    """병렬 갈래 — 착지 신호가 없으면 네 노드 이름을 **한꺼번에** 돌려줌(같은 걸음에 함께 돎)."""

    def branch(state: LunchPickState) -> str | list[str]:
        return LANDING_ROUTE if landing_reason_of(state) is not None else list(targets)

    branch.__name__ = "branch_S_R3_fanout_or_landing"
    return branch


def _section_router(
    context: FlowContext, mapping: Mapping[str, str], *, default: str
) -> Callable[[LunchPickState], str]:
    """③ 도식의 「구획」을 고르는 분기 함수. 진입 값의 `section`으로 갈림."""

    def branch(state: LunchPickState) -> str:
        return mapping.get(str(context.input_of("section", "")), default)

    branch.__name__ = "branch_section_entry"
    return branch


def _alternative_requested(state: LunchPickState) -> bool:
    """L-1 — 거절 후 대체 추천을 더 만들 일이 남았나(④ `R-2` 「중단 조건」 밖의 새 조건 아님)."""
    verification = dict(state.get("verification_result") or {})
    return bool(verification.get("alternative_requested"))


def _batch_has_next_member(state: LunchPickState) -> bool:
    """L-2 — 갱신 대상 회원이 더 남았나."""
    members = list((state.get("precheck_result") or {}).get("eligible_member_ids", ()))
    return int(state.get("iteration_count") or 0) < len(members)


def _expiry_has_next_target(state: LunchPickState) -> bool:
    """L-3 — 전환 대상 건이 더 남았나."""
    precheck = dict(state.get("precheck_result") or {})
    return int(state.get("iteration_count") or 0) < int(precheck.get("target_count") or 0)


def terminal_steps() -> frozenset[str]:
    """계약 대상 밖 5단계. `04-connector`·`07-api-ui`가 참고함."""
    return TERMINAL_STEPS
