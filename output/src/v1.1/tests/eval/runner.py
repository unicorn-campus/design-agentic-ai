"""골든셋 전건을 진입점 포트로 실행하고 원본·요약 리포트를 남김."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from .metrics import MetricValue, aggregate, reproducibility_differences
from .models import CaseResult, EvaluationResponse, GoldenCase, load_golden_set, load_json


class EntryPoint(Protocol):
    def invoke(self, case: GoldenCase) -> Mapping[str, Any]: ...


class ReplayEntryPoint:
    """외부 호출 없이 고정 응답을 돌려주는 대역 포트."""

    def __init__(self, fixture_path: Path) -> None:
        rows = [
            json.loads(line)
            for line in fixture_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self._responses = {str(row["case_id"]): row["response"] for row in rows}

    def invoke(self, case: GoldenCase) -> Mapping[str, Any]:
        try:
            return self._responses[case.case_id]
        except KeyError as exc:
            raise KeyError(f"대역 응답이 없는 문항: {case.case_id}") from exc


class LiveHttpEntryPoint:
    """실제 API가 생긴 뒤 `live_call`에서만 쓰는 HTTP 포트."""

    def __init__(self, url: str, timeout_s: float) -> None:
        self.url = url
        self.timeout_s = timeout_s

    def invoke(self, case: GoldenCase) -> Mapping[str, Any]:
        request = urllib.request.Request(
            self.url,
            data=json.dumps(
                {"case_id": case.case_id, "input": case.input}, ensure_ascii=False
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))


class EvaluationRunner:
    def __init__(
        self,
        cases: Sequence[GoldenCase],
        config: dict[str, Any],
        entrypoint: EntryPoint,
        *,
        live_measurement: bool = False,
    ) -> None:
        self.cases = tuple(cases)
        self.config = config
        self.entrypoint = entrypoint
        self.live_measurement = live_measurement

    @staticmethod
    def _searchable_text(response: EvaluationResponse) -> str:
        return json.dumps(
            {"content": response.content, "payload": response.payload},
            ensure_ascii=False,
            sort_keys=True,
        )

    def _run_case(self, case: GoldenCase, run_id: int) -> CaseResult:
        started = time.perf_counter()
        try:
            raw = self.entrypoint.invoke(case)
            elapsed_ms = (time.perf_counter() - started) * 1000
            response = EvaluationResponse.from_dict(dict(raw))
            text = self._searchable_text(response)
            hits = sum(term in text for term in case.must_include)
            evidence_present = bool(response.evidence) and all(
                expected in response.evidence for expected in case.evidence
            )
            tool_match = response.tool_calls == case.expected_tool_calls
            failure_parts: list[str] = []
            if case.scorable and response.route != case.expected_route:
                failure_parts.append("기대 경로 불일치")
            if case.scorable and hits != len(case.must_include):
                failure_parts.append("필수 응답 요소 누락")
            if case.scorable and not evidence_present:
                failure_parts.append("근거 추적 누락")
            if case.scorable and not tool_match:
                failure_parts.append("도구 호출 순서 불일치")
            return CaseResult(
                run_id=run_id,
                case_id=case.case_id,
                scorable=case.scorable,
                route_match=response.route == case.expected_route,
                must_include_hits=hits,
                must_include_total=len(case.must_include),
                evidence_present=evidence_present,
                tool_sequence_match=tool_match,
                latency_ms=response.latency_ms if response.latency_ms is not None else elapsed_ms,
                failed=bool(failure_parts),
                failure_reason=" · ".join(failure_parts) or None,
                response=response,
            )
        except Exception as exc:  # 오류 문항도 표본에 실패로 남겨야 함
            return CaseResult(
                run_id=run_id,
                case_id=case.case_id,
                scorable=case.scorable,
                route_match=False,
                must_include_hits=0,
                must_include_total=len(case.must_include),
                evidence_present=False,
                tool_sequence_match=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                failed=True,
                failure_reason=f"{type(exc).__name__}: {exc}",
                response=None,
            )

    def run(self, repetitions: int | None = None) -> list[CaseResult]:
        repeat = repetitions or int(self.config["repetitions"])
        return [
            self._run_case(case, run_id)
            for run_id in range(1, repeat + 1)
            for case in self.cases
        ]

    def metrics(self, results: Sequence[CaseResult]) -> list[MetricValue]:
        return aggregate(
            self.cases,
            results,
            self.config,
            live_measurement=self.live_measurement,
        )

    def write_raw(self, results: Sequence[CaseResult], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "\n".join(json.dumps(result.as_dict(), ensure_ascii=False) for result in results)
            + "\n",
            encoding="utf-8",
        )

    def build_report(self, results: Sequence[CaseResult]) -> str:
        metrics = self.metrics(results)
        repetitions = len({result.run_id for result in results})
        differences = reproducibility_differences(results, repetitions)
        unscorable = [case for case in self.cases if not case.scorable]
        failures = [result for result in results if result.failed]
        mode = "실물 API" if self.live_measurement else "대역 계약"
        lines = [
            "# 런치픽 골든셋 평가 리포트",
            "",
            f"- 실행 모드: **{mode}**",
            f"- 골든셋: {len(self.cases)}문항 × {repetitions}회 = {len(results)}실행",
            f"- 측정 보류: {len(unscorable)}문항",
            f"- 실행 실패: {len(failures)}건(회차 포함)",
            "",
        ]
        if not self.live_measurement:
            lines.extend(
                [
                    "> 이 결과는 고정 대역이 평가 계약을 지키는지 확인한 값임. 제품 품질 실측이 아니며,",
                    "> 실물 API 지표는 `미측정`으로 유지함.",
                    "",
                ]
            )
        lines.extend(
            [
                "## 지표",
                "",
                "| 지표 | 목표 | 실측값 | 표본 | 판정 | 비고 |",
                "|------|------|-------:|-----:|------|------|",
            ]
        )
        for metric in metrics:
            target = (
                "목표 없음"
                if metric.target is None or metric.target.get("value") is None
                else f"{metric.target['op']} {metric.target['value']}"
            )
            value = "미측정" if metric.value is None else f"{metric.value:.4f}"
            lines.append(
                f"| {metric.metric_id} | {target} | {value} | {metric.sample_size} | "
                f"{metric.verdict} | {metric.note or '—'} |"
            )
        lines.extend(
            [
                "",
                "## 재현성",
                "",
                "| 항목 | 회차 간 최대 차 |",
                "|------|---------------:|",
                f"| 경로 정확도 | {differences['route_accuracy_difference']:.4f} |",
                f"| 근거 추적률 | {differences['evidence_trace_rate_difference']:.4f} |",
                "",
                "## 측정 보류 문항",
                "",
                "| 문항 | 사유 |",
                "|------|------|",
            ]
        )
        lines.extend(
            f"| {case.case_id} | {case.unscorable_reason} |" for case in unscorable
        )
        lines.extend(
            [
                "",
                "## 다음 조치",
                "",
                "- 실물 API 진입점 확정 후 `live_call`로 전건 재실행 필요 — `07-api-ui` 담당",
                "- 알레르겐 판정 원천 확보 후 GS-19 ~ GS-26 측정 보류 해제 필요 — `02-dataset` 담당",
                "- 향상률 산출식 확정 후 GS-11·GS-34 채점 활성화 필요 — `03-knowledge` 담당",
                "- Q-1은 동시 사용자 부하시험으로 별도 측정 필요 — `09-eval` 실물 실행 단계",
                "",
            ]
        )
        return "\n".join(lines)


def _arguments() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="런치픽 골든셋 평가 실행기")
    parser.add_argument("--golden", type=Path, default=root / "golden_set.jsonl")
    parser.add_argument("--config", type=Path, default=root / "metrics.json")
    parser.add_argument("--fixture", type=Path, default=root / "fixtures" / "replay_responses.jsonl")
    parser.add_argument("--live-url")
    parser.add_argument("--timeout-s", type=float, default=5.0)
    parser.add_argument("--raw-out", type=Path, default=root / "reports" / "raw-baseline-mock.jsonl")
    parser.add_argument("--report-out", type=Path, default=root / "reports" / "eval-baseline-mock.md")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cases = load_golden_set(args.golden)
    config = load_json(args.config)
    entrypoint: EntryPoint
    if args.live_url:
        entrypoint = LiveHttpEntryPoint(args.live_url, args.timeout_s)
        live = True
    else:
        entrypoint = ReplayEntryPoint(args.fixture)
        live = False
    runner = EvaluationRunner(cases, config, entrypoint, live_measurement=live)
    results = runner.run()
    runner.write_raw(results, args.raw_out)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(runner.build_report(results), encoding="utf-8")
    print(
        f"평가 실행 완료 - {len(cases)}문항 × {config['repetitions']}회 · "
        f"실패 {sum(result.failed for result in results)}건 · {args.report_out}"
    )


if __name__ == "__main__":
    main()
