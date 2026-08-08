"""바깥과 실제로 말을 주고받는 자리. 커넥터 어댑터는 이 인터페이스만 보고 씀.

대역(Mock)은 **같은 인터페이스의 다른 구현**이라 커넥터 코드 안에 분기문이 없음.
확인일 2026-08-08 — `httpx==0.28.1` 사양을 context7로 확인하고 씀.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx

from .auth import Credential
from .errors import ErrorClass
from .settings import EndpointConfig

__all__ = [
    "Transport",
    "TransportReply",
    "HttpTransport",
    "NullTransport",
    "classify_http_status",
    "classify_transport_exception",
]

# 상태 코드 → 오류 분류. 10단계 표를 그대로 옮긴 단 하나의 자리임.
_STATUS_TO_CLASS: Mapping[int, ErrorClass] = {
    400: ErrorClass.INPUT,
    401: ErrorClass.AUTH,
    403: ErrorClass.PERMISSION,
    404: ErrorClass.INPUT,
    409: ErrorClass.INPUT,
    422: ErrorClass.INPUT,
    429: ErrorClass.TRANSIENT,
}


@dataclass(frozen=True, slots=True)
class TransportReply:
    """바깥 응답. **본문 원문을 오류 메시지에 담지 않음** — 여기서만 들고 있음."""

    body: Mapping[str, Any]
    status_code: int | None = None
    transport_label: str = ""


@runtime_checkable
class Transport(Protocol):
    label: str

    async def send(self, payload: Mapping[str, Any]) -> TransportReply: ...

    async def aclose(self) -> None: ...


def classify_http_status(status_code: int) -> ErrorClass:
    """분류표 4종 중 하나로 가름. 표에 없는 코드는 `분류 불가`로 두고 재시도하지 않음."""
    known = _STATUS_TO_CLASS.get(status_code)
    if known is not None:
        return known
    if 500 <= status_code < 600:
        return ErrorClass.TRANSIENT
    return ErrorClass.UNCLASSIFIED


def classify_transport_exception(exc: BaseException) -> ErrorClass:
    """연결이 끊기거나 늦는 것은 `일시 장애`. 그 밖은 `분류 불가`임."""
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)):
        return ErrorClass.TRANSIENT
    if isinstance(exc, TimeoutError):
        return ErrorClass.TRANSIENT
    return ErrorClass.UNCLASSIFIED


@dataclass(slots=True)
class HttpTransport(Transport):
    """실물 경로. 주소 · 판본 · 인증 헤더 이름이 전부 설정에서 옴."""

    connector_id: str
    endpoint: EndpointConfig
    credential: Credential
    client_factory: Callable[[str], httpx.AsyncClient] | None = None
    label: str = "실물(HTTP)"
    _client: httpx.AsyncClient | None = None

    def _client_or_new(self) -> httpx.AsyncClient:
        if self._client is None:
            if self.client_factory is not None:
                self._client = self.client_factory(self.endpoint.base_url)
            else:
                self._client = httpx.AsyncClient(base_url=self.endpoint.base_url)
        return self._client

    async def send(self, payload: Mapping[str, Any]) -> TransportReply:
        headers = await self.credential.headers()
        if self.endpoint.api_version:
            headers = {**headers, "X-Api-Version": self.endpoint.api_version}
        client = self._client_or_new()
        method = self.endpoint.method.upper()
        if method == "GET":
            response = await client.get(
                self.endpoint.path, params=dict(payload), headers=headers
            )
        else:
            response = await client.request(
                method, self.endpoint.path, json=dict(payload), headers=headers
            )
        body: Mapping[str, Any]
        try:
            parsed = response.json()
        except ValueError:
            parsed = {}
        body = parsed if isinstance(parsed, Mapping) else {"items": parsed}
        return TransportReply(
            body=body, status_code=response.status_code, transport_label=self.label
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


@dataclass(slots=True)
class NullTransport(Transport):
    """대역이 쓰는 자리. **주소를 읽지 않고 아무 곳에도 붙지 않음.**"""

    connector_id: str
    label: str = "대역(바깥 호출 없음)"
    sent: list[Mapping[str, Any]] = field(default_factory=list)

    async def send(self, payload: Mapping[str, Any]) -> TransportReply:
        raise RuntimeError(
            f"{self.connector_id}: 대역 커넥터는 바깥으로 보내지 않음"
            " — 대역 어댑터가 응답을 직접 만듦"
        )

    async def aclose(self) -> None:
        return None
