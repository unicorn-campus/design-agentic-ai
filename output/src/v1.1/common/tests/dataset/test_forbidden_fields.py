"""반드시 넣을 시험 3 — 만들지 않기로 한 항목이 스냅샷 · 시드 · 매핑 파일에 0건임."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from common.config import Settings
from common.dataset.forbidden import (
    BOUNDARY_SCOPED_FIELDS,
    FORBIDDEN_FIELDS,
    FORBIDDEN_TABLES,
    ForbiddenFieldFound,
    assert_no_forbidden_field,
    forbidden_fields_in,
)
from common.dataset.glossary import DEFAULT_GLOSSARY_DIR
from common.dataset.paths import PATH_IDS, PATHS, spec_of
from common.dataset.seed import SeedSourceReader
from common.dataset.snapshot import read_snapshot, write_snapshot
from common.dataset.source_port import read_path


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_path_columns_hold_no_forbidden_field(path_id: str) -> None:
    """시험 3-ⓐ — 경로 표의 열 이름에 금지 항목이 없음."""
    assert forbidden_fields_in(spec_of(path_id).columns) == ()


def test_no_path_points_at_a_forbidden_table() -> None:
    """감사 로그 · 위치 표는 경로 자체를 만들지 않음."""
    tables = {spec.logical_table for spec in PATHS.values()}
    assert tables & set(FORBIDDEN_TABLES) == set()


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_seed_rows_hold_no_forbidden_field(
    path_id: str, dataset_settings: Settings
) -> None:
    """시험 3-ⓑ — 시드 행에 금지 항목이 없음."""
    result = read_path(path_id, SeedSourceReader(dataset_settings), {}, None, dataset_settings)
    for row in result.rows:
        assert forbidden_fields_in(row) == ()


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_snapshot_rows_hold_no_forbidden_field(
    path_id: str, dataset_settings: Settings, tmp_path: Path
) -> None:
    """시험 3-ⓒ — 남긴 스냅샷 파일에도 금지 항목이 없음."""
    result = read_path(path_id, SeedSourceReader(dataset_settings), {}, None, dataset_settings)
    settings = dataset_settings.model_copy(
        update={"dataset_snapshot_dir": str(tmp_path)}
    )
    handle = write_snapshot(result, settings)
    for row in read_snapshot(handle.data_file):
        assert forbidden_fields_in(row) == ()
    meta = json.loads(handle.meta_file.read_text(encoding="utf-8"))
    assert forbidden_fields_in(meta["columns"]) == ()


@pytest.mark.parametrize(
    "file_name", ["glossary_food_tags.csv", "glossary_allergen_codes.csv"]
)
def test_mapping_files_hold_no_forbidden_field(file_name: str) -> None:
    """시험 3-ⓓ — 매핑 파일의 열 이름과 값에 금지 항목이 없음."""
    path = DEFAULT_GLOSSARY_DIR / file_name
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert forbidden_fields_in(reader.fieldnames) == ()
        for record in reader:
            for value in record.values():
                assert forbidden_fields_in((value or "",)) == ()


def test_forbidden_field_is_reported_not_silently_dropped() -> None:
    with pytest.raises(ForbiddenFieldFound):
        assert_no_forbidden_field({"member_id": "M1", "email": "a@b.c"}, "시험")


def test_boundary_scoped_fields_are_kept_and_labelled() -> None:
    """경계 밖으로만 안 내보내는 필드는 금지 목록에 섞지 않음."""
    scoped = {item.field for item in BOUNDARY_SCOPED_FIELDS}
    assert scoped & set(FORBIDDEN_FIELDS) == set()
    # ⑤ 3절이 읽으라고 적은 값이라 경로 표에 그대로 있음
    assert "nickname" in spec_of("T-1").columns
    assert {"allergen_labels", "diet_type"} <= set(spec_of("T-2").columns)
    for item in BOUNDARY_SCOPED_FIELDS:
        assert item.not_crossing, f"{item.field}에 어느 경계인지 안 적혀 있음"
