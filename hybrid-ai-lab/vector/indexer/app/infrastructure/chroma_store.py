"""cosine 컬렉션과 메모리 smoke 저장소를 같은 포트로 제공함."""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.domain.validation import sanitize_metadata


class SignatureMismatchError(ValueError):
    pass


def _hit_payload(chunk_id: str, score: float, text: str, metadata: dict) -> dict[str, Any]:
    metadata = {**metadata, "chunk_id": chunk_id}
    location = metadata.get("clause_no") or (
        f"{metadata.get('record_id', '')} 턴 {metadata.get('turn_range', '')}".strip()
    )
    return {
        "chunk_id": chunk_id,
        "score": round(score, 3),
        "vector_score": round(score, 3),
        "rerank_score": None,
        "access_level": str(metadata.get("access_level", "")),
        "source": str(metadata.get("source", "")),
        "location": str(location),
        "text": text,
        "metadata": metadata,
    }


class MemoryVectorStore:
    """시험 전용 코사인 저장소. 영속 Chroma와 동일한 반환 계약임."""

    def __init__(self, signature: str) -> None:
        self.signature = signature
        self._rows: dict[str, tuple[str, list[float], dict]] = {}

    def upsert(self, ids, texts, embeddings, metadatas) -> None:
        if not (len(ids) == len(texts) == len(embeddings) == len(metadatas)):
            raise ValueError("upsert 입력 배열 길이 불일치")
        for chunk_id, text, embedding, metadata in zip(ids, texts, embeddings, metadatas):
            clean = sanitize_metadata({**metadata, "chunk_id": chunk_id})
            self._rows[chunk_id] = (text, list(embedding), clean)

    def reset(self) -> None:
        """명시적인 전체 재적재를 위해 모든 행을 제거하고 서명은 유지함."""

        self._rows.clear()

    def search(self, query_embedding: list[float], k: int, where: dict | None = None) -> list[dict]:
        if k <= 0:
            raise ValueError("k는 양수여야 함")
        rows = []
        for chunk_id, (text, embedding, metadata) in self._rows.items():
            if not _matches_where(metadata, where or {}):
                continue
            dot = sum(left * right for left, right in zip(query_embedding, embedding))
            denom = math.sqrt(sum(x * x for x in query_embedding) * sum(x * x for x in embedding)) or 1.0
            rows.append(_hit_payload(chunk_id, dot / denom, text, metadata))
        return sorted(rows, key=lambda row: (-row["score"], row["chunk_id"]))[:k]

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


def _matches_where(metadata: dict, where: dict) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_matches_where(metadata, clause) for clause in where["$and"])
    return all(
        metadata.get(key) in value["$in"] if isinstance(value, dict) and "$in" in value else metadata.get(key) == value
        for key, value in where.items()
    )


class ChromaVectorStore:
    """Chroma 하부 컬렉션을 사용하며 distance를 cosine 유사도로 변환함."""

    def __init__(self, path: Path, collection: str, signature: str, embedding_function=None) -> None:
        from langchain_chroma import Chroma

        self.signature = signature
        self._store = Chroma(
            collection_name=collection,
            embedding_function=embedding_function,
            persist_directory=str(path),
            collection_configuration={"hnsw": {"space": "cosine"}},
            collection_metadata={"lab_embedding": signature, "hnsw:space": "cosine"},
        )
        self._collection = self._store._collection

    def upsert(self, ids, texts, embeddings, metadatas) -> None:
        clean = [sanitize_metadata({**metadata, "chunk_id": chunk_id}) for chunk_id, metadata in zip(ids, metadatas)]
        self._collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=clean)

    def reset(self) -> None:
        """컬렉션을 삭제하고 동일한 cosine·서명 설정으로 다시 생성함."""

        self._store.reset_collection()
        self._collection = self._store._collection
        if not self.check_signature(self.signature):
            raise SignatureMismatchError("재생성된 Chroma 컬렉션의 서명 또는 cosine 설정 불일치")

    def search(self, query_embedding: list[float], k: int, where: dict | None = None) -> list[dict]:
        result = self._collection.query(query_embeddings=[query_embedding], n_results=k, where=where or None, include=["documents", "metadatas", "distances"])
        rows = []
        for chunk_id, text, metadata, distance in zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]):
            rows.append(_hit_payload(chunk_id, 1.0 - float(distance), text, metadata))
        return rows

    def get_all(self) -> dict:
        return self._collection.get(include=["documents", "metadatas", "embeddings"])

    def count(self) -> int:
        return int(self._collection.count())

    def check_signature(self, expected: str) -> bool:
        metadata = self._collection.metadata or {}
        return metadata.get("lab_embedding") == expected and metadata.get("hnsw:space", "cosine") == "cosine"


def create_vector_store(*, backend: str, path: Path, collection: str, signature: str, embedding_function=None):
    if backend == "memory":
        return MemoryVectorStore(signature)
    if backend not in {"smoke", "sentence-transformers"}:
        raise ValueError(f"지원하지 않는 vector backend: {backend}")
    return ChromaVectorStore(path, collection, signature, embedding_function)
