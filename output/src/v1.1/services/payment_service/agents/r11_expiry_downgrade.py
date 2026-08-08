"""`R-11` 해지 만료 무료 전환 배치 처리기 — ④ 3-11절.

맡은 ③ 단계 7개 — `S-X1` ~ `S-X5` · `S-X7` · `S-X8`.
사용 모델 — **모델 미사용(결정론적 실행).** ③ 8-2절 `L-3`도 이 루프의 모델 호출을 0건으로 계산함.
사용 도구 — `T-12` 조회 `읽기` · `S-7` 상태 전환 커밋 · `S-1` 상태 전파 · `S-6` 감사 로그 적재.
**되돌림 불가 쓰기 0건** — 이력 보관 기간 재적용은 `R-16` 소관임.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from common.knowledge.prefilter import expiry_downgrade_filter

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "GUARD_NAMES",
    "RETENTION_DAYS_FREE",
    "acquire_run_lock",
    "collect_targets",
    "check_transition_precondition",
    "commit_downgrade",
    "propagate_state",
    "build_transition_audit",
    "build_expiry_landing",
]

OWNER_ID = "R-11"
STEP_IDS = ("S-X1", "S-X2", "S-X3", "S-X4", "S-X5", "S-X7", "S-X8")

GUARD_NAMES = (
    "precondition_passed",
    "idempotency_key",
    "run_lock",
    "target_count_cap",
    "keep_previous_on_failure",
    "operator_post_notice",
)
"""⑥ 3-1절 `R-11` 행의 `guards` 6개. 이름을 여기서 짓지 않고 ⑥ 값을 인용함."""

RETENTION_DAYS_FREE = 30
"""④ `K-31`이 `30 고정`으로 적은 값 — `US:UFR-PAY-030#검증`임. 단계 상한이 아님."""


def acquire_run_lock(
    *, batch_run_id: str, run_started_at: int, execution_lock_id: str
) -> dict[str, Any]:
    """`S-X1` 스케줄 기동 · 실행 잠금 획득.

    ④ 중단 조건 ⓐ — 잠금 실패는 중복 실행이므로 **즉시 종료**함.
    """
    if not execution_lock_id:
        raise RuntimeError("실행 잠금 실패 — 중복 실행이므로 즉시 종료")
    return {
        "batch_run_id": batch_run_id,
        "run_started_at": run_started_at,
        "execution_lock_id": execution_lock_id,
    }


def collect_targets(
    *, batch_run_id: str, target_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """`S-X2` `K-30` 전환 대상 집합."""
    rows = [
        {
            "member_id": str(row.get("member_id", "")),
            "scheduled_downgrade_on": str(row.get("scheduled_downgrade_on", "")),
            "cancel_schedule_id": str(row.get("cancel_schedule_id", "")),
        }
        for row in target_rows
    ]
    return {
        "batch_run_id": batch_run_id,
        "target_rows": rows,
        "target_count": len(rows),
    }


def check_transition_precondition(
    *,
    member_id: str,
    scheduled_downgrade_on: str | None,
    run_on: str | None,
    cancel_withdrawn: bool | None,
    payment_grace_elapsed: bool | None,
) -> dict[str, Any]:
    """`S-X3` 사전 조건 — 해지 철회 여부·결제 실패 7일 유예 경과(루프 내).

    ④ 중단 조건 ⓑ — 판정할 수 없으면 그 회원을 전환하지 않고 목록을 알림(⑥ `B-26`).
    """
    verdict = expiry_downgrade_filter(
        downgrade_scheduled_on=scheduled_downgrade_on,
        run_on=run_on,
        cancel_withdrawn=cancel_withdrawn,
        payment_grace_elapsed=payment_grace_elapsed,
    )
    return {
        "member_id": member_id,
        "precheck_passed": verdict.passed,
        "skip_reason": None if verdict.passed else verdict.reason,
    }


def commit_downgrade(
    *,
    member_id: str,
    downgrade_idempotency_key: str,
    view_cutoff_on: str,
    committed_at: int,
) -> dict[str, Any]:
    """`S-X4` 구독 상태 무료 전환 커밋(루프 내) → `K-31`.

    ④ 중단 조건 ⓒ — 같은 멱등 키는 다시 전환하지 않음(⑥ `B-30`).
    """
    if not downgrade_idempotency_key:
        raise ValueError("중복 방지 키가 빔 — 전환하지 않음(⑥ `B-30`)")
    if not view_cutoff_on:
        raise ValueError("열람 제한 기준일이 빔 — 전환하지 않음")
    return {
        "member_id": member_id,
        "retention_policy": "30일",
        "retention_days": RETENTION_DAYS_FREE,
        "view_cutoff_on": view_cutoff_on,
        "downgrade_idempotency_key": downgrade_idempotency_key,
        "committed_at": committed_at,
    }


def propagate_state(*, member_id: str, plan_type: str) -> dict[str, Any]:
    """`S-X5` 구독 상태 갱신 전파 — 무료(루프 내)."""
    return {"member_id": member_id, "plan_type": plan_type}


def build_transition_audit(
    *, member_id: str, downgrade_idempotency_key: str, committed_at: int
) -> dict[str, Any]:
    """`S-X7` 전환 실행 기록(루프 내). 규제 필수 기록이라 승인 문을 두지 않음."""
    return {
        "member_id": member_id,
        "downgrade_idempotency_key": downgrade_idempotency_key,
        "committed_at": committed_at,
    }


def build_expiry_landing(
    *,
    batch_run_id: str,
    downgraded_member_count: int,
    skipped_member_ids: Sequence[str],
    fallback_reason: str,
) -> dict[str, Any]:
    """`S-X8` 착지 — 이전 상태(프리미엄) 유지 + 사람 확인 알림.

    사용자에게 불리한 자동 강등을 하지 않음(③ 4-8절).
    **착지 경로가 상한을 다시 쓰지 않음** — 쓰기 0건 · 알림 1건임.
    """
    return {
        "batch_run_id": batch_run_id,
        "downgraded_member_count": downgraded_member_count,
        "skipped_member_ids": list(skipped_member_ids),
        "batch_status": "사람 확인",
        "fallback_reason": fallback_reason,
        "previous_state_kept": True,
        "human_notice": True,
    }
