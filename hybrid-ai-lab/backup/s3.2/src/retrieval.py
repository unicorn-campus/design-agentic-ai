"""슬라이드 13: 조별 실습 골격. TODO 2와 TODO 4 완성 후 실행."""

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
    # TODO 2: filters가 있으면 권한 where를 $and의 첫 항으로 합성
    # 힌트: {"$and": [where] + [{k: v} for k, v in filters.items()]}
    raise NotImplementedError("TODO 2: 권한·조건 필터를 합성하세요")
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
    # TODO 4: res의 ids/documents/metadatas/distances에서 [0] 목록을 zip
    # metadata를 복사해 chunk_id 추가, round(1 - distance, 3)으로 점수 변환
    # Hit 목록을 score 내림차순 정렬. 0건이면 [] 반환
    raise NotImplementedError("TODO 4: 검색 결과를 Hit 목록으로 바꾸세요")
