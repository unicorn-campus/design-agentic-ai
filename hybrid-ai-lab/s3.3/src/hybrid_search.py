"""슬라이드 25: 조별 완성용 Hybrid Search 골격."""

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
    chunks, chunk_ids, bm25_index = get_bm25_index()
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

    # TODO: 조정된 BM25 점수와 Vector 점수에 가중치를 곱해 더함.
    raise NotImplementedError("final_scores 가중합 코드를 작성하세요")

    # final_scores = apply_filters(final_scores, chunks, filters, user_role)
    # return to_hits(final_scores, chunks, top_k)
