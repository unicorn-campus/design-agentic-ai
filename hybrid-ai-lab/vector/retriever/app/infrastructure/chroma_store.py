"""Retriever용 Chroma 조회와 시험용 메모리 저장소."""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
from typing import Any

from ..application.state import Hit


def _to_hit(chunk_id: str, score: float, text: str, metadata: dict) -> Hit:
    metadata = {**dict(metadata or {}), "chunk_id": chunk_id}
    location = metadata.get("clause_no") or (
        f"{metadata.get('record_id', '')} 턴 {metadata.get('turn_range', '')}".strip()
    )
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


def _matches(metadata: dict, where: dict) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_matches(metadata, clause) for clause in where["$and"])
    for key, expected in where.items():
        if isinstance(expected, dict) and "$in" in expected:
            if metadata.get(key) not in expected["$in"]:
                return False
        elif metadata.get(key) != expected:
            return False
    return True


class MemoryVectorStore:
    def __init__(self, signature: str = "smoke-sha256-bigram-v1") -> None:
        self.signature = signature
        self._rows: dict[str, tuple[str, list[float], dict]] = {}

    def upsert(self, ids, texts, embeddings, metadatas) -> None:
        if not (len(ids) == len(texts) == len(embeddings) == len(metadatas)):
            raise ValueError("upsert 입력 배열 길이 불일치")
        for chunk_id, text, embedding, metadata in zip(ids, texts, embeddings, metadatas):
            self._rows[chunk_id] = (text, list(embedding), {**metadata, "chunk_id": chunk_id})

    def search(self, query_embedding: list[float], k: int, where: dict) -> list[Hit]:
        rows = []
        for chunk_id, (text, embedding, metadata) in self._rows.items():
            if not _matches(metadata, where):
                continue
            dot = sum(left * right for left, right in zip(query_embedding, embedding))
            denominator = math.sqrt(sum(value * value for value in query_embedding) * sum(value * value for value in embedding)) or 1.0
            rows.append(_to_hit(chunk_id, dot / denominator, text, metadata))
        return sorted(rows, key=lambda hit: (-hit.score, hit.chunk_id))[:k]

    def get_all(self) -> dict:
        ids = sorted(self._rows)
        return {
            "ids": ids,
            "documents": [self._rows[item][0] for item in ids],
            "embeddings": [deepcopy(self._rows[item][1]) for item in ids],
            "metadatas": [deepcopy(self._rows[item][2]) for item in ids],
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
            metadata={"lab_embedding": signature, "hnsw:space": "cosine"},
            configuration={"hnsw": {"space": "cosine"}},
        )

    def search(self, query_embedding: list[float], k: int, where: dict) -> list[Hit]:
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

    def get_all(self) -> dict:
        return self._collection.get(include=["documents", "metadatas", "embeddings"])

    def count(self) -> int:
        return int(self._collection.count())

    def check_signature(self, expected: str) -> bool:
        metadata = self._collection.metadata or {}
        return metadata.get("lab_embedding") == expected and metadata.get("hnsw:space", "cosine") == "cosine"
