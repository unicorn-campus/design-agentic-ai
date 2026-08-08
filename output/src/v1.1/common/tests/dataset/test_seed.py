"""반드시 넣을 시험 4 — 같은 난수 씨앗으로 두 번 만들면 같은 데이터가 나옴."""

from __future__ import annotations

import pytest

from common.config import Settings
from common.dataset.paths import PATH_IDS, spec_of
from common.dataset.seed import SEED_MARK, SeedSourceReader, seed_blocked_reason, seed_rows_for
from common.dataset.source_port import Origin, read_path

from .conftest import DATASET_ROW_CAP


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_same_seed_gives_same_rows(path_id: str) -> None:
    """시험 4 — 씨앗이 같으면 두 번 만든 결과가 완전히 같음."""
    first, _ = seed_rows_for(path_id, DATASET_ROW_CAP[path_id], seed=7)
    second, _ = seed_rows_for(path_id, DATASET_ROW_CAP[path_id], seed=7)
    assert first == second


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_every_seed_row_carries_the_synthetic_mark(path_id: str) -> None:
    rows, _ = seed_rows_for(path_id, DATASET_ROW_CAP[path_id], seed=7)
    for row in rows:
        assert row[SEED_MARK] is True


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_seed_columns_do_not_add_or_drop_design_columns(path_id: str) -> None:
    """열을 더하거나 빼지 않음. 합성 표식 1개만 더 붙음."""
    rows, _ = seed_rows_for(path_id, DATASET_ROW_CAP[path_id], seed=7)
    if not rows:
        assert seed_blocked_reason(path_id) is not None
        return
    expected = set(spec_of(path_id).columns) | {SEED_MARK}
    for row in rows:
        assert set(row) <= expected
    if path_id not in {"T-9", "T-13", "T-17", "T-14"}:
        assert set(rows[0]) == expected


def test_blocked_path_makes_no_rows_and_says_why() -> None:
    rows, notes = seed_rows_for("T-10", DATASET_ROW_CAP["T-10"], seed=7)
    assert rows == []
    assert notes and "확인필요" in notes[0]


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_seed_reader_has_the_same_shape_as_live_reader(
    path_id: str, dataset_settings: Settings
) -> None:
    """실데이터로 갈아 끼울 수 있게 읽는 사람 모양이 같음."""
    result = read_path(path_id, SeedSourceReader(dataset_settings), {}, None, dataset_settings)
    assert result.origin is Origin.SEED
    assert result.row_count <= result.row_cap


def test_seed_row_count_defaults_to_the_row_cap(dataset_settings: Settings) -> None:
    for path_id in PATH_IDS:
        assert dataset_settings.dataset_seed_row_count(path_id) == DATASET_ROW_CAP[path_id]
