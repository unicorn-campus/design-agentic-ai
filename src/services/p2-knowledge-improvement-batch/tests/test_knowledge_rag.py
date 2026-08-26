from __future__ import annotations

from pathlib import Path

import pytest

from help_desk_dataset.glossary import load_glossary
from help_desk_knowledge.indexing import build_chunks, clean_text, extract_sections
from help_desk_knowledge.rag import PgVectorHybridRetriever, build_index_statements
from help_desk_knowledge.specs import RagSpec


class _Embedding:
    def embed_query(self, text: str, *, model: str, dimensions: int) -> list[float]:
        assert model == "text-embedding-3-large"
        assert dimensions == 3072
        return [float(len(text))] * dimensions

    def embed_documents(
        self,
        texts: list[str],
        *,
        model: str,
        dimensions: int,
    ) -> tuple[list[float], ...]:
        return tuple(self.embed_query(text, model=model, dimensions=dimensions) for text in texts)


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows


class _Connection:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows
        self.calls: list[tuple[object, ...]] = []

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, statement: str, parameters: object = None) -> _Cursor:
        self.calls.append((statement, parameters))
        if statement.startswith("SET LOCAL"):
            return _Cursor([])
        return _Cursor(self.rows)


def _spec(source_count: int | None = 12000, baseline_date: str | None = "2026-08-25") -> RagSpec:
    return RagSpec(
        dsn="postgresql://example.invalid/db",
        table="approved_document_chunks",
        index_name="S-1",
        product="PostgreSQL + pgvector(HNSW)",
        source_documents="승인 약관·상품 안내·상담 지침·FAQ",
        source_count=source_count,
        baseline_date=baseline_date,
        extraction="PDF·HTML 텍스트 파서",
        cleaning="민감 필드 제거",
        chunk_tokens=800,
        overlap_tokens=120,
        separator="Markdown 헤더 다음 빈 문단",
        embedding_model="text-embedding-3-large",
        embedding_dimensions=3072,
        hnsw_min_chunks=10000,
        hnsw_m=16,
        hnsw_ef_construction=64,
        hnsw_ef_search=80,
        search_method="hybrid-tsvector-vector",
        fusion_method="RRF",
        rrf_k=60,
        diversity="none",
        top_k=5,
        filter_score=0.35,
    )


@pytest.mark.parametrize("question", ["이용거절", "청구내역", "혜택"])
def test_three_sample_queries_return_count_and_source(monkeypatch: pytest.MonkeyPatch, question: str) -> None:
    monkeypatch.setattr("help_desk_knowledge.rag.register_vector", lambda connection: None)
    rows = [("c-1", f"{question} 안내", "docs://approved", "p1", 0.8)]
    connection = _Connection(rows)
    glossary = load_glossary(
        Path(__file__).parents[1] / "config" / "glossaries" / "카드업무용어.toml"
    )
    retriever = PgVectorHybridRetriever(_spec(), _Embedding(), lambda _: connection, glossary)
    result = retriever.search(question)
    assert len(result.evidence_refs) == 1
    assert result.evidence_refs[0].source == "docs://approved#p1"


def test_zero_candidates_returns_empty_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("help_desk_knowledge.rag.register_vector", lambda connection: None)
    glossary = load_glossary(
        Path(__file__).parents[1] / "config" / "glossaries" / "카드업무용어.toml"
    )
    result = PgVectorHybridRetriever(
        _spec(), _Embedding(), lambda _: _Connection([]), glossary
    ).search("없는 용어")
    assert result.evidence_refs == ()
    assert result.reason == "후보 수 0건"


def test_index_build_is_blocked_while_confirmation_is_missing() -> None:
    with pytest.raises(ValueError, match="원천 건수와 기준일"):
        build_index_statements(_spec(None, None), "approved_document_chunks_next", 0)


def test_hnsw_is_created_only_after_design_threshold() -> None:
    statements = build_index_statements(_spec(), "approved_document_chunks_next", 12000)
    assert sum("USING hnsw" in statement for statement in statements) == 1


def test_html_table_is_extracted_chunked_and_keeps_source(tmp_path: Path) -> None:
    source = tmp_path / "faq.html"
    source.write_text(
        "<h1>FAQ</h1><table><tr><th>질문</th><th>답</th></tr>"
        "<tr><td>이용거절</td><td>확인</td></tr></table>",
        encoding="utf-8",
    )
    sections = extract_sections(source)
    assert "| 질문 | 답 |" in sections[0].text
    chunks = build_chunks([source], _spec(source_count=1), _Embedding())
    assert len(chunks) == 1
    assert chunks[0].source_uri == source.as_uri()
    assert chunks[0].source_location.startswith("html:token=")


def test_sensitive_patterns_and_page_numbers_are_removed() -> None:
    cleaned = clean_text("1\n카드 1234567890123456\nauth_token=secret-value\n승인 안내")
    assert "1234567890123456" not in cleaned
    assert "secret-value" not in cleaned
    assert not cleaned.startswith("1\n")
