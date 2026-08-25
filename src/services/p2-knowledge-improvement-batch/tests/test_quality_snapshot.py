import json
from datetime import datetime, timezone

import pytest

from help_desk_dataset.quality import measure_quality, render_quality_report
from help_desk_dataset.seed import generate_seed_rows
from help_desk_dataset.snapshot import write_snapshot


def test_quality_report_contains_measured_method_and_date() -> None:
    result = measure_quality("S-R4", generate_seed_rows("S-R4", 10, 20260825))
    report = render_quality_report([result])

    assert result.row_count == 10
    assert result.method in report
    assert result.measured_on.isoformat() in report
    assert "문턱 없음: 관찰값" in report


def test_snapshot_name_contains_basis_time_and_forbidden_fields_are_absent(tmp_path) -> None:
    rows = generate_seed_rows("S-B2", 2, 20260825)
    basis_time = datetime(2026, 8, 25, 1, 2, 3, tzinfo=timezone.utc)
    path = write_snapshot("S-B2", rows, tmp_path, basis_time)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "s_b2_20260825T010203Z.json"
    assert payload["basis_time"] == basis_time.isoformat()
    blocked = {
        "full_card_number",
        "cvc",
        "password",
        "auth_token",
        "resident_registration_number",
        "original_customer_id",
        "raw_transcript",
    }
    assert all(blocked.isdisjoint(row) for row in payload["rows"])


def test_snapshot_rejects_boundary_blocked_field(tmp_path) -> None:
    with pytest.raises(ValueError):
        write_snapshot("S-B2", [{"raw_transcript": "blocked"}], tmp_path)
