"""Retriever용 Chroma 조회와 시험용 메모리 저장소."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..application.state import Hit
from ..domain.location import resolve_location
from ..domain.search_filter import MetadataFilter


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


class MemoryVectorStore:
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
    ) -> list[Hit]:
        rows = []
        for chunk_id, (text, embedding, metadata) in self._rows.items():
            if not _matches(metadata, metadata_filter):
                continue
            dot = sum(left * right for left, right in zip(query_embedding, embedding))
            denominator = math.sqrt(sum(value * value for value in query_embedding) * sum(value * value for value in embedding)) or 1.0
            rows.append(_to_hit(chunk_id, dot / denominator, text, metadata))
        return sorted(rows, key=lambda hit: (-hit.score, hit.chunk_id))[:k]

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


class ChromaVectorStore:
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
    ) -> list[Hit]:
        where = _to_chroma_where(metadata_filter)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )
        return [
            _to_hit(chunk_id, 1.0 - float(distance), text, metadata)
            for chunk_id, text, metadata, distance in zip(
                result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]

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
):
    """저장소 이름을 프로젝트 포트의 구현체로 변환함."""

    if backend == "memory":
        return MemoryVectorStore(signature)
    if backend == "chroma":
        return ChromaVectorStore(path, collection, signature)
    raise ValueError(f"지원하지 않는 벡터 저장소 백엔드: {backend}")
