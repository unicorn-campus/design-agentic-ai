"""반드시 넣을 시험 5 — 후보 0건일 때 **빈 결과 + 사유**가 나오고 지어낸 근거가 0건임."""

from __future__ import annotations

import pytest

from common.config import Settings
from common.dataset import Origin, PathSpec
from common.knowledge import (
    RetrievalKind,
    RetrievalResult,
    filter_by_attributes,
    lookup,
    search_similar,
)
from common.knowledge.vector_index import VectorIndex
from common.knowledge.result import now_utc


class EmptyReader:
    """아무 행도 못 읽는 원천. 실제로 0건이 나오는 자리를 만들려고 씀."""

    origin = Origin.SEED

    def __init__(self) -> None:
        self.notes_by_path: dict[str, tuple[str, ...]] = {}

    def fetch(self, spec: PathSpec, params, row_cap: int):
        return []


def test_structured_lookup_returns_empty_with_reason(knowledge_settings: Settings) -> None:
    """시험 5 — 조회 0건이면 빈 결과 + 사유임."""
    result = lookup("T-5", "R-14", EmptyReader(), params={"member_id": "M000000"},
                    settings=knowledge_settings)
    assert result.is_empty
    assert result.candidate_count == 0
    assert result.empty_reason
    assert "지어낸 근거를 채우지 않음" in result.empty_reason


def test_empty_vector_index_returns_empty_with_reason(knowledge_settings: Settings) -> None:
    index = VectorIndex(
        index_name="시험용 빈 색인",
        embedding_model="시험용 모델",
        embedding_model_version="시험용 버전",
        product=None,
        corpus_scope=None,
        corpus_as_of=None,
        chunking=None,
        built_at=now_utc(),
        items=(),
    )
    result = search_similar(index, [1.0, 0.0, 0.0], settings=knowledge_settings)
    assert result.is_empty
    assert "0건" in (result.empty_reason or "")


def test_attribute_filter_returns_empty_with_reason(knowledge_settings: Settings) -> None:
    result = filter_by_attributes(
        [{"place_id": "P1", "category_code": "한식", "distance_m": 10}],
        {"category_code": "양식"},
        settings=knowledge_settings,
    )
    assert result.is_empty
    assert "0건" in (result.empty_reason or "")


def test_attribute_filter_refuses_axis_without_a_source(knowledge_settings: Settings) -> None:
    """⑤가 「걸 값이 없음」이라 적은 축으로 거르면 빈 결과 + 사유임."""
    result = filter_by_attributes(
        [{"place_id": "P1", "business_status": "영업"}],
        {"business_status": "영업"},
        settings=knowledge_settings,
    )
    assert result.is_empty
    assert "걸 값이 없는 축" in (result.empty_reason or "")


def test_result_cannot_be_empty_without_a_reason() -> None:
    """사유 없이 조용히 비운 결과는 만들 수 없음."""
    with pytest.raises(ValueError):
        RetrievalResult(route_id="K-1", kind=RetrievalKind.VECTOR_SIMILARITY, candidates=())


def test_result_cannot_have_candidates_and_an_empty_reason(
    knowledge_settings: Settings, seed_reader
) -> None:
    filled = lookup("T-5", "R-14", seed_reader, params={"member_id": "M000000"},
                    settings=knowledge_settings)
    with pytest.raises(ValueError):
        RetrievalResult(
            route_id=filled.route_id,
            kind=filled.kind,
            candidates=filled.candidates,
            empty_reason="억지 사유",
        )


def test_low_confidence_signal_is_zero_candidates(knowledge_settings: Settings) -> None:
    """되묻기 5 — 점수 문턱 대신 후보 수 0건을 신호로 씀. 소스에 문턱 숫자가 없음."""
    assert knowledge_settings.knowledge_low_confidence_signal == "후보 수 0건"
    import common.knowledge as knowledge

    threshold_like = [
        name
        for name in knowledge.__all__
        if "threshold" in name.lower() or "cutoff" in name.lower()
    ]
    assert threshold_like == []
