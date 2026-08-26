from __future__ import annotations

import os

import pytest
from evaluation.runner import RUN_CONFIG_PATH, load_json, run_evaluation


@pytest.mark.live_call
@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="GROQ_API_KEY 미설정")
def test_full_golden_set_with_live_generation_model() -> None:
    expected_count = load_json(RUN_CONFIG_PATH)["expected_item_count"]
    raw_path, report_path, raw = run_evaluation()
    assert raw_path.exists()
    assert report_path.exists()
    assert len(raw["runs"]) == 2
    assert all(len(run["results"]) == expected_count for run in raw["runs"])
