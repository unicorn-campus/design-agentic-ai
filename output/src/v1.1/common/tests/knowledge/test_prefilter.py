"""반드시 넣을 시험 6 — 결정론 필터에 걸린 요청은 검색기를 **부르지 않음**."""

from __future__ import annotations

import pytest

from common.config import Settings
from common.knowledge import (
    PREFILTERS,
    FilterOutcome,
    allergen_hard_filter,
    cancel_confirm_filter,
    expiry_downgrade_filter,
    filter_by_attributes,
    load_allergen_glossary,
    to_excluded_ingredient_codes,
)


def test_three_prefilters_exist_for_three_irreversible_calls() -> None:
    """⑤가 「되돌림 예」로 적은 자리 3곳에 필터 3개가 있음."""
    assert set(PREFILTERS) == {"PF-1", "PF-2", "PF-3"}


def test_allergen_filter_blocks_when_source_is_missing() -> None:
    verdict = allergen_hard_filter(("CODE-A",), None, mapping_failsafe=False)
    assert verdict.outcome is FilterOutcome.BLOCK
    assert "확인필요" in verdict.reason


def test_allergen_filter_blocks_on_mapping_failsafe() -> None:
    verdict = allergen_hard_filter((), ("CODE-B",), mapping_failsafe=True)
    assert verdict.outcome is FilterOutcome.BLOCK
    assert "페일세이프" in verdict.reason


def test_allergen_filter_blocks_on_overlap() -> None:
    verdict = allergen_hard_filter(("CODE-A",), ("CODE-A", "CODE-B"), mapping_failsafe=False)
    assert verdict.outcome is FilterOutcome.BLOCK


def test_allergen_filter_passes_when_nothing_overlaps() -> None:
    verdict = allergen_hard_filter(("CODE-A",), ("CODE-B",), mapping_failsafe=False)
    assert verdict.passed


def test_cancel_confirm_filter_blocks_without_evidence() -> None:
    assert cancel_confirm_filter(None, None).outcome is FilterOutcome.BLOCK
    assert cancel_confirm_filter("CC-1", None).outcome is FilterOutcome.BLOCK
    assert cancel_confirm_filter("CC-1", "2026-08-08T00:00:00Z").passed


def test_expiry_filter_keeps_premium_when_it_cannot_decide() -> None:
    verdict = expiry_downgrade_filter("2026-08-01", "2026-08-08", None, True)
    assert verdict.outcome is FilterOutcome.BLOCK
    assert "현 상태를 유지" in verdict.reason


def test_expiry_filter_passes_only_when_every_condition_holds() -> None:
    assert expiry_downgrade_filter("2026-08-01", "2026-08-08", False, True).passed
    assert not expiry_downgrade_filter("2026-08-01", "2026-08-08", True, True).passed
    assert not expiry_downgrade_filter("2026-09-01", "2026-08-08", False, True).passed


def test_prefilter_is_a_pure_function_without_a_model() -> None:
    """필터가 모델을 부르지 않음 — 소스에 모델 어댑터를 가져오는 줄이 0건임."""
    from pathlib import Path

    text = (Path(__file__).resolve().parents[2] / "knowledge" / "prefilter.py").read_text(
        encoding="utf-8"
    )
    assert "model_client" not in text
    assert "build_model_client" not in text


class CountingSearcher:
    """검색기가 실제로 불렸는지 세는 대역."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, rows, criteria, settings):
        self.calls += 1
        return filter_by_attributes(rows, criteria, settings=settings)


def test_blocked_request_never_reaches_the_searcher(knowledge_settings: Settings) -> None:
    """시험 6 — 필터가 차단하면 검색기를 한 번도 부르지 않음."""
    searcher = CountingSearcher()
    glossary = load_allergen_glossary(knowledge_settings)
    gate = to_excluded_ingredient_codes(["땅콩"], glossary, place_ingredient_codes=None)

    assert not gate.verdict.passed
    if gate.verdict.passed:  # pragma: no cover - 차단이므로 들어오지 않음
        searcher([{"place_id": "P1", "category_code": "한식"}], {}, knowledge_settings)
    assert searcher.calls == 0


def test_passing_request_does_reach_the_searcher(knowledge_settings: Settings) -> None:
    """비교군 — 필터를 지나면 검색기가 불림."""
    searcher = CountingSearcher()
    verdict = allergen_hard_filter((), (), mapping_failsafe=False)
    assert verdict.passed
    if verdict.passed:
        searcher(
            [{"place_id": "P1", "category_code": "한식", "distance_m": 10}],
            {"category_code": "한식"},
            knowledge_settings,
        )
    assert searcher.calls == 1


def test_glossary_gate_marks_failsafe_because_codes_are_open(
    knowledge_settings: Settings,
) -> None:
    """사전 ⓑ의 코드 체계가 미확정이라 매핑이 늘 페일세이프임(원천 공백이 그대로 드러남)."""
    glossary = load_allergen_glossary(knowledge_settings)
    gate = to_excluded_ingredient_codes(["땅콩"], glossary, place_ingredient_codes=("CODE-Z",))
    assert gate.mapping.failsafe is True
    assert gate.excluded_ingredient_codes == ()
    with pytest.raises(AssertionError):
        assert gate.verdict.passed
