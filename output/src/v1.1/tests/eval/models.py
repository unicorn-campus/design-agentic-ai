"""골든셋과 실행 결과의 파일 계약."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GoldenCase:
    case_id: str
    input: str
    case_type: str
    expected_route: str
    expected_answer: dict[str, Any]
    must_include: tuple[str, ...]
    evidence: tuple[str, ...]
    expected_tool_calls: tuple[str, ...]
    metric_ids: tuple[str, ...]
    scorable: bool = True
    unscorable_reason: str | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "GoldenCase":
        required = {
            "case_id",
            "input",
            "case_type",
            "expected_route",
            "expected_answer",
            "must_include",
            "evidence",
            "expected_tool_calls",
            "metric_ids",
            "scorable",
        }
        missing = sorted(required - row.keys())
        if missing:
            raise ValueError(f"골든셋 필수 열이 없음: {', '.join(missing)}")
        if not row["expected_answer"] or not row["evidence"]:
            raise ValueError(f"{row['case_id']}의 정답 또는 근거가 비어 있음")
        reason = row.get("unscorable_reason")
        if not row["scorable"] and not reason:
            raise ValueError(f"{row['case_id']}는 측정 보류 사유가 필요함")
        return cls(
            case_id=str(row["case_id"]),
            input=str(row["input"]),
            case_type=str(row["case_type"]),
            expected_route=str(row["expected_route"]),
            expected_answer=dict(row["expected_answer"]),
            must_include=tuple(str(value) for value in row["must_include"]),
            evidence=tuple(str(value) for value in row["evidence"]),
            expected_tool_calls=tuple(str(value) for value in row["expected_tool_calls"]),
            metric_ids=tuple(str(value) for value in row["metric_ids"]),
            scorable=bool(row["scorable"]),
            unscorable_reason=str(reason) if reason else None,
        )


@dataclass(frozen=True, slots=True)
class EvaluationResponse:
    route: str
    content: str
    payload: dict[str, Any]
    evidence: tuple[str, ...]
    tool_calls: tuple[str, ...] = ()
    latency_ms: float | None = None
    cost_krw: float | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "EvaluationResponse":
        return cls(
            route=str(row.get("route", "")),
            content=str(row.get("content", "")),
            payload=dict(row.get("payload", {})),
            evidence=tuple(str(value) for value in row.get("evidence", [])),
            tool_calls=tuple(str(value) for value in row.get("tool_calls", [])),
            latency_ms=float(row["latency_ms"]) if row.get("latency_ms") is not None else None,
            cost_krw=float(row["cost_krw"]) if row.get("cost_krw") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class CaseResult:
    run_id: int
    case_id: str
    scorable: bool
    route_match: bool
    must_include_hits: int
    must_include_total: int
    evidence_present: bool
    tool_sequence_match: bool
    latency_ms: float | None
    failed: bool
    failure_reason: str | None
    response: EvaluationResponse | None = field(repr=False)

    def as_dict(self) -> dict[str, Any]:
        value = {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "scorable": self.scorable,
            "route_match": self.route_match,
            "must_include_hits": self.must_include_hits,
            "must_include_total": self.must_include_total,
            "evidence_present": self.evidence_present,
            "tool_sequence_match": self.tool_sequence_match,
            "latency_ms": self.latency_ms,
            "failed": self.failed,
            "failure_reason": self.failure_reason,
        }
        if self.response is not None:
            value["response"] = {
                "route": self.response.route,
                "content": self.response.content,
                "payload": self.response.payload,
                "evidence": list(self.response.evidence),
                "tool_calls": list(self.response.tool_calls),
                "latency_ms": self.response.latency_ms,
                "cost_krw": self.response.cost_krw,
            }
        return value


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_golden_set(path: Path) -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = GoldenCase.from_dict(json.loads(line))
        if case.case_id in seen:
            raise ValueError(f"골든셋 문항 식별자 중복: {case.case_id}({line_number}행)")
        seen.add(case.case_id)
        cases.append(case)
    return cases
