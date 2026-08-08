"""예산과 마감선. 마감선 값을 넣는 곳은 진입 노드 하나이고 나머지 노드는 읽기만 함."""

from __future__ import annotations

import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .config import Settings
from .state import EpochMillis, LunchPickState, TriggerKind
from .units import MS_PER_SECOND

__all__ = [
    "DeadlineTooTight",
    "StepBudget",
    "now_ms",
    "compute_deadline_at",
    "worst_case_total_ms",
    "step_worst_case_ms",
    "remaining_ms",
    "can_start_step",
    "ensure_step_can_start",
    "retry_allowed",
    "read_deadline_at",
]


class DeadlineTooTight(RuntimeError):
    """남은 시간이 그 단계의 시간 제한보다 적음. 실행 전에 착지로 보내라는 뜻임."""

    def __init__(self, step_id: str, remaining: int, required: int) -> None:
        super().__init__(
            f"단계 {step_id}: 남은 시간 {remaining}ms < 필요한 시간 {required}ms"
        )
        self.step_id = step_id
        self.remaining = remaining
        self.required = required


@dataclass(frozen=True, slots=True)
class StepBudget:
    step_id: str
    timeout_ms: int
    retry_count: int

    @property
    def worst_case_ms(self) -> int:
        return self.timeout_ms * (1 + self.retry_count)


def now_ms() -> EpochMillis:
    return int(time.time() * MS_PER_SECOND)


def compute_deadline_at(
    trigger_kind: TriggerKind,
    received_at_ms: EpochMillis,
    settings: Settings,
) -> EpochMillis:
    """진입 노드만 부름. 착지 경로를 미리 뺀 진입선을 돌려줌."""
    return received_at_ms + settings.entry_deadline_span_ms(trigger_kind.value)


def step_worst_case_ms(step_id: str, settings: Settings) -> int:
    return StepBudget(
        step_id=step_id,
        timeout_ms=settings.timeout_ms(step_id),
        retry_count=settings.retry_count(step_id),
    ).worst_case_ms


def worst_case_total_ms(step_ids: Iterable[str], settings: Settings) -> int:
    """`시간 제한 × (1 + 재시도)`를 단계마다 내고 전부 더함."""
    return sum(step_worst_case_ms(step_id, settings) for step_id in step_ids)


def read_deadline_at(state: LunchPickState) -> EpochMillis:
    deadline = state.get("deadline_at")
    if deadline is None:
        raise DeadlineTooTight("<진입 노드 미실행>", 0, 0)
    return deadline


def remaining_ms(deadline_at: EpochMillis, at_ms: EpochMillis | None = None) -> int:
    return deadline_at - (now_ms() if at_ms is None else at_ms)


def can_start_step(
    step_id: str,
    deadline_at: EpochMillis,
    settings: Settings,
    at_ms: EpochMillis | None = None,
) -> bool:
    return remaining_ms(deadline_at, at_ms) >= settings.timeout_ms(step_id)


def ensure_step_can_start(
    step_id: str,
    deadline_at: EpochMillis,
    settings: Settings,
    at_ms: EpochMillis | None = None,
) -> None:
    """노드가 시작할 때 가장 먼저 부름. 모자라면 실행 전에 멈춤."""
    left = remaining_ms(deadline_at, at_ms)
    required = settings.timeout_ms(step_id)
    if left < required:
        raise DeadlineTooTight(step_id, left, required)


def retry_allowed(
    step_id: str,
    attempt_index: int,
    deadline_at: EpochMillis,
    settings: Settings,
    at_ms: EpochMillis | None = None,
) -> bool:
    """`attempt_index`는 0부터 셈. 조건부 재시도 단계는 진입선 규칙을 한 번 더 통과해야 함."""
    if attempt_index >= settings.retry_count(step_id):
        return False
    if not settings.is_retry_conditional(step_id):
        return True
    return can_start_step(step_id, deadline_at, settings, at_ms)


def entry_step_of(step_ids: Sequence[str]) -> str:
    return step_ids[0]
