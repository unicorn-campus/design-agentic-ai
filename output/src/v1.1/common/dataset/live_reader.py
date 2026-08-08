"""실제 원천에 붙어 읽는 사람. 읽기 전용으로만 붙음.

읽기 전용을 **두 겹**으로 걸어 둠.

- 접속 자체를 읽기 전용으로 열음(`conn.read_only = True`)
- 미리 짠 조회문을 관문에 통과시킨 뒤에만 보냄(`write_guard`)

물리 표 · 열 이름이 아직 정해지지 않았으므로 조회문은 **설정에서 받음.**
설정이 비어 있으면 지어내지 않고 왜 못 읽는지 알리며 멈춤.

확인한 API(context7 · psycopg 3) — `psycopg.connect(conninfo, row_factory=dict_row)` ·
`Connection.read_only` 속성 · `cursor.execute(query, params)` · `psycopg.rows.dict_row`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from common.config import Settings, get_settings

from .paths import PathSpec, StorageKind
from .source_port import Origin, SourceUnavailable
from .write_guard import ROW_CAP_PLACEHOLDER, ensure_read_only_query

__all__ = ["LiveSourceReader", "connection_setting_name", "missing_inputs_for"]

_SCHEMA_TAG = "[확인필요: DBMS 제품명·물리 스키마]"
_VECTOR_TAG = "[확인필요: 벡터 인덱스 제품·임베딩 모델명·버전]"
_CACHE_TAG = "[확인필요: 추천 캐시 TTL·갱신 지연]"

# 저장소 종류 → 접속 정보를 담을 설정 키 이름. **이름만 정하고 값은 정하지 않음.**
_CONNECTION_SETTING: dict[StorageKind, str] = {
    StorageKind.RELATIONAL: "LUNCHPICK_DATASET_SOURCE_DB_URL",
    StorageKind.VECTOR: "LUNCHPICK_DATASET_VECTOR_INDEX_URL",
    StorageKind.CACHE: "LUNCHPICK_DATASET_CACHE_URL",
}

_MISSING_TAG: dict[StorageKind, str] = {
    StorageKind.RELATIONAL: _SCHEMA_TAG,
    StorageKind.VECTOR: _VECTOR_TAG,
    StorageKind.CACHE: _CACHE_TAG,
}


def connection_setting_name(kind: StorageKind) -> str:
    """그 저장소의 접속 정보를 담을 설정 키 이름. 값의 주인은 도구 연동·배포임."""
    return _CONNECTION_SETTING[kind]


def _connection_value(kind: StorageKind, conf: Settings) -> str | None:
    if kind is StorageKind.RELATIONAL:
        return conf.dataset_source_db_url
    if kind is StorageKind.VECTOR:
        return conf.dataset_vector_index_url
    return conf.dataset_cache_url


def missing_inputs_for(spec: PathSpec, settings: Settings | None = None) -> tuple[str, ...]:
    """이 경로를 실제로 읽으려면 아직 무엇이 없나. 비어 있으면 읽을 수 있음."""
    conf = settings if settings is not None else get_settings()
    missing: list[str] = []
    if not _connection_value(spec.storage_kind, conf):
        missing.append(f"{connection_setting_name(spec.storage_kind)} 값 없음")
    if not conf.dataset_physical_query.get(spec.path_id):
        missing.append(f"{spec.path_id}의 미리 짠 조회문 없음 — {_MISSING_TAG[spec.storage_kind]}")
    return tuple(missing)


class LiveSourceReader:
    """실물 원천 1벌. 관계형 저장소만 다루며 다른 종류는 못 읽는다고 알림."""

    origin = Origin.LIVE

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings if settings is not None else get_settings()

    def fetch(
        self, spec: PathSpec, params: Mapping[str, Any], row_cap: int
    ) -> Sequence[Mapping[str, Any]]:
        missing = missing_inputs_for(spec, self._settings)
        if missing:
            raise SourceUnavailable(
                f"{spec.path_id}({spec.logical_table})를 실제로 읽을 수 없음 — " + " · ".join(missing)
            )
        if spec.storage_kind is not StorageKind.RELATIONAL:
            raise SourceUnavailable(
                f"{spec.path_id}는 {spec.storage_kind.value} 저장소임. "
                f"이 읽기 계층은 관계형만 다룸 — 제품이 정해지면 읽는 사람을 갈아 끼움"
            )

        query = ensure_read_only_query(
            self._settings.dataset_physical_query[spec.path_id],
            f"{spec.path_id} 미리 짠 조회문",
        )
        return self._run(query, spec, params, row_cap)

    def _run(
        self,
        query: str,
        spec: PathSpec,
        params: Mapping[str, Any],
        row_cap: int,
    ) -> Sequence[Mapping[str, Any]]:
        import psycopg
        from psycopg.rows import dict_row

        bound: dict[str, Any] = dict(params)
        bound["row_cap"] = row_cap
        dsn = _connection_value(spec.storage_kind, self._settings)
        assert dsn is not None  # 위에서 이미 확인함

        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            conn.read_only = True
            with conn.cursor() as cur:
                cur.execute(query, bound)  # type: ignore[arg-type]
                return [dict(row) for row in cur.fetchall()]


def sample_query_shape(spec: PathSpec) -> str:
    """설정에 넣을 조회문의 **모양**만 보여 줌. 실제 표 · 열 이름은 여기에 없음."""
    conditions = " AND ".join(f"{name} = %({name})s" for name in spec.filter_params) or "TRUE"
    return (
        f"SELECT {', '.join(spec.columns)} "
        f"FROM <{_SCHEMA_TAG}> WHERE {conditions} LIMIT {ROW_CAP_PLACEHOLDER}"
    )
