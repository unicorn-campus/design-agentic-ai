"""주입된 실행기의 전체 인덱싱 구간을 잠금으로 감싸 동시 쓰기를 제한함."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.application.ports import PipelineRunnerPort
from app.infrastructure.file_lock import CrossPlatformFileLock


class LockedPipelineRunner(PipelineRunnerPort):
    """같은 결과 디렉터리에서 인덱싱 실행이 겹치지 않도록 보호함.

    PipelineRunnerPort와 잠금 경로·생성 함수를 받으며, 그래프의 노드나 재개 규칙을 직접 결정하지 않음.
    """

    def __init__(
        self,
        inner: PipelineRunnerPort,
        lock_path: Path,
        *,
        lock_factory: Callable[[Path], CrossPlatformFileLock] = CrossPlatformFileLock,
    ) -> None:
        """실행 계약과 잠금 생성 방법을 주입받고 실제 잠금은 run 호출까지 미룸."""
        self.inner = inner
        self.lock_path = Path(lock_path)
        self.lock_factory = lock_factory

    def run(self, initial_state: dict, thread_id: str) -> dict:
        """쓰기 잠금을 확보한 동안 실행 포트에 요청을 위임하고 결과를 그대로 반환함.

        인자: initial_state와 thread_id는 내부 실행 포트의 요청·재개 계약을 따라야 함.
        예외: 잠금을 얻지 못하면 LockUnavailableError가 발생하며 내부 실행 오류는 그대로 전달됨.
        부수효과: 잠금 파일을 만들 수 있고 내부 실행기가 체크포인트·산출물을 갱신할 수 있음.
        """
        with self.lock_factory(self.lock_path):
            return self.inner.run(initial_state, thread_id)


__all__ = ["LockedPipelineRunner"]
