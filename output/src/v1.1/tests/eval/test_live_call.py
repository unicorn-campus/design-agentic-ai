"""실물 API 시험. 기본 실행에서는 `live_call` 표식으로 빠짐."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.eval.models import load_golden_set, load_json
from tests.eval.runner import EvaluationRunner, LiveHttpEntryPoint

ROOT = Path(__file__).resolve().parent


@pytest.mark.live_call
def test_live_entrypoint_runs_every_golden_case() -> None:
    url = os.getenv("LUNCHPICK_EVAL_API_URL")
    if not url:
        pytest.skip("LUNCHPICK_EVAL_API_URL 값 없음 — 실물 API 진입점 미확정")
    cases = load_golden_set(ROOT / "golden_set.jsonl")
    config = load_json(ROOT / "metrics.json")
    runner = EvaluationRunner(
        cases,
        config,
        LiveHttpEntryPoint(url, timeout_s=5.0),
        live_measurement=True,
    )
    results = runner.run()
    assert len(results) == len(cases) * config["repetitions"]
