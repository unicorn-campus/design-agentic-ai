from datetime import date
from decimal import Decimal
import os
from pathlib import Path

import psycopg
import pytest

from app.infrastructure.postgres_repository import PostgresRepository, _normalize
from app.infrastructure.queries import (
    CARDS_SELECT,
    DELINQUENCY_SELECT,
    MEMBER_SELECT,
    PROFILE_SELECT,
    SEARCH_METADATA_SELECT,
    USAGE_SELECT,
    guarded_query,
)


RLS_DDL = (
    Path(__file__).resolve().parents[3] / "rdb" / "init" / "04_views_rls.sql"
).read_text(encoding="utf-8")


def test_query_module_reads_only_logical_views_and_adds_no_member_condition():
    statements = (
        PROFILE_SELECT,
        CARDS_SELECT,
        USAGE_SELECT,
        DELINQUENCY_SELECT,
        SEARCH_METADATA_SELECT,
        MEMBER_SELECT,
    )
    for statement in statements:
        # 회원 격리는 RLS가 담당함. 같은 조건을 SQL에도 두면 한쪽만 고쳤을 때 어긋남.
        assert "member_id =" not in statement
        assert "%(member_id)s" not in statement
        # 원본 테이블과 재식별 열쇠에는 손대지 않음.
        assert "public.card" not in statement
        assert "public.member" not in statement
        assert "private." not in statement
    assert "app.customer_profile" in PROFILE_SELECT
    assert "app.monthly_usage" in USAGE_SELECT
    assert "app.customer_delinquency" in DELINQUENCY_SELECT
    # 원본 card_id가 필요한 고정 조회만 NL2SQL에 열지 않은 스키마를 씀.
    assert "app_internal.customer_cards_full" in CARDS_SELECT
    assert "app_internal.member_basic" in MEMBER_SELECT


def test_rls_ddl_scopes_members_and_keeps_existing_lab_account_working():
    for table in ("public.member", "public.card", "public.card_txn", "public.delinquency"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in RLS_DDL
    # 값이 없을 때 0행이 되도록 빈 문자열을 NULL과 같게 취급함(정책 4개).
    assert RLS_DDL.count("NULLIF(current_setting('app.member_id', true), '')") == 4
    # 회원ID는 RLS만 씀. 요청 범위 뷰는 시간 범위만 노출함.
    scope_view = RLS_DDL.split("CREATE VIEW app_internal.request_scope")[1].split(";")[0]
    assert "app.member_id" not in scope_view
    assert "app.base_date" in scope_view and "app.coverage_start" in scope_view
    # RLS를 켜면 정책 없는 역할은 0행이 됨. 기존 실습 계정이 조용히 깨지지 않게 함.
    assert RLS_DDL.count("TO lab_user") == 4
    # 뷰는 필터를 먼저 평가해야 조작된 조건으로 필터 이전 행이 새지 않음.
    assert RLS_DDL.count("WITH (security_barrier = true)") == 8
    # 서비스 계정에는 논리 뷰와 메타데이터만 주고 원본 테이블 권한은 주지 않음.
    statements = [
        " ".join(line for line in chunk.splitlines() if not line.strip().startswith("--"))
        for chunk in RLS_DDL.split(";")
    ]
    service_grants = [
        statement
        for statement in statements
        if "GRANT SELECT" in statement and "TO sql_retriever_user" in statement
    ]
    assert len(service_grants) == 3
    for statement in service_grants:
        assert "public.member" not in statement
        assert "public.card" not in statement
        assert "public.delinquency" not in statement


def test_guarded_query_caps_rows_without_adding_scope_or_escaping():
    original = "SELECT card_ref FROM customer_cards WHERE product_name LIKE '%생활%' LIMIT 100"
    query = guarded_query(original)
    # 바인딩 파라미터가 없으므로 사용자 SQL의 %를 더 이상 이스케이프하지 않음.
    assert "LIKE '%생활%'" in query
    assert "%%" not in query
    assert "%(member_id)s" not in query
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


def _live_connection():
    """앱 계층을 거치지 않고 서비스 계정으로 직접 접속함."""

    password = os.environ.get("SQL_RETRIEVER_TEST_PASSWORD", "")
    options = {"password": password} if password else {}
    return psycopg.connect(os.environ["SQL_RETRIEVER_TEST_DSN"], connect_timeout=5, **options)


@pytest.mark.skipif(
    not os.environ.get("SQL_RETRIEVER_TEST_DSN"),
    reason="SQL_RETRIEVER_TEST_DSN을 지정한 읽기 전용 PostgreSQL 통합 시험만 실행함",
)
def test_live_logical_views_are_empty_without_session_scope():
    """요청 범위를 열지 않으면 DB가 스스로 0행을 돌려주는지 확인함(기본 거부)."""

    with _live_connection() as connection:
        for view in (
            "app.customer_profile",
            "app.customer_cards",
            "app.monthly_usage",
            "app.customer_delinquency",
        ):
            assert connection.execute(f"SELECT count(*) FROM {view}").fetchone()[0] == 0


@pytest.mark.skipif(
    not os.environ.get("SQL_RETRIEVER_TEST_DSN"),
    reason="SQL_RETRIEVER_TEST_DSN을 지정한 읽기 전용 PostgreSQL 통합 시험만 실행함",
)
def test_live_service_account_cannot_reach_source_tables():
    """앱 코드를 우회해도 원본 테이블은 DB가 막는지 확인함."""

    with _live_connection() as connection:
        for table in ("public.card", "public.member", "public.card_txn", "public.delinquency"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                connection.execute(f"SELECT count(*) FROM {table}")
            connection.rollback()


@pytest.mark.skipif(
    not os.environ.get("SQL_RETRIEVER_TEST_DSN"),
    reason="SQL_RETRIEVER_TEST_DSN을 지정한 읽기 전용 PostgreSQL 통합 시험만 실행함",
)
def test_live_search_of_one_member_never_returns_another_members_cards():
    """RLS가 회원 경계를 지키는지 두 회원의 결과를 맞대어 확인함."""

    repository = PostgresRepository(
        os.environ["SQL_RETRIEVER_TEST_DSN"],
        os.environ.get("SQL_RETRIEVER_TEST_PASSWORD", ""),
    )
    first = repository.retrieve("M-5015", date(2026, 8, 31))
    second = repository.retrieve("M-5094", date(2026, 8, 31))

    first_cards = {card["card_id"] for card in first["cards"]}
    second_cards = {card["card_id"] for card in second["cards"]}
    assert first_cards and second_cards
    assert first_cards.isdisjoint(second_cards)
    assert all(card_id.startswith("C-5015-") for card_id in first_cards)
    assert all(card_id.startswith("C-5094-") for card_id in second_cards)
