"""D1·D2 청킹과 검색 결과 위치 메타데이터 시험."""

from __future__ import annotations

from app.domain.chunking import chunk_by_clause
from app.infrastructure.chroma_store import MemoryVectorStore


def test_d1_keeps_clause_no_and_adds_section_label():
    chunk = chunk_by_clause(
        "제10조 (안내)\n① 첫 조건",
        {"doc_key": "D1"},
    )[0]

    assert chunk.metadata["section_label"] == "제10조"
    assert chunk.metadata["clause_no"] == "제10조"


def test_d2_adds_section_label_and_removes_legacy_clause_no():
    chunk = chunk_by_clause(
        "## 한빛 모아생활 · D2-C001-B01 · 생활 포인트 적립\n혜택 본문",
        {"doc_key": "D2", "clause_no": "제거할 구버전 값"},
    )[0]

    assert chunk.metadata["section_label"] == (
        "한빛 모아생활 · D2-C001-B01 · 생활 포인트 적립"
    )
    assert "clause_no" not in chunk.metadata


def test_indexer_memory_search_uses_section_label_before_legacy_clause_no():
    store = MemoryVectorStore("test-signature")
    store.upsert(
        ["D2_0000"],
        ["혜택 본문"],
        [[1.0, 0.0]],
        [
            {
                "doc_type": "benefit_guide",
                "access_level": "public",
                "section_label": "한빛 모아생활 · 생활 포인트 적립",
                "clause_no": "사용하면 안 되는 구버전 값",
            }
        ],
    )

    hit = store.search([1.0, 0.0], 1, {})[0]
    assert hit["location"] == "한빛 모아생활 · 생활 포인트 적립"


def test_indexer_memory_search_does_not_create_empty_turn_label():
    store = MemoryVectorStore("test-signature")
    store.upsert(
        ["EMPTY"],
        ["본문"],
        [[1.0]],
        [{"doc_type": "regulation", "access_level": "public"}],
    )

    assert store.search([1.0], 1, {})[0]["location"] == ""
