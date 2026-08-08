"""K-1 색인 만들기 · 유사도 검색기 시험.

색인 이름 · 임베딩 모델 이름 · 버전 · 후보 수가 전부 설정에서 오는지 함께 확인함.
"""

from __future__ import annotations

import pytest

from common.config import Settings, SettingsMissing, load_settings
from common.knowledge import (
    EmbeddingUnavailable,
    UnknownFilterKey,
    build_index,
    cosine_similarity,
    index_name_for,
    plan_index_swap,
    search_similar,
)

ITEMS = [
    {
        "item_key": "F1",
        "locator": "음식카드#1",
        "text": "국물 국물 한식",
        "metadata": {"category_code": "한식", "distance_m": 120, "visited_within_3days": False},
        "payload": {"place_id": "P1", "place_name": "가게1", "distance_m": 120},
    },
    {
        "item_key": "F2",
        "locator": "음식카드#2",
        "text": "매운 매운 매운맛",
        "metadata": {"category_code": "매운맛", "distance_m": 480, "visited_within_3days": False},
        "payload": {"place_id": "P2", "place_name": "가게2", "distance_m": 480},
    },
    {
        "item_key": "F3",
        "locator": "음식카드#3",
        "text": "한식 백반",
        "metadata": {"category_code": "한식", "distance_m": 60, "visited_within_3days": True},
        "payload": {"place_id": "P3", "place_name": "가게3", "distance_m": 60},
    },
]


def test_index_name_comes_from_settings(knowledge_settings: Settings) -> None:
    assert index_name_for("food_item", knowledge_settings) == "food_item_idx"
    assert index_name_for("pref_vector", knowledge_settings) == "pref_vector_idx"


def test_unknown_index_role_fails(knowledge_settings: Settings) -> None:
    with pytest.raises(SettingsMissing):
        index_name_for("no_such_role", knowledge_settings)


def test_rebuild_uses_a_new_name_and_swaps_afterwards(knowledge_settings: Settings) -> None:
    """되묻기 1 — 새 이름으로 만들고 다 되면 갈아 끼움."""
    plan = plan_index_swap("food_item", knowledge_settings)
    assert plan.serving_name == "food_item_idx"
    assert plan.staging_name == "food_item_idx_build"
    assert plan.serving_name != plan.staging_name
    assert len(plan.steps) == 4


def test_build_refuses_without_the_embedding_model(knowledge_settings: Settings, ) -> None:
    """임베딩 모델 이름이 없으면 색인을 만들지 않고 무엇이 없는지 알림."""

    class Anything:
        model_name = "무엇이든"
        model_version = "무엇이든"

        def embed(self, texts):  # pragma: no cover - 부르기 전에 막힘
            raise AssertionError("불려서는 안 됨")

    with pytest.raises(EmbeddingUnavailable) as caught:
        build_index("food_item", ITEMS, Anything(), settings=knowledge_settings)
    assert "확인필요" in str(caught.value)


def test_build_refuses_when_the_caller_uses_another_model(embedding_ready: Settings) -> None:
    class Other:
        model_name = "다른-모델"
        model_version = "다른-버전"

        def embed(self, texts):  # pragma: no cover - 부르기 전에 막힘
            raise AssertionError("불려서는 안 됨")

    with pytest.raises(EmbeddingUnavailable):
        build_index("food_item", ITEMS, Other(), settings=embedding_ready)


def test_build_records_where_each_item_came_from(embedding_ready: Settings, embedder) -> None:
    index = build_index("food_item", ITEMS, embedder, settings=embedding_ready)
    assert index.item_count == len(ITEMS)
    assert index.index_name == "food_item_idx_build"
    assert [item.locator for item in index.items] == ["음식카드#1", "음식카드#2", "음식카드#3"]
    assert index.chunking == "해당 없음 — 항목 1건 = 벡터 1건"


def test_build_with_zero_items_says_so(embedding_ready: Settings, embedder) -> None:
    index = build_index("food_item", [], embedder, settings=embedding_ready)
    assert index.item_count == 0
    assert any("0건" in note for note in index.notes)
    assert embedder.calls == []


def test_metadata_key_outside_the_contract_is_refused(
    embedding_ready: Settings, embedder
) -> None:
    bad = [dict(ITEMS[0], metadata={"price_band": "저가"})]
    with pytest.raises(UnknownFilterKey):
        build_index("food_item", bad, embedder, settings=embedding_ready)


def test_filter_runs_before_similarity(embedding_ready: Settings, embedder) -> None:
    """⑤ K-1 「검색 방식」 — 거르기를 먼저 걸어 조건 밖 항목이 상위에 섞이지 않음."""
    index = build_index("food_item", ITEMS, embedder, settings=embedding_ready)
    result = search_similar(
        index,
        [1.0, 3.0, 1.0],
        metadata_filter={"category_code": "한식"},
        settings=embedding_ready,
    )
    keys = [candidate.source.locator for candidate in result.candidates]
    assert "음식카드#2" not in keys
    assert set(keys) == {"음식카드#1", "음식카드#3"}


def test_recent_visit_axis_removes_the_item_at_search_time(
    embedding_ready: Settings, embedder
) -> None:
    """못 볼 항목을 검색 단계에서 걸러 냄 — 뽑아 놓고 나중에 지우지 않음."""
    index = build_index("food_item", ITEMS, embedder, settings=embedding_ready)
    result = search_similar(
        index,
        [1.0, 1.0, 1.0],
        metadata_filter={"visited_within_3days": True},
        settings=embedding_ready,
    )
    assert [candidate.source.locator for candidate in result.candidates] == ["음식카드#3"]


def test_scores_are_sorted_descending(embedding_ready: Settings, embedder) -> None:
    index = build_index("food_item", ITEMS, embedder, settings=embedding_ready)
    result = search_similar(index, [1.0, 2.0, 1.0], settings=embedding_ready)
    scores = [candidate.score for candidate in result.candidates]
    assert scores == sorted(scores, reverse=True)


def test_top_k_comes_from_settings(embedding_ready: Settings, embedder) -> None:
    index = build_index("food_item", ITEMS, embedder, settings=embedding_ready)
    result = search_similar(index, [1.0, 1.0, 1.0], settings=embedding_ready)
    assert result.candidate_count <= embedding_ready.knowledge_top_k_value()


def test_search_refuses_without_top_k(embedding_ready: Settings, embedder,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
    index = build_index("food_item", ITEMS, embedder, settings=embedding_ready)
    monkeypatch.delenv("LUNCHPICK_KNOWLEDGE_TOP_K", raising=False)
    thin = load_settings()
    with pytest.raises(SettingsMissing):
        search_similar(index, [1.0, 1.0, 1.0], settings=thin)


def test_search_refuses_a_filter_key_outside_the_contract(
    embedding_ready: Settings, embedder
) -> None:
    index = build_index("food_item", ITEMS, embedder, settings=embedding_ready)
    with pytest.raises(UnknownFilterKey):
        search_similar(index, [1.0, 1.0, 1.0], metadata_filter={"price_band": "저가"},
                       settings=embedding_ready)


def test_cosine_similarity_basics() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        cosine_similarity([1.0], [1.0, 0.0])
    with pytest.raises(ValueError):
        cosine_similarity([0.0, 0.0], [1.0, 0.0])
