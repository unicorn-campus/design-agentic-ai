"""동기 노드의 작업자 수를 제한하는 타임아웃·감사 로깅 런타임."""

from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any, Callable, TypeVar


T = TypeVar("T")
MAX_WORKERS = 4


class OperationTimeoutError(TimeoutError):
    """하위 호출이 주어진 마감선을 넘었음을 나타냄."""

    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(f"{operation} 타임아웃: {timeout_seconds}초")
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class TimeoutCapacityError(TimeoutError):
    """이전 타임아웃 작업이 남아 작업자 상한에 도달함."""


class BoundedTimeoutRunner:
    """대기열을 만들지 않고 최대 작업자 수만 유지하는 실행기."""

    def __init__(self, max_workers: int = MAX_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="vector-timeout")
        self._slots = threading.BoundedSemaphore(max_workers)
        self._closed = False
        self._lock = threading.Lock()

    def run(
        self,
        # 실행할 함수: 받은 값을 처리할 함수이며, 결과의 자료형(T)을 그대로 돌려줌.
        function: Callable[..., T],
        # *args: key 없이 값만 전달한 추가 인수들을 순서대로 모음.
        # 예: run(함수, "민지", 25, ...)를 호출하면 args는 ("민지", 25)가 됨.
        *args: Any,
        # 함수가 끝나기를 기다릴 최대 시간(초)임.
        timeout_seconds: float,
        # 타임아웃이 나면 오류 메시지에 표시할 작업 이름임.
        operation: str,
        # **kwargs: key=value 형식으로 전달한 추가 인수들을 이름과 함께 모음.
        # 예: run(함수, 이름="민지", ...)를 호출하면 kwargs는 {"이름": "민지"}가 됨.
        **kwargs: Any,
    ) -> T:
        timeout = float(timeout_seconds)
        if timeout <= 0:
            raise ValueError("타임아웃은 양수여야 함")
        with self._lock:
            if self._closed:
                raise RuntimeError("타임아웃 실행기가 종료됨")
        if not self._slots.acquire(blocking=False):
            raise TimeoutCapacityError("타임아웃 작업자 상한에 도달함")
        try:
            future = self._executor.submit(function, *args, **kwargs)
        except BaseException:
            self._slots.release()
            raise
        future.add_done_callback(lambda _future: self._slots.release())
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError as error:
            future.cancel()
            raise OperationTimeoutError(operation, timeout) from error

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)


_RUNNER = BoundedTimeoutRunner()
_LOG_LOCK = threading.Lock()
atexit.register(_RUNNER.close)


def run_with_timeout(
    # 실행할 함수: 받은 값을 처리할 함수이며, 결과의 자료형(T)을 그대로 돌려줌.
    function: Callable[..., T],
    # *args: key 없이 값만 전달한 추가 인수들을 순서대로 모음.
    # 예: run(함수, "민지", 25, ...)를 호출하면 args는 ("민지", 25)가 됨.
    *args: Any,
    # 함수가 끝나기를 기다릴 최대 시간(초)임.
    timeout_seconds: float,
    # 타임아웃이 나면 오류 메시지에 표시할 작업 이름임.
    operation: str,
    # **kwargs: key=value 형식으로 전달한 추가 인수들을 이름과 함께 모음.
    # 예: run(함수, 이름="민지", ...)를 호출하면 kwargs는 {"이름": "민지"}가 됨.
    **kwargs: Any,
) -> T:
    """프로세스 공용 제한 실행기에서 하위 호출을 실행함."""

    return _RUNNER.run(
        function,
        *args,
        timeout_seconds=timeout_seconds,
        operation=operation,
        **kwargs,
    )


def append_node_log(log_path: Path, thread_id: str, node: str, event: str, elapsed_ms: int, error: str = "") -> None:
    """본문·메타데이터·비밀값 없이 노드 실행 결과만 기록함."""

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": thread_id,
        "node": node,
        "event": event,
        "elapsed_ms": elapsed_ms,
    }
    if error:
        row["error_type"] = error
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    with _LOG_LOCK, log_path.open("a", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
