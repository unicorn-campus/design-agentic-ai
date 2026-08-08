"""바깥 호출을 감싸는 껍데기. 실제 연결은 `04-connector.md` 몫이고 여기는 상한만 씌움."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from .budget import DeadlineTooTight, ensure_step_can_start, now_ms, retry_allowed
from .config import Settings
from .state import EpochMillis, ErrorRecord, RetryCountByStep
from .units import ms_to_seconds

__all__ = ["CallOutcome", "StepExhausted", "call_with_limits"]

T = TypeVar("T")


class StepExhausted(RuntimeError):
    """시간 제한과 재시도를 다 쓰고도 못 끝냄. 착지 노드로 보내라는 뜻임."""

    def __init__(self, step_id: str, attempts: int, last_error: BaseException) -> None:
        super().__init__(f"단계 {step_id}: {attempts}번 시도 후 실패 — {last_error!r}")
        self.step_id = step_id
        self.attempts = attempts
        self.last_error = last_error


@dataclass(slots=True)
class CallOutcome:
    """상태에 그대로 얹을 수 있는 모양으로 결과를 담음."""

    step_id: str
    attempts: int
    value: Any | None = None
    retry_count_by_step: RetryCountByStep = field(default_factory=dict)
    error_history: list[ErrorRecord] = field(default_factory=list)


async def call_with_limits(
    step_id: str,
    call: Callable[[], Awaitable[T]],
    settings: Settings,
    deadline_at: EpochMillis,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    now_fn: Callable[[], EpochMillis] = now_ms,
) -> CallOutcome:
    """시간 제한·재시도·백오프를 씌워 부름. 값을 코드에 박지 않고 설정에서 읽음."""
    ensure_step_can_start(step_id, deadline_at, settings, at_ms=now_fn())

    timeout_s = ms_to_seconds(settings.timeout_ms(step_id))
    backoff_s = ms_to_seconds(settings.backoff_ms(step_id))
    outcome = CallOutcome(step_id=step_id, attempts=0)

    while True:
        outcome.attempts += 1
        try:
            outcome.value = await asyncio.wait_for(call(), timeout=timeout_s)
            return outcome
        except Exception as exc:
            outcome.error_history.append(
                {
                    "step_id": step_id,
                    "attempt": outcome.attempts,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            attempt_index = outcome.attempts - 1
            if not retry_allowed(
                step_id, attempt_index, deadline_at, settings, at_ms=now_fn()
            ):
                raise StepExhausted(step_id, outcome.attempts, exc) from exc
            outcome.retry_count_by_step[step_id] = outcome.attempts
            if backoff_s:
                await sleep(backoff_s)
            try:
                ensure_step_can_start(step_id, deadline_at, settings, at_ms=now_fn())
            except DeadlineTooTight as tight:
                raise StepExhausted(step_id, outcome.attempts, tight) from tight
