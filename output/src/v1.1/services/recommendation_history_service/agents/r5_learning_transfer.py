"""`R-5` 학습 데이터 전달 처리기 — ④ 3-5절.

맡은 ③ 단계 5개 — `S-E1` ~ `S-E4` · `S-E8`.
사용 모델 — **모델 미사용(결정론적 실행).**
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "receive_feedback_signal",
    "check_undo_window",
    "build_transfer",
    "build_receipt",
    "build_undelivered_entry",
]

OWNER_ID = "R-5"
STEP_IDS = ("S-E1", "S-E2", "S-E3", "S-E4", "S-E8")


def receive_feedback_signal(
    *, meal_record_id: str, member_id: str, feedback_submitted_at: int
) -> dict[str, Any]:
    """`S-E1` 저장 완료 신호 수신 — 진입 값을 그대로 담음."""
    return {
        "meal_record_id": meal_record_id,
        "member_id": member_id,
        "feedback_submitted_at": feedback_submitted_at,
    }


def check_undo_window(*, undo_window_elapsed: bool) -> dict[str, Any]:
    """`S-E2` 사전 조건 — 30초 실행취소 창 경과 확인.

    ④ 중단 조건 ⓐ — 창 안이면 전달을 **보류**함(⑥ `B-8`).
    """
    return {"undo_window_elapsed": bool(undo_window_elapsed),
            "precheck_passed": bool(undo_window_elapsed)}


def build_transfer(
    *,
    transfer_id: str,
    member_id: str,
    meal_record_id: str,
    satisfaction: str,
    context_snapshot: Mapping[str, Any],
    idempotency_key: str,
    feedback_keyword: str | None = None,
) -> dict[str, Any]:
    """`S-E3` `K-15` 학습 데이터 전달 집합.

    ④ 중단 조건 ⓒ — 컨텍스트 스냅샷이 비면 전달하지 않고 미전달 큐로 넘김.
    """
    if not context_snapshot:
        raise ValueError("컨텍스트 스냅샷이 빔 — 전달하지 않고 미전달 큐로 넘김")
    return {
        "transfer_id": transfer_id,
        "member_id": member_id,
        "meal_record_id": meal_record_id,
        "satisfaction": satisfaction,
        "feedback_keyword": feedback_keyword,
        "context_snapshot": dict(context_snapshot),
        "idempotency_key": idempotency_key,
    }


def build_receipt(*, transfer_id: str, idempotency_key: str) -> dict[str, Any]:
    """`S-E4` 수신 확인 회신 · 감사 로그 적재에 넘길 값."""
    return {"transfer_id": transfer_id, "idempotency_key": idempotency_key,
            "acknowledged": True}


def build_undelivered_entry(
    *, transfer_id: str, fallback_reason: str
) -> dict[str, Any]:
    """`S-E8` 착지 — 미전달 큐 적재 + 사람 확인 알림.

    큐 수단은 `[확인필요: 미전달 건의 대기열(DLQ) 유무·보관 위치]`(③ 소유 · 인용)임.
    **착지 경로가 상한을 다시 쓰지 않음** — 쓰기 1건 · 재시도 0건임.
    """
    return {
        "transfer_id": transfer_id,
        "fallback_reason": fallback_reason,
        "undelivered_queue_key": "[확인필요: 미전달 건의 대기열(DLQ) 유무·보관 위치]",
        "human_notice": True,
    }
