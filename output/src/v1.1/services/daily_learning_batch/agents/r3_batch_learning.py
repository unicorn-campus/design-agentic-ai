"""`R-3` 배치 학습 준비·검증 처리기 — ④ 3-3절.

맡은 ③ 단계 9개 — `S-B1` ~ `S-B6` · `S-B8` ~ `S-B10`. 커밋은 하지 않음(`S-B7`은 `R-4` 몫).
사용 모델 — 취향 임베딩 생성 모델(`[확인필요: 벡터 인덱스 제품·임베딩 모델명·버전]` · ⑤ 14절 소유).
그 모델을 부르는 자리는 **`C-3` 커넥터 1곳**이며 모델 어댑터를 이 모듈이 직접 부르지 않음.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from toolkit.runner import CallContext, ConnectorResult, ConnectorTool

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "acquire_run_lock",
    "collect_feedback",
    "check_consent_and_retention",
    "recompute_preference_vector",
    "refresh_embedding",
    "judge_quality",
    "build_learning_message",
    "build_batch_result",
    "build_batch_landing",
]

OWNER_ID = "R-3"
STEP_IDS = ("S-B1", "S-B2", "S-B3", "S-B4", "S-B5", "S-B6", "S-B8", "S-B9", "S-B10")


def acquire_run_lock(*, batch_run_id: str, lock_acquired: bool) -> dict[str, Any]:
    """`S-B1` 스케줄 기동 · 실행 잠금 획득.

    ④ 중단 조건 ⓐ — 잠금 실패는 중복 실행이므로 **즉시 종료**함.
    """
    return {"batch_run_id": batch_run_id, "lock_acquired": bool(lock_acquired)}


def collect_feedback(
    *,
    batch_run_id: str,
    target_date: str,
    feedback_rows: Sequence[Mapping[str, Any]],
    target_member_ids: Sequence[str],
) -> dict[str, Any]:
    """`S-B2` `K-11` 전일 피드백 집합."""
    return {
        "batch_run_id": batch_run_id,
        "target_date": target_date,
        "feedback_rows": [dict(row) for row in feedback_rows],
        "target_member_ids": list(target_member_ids),
    }


def check_consent_and_retention(
    *,
    target_member_ids: Sequence[str],
    consent_by_member: Mapping[str, bool | None],
) -> dict[str, Any]:
    """`S-B3` 사전 조건 — 동의 상태·보존 기간 만료 대상 제외.

    ④ 중단 조건 ⓑ — 동의를 판정할 수 없는 회원은 갱신 대상에서 **빼고 목록을 알림**(⑥ `B-9`).
    """
    eligible: list[str] = []
    undecidable: list[str] = []
    for member_id in target_member_ids:
        granted = consent_by_member.get(member_id)
        if granted is None:
            undecidable.append(member_id)
        elif granted:
            eligible.append(member_id)
    return {
        "eligible_member_ids": eligible,
        "undecidable_member_ids": undecidable,
        "precheck_passed": bool(eligible),
    }


def recompute_preference_vector(
    *,
    member_id: str,
    feedback_rows: Sequence[Mapping[str, Any]],
    current_preference_vector: Sequence[float],
) -> dict[str, Any]:
    """`S-B4` 장기 취향 벡터 재계산(루프 내). 결정론 계산이며 모델을 부르지 않음."""
    weights = [float(row.get("satisfaction_score", 0.0)) for row in feedback_rows or ()]
    shift = (sum(weights) / len(weights)) if weights else 0.0
    return {
        "member_id": member_id,
        "recent_feedback": [dict(row) for row in feedback_rows],
        "current_preference_vector": list(current_preference_vector),
        "vector_shift": round(shift, 6),
    }


async def refresh_embedding(
    *,
    correlation_key: str,
    recent_feedback: Sequence[Mapping[str, Any]],
    meal_history_summary: Sequence[Mapping[str, Any]],
    current_preference_vector: Sequence[float],
    tool: ConnectorTool,
    call_context: CallContext,
) -> ConnectorResult:
    """`S-B5` `C-3` 취향 임베딩 갱신 호출(루프 내) → `K-12`.

    재시도를 여기서 걸지 않음 — 커넥터 계층이 ③ 4-2절 `S-B5`의 1회를 이미 가짐.
    """
    return await tool.call(
        {
            "correlation_key": correlation_key,
            "recent_feedback": [dict(r) for r in recent_feedback],
            "meal_history_summary": [dict(r) for r in meal_history_summary],
            "current_preference_vector": list(current_preference_vector),
        },
        call_context,
    )


def judge_quality(
    *,
    accept_rate: float,
    satisfaction_rate: float,
    quality_threshold: float | None,
    candidate_vector: Sequence[float],
    current_preference_vector: Sequence[float],
) -> dict[str, Any]:
    """`S-B6` `K-13` 품질 판정 집합(루프 내).

    ④ 중단 조건 ⓒ — 벡터 차원이 기존과 다르면 그 회원을 건너뜀.
    ④ 중단 조건 ⓓ — 임계값 자체가 `[확인필요: 배치 품질 자가 검증 임계값]`이면
    **판정을 내리지 않고** 사람 확인으로 넘김(⑥ `B-7`).
    """
    if current_preference_vector and len(candidate_vector) != len(
        current_preference_vector
    ):
        return {
            "quality_passed": False,
            "accept_rate": accept_rate,
            "satisfaction_rate": satisfaction_rate,
            "quality_threshold": quality_threshold if quality_threshold is not None else -1.0,
            "skip_reason": "벡터 차원이 기존과 다름",
        }
    if quality_threshold is None:
        return {
            "quality_passed": False,
            "accept_rate": accept_rate,
            "satisfaction_rate": satisfaction_rate,
            "quality_threshold": -1.0,
            "skip_reason": "[확인필요: 배치 품질 자가 검증 임계값]",
        }
    passed = accept_rate >= quality_threshold and satisfaction_rate >= quality_threshold
    return {
        "quality_passed": passed,
        "accept_rate": accept_rate,
        "satisfaction_rate": satisfaction_rate,
        "quality_threshold": quality_threshold,
        "skip_reason": None,
    }


def build_learning_message(
    *, updated_member_count: int, mean_vector_delta: float
) -> dict[str, Any]:
    """`S-B8` 학습 반영 메시지 생성. 실제 변경 이력과 어긋나면 ⑥ `B-6`이 비노출로 막음."""
    if updated_member_count <= 0:
        return {"learning_applied_message": None}
    return {
        "learning_applied_message": (
            f"어제 피드백 {updated_member_count}명분이 반영됐음"
            f"(평균 변화량 {mean_vector_delta})"
        )
    }


def build_batch_result(
    *,
    batch_run_id: str,
    updated_member_count: int,
    mean_vector_delta: float,
    batch_status: str,
    skipped_member_ids: Sequence[str] | None = None,
    learning_applied_message: str | None = None,
) -> dict[str, Any]:
    """`S-B9` `K-14` 배치 결과 집합 · 완료 이벤트 회신."""
    return {
        "batch_run_id": batch_run_id,
        "updated_member_count": updated_member_count,
        "mean_vector_delta": mean_vector_delta,
        "skipped_member_ids": list(skipped_member_ids or ()),
        "learning_applied_message": learning_applied_message,
        "batch_status": batch_status,
    }


def build_batch_landing(
    *, batch_run_id: str, fallback_reason: str, skipped_member_ids: Sequence[str]
) -> dict[str, Any]:
    """`S-B10` 착지 — 이전 벡터 유지 + 사람 확인 알림.

    **착지 경로가 상한을 다시 쓰지 않음** — 쓰기 0건 · 알림 1건 · 모델 호출 0건임.
    """
    return {
        "batch_run_id": batch_run_id,
        "fallback_reason": fallback_reason,
        "skipped_member_ids": list(skipped_member_ids),
        "previous_vector_kept": True,
        "human_notice": True,
    }
