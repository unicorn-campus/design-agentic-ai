from __future__ import annotations

from typing import Protocol

from .base import HttpConnector
from .schemas import LlmRequest, LlmResponse


class LlmApiConnector(Protocol):
    async def invoke(self, request: LlmRequest, *, acting_user_ref: str | None = None) -> LlmResponse: ...


class HttpLlmApiConnector(HttpConnector):
    method = "POST"
    endpoint = "/v1/responses"

    async def invoke(self, request: LlmRequest, *, acting_user_ref: str | None = None) -> LlmResponse:
        return LlmResponse.model_validate(
            await self._send(request, acting_user_ref=acting_user_ref)
        )


class MockLlmApiConnector:
    def __init__(self, response: LlmResponse) -> None:
        self.response = response
        self.calls = 0

    async def invoke(self, request: LlmRequest, *, acting_user_ref: str | None = None) -> LlmResponse:
        self.calls += 1
        return self.response
