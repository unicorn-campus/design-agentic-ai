"""반드시 넣을 시험 5 — 사전에 없는 낱말은 원문이 유지되고 기록이 1건 남음."""

from __future__ import annotations

import pytest

from common.config import Settings
from common.dataset.glossary import (
    GlossaryKind,
    allergen_codes_for,
    load_glossary,
    to_canonical,
    unmapped_report,
)


@pytest.mark.parametrize("kind", list(GlossaryKind))
def test_glossary_file_loads(kind: GlossaryKind, dataset_settings: Settings) -> None:
    glossary = load_glossary(kind, dataset_settings)
    assert glossary.terms, f"{kind.value} 사전이 비어 있음"
    assert glossary.source_file.exists()


@pytest.mark.parametrize("kind", list(GlossaryKind))
def test_unknown_term_keeps_the_original_and_logs_once(
    kind: GlossaryKind, dataset_settings: Settings
) -> None:
    """시험 5 — 원문이 그대로 나오고 기록이 정확히 1건 남음."""
    glossary = load_glossary(kind, dataset_settings)
    result = to_canonical(glossary, "사전에없는낱말")
    assert result.matched is False
    assert result.passthrough == "사전에없는낱말"
    assert result.canonical_terms == ()
    assert len(glossary.unmapped_log) == 1
    assert glossary.unmapped_log[0].term == "사전에없는낱말"
    assert glossary.unmapped_log[0].handling


def test_known_term_maps_to_the_canonical_word(dataset_settings: Settings) -> None:
    glossary = load_glossary(GlossaryKind.FOOD_TAG, dataset_settings)
    assert to_canonical(glossary, "#한식").canonical_terms == ("한식",)
    assert to_canonical(glossary, "찌개").canonical_terms == ("국물",)
    assert glossary.unmapped_log == []


def test_open_rows_are_not_used_as_canonical_words(dataset_settings: Settings) -> None:
    """대표어 자리가 비어 있는 행은 매칭에 쓰이지 않음."""
    glossary = load_glossary(GlossaryKind.FOOD_TAG, dataset_settings)
    assert glossary.open_row_count > 0
    for term in glossary.usable_terms:
        assert not term.is_open


def test_allergen_mapping_falls_back_safe_when_codes_are_open(
    dataset_settings: Settings,
) -> None:
    """코드 체계가 아직 없으므로 바꾸지 못하고 페일세이프로 감."""
    glossary = load_glossary(GlossaryKind.ALLERGEN_CODE, dataset_settings)
    mapping = allergen_codes_for(glossary, ["땅콩"])
    assert mapping.failsafe is True
    assert mapping.codes == ()
    assert "확인필요" in mapping.reason


def test_allergen_label_is_recognised_even_though_codes_are_open(
    dataset_settings: Settings,
) -> None:
    glossary = load_glossary(GlossaryKind.ALLERGEN_CODE, dataset_settings)
    assert to_canonical(glossary, "피넛").canonical_terms == ("땅콩",)
    assert to_canonical(glossary, "vegan").canonical_terms == ("비건",)


def test_unmapped_report_gathers_every_glossary(dataset_settings: Settings) -> None:
    food = load_glossary(GlossaryKind.FOOD_TAG, dataset_settings)
    allergen = load_glossary(GlossaryKind.ALLERGEN_CODE, dataset_settings)
    to_canonical(food, "없는태그")
    to_canonical(allergen, "없는라벨")
    assert len(unmapped_report([food, allergen])) == 2
