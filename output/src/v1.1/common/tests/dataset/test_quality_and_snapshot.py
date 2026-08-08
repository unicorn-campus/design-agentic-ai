"""품질 세기 · 스냅샷 · 리포트 시험. 짐작한 숫자가 리포트에 들어가지 않는지도 봄."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.config import Settings
from common.dataset.live_reader import LiveSourceReader, missing_inputs_for
from common.dataset.paths import PATH_IDS, StorageKind, spec_of
from common.dataset.quality import NOT_MEASURED, check_threshold, measure
from common.dataset.report import build_report, collect
from common.dataset.seed import SeedSourceReader
from common.dataset.snapshot import (
    read_snapshot,
    retention_days_for,
    snapshot_stem,
    write_snapshot,
)
from common.dataset.source_port import Origin, SourceUnavailable, read_path


@pytest.fixture
def tmp_settings(dataset_settings: Settings, tmp_path: Path) -> Settings:
    return dataset_settings.model_copy(update={"dataset_snapshot_dir": str(tmp_path)})


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_measure_counts_only_what_it_saw(path_id: str, dataset_settings: Settings) -> None:
    result = read_path(path_id, SeedSourceReader(dataset_settings), {}, None, dataset_settings)
    quality = measure(result)
    assert quality.row_count == result.row_count
    if result.row_count == 0:
        assert quality.measured_error_rate is None
        assert quality.duplicate_ratio is None
        assert quality.format_mismatch_count is None
    else:
        assert quality.measured_error_rate is not None
        assert 0.0 <= quality.measured_error_rate <= 1.0


def test_seed_measurement_is_labelled_as_not_a_real_source_measure(
    dataset_settings: Settings,
) -> None:
    result = read_path("T-1", SeedSourceReader(dataset_settings), {}, None, dataset_settings)
    quality = measure(result)
    assert quality.origin is Origin.SEED
    assert any("원천 실측이 아님" in note for note in quality.notes)


def test_design_error_rate_is_carried_over_unchanged(dataset_settings: Settings) -> None:
    """⑤ 8절에 적힌 값을 고쳐 적지 않음."""
    result = read_path("T-1", SeedSourceReader(dataset_settings), {}, None, dataset_settings)
    assert measure(result).design_error_rate == "[확인필요: 원천 오류율 실측값]"


def test_threshold_stays_open_when_the_design_has_none(dataset_settings: Settings) -> None:
    verdict = check_threshold("T-1.error_rate", 0.5, dataset_settings)
    assert verdict.threshold is None
    assert verdict.verdict == "[확인필요: 원천 품질 문턱]"


def test_threshold_is_read_from_settings_not_from_source(
    dataset_settings: Settings,
) -> None:
    settings = dataset_settings.model_copy(
        update={"dataset_quality_threshold": {"T-1.error_rate": 0.1}}
    )
    assert check_threshold("T-1.error_rate", 0.05, settings).verdict == "통과"
    assert check_threshold("T-1.error_rate", 0.2, settings).verdict == "미통과"


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_snapshot_name_carries_the_reference_time(
    path_id: str, tmp_settings: Settings
) -> None:
    result = read_path(path_id, SeedSourceReader(tmp_settings), {}, None, tmp_settings)
    handle = write_snapshot(result, tmp_settings)
    assert handle.data_file.name.startswith(
        snapshot_stem(path_id, result.read_at, result.origin.value)
    )
    assert len(read_snapshot(handle.data_file)) == result.row_count


def test_snapshot_meta_keeps_retention_as_open_when_the_design_has_none(
    tmp_settings: Settings,
) -> None:
    result = read_path("T-1", SeedSourceReader(tmp_settings), {}, None, tmp_settings)
    handle = write_snapshot(result, tmp_settings)
    meta = json.loads(handle.meta_file.read_text(encoding="utf-8"))
    assert retention_days_for("T-1", tmp_settings) is None
    assert meta["retention_days"] == "[확인필요: 보존 기간]"
    assert "배포" in meta["purge_owner"]


def test_retention_is_read_from_settings(dataset_settings: Settings) -> None:
    settings = dataset_settings.model_copy(
        update={"dataset_snapshot_retention_days": {"T-4": 30}}
    )
    assert retention_days_for("T-4", settings) == 30


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_live_reader_says_what_is_missing_instead_of_guessing(
    path_id: str, dataset_settings: Settings
) -> None:
    spec = spec_of(path_id)
    assert missing_inputs_for(spec, dataset_settings)
    with pytest.raises(SourceUnavailable):
        read_path(path_id, LiveSourceReader(dataset_settings), {}, None, dataset_settings)


def test_live_reader_refuses_non_relational_storage_after_config_arrives(
    dataset_settings: Settings,
) -> None:
    """제품이 정해지지 않은 벡터 · 캐시 저장소는 읽지 못한다고 알림."""
    vector_path = next(
        path_id
        for path_id in PATH_IDS
        if spec_of(path_id).storage_kind is StorageKind.VECTOR
    )
    settings = dataset_settings.model_copy(
        update={
            "dataset_vector_index_url": "vector://placeholder",
            "dataset_physical_query": {
                vector_path: "SELECT 1 FROM t LIMIT %(row_cap)s"
            },
        }
    )
    with pytest.raises(SourceUnavailable):
        read_path(vector_path, LiveSourceReader(settings), {}, None, settings)


def test_report_holds_no_invented_number(tmp_settings: Settings) -> None:
    collected, _ = collect(tmp_settings)
    text = build_report(collected, tmp_settings)
    assert "[확인필요: 원천 오류율 실측값]" in text
    assert NOT_MEASURED in text
    assert "원천 실측이 아님" in text
    for path_id in PATH_IDS:
        assert f"| {path_id} |" in text


def test_report_lists_every_path(tmp_settings: Settings) -> None:
    collected, unread = collect(tmp_settings)
    assert len(collected) == len(PATH_IDS)
    assert any("T-10" in line for line in unread)
