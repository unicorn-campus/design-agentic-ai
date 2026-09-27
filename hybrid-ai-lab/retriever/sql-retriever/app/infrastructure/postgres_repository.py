"""PostgreSQL 고객 현황 조회 어댑터."""

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from sqlglot import exp, parse_one

from app.domain.customer import (
    snapshot_warnings,
    usage_window,
    validate_member_id,
    validate_requested_date,
)
from .queries import (
    CARDS_SELECT,
    DELINQUENCY_SELECT,
    PROFILE_SELECT,
    SEARCH_METADATA_SELECT,
    USAGE_SELECT,
    guarded_query,
    scoped_query,
)


PUBLIC_TABLES = (
    "member",
    "product",
    "product_annual_fee",
    "merchant",
    "card",
    "card_txn",
    "delinquency",
    "lab_metadata",
)


def _normalize(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else str(value)
    return value


class PostgresRepository:
    """읽기 전용·반복 읽기 트랜잭션에서만 정형 데이터를 조회함."""

    def __init__(self, dsn: str, password: str = "", statement_timeout_ms: int = 5000) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("PostgreSQL 연결 설정이 필요합니다.")
        if not 100 <= statement_timeout_ms <= 60000:
            raise ValueError("SQL 제한 시간은 100~60000ms 범위여야 합니다.")
        self._dsn = dsn
        self._password = password
        self._statement_timeout_ms = statement_timeout_ms

    @contextmanager
    def _transaction(self) -> Iterator[Any]:
        kwargs: dict[str, Any] = {"row_factory": dict_row, "connect_timeout": 5}
        if self._password:
            kwargs["password"] = self._password
        try:
            with psycopg.connect(self._dsn, **kwargs) as connection:
                with connection.transaction():
                    connection.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                    )
                    connection.execute("SET LOCAL search_path TO pg_catalog, public")
                    connection.execute(
                        "SELECT set_config('statement_timeout', %s, true)",
                        (str(self._statement_timeout_ms),),
                    )
                    yield connection
        except psycopg.Error as error:
            raise RuntimeError(
                "PostgreSQL 읽기 전용 조회에 실패했습니다. 연결·권한·컨테이너 상태를 확인해 주세요."
            ) from error

    @staticmethod
    def _rows(connection: Any, sql: str, parameters: dict | None = None) -> list[dict]:
        rows = connection.execute(sql, parameters or {}).fetchall()
        return [_normalize(dict(row)) for row in rows]

    @staticmethod
    def _request_context(
        connection: Any,
        member_id: str,
        base_date: date,
    ) -> tuple[dict, date, date]:
        validate_member_id(member_id)
        if type(base_date) is not date:
            raise ValueError("기준일은 날짜여야 합니다.")
        metadata_rows = connection.execute(
            "SELECT key, value FROM public.lab_metadata "
            "WHERE key IN ('base_date', 'txn_period')"
        ).fetchall()
        metadata = {row["key"]: row["value"] for row in metadata_rows}
        if "base_date" not in metadata or "txn_period" not in metadata:
            raise RuntimeError("정형 데이터의 기준일 메타데이터를 확인할 수 없습니다.")
        try:
            data_base_date = date.fromisoformat(metadata["base_date"])
            period_match = re.fullmatch(
                r"\s*(\d{4}-\d{2})\s*~\s*(\d{4}-\d{2})\s*",
                metadata["txn_period"],
            )
            if period_match is None:
                raise ValueError
            coverage_start = date.fromisoformat(f"{period_match.group(1)}-01")
        except (TypeError, ValueError) as error:
            raise RuntimeError("정형 데이터의 기준일 메타데이터 형식이 올바르지 않습니다.") from error
        member = connection.execute(
            "SELECT member_id, join_date, age_band "
            "FROM public.member WHERE member_id = %(member_id)s LIMIT 1",
            {"member_id": member_id},
        ).fetchone()
        if member is None:
            raise ValueError("존재하지 않는 회원ID입니다.")
        validate_requested_date(base_date, data_base_date, member["join_date"], coverage_start)
        return dict(member), data_base_date, coverage_start

    def retrieve(self, member_id: str, base_date: date) -> dict:
        """UFR-EVID-010의 고객 현황을 근거와 기준시점까지 함께 반환함."""

        with self._transaction() as connection:
            member, data_base_date, coverage_start = self._request_context(
                connection, member_id, base_date
            )
            parameters = {
                "member_id": member_id,
                "base_date": base_date,
                "coverage_start": coverage_start,
            }
            profile_rows = self._rows(connection, scoped_query(PROFILE_SELECT), parameters)
            cards = self._rows(connection, scoped_query(CARDS_SELECT), parameters)
            usage = self._rows(connection, scoped_query(USAGE_SELECT), parameters)
            delinquency_rows = self._rows(connection, scoped_query(DELINQUENCY_SELECT), parameters)

        delinquency = delinquency_rows[0] if delinquency_rows else None
        product_future = any(not row["is_product_effective_on_base_date"] for row in cards)
        warnings = snapshot_warnings(base_date, product_future)
        requested_window_start, _ = usage_window(base_date)
        if coverage_start > requested_window_start:
            warnings.append(
                "최근 6개월 전체를 채울 거래 자료가 없어 데이터 제공 시작월부터만 반환합니다."
            )
        if delinquency is None:
            warnings.append("기준일까지 이용 가능한 연체 자료가 없어 연체액은 확인 필요 상태입니다.")

        approved_amount = sum(row["approved_amount"] for row in usage)
        overdue_amount = delinquency["overdue_amount"] if delinquency else None
        delinquency_basis = delinquency["as_of_date"] if delinquency else None
        sources = [
            {
                "name": "customer_profile",
                "tables": ["public.member"],
                "actual_basis_date": data_base_date.isoformat(),
            },
            {
                "name": "customer_cards",
                "tables": ["public.card", "public.product", "public.product_annual_fee"],
                "actual_basis_date": data_base_date.isoformat(),
            },
            {
                "name": "monthly_usage",
                "tables": ["public.card_txn", "public.card"],
                "actual_basis_date": base_date.isoformat(),
                "coverage_start": coverage_start.isoformat(),
                "filter": "approval_code=APPROVED, 최근 6개월, txn_date<=requested_base_date",
            },
            {
                "name": "customer_delinquency",
                "tables": ["public.delinquency"],
                "actual_basis_date": delinquency_basis,
                "status": "available" if delinquency else "unknown",
            },
        ]
        event = {
            "event_id": "E-3",
            "event_name": "고객 현황 확보됨",
            "card_ids": [row["card_id"] for row in cards],
            "product_ids": list(dict.fromkeys(row["product_id"] for row in cards)),
            "approved_amount": approved_amount,
            "approved_amount_period": {
                "start": min((row["period_start"] for row in usage), default=None),
                "end": base_date.isoformat(),
            },
            "overdue_amount": overdue_amount,
            "basis_date": base_date.isoformat(),
            "delinquency_basis_date": delinquency_basis,
            "sources": sources,
        }
        return {
            "member_id": member_id,
            "requested_base_date": base_date.isoformat(),
            "data_base_date": data_base_date.isoformat(),
            "customer_profile": profile_rows[0] if profile_rows else _normalize(member),
            "cards": cards,
            "monthly_usage": usage,
            "delinquency": delinquency,
            "sources": sources,
            "warnings": warnings,
            "event": event,
        }

    def search(self, member_id: str, base_date: date, validated_sql: str) -> dict:
        """검증된 논리 SQL을 회원·기준일 CTE 안에서 다시 검사해 실행함."""

        if not isinstance(validated_sql, str) or not validated_sql.strip():
            raise ValueError("실행할 SQL이 필요합니다.")
        # 서비스 계층을 우회한 직접 호출에서도 같은 검사 적용
        from .sql_guard import validate_sql

        checked_sql = validate_sql(validated_sql)
        with self._transaction() as connection:
            _, data_base_date, coverage_start = self._request_context(
                connection, member_id, base_date
            )
            parameters = {
                "member_id": member_id,
                "base_date": base_date,
                "coverage_start": coverage_start,
            }
            rows = self._rows(connection, guarded_query(checked_sql), parameters)
            metadata = self._rows(
                connection,
                scoped_query(SEARCH_METADATA_SELECT),
                parameters,
            )[0]
        if len(rows) > 100:
            raise ValueError("조회 결과가 최대 100행을 초과했습니다.")
        referenced_models = {
            table.name.lower()
            for table in parse_one(checked_sql, read="postgres").find_all(exp.Table)
        }
        source_by_model = {
            "customer_profile": {
                "name": "customer_profile",
                "tables": ["public.member"],
                "actual_basis_date": data_base_date.isoformat(),
            },
            "customer_cards": {
                "name": "customer_cards",
                "tables": ["public.card", "public.product", "public.product_annual_fee"],
                "actual_basis_date": data_base_date.isoformat(),
            },
            "monthly_usage": {
                "name": "monthly_usage",
                "tables": ["public.card_txn", "public.card"],
                "actual_basis_date": base_date.isoformat(),
                "coverage_start": coverage_start.isoformat(),
                "filter": "approval_code=APPROVED, 최근 6개월, txn_date<=requested_base_date",
            },
            "customer_delinquency": {
                "name": "customer_delinquency",
                "tables": ["public.delinquency"],
                "actual_basis_date": metadata["delinquency_as_of_date"],
                "status": "available" if metadata["delinquency_as_of_date"] else "unknown",
            },
        }
        warnings = snapshot_warnings(
            base_date,
            "customer_cards" in referenced_models and metadata["has_future_product"],
        )
        if "monthly_usage" in referenced_models and coverage_start > usage_window(base_date)[0]:
            warnings.append(
                "최근 6개월 전체를 채울 거래 자료가 없어 데이터 제공 시작월부터만 반환합니다."
            )
        if (
            "customer_delinquency" in referenced_models
            and metadata["delinquency_as_of_date"] is None
        ):
            warnings.append("기준일까지 이용 가능한 연체 자료가 없어 연체액은 확인 필요 상태입니다.")
        return {
            "rows": rows,
            "row_count": len(rows),
            "sql": checked_sql,
            "member_id": member_id,
            "requested_base_date": base_date.isoformat(),
            "data_base_date": data_base_date.isoformat(),
            "sources": [
                source_by_model[name]
                for name in (
                    "customer_profile",
                    "customer_cards",
                    "monthly_usage",
                    "customer_delinquency",
                )
                if name in referenced_models
            ],
            "warnings": warnings,
        }

    def schema(self) -> list[dict]:
        """private를 제외한 public 허용 목록의 컬럼만 반환함."""

        with self._transaction() as connection:
            result = []
            for table in PUBLIC_TABLES:
                columns = self._rows(
                    connection,
                    "SELECT ordinal_position, column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = %(table)s "
                    "ORDER BY ordinal_position",
                    {"table": table},
                )
                count = connection.execute(
                    f'SELECT count(*) AS row_count FROM public."{table}"'
                ).fetchone()["row_count"]
                result.append({"table": table, "row_count": count, "columns": columns})
        return result
