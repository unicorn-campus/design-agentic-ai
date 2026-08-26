from pathlib import Path

import pytest
from pydantic import ValidationError

from help_desk_runtime.settings import RuntimeSettings


ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def test_missing_required_settings_fail_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(RuntimeSettings.model_fields):
        monkeypatch.delenv(f"HELP_DESK_{name.upper()}", raising=False)
    with pytest.raises(ValidationError):
        RuntimeSettings(_env_file=None)


def test_design_values_load_from_environment_example(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HELP_DESK_LLM_PROVIDER", "provider-from-runtime")
    monkeypatch.setenv("HELP_DESK_LLM_MODEL", "model-from-runtime")
    monkeypatch.setenv("HELP_DESK_LLM_API_KEY", "key-from-runtime")
    monkeypatch.setenv("HELP_DESK_CHECKPOINT_URI", "checkpoint-from-runtime")
    monkeypatch.setenv("HELP_DESK_CHECKPOINT_ENCRYPTION_KEY", "encryption-from-runtime")
    monkeypatch.setenv("HELP_DESK_MASKING_SALT", "masking-salt-from-runtime")

    settings = RuntimeSettings(_env_file=ENV_EXAMPLE)

    assert settings.stage_budgets["S-R9"].timeout_ms == 600000
    assert settings.stage_budgets["S-E6"].retry_count == 2
    assert settings.checkpoint_w2_retention_ms == 3600000
    assert settings.w3_total_budget_ms == 60000
