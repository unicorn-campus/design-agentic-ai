"""시험용 설정 대역. 여기 숫자는 시험 고정값이며 소스 코드에는 없음."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from common.config import Settings, load_settings, reset_settings_cache

STEP_TIMEOUT_MS = {"S-R2": 50, "S-R3": 200, "S-R4": 500, "S-R11": 1800, "S-R16": 300}
STEP_RETRY_COUNT = {"S-R2": 0, "S-R3": 1, "S-R4": 1, "S-R11": 1, "S-R16": 0}
BUDGET_TOTAL_MS = {"S-R": 3000}
BUDGET_LANDING_MS = {"S-R": 150}

REQUIRED_ENV = {
    "LUNCHPICK_STEP_TIMEOUT_MS": json.dumps(STEP_TIMEOUT_MS),
    "LUNCHPICK_STEP_RETRY_COUNT": json.dumps(STEP_RETRY_COUNT),
    "LUNCHPICK_LLM_PROVIDER": "anthropic",
    "LUNCHPICK_LLM_MODEL": "test-model-id",
    "LUNCHPICK_LLM_API_KEY": "test-key",
}

OPTIONAL_ENV = {
    "LUNCHPICK_BUDGET_TOTAL_MS": json.dumps(BUDGET_TOTAL_MS),
    "LUNCHPICK_BUDGET_LANDING_MS": json.dumps(BUDGET_LANDING_MS),
    "LUNCHPICK_STEP_RETRY_CONDITIONAL": json.dumps(["S-R11"]),
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """남은 환경변수와 실제 환경 파일이 시험에 새지 않게 함."""
    for name in list(os.environ):
        if name.startswith("LUNCHPICK_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    reset_settings_cache()


@pytest.fixture
def env_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {**REQUIRED_ENV, **OPTIONAL_ENV}.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def settings(env_ready: None) -> Settings:
    return load_settings()


# --- 05-guardrail 시험용 대역 -------------------------------------------------
# 규칙 원본은 실제 설정 파일을 그대로 읽음 — 시험용 사본을 따로 만들면 규칙이 두 벌이 됨.


@pytest.fixture
def rulebook():
    from common.guardrail.rules import load_rulebook

    return load_rulebook()


@pytest.fixture
def masker(rulebook):
    from common.guardrail.masking import Masker

    return Masker(rulebook)


@pytest.fixture
def sink():
    from common.observability.exporter import MemorySink

    return MemorySink()
