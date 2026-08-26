from pathlib import Path

import httpx
import pytest

from help_desk_dataset.source import AnalyticsSource, PATH_SPECS, validate_read_statement
from help_desk_runtime.settings import RuntimeSettings


SOURCE_FILE = Path(__file__).resolve().parents[1] / "help_desk_dataset" / "source.py"
COMMON_ENV = Path(__file__).resolve().parents[3] / "common" / ".env.example"


def _settings(**overrides: object) -> RuntimeSettings:
    values = {
        "analytics_base_url": "https://analytics-mock.helpdesk.test",
        "analytics_timeout_seconds": 1.0,
        "dataset_s_r4_max_rows": 100,
        "dataset_s_b2_max_rows": 10_000,
        "dataset_s_b4_max_rows": 100,
    }
    values.update(overrides)
    return RuntimeSettings.model_construct(**values)


def test_dataset_settings_load_through_common_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HELP_DESK_LLM_PROVIDER", "local")
    monkeypatch.setenv("HELP_DESK_LLM_MODEL", "unused")
    monkeypatch.setenv("HELP_DESK_LLM_API_KEY", "unused")
    monkeypatch.setenv("HELP_DESK_CHECKPOINT_URI", "unused")
    monkeypatch.setenv("HELP_DESK_CHECKPOINT_ENCRYPTION_KEY", "unused")
    monkeypatch.setenv("HELP_DESK_MASKING_SALT", "test-only-salt")

    settings = RuntimeSettings(_env_file=COMMON_ENV)

    assert settings.dataset_s_r4_max_rows == 100
    assert settings.dataset_s_b2_seed_rows == 10_000
    assert settings.dataset_seed == 20260825


def test_access_layer_contains_no_write_statement() -> None:
    source = SOURCE_FILE.read_text(encoding="utf-8").upper()
    blocked = ("IN" + "SERT", "UP" + "DATE", "DE" + "LETE")
    assert all(token not in source for token in blocked)


def test_three_design_paths_have_three_read_functions() -> None:
    assert set(PATH_SPECS) == {"S-R4", "S-B2", "S-B4"}
    assert all(hasattr(AnalyticsSource, f"read_{stage.lower().replace('-', '_')}") for stage in PATH_SPECS)


def test_requested_rows_are_clamped_to_configured_limit() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed.update(__import__("json").loads(request.content))
        return httpx.Response(200, json={"rows": [{"masked_customer_id": "SYNTHETIC:C000001"}] * 150})

    client = httpx.Client(
        base_url="https://analytics-mock.helpdesk.test",
        transport=httpx.MockTransport(handler),
    )
    source = AnalyticsSource(_settings(), client)
    rows = source.read_s_r4(
        "SELECT masked_customer_id FROM masked_transaction_analysis_v",
        {},
        requested_limit=1_000,
    )

    assert len(rows) == 100
    assert observed["max_rows"] == 100
    assert str(observed["statement"]).endswith("LIMIT 100")


def test_response_with_forbidden_column_is_rejected() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rows": [{"full_card_number": "blocked"}]})

    client = httpx.Client(
        base_url="https://analytics-mock.helpdesk.test",
        transport=httpx.MockTransport(handler),
    )
    source = AnalyticsSource(_settings(), client)

    with pytest.raises(ValueError):
        source.read_s_r4(
            "SELECT masked_customer_id FROM masked_transaction_analysis_v",
            {},
            requested_limit=1,
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE masked_transaction_analysis_v SET transaction_status = '정상'",
        "DELETE FROM masked_transaction_analysis_v",
        "SELECT * FROM masked_transaction_analysis_v",
        "SELECT full_card_number FROM masked_transaction_analysis_v",
    ],
)
def test_non_read_or_forbidden_column_statement_is_rejected(statement: str) -> None:
    with pytest.raises(ValueError):
        validate_read_statement(statement, PATH_SPECS["S-R4"], 100)
