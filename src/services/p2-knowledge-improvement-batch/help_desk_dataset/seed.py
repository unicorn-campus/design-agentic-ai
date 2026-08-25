from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from help_desk_runtime.settings import RuntimeSettings

from .source import CONSULTATION_COLUMNS, PATH_SPECS, TRANSACTION_COLUMNS, _required_setting


def _transaction_row(index: int, rng: random.Random) -> dict[str, object]:
    return {
        "masked_customer_id": f"SYNTHETIC:C{index:06d}",
        "transaction_date": (date(2026, 1, 1) + timedelta(days=index % 365)).isoformat(),
        "transaction_status": rng.choice(("정상", "이용거절")),
        "decline_reason_code": rng.choice(("NOT_APPLICABLE", "LIMIT", "STATUS")),
        "amount_bucket": rng.choice(("LOW", "MEDIUM", "HIGH")),
        "merchant_category_code": f"MCC{index % 20:02d}",
    }


def _consultation_row(index: int, rng: random.Random) -> dict[str, object]:
    ended_at = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index)
    return {
        "consultation_ref": f"SYNTHETIC:Q{index:06d}",
        "ended_at": ended_at.isoformat(),
        "topic_code": rng.choice(("BILLING", "DECLINE", "BENEFIT", "DISPUTE")),
        "resolution_code": rng.choice(("RESOLVED", "HANDOFF", "FOLLOW_UP")),
        "reopen_count": rng.randrange(0, 4),
        "masked_summary": f"합성 상담 요약 {index}",
    }


def generate_seed_rows(stage_id: str, count: int, seed: int) -> list[dict[str, object]]:
    if count < 0:
        raise ValueError("시드 건수는 0 이상이어야 함")
    rng = random.Random(f"{seed}:{stage_id}")
    row_factory = _transaction_row if stage_id == "S-R4" else _consultation_row
    rows = [row_factory(index, rng) for index in range(count)]
    expected = TRANSACTION_COLUMNS if stage_id == "S-R4" else CONSULTATION_COLUMNS
    if any(set(row) != expected for row in rows):
        raise AssertionError("합성 시드 열이 설계 열과 다름")
    return rows


def generate_all_seed_files(settings: RuntimeSettings, output_dir: Path) -> dict[str, Path]:
    seed = int(_required_setting(settings, "dataset_seed"))
    output_dir.mkdir(parents=True, exist_ok=True)
    created: dict[str, Path] = {}
    for stage_id in PATH_SPECS:
        suffix = stage_id.lower().replace("-", "_")
        count = int(_required_setting(settings, f"dataset_{suffix}_seed_rows"))
        rows = generate_seed_rows(stage_id, count, seed)
        path = output_dir / f"{suffix}_mock_response.json"
        path.write_text(
            json.dumps({"stage_id": stage_id, "synthetic": True, "rows": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        created[stage_id] = path
    return created
