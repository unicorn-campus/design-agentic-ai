"""분기 함수 — 판정식은 ④ 「중단 조건」을 그대로 옮김. 새 조건을 더하지 않음.

분기를 **어느 노드 뒤에 붙일지**는 ④ 「중단 조건의 판정 주체·시점」에서 읽음.
`시점: {단계} 종료 직후`면 그 노드 뒤, `시점: {단계} 진입 직전`이면 앞 단계 뒤에 붙임.

반복 상한 값은 ③ 8-2절 소유이며 `01`의 설정에서 **읽기만** 함 — 이 파일에 숫자가 없음.
상한에 **닿기 전 마지막 여유**에서 착지로 감(넘긴 뒤에 가면 흐름이 이미 끊겨 착지가 안 돎).
"""

from __future__ import annotations

from typing import Callable

from common.config import Settings, SettingsMissing
from common.state import LunchPickState

from .signals import LandingReason, landing_reason_of
from .steps import LOOPS, LANDING_STEP_BY_TRIGGER, LoopSpec, trigger_of_step

__all__ = [
    "LANDING_ROUTE",
    "make_landing_branch",
    "make_loop_branch",
    "loop_verdict",
    "LoopVerdict",
]

LANDING_ROUTE = "landing"
"""분기 함수가 착지로 보낼 때 쓰는 이름. 실제 노드 이름은 ③ 8-1절이 정한 착지 단계임."""


def make_landing_branch(next_step: str) -> Callable[[LunchPickState], str]:
    """착지 신호가 있으면 착지로, 없으면 다음 단계로 보내는 분기 함수를 만듦."""

    def branch(state: LunchPickState) -> str:
        return LANDING_ROUTE if landing_reason_of(state) is not None else next_step

    branch.__name__ = f"branch_to_{next_step.replace('-', '_')}_or_landing"
    return branch


class LoopVerdict:
    """루프 1회의 판정. `reason`이 있으면 착지로 가는 사유임."""

    __slots__ = ("continue_loop", "reason")

    def __init__(self, continue_loop: bool, reason: LandingReason | None = None) -> None:
        self.continue_loop = continue_loop
        self.reason = reason


def loop_verdict(
    loop: LoopSpec, state: LunchPickState, settings: Settings
) -> LoopVerdict:
    """반복 상한을 설정에서 읽어 **닿기 전 마지막 여유**에서 갈라짐.

    상한 값이 설정에 없으면(③ 8-2절이 `[확인필요]`로 남긴 자리) **상한 없이 돌리지 않고**
    착지로 감 — 값을 지어내지 않는 대신 흐름이 끝나는 것을 보장함.
    """
    try:
        max_iter = settings.max_iter(loop.loop_id)
    except SettingsMissing:
        return LoopVerdict(False, LandingReason.LOOP_LIMIT_UNSET)
    iteration = int(state.get("iteration_count") or 0)
    if iteration + 1 >= max_iter:
        return LoopVerdict(False, LandingReason.LOOP_LIMIT_REACHED)
    return LoopVerdict(True)


def make_loop_branch(
    loop_id: str,
    settings: Settings,
    *,
    continue_step: str,
    exit_step: str,
    should_repeat: Callable[[LunchPickState], bool],
) -> Callable[[LunchPickState], str]:
    """되돌아가는 간선의 분기 함수를 만듦.

    순서 — ⓐ 착지 신호 ⓑ 더 돌 일이 남았나 ⓒ 반복 상한.
    """
    loop = LOOPS[loop_id]

    def branch(state: LunchPickState) -> str:
        if landing_reason_of(state) is not None:
            return LANDING_ROUTE
        if not should_repeat(state):
            return exit_step
        verdict = loop_verdict(loop, state, settings)
        return continue_step if verdict.continue_loop else LANDING_ROUTE

    branch.__name__ = f"branch_{loop_id.replace('-', '_')}_loop_or_exit"
    return branch


def landing_step_of(step_id: str) -> str:
    """그 단계가 속한 트리거의 착지 노드 이름."""
    return LANDING_STEP_BY_TRIGGER[trigger_of_step(step_id)]
