"""슬라이드 25: 이해하기 쉬운 Hybrid Search 완성본."""

from .hybrid_utils import (
    apply_filters,
    get_bm25_index,
    get_top_chunk_ids,
    map_scores_to_chunk_ids,
    normalize_scores,
    to_hits,
)
from .s32_bridge import get_search


vector_search = get_search(reference=True)


def search_hybrid(
    query: str,
    top_k: int = 5,
    w_bm25: float = 0.4,
    w_vec: float = 0.6,
    filters: dict | None = None,
    user_role: str = "agent",
):
    """BM25 검색 결과와 Vector 검색 결과를 가중합하여 반환함."""
    if not query.strip():
        raise ValueError("검색 질문이 비어 있음")
    if top_k <= 0:
        raise ValueError("top_k는 양수여야 함")
    if w_bm25 < 0 or w_vec < 0 or w_bm25 + w_vec == 0:
        raise ValueError("검색 가중치는 0 이상이며 합계가 0보다 커야 함")

    chunks, chunk_ids, bm25_index = get_bm25_index()
    if bm25_index is None:
        return []

    candidate_count = top_k * 4

    # (1) Vector 검색: 질문의 의미와 비슷한 청크를 찾음.
    vector_hits = vector_search(query, candidate_count, filters, user_role)

    # (2) BM25 검색: 질문과 같은 단어가 많이 나온 청크에 점수를 매김.
    bm25_scores = bm25_index.get_scores(query.split())

    # (3) 두 검색 결과를 청크 ID로 연결함.
    vector_scores_by_id = {
        hit.metadata["chunk_id"]: hit.score for hit in vector_hits
    }
    bm25_scores_by_id = map_scores_to_chunk_ids(bm25_scores, chunk_ids)

    # (4) Vector 후보와 BM25 상위 후보를 하나의 후보 목록으로 합침.
    bm25_candidate_ids = get_top_chunk_ids(
        bm25_scores, chunk_ids, candidate_count
    )
    candidate_ids = set(vector_scores_by_id) | bm25_candidate_ids

    # (5) BM25와 Vector는 점수 범위가 다르므로 각각 0~1로 맞춤.
    normalized_bm25 = normalize_scores(bm25_scores_by_id, candidate_ids)
    normalized_vector = normalize_scores(vector_scores_by_id, candidate_ids)

    # (6) 청크마다 조정된 두 점수에 가중치를 곱해 더함.
    final_scores = {
        chunk_id: (
            w_bm25 * normalized_bm25[chunk_id]
            + w_vec * normalized_vector[chunk_id]
        )
        for chunk_id in candidate_ids
    }

    # (7) 볼 수 없는 청크를 제외하고 최종 점수가 높은 순서로 반환함.
    final_scores = apply_filters(final_scores, chunks, filters, user_role)
    return to_hits(final_scores, chunks, top_k)
