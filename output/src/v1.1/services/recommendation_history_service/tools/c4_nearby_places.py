"""`C-4` 주변 식당 조회 — (E)지도 API(TB-3) · 실물 · 읽기.

출처 — ⑤ 6절 `C-4` · ④ 5-2절 `C-4` · ② 4절 (E)지도 API.
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

__all__ = ["CONNECTOR_ID", "SPEC", "NearbyPlacesInput", "NearbyPlacesOutput", "build"]

CONNECTOR_ID = "C-4"


class Place(ToolPayload):
    """④ 5-2절 `places` 안쪽 키 4개를 글자 그대로 옮김."""

    place_id: str
    place_name: str
    distance_m: int
    rating: float


class NearbyPlacesInput(ToolPayload):
    """④ 5-2절 `C-4` 입력 키 3개. `radius_m`은 500 고정값이며 값은 부르는 쪽이 넣음."""

    origin_lat: float
    origin_lng: float
    radius_m: int


class NearbyPlacesOutput(ToolPayload):
    places: list[Place]


SPEC = ToolSpec(
    connector_id=CONNECTOR_ID,
    display_name="주변 식당 조회",
    external_service="(E)지도 API",
    trust_boundary="TB-3",
    side_effect=SideEffect.READ,
    usage_condition="위치 동의를 확인한 뒤 후보 식당을 모을 때 부름(날씨 조회와 병렬 가능)",
    step_id="S-R7",
    owner_role="R-2",
    owning_service="추천·이력 서비스",
    input_model=NearbyPlacesInput,
    output_model=NearbyPlacesOutput,
    credential_kind=CredentialKind.API_KEY,
    requested_scopes=REQUESTED_SCOPES[CONNECTOR_ID],
    preconditions=("S-R3",),
    strict_order=False,
    backend_kind=BackendKind.HTTP,
    design_source="⑤ 6절 C-4 · ④ 5-2절 C-4 · ③ 4-1절 S-R7",
)


class NearbyPlacesConnector(HttpConnector):
    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        return {"places": reply.body.get("places", [])}


def build(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    *,
    client_factory: Any = None,
    **_: Any,
) -> NearbyPlacesConnector:
    endpoint = tool_settings.endpoint_of(CONNECTOR_ID)
    credential = build_credential(CONNECTOR_ID, tool_settings, endpoint)
    return NearbyPlacesConnector(
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
