"""프로그램 준비 작업 시험."""

from __future__ import annotations

import asyncio
import sys

import pytest

from common.runtime import configure_event_loop_for_async_db, needs_selector_event_loop


def test_platform_check_matches_the_running_platform() -> None:
    assert needs_selector_event_loop() == (sys.platform == "win32")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows에서만 루프를 바꿈")
def test_windows_gets_a_loop_that_async_db_can_use() -> None:
    configure_event_loop_for_async_db()
    policy = asyncio.get_event_loop_policy()
    assert isinstance(policy, asyncio.WindowsSelectorEventLoopPolicy)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows에서만 루프를 바꿈")
def test_second_call_is_a_no_op() -> None:
    configure_event_loop_for_async_db()
    assert configure_event_loop_for_async_db() is False


@pytest.mark.skipif(sys.platform == "win32", reason="다른 플랫폼은 바꿀 것이 없음")
def test_other_platforms_change_nothing() -> None:
    assert configure_event_loop_for_async_db() is False
