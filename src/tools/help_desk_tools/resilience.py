from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from help_desk_guardrails import CircuitBreaker, InvocationLimiter

from .errors import ConnectorError, ErrorCategory


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    retry_count: int
    delays_ms: tuple[int, ...]
    jitter_ratio: float


@dataclass
class ConnectorGuards:
    limiter: InvocationLimiter | None = None
    circuit_breaker: CircuitBreaker | None = None

    def before_call(self) -> None:
        if self.circuit_breaker is not None:
            self.circuit_breaker.before_call()
        if self.limiter is not None:
            self.limiter.acquire()

    def after_call(self, succeeded: bool) -> None:
        if self.limiter is not None:
            self.limiter.release()
        if self.circuit_breaker is not None:
            if succeeded:
                self.circuit_breaker.record_success()
            else:
                self.circuit_breaker.record_failure()


async def execute_with_resilience(
    operation: Callable[[], Awaitable[T]],
    *,
    timeout_ms: int,
    retry: RetryPolicy,
    guards: ConnectorGuards,
    irreversible: bool = False,
) -> T:
    for attempt in range(retry.retry_count + 1):
        guards.before_call()
        succeeded = False
        try:
            task = asyncio.create_task(operation())
            if irreversible:
                try:
                    result = await asyncio.wait_for(
                        asyncio.shield(task),
                        timeout=timeout_ms / 1000,
                    )
                except TimeoutError:
                    result = await task
            else:
                result = await asyncio.wait_for(task, timeout=timeout_ms / 1000)
            succeeded = True
            return result
        except ConnectorError as exc:
            if exc.category is not ErrorCategory.TRANSIENT or attempt >= retry.retry_count:
                raise
        except TimeoutError as exc:
            if attempt >= retry.retry_count:
                raise ConnectorError(ErrorCategory.TRANSIENT, "외부 호출 시간 상한을 넘김") from exc
        finally:
            guards.after_call(succeeded)
        delay_ms = retry.delays_ms[attempt]
        jitter = delay_ms * retry.jitter_ratio * random.random()
        await asyncio.sleep((delay_ms + jitter) / 1000)
    raise AssertionError("도달할 수 없는 재시도 상태")
