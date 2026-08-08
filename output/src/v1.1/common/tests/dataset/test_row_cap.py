"""반드시 넣을 시험 2 — 상한을 넘겨 달라고 해도 상한까지만 돌려줌."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from common.config import Settings, SettingsMissing, load_settings
from common.dataset.paths import PATH_IDS, PathSpec, spec_of
from common.dataset.readers import READ_FUNCTIONS
from common.dataset.source_port import Origin, read_path

from .conftest import DATASET_ROW_CAP


class GreedyReader:
    """상한을 무시하고 더 많이 돌려주는 짓궂은 원천. 관문이 잘라야 함."""

    origin = Origin.SEED

    def __init__(self, overshoot: int) -> None:
        self.overshoot = overshoot
        self.asked_row_cap: int | None = None

    def fetch(
        self, spec: PathSpec, params: Mapping[str, Any], row_cap: int
    ) -> Sequence[Mapping[str, Any]]:
        self.asked_row_cap = row_cap
        return [
            {column: f"{column}#{index}" for column in spec.columns}
            for index in range(row_cap + self.overshoot)
        ]


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_row_cap_is_enforced_even_when_more_is_asked(
    path_id: str, dataset_settings: Settings
) -> None:
    """시험 2 — 상한보다 큰 수를 달라고 해도 상한까지만 옴."""
    reader = GreedyReader(overshoot=3)
    cap = DATASET_ROW_CAP[path_id]
    result = read_path(path_id, reader, {}, limit=cap * 2 + 1, settings=dataset_settings)
    assert result.row_cap == cap
    assert result.effective_limit == cap
    assert result.row_count == cap
    assert result.truncated is True
    assert reader.asked_row_cap == cap


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_limit_below_cap_is_respected(path_id: str, dataset_settings: Settings) -> None:
    reader = GreedyReader(overshoot=0)
    result = read_path(path_id, reader, {}, limit=1, settings=dataset_settings)
    assert result.effective_limit == 1
    assert result.row_count == 1


def test_path_without_cap_setting_is_not_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """상한을 안 정한 경로는 짐작하지 않고 읽기를 거부함."""
    from ..conftest import OPTIONAL_ENV, REQUIRED_ENV

    for name, value in {**REQUIRED_ENV, **OPTIONAL_ENV}.items():
        monkeypatch.setenv(name, value)
    settings = load_settings()
    with pytest.raises(SettingsMissing):
        read_path("T-1", GreedyReader(0), {}, None, settings)


def test_read_function_count_matches_design_row_count() -> None:
    """⑤ 3절 행 수와 만든 읽기 함수 수가 같음(`경로 불가` 행 0건)."""
    assert set(READ_FUNCTIONS) == set(PATH_IDS)
    assert len(READ_FUNCTIONS) == len(PATH_IDS)


@pytest.mark.parametrize("path_id", PATH_IDS)
def test_reader_receives_only_declared_filter_params(
    path_id: str, dataset_settings: Settings
) -> None:
    spec = spec_of(path_id)
    with pytest.raises(ValueError):
        read_path(
            path_id,
            GreedyReader(0),
            {"없는조건": "x"},
            None,
            dataset_settings,
        )
    assert set(spec.filter_params) == set(spec.filter_params)
