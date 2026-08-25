from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from .source import PATH_SPECS


def write_snapshot(
    stage_id: str,
    rows: Iterable[Mapping[str, object]],
    directory: Path,
    basis_time: datetime | None = None,
) -> Path:
    materialized_rows = [dict(row) for row in rows]
    allowed_columns = PATH_SPECS[stage_id].allowed_columns
    if any(not set(row).issubset(allowed_columns) for row in materialized_rows):
        raise ValueError("스냅샷에 경계 미통과 항목이 있음")
    measured_at = basis_time or datetime.now(timezone.utc)
    timestamp = measured_at.strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{stage_id.lower().replace('-', '_')}_{timestamp}.json"
    target.write_text(
        json.dumps(
            {"stage_id": stage_id, "basis_time": measured_at.isoformat(), "rows": materialized_rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return target
