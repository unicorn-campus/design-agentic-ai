"""③ 4절 시퀀스 단계 90행을 코드에 그대로 옮긴 표. **단계를 합치거나 쪼개지 않음.**

여기에는 시간 제한·재시도·반복 상한 **숫자가 없음** — 값은 전부 `common.config`(=③ 소유)에서 읽음.
이 파일이 가진 것은 ⓐ 단계 이름 ⓑ 단계 순서 ⓒ 담당자 배정 ⓓ 착지 노드 ⓔ 루프 구간뿐임.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from common.state import TriggerKind

__all__ = [
    "STEP_IDS",
    "STEPS_BY_TRIGGER",
    "SECTIONS_BY_TRIGGER",
    "OWNER_BY_STEP",
    "STEPS_BY_OWNER",
    "LANDING_STEP_BY_TRIGGER",
    "ENTRY_STEPS_BY_TRIGGER",
    "PRECHECK_STEPS",
    "COMMIT_STEPS",
    "HUMAN_GATE_STEPS",
    "TERMINAL_STEPS",
    "POST_RESPONSE_STEPS",
    "BUDGET_EXEMPT_STEPS",
    "IRREVERSIBLE_TOOL_STEPS",
    "PARALLEL_GROUPS",
    "LOOPS",
    "LoopSpec",
    "OWNER_NAMES",
    "OWNER_SERVICE",
    "node_symbol_of",
    "trigger_of_step",
]


# ---------------------------------------------------------------------------
# ③ 4절 — 트리거별 단계 순서. 행 수와 노드 수가 같아야 함.
# ---------------------------------------------------------------------------
_STEPS_BY_TRIGGER: dict[TriggerKind, tuple[str, ...]] = {
    TriggerKind.SYNC_RECOMMEND: tuple(f"S-R{n}" for n in range(1, 17)),
    TriggerKind.BATCH_PREFERENCE_LEARNING: tuple(f"S-B{n}" for n in range(1, 11)),
    TriggerKind.EVENT_PIPELINE: tuple(f"S-E{n}" for n in range(1, 9)),
    TriggerKind.SYNC_SUBSCRIBE: tuple(f"S-S{n}" for n in range(1, 14)),
    TriggerKind.SYNC_CANCEL: tuple(f"S-C{n}" for n in range(1, 12)),
    TriggerKind.SYNC_INSIGHT: tuple(f"S-I{n}" for n in range(1, 15)),
    TriggerKind.BATCH_CANCEL_EXPIRY: tuple(f"S-X{n}" for n in range(1, 9)),
    TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION: tuple(f"S-N{n}" for n in range(1, 11)),
}
STEPS_BY_TRIGGER: Mapping[TriggerKind, tuple[str, ...]] = MappingProxyType(_STEPS_BY_TRIGGER)

STEP_IDS: tuple[str, ...] = tuple(
    step for steps in _STEPS_BY_TRIGGER.values() for step in steps
)

# ③ 3절 도식의 「구획」 — 한 트리거 안에서 진입 노드가 여럿인 자리임.
# 구획 이름은 ③ 도식·11절 「재개 경계」가 쓴 말을 그대로 옮김.
_SECTIONS_BY_TRIGGER: dict[TriggerKind, Mapping[str, tuple[str, ...]]] = {
    TriggerKind.SYNC_RECOMMEND: MappingProxyType({"추천": _STEPS_BY_TRIGGER[TriggerKind.SYNC_RECOMMEND][:15]}),
    TriggerKind.BATCH_PREFERENCE_LEARNING: MappingProxyType(
        {"배치": _STEPS_BY_TRIGGER[TriggerKind.BATCH_PREFERENCE_LEARNING][:9]}
    ),
    TriggerKind.EVENT_PIPELINE: MappingProxyType(
        {
            "구획1": ("S-E1", "S-E2", "S-E3", "S-E4"),
            "구획2": ("S-E5", "S-E6", "S-E7"),
        }
    ),
    TriggerKind.SYNC_SUBSCRIBE: MappingProxyType(
        {
            "플랜조회": ("S-S1", "S-S2", "S-S3", "S-S4"),
            "결제": ("S-S5", "S-S6", "S-S7", "S-S8", "S-S9", "S-S10", "S-S11", "S-S12"),
        }
    ),
    TriggerKind.SYNC_CANCEL: MappingProxyType(
        {
            "해지": (
                "S-C1", "S-C2", "S-C3", "S-C4", "S-C5", "S-C6",
                "S-C7", "S-C8", "S-C9", "S-C10",
            )
        }
    ),
    TriggerKind.SYNC_INSIGHT: MappingProxyType(
        {
            "타임라인": ("S-I1", "S-I2", "S-I3", "S-I4", "S-I5"),
            "인사이트": (
                "S-I6", "S-I7", "S-I8", "S-I9", "S-I10",
                "S-I11", "S-I12", "S-I13",
            ),
        }
    ),
    TriggerKind.BATCH_CANCEL_EXPIRY: MappingProxyType(
        {"배치": ("S-X1", "S-X2", "S-X3", "S-X4", "S-X5", "S-X6", "S-X7")}
    ),
    TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION: MappingProxyType(
        {
            "구획1": ("S-N1", "S-N2", "S-N3", "S-N4"),
            "구획2": ("S-N5", "S-N6", "S-N7", "S-N8", "S-N9"),
        }
    ),
}
SECTIONS_BY_TRIGGER: Mapping[TriggerKind, Mapping[str, tuple[str, ...]]] = MappingProxyType(
    _SECTIONS_BY_TRIGGER
)

# ③ 6절 1번 「진입 노드」 열이 지목한 단계임. 마감선을 넣는 자리가 여기뿐임.
ENTRY_STEPS_BY_TRIGGER: Mapping[TriggerKind, tuple[str, ...]] = MappingProxyType(
    {
        TriggerKind.SYNC_RECOMMEND: ("S-R2",),
        TriggerKind.BATCH_PREFERENCE_LEARNING: ("S-B1",),
        TriggerKind.EVENT_PIPELINE: ("S-E1", "S-E5"),
        TriggerKind.SYNC_SUBSCRIBE: ("S-S2", "S-S5"),
        TriggerKind.SYNC_CANCEL: ("S-C2", "S-C6"),
        TriggerKind.SYNC_INSIGHT: ("S-I2", "S-I6"),
        TriggerKind.BATCH_CANCEL_EXPIRY: ("S-X1",),
        TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION: ("S-N1", "S-N5"),
    }
)

# ③ 8-1 · 8-1-2절이 트리거마다 고른 착지 값 1개가 도착하는 자리임.
LANDING_STEP_BY_TRIGGER: Mapping[TriggerKind, str] = MappingProxyType(
    {
        TriggerKind.SYNC_RECOMMEND: "S-R16",
        TriggerKind.BATCH_PREFERENCE_LEARNING: "S-B10",
        TriggerKind.EVENT_PIPELINE: "S-E8",
        TriggerKind.SYNC_SUBSCRIBE: "S-S13",
        TriggerKind.SYNC_CANCEL: "S-C11",
        TriggerKind.SYNC_INSIGHT: "S-I14",
        TriggerKind.BATCH_CANCEL_EXPIRY: "S-X8",
        TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION: "S-N10",
    }
)

# ③ 6절 3번 「사전 조건 확인 노드」 열.
PRECHECK_STEPS: frozenset[str] = frozenset(
    {"S-R3", "S-B3", "S-E2", "S-E5", "S-S3", "S-C3", "S-I3", "S-I7", "S-X3", "S-N2"}
)

# ③ 6절 13번 「커밋 노드」 열 · ③ 11절 「경계 단계」.
COMMIT_STEPS: frozenset[str] = frozenset({"S-B7", "S-E3", "S-E6", "S-X4", "S-N6"})

# ③ 4-5 · 4-6절 「사람 확인」 단계 — 흐름이 여기서 멈추고 사람 응답을 기다림.
HUMAN_GATE_STEPS: frozenset[str] = frozenset({"S-S7", "S-C5"})

# ③ 4절 「p95 배정」이 `TB-1 단말 구간 · API 예산 밖`이라고 적은 단계임(계약 대상 밖 5건).
TERMINAL_STEPS: frozenset[str] = frozenset({"S-R1", "S-R14", "S-S1", "S-C1", "S-I1"})

# 응답을 닫은 뒤 도는 후처리 — 어느 마감선에도 들어가지 않음(③ 4-1 `S-R15` · 4-6 `S-C10`).
POST_RESPONSE_STEPS: frozenset[str] = frozenset({"S-R15", "S-C10"})

# 마감선 판정을 하지 않는 단계 = 단말 구간 + 사람 대기 + 응답 후 후처리.
BUDGET_EXEMPT_STEPS: frozenset[str] = (
    TERMINAL_STEPS | HUMAN_GATE_STEPS | POST_RESPONSE_STEPS
)

# ③ 8-1-2절 ⓐ가 확정한 「되돌릴 수 없는 단계」 3개 + 승인 문 판정 대상 도구 식별자(⑥ 3절 표 이름).
IRREVERSIBLE_TOOL_STEPS: Mapping[str, str] = MappingProxyType(
    {"S-S9": "C-9", "S-C10": "C-12", "S-X4": "R-11"}
)

# ③ 4-1절 「(병렬)」 표기가 붙은 묶음. 같은 상태 필드를 쓰지 않는 것을 시험이 셈.
PARALLEL_GROUPS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"S-R-context": ("S-R4", "S-R5", "S-R6", "S-R7")}
)


@dataclass(frozen=True, slots=True)
class LoopSpec:
    """③ 8-2절 「반복 상한」 표 1행. `max_iter` 값은 여기 없고 설정에서 읽음."""

    loop_id: str
    trigger_kind: TriggerKind
    counter_entry_step: str
    """③ 6절 11번 `iteration_count`의 갱신 주체. 되돌아가는 간선의 도착 단계임."""
    exit_step: str
    """되돌아가는 간선이 출발하는 단계(분기 함수가 붙는 자리)."""
    span: tuple[str, ...]


LOOPS: Mapping[str, LoopSpec] = MappingProxyType(
    {
        "L-1": LoopSpec(
            loop_id="L-1",
            trigger_kind=TriggerKind.SYNC_RECOMMEND,
            counter_entry_step="S-R2",
            exit_step="S-R13",
            span=tuple(f"S-R{n}" for n in range(2, 14)),
        ),
        "L-2": LoopSpec(
            loop_id="L-2",
            trigger_kind=TriggerKind.BATCH_PREFERENCE_LEARNING,
            counter_entry_step="S-B4",
            exit_step="S-B7",
            span=("S-B4", "S-B5", "S-B6", "S-B7"),
        ),
        "L-3": LoopSpec(
            loop_id="L-3",
            trigger_kind=TriggerKind.BATCH_CANCEL_EXPIRY,
            counter_entry_step="S-X3",
            exit_step="S-X7",
            span=("S-X3", "S-X4", "S-X5", "S-X6", "S-X7"),
        ),
    }
)


# ---------------------------------------------------------------------------
# ④ 2-6 · 2-6-2절 담당자 명부 16명 — 단계 배정을 그대로 옮김.
# ---------------------------------------------------------------------------
OWNER_NAMES: Mapping[str, str] = MappingProxyType(
    {
        "R-1": "추천 문장 생성 담당자",
        "R-2": "추천 요청 조립·검증 처리기",
        "R-3": "배치 학습 준비·검증 처리기",
        "R-4": "취향 벡터 커밋 처리기",
        "R-5": "학습 데이터 전달 처리기",
        "R-6": "온보딩 프로파일 생성 처리기",
        "R-7": "구독 결제 요청 조립·검증 처리기",
        "R-8": "PG 정기 결제 등록 실행 처리기",
        "R-9": "구독 해지 예약 처리기",
        "R-10": "PG 정기 결제 중지 실행 처리기",
        "R-11": "해지 만료 무료 전환 배치 처리기",
        "R-12": "구독 플랜 안내 처리기",
        "R-13": "구독 상태 반영 처리기",
        "R-14": "이력·인사이트 조회 처리기",
        "R-15": "기억 제한 알림 전달 처리기",
        "R-16": "이력 보관 기간 적용 처리기",
    }
)

OWNER_SERVICE: Mapping[str, str] = MappingProxyType(
    {
        "R-1": "recommendation_history_service",
        "R-2": "recommendation_history_service",
        "R-3": "daily_learning_batch",
        "R-4": "daily_learning_batch",
        "R-5": "recommendation_history_service",
        "R-6": "member_service",
        "R-7": "payment_service",
        "R-8": "payment_service",
        "R-9": "payment_service",
        "R-10": "payment_service",
        "R-11": "payment_service",
        "R-12": "member_service",
        "R-13": "member_service",
        "R-14": "recommendation_history_service",
        "R-15": "recommendation_history_service",
        "R-16": "recommendation_history_service",
    }
)

_STEPS_BY_OWNER: dict[str, tuple[str, ...]] = {
    "R-1": ("S-R11",),
    "R-2": (
        "S-R2", "S-R3", "S-R4", "S-R5", "S-R6", "S-R7", "S-R8", "S-R9", "S-R10",
        "S-R12", "S-R13", "S-R15", "S-R16",
    ),
    "R-3": ("S-B1", "S-B2", "S-B3", "S-B4", "S-B5", "S-B6", "S-B8", "S-B9", "S-B10"),
    "R-4": ("S-B7",),
    "R-5": ("S-E1", "S-E2", "S-E3", "S-E4", "S-E8"),
    "R-6": ("S-E5", "S-E6", "S-E7"),
    "R-7": ("S-S5", "S-S6", "S-S7", "S-S8", "S-S10", "S-S11", "S-S12", "S-S13"),
    "R-8": ("S-S9",),
    "R-9": (
        "S-C2", "S-C3", "S-C4", "S-C5", "S-C6", "S-C7", "S-C8", "S-C9", "S-C11",
    ),
    "R-10": ("S-C10",),
    "R-11": ("S-X1", "S-X2", "S-X3", "S-X4", "S-X5", "S-X7", "S-X8"),
    "R-12": ("S-S2", "S-S3", "S-S4"),
    "R-13": ("S-N4", "S-N5", "S-N8", "S-N9", "S-N10"),
    "R-14": tuple(f"S-I{n}" for n in range(2, 15)),
    "R-15": ("S-N1", "S-N2", "S-N3"),
    "R-16": ("S-N6", "S-N7", "S-X6"),
}
STEPS_BY_OWNER: Mapping[str, tuple[str, ...]] = MappingProxyType(_STEPS_BY_OWNER)

OWNER_BY_STEP: Mapping[str, str] = MappingProxyType(
    {step: owner for owner, steps in _STEPS_BY_OWNER.items() for step in steps}
)


def node_symbol_of(step_id: str) -> str:
    """노드 함수 이름에 남기는 단계 식별자 표기 — 붙임표만 밑줄로 바꿈(`S-R2` → `S_R2`)."""
    return step_id.replace("-", "_")


_TRIGGER_OF_STEP: Mapping[str, TriggerKind] = MappingProxyType(
    {step: kind for kind, steps in _STEPS_BY_TRIGGER.items() for step in steps}
)


def trigger_of_step(step_id: str) -> TriggerKind:
    try:
        return _TRIGGER_OF_STEP[step_id]
    except KeyError as exc:
        raise KeyError(f"③ 4절에 없는 단계 이름임: {step_id}") from exc
