"""`R-13` 구독 상태 반영 처리기 — ④ 3-13절.

맡은 ③ 단계 5개 — `S-N4` · `S-N5` · `S-N8` ~ `S-N10`.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `T-1` 조회 `읽기` · `S-1` 구독 상태 갱신 `쓰기(되돌림 가능)` · `S-6` 감사 로그 적재.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "build_subscription_notice",
    "apply_subscription_state",
    "build_state_audit",
    "build_activation_notice",
    "build_undelivered_entry",
]

OWNER_ID = "R-13"
STEP_IDS = ("S-N4", "S-N5", "S-N8", "S-N9", "S-N10")


def build_subscription_notice(
    *,
    total_record_count: int,
    expiring_record_count: int,
    accuracy_gain_rate: float | None = None,
) -> dict[str, Any]:
    """`S-N4` 구독 안내 표시 — 누적 기록 수·정확도 향상률.

    향상률 산출식이 없으면 **향상률 없이 누적 수만** 표시함(`V-10` 11번 · ⑥ `B-25`).
    """
    return {
        "total_record_count": total_record_count,
        "expiring_record_count": expiring_record_count,
        "accuracy_gain_rate": accuracy_gain_rate,
    }


def apply_subscription_state(
    *,
    member_id: str,
    plan_type: str,
    applied_at: int,
    payment_id: str,
    retention_policy: str,
    state_idempotency_key: str,
) -> dict[str, Any]:
    """`S-N5` `K-29` 구독 상태 갱신 집합(멱등 처리).

    ④ 중단 조건 ⓐ — `payment_id`가 비면 상태를 바꾸지 않고 멈춤.
    ④ 중단 조건 ⓑ — 같은 멱등 키는 다시 갱신하지 않음(⑥ `B-30`).
    """
    if not payment_id:
        raise ValueError("결제 식별자가 빔 — 구독 상태를 바꾸지 않음")
    if not state_idempotency_key:
        raise ValueError("중복 방지 키가 빔 — 쓰기를 하지 않음(⑥ `B-30`)")
    return {
        "member_id": member_id,
        "plan_type": plan_type,
        "applied_at": applied_at,
        "payment_id": payment_id,
        "retention_policy": retention_policy,
        "state_idempotency_key": state_idempotency_key,
    }


def build_state_audit(
    *, member_id: str, plan_type: str, applied_at: int, state_idempotency_key: str
) -> dict[str, Any]:
    """`S-N8` 구독 상태 변경 감사 기록. 규제 필수 기록이라 승인 문을 두지 않음(⑥ 3-2절 15번)."""
    return {
        "member_id": member_id,
        "plan_type": plan_type,
        "applied_at": applied_at,
        "state_idempotency_key": state_idempotency_key,
    }


def build_activation_notice(
    *, member_id: str, plan_type: str, retention_applied: bool
) -> dict[str, Any]:
    """`S-N9` 프리미엄 활성화 완료 표시.

    ④ 중단 조건 ⓒ — 이력 보관 해제 회신이 오지 않았으면 완료 표시를 하지 않고 사람 확인으로 넘김.
    """
    if not retention_applied:
        raise ValueError("이력 보관 해제 회신이 없음 — 완료 표시를 하지 않음")
    return {"member_id": member_id, "plan_type": plan_type, "activated": True}


def build_undelivered_entry(
    *, member_id: str, fallback_reason: str
) -> dict[str, Any]:
    """`S-N10` 착지 — 미전달 큐 적재 + 사람 확인 알림.

    **착지 경로가 상한을 다시 쓰지 않음** — 모델 호출 0건 · 재시도 0건임.
    """
    return {
        "member_id": member_id,
        "fallback_reason": fallback_reason,
        "undelivered_queue_key": "[확인필요: 미전달 건의 대기열(DLQ) 유무·보관 위치]",
        "human_notice": True,
    }
