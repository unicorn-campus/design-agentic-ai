"""재개 진입점과 중복 방지 키 — ③ 11절 「재개 경계」를 그대로 옮긴 표.

`재개 안 함`으로 판정된 트리거는 **재개 진입점을 만들지 않았음** — `S-R`(사람이 기다림) ·
`S-I`(읽기 전용 · 부작용 0건) 2종임.

중간 저장은 `01`이 만든 중간 저장 장치(`common.checkpointer.open_checkpointer`)를 부름 —
저장 장치를 여기서 새로 만들지 않음.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from common.state import TriggerKind

__all__ = [
    "ResumeBoundary",
    "RESUME_BOUNDARIES",
    "NO_RESUME_TRIGGERS",
    "boundaries_of",
    "boundary_of_step",
    "side_effect_steps",
]


@dataclass(frozen=True, slots=True)
class ResumeBoundary:
    """③ 11절 표 1행. 여기까지는 **끝난 것으로 인정**하고 다음부터 다시 돌게 함."""

    trigger_kind: TriggerKind
    section: str
    resume_unit: str
    boundary_step: str
    side_effect: bool
    idempotency_scope: str
    """중복 방지 키의 앞자리. `common.checkpointer.build_idempotency_key`의 첫 인자로 씀."""
    idempotency_parts: tuple[str, ...]
    """③이 정한 조합 키의 조각 이름. 값은 흐름이 넣음."""


RESUME_BOUNDARIES: tuple[ResumeBoundary, ...] = (
    ResumeBoundary(
        TriggerKind.BATCH_PREFERENCE_LEARNING,
        "배치",
        "회원 1명",
        "S-B7",
        True,
        "member_and_target_date",
        ("member_id", "target_date"),
    ),
    ResumeBoundary(
        TriggerKind.EVENT_PIPELINE,
        "구획1",
        "피드백 1건",
        "S-E3",
        True,
        "record_and_member",
        ("meal_record_id", "member_id"),
    ),
    ResumeBoundary(
        TriggerKind.EVENT_PIPELINE,
        "구획2",
        "회원 1명",
        "S-E6",
        True,
        "member_and_onboarding_round",
        ("member_id", "onboarding_round"),
    ),
    ResumeBoundary(
        TriggerKind.SYNC_SUBSCRIBE,
        "결제",
        "결제 요청 1건",
        "S-S9",
        True,
        "member_plan_and_payment_idempotency",
        ("member_id", "plan_type", "payment_request_id"),
    ),
    ResumeBoundary(
        TriggerKind.SYNC_CANCEL,
        "해지",
        "해지 요청 1건",
        "S-C7",
        True,
        "member_and_scheduled_downgrade_on",
        ("member_id", "scheduled_downgrade_on"),
    ),
    ResumeBoundary(
        TriggerKind.SYNC_CANCEL,
        "PG 중지 후처리",
        "해지 1건",
        "S-C10",
        True,
        "pg_payment_and_stop",
        ("pg_payment_id", "cancel_schedule_id"),
    ),
    ResumeBoundary(
        TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION,
        "구획1",
        "알림 1건",
        "S-N3",
        True,
        "member_and_expiring_baseline",
        ("member_id", "expiring_baseline_on"),
    ),
    ResumeBoundary(
        TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION,
        "구획2",
        "결제 1건",
        "S-N6",
        True,
        "payment_id",
        ("payment_id",),
    ),
    ResumeBoundary(
        TriggerKind.BATCH_CANCEL_EXPIRY,
        "배치",
        "회원 1명",
        "S-X4",
        True,
        "member_and_scheduled_downgrade_on",
        ("member_id", "scheduled_downgrade_on"),
    ),
)
"""③ 11절 「재개 경계」에서 `재실행 부작용 = 있음`인 **9건** 전부임. 중복 방지 키 공란 0건."""

NO_RESUME_TRIGGERS: Mapping[TriggerKind, str] = MappingProxyType(
    {
        TriggerKind.SYNC_RECOMMEND: "재개 안 함 — 사람이 기다림(③ 11절)",
        TriggerKind.SYNC_INSIGHT: "재개 안 함 — 읽기 전용이라 부작용 0건(③ 11절)",
    }
)


def boundaries_of(trigger_kind: TriggerKind) -> tuple[ResumeBoundary, ...]:
    return tuple(row for row in RESUME_BOUNDARIES if row.trigger_kind is trigger_kind)


def boundary_of_step(step_id: str) -> ResumeBoundary | None:
    for row in RESUME_BOUNDARIES:
        if row.boundary_step == step_id:
            return row
    return None


def side_effect_steps() -> frozenset[str]:
    """재실행 부작용이 있어 중복 방지 키를 **반드시** 걸어야 하는 단계 목록."""
    return frozenset(row.boundary_step for row in RESUME_BOUNDARIES if row.side_effect)
