from __future__ import annotations

import pytest

from help_desk_dataset.source import PATH_SPECS, validate_read_statement
from help_desk_knowledge.structured import (
    BLOCKED_COLUMNS,
    NL2SQLGenerator,
    validate_knowledge_statement,
)


@pytest.mark.parametrize("qualified", sorted(BLOCKED_COLUMNS))
def test_every_blocked_column_is_rejected(qualified: str) -> None:
    table, column = qualified.split(".", 1)
    matching = [spec for spec in PATH_SPECS.values() if spec.table == table]
    if not matching:
        with pytest.raises(ValueError, match="허용 테이블"):
            validate_read_statement(
                f"SELECT {column} FROM {table}",
                PATH_SPECS["S-R4"],
                10,
            )
        return
    with pytest.raises(ValueError, match="허용 열"):
        validate_read_statement(f"SELECT {column} FROM {table}", matching[0], 10)


def test_unlisted_column_is_rejected() -> None:
    with pytest.raises(ValueError, match="허용 열"):
        validate_read_statement(
            "SELECT internal_note FROM masked_transaction_analysis_v",
            PATH_SPECS["S-R4"],
            10,
        )


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO masked_transaction_analysis_v(masked_customer_id) VALUES ('x')",
        "UPDATE masked_transaction_analysis_v SET transaction_status = 'x'",
        "DELETE FROM masked_transaction_analysis_v",
        "SELECT masked_customer_id FROM masked_transaction_analysis_v; SELECT 1",
    ],
)
def test_write_and_multiple_statements_are_rejected(statement: str) -> None:
    with pytest.raises(ValueError, match="단일 SELECT"):
        validate_read_statement(statement, PATH_SPECS["S-R4"], 10)


def test_missing_limit_is_added() -> None:
    statement = validate_read_statement(
        "SELECT masked_customer_id FROM masked_transaction_analysis_v",
        PATH_SPECS["S-R4"],
        7,
    )
    assert statement.endswith("LIMIT 7")


def test_unsafe_function_and_comment_are_rejected() -> None:
    with pytest.raises(ValueError, match="함수"):
        validate_knowledge_statement(
            "SELECT pg_sleep(1), masked_customer_id FROM masked_transaction_analysis_v",
            "S-R4",
            10,
        )
    with pytest.raises(ValueError, match="주석"):
        validate_knowledge_statement(
            "SELECT masked_customer_id FROM masked_transaction_analysis_v -- hidden",
            "S-R4",
            10,
        )


class _Message:
    content = "SELECT masked_customer_id FROM masked_transaction_analysis_v"


class _Model:
    def __init__(self) -> None:
        self.prompt = ""

    def invoke(self, prompt: str) -> _Message:
        self.prompt = prompt
        return _Message()


class _Adapter:
    def __init__(self) -> None:
        self.model = _Model()

    def create(self) -> _Model:
        return self.model


def test_model_schema_contains_only_allowed_columns() -> None:
    adapter = _Adapter()
    generated = NL2SQLGenerator(adapter).generate("S-R4", "최근 거절 사유", 10)
    assert "masked_customer_id" in adapter.model.prompt
    assert "full_card_number" not in adapter.model.prompt
    assert generated.statement.endswith("LIMIT 10")


def test_deterministic_filter_is_not_created_without_design_field() -> None:
    from pathlib import Path

    package = Path(__file__).parents[1] / "help_desk_knowledge"
    assert not (package / "deterministic_filter.py").exists()
