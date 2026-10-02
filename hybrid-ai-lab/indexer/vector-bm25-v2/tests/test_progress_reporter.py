"""노드 완료 진행 표시의 출력 형식을 검증함."""

from __future__ import annotations

import io

from app.infrastructure.progress_reporter import ConsoleProgressReporter


def test_console_reporter_prints_node_time_total_and_repeat_count() -> None:
    """한 줄에 노드 이름·노드 시간·누적 시간을 쓰고 반복 노드는 회차를 붙임을 보증함."""
    stream = io.StringIO()
    reporter = ConsoleProgressReporter(stream)

    reporter.node_completed("discover_docs", 0.123, 0.5)
    reporter.node_completed("embed", 1.0, 2.0)
    reporter.node_completed("embed", 1.5, 3.75)

    lines = stream.getvalue().splitlines()
    assert lines[0].startswith("[노드 완료] discover_docs")
    assert "노드     0.12초" in lines[0] and "누적     0.50초" in lines[0]
    assert "[노드 완료] embed " in lines[1]
    assert "[노드 완료] embed #2" in lines[2] and "누적     3.75초" in lines[2]


def test_console_reporter_ignores_closed_stream() -> None:
    """출력 스트림이 닫혀도 진행 표시 실패가 색인 작업으로 번지지 않음을 보증함."""
    stream = io.StringIO()
    stream.close()

    ConsoleProgressReporter(stream).node_completed("publish", 0.1, 0.2)
