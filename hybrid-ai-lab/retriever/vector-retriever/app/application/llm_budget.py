"""서버 프로세스 전체의 LLM 전송 횟수 예산을 집계함."""

from __future__ import annotations

import threading

from .errors import LLMCallLimitError, LLMConfigError


class LLMCallCounter:
    """프로세스 안에서 서버 누적 전송 횟수를 원자적으로 집계함."""

    def __init__(self, limit: int):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise LLMConfigError("MAX_LLM_CALLS_TOTAL은 양의 정수여야 함")
        self.limit = limit
        self._used = 0
        self._lock = threading.Lock()

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.limit - self._used)

    def add(self, count: int) -> int:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("LLM 호출 증가량은 0 이상의 정수여야 함")
        with self._lock:
            if self._used + count > self.limit:
                raise LLMCallLimitError(scope="total", limit=self.limit, used=self._used)
            self._used += count
            return self._used


__all__ = ["LLMCallCounter"]
