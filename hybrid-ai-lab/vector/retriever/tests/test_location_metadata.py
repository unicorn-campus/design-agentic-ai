"""신규·구버전 문서 위치 메타데이터 호환 시험."""

from __future__ import annotations

from app.domain.location import resolve_location
from app.infrastructure.bm25_index import BM25Index


class StaticStore:
    def __init__(self, rows: list[tuple[str, str, dict]]):
        self.rows = rows

    def get_all(self) -> dict:
        return {
            "ids": [row[0] for row in self.rows],
            "documents": [row[1] for row in self.rows],
            "metadatas": [row[2] for row in self.rows],
        }


def test_resolve_location_supports_d1_d2_d3_and_legacy_metadata():
    assert resolve_location(
        {"section_label": "제10조 제7항", "clause_no": "제10조 제7항"}
    ) == "제10조 제7항"
    assert resolve_location(
        {"section_label": "한빛 모아생활 · D2-C001-B01 · 생활 포인트 적립"}
    ) == "한빛 모아생활 · D2-C001-B01 · 생활 포인트 적립"
    assert resolve_location(
        {"record_id": "C-20260302-002", "turn_range": "1-4"}
    ) == "C-20260302-002 턴 1-4"
    assert resolve_location({"clause_no": "제10조"}) == "제10조"


def test_resolve_location_does_not_create_empty_turn_label():
    assert resolve_location({}) == ""
    assert resolve_location({"section_label": None, "clause_no": None}) == ""
    assert resolve_location({"record_id": "C-20260302-002"}) == "C-20260302-002"
    assert resolve_location({"turn_range": "1-4"}) == "턴 1-4"


def test_bm25_uses_common_location_resolution():
    index = BM25Index(
        StaticStore(
            [
                (
                    "D2_0000",
                    "혜택 본문",
                    {
                        "section_label": "한빛 모아생활 · 생활 포인트 적립",
                        "clause_no": "사용하면 안 되는 구버전 값",
                        "access_level": "public",
                    },
                )
            ]
        )
    )

    assert index.chunks()["D2_0000"].location == "한빛 모아생활 · 생활 포인트 적립"
