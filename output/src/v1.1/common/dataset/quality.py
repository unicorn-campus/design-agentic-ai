"""원천 품질 세기.

**직접 센 숫자만** 담음. 세지 못한 칸은 `미측정`이라는 글자를 그대로 둠.
짐작한 값을 넣지 않음 — 이 숫자를 평가 쪽이 기준선으로 쓰기 때문임.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from common.config import Settings, get_settings

from .paths import PathSpec, spec_of
from .source_port import Origin, ReadResult

__all__ = [
    "NOT_MEASURED",
    "PathQuality",
    "ThresholdVerdict",
    "check_threshold",
    "measure",
]

NOT_MEASURED = "미측정"

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class PathQuality:
    """경로 1개의 품질 실측값. 못 센 칸은 `None`이며 리포트에서 `미측정`으로 나감."""

    path_id: str
    origin: Origin
    row_count: int
    empty_ratio_by_column: Mapping[str, float]
    worst_empty_ratio: float | None
    duplicate_ratio: float | None
    format_mismatch_count: int | None
    measured_error_rate: float | None
    measured_on: str
    method: str
    refresh_lag: str
    design_error_rate: str
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ThresholdVerdict:
    """문턱 검사 결과. 문턱이 없으면 통과·미통과를 말하지 않음."""

    item: str
    threshold: float | None
    measured: float | None
    verdict: str


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def _format_ok(column: str, value: Any) -> bool:
    if _is_empty(value):
        return True  # 비어 있는 것은 「빈 값 비율」이 세므로 여기서 두 번 세지 않음
    if column.endswith("_on"):
        if isinstance(value, date) and not isinstance(value, datetime):
            return True
        return isinstance(value, str) and bool(_DATE_PATTERN.match(value))
    if column.endswith("_at"):
        if isinstance(value, datetime):
            return True
        if not isinstance(value, str):
            return False
        try:
            datetime.fromisoformat(value)
        except ValueError:
            return False
        return True
    if column in {"confidence_score", "value"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if column in {"fail_count", "remaining_days", "generation", "price_krw"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if column in {"notify_enabled", "is_active", "winback_offer_used"}:
        return isinstance(value, bool)
    if column in {"allergen_labels", "context_tags", "recommendation_set", "vector"}:
        return isinstance(value, (list, tuple))
    return True


def _empty_ratios(
    rows: Sequence[Mapping[str, Any]], columns: Sequence[str]
) -> dict[str, float]:
    total = len(rows)
    if total == 0:
        return {}
    return {
        column: sum(1 for row in rows if _is_empty(row.get(column))) / total
        for column in columns
    }


def _duplicate_ratio(
    rows: Sequence[Mapping[str, Any]], key_columns: Sequence[str]
) -> float | None:
    if not rows or not key_columns:
        return None
    keys = [tuple(str(row.get(column)) for column in key_columns) for row in rows]
    counts = Counter(keys)
    extra = sum(count - 1 for count in counts.values() if count > 1)
    return extra / len(rows)


def _format_mismatches(
    rows: Sequence[Mapping[str, Any]], columns: Sequence[str]
) -> int:
    return sum(
        1
        for row in rows
        for column in columns
        if not _format_ok(column, row.get(column))
    )


def _refresh_lag(spec: PathSpec) -> str:
    """캐시를 거치는 경로만 값이 있음. 그 밖은 해당 없음."""
    if spec.storage_id == "S-5":
        return "[확인필요: 추천 캐시 TTL·갱신 지연]"
    if spec.storage_id == "S-4":
        return "최대 24시간 + 배치 소요 — 매일 03:00 1회 갱신(⑤ 8절 E-3)"
    if spec.storage_id == "S-7":
        return (
            "해당 없음 — S-7이 결제 결과의 원본임. 회원계 사본으로 가는 전파 지연의 크기는 "
            "③의 전파 단계 배정값을 씀(⑤ 8절 E-13)"
        )
    return "해당 없음"


# ⑤ 8절 「원천 오류율」에 적힌 값. 전부 실측 전이라 태그가 그대로 들어 있음.
_DESIGN_ERROR_RATE: dict[str, str] = {
    "E-1": "[확인필요: 원천 오류율 실측값]",
    "E-2": "[확인필요: 원천 오류율 실측값]",
    "E-3": "[확인필요: 원천 오류율 실측값]",
    "E-13": "[확인필요: 원천 오류율 실측값]",
}


def measure(result: ReadResult, extra_notes: Sequence[str] = ()) -> PathQuality:
    """읽은 결과를 세어 품질 값을 냄. 0행이면 셀 것이 없으므로 못 센 칸을 비워 둠."""
    spec = spec_of(result.path_id)
    rows = result.rows
    empty = _empty_ratios(rows, spec.columns)
    worst = max(empty.values()) if empty else None
    duplicate = _duplicate_ratio(rows, spec.key_columns)
    mismatch = _format_mismatches(rows, spec.columns) if rows else None

    error_rate: float | None = None
    if rows:
        required_empty = [
            empty.get(column, 0.0) for column in spec.required_columns if column in empty
        ]
        cell_total = len(rows) * len(spec.columns)
        parts = [
            max(required_empty) if required_empty else 0.0,
            duplicate if duplicate is not None else 0.0,
            (mismatch or 0) / cell_total if cell_total else 0.0,
        ]
        error_rate = round(min(sum(parts), 1.0), 6)

    notes = list(extra_notes)
    if result.origin is Origin.SEED:
        notes.insert(
            0,
            "합성 시드를 센 값임 — **원천 실측이 아님.** 원천 실측은 미측정으로 남아 있음",
        )
    if not rows:
        notes.append("0행이라 비율을 세지 못했음")

    return PathQuality(
        path_id=result.path_id,
        origin=result.origin,
        row_count=result.row_count,
        empty_ratio_by_column=empty,
        worst_empty_ratio=worst,
        duplicate_ratio=duplicate,
        format_mismatch_count=mismatch,
        measured_error_rate=error_rate,
        measured_on=result.read_at.date().isoformat(),
        method="읽어 온 행을 직접 셈 — 필수 열 결측 · 열쇠 중복 · 기대한 모양 어긋남 3항목 합",
        refresh_lag=_refresh_lag(spec),
        design_error_rate=_DESIGN_ERROR_RATE.get(
            spec.error_rate_row, f"{spec.error_rate_row} — 설계서에 행이 없음"
        ),
        notes=tuple(notes),
    )


def check_threshold(
    item: str, measured: float | None, settings: Settings | None = None
) -> ThresholdVerdict:
    """품질 문턱을 넘는지 봄. 문턱 값은 설정에서만 오고 코드에 두지 않음."""
    conf = settings if settings is not None else get_settings()
    threshold = conf.dataset_quality_threshold.get(item)
    if threshold is None:
        return ThresholdVerdict(item, None, measured, "[확인필요: 원천 품질 문턱]")
    if measured is None:
        return ThresholdVerdict(item, threshold, None, NOT_MEASURED)
    return ThresholdVerdict(
        item, threshold, measured, "통과" if measured <= threshold else "미통과"
    )
