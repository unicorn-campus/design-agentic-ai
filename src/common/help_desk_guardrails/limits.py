from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic


class InvocationLimitExceeded(RuntimeError):
    pass


class CircuitOpen(RuntimeError):
    def __init__(self, fallback: str) -> None:
        super().__init__(fallback)
        self.fallback = fallback


@dataclass
class InvocationLimiter:
    concurrent_limit: int
    call_limit: int
    depth_limit: int | None = None
    active: int = 0
    calls: int = 0

    def acquire(self, depth: int | None = None) -> None:
        if self.depth_limit is not None and depth is not None and depth > self.depth_limit:
            raise InvocationLimitExceeded("위임 깊이 상한 초과")
        if self.active >= self.concurrent_limit:
            raise InvocationLimitExceeded("동시 실행 상한 초과")
        if self.calls >= self.call_limit:
            raise InvocationLimitExceeded("호출 수 상한 초과")
        self.active += 1
        self.calls += 1

    def release(self) -> None:
        self.active = max(0, self.active - 1)


def retry_delays(interval: dict[str, int], attempts: int) -> tuple[int, ...]:
    if attempts < 0:
        raise ValueError("시도 횟수는 음수일 수 없음")
    initial = interval["initial_ms"]
    if interval["kind"] == "fixed":
        return (initial,) * attempts
    multiplier = interval["multiplier"]
    maximum = interval["max_ms"]
    return tuple(min(initial * multiplier**index, maximum) for index in range(attempts))


class CircuitState(str, Enum):
    CLOSED = "닫힘"
    OPEN = "열림"
    HALF_OPEN = "반열림"


class CircuitBreaker:
    def __init__(self, failure_threshold: int, open_seconds: float, fallback: str) -> None:
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.fallback = fallback
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at: float | None = None
        self._probe_in_progress = False

    def before_call(self, now: float | None = None) -> None:
        now = monotonic() if now is None else now
        if self.state is CircuitState.OPEN:
            assert self.opened_at is not None
            if now - self.opened_at < self.open_seconds:
                raise CircuitOpen(self.fallback)
            self.state = CircuitState.HALF_OPEN
        if self.state is CircuitState.HALF_OPEN:
            if self._probe_in_progress:
                raise CircuitOpen(self.fallback)
            self._probe_in_progress = True

    def record_success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None
        self._probe_in_progress = False

    def record_failure(self, now: float | None = None) -> None:
        self.failures += 1
        self._probe_in_progress = False
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = monotonic() if now is None else now
