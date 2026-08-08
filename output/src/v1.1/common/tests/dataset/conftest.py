"""데이터 준비 시험용 설정 대역.

여기 적힌 행 수 상한은 **설계서 ⑤ 3절에서 옮긴 값**이며 시험 고정값으로만 씀.
소스 코드에는 이 숫자가 없음(`test_no_hardcoded_values.py`가 그것을 검사함).
"""

from __future__ import annotations

import json

import pytest

from common.config import Settings, load_settings

from ..conftest import OPTIONAL_ENV, REQUIRED_ENV

# ⑤ 3절 「행 수 상한」 열. 3칸을 준 행은 부분 합을 씀(주석에 계산을 적어 둠).
DATASET_ROW_CAP: dict[str, int] = {
    "T-1": 1,
    "T-2": 1,
    "T-3": 100,  # 최신 1행 · 이력 조회 100행 → 상한은 100
    "T-4": 50,
    "T-5": 100,  # 페이지당
    "T-6": 1000,  # 커서 페이지당
    "T-7": 1,
    "T-8": 200,
    "T-9": 37,  # Top 5 + 추이 12 + 빈도 20
    "T-10": 1,
    "T-11": 1,
    "T-12": 1,
    "T-13": 13,  # 요일 7 + 시간대 5 + 누적 1
    "T-14": 10,
    "T-15": 1,
    "T-16": 500,  # 커서 페이지당
    "T-17": 2,
    "T-18": 3,
}

DATASET_ENV = {
    "LUNCHPICK_DATASET_ROW_CAP": json.dumps(DATASET_ROW_CAP),
    "LUNCHPICK_DATASET_SEED": "7",
}


@pytest.fixture
def dataset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {**REQUIRED_ENV, **OPTIONAL_ENV, **DATASET_ENV}.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def dataset_settings(dataset_env: None) -> Settings:
    return load_settings()
