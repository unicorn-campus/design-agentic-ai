"""평가 실행기 자체의 단위 시험."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from tests.eval.models import GoldenCase, load_golden_set, load_json
from tests.eval.runner import EvaluationRunner, ReplayEntryPoint

ROOT = Path(__file__).resolve().parent
GOLDEN = ROOT / "golden_set.jsonl"
CONFIG = ROOT / "metrics.json"
FIXTURE = ROOT / "fixtures" / "replay_responses.jsonl"


@pytest.fixture
def cases() -> list[GoldenCase]:
    return load_golden_set(GOLDEN)


@pytest.fixture
def config() -> dict[str, object]:
    return load_json(CONFIG)


def test_golden_count_and_type_distribution_match_design(cases: list[GoldenCase]) -> None:
    """⑤ 9절 문항 34건과 유형 배분을 그대로 유지함."""
    assert len(cases) == 34
    assert Counter(case.case_type for case in cases) == {
        "목록 조회": 8,
        "집계 · 추이": 7,
        "단건 사실 조회": 5,
        "의미 근접": 3,
        "코드 고정": 8,
        "해석 · 생성": 3,
    }
    assert [case.case_id for case in cases] == [f"GS-{index:02d}" for index in range(1, 35)]


def test_every_case_has_answer_evidence_route_and_nonempty_input(
    cases: list[GoldenCase],
) -> None:
    """정답 또는 근거가 빈 문항은 골든셋에 들어가지 않음."""
    for case in cases:
        assert case.input
        assert case.expected_answer
        assert case.expected_route
        assert case.evidence


def test_unscorable_cases_are_kept_with_an_explicit_reason(
    cases: list[GoldenCase],
) -> None:
    deferred = [case for case in cases if not case.scorable]
    assert {case.case_id for case in deferred} == {
        "GS-11",
        "GS-19",
        "GS-20",
        "GS-21",
        "GS-22",
        "GS-23",
        "GS-24",
        "GS-25",
        "GS-26",
        "GS-34",
    }
    assert all(case.unscorable_reason for case in deferred)


def test_replay_runs_all_cases_twice_without_dropping_any(
    cases: list[GoldenCase], config: dict[str, object]
) -> None:
    runner = EvaluationRunner(cases, config, ReplayEntryPoint(FIXTURE))
    results = runner.run()
    assert len(results) == 68
    assert Counter(result.case_id for result in results) == {
        case.case_id: 2 for case in cases
    }
    assert sum(result.failed for result in results) == 0


def test_metric_targets_are_loaded_from_config(
    cases: list[GoldenCase], config: dict[str, object]
) -> None:
    changed = json.loads(json.dumps(config))
    q2 = next(item for item in changed["metrics"] if item["metric_id"] == "Q-2 설명가능성")
    q2["target"]["value"] = 1.1
    runner = EvaluationRunner(
        cases, changed, ReplayEntryPoint(FIXTURE), live_measurement=True
    )
    values = {metric.metric_id: metric for metric in runner.metrics(runner.run())}
    assert values["Q-2 설명가능성"].value == 1.0
    assert values["Q-2 설명가능성"].verdict == "미달"


def test_mock_mode_does_not_claim_live_latency(
    cases: list[GoldenCase], config: dict[str, object]
) -> None:
    runner = EvaluationRunner(cases, config, ReplayEntryPoint(FIXTURE))
    values = {metric.metric_id: metric for metric in runner.metrics(runner.run())}
    assert values["Q-1 응답시간"].value is None
    assert values["Q-1 응답시간"].verdict == "미측정"
    assert values["Q-2 설명가능성"].value is None
    assert values["Q-3 안전성"].value is None


def test_entrypoint_error_stays_in_sample_as_failure(config: dict[str, object]) -> None:
    class BrokenEntryPoint:
        def invoke(self, case: GoldenCase) -> dict[str, object]:
            raise TimeoutError(case.case_id)

    case = load_golden_set(GOLDEN)[0]
    result = EvaluationRunner([case], config, BrokenEntryPoint()).run(repetitions=1)[0]
    assert result.failed is True
    assert result.case_id == case.case_id
    assert "TimeoutError" in (result.failure_reason or "")


def test_reproducibility_is_numeric_and_raw_is_preserved(
    cases: list[GoldenCase], config: dict[str, object], tmp_path: Path
) -> None:
    runner = EvaluationRunner(cases, config, ReplayEntryPoint(FIXTURE))
    results = runner.run()
    report = runner.build_report(results)
    raw_path = tmp_path / "raw.jsonl"
    runner.write_raw(results, raw_path)
    rows = raw_path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 68
    assert "경로 정확도 | 0.0000" in report
    assert "제품 품질 실측이 아니며" in report


def test_readme_open_item_count_matches_config(config: dict[str, object]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    open_items = config["open_items"]
    assert f"`[확인필요]` 목록 — {len(open_items)}건" in readme
    for item in open_items:
        assert str(item) in readme
