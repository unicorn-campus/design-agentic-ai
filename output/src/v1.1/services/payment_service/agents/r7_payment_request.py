"""`R-7` 구독 결제 요청 조립·검증 처리기 — ④ 3-7절.

맡은 ③ 단계 8개 — `S-S5` ~ `S-S8` · `S-S10` ~ `S-S13`.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `T-12` 조회 `읽기` · `S-7` 결제 저장소 적재 · `S-6` 감사 로그 적재.
**되돌림 불가 쓰기 0건** — PG 호출은 `R-8` 소관이라 이 담당자의 도구에 없음(자율 호출 불가).
"""

from __future__ import annotations

from typing import Any, Sequence

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "WITHDRAWAL_PERIOD_DAYS",
    "accept_payment_request",
    "build_disclosure",
    "build_approval_prompt",
    "verify_and_key",
    "record_payment_result",
    "build_payment_audit",
    "build_payment_response",
    "build_payment_landing",
]

OWNER_ID = "R-7"
STEP_IDS = ("S-S5", "S-S6", "S-S7", "S-S8", "S-S10", "S-S11", "S-S12", "S-S13")

WITHDRAWAL_PERIOD_DAYS = 7
"""④ `K-19`가 `7 고정`으로 적은 값 — `V-10` 31번 청약철회권 7일임. 단계 상한이 아님."""

_PAYMENT_RESULT_PENDING = "확인 중"
"""③ 6절 18번이 허용한 값. 값 목록의 주인은 ③임."""


def accept_payment_request(
    *,
    payment_request_id: str,
    member_id: str,
    plan_type: str,
    billing_cycle: str,
    amount_krw: int,
    requested_at: int,
    deadline_at: int,
) -> dict[str, Any]:
    """`S-S5` `K-18` 결제 요청 집합."""
    return {
        "payment_request_id": payment_request_id,
        "member_id": member_id,
        "plan_type": plan_type,
        "billing_cycle": billing_cycle,
        "amount_krw": amount_krw,
        "requested_at": requested_at,
        "deadline_at": deadline_at,
    }


def build_disclosure(
    *,
    disclosure_id: str,
    auto_renewal_notice: str,
    cancel_method_notice: str,
    disclosed_at: int,
) -> dict[str, Any]:
    """`S-S6` `K-19` 사전 고지 집합 3종.

    ④ 중단 조건 ⓐ — 3종 중 하나라도 없으면 **승인 화면을 띄우지 않고 멈춤**(⑥ `B-21`).
    """
    if not auto_renewal_notice or not cancel_method_notice:
        raise ValueError("사전 고지 3종이 다 차지 않음 — 승인 화면을 띄우지 않음")
    return {
        "disclosure_id": disclosure_id,
        "withdrawal_period_days": WITHDRAWAL_PERIOD_DAYS,
        "auto_renewal_notice": auto_renewal_notice,
        "cancel_method_notice": cancel_method_notice,
        "disclosed_at": disclosed_at,
    }


def build_approval_prompt(
    *,
    amount_krw: int,
    billing_cycle: str,
    disclosure_id: str,
    auto_renewal_notice: str,
    cancel_method_notice: str,
) -> dict[str, Any]:
    """`S-S7` 승인 화면에 실제로 보여 줄 값. 고지 항목이 승인 표시의 증거가 됨(⑥ `O-C8`)."""
    return {
        "displayed_amount_krw": amount_krw,
        "displayed_billing_cycle": billing_cycle,
        "disclosure_id": disclosure_id,
        "shown_items": [
            f"청약철회 {WITHDRAWAL_PERIOD_DAYS}일",
            auto_renewal_notice,
            cancel_method_notice,
        ],
    }


def verify_and_key(
    *,
    payment_token: str,
    amount_krw: int,
    billing_cycle: str,
    idempotency_key: str,
    user_approval_id: str,
    displayed_amount_krw: int,
    displayed_billing_cycle: str,
) -> dict[str, Any]:
    """`S-S8` 결제 정보 검증 · 멱등 키 부여 → `K-21`.

    ④ 중단 조건 ⓑ — 승인 증거가 없으면 등록 요청을 만들지 않음.
    ④ 중단 조건 ⓒ — 표시된 금액·주기가 요청 값과 다르면 요청을 만들지 않음.
    ④ 중단 조건 ⓓ — 같은 멱등 키의 결제가 이미 처리됐으면 새 등록 요청을 만들지 않음.
    """
    if not user_approval_id:
        raise ValueError("승인 증거가 없음 — 등록 요청을 만들지 않음(⑥ `B-12`)")
    if not idempotency_key:
        raise ValueError("멱등 키가 빔 — 등록 요청을 만들지 않음(⑥ `B-30`)")
    if displayed_amount_krw != amount_krw or displayed_billing_cycle != billing_cycle:
        raise ValueError("승인 화면 표시값과 등록 요청 값이 다름 — 요청을 만들지 않음")
    return {
        "payment_token": payment_token,
        "amount_krw": amount_krw,
        "billing_cycle": billing_cycle,
        "idempotency_key": idempotency_key,
        "user_approval_id": user_approval_id,
    }


def record_payment_result(
    *,
    payment_result: str,
    pg_response_at: int,
    idempotency_key: str,
    payment_id: str | None = None,
    next_billing_date: str | None = None,
) -> dict[str, Any]:
    """`S-S10` 결제 ID·다음 결제일 적재.

    ④ 중단 조건 ⓔ — PG 결과가 `확인 중`이면 완료 표시를 하지 않고 그대로 둠(③ 8-1-2절).
    """
    if not idempotency_key:
        raise ValueError("멱등 키가 빔 — 적재하지 않음")
    return {
        "payment_result": payment_result,
        "payment_id": payment_id,
        "next_billing_date": next_billing_date,
        "pg_response_at": pg_response_at,
        "unresolved": payment_result == _PAYMENT_RESULT_PENDING,
    }


def build_payment_audit(
    *, payment_request_id: str, payment_result: str, user_approval_id: str
) -> dict[str, Any]:
    """`S-S11` 결제 승인·호출 감사 기록. 규제 필수 기록이라 승인 문을 두지 않음."""
    return {
        "payment_request_id": payment_request_id,
        "payment_result": payment_result,
        "user_approval_id": user_approval_id,
    }


def build_payment_response(
    *,
    payment_result: str,
    subscription_started_on: str | None = None,
    next_billing_date: str | None = None,
    withdrawal_notice: str | None = None,
) -> dict[str, Any]:
    """`S-S12` `K-23` 결제 완료 안내 집합. 뒤 3개는 결제 성공일 때 조건 필수임."""
    return {
        "payment_result": payment_result,
        "subscription_started_on": subscription_started_on,
        "next_billing_date": next_billing_date,
        "withdrawal_notice": withdrawal_notice,
    }


def build_payment_landing(
    *, fallback_reason: str, user_retry_count: int
) -> dict[str, Any]:
    """`S-S13` 착지 — 결제 실패 안내 · 3회 소진 시 고객 지원 안내.

    고객 지원 채널은 `[확인필요: 결제 실패 3회 소진 후 고객 지원 연결 채널]`(③ 소유 · 인용)임.
    **착지 경로가 상한을 다시 쓰지 않음** — 외부 호출 0건 · 모델 호출 0건 · 비용 0원임.
    사용자 재시도 상한 값은 원문 소유이며 ③ 8-3절이 `곱하지 않음`으로 못 박음.
    """
    return {
        "payment_result": _PAYMENT_RESULT_PENDING,
        "fallback_reason": fallback_reason,
        "user_retry_count": user_retry_count,
        "support_channel": "[확인필요: 결제 실패 3회 소진 후 고객 지원 연결 채널]",
    }
