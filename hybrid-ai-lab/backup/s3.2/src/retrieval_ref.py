"""슬라이드 12~14: 권한·조건 필터와 Top-K 검색 완성본."""

from .helpers import embed_texts, get_collection
from .models import Hit


ROLE_ACCESS = {
    "agent": ["public", "internal"],
    "auditor": ["public", "internal", "restricted"],
}


def search(query: str, top_k: int = 5, filters: dict | None = None,
           user_role: str = "agent") -> list[Hit]:
    """권한과 조건을 모두 만족하는 조각을 코사인 유사도순으로 반환."""
    # 역할을 모르면 KeyError로 멈춤. 이 줄은 조건문 밖에 유지.
    where = {"access_level": {"$in": ROLE_ACCESS[user_role]}}
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k는 양의 정수여야 함")
    if not query.strip():
        raise ValueError("검색 질문이 비어 있음")
    if filters:
        where = {"$and": [where] + [{k: v} for k, v in filters.items()]}
    col = get_collection("card_docs")
    count = col.count()
    if count == 0:
        return []
    res = col.query(
        query_embeddings=embed_texts([query], kind="query"),
        n_results=min(top_k, count),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for chunk_id, document, metadata, distance in zip(
        res["ids"][0], res["documents"][0],
        res["metadatas"][0], res["distances"][0],
    ):
        meta = dict(metadata or {})
        meta["chunk_id"] = chunk_id
        hits.append(Hit(document, round(1 - distance, 3), meta))
    return sorted(hits, key=lambda h: h.score, reverse=True)
