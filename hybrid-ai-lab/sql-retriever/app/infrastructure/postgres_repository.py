"""PostgreSQL 읽기 전용 고객 저장소 어댑터."""

from contextlib import contextmanager
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row

from ..application.ports import CustomerRepositoryPort


TABLES = (
    "member",
    "product",
    "product_annual_fee",
    "merchant",
    "card",
    "card_txn",
    "delinquency",
    "lab_metadata",
)


def _normalize(row: dict) -> dict:
    return {
        key: value.isoformat() if isinstance(value, (date, datetime)) else value
        for key, value in row.items()
    }


class PostgresRepository(CustomerRepositoryPort):
    def __init__(self, dsn: str, password: str = "") -> None:
        self.dsn = dsn
        self.password = password

    @contextmanager
    def connect(self):
        kwargs = {"row_factory": dict_row, "connect_timeout": 5}
        if self.password:
            kwargs["password"] = self.password
        try:
            with psycopg.connect(self.dsn, **kwargs) as connection:
                connection.execute("SET TRANSACTION READ ONLY")
                yield connection
        except psycopg.Error as error:
            raise RuntimeError("PostgreSQL 읽기 전용 조회 실패. 연결·권한·컨테이너 상태 확인 필요") from error

    def rows(self, sql: str, parameters: dict) -> list[dict]:
        with self.connect() as connection:
            return [_normalize(row) for row in connection.execute(sql, parameters).fetchall()]

    def member(self, member_id: str) -> dict | None:
        rows = self.rows(
            "SELECT member_id, segment_id, join_date, age_band "
            "FROM member WHERE member_id=%(member_id)s LIMIT 1",
            {"member_id": member_id},
        )
        return rows[0] if rows else None

    def schema(self) -> list[dict]:
        with self.connect() as connection:
            result = []
            column_sql = """
                SELECT ordinal_position, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %(table)s
                ORDER BY ordinal_position
            """
            for table in TABLES:
                count = connection.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()["count"]
                columns = connection.execute(column_sql, {"table": table}).fetchall()
                result.append({"table": table, "rows": count, "columns": columns})
            return result

