"""관측 기록 내보내기 — 갈아 끼울 수 있게 한 겹 감쌈.

**제품 이름이 이 파일에 없음.** `D-11`의 관측 백엔드 제품이 `[확인필요]`라서,
내보낼 곳은 설정값(`LUNCHPICK_OTLP_ENDPOINT`) 하나로만 정함. 값이 비면 로컬에서 볼 수 있는
대체 방식(표준출력 JSON 한 줄씩)만 붙음.

이름 규칙 병기 — OpenTelemetry GenAI 이름 규칙은 문서 상태가 `Development`이며 **확정 표준이
아닌 표준 후보**임(조회일 2026-08-05 · ⑥ 10절). `gen_ai.*`에 `Stable`은 0건이고
`error.type` · `server.address` · `server.port`만 `Stable`임. 이름이 바뀔 수 있음.

여기서 쓴 규격은 코드 작성 직전에 context7 MCP로 확인함(2026-08-08) —
`TracerProvider(resource=...)` · `trace.set_tracer_provider` · `BatchSpanProcessor` ·
`SimpleSpanProcessor` · `ConsoleSpanExporter` · `tracer.start_as_current_span(name, attributes=...)` ·
`Status(StatusCode.ERROR, description)`.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Protocol, TextIO, runtime_checkable

__all__ = [
    "SpanRecord",
    "SpanSink",
    "StdoutJsonSink",
    "MemorySink",
    "OtelSink",
    "otel_available",
    "build_sink",
]

_LOGGER_NAME = "lunchpick.observability"


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """내보낼 기록 1토막. 값은 **이미 가려진 것만** 담겨 옴."""

    name: str
    step_id: str | None
    record_points: tuple[str, ...]
    attributes: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    """`error.type` — A07에서 `Stable`인 속성."""

    def as_json_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "span_name": self.name,
            "step_id": self.step_id,
            "record_points": list(self.record_points),
            "attributes": self.attributes,
        }
        if self.error_type is not None:
            out["error.type"] = self.error_type
        return out


@runtime_checkable
class SpanSink(Protocol):
    """내보내는 곳. 제품이 정해지면 이 자리만 갈아 끼움."""

    def emit(self, record: SpanRecord) -> None: ...

    def flush(self) -> None: ...


class StdoutJsonSink:
    """로컬 개발용 대체 방식 — 구조화 JSON 로그 한 줄씩(`D-11` 「로컬 개발 시 대체 방식」)."""

    def __init__(self, stream: TextIO | None = None, logger: logging.Logger | None = None) -> None:
        self._stream = stream
        self._logger = logger or logging.getLogger(_LOGGER_NAME)

    def emit(self, record: SpanRecord) -> None:
        line = json.dumps(record.as_json_dict(), ensure_ascii=False)
        if self._stream is not None:
            self._stream.write(line + "\n")
        else:
            self._logger.info(line)

    def flush(self) -> None:
        if self._stream is not None:
            self._stream.flush()


class MemorySink:
    """시험용. 바깥을 부르지 않음."""

    def __init__(self) -> None:
        self.records: list[SpanRecord] = []

    def emit(self, record: SpanRecord) -> None:
        self.records.append(record)

    def flush(self) -> None:  # noqa: D102 - 할 일이 없음
        return None

    def attribute_values(self) -> list[Any]:
        """기록 전수 검색에 쓰는 평평한 값 목록."""
        out: list[Any] = []
        for record in self.records:
            _flatten(record.as_json_dict(), out)
        return out


def _flatten(value: Any, out: list[Any]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            out.append(key)
            _flatten(item, out)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            _flatten(item, out)
    else:
        out.append(value)


def otel_available() -> bool:
    """관측 SDK가 이 환경에 깔려 있나. 없으면 대체 방식으로 감."""
    try:
        import opentelemetry.sdk.trace  # noqa: F401
    except Exception:
        return False
    return True


class OtelSink:
    """표준 규격(OTLP)으로 내보내는 자리.

    `endpoint`가 없으면 **콘솔 내보내기**로 떨어짐. 제품 이름은 이 파일에 없고
    설정값으로만 들어옴.
    """

    def __init__(self, *, endpoint: str | None, service_name: str) -> None:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )

        self._trace = trace
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        if endpoint:
            exporter = self._otlp_exporter(endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        else:
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        self._provider = provider
        self._tracer = trace.get_tracer(_LOGGER_NAME)

    @staticmethod
    def _otlp_exporter(endpoint: str) -> Any:
        """표준 내보내기 규격만 씀. 어느 제품인지는 주소값이 정함."""
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter(endpoint=endpoint)

    def emit(self, record: SpanRecord) -> None:
        from opentelemetry.trace import Status, StatusCode

        attributes = {k: _as_attribute(v) for k, v in record.attributes.items()}
        attributes["step_id"] = record.step_id or ""
        attributes["record_points"] = ",".join(record.record_points)
        with self._tracer.start_as_current_span(record.name, attributes=attributes) as span:
            if record.error_type is not None:
                span.set_attribute("error.type", record.error_type)
                span.set_status(Status(StatusCode.ERROR, record.error_type))

    def flush(self) -> None:
        self._provider.force_flush()


def _as_attribute(value: Any) -> Any:
    """스팬 속성은 원시값·원시값 배열만 받음. 그 밖은 JSON 글로 눌러 넣음."""
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)) and all(
        isinstance(v, (str, bool, int, float)) for v in value
    ):
        return list(value)
    return json.dumps(value, ensure_ascii=False, default=str)


def build_sink(
    *,
    endpoint: str | None,
    service_name: str,
    prefer_otel: bool = True,
) -> SpanSink:
    """내보낼 곳을 고름. 제품 이름을 고르지 않음 — 주소값과 SDK 유무만 봄."""
    if prefer_otel and otel_available():
        return OtelSink(endpoint=endpoint, service_name=service_name)
    return StdoutJsonSink(stream=sys.stdout if endpoint is None else None)
