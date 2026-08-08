"""`R-8` PG 정기 결제 등록 실행 처리기 — ④ 3-8절.

맡은 ③ 단계 1개 — `S-S9`. **되돌림 불가 쓰기 1건**임.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `C-9` 정기 결제 등록 커넥터 1개. 다른 도구 0건(감사 기록은 `R-7`의 `S-S11`이 남김).

짝지은 사람 확인 노드 — ③ `S-S7`(금액·주기·고지 재표시 후 명시 승인). **사전 승인이라 짝이 성립함.**
자동 재시도는 ③ 8-3절이 **0회로 못 박았음** — 응답을 못 받은 상태에서 재호출하면 이중 결제가 남음.
"""

from __future__ import annotations

from typing import Any

from toolkit.runner import CallContext, ConnectorResult, ConnectorTool

__all__ = ["OWNER_ID", "STEP_IDS", "CONNECTOR_ID", "GUARD_NAMES", "register_recurring_payment"]

OWNER_ID = "R-8"
STEP_IDS = ("S-S9",)
CONNECTOR_ID = "C-9"

GUARD_NAMES = ("approval_flag", "approval_session_fresh", "idempotency_key", "pg_auto_retry_zero")
"""⑥ 3-1절 `C-9` 행의 `guards` 4개. 이름을 여기서 짓지 않고 ⑥ 값을 인용함."""


async def register_recurring_payment(
    *,
    payment_token: str,
    amount_krw: int,
    billing_cycle: str,
    idempotency_key: str,
    user_approval_id: str,
    tool: ConnectorTool,
    call_context: CallContext,
) -> ConnectorResult:
    """④ `K-21`을 받아 `K-22`를 냄.

    ④ 중단 조건 ⓐ — `user_approval_id`가 비면 **호출하지 않고 멈춤**(⑥ `B-12`).
    ④ 중단 조건 ⓑ — `idempotency_key`가 비면 호출하지 않고 멈춤(⑥ `B-30`).
    ④ 중단 조건 ⓒ — 같은 멱등 키의 응답을 이미 받았으면 다시 호출하지 않음
      (커넥터 계층의 먼저 낸 결과 저장소가 그 자리를 막음).
    ④ 중단 조건 ⓓ — 응답을 못 받으면 다시 호출하지 않고 `확인 중`으로 두고 멈춤.

    **재시도를 여기서 걸지 않음** — ③이 `S-S9` 자동 재시도를 0회로 못 박았고
    그 값은 설정(`LUNCHPICK_STEP_RETRY_COUNT`)에서 커넥터 계층이 읽음.
    """
    if not user_approval_id:
        raise PermissionError("승인 증거가 없음 — PG를 부르지 않음(⑥ `B-12`)")
    if not idempotency_key:
        raise ValueError("멱등 키가 빔 — PG를 부르지 않음(⑥ `B-30`)")
    payload: dict[str, Any] = {
        "payment_token": payment_token,
        "amount_krw": amount_krw,
        "billing_cycle": billing_cycle,
        "idempotency_key": idempotency_key,
        "user_approval_id": user_approval_id,
    }
    return await tool.call(payload, call_context)
