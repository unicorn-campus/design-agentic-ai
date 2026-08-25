from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


REQUIRED_SECTIONS = frozenset({
    "stage_logs",
    "segment_logs",
    "observation_names",
    "observation_sinks",
    "input_rules",
    "approval_points",
    "delegation_limits",
    "connector_limits",
    "circuit_breakers",
    "cost_limits",
    "output_rules",
    "kill_switches",
    "alert_thresholds",
    "masking",
})


class PolicyRow(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    workflow: str | None = None
    stage: str | None = None


class GuardrailPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1"]
    source: str
    decisions: dict[str, Any]
    stage_logs: list[PolicyRow]
    segment_logs: list[PolicyRow]
    observation_names: list[PolicyRow]
    observation_sinks: list[PolicyRow]
    input_rules: list[PolicyRow]
    approval_points: list[PolicyRow]
    delegation_limits: list[PolicyRow]
    connector_limits: list[PolicyRow]
    circuit_breakers: list[PolicyRow]
    cost_limits: list[PolicyRow]
    output_rules: list[PolicyRow]
    kill_switches: list[PolicyRow]
    alert_thresholds: list[PolicyRow]
    masking: list[PolicyRow]

    @model_validator(mode="after")
    def validate_policy_integrity(self) -> "GuardrailPolicy":
        ids: list[str] = []
        for section in REQUIRED_SECTIONS:
            rows = getattr(self, section)
            ids.extend(row.id for row in rows)
        duplicates = sorted({row_id for row_id in ids if ids.count(row_id) > 1})
        if duplicates:
            raise ValueError(f"규칙 ID 중복: {', '.join(duplicates)}")
        if len(self.observation_names) != 4:
            raise ValueError("관측 이름 규칙은 4행이어야 함")
        stage_counts: dict[str, int] = {}
        for row in self.stage_logs:
            stage_counts[row.workflow or ""] = stage_counts.get(row.workflow or "", 0) + 1
        if stage_counts != {"W-1": 10, "W-2": 10, "W-3": 7}:
            raise ValueError(f"단계 기록 행 수 불일치: {stage_counts}")
        limit_targets = {(row.workflow, row.model_extra.get("target")) for row in self.connector_limits}
        breaker_targets = {(row.workflow, row.model_extra.get("target")) for row in self.circuit_breakers}
        if limit_targets != breaker_targets:
            raise ValueError("Circuit Breaker 대상 집합이 커넥터 상한 대상 집합과 다름")
        return self


DEFAULT_POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "guardrail_policy.json"


@lru_cache(maxsize=1)
def load_policy(path: str | Path = DEFAULT_POLICY_PATH) -> GuardrailPolicy:
    policy_path = Path(path)
    raw = policy_path.read_text(encoding="utf-8")
    return GuardrailPolicy.model_validate_json(raw)
