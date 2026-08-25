from __future__ import annotations

from typing import Protocol

from .base import HttpConnector
from .schemas import CrmRequest, CrmResponse


class CrmConnector(Protocol):
    async def save(self, request: CrmRequest, *, acting_user_ref: str | None = None) -> CrmResponse: ...


class HttpCrmConnector(HttpConnector):
    method = "PUT"
    endpoint = "/v1/consultations/{consultation_ref}"

    async def save(self, request: CrmRequest, *, acting_user_ref: str | None = None) -> CrmResponse:
        return CrmResponse.model_validate(
            await self._send(
                request,
                acting_user_ref=acting_user_ref,
                path_params={"consultation_ref": request.consultation_ref},
            )
        )


class MockCrmConnector:
    def __init__(self, response: CrmResponse) -> None:
        self.response = response
        self.calls = 0

    async def save(self, request: CrmRequest, *, acting_user_ref: str | None = None) -> CrmResponse:
        self.calls += 1
        return self.response
