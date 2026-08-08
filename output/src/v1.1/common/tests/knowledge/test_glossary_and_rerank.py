"""K-3 적용 지점과 재정렬 시험.

사전을 다시 만들지 않고 데이터 준비 묶음의 파일 1벌을 그대로 쓰는지 함께 확인함.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.config import Settings, load_settings
from common.knowledge import (
    RERANK_AXES,
    RERANK_WEIGHTS_OPEN_TAG,
    RerankFactors,
    display_labels,
    expand_query_tags,
    load_allergen_glossary,
    load_food_tag_glossary,
    lookup,
    rerank,
)

KNOWLEDGE_ROOT = Path(__file__).resolve().parents[2] / "knowledge"


def test_glossary_is_not_rebuilt_here() -> None:
    """사전 파일이나 매핑을 이 묶음에 다시 적지 않았음."""
    for path in sorted(KNOWLEDGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "glossary_food_tags.csv" not in text
        assert "glossary_allergen_codes.csv" not in text
    assert not list(KNOWLEDGE_ROOT.rglob("*.csv"))


def test_query_expansion_keeps_both_when_a_tag_maps_twice(
    knowledge_settings: Settings,
) -> None:
    """ⓐ 1:N 충돌 — 양쪽 후보를 모두 남김."""
    glossary = load_food_tag_glossary(knowledge_settings)
    result = expand_query_tags(["한식"], glossary, settings=knowledge_settings)
    assert result.applied
    assert "한식" in result.expanded


def test_unmapped_tag_is_not_put_into_the_filter(knowledge_settings: Settings) -> None:
    """ⓐ 미등록어 — 필터에 넣지 않고 기록만 남김."""
    glossary = load_food_tag_glossary(knowledge_settings)
    result = expand_query_tags(["없는태그"], glossary, settings=knowledge_settings)
    assert result.unmapped == ("없는태그",)
    assert "없는태그" not in result.expanded
    assert glossary.unmapped_log


def test_expansion_is_skipped_when_the_setting_says_so(
    knowledge_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUNCHPICK_KNOWLEDGE_QUERY_EXPANSION_ENABLED", "false")
    settings = load_settings()
    glossary = load_food_tag_glossary(settings)
    result = expand_query_tags(["한식"], glossary, settings=settings)
    assert not result.applied
    assert result.expanded == ("한식",)


def test_display_labels_only_pass_usable_terms(knowledge_settings: Settings) -> None:
    glossary = load_food_tag_glossary(knowledge_settings)
    assert display_labels(["한식", "없는태그"], glossary) == ("한식",)


def test_allergen_glossary_apply_point_is_before_the_model(
    knowledge_settings: Settings,
) -> None:
    """ⓑ 적용 지점이 결정론 단계임을 설정으로 확인함."""
    points = knowledge_settings.knowledge_glossary_apply_points
    assert "결정론" in points["allergen_code"]
    assert load_allergen_glossary(knowledge_settings).open_row_count > 0


def test_rerank_axes_match_the_design() -> None:
    assert RERANK_AXES == (
        "preference_similarity",
        "distance",
        "repeat_avoidance",
        "confidence",
    )


def _sample_result(settings: Settings, reader):
    return lookup("T-5", "R-14", reader, params={"member_id": "M000000"}, settings=settings)


def test_rerank_does_not_reorder_without_weights(
    knowledge_settings: Settings, seed_reader
) -> None:
    """가중치가 ⑤에 없으므로 순서를 바꾸지 않고 사유를 남김. 숫자를 지어내지 않음."""
    result = _sample_result(knowledge_settings, seed_reader)
    before = [candidate.source.locator for candidate in result.candidates]
    reranked = rerank(result, settings=knowledge_settings)
    after = [candidate.source.locator for candidate in reranked.candidates]
    assert before == after
    assert any(RERANK_WEIGHTS_OPEN_TAG in note for note in reranked.notes)


def test_rerank_reorders_once_weights_are_given(
    knowledge_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """가중치가 오면 코드 수정 없이 순서가 바뀜(가중치는 설정에만 있음)."""
    monkeypatch.setenv(
        "LUNCHPICK_KNOWLEDGE_RERANK_WEIGHTS",
        '{"preference_similarity": 1.0, "distance": -0.01}',
    )
    settings = load_settings()
    from common.dataset import SeedSourceReader

    reader = SeedSourceReader(settings)
    result = _sample_result(settings, reader)
    keys = [candidate.source.locator for candidate in result.candidates]
    factors = {
        key: RerankFactors(preference_similarity=float(index), distance=0.0)
        for index, key in enumerate(keys)
    }
    reranked = rerank(result, factors, settings=settings)
    after = [candidate.source.locator for candidate in reranked.candidates]
    assert after[0] == keys[-1]
    assert len(after) == settings.knowledge_rerank_keep
    assert reranked.traces[-1].stage == "재정렬"
    assert reranked.traces[-1].before != reranked.traces[-1].after


def test_rerank_refuses_an_axis_outside_the_design(
    knowledge_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUNCHPICK_KNOWLEDGE_RERANK_WEIGHTS", '{"brand_new_axis": 1.0}')
    settings = load_settings()
    from common.dataset import SeedSourceReader

    result = _sample_result(settings, SeedSourceReader(settings))
    with pytest.raises(ValueError):
        rerank(result, {}, settings=settings)


def test_rerank_is_skipped_when_disabled(
    knowledge_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUNCHPICK_KNOWLEDGE_RERANK_ENABLED", "false")
    settings = load_settings()
    from common.dataset import SeedSourceReader

    result = _sample_result(settings, SeedSourceReader(settings))
    reranked = rerank(result, settings=settings)
    assert any("쓰지 않기로" in note for note in reranked.notes)
