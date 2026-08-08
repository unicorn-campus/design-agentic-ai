"""시험용 설정 대역. 여기 숫자는 **시험 고정값**이며 소스 코드에는 없음.

시간 상한·재시도 값은 ③ 4절 표에서 그대로 옮긴 것임 —
`S-R6` 800/1회 · `S-R7` 1,000/1회 · `S-R8` 600/0회 · `S-R11` 1,800/조건부 1회 ·
`S-B5` 3,000/1회 · `S-S9` `[확인필요]`(자동 0회) · `S-C10` `[확인필요]`(1회 · 백오프 1s).
`[확인필요]`인 두 단계의 **시간 상한만** 시험 고정값을 넣었고 재시도 횟수는 ③ 값을 씀.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from common.config import Settings, load_settings, reset_settings_cache
from toolkit.settings import ToolSettings, load_tool_settings, reset_tool_settings_cache

# ③ 4절 「타임아웃(상한)」 — `S-S9` · `S-C10`은 ③이 `[확인필요]`로 남긴 자리라 시험 고정값임
STEP_TIMEOUT_MS = {
    "S-R6": 800,
    "S-R7": 1000,
    "S-R8": 600,
    "S-R11": 1800,
    "S-B5": 3000,
    "S-S9": 2000,
    "S-C10": 2000,
}
# ③ 4절 「재시도」 — 값을 바꾸지 않고 그대로 옮김
STEP_RETRY_COUNT = {
    "S-R6": 1,
    "S-R7": 1,
    "S-R8": 0,
    "S-R11": 1,
    "S-B5": 1,
    "S-S9": 0,
    "S-C10": 1,
}
# ③ 4-6절 `S-C10` 백오프 = 1s
STEP_BACKOFF_MS = {"S-C10": 1000}

CONNECTOR_MODE = {
    "C-2": "live",
    "C-3": "live",
    "C-4": "live",
    "C-7": "live",
    "C-8": "mock",
    "C-9": "mock",
    "C-12": "mock",
}

# 시험용 가짜 주소 · 헤더 이름. 실제 제공자 주소가 아니며 시험에서만 씀.
_ENDPOINT_TEMPLATE = {
    "base_url": "http://connector.test",
    "path": "/query",
    "method": "POST",
    "auth_header": "X-Test-Key",
}
CONNECTOR_ENDPOINT = {
    "C-4": {**_ENDPOINT_TEMPLATE, "path": "/places/nearby", "method": "GET"},
    "C-7": {**_ENDPOINT_TEMPLATE, "path": "/weather/current", "method": "GET"},
    "C-8": {**_ENDPOINT_TEMPLATE, "path": "/business-status"},
    "C-9": {
        "base_url": "http://pg.test",
        "path": "/billing/subscriptions",
        "method": "POST",
        "auth_header": "X-Merchant-Id",
        "secondary_auth_header": "X-Merchant-Secret",
        "idempotency_header": "X-Idempotency-Key",
    },
    "C-12": {
        "base_url": "http://pg.test",
        "path": "/billing/subscriptions/stop",
        "method": "POST",
        "auth_header": "X-Merchant-Id",
        "secondary_auth_header": "X-Merchant-Secret",
        "idempotency_header": "X-Idempotency-Key",
    },
}

# 시험용 자리표시 자격. 실제 열쇠가 아니며 로그 유출 시험의 검색 대상으로도 씀.
SECRET_PLACEHOLDERS = {
    "LUNCHPICK_MAP_API_KEY": "map-secret-value-for-test",
    "LUNCHPICK_WEATHER_API_KEY": "weather-secret-value-for-test",
    "LUNCHPICK_MFDS_API_KEY": "mfds-secret-value-for-test",
    "LUNCHPICK_PG_MERCHANT_ID": "pg-merchant-value-for-test",
    "LUNCHPICK_PG_API_SECRET": "pg-secret-value-for-test",
}

RUNTIME_ENV = {
    "LUNCHPICK_STEP_TIMEOUT_MS": json.dumps(STEP_TIMEOUT_MS),
    "LUNCHPICK_STEP_RETRY_COUNT": json.dumps(STEP_RETRY_COUNT),
    "LUNCHPICK_STEP_BACKOFF_MS": json.dumps(STEP_BACKOFF_MS),
    "LUNCHPICK_STEP_RETRY_CONDITIONAL": json.dumps(["S-R11"]),
    "LUNCHPICK_LLM_PROVIDER": "anthropic",
    "LUNCHPICK_LLM_MODEL": "test-model-id",
    "LUNCHPICK_LLM_API_KEY": "llm-secret-value-for-test",
}

TOOL_ENV = {
    "LUNCHPICK_CONNECTOR_MODE": json.dumps(CONNECTOR_MODE),
    "LUNCHPICK_CONNECTOR_ENDPOINT": json.dumps(CONNECTOR_ENDPOINT),
    "LUNCHPICK_IDEMPOTENCY_TTL_HOURS": "24",
    **SECRET_PLACEHOLDERS,
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in list(os.environ):
        if name.startswith("LUNCHPICK_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    reset_settings_cache()
    reset_tool_settings_cache()


@pytest.fixture
def env_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {**RUNTIME_ENV, **TOOL_ENV}.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def runtime_settings(env_ready: None) -> Settings:
    return load_settings()


@pytest.fixture
def tool_settings(env_ready: None) -> ToolSettings:
    return load_tool_settings()


def live_mode(**overrides: str) -> dict[str, Any]:
    """대역으로 적힌 커넥터를 시험에서만 실물 경로로 돌려 볼 때 씀."""
    return {**CONNECTOR_MODE, **overrides}
