"""K-2 키워드 · 속성 필터 검색 — 정확 조건으로 후보를 거름.

축 이름은 ④ 「입출력 형식」 메타데이터 거르기 키 4개를 그대로 씀. 새 이름을 짓지 않음.
⑤ K-2가 **부분 성립**이라고 적은 축(가격대 · 영업 상태)은 값을 지어내지 않고
「걸 값이 없음」을 사유로 돌려줌.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from common.config import Settings, SettingsMissing, get_settings

from .result import (
    Candidate,
    Provenance,
    RetrievalKind,
    RetrievalResult,
    RetrievalTrace,
    ScoreKind,
    now_utc,
)

__all__ = [
    "AXIS_ESTABLISHED",
    "AXIS_NOT_ESTABLISHED",
    "AxisNotEstablished",
    "AxisStatus",
    "axis_status",
    "filter_by_attributes",
]

_ROUTE_ID = "K-2"

AXIS_ESTABLISHED = "성립"
AXIS_NOT_ESTABLISHED = "부분 성립 — 원천 미확정으로 걸 값이 없음"


class AxisNotEstablished(ValueError):
    """⑤가 「걸 값이 없음」이라고 적은 축으로 거르려 했음."""


@dataclass(frozen=True, slots=True)
class AxisStatus:
    """축 1개의 성립 여부. 값의 주인은 ⑤ K-2임."""

    key: str
    established: bool
    note: str


def axis_status(settings: Settings | None = None) -> dict[str, AxisStatus]:
    """⑤ K-2 「성립 여부」를 설정에서 읽음. 코드에 성립·미성립을 박지 않음."""
    conf = settings if settings is not None else get_settings()
    axes = conf.knowledge_attribute_axes
    if not axes:
        raise SettingsMissing("속성 필터 축이 설정에 없음 — ⑤ K-2 「필터 축」을 채워야 함")
    return {
        key: AxisStatus(key=key, established=value == AXIS_ESTABLISHED, note=value)
        for key, value in axes.items()
    }


def filter_by_attributes(
    rows: Sequence[Mapping[str, Any]],
    criteria: Mapping[str, Any],
    settings: Settings | None = None,
) -> RetrievalResult:
    """정확 조건으로 거른 뒤 기본 정렬 기준으로 줄 세움.

    - 조건 키는 ④가 소유한 메타데이터 거르기 키 안에만 있어야 함
    - ⑤가 미성립이라고 적은 축을 쓰면 거르지 않고 **사유와 함께 빈 결과**를 돌려줌
    """
    conf = settings if settings is not None else get_settings()
    owned = set(conf.knowledge_metadata_filter_keys)
    if not owned:
        raise SettingsMissing(
            "메타데이터 거르기 키가 설정에 없음 — 이름의 주인은 ④ 「입출력 형식」임"
        )
    outside = sorted(set(criteria) - owned)
    if outside:
        raise AxisNotEstablished(f"④가 소유하지 않은 거르기 키임 — {outside}")

    status = axis_status(conf)
    unusable = sorted(
        key for key in criteria if key in status and not status[key].established
    )
    if unusable:
        notes = tuple(f"{key} — {status[key].note}" for key in unusable)
        return RetrievalResult.empty(
            _ROUTE_ID,
            RetrievalKind.ATTRIBUTE_FILTER,
            f"걸 값이 없는 축으로 거르려 했음 — {unusable}",
            notes=notes,
        )

    kept = [
        row
        for row in rows
        if all(key in row and row[key] == wanted for key, wanted in criteria.items())
    ]
    sort_key = conf.knowledge_sort_primary
    if sort_key and kept and all(sort_key in row for row in kept):
        kept.sort(key=lambda row: row[sort_key])

    read_at = now_utc()
    candidates = tuple(
        Candidate(
            payload=dict(row),
            source=Provenance(
                route_id=_ROUTE_ID,
                locator=f"속성 후보#{index}",
                design_row="⑤ 5절 K-2",
                origin="부르는 쪽이 넘긴 후보 목록",
                read_at=read_at,
            ),
            score=float(index),
            score_kind=ScoreKind.DISTANCE_ASC,
        )
        for index, row in enumerate(kept)
    )
    trace = RetrievalTrace(
        stage="속성 필터",
        before=tuple(str(row.get("place_id", index)) for index, row in enumerate(rows)),
        after=tuple(str(row.get("place_id", index)) for index, row in enumerate(kept)),
        detail={"criteria": dict(criteria), "sort_primary": sort_key},
    )
    return RetrievalResult.of(
        _ROUTE_ID,
        RetrievalKind.ATTRIBUTE_FILTER,
        candidates,
        reason_when_empty=(
            f"정확 조건 {sorted(criteria)}을 지난 후보가 0건임 — 조건을 늘려 채우지 않음"
        ),
        notes=(f"들어온 {len(rows)}건 → 남은 {len(kept)}건",),
        traces=(trace,),
    )
