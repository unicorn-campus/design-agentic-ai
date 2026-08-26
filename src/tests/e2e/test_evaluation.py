from __future__ import annotations

import json
from pathlib import Path

import pytest
from evaluation.runner import (
    GOLDEN_SET_PATH,
    METRICS_PATH,
    RUN_CONFIG_PATH,
    load_golden_set,
    load_json,
    metric_snapshot,
    reproducibility,
    required_sample_size,
    run_once,
)


def test_golden_set_has_confirmed_count_and_distribution() -> None:
    items = load_golden_set()
    config = load_json(RUN_CONFIG_PATH)
    assert len(items) == config["expected_item_count"]
    assert {
        workflow: sum(item["workflow"] == workflow for item in items)
        for workflow in config["distribution"]
    } == config["distribution"]


def test_every_design_scoring_method_has_items() -> None:
    items = load_golden_set()
    metrics = load_json(METRICS_PATH)
    assert {item["scoring_method"] for item in items} == set(
        metrics["required_scoring_methods"]
    )


def test_error_item_remains_in_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    items = load_golden_set()[:2]

    def fail(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("의도한 실패")

    monkeypatch.setattr("evaluation.runner.invoke_api_entrypoint", fail)
    result = run_once(items, object(), 1)
    assert len(result["results"]) == len(items)
    assert all(not row["score"]["correct"] for row in result["results"])
    assert all(row["error"] for row in result["results"])


def test_thresholds_and_model_name_are_not_embedded_in_runner() -> None:
    source = Path(__file__).parent.joinpath("evaluation/runner.py").read_text(encoding="utf-8")
    metrics = load_json(METRICS_PATH)
    config = load_json(RUN_CONFIG_PATH)
    forbidden = [config["generation_model"]["model"]]
    forbidden.extend(
        str(metric["target"].get("value"))
        for metric in metrics["metrics"]
        if metric["target"].get("value") not in (None, 0, 1, 1.0)
    )
    assert all(value not in source for value in forbidden)


def test_two_runs_produce_numeric_reproducibility_differences() -> None:
    metrics = load_json(METRICS_PATH)
    base = {
        "workflow": "W-1",
        "latency_ms": 100.0,
        "score": {"grounded": True, "sensitive_exposures": 0, "unauthorized_changes": 0},
    }
    runs = [
        {"run": 1, "results": [base]},
        {"run": 2, "results": [{**base, "latency_ms": 120.0}]},
    ]
    values = reproducibility(runs, metrics)
    assert isinstance(values["G-1"]["mean_difference"], float)
    assert isinstance(values["Q-2"]["mean_difference"], float)
    assert isinstance(values["Q-3"]["mean_difference"], float)


def test_blank_answer_or_evidence_is_rejected(tmp_path: Path) -> None:
    item = load_golden_set()[0]
    item["expected_answer"] = ""
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected_answer"):
        load_golden_set(path)


def test_ratio_target_sample_size_is_counted_without_lowering_target() -> None:
    assert required_sample_size(0.95) == 20
    assert required_sample_size(1.0) is None


def test_metric_ids_and_names_match_design_configuration() -> None:
    metrics = load_json(METRICS_PATH)["metrics"]
    assert [metric["id"] for metric in metrics] == ["G-1", "G-2", "G-3", "Q-1", "Q-2", "Q-3"]
    assert [metric["name"] for metric in metrics[3:]] == ["응답시간", "설명가능성", "안전성"]


def test_unmeasurable_full_path_metrics_remain_unmeasured() -> None:
    metrics = load_json(METRICS_PATH)
    result = metric_snapshot([], metrics)
    assert result["G-2"]["value"] is None
    assert result["G-3"]["value"] is None
    assert result["Q-1"]["value"] is None


def test_every_role_success_criterion_has_one_judgment_mapping() -> None:
    criteria = load_json(METRICS_PATH)["role_criteria"]
    expected_stages = {
        *(f"S-R{number}" for number in range(1, 11)),
        *(f"S-B{number}" for number in range(1, 11)),
        *(f"S-E{number}" for number in range(1, 8)),
    }
    assert len(criteria) == len(expected_stages)
    assert {row["stage"] for row in criteria} == expected_stages
    assert all(row["role_id"] and row["criterion"] for row in criteria)
