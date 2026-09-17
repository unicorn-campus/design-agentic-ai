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


def _resolve_location(metadata: dict[str, Any] | None) -> str:
    values = dict(metadata or {})
    for key in ("section_label", "clause_no"):
        raw_value = values.get(key)
        value = str(raw_value).strip() if raw_value is not None else ""
        if value:
            return value

    raw_record_id = values.get("record_id")
    raw_turn_range = values.get("turn_range")
    record_id = str(raw_record_id).strip() if raw_record_id is not None else ""
    turn_range = str(raw_turn_range).strip() if raw_turn_range is not None else ""
    return " ".join(
        part
        for part in (record_id, f"턴 {turn_range}" if turn_range else "")
        if part
    )


def _hit_payload(chunk_id: str, score: float, text: str, metadata: dict) -> dict[str, Any]:
    metadata = {**metadata, "chunk_id": chunk_id}
    location = _resolve_location(metadata)
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
        # Chroma 생성 파라미터:
        # - collection_name: Chroma 안에서 벡터 묶음을 구분하는 컬렉션 이름
        # - embedding_function: 텍스트를 벡터로 바꿀 함수이며, 이미 만든 벡터를 직접 넣으면 None 사용 가능
        # - persist_directory: Chroma 데이터와 인덱스를 디스크에 영구 저장할 폴더 경로
        # - collection_configuration: HNSW 벡터 인덱스가 코사인 거리를 사용하도록 설정
        #   HNSW(Hierarchical Navigable Small World)는 가까운 벡터끼리 여러 층의 그래프로 연결하는 인덱스임.
        #   검색할 때 모든 벡터를 하나씩 비교하지 않고 그래프를 따라가며 유사한 벡터를 빠르게 찾음.
        # - collection_metadata: 사용한 임베딩 서명과 거리 방식을 컬렉션 정보에 기록하여 나중에 검증
        self._store = Chroma(
            collection_name=collection,
            embedding_function=embedding_function,
            persist_directory=str(path),
            collection_configuration={"hnsw": {"space": "cosine"}},

            #   embedding_model_signature: Chroma 예약어가 아닌 프로젝트 키이며, 모델·정책 서명을 저장함.
            #   hnsw:space: Chroma가 벡터 거리 계산 방식을 확인하는 데 사용하는 설정 키임.
            collection_metadata={"embedding_model_signature": signature, "hnsw:space": "cosine"},
        )
        self._collection = self._store._collection

    def upsert(self, ids, texts, embeddings, metadatas) -> None:
        # sanitize_metadata의 목적:
        # Chroma 메타데이터가 허용하는 str·int·float·bool 값만 그대로 두고 저장 가능한 형태로 정리함.
        # 필수 항목인 access_level과 doc_type을 검사하고, 잘못되었으면 MetadataError를 발생시킴.
        # None 값은 제거하고, list·dict 같은 복합 값은 한글을 유지한 JSON 문자열로 변환하여 내용을 보존함.
        clean = []

        # 같은 위치의 청크 ID와 메타데이터를 한 쌍씩 가져옴.
        for chunk_id, metadata in zip(ids, metadatas):
            # 기존 메타데이터를 복사하고 실제 저장 ID를 chunk_id에 넣음. 기존 chunk_id가 있으면 새 값으로 덮어씀.
            metadata_with_id = {**metadata, "chunk_id": chunk_id}

            # Chroma에 안전하게 저장할 수 있도록 필수값을 검사하고 각 값을 원시값 또는 JSON 문자열로 정리함.
            clean_metadata = sanitize_metadata(metadata_with_id)

            # 정리된 메타데이터를 Chroma upsert에 전달할 최종 목록에 추가함.
            clean.append(clean_metadata)

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
        return (
            metadata.get("embedding_model_signature") == expected
            and metadata.get("hnsw:space", "cosine") == "cosine"
        )


def create_vector_store(
    *,
    embedding_backend: str,
    path: Path,
    collection: str,
    signature: str,
    embedding_function=None,
):
    if embedding_backend == "memory":
        return MemoryVectorStore(signature)
    if embedding_backend not in {"smoke", "sentence-transformers"}:
        raise ValueError(f"지원하지 않는 임베딩 백엔드: {embedding_backend}")
    return ChromaVectorStore(path, collection, signature, embedding_function)
