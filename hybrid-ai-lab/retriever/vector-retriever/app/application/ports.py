"""Retriever가 하위 계층에 요구하는 입출력 계약."""

from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from ..domain.corpus import CorpusSnapshot
from ..domain.search_filter import MetadataFilter
from ..domain.vector_search import DEFAULT_VECTOR_SEARCH_OPTIONS, VectorSearchOptions
from .state import HealthResult, Hit, RetrieverRequest, RouteDecision, SearchResult


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class EmbedderPort(Protocol):
    signature: str
    dimension: int

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class VectorSearchPort(Protocol):
    """질의 임베딩으로 근거 후보를 찾는 계약."""

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        k: int,
        metadata_filter: MetadataFilter,
        options: VectorSearchOptions = DEFAULT_VECTOR_SEARCH_OPTIONS,
    ) -> list[Hit]: ...


class VectorCatalogPort(Protocol):
    """검색 준비 상태를 전체 레코드 조회 없이 확인하는 계약."""

    @abstractmethod
    def describe(self) -> dict[str, Any]: ...


class VectorStorePort(VectorSearchPort, VectorCatalogPort, Protocol):
    """Retriever가 사용하는 검색·카탈로그 계약."""


class CorpusPort(Protocol):
    """Retriever가 활성 corpus 세대에 요구하는 읽기 계약."""

    @abstractmethod
    def active_generation(self) -> str | None: ...

    @abstractmethod
    def load_active(self) -> CorpusSnapshot | None: ...


class BM25Port(Protocol):
    @abstractmethod
    def keyword_search(
        self,
        query: str,
        *,
        allowed_access_levels: frozenset[str] | None = None,
        k: int,
    ) -> dict[str, float]: ...

    @abstractmethod
    def chunks(self) -> dict[str, Hit]: ...

    @abstractmethod
    def is_ready(self) -> bool: ...


class RerankerPort(Protocol):
    @abstractmethod
    def score(self, query: str, texts: list[str]) -> list[float]: ...


class LLMPort(Protocol):
    @abstractmethod
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
    @abstractmethod
    def get(self, query: str) -> RouteDecision | None: ...

    @abstractmethod
    def put(self, query: str, decision: RouteDecision) -> None: ...


class RetrieverGraphPort(Protocol):
    """검색·답변 흐름(그래프) 실행을 응용 서비스에 제공하는 계약."""

    @abstractmethod
    def search(self, request: RetrieverRequest) -> SearchResult:
        """답변 LLM 없이 검색 결과만 확정함."""

    @abstractmethod
    def answer(self, request: RetrieverRequest) -> SearchResult:
        """검색·답변·근거 검증을 한 번 실행함."""

    @abstractmethod
    def stream(self, request: RetrieverRequest) -> AsyncIterator[dict[str, Any]]:
        """노드 진행 이벤트와 최종 결과를 순서대로 전달함."""

    @abstractmethod
    def health(self) -> HealthResult:
        """검색 자원 준비 상태를 확인함."""
