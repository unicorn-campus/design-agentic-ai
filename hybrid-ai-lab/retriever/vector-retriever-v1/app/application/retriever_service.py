"""표현 계층(CLI·API)이 부르는 Retriever 유스케이스 진입점."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from ..domain.access import is_known_role as _is_known_role
from .errors import describe_error as _describe_error
from .ports import RetrieverGraphPort
from .state import HealthResult, RetrieverRequest, SearchResult


@dataclass(frozen=True)
class ServiceLimits:
    """API 표현 계층이 쓰는 호출 예산·제한 시간 값. 설정에서 읽어 bootstrap이 주입함."""

    max_llm_calls_total: int = 200  # 서버 프로세스 전체의 누적 LLM 호출 상한
    max_llm_calls_per_request: int = 2  # API 요청 한 건의 LLM 호출 상한
    request_timeout_seconds: float = 120.0  # Retriever 요청 전체의 제한 시간(초)


class RetrieverService:
    """검색·답변·스트림·헬스체크 기능을 제공함.

    실제 실행은 생성자로 주입받은 그래프 실행 포트(RetrieverGraphPort)에 맡김.
    구현체 생성은 하지 않으며, 조립은 app/bootstrap.py가 담당함.
    """

    def __init__(self, runner: RetrieverGraphPort, limits: ServiceLimits | None = None) -> None:
        self._runner = runner
        self.limits = limits or ServiceLimits()

    def search(self, request: RetrieverRequest) -> SearchResult:
        """검색 유스케이스 한 건을 실행함(답변 LLM 호출 없음)."""

        return self._runner.search(request)

    def answer(self, request: RetrieverRequest) -> SearchResult:
        """답변 유스케이스 한 건을 실행함."""

        return self._runner.answer(request)

    def stream(self, request: RetrieverRequest) -> AsyncIterator[dict[str, Any]]:
        """그래프 이벤트와 최종 결과를 순서대로 전달함."""

        return self._runner.stream(request)

    def health(self) -> HealthResult:
        """준비된 검색 자원의 상태를 확인함."""

        return self._runner.health()

    @staticmethod
    def describe_error(error: BaseException) -> str:
        """예외 연쇄를 한 줄 요약으로 바꿈."""

        return _describe_error(error)


def is_known_role(role: str) -> bool:
    """표현 계층이 받은 역할 값이 허용된 역할인지 확인함."""

    return _is_known_role(role)


__all__ = ["RetrieverService", "ServiceLimits", "is_known_role"]
