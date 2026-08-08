"""읽어 온 결과를 파일로 남김.

파일 이름에 **기준 시점**을 넣음 — 언제 뜬 것인지 파일 이름만 보고 알 수 있게 함.
보존 기간은 **자리만** 만들어 둠. 실제 파기 작업은 배포 쪽 몫임.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from common.config import Settings, get_settings

from .forbidden import assert_no_forbidden_field
from .paths import spec_of
from .source_port import ReadResult

__all__ = [
    "DEFAULT_SNAPSHOT_DIR",
    "SnapshotHandle",
    "read_snapshot",
    "retention_days_for",
    "snapshot_dir",
    "snapshot_stem",
    "write_snapshot",
]

DEFAULT_SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
_TIME_FORMAT = "%Y%m%dT%H%M%SZ"


@dataclass(frozen=True, slots=True)
class SnapshotHandle:
    """남긴 파일 2개의 자리. 본문과 딸림 정보를 따로 둠."""

    path_id: str
    taken_at: datetime
    data_file: Path
    meta_file: Path
    row_count: int
    retention_days: int | None


def snapshot_dir(settings: Settings | None = None) -> Path:
    conf = settings if settings is not None else get_settings()
    if conf.dataset_snapshot_dir:
        return Path(conf.dataset_snapshot_dir)
    return DEFAULT_SNAPSHOT_DIR


def retention_days_for(path_id: str, settings: Settings | None = None) -> int | None:
    """스냅샷 보존 기간. 설계서에 기간이 없으면 `None`이며 파기를 돌리지 않음."""
    conf = settings if settings is not None else get_settings()
    return conf.dataset_snapshot_retention_days.get(path_id)


def snapshot_stem(path_id: str, taken_at: datetime, origin: str) -> str:
    """파일 이름 규칙 — `경로_기준시점_출처`."""
    return f"{path_id}_{taken_at.strftime(_TIME_FORMAT)}_{origin}"


def write_snapshot(
    result: ReadResult,
    settings: Settings | None = None,
    taken_at: datetime | None = None,
) -> SnapshotHandle:
    """읽은 결과를 한 줄에 한 행씩 남기고 딸림 정보를 곁에 둠."""
    conf = settings if settings is not None else get_settings()
    spec = spec_of(result.path_id)
    stamp = taken_at if taken_at is not None else result.read_at
    target = snapshot_dir(conf)
    target.mkdir(parents=True, exist_ok=True)

    stem = snapshot_stem(result.path_id, stamp, result.origin.value)
    data_file = target / f"{stem}.jsonl"
    meta_file = target / f"{stem}.meta.json"

    with data_file.open("w", encoding="utf-8") as handle:
        for row in result.rows:
            assert_no_forbidden_field(row, f"{result.path_id} 스냅샷 행")
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    retention = retention_days_for(result.path_id, conf)
    meta: dict[str, Any] = {
        "path_id": result.path_id,
        "logical_table": spec.logical_table,
        "storage_id": spec.storage_id,
        "storage_kind": spec.storage_kind.value,
        "owner_service": spec.owner_service,
        "design_row": spec.design_row,
        "origin": result.origin.value,
        "taken_at": stamp.isoformat(),
        "row_cap": result.row_cap,
        "requested_limit": result.requested_limit,
        "effective_limit": result.effective_limit,
        "row_count": result.row_count,
        "truncated": result.truncated,
        "columns": list(spec.columns),
        "retention_days": retention if retention is not None else "[확인필요: 보존 기간]",
        "purge_owner": "배포 프롬프트 — 이 모듈은 기간을 적어 두는 자리만 만듦",
    }
    meta_file.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return SnapshotHandle(
        path_id=result.path_id,
        taken_at=stamp,
        data_file=data_file,
        meta_file=meta_file,
        row_count=result.row_count,
        retention_days=retention,
    )


def read_snapshot(data_file: Path) -> list[dict[str, Any]]:
    """남긴 스냅샷을 다시 읽음. 검색 쪽과 평가 쪽이 이 함수를 씀."""
    rows: list[dict[str, Any]] = []
    with data_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows
