"""원천에서 읽어 오는 계약과 상한 강제.

읽기 함수는 전부 이 관문을 지남. 관문이 하는 일 3가지임.

1. 행 수 상한을 **설정에서 읽어** 호출마다 붙임. 상한을 안 정한 경로는 읽지 않음
2. 만들지 않기로 한 필드가 결과에 섞이면 바로 드러냄
3. 읽어 온 것이 실물인지 합성인지 결과에 적어 둠
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from common.config import Settings, get_settings

from .forbidden import assert_no_forbidden_field
from .paths import PathSpec, spec_of

__all__ = [
    "Origin",
    "ReadResult",
    "SourceReader",
    "SourceUnavailable",
    "read_path",
]


class SourceUnavailable(RuntimeError):
    """원천에 붙을 수 없음. 없는 값을 지어내지 않고 왜 못 붙는지 그대로 알림."""


class Origin(StrEnum):
    """읽어 온 곳. 실물과 합성이 섞여도 구분되게 함."""

    LIVE = "실접속"
    SEED = "합성시드"


@runtime_checkable
class SourceReader(Protocol):
    """원천 1벌을 읽는 사람. 합성 시드와 실접속이 이 모양을 같이 씀."""

    origin: Origin

    def fetch(
        self, spec: PathSpec, params: Mapping[str, Any], row_cap: int
    ) -> Sequence[Mapping[str, Any]]:
        """`row_cap`행을 넘겨 돌려주지 않음. 넘기면 관문이 자름."""


@dataclass(frozen=True, slots=True)
class ReadResult:
    """읽은 결과 1벌. 스냅샷과 품질 리포트가 이 값만 봄."""

    path_id: str
    origin: Origin
    row_cap: int
    requested_limit: int | None
    effective_limit: int
    rows: tuple[Mapping[str, Any], ...]
    read_at: datetime
    truncated: bool
    notes: tuple[str, ...] = field(default=())

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _effective_limit(row_cap: int, requested: int | None) -> int:
    if requested is None:
        return row_cap
    if requested < 0:
        raise ValueError("행 수를 음수로 달라고 할 수 없음")
    return min(requested, row_cap)


def read_path(
    path_id: str,
    reader: SourceReader,
    params: Mapping[str, Any] | None = None,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """경로 1개를 읽음. 상한은 설정에서만 오고 호출마다 붙음."""
    spec = spec_of(path_id)
    conf = settings if settings is not None else get_settings()
    row_cap = conf.dataset_row_cap_for(path_id)
    if row_cap < 1:
        raise ValueError(f"{path_id}의 행 수 상한이 1보다 작음 — 설정을 고쳐야 함")
    effective = _effective_limit(row_cap, limit)

    given = dict(params or {})
    unknown = set(given) - set(spec.filter_params)
    if unknown:
        raise ValueError(f"{path_id}가 받지 않는 거르는 조건임: {sorted(unknown)}")
    assert_no_forbidden_field(given, f"{path_id} 거르는 조건")

    fetched = list(reader.fetch(spec, given, effective))
    truncated = len(fetched) > effective
    rows = fetched[:effective]
    for index, row in enumerate(rows):
        assert_no_forbidden_field(row, f"{path_id} {index}번째 행")

    return ReadResult(
        path_id=path_id,
        origin=reader.origin,
        row_cap=row_cap,
        requested_limit=limit,
        effective_limit=effective,
        rows=tuple(rows),
        read_at=datetime.now(UTC),
        truncated=truncated,
    )
