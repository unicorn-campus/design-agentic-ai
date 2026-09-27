"""Retriever용 Chroma 조회와 시험용 메모리 저장소."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..application.ports import VectorStorePort
from ..application.state import Hit
from ..domain.location import resolve_location
from ..domain.search_filter import MetadataFilter
from ..domain.vector_search import (
    DEFAULT_VECTOR_SEARCH_OPTIONS,
    VectorSearchOptions,
    maximal_marginal_relevance_indices,
)


def _to_hit(chunk_id: str, score: float, text: str, metadata: dict) -> Hit:
    metadata = {**dict(metadata or {}), "chunk_id": chunk_id}
    location = resolve_location(metadata)
    return Hit(
        chunk_id=chunk_id,
        score=round(score, 3),
        vector_score=round(score, 3),
        access_level=str(metadata.get("access_level", "")),
        source=str(metadata.get("source", "")),
        location=str(location),
        text=text,
        metadata=metadata,
    )


def _matches(metadata: dict, metadata_filter: MetadataFilter) -> bool:
    for key, allowed in metadata_filter.allowed_values:
        if metadata.get(key) not in allowed:
            return False
    for key, expected in metadata_filter.equalities:
        if metadata.get(key) != expected:
            return False
    return True


def _to_chroma_where(metadata_filter: MetadataFilter) -> dict[str, Any]:
    clauses: list[dict[str, Any]] = [
        {key: {"$in": list(allowed)}}
        for key, allowed in metadata_filter.allowed_values
    ]
    clauses.extend({key: value} for key, value in metadata_filter.equalities)
    if not clauses:
        return {}
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


class MemoryVectorStore(VectorStorePort):
    def __init__(self, signature: str = "smoke-sha256-bigram-v1") -> None:
        self.signature = signature
        self._rows: dict[str, tuple[str, list[float], dict]] = {}

    def upsert(self, ids, texts, embeddings, metadatas) -> None:
        if not (len(ids) == len(texts) == len(embeddings) == len(metadatas)):
            raise ValueError("upsert 입력 배열 길이 불일치")
        for chunk_id, text, embedding, metadata in zip(ids, texts, embeddings, metadatas):
            self._rows[chunk_id] = (text, list(embedding), {**metadata, "chunk_id": chunk_id})

    def search(
        self,
        query_embedding: list[float],
        k: int,
        metadata_filter: MetadataFilter,
        options: VectorSearchOptions = DEFAULT_VECTOR_SEARCH_OPTIONS,
    ) -> list[Hit]:
        if k <= 0:
            return []
        rows: list[tuple[Hit, list[float]]] = []
        for chunk_id, (text, embedding, metadata) in self._rows.items():
            if not _matches(metadata, metadata_filter):
                continue
            dot = sum(left * right for left, right in zip(query_embedding, embedding))
            denominator = math.sqrt(
                sum(value * value for value in query_embedding)
                * sum(value * value for value in embedding)
            ) or 1.0
            rows.append((_to_hit(chunk_id, dot / denominator, text, metadata), embedding))
        rows.sort(key=lambda row: (-row[0].score, row[0].chunk_id))
        if options.strategy == "similarity":
            return [hit for hit, _embedding in rows[:k]]

        candidates = rows[: options.fetch_k(k)]
        selected = maximal_marginal_relevance_indices(
            query_embedding,
            [embedding for _hit, embedding in candidates],
            k=k,
            lambda_mult=options.lambda_mult,
        )
        return [candidates[index][0] for index in selected]

    def describe(self) -> dict[str, Any]:
        first = next(iter(self._rows.values()), None)
        return {
            "count": len(self._rows),
            "dimension": len(first[1]) if first else 0,
            "signature": self.signature,
        }

    def count(self) -> int:
        return len(self._rows)

    def check_signature(self, expected: str) -> bool:
        return self.signature == expected


class ChromaVectorStore(VectorStorePort):
    def __init__(self, path: Path, collection: str, signature: str) -> None:
        import chromadb

        self.signature = signature
        client = chromadb.PersistentClient(path=str(path))
        self._collection = client.get_or_create_collection(
            name=collection,
            metadata={"embedding_model_signature": signature, "hnsw:space": "cosine"},
            configuration={"hnsw": {"space": "cosine"}},
        )

    def search(
        self,
        query_embedding: list[float],
        k: int,
        metadata_filter: MetadataFilter,
        options: VectorSearchOptions = DEFAULT_VECTOR_SEARCH_OPTIONS,
    ) -> list[Hit]:
        if k <= 0:
            return []
        where = _to_chroma_where(metadata_filter)
        include = ["documents", "metadatas", "distances"]
        if options.strategy == "mmr":
            include.append("embeddings")
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=options.fetch_k(k),
            where=where or None,  # Chroma 메타데이터 조건으로 검색 문서를 제한하며, 빈 조건은 None으로 보내 필터를 적용하지 않음
            include=include,  # MMR은 후보끼리의 유사도 계산을 위해 임베딩도 함께 조회함
        )
        candidates = [
            _to_hit(chunk_id, 1.0 - float(distance), text, metadata)
            for chunk_id, text, metadata, distance in zip(
                result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]
        if options.strategy == "similarity":
            return candidates
        if not candidates:
            return []

        embedding_rows = result.get("embeddings")
        if embedding_rows is None or len(embedding_rows) == 0:
            raise RuntimeError("Chroma MMR 검색 결과에 후보 임베딩이 없음")
        candidate_embeddings = embedding_rows[0]
        if len(candidate_embeddings) != len(candidates):
            raise RuntimeError("Chroma MMR 후보와 임베딩 수가 일치하지 않음")
        selected = maximal_marginal_relevance_indices(
            query_embedding,
            candidate_embeddings,
            k=k,
            lambda_mult=options.lambda_mult,
        )
        return [candidates[index] for index in selected]

    def upsert(self, ids, texts, embeddings, metadatas) -> None:
        self._collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def describe(self) -> dict[str, Any]:
        sample = self._collection.get(limit=1, include=["embeddings"])
        embeddings = sample.get("embeddings")
        dimension = len(embeddings[0]) if embeddings is not None and len(embeddings) else 0
        metadata = self._collection.metadata or {}
        return {
            "count": int(self._collection.count()),
            "dimension": dimension,
            "signature": metadata.get("embedding_model_signature") or metadata.get("lab_embedding", ""),
        }

    def count(self) -> int:
        return int(self._collection.count())

    def check_signature(self, expected: str) -> bool:
        metadata = self._collection.metadata or {}
        signature = metadata.get("embedding_model_signature") or metadata.get("lab_embedding")
        return signature == expected and metadata.get("hnsw:space", "cosine") == "cosine"


def create_vector_store(
    *,
    backend: str,
    path: Path,
    collection: str,
    signature: str,
) -> VectorStorePort:
    """저장소 이름을 프로젝트 포트의 구현체로 변환함."""

    if backend == "memory":
        return MemoryVectorStore(signature)
    if backend == "chroma":
        return ChromaVectorStore(path, collection, signature)
    raise ValueError(f"지원하지 않는 벡터 저장소 백엔드: {backend}")
