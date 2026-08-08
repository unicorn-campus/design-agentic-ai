"""관측 계층 — 기록 지점 계측 · 비용 카운터 · 감사 기록 · 내보내기 감싸개.

관측 백엔드 **제품 이름이 이 계층에 없음**(`D-11` `[확인필요]`). 내보낼 곳은 설정값으로만 옴.
"""

from __future__ import annotations

from .audit import AuditLog, AuditRow
from .cost_counter import CostVerdict, RuleCostCounter, WorstCase
from .exporter import (
    MemorySink,
    OtelSink,
    SpanRecord,
    SpanSink,
    StdoutJsonSink,
    build_sink,
    otel_available,
)
from .record import StepCoverage, StepRecorder, UnknownRecordItem

__all__ = [
    "AuditLog",
    "AuditRow",
    "CostVerdict",
    "MemorySink",
    "OtelSink",
    "RuleCostCounter",
    "SpanRecord",
    "SpanSink",
    "StdoutJsonSink",
    "StepCoverage",
    "StepRecorder",
    "UnknownRecordItem",
    "WorstCase",
    "build_sink",
    "otel_available",
]
