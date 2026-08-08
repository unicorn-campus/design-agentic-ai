"""`R-15` 기억 제한 알림 전달 처리기 — ④ 3-15절.

맡은 ③ 단계 3개 — `S-N1` ~ `S-N3`.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `T-1` · `T-5` 조회 `읽기` · `S-1` 알림 전달 `쓰기(되돌림 가능)`.
발송 커넥터 `C-10`은 **계약에 0건**임(③ 12-2절 6번) — 구독 안내가 화면 표시로만 나감.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "receive_memory_limit_signal",
    "check_free_plan_and_count",
    "build_notice",
]

OWNER_ID = "R-15"
STEP_IDS = ("S-N1", "S-N2", "S-N3")


def receive_memory_limit_signal(
    *,
    memory_limit_signal_id: str,
    member_id: str,
    detected_at: int,
    trigger_kind: str,
) -> dict[str, Any]:
    """`S-N1` 진입 값(③에 집합 식별자 없음).

    촉발 수단은 `[확인필요: 기억 제한 도달 감지의 촉발 수단(조회 시점 감지 vs 만료 D-1 주기 감지)]`
    (③ 소유 · 인용)임.
    """
    return {
        "memory_limit_signal_id": memory_limit_signal_id,
        "member_id": member_id,
        "detected_at": detected_at,
        "trigger_kind": trigger_kind,
    }


def check_free_plan_and_count(
    *,
    member_id: str,
    subscription_state: str | None,
    total_record_count: int | None,
    expiring_record_count: int | None,
) -> dict[str, Any]:
    """`S-N2` 사전 조건 — 무료 플랜 + 누적·만료 예정 기록 수 집계.

    ④ 중단 조건 ⓐ — 프리미엄이면 알림을 만들지 않음.
    ④ 중단 조건 ⓑ — 건수를 집계할 수 없으면 알림을 만들지 않음.
    """
    ok = (
        subscription_state == "무료"
        and total_record_count is not None
        and expiring_record_count is not None
    )
    return {
        "member_id": member_id,
        "subscription_state": subscription_state,
        "total_record_count": total_record_count,
        "expiring_record_count": expiring_record_count,
        "precheck_passed": ok,
    }


def build_notice(
    *,
    memory_limit_notice_id: str,
    member_id: str,
    total_record_count: int,
    expiring_record_count: int,
    notice_idempotency_key: str,
    accuracy_gain_rate: float | None = None,
) -> dict[str, Any]:
    """`S-N3` `K-28` 기억 제한 도달 집합.

    ④ 중단 조건 ⓓ — 향상률 산출식이 없으면 향상률 없이 누적 수만 실어 보냄(⑥ `B-25`).
    """
    return {
        "memory_limit_notice_id": memory_limit_notice_id,
        "member_id": member_id,
        "total_record_count": total_record_count,
        "expiring_record_count": expiring_record_count,
        "accuracy_gain_rate": accuracy_gain_rate,
        "notice_idempotency_key": notice_idempotency_key,
    }
