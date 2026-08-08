"""예산·마감선 시험. 반드시 넣을 시험 4번·5번이 여기 있음."""

from __future__ import annotations

import pytest

from common.budget import (
    DeadlineTooTight,
    can_start_step,
    compute_deadline_at,
    ensure_step_can_start,
    remaining_ms,
    retry_allowed,
    step_worst_case_ms,
    worst_case_total_ms,
)
from common.config import Settings
from common.state import TriggerKind

RECEIVED_AT = 1_760_000_000_000


def test_worst_case_is_timeout_times_one_plus_retry(settings: Settings) -> None:
    """시험 4 — 최악값이 `시간 제한 × (1 + 재시도)`임."""
    assert step_worst_case_ms("S-R2", settings) == 50 * (1 + 0)
    assert step_worst_case_ms("S-R3", settings) == 200 * (1 + 1)
    assert step_worst_case_ms("S-R4", settings) == 500 * (1 + 1)


def test_worst_case_total_sums_every_step(settings: Settings) -> None:
    """시험 4 — 합계 함수가 단계별 최악값을 더한 값을 냄."""
    steps = ["S-R2", "S-R3", "S-R4"]
    assert worst_case_total_ms(steps, settings) == 50 + 400 + 1000


def test_deadline_is_receipt_plus_span_without_landing_path(settings: Settings) -> None:
    deadline = compute_deadline_at(TriggerKind.SYNC_RECOMMEND, RECEIVED_AT, settings)
    assert deadline == RECEIVED_AT + 2850
    assert remaining_ms(deadline, RECEIVED_AT) == 2850


def test_node_stops_before_running_when_time_is_short(settings: Settings) -> None:
    """시험 5 — 남은 시간이 모자라면 노드가 실행 전에 멈춤."""
    deadline = RECEIVED_AT + 100
    assert can_start_step("S-R4", deadline, settings, at_ms=RECEIVED_AT) is False
    with pytest.raises(DeadlineTooTight) as caught:
        ensure_step_can_start("S-R4", deadline, settings, at_ms=RECEIVED_AT)
    assert caught.value.step_id == "S-R4"
    assert caught.value.remaining == 100
    assert caught.value.required == 500


def test_node_starts_when_time_is_exactly_enough(settings: Settings) -> None:
    deadline = RECEIVED_AT + 500
    assert can_start_step("S-R4", deadline, settings, at_ms=RECEIVED_AT) is True
    ensure_step_can_start("S-R4", deadline, settings, at_ms=RECEIVED_AT)


def test_unconditional_retry_ignores_remaining_time(settings: Settings) -> None:
    deadline = RECEIVED_AT + 1
    assert retry_allowed("S-R3", 0, deadline, settings, at_ms=RECEIVED_AT) is True


def test_conditional_retry_needs_room_for_a_full_attempt(settings: Settings) -> None:
    tight = RECEIVED_AT + 1799
    roomy = RECEIVED_AT + 1800
    assert retry_allowed("S-R11", 0, tight, settings, at_ms=RECEIVED_AT) is False
    assert retry_allowed("S-R11", 0, roomy, settings, at_ms=RECEIVED_AT) is True


def test_retry_stops_once_the_count_is_used_up(settings: Settings) -> None:
    deadline = RECEIVED_AT + 100_000
    assert retry_allowed("S-R3", 1, deadline, settings, at_ms=RECEIVED_AT) is False
    assert retry_allowed("S-R2", 0, deadline, settings, at_ms=RECEIVED_AT) is False
