"""`R-12` 구독 플랜 안내 처리기 — ④ 3-12절.

맡은 ③ 단계 3개 — `S-S2` ~ `S-S4`.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `T-1` · `T-12` 조회 `읽기`. **쓰기 0건 · 되돌림 불가 쓰기 0건.**
캐시된 가격 조회 수단은 `[확인필요: 구독 플랜 가격 캐시의 보관 위치]`(③ 4-5절 소유 · 인용)임.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "accept_plan_view_request",
    "check_subscription_state",
    "build_plan_view",
]

OWNER_ID = "R-12"
STEP_IDS = ("S-S2", "S-S3", "S-S4")


def accept_plan_view_request(
    *,
    plan_view_request_id: str,
    member_id: str,
    requested_at: int,
    deadline_at: int,
    trigger_kind: str,
) -> dict[str, Any]:
    """`S-S2` 진입 값(③에 집합 식별자 없음)."""
    return {
        "plan_view_request_id": plan_view_request_id,
        "member_id": member_id,
        "requested_at": requested_at,
        "deadline_at": deadline_at,
        "trigger_kind": trigger_kind,
    }


def check_subscription_state(
    *,
    member_id: str,
    current_plan: str | None,
    subscription_state: str | None,
    duplicate_subscription: bool,
    next_billing_date: str | None = None,
) -> dict[str, Any]:
    """`S-S3` `K-17` 구독 상태 판정 집합.

    ④ 중단 조건 ⓐ — 이미 프리미엄이면 결제 진입을 열지 않음(⑥ `B-28`).
    ④ 중단 조건 ⓑ — 구독 상태를 못 읽으면 플랜 안내를 만들지 않음.
    """
    unreadable = current_plan is None or subscription_state is None
    already_premium = subscription_state == "프리미엄" or duplicate_subscription
    return {
        "member_id": member_id,
        "current_plan": current_plan,
        "duplicate_subscription": duplicate_subscription,
        "subscription_state": subscription_state,
        "next_billing_date": next_billing_date,
        "precheck_passed": not unreadable and not already_premium,
    }


def build_plan_view(
    *,
    plan_comparison: Sequence[Mapping[str, Any]],
    price_monthly_krw: int | None,
    price_yearly_monthly_krw: int | None,
    current_plan: str,
    price_source: str,
    next_billing_date: str | None = None,
    fallback_notice: str | None = None,
) -> dict[str, Any]:
    """`S-S4` 플랜 비교표·가격 표시.

    ④ 중단 조건 ⓒ — 실시간 가격과 캐시 가격이 둘 다 없으면 **가격 없는 비교표를 내보내지 않음.**
    """
    if price_monthly_krw is None or price_yearly_monthly_krw is None:
        raise ValueError("실시간·캐시 가격이 둘 다 없음 — 비교표를 내보내지 않음")
    return {
        "plan_comparison": [dict(row) for row in plan_comparison],
        "price_monthly_krw": price_monthly_krw,
        "price_yearly_monthly_krw": price_yearly_monthly_krw,
        "current_plan": current_plan,
        "next_billing_date": next_billing_date,
        "price_source": price_source,
        "fallback_notice": fallback_notice,
    }
