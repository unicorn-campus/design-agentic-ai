"""Retriever가 하위 계층에 요구하는 입출력 계약."""

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from ..domain.corpus import CorpusSnapshot
from ..domain.search_filter import MetadataFilter
from .state import Hit, RouteDecision


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class EmbedderPort(Protocol):
    dimension: int

    def embed_query(self, text: str) -> list[float]: ...


class VectorSearchPort(Protocol):
    """질의 임베딩으로 근거 후보를 찾는 계약."""

    def search(
        self,
        query_embedding: list[float],
        k: int,
        metadata_filter: MetadataFilter,
    ) -> list[Hit]: ...


class VectorCatalogPort(Protocol):
    """검색 준비 상태를 전체 레코드 조회 없이 확인하는 계약."""

    def describe(self) -> dict[str, Any]: ...


class VectorStorePort(VectorSearchPort, VectorCatalogPort, Protocol):
    """Retriever가 사용하는 검색·카탈로그 계약."""


class CorpusPort(Protocol):
    """Retriever가 활성 corpus 세대에 요구하는 읽기 계약."""

    def active_generation(self) -> str | None: ...

    def load_active(self) -> CorpusSnapshot | None: ...


class BM25Port(Protocol):
    def scores(
        self,
        query: str,
        *,
        allowed_access_levels: frozenset[str] | None = None,
        k: int,
    ) -> dict[str, float]: ...

    def chunks(self) -> dict[str, Hit]: ...

    def is_ready(self) -> bool: ...


class RerankerPort(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]: ...


class LLMPort(Protocol):
    def complete_structured(
        self,
        system: str,
        user: str,
        schema: type[StructuredModel],
        *,
        max_tokens: int,
        max_attempts: int = 3,
        deadline_seconds: float | None = None,
    ) -> Any: ...


class TransformCachePort(Protocol):
    def get(self, query: str) -> RouteDecision | None: ...

    def put(self, query: str, decision: RouteDecision) -> None: ...
