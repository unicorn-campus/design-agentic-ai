"""신규·구버전 문서 위치 메타데이터 호환 시험."""

from __future__ import annotations

import tempfile
from pathlib import Path

import bm25s

from app.domain.corpus import CorpusSnapshot
from app.domain.korean_tokenizer import KoreanTokenizer
from app.domain.location import resolve_location
from app.infrastructure.bm25_index import BM25Index


class StaticCorpusStore:
    def __init__(self, snapshot: CorpusSnapshot):
        self.snapshot = snapshot

    def active_generation(self) -> str:
        return self.snapshot.generation

    def load_active(self) -> CorpusSnapshot:
        return self.snapshot


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
    tokenizer = KoreanTokenizer()
    records = (
        {
            "chunk_id": "D2_0000",
            "text": "혜택 본문",
            "metadata": {
                "section_label": "한빛 모아생활 · 생활 포인트 적립",
                "clause_no": "사용하면 안 되는 구버전 값",
                "access_level": "public",
            },
        },
    )
    with tempfile.TemporaryDirectory() as directory:
        bm25_path = Path(directory) / "bm25"
        retriever = bm25s.BM25()
        retriever.index(tokenizer.tokenize_many(["혜택 본문"]), show_progress=False)
        retriever.save(bm25_path, show_progress=False)
        snapshot = CorpusSnapshot(
            generation="test",
            corpus_sha256="hash",
            records=records,
            bm25_path=bm25_path,
            manifest={
                "generation": "test",
                "corpus_sha256": "hash",
                "tokenizer_signature": tokenizer.signature,
            },
        )
        index = BM25Index(StaticCorpusStore(snapshot), tokenizer)

        assert index.chunks()["D2_0000"].location == "한빛 모아생활 · 생활 포인트 적립"
