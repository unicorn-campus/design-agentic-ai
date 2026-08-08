"""`C-7` 현재 날씨 조회 — (E)날씨 API(TB-3) · 실물 · 읽기.

출처 — ⑤ 6절 `C-7` · ④ 5-2절 `C-7` · ② 4절 (E)날씨 API.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from common.config import Settings
from toolkit.auth import REQUESTED_SCOPES, build_credential
from toolkit.base_adapter import HttpConnector
from toolkit.schema import (
    BackendKind,
    CredentialKind,
    SideEffect,
    ToolPayload,
    ToolSpec,
)
from toolkit.settings import ConnectorMode, ToolSettings
from toolkit.transport import HttpTransport, TransportReply

__all__ = ["CONNECTOR_ID", "SPEC", "CurrentWeatherInput", "CurrentWeatherOutput", "build"]

CONNECTOR_ID = "C-7"


class CurrentWeatherInput(ToolPayload):
    origin_lat: float
    origin_lng: float


class CurrentWeatherOutput(ToolPayload):
    weather_temp_c: float
    weather_condition: str


SPEC = ToolSpec(
    connector_id=CONNECTOR_ID,
    display_name="현재 날씨 조회",
    external_service="(E)날씨 API",
    trust_boundary="TB-3",
    side_effect=SideEffect.READ,
    usage_condition="위치 동의를 확인한 뒤 컨텍스트에 기온·날씨를 채울 때 부름(식당 조회와 병렬 가능)",
    step_id="S-R6",
    owner_role="R-2",
    owning_service="추천·이력 서비스",
    input_model=CurrentWeatherInput,
    output_model=CurrentWeatherOutput,
    credential_kind=CredentialKind.API_KEY,
    requested_scopes=REQUESTED_SCOPES[CONNECTOR_ID],
    preconditions=("S-R3",),
    strict_order=False,
    backend_kind=BackendKind.HTTP,
    design_source="⑤ 6절 C-7 · ④ 5-2절 C-7 · ③ 4-1절 S-R6",
)


class CurrentWeatherConnector(HttpConnector):
    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        return {
            "weather_temp_c": reply.body.get("weather_temp_c"),
            "weather_condition": reply.body.get("weather_condition"),
        }


def build(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    *,
    client_factory: Any = None,
    **_: Any,
) -> CurrentWeatherConnector:
    endpoint = tool_settings.endpoint_of(CONNECTOR_ID)
    credential = build_credential(CONNECTOR_ID, tool_settings, endpoint)
    return CurrentWeatherConnector(
        spec=SPEC,
        transport=HttpTransport(
            connector_id=CONNECTOR_ID,
            endpoint=endpoint,
            credential=credential,
            client_factory=client_factory,
        ),
        credential=credential,
        endpoint=endpoint,
        mode=ConnectorMode.LIVE,
    )
