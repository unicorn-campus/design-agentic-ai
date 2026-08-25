from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import httpx
from sqlglot import exp, parse

from help_desk_runtime.settings import RuntimeSettings


class DatasetConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class PathSpec:
    stage_id: str
    table: str
    allowed_columns: frozenset[str]
    max_rows_setting: str


TRANSACTION_COLUMNS = frozenset(
    {
        "masked_customer_id",
        "transaction_date",
        "transaction_status",
        "decline_reason_code",
        "amount_bucket",
        "merchant_category_code",
    }
)
CONSULTATION_COLUMNS = frozenset(
    {
        "consultation_ref",
        "ended_at",
        "topic_code",
        "resolution_code",
        "reopen_count",
        "masked_summary",
    }
)

PATH_SPECS = {
    "S-R4": PathSpec(
        stage_id="S-R4",
        table="masked_transaction_analysis_v",
        allowed_columns=TRANSACTION_COLUMNS,
        max_rows_setting="dataset_s_r4_max_rows",
    ),
    "S-B2": PathSpec(
        stage_id="S-B2",
        table="masked_consultation_analysis_v",
        allowed_columns=CONSULTATION_COLUMNS,
        max_rows_setting="dataset_s_b2_max_rows",
    ),
    "S-B4": PathSpec(
        stage_id="S-B4",
        table="masked_consultation_analysis_v",
        allowed_columns=CONSULTATION_COLUMNS,
        max_rows_setting="dataset_s_b4_max_rows",
    ),
}


def _required_setting(settings: RuntimeSettings, name: str) -> Any:
    value = getattr(settings, name, None)
    if value is None or value == "":
        raise DatasetConfigurationError(f"필수 설정이 비어 있음: HELP_DESK_{name.upper()}")
    return value


def validate_read_statement(statement: str, spec: PathSpec, limit: int) -> str:
    statements = parse(statement, read="postgres")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("단일 SELECT 문만 허용됨")
    query = statements[0]
    if query.find(exp.DML) is not None or query.find(exp.DDL) is not None:
        raise ValueError("읽기 외 구문은 허용되지 않음")
    tables = {table.name for table in query.find_all(exp.Table)}
    if tables != {spec.table}:
        raise ValueError(f"허용 테이블은 {spec.table} 하나임")
    columns = {column.name for column in query.find_all(exp.Column)}
    if query.find(exp.Star) is not None or not columns.issubset(spec.allowed_columns):
        raise ValueError("허용 열만 조회 가능함")
    return query.limit(limit, copy=True).sql(dialect="postgres")


class AnalyticsSource:
    def __init__(self, settings: RuntimeSettings, client: httpx.Client | None = None) -> None:
        base_url = str(_required_setting(settings, "analytics_base_url"))
        timeout = float(_required_setting(settings, "analytics_timeout_seconds"))
        self._settings = settings
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def _read(
        self,
        stage_id: str,
        statement: str,
        parameters: Mapping[str, object] | None,
        requested_limit: int,
    ) -> list[dict[str, object]]:
        spec = PATH_SPECS[stage_id]
        configured_limit = int(_required_setting(self._settings, spec.max_rows_setting))
        effective_limit = min(max(requested_limit, 0), configured_limit)
        safe_statement = validate_read_statement(statement, spec, effective_limit)
        response = self._client.post(
            "/v1/query",
            json={
                "statement": safe_statement,
                "parameters": dict(parameters or {}),
                "max_rows": effective_limit,
            },
        )
        payload = response.raise_for_status().json()
        rows = payload.get("rows", [])
        if any(not set(row).issubset(spec.allowed_columns) for row in rows):
            raise ValueError("응답에 허용되지 않은 열이 있음")
        return [dict(row) for row in rows[:effective_limit]]

    def read_s_r4(
        self, statement: str, parameters: Mapping[str, object] | None, requested_limit: int
    ) -> list[dict[str, object]]:
        return self._read("S-R4", statement, parameters, requested_limit)

    def read_s_b2(
        self, statement: str, parameters: Mapping[str, object] | None, requested_limit: int
    ) -> list[dict[str, object]]:
        return self._read("S-B2", statement, parameters, requested_limit)

    def read_s_b4(
        self, statement: str, parameters: Mapping[str, object] | None, requested_limit: int
    ) -> list[dict[str, object]]:
        return self._read("S-B4", statement, parameters, requested_limit)

    def close(self) -> None:
        self._client.close()
