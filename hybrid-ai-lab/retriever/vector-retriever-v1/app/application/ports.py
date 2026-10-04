"""Retriever가 하위 계층에 요구하는 입출력 계약."""

from abc import abstractmethod
from collections.abc import AsyncIterator, Iterable
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from ..domain.corpus import CorpusSnapshot
from ..domain.keywords import TermObservation
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


class KeywordAnalyzerPort(Protocol):
    """질문과 검색 결과를 색인과 같은 분석기로 자르고 색인 통계를 제공하는 계약."""

    @abstractmethod
    def observe(self, text: str) -> tuple[TermObservation, ...]:
        """질문을 색인과 같은 토큰으로 자르고 품사·고유이름 여부를 붙여 반환함.

        인자: text는 사용자가 입력한 원문이며 정규화는 구현체가 수행함.
        반환값: 질문에 나온 순서를 유지한 토큰 관찰값이며, 빈 문자열이면 빈 묶음임.
        예외: 형태소 분석기 초기화·실행 실패 예외를 호출자에게 전달함.
        부수효과: 활성 세대가 바뀌었으면 색인 묶음을 다시 읽을 수 있음.
        """
        ...

    @abstractmethod
    def index_tokens(self, text: str) -> frozenset[str]:
        """검색 결과 본문을 같은 분석기로 잘라 중복 없는 토큰 집합으로 반환함.

        반환값: 질문 토큰과 그대로 비교 가능한 토큰 집합임.
        예외: 형태소 분석 실패 예외를 호출자에게 전달함.
        부수효과: 없음.
        """
        ...

    @abstractmethod
    def corpus_statistics(self, tokens: Iterable[str]) -> tuple[int, dict[str, int]]:
        """색인 전체 청크 수와 요청한 토큰별 문서빈도를 반환함.

        인자: tokens는 문서빈도를 알고 싶은 토큰 목록이며 중복이 있어도 됨.
        반환값: (전체 청크 수, 토큰별 청크 수)이며 색인에 없는 토큰은 0임. 활성 세대가 없으면 (0, {})임.
        예외: 색인 읽기 실패 예외를 호출자에게 전달함.
        부수효과: 활성 세대가 바뀐 첫 호출에서 전체 corpus를 토큰화해 통계를 다시 만듦.
        """
        ...


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
