from __future__ import annotations

from typing import Protocol

from .base import HttpConnector
from .schemas import SearchRequest, SearchResponse


class OfficialSearchConnector(Protocol):
    async def search(self, request: SearchRequest, *, acting_user_ref: str | None = None) -> SearchResponse: ...


class HttpOfficialSearchConnector(HttpConnector):
    method = "POST"
    endpoint = "/v1/search"

    async def search(self, request: SearchRequest, *, acting_user_ref: str | None = None) -> SearchResponse:
        return SearchResponse.model_validate(
            await self._send(request, acting_user_ref=acting_user_ref)
        )


class MockOfficialSearchConnector:
    def __init__(self, response: SearchResponse) -> None:
        self.response = response
        self.calls = 0

    async def search(self, request: SearchRequest, *, acting_user_ref: str | None = None) -> SearchResponse:
        self.calls += 1
        return self.response
