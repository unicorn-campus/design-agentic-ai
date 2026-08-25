from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence

from .source import PATH_SPECS


@dataclass(frozen=True)
class QualityResult:
    stage_id: str
    row_count: int
    empty_rates: dict[str, float]
    duplicate_rate: float
    format_mismatch_count: int
    measured_error_rate: float
    method: str
    measured_on: date
    refresh_lag: str
    threshold: str = "문턱 없음: 관찰값"


def _is_valid(column: str, value: object) -> bool:
    if value in (None, ""):
        return True
    if column == "transaction_date":
        try:
            date.fromisoformat(str(value))
        except ValueError:
            return False
    elif column == "ended_at":
        try:
            datetime.fromisoformat(str(value))
        except ValueError:
            return False
    elif column == "reopen_count":
        return isinstance(value, int) and value >= 0
    return isinstance(value, str)


def measure_quality(stage_id: str, rows: Sequence[Mapping[str, object]]) -> QualityResult:
    spec = PATH_SPECS[stage_id]
    total = len(rows)
    empty_rates = {
        column: (sum(row.get(column) in (None, "") for row in rows) / total if total else 0.0)
        for column in sorted(spec.allowed_columns)
    }
    key_column = "masked_customer_id" if stage_id == "S-R4" else "consultation_ref"
    keys = [row.get(key_column) for row in rows]
    duplicate_count = len(keys) - len(set(keys))
    format_bad_rows = {
        index
        for index, row in enumerate(rows)
        if set(row) != set(spec.allowed_columns)
        or any(not _is_valid(column, row.get(column)) for column in spec.allowed_columns)
    }
    empty_rows = {
        index for index, row in enumerate(rows) if any(row.get(column) in (None, "") for column in spec.allowed_columns)
    }
    duplicate_rows: set[int] = set()
    seen: set[object] = set()
    for index, key in enumerate(keys):
        if key in seen:
            duplicate_rows.add(index)
        seen.add(key)
    bad_rows = empty_rows | duplicate_rows | format_bad_rows
    return QualityResult(
        stage_id=stage_id,
        row_count=total,
        empty_rates=empty_rates,
        duplicate_rate=(duplicate_count / total if total else 0.0),
        format_mismatch_count=len(format_bad_rows),
        measured_error_rate=(len(bad_rows) / total if total else 0.0),
        method="합성 고정 응답 전건 스캔",
        measured_on=date.today(),
        refresh_lag="해당 없음",
    )


def render_quality_report(results: Sequence[QualityResult]) -> str:
    lines = [
        "# 원천 품질 리포트",
        "",
        "> 설계서의 오류율 인용값이 아닌 합성 고정 응답 실측 결과임.  ",
        "> 실제 원천 전환 시 같은 측정기를 다시 실행해야 함.",
        "",
        "| 경로 | 행 수 | 빈 값 비율 | 중복 비율 | 형식 어긋남 | 실측 오류율 | "
        "측정 방법 | 측정일 | 갱신 지연 | 품질 문턱 |",
        "|---|---:|---|---:|---:|---:|---|---|---|---|",
    ]
    for result in results:
        empties = ", ".join(f"{key}={value:.2%}" for key, value in result.empty_rates.items())
        lines.append(
            f"| `{result.stage_id}` | {result.row_count} | {empties} | {result.duplicate_rate:.2%} | "
            f"{result.format_mismatch_count}건 | {result.measured_error_rate:.2%} | {result.method} | "
            f"{result.measured_on.isoformat()} | {result.refresh_lag} | {result.threshold} |"
        )
    lines.extend(
        [
            "",
            "## 기준선 전달",
            "",
            "`09-eval.md`는 위 실측값을 합성 데이터 기준선으로 사용함.  ",
            "실제 원천 결과가 확보되면 합성값과 섞지 않고 새 측정일의 행으로 교체함.",
            "",
        ]
    )
    return "\n".join(lines)
