"""`C-8` 영업 상태 조회 — (E)식약처 영업상태 API(TB-3) · **Mock**(② 4절 소유) · 읽기.

② 4절이 `Mock`으로 판정한 커넥터임 — 연동이 계획 문장뿐이고 확정이 아님(`V-04` 20번).
그래서 **대역 구현이 기본 경로**이고 실물 어댑터는 인증키가 발급된 뒤에만 켜짐
(⑦ 6-1절: `Mock 판에는 K-11을 주입하지 않음`).

출처 — ⑤ 6절 `C-8` · ④ 5-2절 `C-8` · ③ 4-1절 `S-R8`.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from common.config import Settings
from toolkit.auth import REQUESTED_SCOPES, NoCredential, build_credential
from toolkit.base_adapter import HttpConnector, MockConnector
from toolkit.schema import (
    BackendKind,
    CredentialKind,
    SideEffect,
    ToolPayload,
    ToolSpec,
)
from toolkit.settings import ConnectorMode, ToolSettings
from toolkit.transport import HttpTransport, TransportReply

__all__ = [
    "CONNECTOR_ID",
    "SPEC",
    "BusinessStatus",
    "BusinessStatusInput",
    "BusinessStatusOutput",
    "build",
    "build_mock",
]

CONNECTOR_ID = "C-8"


class BusinessStatus(StrEnum):
    """② 4절 · ⑤ 6절이 적은 3값. 값을 새로 만들지 않았음."""

    OPEN = "영업"
    CLOSED = "폐업"
    SUSPENDED = "정지"


class BusinessStatusInput(ToolPayload):
    place_ids: list[str]


class BusinessStatusOutput(ToolPayload):
    business_status_by_place: dict[str, BusinessStatus]


SPEC = ToolSpec(
    connector_id=CONNECTOR_ID,
    display_name="영업 상태 조회",
    external_service="(E)식약처 영업상태 API",
    trust_boundary="TB-3",
    side_effect=SideEffect.READ,
    usage_condition="후보 식당을 확정하기 **앞에** 폐업·정지 식당을 걸러낼 때 부름",
    step_id="S-R8",
    owner_role="R-2",
    owning_service="추천·이력 서비스",
    input_model=BusinessStatusInput,
    output_model=BusinessStatusOutput,
    credential_kind=CredentialKind.API_KEY,
    requested_scopes=REQUESTED_SCOPES[CONNECTOR_ID],
    preconditions=("S-R7",),
    strict_order=True,
    backend_kind=BackendKind.HTTP,
    design_source="⑤ 6절 C-8 · ④ 5-2절 C-8 · ② 4절 Mock 판정",
)


class BusinessStatusConnector(HttpConnector):
    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        return {
            "business_status_by_place": reply.body.get("business_status_by_place", {})
        }


class BusinessStatusMockConnector(MockConnector):
    """대역 — 주소를 읽지 않고 아무 곳에도 붙지 않음.

    원천이 확정되기 전이므로 **모든 식당을 `영업`으로 두지 않고** 판정 자체를 하지 않음:
    빈 사전과 함께 `필터 미적용`이 드러나게 함(③ `S-R8` 초과 시 처리와 같은 뜻).
    폐업 식당을 `영업`으로 꾸며 내보내면 ①의 `위반 노출 0건`을 거짓으로 통과시킴.
    """

    def canned(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"business_status_by_place": {}}


def build(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    *,
    client_factory: Any = None,
) -> BusinessStatusConnector:
    endpoint = tool_settings.endpoint_of(CONNECTOR_ID)
    credential = build_credential(CONNECTOR_ID, tool_settings, endpoint)
    return BusinessStatusConnector(
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


def build_mock(
    tool_settings: ToolSettings, runtime_settings: Settings, **_: Any
) -> BusinessStatusMockConnector:
    """대역은 **설정을 읽지 않음** — 주소도 자격도 필요 없음(⑦ 6-1절)."""
    return BusinessStatusMockConnector(
        spec=SPEC, credential=NoCredential(connector_id=CONNECTOR_ID)
    )
