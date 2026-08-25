from __future__ import annotations

from typing import Protocol

from .base import HttpConnector
from .schemas import SurveyRequest, SurveyResponse


class SurveyConnector(Protocol):
    async def send(self, request: SurveyRequest, *, acting_user_ref: str | None = None) -> SurveyResponse: ...


class HttpSurveyConnector(HttpConnector):
    method = "POST"
    endpoint = "/v1/surveys/send"

    async def send(self, request: SurveyRequest, *, acting_user_ref: str | None = None) -> SurveyResponse:
        return SurveyResponse.model_validate(
            await self._send(request, acting_user_ref=acting_user_ref)
        )


class MockSurveyConnector:
    def __init__(self, response: SurveyResponse) -> None:
        self.response = response
        self.calls = 0

    async def send(self, request: SurveyRequest, *, acting_user_ref: str | None = None) -> SurveyResponse:
        self.calls += 1
        return self.response
