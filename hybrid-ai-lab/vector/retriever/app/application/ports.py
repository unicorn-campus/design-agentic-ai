"""Retriever가 하위 계층에 요구하는 입출력 계약."""

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from .state import Hit, RouteDecision


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class EmbedderPort(Protocol):
    dimension: int

    def embed_query(self, text: str) -> list[float]: ...


class VectorStorePort(Protocol):
    def search(self, query_embedding: list[float], k: int, where: dict) -> list[Hit]: ...

    def upsert(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None: ...

    def get_all(self) -> dict: ...

    def count(self) -> int: ...

    def check_signature(self, expected: str) -> bool: ...


class BM25Port(Protocol):
    def scores(self, query: str) -> dict[str, float]: ...

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
