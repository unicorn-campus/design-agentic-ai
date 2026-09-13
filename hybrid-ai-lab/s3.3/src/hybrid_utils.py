"""Hybrid Search에서 공통으로 사용하는 강사 제공 함수."""

from functools import lru_cache

from rank_bm25 import BM25Okapi

from .s32_bridge import load_s32_module


ROLE_ACCESS = {
    "agent": {"public", "internal"},
    "auditor": {"public", "internal", "restricted"},
}


@lru_cache(maxsize=1)
def get_bm25_index():
    """ChromaDB의 전체 청크를 읽고 BM25 색인을 한 번만 생성함."""
    helpers = load_s32_module("helpers")
    collection = helpers.get_collection("card_docs")
    records = collection.get(include=["documents", "metadatas"])

    chunks = {}
    tokenized_documents = []
    chunk_ids = []
    for chunk_id, text, metadata in zip(
        records["ids"], records["documents"], records["metadatas"]
    ):
        chunk_ids.append(chunk_id)
        tokenized_documents.append(text.split())
        chunks[chunk_id] = {
            "text": text,
            "metadata": {**dict(metadata or {}), "chunk_id": chunk_id},
        }

    if not chunk_ids:
        return chunks, chunk_ids, None
    return chunks, chunk_ids, BM25Okapi(tokenized_documents)


def get_top_chunk_ids(scores, chunk_ids: list[str], count: int) -> set[str]:
    """점수가 높은 청크 ID를 count개까지 반환함."""
    ranked_positions = sorted(
        range(len(chunk_ids)), key=lambda position: scores[position], reverse=True
    )
    return {chunk_ids[position] for position in ranked_positions[:count]}


def map_scores_to_chunk_ids(scores, chunk_ids: list[str]) -> dict[str, float]:
    """BM25 점수 배열을 ``청크 ID: 점수`` 형태로 바꿈."""
    return {
        chunk_id: float(scores[position])
        for position, chunk_id in enumerate(chunk_ids)
    }


def normalize_scores(scores_by_id: dict[str, float], candidate_ids: set[str]) -> dict[str, float]:
    """후보 집합 안에서 점수를 0~1로 변환하고, 점수가 없는 후보에는 0을 사용함."""
    values = [float(scores_by_id.get(chunk_id, 0.0)) for chunk_id in candidate_ids]
    if not values:
        return {}
    lowest, highest = min(values), max(values)
    if highest == lowest:
        return {chunk_id: 0.0 for chunk_id in candidate_ids}
    return {
        chunk_id: (float(scores_by_id.get(chunk_id, 0.0)) - lowest) / (highest - lowest)
        for chunk_id in candidate_ids
    }


def apply_filters(
    scores_by_id: dict[str, float],
    chunks: dict,
    filters: dict | None,
    user_role: str,
) -> dict[str, float]:
    """BM25에서 새로 들어온 후보에도 권한과 메타데이터 조건을 적용함."""
    allowed_access = ROLE_ACCESS[user_role]
    filtered = {}
    for chunk_id, score in scores_by_id.items():
        metadata = chunks[chunk_id]["metadata"]
        if metadata.get("access_level") not in allowed_access:
            continue
        if filters and any(metadata.get(key) != value for key, value in filters.items()):
            continue
        filtered[chunk_id] = score
    return filtered


def to_hits(scores_by_id: dict[str, float], chunks: dict, top_k: int):
    """최종 점수순으로 정렬하여 S3.2의 Hit 목록으로 변환함."""
    Hit = load_s32_module("models").Hit
    ranked = sorted(scores_by_id.items(), key=lambda item: (-item[1], item[0]))[:top_k]
    return [
        Hit(
            text=chunks[chunk_id]["text"],
            score=round(score, 6),
            metadata=chunks[chunk_id]["metadata"],
        )
        for chunk_id, score in ranked
    ]
