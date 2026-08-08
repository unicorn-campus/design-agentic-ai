"""`R-9` 구독 해지 예약 처리기 — ④ 3-9절.

맡은 ③ 단계 9개 — `S-C2` ~ `S-C9` · `S-C11`.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `T-12` 조회 `읽기`(PG 결제 ID 포함 · ⑤ 4절 `D-8` 예외 행) ·
`S-7` 해지 예약 등록 `쓰기(되돌림 가능)` · `S-6` 감사 로그 적재.
**되돌림 불가 쓰기 0건** — PG 중지 호출은 `R-10` 소관이라 이 담당자의 도구에 없음.
"""

from __future__ import annotations

from typing import Any

from common.knowledge.prefilter import cancel_confirm_filter

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "accept_cancel_request",
    "check_cancel_precondition",
    "build_winback_offer",
    "build_confirm_prompt",
    "collect_cancel_reason",
    "register_cancel_schedule",
    "build_cancel_audit",
    "build_cancel_response",
    "build_pg_stop_request",
    "build_cancel_landing",
]

OWNER_ID = "R-9"
STEP_IDS = (
    "S-C2", "S-C3", "S-C4", "S-C5", "S-C6", "S-C7", "S-C8", "S-C9", "S-C11",
)

CANCEL_REASON_CODES = ("가격", "사용빈도", "추천품질", "기타")
"""④ `K-26` 선택형 4종. 값은 `[확인필요: 해지 사유 고정 라벨 4종의 값]`(⑥ 소유)이라 자리만 둠."""


def accept_cancel_request(
    *,
    cancel_request_id: str,
    member_id: str,
    requested_at: int,
    deadline_at: int,
    trigger_kind: str,
) -> dict[str, Any]:
    """`S-C2` 진입 값(③에 집합 식별자 없음)."""
    return {
        "cancel_request_id": cancel_request_id,
        "member_id": member_id,
        "requested_at": requested_at,
        "deadline_at": deadline_at,
        "trigger_kind": trigger_kind,
    }


def check_cancel_precondition(
    *,
    cancel_request_id: str,
    member_id: str,
    remaining_days: int | None,
    scheduled_downgrade_on: str | None,
    winback_offer_used: bool | None,
    retention_notice: str,
    pg_payment_id: str | None,
) -> dict[str, Any]:
    """`S-C3` `K-24` 해지 사전 조건 집합.

    ④ 중단 조건 ⓐ — 구독 상태를 읽을 수 없으면 **예약하지 않고 멈춤.**
    ④ 중단 조건 ⓓ — PG 결제 ID를 읽을 수 없으면 예약은 그대로 두고 중지 요청을 만들지 않음.
    """
    readable = (
        remaining_days is not None
        and scheduled_downgrade_on is not None
        and winback_offer_used is not None
    )
    return {
        "cancel_request_id": cancel_request_id,
        "member_id": member_id,
        "remaining_days": remaining_days,
        "scheduled_downgrade_on": scheduled_downgrade_on,
        "winback_offer_used": winback_offer_used,
        "retention_notice": retention_notice,
        "pg_payment_id": pg_payment_id,
        "precheck_passed": readable,
        "pg_payment_id_readable": bool(pg_payment_id),
    }


def build_winback_offer(*, winback_offer_used: bool) -> dict[str, Any]:
    """`S-C4` 복귀 유도 제안 표시 — 7일 무료 연장 1회 한정. 없으면 그냥 해지 흐름을 감."""
    return {
        "winback_offer_available": not winback_offer_used,
        "winback_offer_label": None if winback_offer_used else "7일 무료 연장",
    }


def build_confirm_prompt(
    *, remaining_days: int, retention_notice: str
) -> dict[str, Any]:
    """`S-C5` 확인 모달에 실제로 보여 줄 값(⑥ `O-C9`의 통과 증거가 됨)."""
    return {
        "displayed_remaining_days": remaining_days,
        "displayed_retention_notice": retention_notice,
        "shown_items": [f"남은 기간 {remaining_days}일", retention_notice],
    }


def collect_cancel_reason(*, cancel_reason_code: str | None) -> dict[str, Any]:
    """`S-C6` 해지 사유 수집 — `K-26`은 **선택**임(③ 4-6절이 `사유는 필수 아님`이라 적음)."""
    return {"cancel_reason_code": cancel_reason_code}


def register_cancel_schedule(
    *,
    cancel_schedule_id: str,
    scheduled_downgrade_on: str,
    remaining_days: int,
    retention_notice: str,
    cancel_idempotency_key: str,
    cancel_confirm_id: str | None,
    confirmed_at: str | None,
) -> dict[str, Any]:
    """`S-C7` `K-27` 해지 예약 결과 집합.

    ④ 중단 조건 ⓑ — 확인 플래그가 없거나 만료면 예약하지 않음(⑥ `B-13` · 결정론 필터 `PF-2`).
    ④ 중단 조건 ⓒ — 같은 멱등 키는 다시 예약하지 않음(⑥ `B-30`).
    """
    verdict = cancel_confirm_filter(cancel_confirm_id, confirmed_at)
    if not verdict.passed:
        raise PermissionError(f"해지 확인 증거 미통과 — {verdict.reason}")
    if not cancel_idempotency_key:
        raise ValueError("중복 방지 키가 빔 — 예약하지 않음(⑥ `B-30`)")
    return {
        "cancel_schedule_id": cancel_schedule_id,
        "cancel_state": "해지예약",
        "scheduled_downgrade_on": scheduled_downgrade_on,
        "remaining_days": remaining_days,
        "retention_notice": retention_notice,
        "cancel_idempotency_key": cancel_idempotency_key,
    }


def build_cancel_audit(
    *, cancel_schedule_id: str, cancel_reason_code: str | None, cancel_idempotency_key: str
) -> dict[str, Any]:
    """`S-C8` 해지 예약 감사 기록. 규제 필수 기록이라 승인 문을 두지 않음."""
    return {
        "cancel_schedule_id": cancel_schedule_id,
        "cancel_reason_code": cancel_reason_code,
        "cancel_idempotency_key": cancel_idempotency_key,
    }


def build_cancel_response(
    *,
    cancel_schedule_id: str,
    cancel_state: str,
    scheduled_downgrade_on: str,
    remaining_days: int,
    retention_notice: str,
    cancel_idempotency_key: str,
) -> dict[str, Any]:
    """`S-C9` 해지 예약 완료 표시 — `K-27` 키를 그대로 냄."""
    return {
        "cancel_schedule_id": cancel_schedule_id,
        "cancel_state": cancel_state,
        "scheduled_downgrade_on": scheduled_downgrade_on,
        "remaining_days": remaining_days,
        "retention_notice": retention_notice,
        "cancel_idempotency_key": cancel_idempotency_key,
    }


def build_pg_stop_request(
    *,
    pg_payment_id: str | None,
    cancel_schedule_id: str | None,
    pg_cancel_idempotency_key: str,
) -> dict[str, Any]:
    """`S-C7` → `S-C10`으로 보내는 `K-36` PG 중지 요청 집합.

    사전 조건 — **해지 예약이 방금 등록됨**(`S-C7` 커밋 성공). 예약이 없으면 부르지 않음.
    """
    return {
        "pg_payment_id": pg_payment_id,
        "cancel_schedule_id": cancel_schedule_id,
        "pg_cancel_idempotency_key": pg_cancel_idempotency_key,
    }


def build_cancel_landing(*, fallback_reason: str) -> dict[str, Any]:
    """`S-C11` 착지 — 해지 요청 접수 안내 + 고객 지원 연결 안내.

    **착지 경로가 상한을 다시 쓰지 않음** — 외부 호출 0건 · 모델 호출 0건 · 비용 0원임.
    """
    return {
        "cancel_state": "접수",
        "fallback_reason": fallback_reason,
        "support_channel": "[확인필요: 결제 실패 3회 소진 후 고객 지원 연결 채널]",
    }
