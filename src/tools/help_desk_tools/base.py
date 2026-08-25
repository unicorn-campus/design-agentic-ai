from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from .auth import AuthenticationManager
from .errors import ConnectorError, ErrorCategory, classify_http_failure


class HttpConnector:
    method: str
    endpoint: str

    def __init__(self, client: httpx.AsyncClient, auth: AuthenticationManager) -> None:
        self._client = client
        self._auth = auth

    async def _send(
        self,
        payload: BaseModel,
        *,
        acting_user_ref: str | None = None,
        path_params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        endpoint = self.endpoint.format(**(path_params or {}))
        headers = await self._auth.request_headers(acting_user_ref)
        refreshed = False
        while True:
            try:
                response = await self._client.request(
                    self.method,
                    endpoint,
                    json=payload.model_dump(mode="json"),
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                raise ConnectorError(ErrorCategory.TRANSIENT, "외부 호출 시간 상한을 넘김") from exc
            except httpx.TransportError as exc:
                raise ConnectorError(ErrorCategory.TRANSIENT, "외부 전송이 일시적으로 실패함") from exc
            if response.is_success:
                try:
                    return response.json()
                except ValueError as exc:
                    raise ConnectorError(ErrorCategory.INPUT, "외부 응답 JSON 규격이 잘못됨") from exc
            failure = classify_http_failure(response)
            if failure.category is ErrorCategory.AUTHENTICATION and not refreshed:
                await self._auth.refresh_after_rejection(acting_user_ref)
                headers = await self._auth.request_headers(acting_user_ref)
                refreshed = True
                continue
            raise failure
