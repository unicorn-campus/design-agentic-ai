from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from help_desk_guardrails.masking import SensitiveDataMasker

from .context import current_labels


def configure_opentelemetry(service_name: str, span_exporter: Any | None = None) -> Any:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(span_exporter or ConsoleSpanExporter()))
    return trace.get_tracer(__name__, tracer_provider=provider)


def observation_name(workflow_id: str, stage_id: str | None = None, segment: tuple[str, str] | None = None) -> str:
    if stage_id is not None and segment is not None:
        raise ValueError("단계와 구간 이름을 동시에 만들 수 없음")
    if stage_id is not None:
        return f"{workflow_id}.{stage_id}"
    if segment is not None:
        return f"{workflow_id}.{segment[0]}~{segment[1]}"
    return workflow_id


class Exporter(Protocol):
    def export(self, log_type: str, payload: dict[str, Any]) -> None: ...


@dataclass
class InMemoryExporter:
    records: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def export(self, log_type: str, payload: dict[str, Any]) -> None:
        self.records.append((log_type, payload))


class GuardedExporter:
    def __init__(self, delegate: Exporter, masker: SensitiveDataMasker) -> None:
        self._delegate = delegate
        self._masker = masker

    def export(self, log_type: str, payload: dict[str, Any]) -> None:
        if log_type == "트레이싱 로그":
            safe = {
                "요약": "입력과 출력 원문을 적재하지 않음",
                "해시": hashlib.sha256(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
                **current_labels(),
            }
        elif log_type == "구조화 로그":
            safe = {
                key: value
                for key, value in payload.items()
                if key in {"요청ID", "워크플로우ID", "지연", "총토큰", "최종상태", "종료사유"}
            }
        elif log_type == "감사 로그":
            safe = self._masker.sanitize(payload, "audit")
        else:
            raise ValueError(f"정의되지 않은 로그 유형: {log_type}")
        self._delegate.export(log_type, safe)


@dataclass
class NodeTelemetryCallback:
    exporter: Exporter
    stage_fields: dict[tuple[str, str], tuple[str, ...]]

    def on_node_end(self, workflow_id: str, stage_id: str, values: dict[str, Any]) -> None:
        allowed = self.stage_fields[(workflow_id, stage_id)]
        payload = {field: values.get(field) for field in allowed}
        payload.update(current_labels())
        payload["관측이름"] = observation_name(workflow_id, stage_id=stage_id)
        self.exporter.export("구조화 로그", payload)
