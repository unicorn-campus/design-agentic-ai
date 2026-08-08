"""`R-10` PG 정기 결제 중지 실행 처리기 — ④ 3-10절.

맡은 ③ 단계 1개 — `S-C10`. **되돌림 불가 쓰기 1건**임.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `C-12` PG 정기 결제 중지 커넥터 · `S-6` 감사 로그 적재.

짝지은 사람 확인 노드 — ③ `S-C5`(해지 확인 모달 · 사전 확인)이고 사전 조건은 `S-C7` 커밋 성공임.
실패해도 **해지 예약을 되돌리지 않음**(③ 4-6절 · ⑥ `B-23`).
"""

from __future__ import annotations

from common.state import PgCancelStatus
from toolkit.runner import CallContext, ConnectorResult, ConnectorTool

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "CONNECTOR_ID",
    "GUARD_NAMES",
    "stop_recurring_payment",
    "failed_status",
]

OWNER_ID = "R-10"
STEP_IDS = ("S-C10",)
CONNECTOR_ID = "C-12"

GUARD_NAMES = ("confirm_modal_passed", "reservation_commit_success", "idempotency_key")
"""⑥ 3-1절 `C-12` 행의 `guards` 3개. 이름을 여기서 짓지 않고 ⑥ 값을 인용함."""


async def stop_recurring_payment(
    *,
    pg_payment_id: str | None,
    cancel_schedule_id: str | None,
    pg_cancel_idempotency_key: str,
    tool: ConnectorTool,
    call_context: CallContext,
) -> ConnectorResult:
    """④ `K-36`을 받아 `pg_cancel_status` 계열 3키를 냄.

    ④ 중단 조건 ⓐ — `cancel_schedule_id`가 비면 **호출하지 않고 멈춤.**
      예약 없는 중지는 결제 중인 구독을 끊는 반대 방향 사고임.
    ④ 중단 조건 ⓑ — `pg_payment_id`가 비면 호출하지 않고 `pg_cancel_status`를 `실패`로 둠.
    ④ 중단 조건 ⓒ — 중지 멱등 키가 비면 호출하지 않고 멈춤.
    ④ 중단 조건 ⓓ — 응답을 못 받으면 `확인 중`으로 두고 **예약을 되돌리지 않음.**

    재시도를 여기서 걸지 않음 — ③ 4-6절이 준 1회와 백오프 값은 설정에서 커넥터 계층이 읽음.
    """
    if not cancel_schedule_id:
        raise PermissionError("해지 예약이 없음 — PG 중지를 부르지 않음(⑥ `B-23`)")
    if not pg_payment_id:
        raise ValueError("PG 결제 식별자가 빔 — 부르지 않고 `실패`로 둠")
    if not pg_cancel_idempotency_key:
        raise ValueError("중지 멱등 키가 빔 — 부르지 않음(⑥ `B-30`)")
    return await tool.call(
        {
            "pg_payment_id": pg_payment_id,
            "cancel_schedule_id": cancel_schedule_id,
            "pg_cancel_idempotency_key": pg_cancel_idempotency_key,
        },
        call_context,
    )


def failed_status(*, cancel_schedule_id: str | None, requested_at: int) -> dict[str, object]:
    """부르지 못했거나 거절당한 자리에 남길 값. `실패`가 재시도 큐·사람 확인의 대상 표시임."""
    return {
        "pg_cancel_status": PgCancelStatus.FAILED,
        "pg_cancel_requested_at": requested_at,
        "cancel_schedule_id": cancel_schedule_id,
    }
