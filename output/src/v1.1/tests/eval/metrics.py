"""설정에 적힌 판정식으로 실행 결과를 집계함."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .models import CaseResult, GoldenCase


@dataclass(frozen=True, slots=True)
class MetricValue:
    metric_id: str
    value: float | None
    sample_size: int
    target: dict[str, Any] | None
    verdict: str
    note: str


def percentile(values: Sequence[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * ratio) - 1)
    return ordered[index]


def _verdict(value: float | None, target: dict[str, Any] | None) -> str:
    if value is None:
        return "미측정"
    if target is None or target.get("value") is None:
        return "목표 없음 — 관찰값"
    expected = float(target["value"])
    operation = target["op"]
    passed = {
        "gte": value >= expected,
        "lte": value <= expected,
        "eq": value == expected,
    }.get(operation)
    if passed is None:
        raise ValueError(f"지원하지 않는 목표 비교식: {operation}")
    return "통과" if passed else "미달"


def aggregate(
    cases: Sequence[GoldenCase],
    results: Sequence[CaseResult],
    config: dict[str, Any],
    *,
    live_measurement: bool,
) -> list[MetricValue]:
    case_map = {case.case_id: case for case in cases}
    run_one = [result for result in results if result.run_id == 1]
    values: list[MetricValue] = []

    for spec in config["metrics"]:
        metric_id = spec["metric_id"]
        selected = [
            result
            for result in run_one
            if metric_id in case_map[result.case_id].metric_ids
            and case_map[result.case_id].scorable
        ]
        target = spec.get("target")
        kind = spec["kind"]
        note = ""
        value: float | None
        if spec.get("measurement") == "live_only" and not live_measurement:
            value = None
            note = "대역 계약 실행값을 제품 실측으로 쓰지 않음"
        elif kind == "p95_latency_ms":
            samples = [result.latency_ms for result in selected if result.latency_ms is not None]
            minimum = int(spec.get("minimum_samples", 0))
            ratio = float(spec["percentile_ratio"])
            value = percentile(samples, ratio) if len(samples) >= minimum else None
            if value is None:
                note = f"표본 {len(samples)}건 — 최소 {minimum}건 미충족"
        elif kind == "all_pass_ratio":
            value = (
                sum(not result.failed and result.must_include_hits == result.must_include_total for result in selected)
                / len(selected)
                if selected
                else None
            )
        elif kind == "failure_count":
            value = float(sum(result.failed for result in selected)) if selected else None
        else:
            raise ValueError(f"지원하지 않는 지표 계산식: {kind}")
        values.append(
            MetricValue(
                metric_id=metric_id,
                value=value,
                sample_size=len(selected),
                target=target,
                verdict=_verdict(value, target),
                note=note,
            )
        )

    diagnostics = config["diagnostics"]
    scored = [result for result in run_one if result.scorable]
    denominators = {
        "route_accuracy": len(scored),
        "must_include_coverage": sum(result.must_include_total for result in scored),
        "evidence_trace_rate": len(scored),
        "tool_sequence_accuracy": len(scored),
    }
    numerators = {
        "route_accuracy": sum(result.route_match for result in scored),
        "must_include_coverage": sum(result.must_include_hits for result in scored),
        "evidence_trace_rate": sum(result.evidence_present for result in scored),
        "tool_sequence_accuracy": sum(result.tool_sequence_match for result in scored),
    }
    for spec in diagnostics:
        metric_id = spec["metric_id"]
        denominator = denominators[metric_id]
        value = numerators[metric_id] / denominator if denominator else None
        target = spec.get("target")
        values.append(
            MetricValue(
                metric_id=metric_id,
                value=value,
                sample_size=denominator,
                target=target,
                verdict=_verdict(value, target),
                note="진단 지표 — ①·⑥의 배포 목표가 아님",
            )
        )
    return values


def reproducibility_differences(
    results: Sequence[CaseResult], repetitions: int
) -> dict[str, float]:
    """회차별 비율의 최대값과 최소값 차이를 숫자로 냄."""
    route_rates: list[float] = []
    evidence_rates: list[float] = []
    for run_id in range(1, repetitions + 1):
        run = [result for result in results if result.run_id == run_id and result.scorable]
        if not run:
            continue
        route_rates.append(sum(result.route_match for result in run) / len(run))
        evidence_rates.append(sum(result.evidence_present for result in run) / len(run))
    return {
        "route_accuracy_difference": max(route_rates) - min(route_rates) if route_rates else 0.0,
        "evidence_trace_rate_difference": (
            max(evidence_rates) - min(evidence_rates) if evidence_rates else 0.0
        ),
    }
