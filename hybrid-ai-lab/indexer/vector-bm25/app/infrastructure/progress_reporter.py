"""노드 완료 진행 상황을 명령행 화면에 한 줄씩 출력하는 어댑터임."""

from __future__ import annotations

from collections import Counter
import sys
from typing import TextIO

from app.application.ports import ProgressReporterPort


class ConsoleProgressReporter(ProgressReporterPort):
    """노드 이름·호출 회차·노드 시간·누적 시간을 사람이 읽는 형식으로 출력함.

    출력 스트림을 주입받으며 기본값은 표준 오류임. 표준 출력은 자동화 도구가 읽는 결과 JSON 전용이기 때문임.
    진행 상황을 저장하거나 실행 흐름을 바꾸지 않음.
    """

    def __init__(self, stream: TextIO | None = None) -> None:
        """출력 스트림을 설정하고 노드별 호출 회차를 0부터 셈.

        부수효과: 없음. 스트림이 None이면 출력 시점의 sys.stderr를 사용함.
        """
        self._stream = stream
        self._calls: Counter[str] = Counter()

    def node_completed(self, node: str, node_seconds: float, total_seconds: float) -> None:
        """노드 완료 한 줄을 출력함.

        embed·upsert처럼 배치마다 반복되는 노드는 몇 번째 호출인지 함께 표시함.
        부수효과: 스트림에 한 줄을 쓰고 즉시 비움. 출력 실패는 색인 작업을 멈추지 않도록 무시함.
        """
        self._calls[node] += 1
        count = self._calls[node]
        label = node if count == 1 else f"{node} #{count}"
        line = f"[노드 완료] {label:<22} 노드 {node_seconds:8.2f}초 | 누적 {total_seconds:8.2f}초"
        try:
            stream = self._stream or sys.stderr
            print(line, file=stream, flush=True)
        except (OSError, ValueError):
            # 닫힌 파이프·콘솔에 쓰지 못해도 진행 표시는 부가 기능이므로 색인 결과에 영향을 주지 않음.
            pass


__all__ = ["ConsoleProgressReporter"]
