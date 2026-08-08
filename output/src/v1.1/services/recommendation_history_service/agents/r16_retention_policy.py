"""`R-16` 이력 보관 기간 적용 처리기 — ④ 3-16절.

맡은 ③ 단계 3개 — `S-N6` · `S-N7` · `S-X6`.
사용 모델 — **모델 미사용(결정론적 실행).**
사용 도구 — `S-3` 보관 기간 정책 적용 `쓰기(되돌림 가능)` 1개.
**기록 삭제 도구를 계약에 두지 않았음**(제한 장치 · ④ 7-2절) — 열람 제한과 삭제를 가름.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "RETENTION_POLICIES",
    "apply_retention_policy",
    "build_retention_reply",
]

OWNER_ID = "R-16"
STEP_IDS = ("S-N6", "S-N7", "S-X6")

RETENTION_POLICIES = ("무제한", "30일")
"""④ 중단 조건 ⓐ — 이 2값 밖이면 적용하지 않고 멈춤."""


def apply_retention_policy(
    *,
    member_id: str,
    retention_policy: str,
    idempotency_key: str,
    applied_at: int,
    view_cutoff_on: str | None = None,
    retention_days: int | None = None,
) -> dict[str, Any]:
    """`S-N6`(프리미엄 방향 `K-29`) · `S-X6`(무료 방향 `K-31`) 공통 적용 함수.

    ④ 중단 조건 ⓐ — 정책 값이 2값 밖이면 멈춤.
    ④ 중단 조건 ⓒ — 무료 방향인데 `view_cutoff_on`이 비면 멈춤
    (기준일 없는 제한은 과다 노출 또는 과다 차단이 됨).
    """
    if retention_policy not in RETENTION_POLICIES:
        raise ValueError(f"보관 기간 정책이 2값 밖임: {retention_policy!r}")
    if retention_policy == "30일" and not view_cutoff_on:
        raise ValueError("무료 방향인데 열람 제한 기준일이 빔 — 적용하지 않음")
    if not idempotency_key:
        raise ValueError("중복 방지 키가 빔 — 쓰기를 하지 않음(⑥ `B-30`)")
    return {
        "member_id": member_id,
        "retention_policy": retention_policy,
        "applied_at": applied_at,
        "retention_result": "적용",
        "retention_days": retention_days,
        "view_cutoff_on": view_cutoff_on,
        "deleted_record_count": 0,
    }


def build_retention_reply(
    *, member_id: str, retention_policy: str, applied_at: int, retention_result: str
) -> dict[str, Any]:
    """`S-N7` 회신 · `S-X6` 회신 공통 출력.

    ④ 중단 조건 ⓓ — 정책 적용이 확인되지 않았으면 회신하지 않음
    (호출한 쪽이 완료 표시를 못 하게 함).
    """
    if retention_result != "적용":
        raise ValueError("정책 적용이 확인되지 않음 — 회신하지 않음")
    return {
        "member_id": member_id,
        "retention_policy": retention_policy,
        "applied_at": applied_at,
        "retention_result": retention_result,
    }
