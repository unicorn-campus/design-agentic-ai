from time import monotonic

import pytest

from help_desk_runtime.budget import (
    DeadlineExceeded,
    RuntimeDeadline,
    StageBudget,
    calculate_worst_case_ms,
)


def test_worst_case_uses_serial_sum_and_parallel_maximum() -> None:
    serial = [StageBudget(timeout_ms=100, retry_count=1)]
    parallel = [[StageBudget(200, 0), StageBudget(100, 2)]]
    assert calculate_worst_case_ms(serial, parallel) == 500


def test_deadline_stops_before_stage_start() -> None:
    deadline = RuntimeDeadline(deadline_monotonic_ms=int(monotonic() * 1000))
    with pytest.raises(DeadlineExceeded):
        deadline.ensure_stage_can_start(stage_timeout_ms=1)
