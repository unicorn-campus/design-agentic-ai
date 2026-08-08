"""지식 경로 시험용 설정 대역.

여기 적힌 값은 **설계서 ⑤에서 옮긴 값**이며 시험 고정값으로만 씀.
소스 코드에는 이 숫자·이름이 없음(`test_no_hardcoded_settings.py`가 그것을 검사함).
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import pytest

from common.config import Settings, load_settings

from ..conftest import OPTIONAL_ENV, REQUIRED_ENV
from ..dataset.conftest import DATASET_ENV

# ⑤ 5절 K-1 「인덱스명」 2개.
INDEX_NAME = {"pref_vector": "pref_vector_idx", "food_item": "food_item_idx"}

# ④ 5-3절 메타데이터 필터 키 4축(이름의 주인은 ④임).
METADATA_FILTER_KEYS = [
    "category_code",
    "distance_m",
    "business_status",
    "visited_within_3days",
]

# ⑤ 5절 K-2 「성립 여부」 — 가격대·영업 상태는 원천 미확정이라 부분 성립임.
ATTRIBUTE_AXES = {
    "category_code": "성립",
    "distance_m": "성립",
    "visited_within_3days": "성립",
    "business_status": "부분 성립 — 원천 미확정으로 걸 값이 없음",
}

KNOWLEDGE_ENV = {
    "LUNCHPICK_KNOWLEDGE_INDEX_NAME": json.dumps(INDEX_NAME),
    "LUNCHPICK_KNOWLEDGE_INDEX_BUILD_SUFFIX": "_build",
    "LUNCHPICK_KNOWLEDGE_CORPUS_SCOPE": "음식 카드 마스터 + 추천 후보 식당의 대표 메뉴",
    "LUNCHPICK_KNOWLEDGE_CHUNKING": "해당 없음 — 항목 1건 = 벡터 1건",
    "LUNCHPICK_KNOWLEDGE_SEARCH_MODE": "필터 먼저 · 코사인 유사도 정렬",
    "LUNCHPICK_KNOWLEDGE_TOP_K": "30",
    "LUNCHPICK_KNOWLEDGE_RERANK_ENABLED": "true",
    "LUNCHPICK_KNOWLEDGE_RERANK_KEEP": "3",
    "LUNCHPICK_KNOWLEDGE_METADATA_FILTER_KEYS": json.dumps(METADATA_FILTER_KEYS),
    "LUNCHPICK_KNOWLEDGE_ATTRIBUTE_AXES": json.dumps(ATTRIBUTE_AXES),
    "LUNCHPICK_KNOWLEDGE_RADIUS_M": "500",
    "LUNCHPICK_KNOWLEDGE_SORT_PRIMARY": "distance_m",
    "LUNCHPICK_KNOWLEDGE_GLOSSARY_APPLY_POINTS": json.dumps(
        {
            "food_tag": "질의 확장(온보딩 태그 → 후보 카테고리) + 출력 표기",
            "allergen_code": "결정론 단계 — 모델 호출 앞",
        }
    ),
    "LUNCHPICK_KNOWLEDGE_QUERY_EXPANSION_ENABLED": "true",
    "LUNCHPICK_KNOWLEDGE_RESULT_MERGE": "합치지 않고 경로별로 따로 돌려줌",
    "LUNCHPICK_KNOWLEDGE_LOW_CONFIDENCE_SIGNAL": "후보 수 0건",
}

# 임베딩 모델 이름·버전은 ⑤가 `[확인필요]`로 남긴 값이라 **기본 대역에 넣지 않음.**
# 색인 만들기 시험만 아래 값을 따로 넣어 씀(설계서 값이 아니라 시험 고정값임).
TEST_EMBEDDING_ENV = {
    "LUNCHPICK_EMBEDDING_MODEL": "test-embedding-id",
    "LUNCHPICK_KNOWLEDGE_EMBEDDING_MODEL_VERSION": "test-version",
}


@pytest.fixture
def knowledge_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {
        **REQUIRED_ENV,
        **OPTIONAL_ENV,
        **DATASET_ENV,
        **KNOWLEDGE_ENV,
    }.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def knowledge_settings(knowledge_env: None) -> Settings:
    return load_settings()


@pytest.fixture
def embedding_ready(knowledge_env: None, monkeypatch: pytest.MonkeyPatch) -> Settings:
    for name, value in TEST_EMBEDDING_ENV.items():
        monkeypatch.setenv(name, value)
    return load_settings()


@pytest.fixture
def seed_reader(knowledge_settings: Settings):
    from common.dataset import SeedSourceReader

    return SeedSourceReader(knowledge_settings)


class StubEmbedder:
    """시험용 임베딩 대역. 글자 수를 축으로 쓰는 3차원 벡터를 냄."""

    def __init__(self, model_name: str, model_version: str) -> None:
        self.model_name = model_name
        self.model_version = model_version
        self.calls: list[tuple[str, ...]] = []

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        self.calls.append(tuple(texts))
        return [
            [float(len(text)), float(text.count("국") + 1), float(text.count("매") + 1)]
            for text in texts
        ]


@pytest.fixture
def embedder(embedding_ready: Settings) -> StubEmbedder:
    return StubEmbedder(
        model_name=TEST_EMBEDDING_ENV["LUNCHPICK_EMBEDDING_MODEL"],
        model_version=TEST_EMBEDDING_ENV["LUNCHPICK_KNOWLEDGE_EMBEDDING_MODEL_VERSION"],
    )
