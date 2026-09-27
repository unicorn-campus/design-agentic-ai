"""응용 계층이 외부 구현에 요구하는 포트 계약."""

from abc import abstractmethod
from typing import Protocol


class CustomerRepositoryPort(Protocol):
    @abstractmethod
    def rows(self, sql: str, parameters: dict) -> list[dict]: ...

    @abstractmethod
    def member(self, member_id: str) -> dict | None: ...

    @abstractmethod
    def schema(self) -> list[dict]: ...


class LLMPort(Protocol):
    @abstractmethod
    def ask(self, system: str, user: str, max_tokens: int = 1800) -> dict: ...


class QueryPort(Protocol):
    @abstractmethod
    def __call__(self, repository: CustomerRepositoryPort, member_id: str, base_date: str): ...


class ContextBuilderPort(Protocol):
    @abstractmethod
    def __call__(
        self,
        member_id: str,
        products: list[dict],
        monthly_usage: list[dict],
        delinquency: dict | None,
        base_date: str,
    ) -> str: ...

