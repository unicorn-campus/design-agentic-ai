"""노드 공통 처리 — 남은 시간 확인 · 검사 훅 · 기록 · 착지 신호.

**재시도가 여기 없음.** 재시도는 커넥터 1계층(`common.external_call.call_with_limits`)뿐이며
`04-connector`가 그것을 부르는 자리를 1곳으로 못 박아 두었음. 노드나 그래프에 또 붙이면
횟수가 곱해지므로 이 파일에 재시도 루프가 **0건**임.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from common.budget import DeadlineTooTight, ensure_step_can_start, now_ms, read_deadline_at
from common.config import SettingsMissing
from common.state import LunchPickState

from .context import FlowContext
from .signals import LandingReason, halt_to_landing
from .steps import BUDGET_EXEMPT_STEPS

__all__ = ["DeadlineVerdict", "check_deadline", "TIMEOUT_UNSET_TAG"]

TIMEOUT_UNSET_TAG = "[확인필요: 이 단계의 시간 제한 값이 설정에 없음]"


@dataclass(frozen=True, slots=True)
class DeadlineVerdict:
    """마감선 판정 결과. `update`가 비어 있지 않으면 그대로 돌려주고 착지로 감."""

    can_start: bool
    remaining_ms: int | None
    update: dict[str, Any]
    note: str | None = None

    @property
    def blocked(self) -> bool:
        return not self.can_start


def check_deadline(
    step_id: str,
    state: LunchPickState,
    context: FlowContext,
) -> DeadlineVerdict:
    """단계가 시작하기 **전에** 남은 시간을 봄. 모자라면 실행하지 않고 착지로 감.

    ③ 6절이 착지 경로를 진입선에서 이미 뺐으므로 여기서 착지 시간을 다시 더하지 않음.
    예산 밖 단계(단말 구간 · 사람 대기 · 응답 후 후처리)는 어느 마감선에도 들어가지 않으므로 건너뜀.
    """
    if step_id in BUDGET_EXEMPT_STEPS:
        return DeadlineVerdict(can_start=True, remaining_ms=None, update={},
                               note="예산 밖 단계 — ③ 4절 「p95 배정」 인용")

    try:
        deadline_at = read_deadline_at(state)
    except DeadlineTooTight:
        # 진입 노드가 마감선을 아직 넣지 않은 자리 — 진입 노드 자신이 여기 해당함.
        return DeadlineVerdict(can_start=True, remaining_ms=None, update={},
                               note="진입 노드 — 마감선을 이 단계가 넣음")

    try:
        ensure_step_can_start(step_id, deadline_at, context.settings, at_ms=now_ms())
    except SettingsMissing:
        # 값이 없으면 지어내지 않음. 판정을 못 했다는 사실만 남기고 흐름은 계속함.
        return DeadlineVerdict(
            can_start=True,
            remaining_ms=deadline_at - now_ms(),
            update={},
            note=TIMEOUT_UNSET_TAG,
        )
    except DeadlineTooTight as tight:
        return DeadlineVerdict(
            can_start=False,
            remaining_ms=tight.remaining,
            update=halt_to_landing(
                step_id,
                LandingReason.DEADLINE_TOO_TIGHT,
                {"remaining_ms": tight.remaining, "required_ms": tight.required},
            ),
        )
    return DeadlineVerdict(
        can_start=True, remaining_ms=deadline_at - now_ms(), update={}
    )


def merged(*updates: Mapping[str, Any] | None) -> dict[str, Any]:
    """상태 업데이트 여러 조각을 합침. 목록형 필드는 이어 붙임(③ 6절 병합 규칙과 같은 방향)."""
    out: dict[str, Any] = {}
    for update in updates:
        if not update:
            continue
        for key, value in update.items():
            if key in out and isinstance(out[key], list) and isinstance(value, list):
                out[key] = [*out[key], *value]
            else:
                out[key] = value
    return out
