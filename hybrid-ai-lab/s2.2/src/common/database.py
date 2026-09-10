"""완성 제공: PostgreSQL 읽기 전용 연결과 결과 변환."""
from contextlib import contextmanager
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row

TABLES = (
    'member',
    'product',
    'product_annual_fee',
    'merchant',
    'card',
    'card_txn',
    'delinquency',
    'lab_metadata',
)


def require_complete(sql, filename):
    if '___' in sql:
        raise ValueError(f'{filename}: SQL 빈칸을 먼저 작성해 주세요.')


def fill_months(rows, base_date):
    """완성 제공: 거래가 없는 월을 0원으로 보충함."""
    end = date.fromisoformat(base_date)
    index = end.year * 12 + end.month - 1
    amounts = {row['month']: row['total_amount'] for row in rows}
    months = [f'{i // 12:04d}-{i % 12 + 1:02d}' for i in range(index - 5, index + 1)]
    return [{'month': month, 'total_amount': amounts.get(month, 0)} for month in months]


def _normalize(row: dict) -> dict:
    """PostgreSQL 날짜 값을 기존 출력 계약인 ISO 문자열로 변환함."""
    return {
        key: value.isoformat() if isinstance(value, (date, datetime)) else value
        for key, value in row.items()
    }


class PostgresRepository:
    def __init__(self, dsn: str, password: str = ''):
        self.dsn = dsn
        self.password = password

    @contextmanager
    def connect(self):
        kwargs = {'row_factory': dict_row, 'connect_timeout': 5}
        if self.password:
            kwargs['password'] = self.password
        with psycopg.connect(self.dsn, **kwargs) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            yield connection

    def rows(self, sql: str, parameters: dict) -> list[dict]:
        with self.connect() as connection:
            return [_normalize(row) for row in connection.execute(sql, parameters).fetchall()]

    def member(self, member_id: str) -> dict | None:
        rows = self.rows('SELECT member_id, segment_id, join_date, age_band '
                         'FROM member WHERE member_id=%(member_id)s LIMIT 1',
                         {'member_id': member_id})
        return rows[0] if rows else None

    def schema(self) -> list[dict]:
        with self.connect() as connection:
            result = []
            column_sql = '''
                SELECT ordinal_position, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %(table)s
                ORDER BY ordinal_position
            '''
            for table in TABLES:
                count = connection.execute(
                    f'SELECT COUNT(*) AS count FROM "{table}"'
                ).fetchone()['count']
                columns = connection.execute(column_sql, {'table': table}).fetchall()
                result.append({'table': table, 'rows': count, 'columns': columns})
            return result
