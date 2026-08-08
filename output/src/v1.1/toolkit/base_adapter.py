"""어댑터가 공통으로 쓰는 뼈대. 커넥터마다 다른 것은 커넥터 파일에만 둠."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from common.config import Settings
from common.model_client import ModelClient

from .auth import Credential
from .schema import ToolSpec
from .settings import ConnectorMode, EndpointConfig
from .transport import NullTransport, Transport, TransportReply

__all__ = ["HttpConnector", "ModelConnector", "MockConnector"]


@dataclass(slots=True)
class HttpConnector:
    """실물 HTTP 경로를 타는 어댑터의 바탕. 주소·자격을 자기 안에서만 알고 있음."""

    spec: ToolSpec
    transport: Transport
    credential: Credential
    endpoint: EndpointConfig
    mode: ConnectorMode = ConnectorMode.LIVE

    async def call(self, payload: Mapping[str, Any]) -> TransportReply:
        return await self.transport.send(self.request_body(payload))

    def request_body(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """④ 키를 제공자 규격으로 옮기는 자리.

        제공자 규격이 원문에 없어 지금은 ④ 키를 그대로 보냄 —
        `[확인필요: 제공자별 요청 필드 이름]`. 이름이 오면 이 함수만 고침.
        """
        return dict(payload)

    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        """바깥 응답에서 ⑤ 키만 뽑는 자리. 커넥터마다 덮어씀."""
        return reply.body

    async def aclose(self) -> None:
        await self.transport.aclose()


@dataclass(slots=True)
class ModelConnector:
    """(E)LLM API에 붙는 어댑터의 바탕. 모델 어댑터는 `common.model_client`를 그대로 씀."""

    spec: ToolSpec
    transport: Transport
    credential: Credential
    client: ModelClient
    settings: Settings
    mode: ConnectorMode = ConnectorMode.LIVE

    async def call(self, payload: Mapping[str, Any]) -> TransportReply:
        raise NotImplementedError

    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        return reply.body

    async def aclose(self) -> None:
        await self.transport.aclose()


@dataclass(slots=True)
class MockConnector:
    """대역 어댑터의 바탕. **주소를 읽지 않고 자격도 쓰지 않음.**

    실물 코드 안에 분기문을 심지 않기 위해 아예 다른 구현으로 둠(설정으로 갈아 끼움).
    """

    spec: ToolSpec
    credential: Credential
    transport: Transport = None  # type: ignore[assignment]
    mode: ConnectorMode = ConnectorMode.MOCK

    def __post_init__(self) -> None:
        if self.transport is None:
            self.transport = NullTransport(connector_id=self.spec.connector_id)

    async def call(self, payload: Mapping[str, Any]) -> TransportReply:
        return TransportReply(
            body=self.canned(payload),
            status_code=200,
            transport_label=self.transport.label,
        )

    def canned(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError

    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        return reply.body

    async def aclose(self) -> None:
        await self.transport.aclose()
