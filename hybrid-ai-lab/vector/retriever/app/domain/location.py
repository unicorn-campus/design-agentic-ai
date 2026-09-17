"""문서 유형별 메타데이터에서 공통 표시 위치를 결정함."""

from __future__ import annotations

from typing import Any


def resolve_location(metadata: dict[str, Any] | None) -> str:
    """신규·구버전 메타데이터를 모두 지원하는 검색 결과 위치를 반환함."""

    values = dict(metadata or {})
    for key in ("section_label", "clause_no"):
        raw_value = values.get(key)
        value = str(raw_value).strip() if raw_value is not None else ""
        if value:
            return value

    raw_record_id = values.get("record_id")
    raw_turn_range = values.get("turn_range")
    record_id = str(raw_record_id).strip() if raw_record_id is not None else ""
    turn_range = str(raw_turn_range).strip() if raw_turn_range is not None else ""
    return " ".join(
        part
        for part in (record_id, f"턴 {turn_range}" if turn_range else "")
        if part
    )
