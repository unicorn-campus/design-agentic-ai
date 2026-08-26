from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from help_desk_dataset.glossary import Glossary
from pgvector.psycopg import register_vector

from .results import Evidence, SearchResult
from .specs import RagSpec


class EmbeddingClient(Protocol):
    def embed_query(self, text: str, *, model: str, dimensions: int) -> Sequence[float]: ...


class PgVectorHybridRetriever:
    def __init__(
        self,
        spec: RagSpec,
        embedding_client: EmbeddingClient,
        connection_factory: Callable[[str], Any],
        glossary: Glossary,
    ) -> None:
        self._spec = spec
        self._embedding_client = embedding_client
        self._connection_factory = connection_factory
        self._glossary = glossary

    def search(self, query: str) -> SearchResult:
        normalized = self._glossary.normalize(query)
        if normalized.status == "정규화" or normalized.status == "둘 다 확장":
            terms = tuple(dict.fromkeys((query, *normalized.canonical_terms)))
        else:
            terms = (query,)
        all_rows: dict[str, Evidence] = {}
        for term in terms:
            for evidence in self._search_one(term, query, normalized.canonical_terms):
                previous = all_rows.get(evidence.source)
                if previous is None or evidence.score > previous.score:
                    all_rows[evidence.source] = evidence
        ranked = sorted(all_rows.values(), key=lambda item: item.score, reverse=True)
        kept = tuple(item for item in ranked if item.score >= self._spec.filter_score)
        if not kept:
            return SearchResult.empty("후보 수 0건")
        return SearchResult(evidence_refs=kept[: self._spec.top_k])

    def _search_one(
        self,
        term: str,
        original: str,
        canonical_terms: tuple[str, ...],
    ) -> tuple[Evidence, ...]:
        vector = self._embedding_client.embed_query(
            term,
            model=self._spec.embedding_model,
            dimensions=self._spec.embedding_dimensions,
        )
        table = self._spec.table
        statement = f"""
            WITH semantic AS (
                SELECT chunk_id, content, source_uri, source_location,
                       ROW_NUMBER() OVER (ORDER BY embedding <=> %(embedding)s) AS rank,
                       1 - (embedding <=> %(embedding)s) AS raw_score
                FROM {table}
                WHERE 1 - (embedding <=> %(embedding)s) >= %(minimum_score)s
                ORDER BY embedding <=> %(embedding)s
                LIMIT %(candidate_count)s
            ), keyword AS (
                SELECT chunk_id, content, source_uri, source_location,
                       ROW_NUMBER() OVER (
                           ORDER BY ts_rank(search_vector, plainto_tsquery('simple', %(query)s)) DESC
                       ) AS rank
                FROM {table}
                WHERE search_vector @@ plainto_tsquery('simple', %(query)s)
                LIMIT %(candidate_count)s
            )
            SELECT COALESCE(s.chunk_id, k.chunk_id) AS chunk_id,
                   COALESCE(s.content, k.content) AS content,
                   COALESCE(s.source_uri, k.source_uri) AS source_uri,
                   COALESCE(s.source_location, k.source_location) AS source_location,
                   COALESCE(s.raw_score, 0.0) AS score,
                   COALESCE(1.0 / (%(rrf_k)s + s.rank), 0.0)
                     + COALESCE(1.0 / (%(rrf_k)s + k.rank), 0.0) AS fusion_score
            FROM semantic s FULL OUTER JOIN keyword k USING (chunk_id)
            ORDER BY fusion_score DESC
            LIMIT %(top_k)s
        """
        parameters = {
            "embedding": list(vector),
            "query": term,
            "candidate_count": self._spec.top_k,
            "minimum_score": self._spec.filter_score,
            "rrf_k": self._spec.rrf_k,
            "top_k": self._spec.top_k,
        }
        with self._connection_factory(self._spec.dsn) as connection:
            register_vector(connection)
            connection.execute("SET LOCAL hnsw.ef_search = %s", (self._spec.hnsw_ef_search,))
            rows = connection.execute(statement, parameters).fetchall()
        return tuple(
            Evidence(
                content=str(row[1]),
                source=f"{row[2]}#{row[3]}",
                score=float(row[4]),
                original_term=original,
                canonical_terms=canonical_terms,
            )
            for row in rows
        )


def build_index_statements(
    spec: RagSpec,
    target_table: str,
    indexed_chunk_count: int,
) -> tuple[str, ...]:
    if spec.unresolved():
        raise ValueError("승인 문서 원천 건수와 기준일 확정 전에는 색인을 만들 수 없음")
    from .specs import safe_identifier

    table = safe_identifier(target_table)
    statements = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        (
            f"CREATE TABLE {table} ("
            "chunk_id text PRIMARY KEY, document_id text NOT NULL, content text NOT NULL, "
            "source_uri text NOT NULL, source_location text NOT NULL, baseline_date date NOT NULL, "
            f"embedding vector({spec.embedding_dimensions}) NOT NULL, "
            "search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED)"
        ),
        f"CREATE INDEX {table}_search_gin ON {table} USING gin (search_vector)",
    ]
    if indexed_chunk_count >= spec.hnsw_min_chunks:
        statements.append(
            f"CREATE INDEX {table}_embedding_hnsw ON {table} USING hnsw "
            f"(embedding vector_cosine_ops) WITH (m={spec.hnsw_m}, "
            f"ef_construction={spec.hnsw_ef_construction})"
        )
    return tuple(statements)
