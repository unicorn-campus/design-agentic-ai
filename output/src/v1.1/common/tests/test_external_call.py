"""바깥 호출 감싸개 시험. 실제로 부르는 것은 하나도 없고 시계도 대역으로 바꿈."""

from __future__ import annotations

import asyncio

import pytest

from common.budget import DeadlineTooTight
from common.config import Settings
from common.external_call import StepExhausted, call_with_limits

RECEIVED_AT = 1_760_000_000_000


async def _noop_sleep(_seconds: float) -> None:
    return None


def _frozen_clock(at_ms: int = RECEIVED_AT):
    def clock() -> int:
        return at_ms

    return clock


def _advancing_clock(step_ms: int, base_ms: int = RECEIVED_AT):
    """읽을 때마다 정해진 만큼 앞으로 감. 조건부 재시도가 시간에 따라 갈리는 것을 보임."""
    reads = {"n": 0}

    def clock() -> int:
        at = base_ms + step_ms * reads["n"]
        reads["n"] += 1
        return at

    return clock


async def test_successful_call_records_no_retry(settings: Settings) -> None:
    async def call() -> str:
        return "ok"

    outcome = await call_with_limits(
        "S-R3",
        call,
        settings,
        RECEIVED_AT + 100_000,
        sleep=_noop_sleep,
        now_fn=_frozen_clock(),
    )
    assert outcome.value == "ok"
    assert outcome.attempts == 1
    assert outcome.retry_count_by_step == {}
    assert outcome.error_history == []


async def test_failure_retries_up_to_the_configured_count(settings: Settings) -> None:
    calls = {"n": 0}

    async def call() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("첫 시도 실패")
        return "ok"

    outcome = await call_with_limits(
        "S-R3",
        call,
        settings,
        RECEIVED_AT + 100_000,
        sleep=_noop_sleep,
        now_fn=_frozen_clock(),
    )
    assert outcome.value == "ok"
    assert outcome.attempts == 2
    assert outcome.retry_count_by_step == {"S-R3": 1}
    assert len(outcome.error_history) == 1
    assert outcome.error_history[0]["step_id"] == "S-R3"


async def test_zero_retry_step_gives_up_immediately(settings: Settings) -> None:
    async def call() -> str:
        raise RuntimeError("실패")

    with pytest.raises(StepExhausted) as caught:
        await call_with_limits(
            "S-R2",
            call,
            settings,
            RECEIVED_AT + 100_000,
            sleep=_noop_sleep,
            now_fn=_frozen_clock(),
        )
    assert caught.value.attempts == 1
    assert caught.value.step_id == "S-R2"


async def test_call_is_not_started_when_deadline_is_already_tight(
    settings: Settings,
) -> None:
    started = {"yes": False}

    async def call() -> str:
        started["yes"] = True
        return "ok"

    with pytest.raises(DeadlineTooTight):
        await call_with_limits(
            "S-R4",
            call,
            settings,
            RECEIVED_AT + 1,
            sleep=_noop_sleep,
            now_fn=_frozen_clock(),
        )
    assert started["yes"] is False


async def test_conditional_retry_fires_only_when_a_full_attempt_still_fits(
    settings: Settings,
) -> None:
    """마감선까지 시간 제한만큼 남았을 때만 조건부 재시도가 발화함."""
    calls = {"n": 0}

    async def call() -> str:
        calls["n"] += 1
        raise RuntimeError("즉시 실패")

    with pytest.raises(StepExhausted) as roomy:
        await call_with_limits(
            "S-R11",
            call,
            settings,
            RECEIVED_AT + 2100,
            sleep=_noop_sleep,
            now_fn=_advancing_clock(step_ms=100),
        )
    assert calls["n"] == 2
    assert roomy.value.attempts == 2

    calls["n"] = 0
    with pytest.raises(StepExhausted) as tight:
        await call_with_limits(
            "S-R11",
            call,
            settings,
            RECEIVED_AT + 1900,
            sleep=_noop_sleep,
            now_fn=_advancing_clock(step_ms=200),
        )
    assert calls["n"] == 1
    assert tight.value.attempts == 1


async def test_timeout_is_read_from_settings_not_hardcoded(settings: Settings) -> None:
    async def slow() -> str:
        await asyncio.sleep(settings.timeout_ms("S-R2") * 5)
        return "늦음"

    with pytest.raises(StepExhausted) as caught:
        await call_with_limits(
            "S-R2",
            slow,
            settings,
            RECEIVED_AT + 100_000,
            sleep=_noop_sleep,
            now_fn=_frozen_clock(),
        )
    assert isinstance(caught.value.last_error, TimeoutError)
