"""설정 로더 시험. 반드시 넣을 시험 3번이 여기 있음."""

from __future__ import annotations

import json

import pytest

from common.config import (
    CheckpointBackend,
    CheckpointFailurePolicy,
    Settings,
    SettingsMissing,
    load_settings,
)

from .conftest import OPTIONAL_ENV, REQUIRED_ENV


def test_missing_required_setting_fails_at_load_time() -> None:
    """시험 3 — 필수 설정이 없으면 뜨는 시점에 실패함."""
    with pytest.raises(SettingsMissing):
        load_settings()


@pytest.mark.parametrize("dropped", sorted(REQUIRED_ENV))
def test_each_required_setting_is_really_required(
    monkeypatch: pytest.MonkeyPatch, dropped: str
) -> None:
    for name, value in {**REQUIRED_ENV, **OPTIONAL_ENV}.items():
        if name != dropped:
            monkeypatch.setenv(name, value)
    with pytest.raises(SettingsMissing):
        load_settings()


@pytest.mark.parametrize("dropped", sorted(OPTIONAL_ENV))
def test_optional_setting_absence_does_not_block_startup(
    monkeypatch: pytest.MonkeyPatch, dropped: str
) -> None:
    for name, value in {**REQUIRED_ENV, **OPTIONAL_ENV}.items():
        if name != dropped:
            monkeypatch.setenv(name, value)
    assert load_settings() is not None


def test_loads_when_every_required_setting_is_present(settings: Settings) -> None:
    assert settings.timeout_ms("S-R11") == 1800
    assert settings.retry_count("S-R11") == 1
    assert settings.is_retry_conditional("S-R11") is True
    assert settings.is_retry_conditional("S-R4") is False


def test_optional_settings_default_to_unset(settings: Settings) -> None:
    assert settings.checkpoint_backend is CheckpointBackend.MEMORY
    assert settings.checkpoint_failure_policy is CheckpointFailurePolicy.FAIL_FAST
    assert settings.checkpoint_retention_days is None
    assert settings.cost_limit_krw_per_request is None
    assert settings.embedding_model is None


def test_unknown_step_raises_instead_of_guessing(settings: Settings) -> None:
    with pytest.raises(SettingsMissing):
        settings.timeout_ms("S-없는단계")
    with pytest.raises(SettingsMissing):
        settings.retry_count("S-없는단계")


def test_entry_deadline_span_subtracts_landing_path(settings: Settings) -> None:
    assert settings.entry_deadline_span_ms("S-R") == 3000 - 150


def test_postgres_backend_requires_db_url(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_BACKEND", "postgres")
    with pytest.raises(SettingsMissing):
        load_settings()


def test_postgres_backend_loads_with_db_url(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_BACKEND", "postgres")
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_DB_URL", "postgresql://localhost/test")
    assert load_settings().checkpoint_backend is CheckpointBackend.POSTGRES


def test_development_memory_fallback_must_be_selected_explicitly(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_BACKEND", "postgres")
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv(
        "LUNCHPICK_CHECKPOINT_FAILURE_POLICY",
        "memory_fallback_for_development",
    )
    assert (
        load_settings().checkpoint_failure_policy
        is CheckpointFailurePolicy.MEMORY_FALLBACK_FOR_DEVELOPMENT
    )


def test_missing_loop_max_iter_raises(settings: Settings) -> None:
    with pytest.raises(SettingsMissing):
        settings.max_iter("L-1")


def test_loop_max_iter_reads_from_env(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    monkeypatch.setenv("LUNCHPICK_LOOP_MAX_ITER", json.dumps({"L-1": 2}))
    assert load_settings().max_iter("L-1") == 2
