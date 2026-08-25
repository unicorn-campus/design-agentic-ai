from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Iterable


class DeadlineExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class StageBudget:
    timeout_ms: int
    retry_count: int

    @property
    def worst_case_ms(self) -> int:
        return self.timeout_ms * (self.retry_count + 1)


def calculate_worst_case_ms(
    serial: Iterable[StageBudget],
    parallel_groups: Iterable[Iterable[StageBudget]] = (),
) -> int:
    serial_total = sum(item.worst_case_ms for item in serial)
    parallel_total = sum(
        max((item.worst_case_ms for item in group), default=0)
        for group in parallel_groups
    )
    return serial_total + parallel_total


@dataclass(frozen=True)
class RuntimeDeadline:
    deadline_monotonic_ms: int

    @classmethod
    def from_budget_ms(cls, budget_ms: int) -> "RuntimeDeadline":
        return cls(int(monotonic() * 1000) + budget_ms)

    def remaining_ms(self) -> int:
        return self.deadline_monotonic_ms - int(monotonic() * 1000)

    def ensure_stage_can_start(self, stage_timeout_ms: int) -> None:
        if self.remaining_ms() < stage_timeout_ms:
            raise DeadlineExceeded("단계 시간 제한보다 남은 시간이 짧음")


@dataclass
class ModelCallCounter:
    count: int = 0
