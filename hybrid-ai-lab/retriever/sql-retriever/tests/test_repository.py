from datetime import date
from decimal import Decimal
import os

import pytest

from app.infrastructure.postgres_repository import PostgresRepository, _normalize
from app.infrastructure.queries import (
    LOGICAL_CTE_SQL,
    guarded_query,
)


def test_logical_ctes_bind_scope_and_only_read_public_tables():
    assert "%(member_id)s" in LOGICAL_CTE_SQL
    assert "%(base_date)s" in LOGICAL_CTE_SQL
    assert "%(coverage_start)s" in LOGICAL_CTE_SQL
    assert "private." not in LOGICAL_CTE_SQL
    assert "public.member" in LOGICAL_CTE_SQL
    assert "public.card_txn" in LOGICAL_CTE_SQL
    assert "approval_code = 'APPROVED'" in LOGICAL_CTE_SQL
    assert "1 month - 1 day" in LOGICAL_CTE_SQL
    assert "c.status = 'ACTIVE'" not in LOGICAL_CTE_SQL


def test_guarded_query_escapes_percent_only_in_user_sql():
    query = guarded_query(
        "SELECT card_ref FROM customer_cards WHERE product_name LIKE '%생활%' LIMIT 100"
    )
    assert "%(member_id)s" in query
    assert "LIKE '%%생활%%'" in query
    assert query.rstrip().endswith("LIMIT 101")


def test_repository_constructor_rejects_unsafe_timeout_and_empty_dsn():
    with pytest.raises(ValueError):
        PostgresRepository("")
    with pytest.raises(ValueError):
        PostgresRepository("host=localhost", statement_timeout_ms=99)


def test_sql_numeric_values_preserve_precision_and_integer_amount_type():
    assert _normalize({"sum": Decimal("8262000"), "average": Decimal("123.456789")}) == {
        "sum": 8262000, "average": "123.456789"
    }


@pytest.mark.skipif(
    not os.environ.get("SQL_RETRIEVER_TEST_DSN"),
    reason="SQL_RETRIEVER_TEST_DSN을 지정한 읽기 전용 PostgreSQL 통합 시험만 실행함",
)
def test_live_repository_preserves_dates_sources_and_e3_contract():
    repository = PostgresRepository(
        os.environ["SQL_RETRIEVER_TEST_DSN"],
        os.environ.get("SQL_RETRIEVER_TEST_PASSWORD", ""),
    )
    result = repository.retrieve("M-1042", date(2026, 8, 15))

    assert result["requested_base_date"] == "2026-08-15"
    assert result["data_base_date"] == "2026-08-31"
    assert result["event"]["event_id"] == "E-3"
    assert all(card["card_ref"].startswith("CARD_") for card in result["cards"])
    assert all(item["period_end"] <= "2026-08-15" for item in result["monthly_usage"])
    assert result["delinquency"]["as_of_date"] == "2026-07-31"
    assert any(source["name"] == "monthly_usage" for source in result["sources"])


@pytest.mark.skipif(
    not os.environ.get("SQL_RETRIEVER_TEST_DSN"),
    reason="SQL_RETRIEVER_TEST_DSN을 지정한 읽기 전용 PostgreSQL 통합 시험만 실행함",
)
def test_live_search_cannot_cross_member_scope():
    repository = PostgresRepository(
        os.environ["SQL_RETRIEVER_TEST_DSN"],
        os.environ.get("SQL_RETRIEVER_TEST_PASSWORD", ""),
    )
    result = repository.search(
        "M-1042",
        date(2026, 8, 31),
        "SELECT card_ref, product_id FROM customer_cards ORDER BY card_ref LIMIT 100",
    )
    assert result["row_count"] == 2
    assert {row["card_ref"] for row in result["rows"]} == {"CARD_001", "CARD_002"}


@pytest.mark.skipif(
    not os.environ.get("SQL_RETRIEVER_TEST_DSN"),
    reason="SQL_RETRIEVER_TEST_DSN을 지정한 읽기 전용 PostgreSQL 통합 시험만 실행함",
)
def test_live_search_keeps_future_product_warning_when_projection_hides_flag():
    repository = PostgresRepository(
        os.environ["SQL_RETRIEVER_TEST_DSN"],
        os.environ.get("SQL_RETRIEVER_TEST_PASSWORD", ""),
    )
    result = repository.search(
        "M-1042",
        date(2026, 8, 31),
        "SELECT annual_fee FROM customer_cards ORDER BY annual_fee LIMIT 100",
    )
    assert any("기준일 이후 시행" in warning for warning in result["warnings"])
    assert result["sources"] == [
        {
            "name": "customer_cards",
            "tables": ["public.card", "public.product", "public.product_annual_fee"],
            "actual_basis_date": "2026-08-31",
        }
    ]


@pytest.mark.skipif(
    not os.environ.get("SQL_RETRIEVER_TEST_DSN"),
    reason="SQL_RETRIEVER_TEST_DSN을 지정한 읽기 전용 PostgreSQL 통합 시험만 실행함",
)
def test_live_coverage_start_truncates_months_and_older_date_is_rejected():
    repository = PostgresRepository(
        os.environ["SQL_RETRIEVER_TEST_DSN"],
        os.environ.get("SQL_RETRIEVER_TEST_PASSWORD", ""),
    )
    result = repository.retrieve("M-1042", date(2025, 8, 15))
    assert {row["month"] for row in result["monthly_usage"]} == {"2025-08"}
    assert any("데이터 제공 시작월" in warning for warning in result["warnings"])
    with pytest.raises(ValueError, match="거래 데이터 제공 기간 이전"):
        repository.retrieve("M-1042", date(2025, 7, 31))
