"""`C-12` 정기 결제 중지 — (E)결제 게이트웨이(TB-5) · **Mock**(② 4절 소유) · **쓰기(되돌림 불가)**.

`C-9`와 **같은 외부 API의 다른 동작**임(⑤ 6절). 위험이 반대 방향으로 생김 —
예약 없이 부르면 **결제 중인 구독을 끊고**, 예약 뒤 안 부르면 **다음 결제일에 자동 재청구**가 나감.

승인 문 — ⑥ 3-2절 8행이 `사람 확인 필수`로 판정했음. 두 조건을 **모두** 요구함:
ⓐ `S-C5` 해지 확인 모달 통과 ⓑ `S-C7` 예약 커밋 성공.

실패 시 — **해지 예약을 되돌리지 않음.** 감사 기록 + 재시도 큐 + 사람 확인임(③ 4-6절 `S-C10`).
`pg_cancel_status`를 `실패`(응답을 받았고 거절됨) 또는 `확인 중`(응답을 못 받음)으로 둠.

출처 — ⑤ 6절 `C-12` · ④ 3-10절 `R-10` 입출력 형식(=`K-36`) · ③ 4-6절 `S-C10` · ⑥ 3-2절.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from common.config import Settings
from common.state import PgCancelStatus
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
    "BillingStopInput",
    "BillingStopOutput",
    "build",
    "build_mock",
]

CONNECTOR_ID = "C-12"


class BillingStopInput(ToolPayload):
    """④ 3-10절 `R-10` 입력 키 3개(=`K-36`)를 글자 그대로 옮김.

    결제 수단 항목을 **아예 두지 않았음** — 중지에는 결제 식별자만 필요함(⑤ 6절).
    회원 식별자 칸도 없음(④ 3-10절이 두지 않았음).
    """

    pg_payment_id: str
    cancel_schedule_id: str
    pg_cancel_idempotency_key: str


class BillingStopOutput(ToolPayload):
    """④ 3-10절 출력 키 3개. `pg_cancel_status`는 ③ 6절 23번 상태 필드 이름을 그대로 씀."""

    pg_cancel_status: PgCancelStatus
    pg_cancel_requested_at: datetime
    cancel_schedule_id: str


SPEC = ToolSpec(
    connector_id=CONNECTOR_ID,
    display_name="정기 결제 중지",
    external_service="(E)결제 게이트웨이",
    trust_boundary="TB-5",
    side_effect=SideEffect.WRITE_IRREVERSIBLE,
    usage_condition="사람이 해지를 확인하고 해지 예약이 커밋된 직후, 자동 재청구를 끊을 때 부름",
    step_id="S-C10",
    owner_role="R-10",
    owning_service="결제 서비스",
    input_model=BillingStopInput,
    output_model=BillingStopOutput,
    credential_kind=CredentialKind.SERVICE_ACCOUNT,
    requested_scopes=REQUESTED_SCOPES[CONNECTOR_ID],
    preconditions=("S-C5", "S-C7"),
    strict_order=True,
    approval_marks=("S-C5", "S-C7"),
    idempotency_key_field="pg_cancel_idempotency_key",
    external_accepts_idempotency_key=True,
    unresolved_marker={"pg_cancel_status": PgCancelStatus.PENDING.value},
    failure_marker={"pg_cancel_status": PgCancelStatus.FAILED.value},
    backend_kind=BackendKind.HTTP,
    design_source="⑤ 6절 C-12 · ④ 3-10절 R-10 · ③ 4-6절 S-C10 · ⑥ 3-2절 8행",
)


class BillingStopConnector(HttpConnector):
    def translate(self, reply: TransportReply) -> Mapping[str, Any]:
        return {
            "pg_cancel_status": reply.body.get("pg_cancel_status"),
            "pg_cancel_requested_at": reply.body.get("pg_cancel_requested_at"),
            "cancel_schedule_id": reply.body.get("cancel_schedule_id"),
        }


class BillingStopMockConnector(MockConnector):
    """대역 — 실제 PG 스케줄을 끊지 않았으므로 `중지완료`로 꾸미지 않음.

    `확인 중`으로 두어 **다음 결제일 전에 사람이 확인해야 함**이 위쪽에 그대로 드러나게 함
    (③ 4-6절 `S-C10`이 지정한 재시도 큐·사람 확인 경로로 감).
    """

    def canned(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "pg_cancel_status": PgCancelStatus.PENDING.value,
            "pg_cancel_requested_at": datetime.min.isoformat(),
            "cancel_schedule_id": payload["cancel_schedule_id"],
        }


def build(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    *,
    client_factory: Any = None,
    **_: Any,
) -> BillingStopConnector:
    endpoint = tool_settings.endpoint_of(CONNECTOR_ID)
    credential = build_credential(CONNECTOR_ID, tool_settings, endpoint)
    return BillingStopConnector(
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
) -> BillingStopMockConnector:
    return BillingStopMockConnector(
        spec=SPEC, credential=NoCredential(connector_id=CONNECTOR_ID)
    )
