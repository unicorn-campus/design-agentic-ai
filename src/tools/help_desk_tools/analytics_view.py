from __future__ import annotations

from typing import Protocol

from .base import HttpConnector
from .schemas import AnalyticsRequest, AnalyticsResponse


class AnalyticsViewConnector(Protocol):
    async def query(self, request: AnalyticsRequest, *, acting_user_ref: str | None = None) -> AnalyticsResponse: ...


class HttpAnalyticsViewConnector(HttpConnector):
    method = "POST"
    endpoint = "/v1/query"

    async def query(self, request: AnalyticsRequest, *, acting_user_ref: str | None = None) -> AnalyticsResponse:
        return AnalyticsResponse.model_validate(
            await self._send(request, acting_user_ref=acting_user_ref)
        )


class MockAnalyticsViewConnector:
    def __init__(self, response: AnalyticsResponse) -> None:
        self.response = response
        self.calls = 0

    async def query(self, request: AnalyticsRequest, *, acting_user_ref: str | None = None) -> AnalyticsResponse:
        self.calls += 1
        return self.response
