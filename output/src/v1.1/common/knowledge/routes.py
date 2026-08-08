"""적용 판정표 — 설계서 ⑤가 **채택한 경로만** 여기에 있음.

이 표가 이 묶음의 목차임. 미채택 경로는 행만 남기고 **파일·설정·의존성을 0건으로 둠**
(`tests/knowledge/test_routes.py`가 실제로 없는지 검사함).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "ADOPTED_ROUTES",
    "KNOWLEDGE_ROUTES",
    "NOT_ADOPTED_MODULE_NAMES",
    "NOT_ADOPTED_ROUTES",
    "NOT_ADOPTED_SETTING_NAMES",
    "Adoption",
    "KnowledgeRoute",
    "module_of",
    "route_of",
]


class Adoption(StrEnum):
    """⑤가 그 경로를 골랐나."""

    ADOPTED = "채택"
    NOT_ADOPTED = "미채택"


@dataclass(frozen=True, slots=True)
class KnowledgeRoute:
    """경로 1개. `⑤의 한 줄 = 이 객체 1개`임."""

    route_id: str
    generic_name: str
    adoption: Adoption
    design_row: str
    reason: str
    module: str | None


_ROUTES: tuple[KnowledgeRoute, ...] = (
    KnowledgeRoute(
        route_id="T-1~T-18",
        generic_name="조회",
        adoption=Adoption.ADOPTED,
        design_row="⑤ 3절 「정형 접근 경로」 18행",
        reason="답이 조건에 맞는 목록·단건·사전 정의 집계인 질문이 17건 중 13건임",
        module="structured",
    ),
    KnowledgeRoute(
        route_id="K-1",
        generic_name="벡터 유사도",
        adoption=Adoption.ADOPTED,
        design_row="⑤ 5절 K-1",
        reason="취향 프로파일과 음식·메뉴를 뜻으로 견주는 것이 후보 순위의 근거임",
        module="vector_index",
    ),
    KnowledgeRoute(
        route_id="K-2",
        generic_name="속성 필터 검색",
        adoption=Adoption.ADOPTED,
        design_row="⑤ 5절 K-2",
        reason="카테고리·거리·영업 상태는 정확 조건이라 유사도로 대신할 수 없음",
        module="attribute_filter",
    ),
    KnowledgeRoute(
        route_id="K-3",
        generic_name="용어사전",
        adoption=Adoption.ADOPTED,
        design_row="⑤ 5절 K-3",
        reason="온보딩 태그와 추천 카테고리를 같은 낱말로 묶어야 취향 학습이 이어짐",
        module="glossary_apply",
    ),
    KnowledgeRoute(
        route_id="K-4",
        generic_name="문서 검색",
        adoption=Adoption.NOT_ADOPTED,
        design_row="⑤ 5절 K-4",
        reason="색인할 문서 코퍼스가 원문에 0건임. 만들 색인이 없음",
        module=None,
    ),
    KnowledgeRoute(
        route_id="K-5",
        generic_name="관계 검색",
        adoption=Adoption.NOT_ADOPTED,
        design_row="⑤ 5절 K-5",
        reason="다단계 관계 질문이 0건이고 개체·관계 구축 비용이 기간·단가 상한을 넘김",
        module=None,
    ),
    KnowledgeRoute(
        route_id="NL-0",
        generic_name="질의 생성",
        adoption=Adoption.NOT_ADOPTED,
        design_row="⑤ 판정 3 · 판정 3-B · ⑤ 3절 머리 원칙",
        reason="자연어로 저장소를 묻는 화면이 0건임. 담당자는 미리 짠 조회 이름만 고름",
        module=None,
    ),
)

KNOWLEDGE_ROUTES: dict[str, KnowledgeRoute] = {route.route_id: route for route in _ROUTES}
ADOPTED_ROUTES: tuple[KnowledgeRoute, ...] = tuple(
    route for route in _ROUTES if route.adoption is Adoption.ADOPTED
)
NOT_ADOPTED_ROUTES: tuple[KnowledgeRoute, ...] = tuple(
    route for route in _ROUTES if route.adoption is Adoption.NOT_ADOPTED
)

# 미채택 경로를 만들었다면 생겼을 파일 이름. 시험이 이 이름이 0건인지 검사함.
NOT_ADOPTED_MODULE_NAMES: tuple[str, ...] = (
    "document_index",
    "document_search",
    "bm25",
    "graph_loader",
    "graph_search",
    "community_summary",
    "sql_generator",
    "query_to_sql",
    "schema_prompt",
)

# 미채택 경로를 만들었다면 생겼을 설정 이름. 시험이 이 이름이 0건인지 검사함.
NOT_ADOPTED_SETTING_NAMES: tuple[str, ...] = (
    "knowledge_document_index_name",
    "knowledge_chunk_size",
    "knowledge_chunk_overlap",
    "knowledge_graph_hops",
    "knowledge_graph_result_cap",
    "knowledge_community_summary_enabled",
    "knowledge_sql_schema_scope",
)


def route_of(route_id: str) -> KnowledgeRoute:
    try:
        return KNOWLEDGE_ROUTES[route_id]
    except KeyError as exc:
        raise KeyError(f"판정표에 없는 경로 이름임: {route_id}") from exc


def module_of(route_id: str) -> str:
    """그 경로를 만든 파일 이름. 미채택이면 파일이 없으므로 실패함."""
    route = route_of(route_id)
    if route.module is None:
        raise ValueError(f"{route_id}는 미채택 경로임 — 만든 파일이 없음")
    return route.module
