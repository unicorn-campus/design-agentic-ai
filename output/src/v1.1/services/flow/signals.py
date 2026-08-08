"""착지로 보내는 신호와 사유 코드.

**상태 필드를 새로 만들지 않았음**(필드 이름의 주인은 ③ 6절임).
착지로 가라는 신호는 ③ 6절 12번 `error_history`(누적 리듀서)에 한 줄을 붙이는 방식으로 전달하고,
9번 `fallback_reason`은 ③이 정한 대로 **착지 노드 1개만** 씀.

착지 = 상한을 넘겼을 때 흐름이 마지막으로 도착하는 자리임.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Mapping

from common.state import LunchPickState

__all__ = [
    "LandingReason",
    "halt_to_landing",
    "note_failure",
    "landing_reason_of",
    "is_landing_requested",
]


class LandingReason(StrEnum):
    """착지로 간 사유. `fallback_reason`에 남는 값이며 사유 없이 결과만 바꾸지 않음."""

    DEADLINE_TOO_TIGHT = "deadline_too_tight"
    """남은 시간이 그 단계 시간 제한보다 적어 실행 전에 갈라짐(③ 6절 진입선 규칙)."""
    STEP_EXHAUSTED = "step_exhausted"
    """커넥터 계층의 시간 제한·재시도를 다 쓰고도 못 끝냄."""
    PRECHECK_FAILED = "precheck_failed"
    """사전 조건 확인 미통과(④ 「중단 조건」)."""
    CANDIDATE_EMPTY = "candidate_empty"
    """후보 0건 — 추천을 만들지 않음(④ `R-2` ⓑ · ⓒ)."""
    HARD_FILTER_UNCERTAIN = "hard_filter_uncertain"
    APPROVAL_ABSENT = "approval_absent"
    """승인 문 미통과 — 되돌릴 수 없는 도구를 부르지 않음(⑥ `B-12` · `B-13` · `B-23`)."""
    TOOL_DENIED = "tool_denied"
    IDEMPOTENCY_REPLAYED = "idempotency_replayed"
    """같은 중복 방지 키가 이미 처리됨 — 바깥을 다시 부르지 않음."""
    PG_UNRESOLVED = "pg_unresolved"
    """PG 결과 미확정 — `확인 중`으로 두고 응답을 닫음(③ 8-1-2절)."""
    LOOP_LIMIT_REACHED = "loop_limit_reached"
    """반복 상한에 닿기 전 마지막 여유에서 갈라짐(③ 8-2절)."""
    LOOP_LIMIT_UNSET = "loop_limit_unset"
    """[확인필요] 반복 상한 값이 설정에 없음 — 상한 없이 돌리지 않고 착지로 감."""
    FLOW_STEP_CAP_REACHED = "flow_step_cap_reached"
    """흐름 전체 단계 상한(되묻기 1)에 닿아 프레임워크가 멈춤."""
    RUN_LOCK_FAILED = "run_lock_failed"
    """실행 잠금 실패 = 중복 실행이므로 즉시 종료(④ `R-3` ⓐ · `R-11` ⓐ)."""
    CONSISTENCY_MISMATCH = "consistency_mismatch"
    """통계 일치 검사 불일치 — 수치 없는 타임라인만 제시(`V-10` 11번)."""
    RECORD_COUNT_BELOW_MIN = "record_count_below_min"
    ALREADY_PREMIUM = "already_premium"
    DISCLOSURE_MISSING = "disclosure_missing"
    GUARDRAIL_BLOCKED = "guardrail_blocked"


_HALT_MARK = "to_landing"


def halt_to_landing(
    step_id: str,
    reason: LandingReason,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """착지로 가라는 신호 1줄을 `error_history`에 붙임. 상태 업데이트 형태로 돌려줌."""
    return {
        "error_history": [
            {
                "step_id": step_id,
                "reason_code": reason.value,
                _HALT_MARK: True,
                "detail": dict(detail or {}),
            }
        ]
    }


def note_failure(
    step_id: str,
    reason: LandingReason,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """착지로 보내지 않고 실패만 기록함(`부분 결과로 계속` 경로)."""
    return {
        "error_history": [
            {
                "step_id": step_id,
                "reason_code": reason.value,
                _HALT_MARK: False,
                "detail": dict(detail or {}),
            }
        ]
    }


def landing_reason_of(state: LunchPickState) -> str | None:
    """착지 신호가 있으면 그 사유 코드를 돌려줌. 없으면 `None`."""
    for row in state.get("error_history") or ():
        if isinstance(row, Mapping) and row.get(_HALT_MARK):
            return str(row.get("reason_code", LandingReason.STEP_EXHAUSTED.value))
    return None


def is_landing_requested(state: LunchPickState) -> bool:
    return landing_reason_of(state) is not None
