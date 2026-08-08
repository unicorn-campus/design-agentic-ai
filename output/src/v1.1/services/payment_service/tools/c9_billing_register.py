"""`C-9` 정기 결제 등록 — (E)결제 게이트웨이(TB-5) · **Mock**(② 4절 소유) · **쓰기(되돌림 불가)**.

승인 문 — ⑥ 3-2절 8번 표 1행이 `사람 승인 필수`로 판정했음.
`S-S7`(금액·주기·고지 재표시 후 명시 승인) 표시가 없으면 **호출 자체가 거부됨**.
승인 결과를 인자(`user_approval_id`)로 받게 둔 ④ 설계 덕에 게이트 우회가 구조적으로 불가함.

재시도 — ③ 8-3절 `PG 자동 재시도`를 **0회로 못 박음**. 응답을 못 받은 상태에서 다시 부르면
이중 결제가 남음. 그래서 시간 상한을 넘겼을 때 **취소를 성공으로 보고하지 않고**
`payment_result = 확인 중`으로 두고 사람 확인으로 올림(③ `S-S9` 「초과 시 처리」와 같음).

출처 — ⑤ 6절 `C-9` · ④ 5-2절 `C-9`(=`K-21`) · ③ 4-5절 `S-S9` · ⑥ 3-2절.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from common.config import Settings
from common.state import PAYMENT_RESULT_PENDING
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
    "BillingRegisterInput",
    "BillingRegisterOutput",
    "build",
    "build_mock",
]

CONNECTOR_ID = "C-9"


class BillingRegisterInput(ToolPayload):
    """④ 5-2절 `C-9` 입력 키 5개(=`K-21`)를 글자 그대로 옮김.

    카드번호 · 유효기간 · CVC 칸이 **없음** — ② 판정 2-2가 시스템 내부 전체에서 칸을 없앴고
    단말이 PG에 직접 보내 받은 `payment_token`만 실림.
    `billing_cycle` · `payment_result`의 enum 값 목록은 `[확인필요]`이므로 문자로 두고
    값을 지어내지 않음.
    """

    payment_token: str
    amount_krw: int
    billing_cycle: str
    idempotency_key: str
    user_approval_id: str


class BillingRegisterOutput(ToolPayload):
    payment_result: str
    payment_id: str
    next_billing_date: date


SPEC = ToolSpec(
    connector_id=CONNECTOR_ID,
    display_name="정기 결제 등록",
    external_service="(E)결제 게이트웨이",
    trust_boundary="TB-5",
    side_effect=SideEffect.WRITE_IRREVERSIBLE,
    usage_condition="사용자가 금액·주기를 다시 보고 명시 승인한 뒤 최초 정기 결제를 등록할 때 부름",
    step_id="S-S9",
    owner_role="R-8",
    owning_service="결제 서비스",
    input_model=BillingRegisterInput,
    output_model=BillingRegisterOutput,
    credential_kind=CredentialKind.SERVICE_ACCOUNT,
    requested_scopes=REQUESTED_SCOPES[CONNECTOR_ID],
    preconditions=("S-S7", "S-S8"),
    strict_order=True,
    approval_marks=("S-S7",),
    idempotency_key_field="idempotency_key",
    external_accepts_idempotency_key=True,
    unresolved_marker={"payment_result": PAYMENT_RESULT_PENDING},
    backend_kind=BackendKind.HTTP,
    design_source="⑤ 6절 C-9 · ④ 5-2절 C-9 · ③ 4-5절 S-S9 · ⑥ 3-2절 8번표 1행",
)


class BillingRegisterConnector(HttpConnector):
    async def call(self, payload: Mapping[str, Any]) -> TransportReply:
        # 중복 방지 키를 **바깥에도** 실어 보냄 — PG가 그 키로 이중 결제를 막아 줌.
        return await self.transport.send(self.request_body(payload))

    def request_body(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return dict(payload)

    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        return {
            "payment_result": reply.body.get("payment_result"),
            "payment_id": reply.body.get("payment_id"),
            "next_billing_date": reply.body.get("next_billing_date"),
        }


class BillingRegisterMockConnector(MockConnector):
    """대역 — 실결제를 붙일 수 없는 기간의 구현임(② 4절 사유: 법적 기반이 론칭 전 과제).

    **실제 돈이 움직이지 않았음을 결과에 드러냄** — 결제 결과를 `확인 중`으로 두고
    사람 확인이 필요한 상태로 올림. `성공`으로 꾸며 내보내면 위쪽이 구독을 켜 버림.
    """

    def canned(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "payment_result": PAYMENT_RESULT_PENDING,
            "payment_id": f"mock-{payload['idempotency_key']}",
            "next_billing_date": date.min.isoformat(),
        }


def build(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    *,
    client_factory: Any = None,
    **_: Any,
) -> BillingRegisterConnector:
    endpoint = tool_settings.endpoint_of(CONNECTOR_ID)
    credential = build_credential(CONNECTOR_ID, tool_settings, endpoint)
    return BillingRegisterConnector(
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
) -> BillingRegisterMockConnector:
    return BillingRegisterMockConnector(
        spec=SPEC, credential=NoCredential(connector_id=CONNECTOR_ID)
    )
