"""흐름 상태 타입. 흐름 조립·노드 함수는 여기에 두지 않음(`06-workflow.md` 몫)."""

from __future__ import annotations

import operator
from enum import StrEnum
from typing import Annotated, Any, TypedDict, get_type_hints

__all__ = [
    "TriggerKind",
    "TriggerFamily",
    "SubscriptionState",
    "PgCancelStatus",
    "PAYMENT_RESULT_PENDING",
    "TRIGGER_FAMILY_BY_KIND",
    "LunchPickState",
    "MERGED_FIELDS",
    "SINGLE_WRITER_FIELDS",
    "STATE_FIELDS",
    "merge_last_wins_by_key",
    "reducer_of",
]


class TriggerKind(StrEnum):
    """③ 3절 트리거 인스턴스 8종의 단계 접두."""

    SYNC_RECOMMEND = "S-R"
    BATCH_PREFERENCE_LEARNING = "S-B"
    EVENT_PIPELINE = "S-E"
    SYNC_SUBSCRIBE = "S-S"
    SYNC_CANCEL = "S-C"
    SYNC_INSIGHT = "S-I"
    BATCH_CANCEL_EXPIRY = "S-X"
    EVENT_SUBSCRIPTION_PROPAGATION = "S-N"


class TriggerFamily(StrEnum):
    """③ 판정 1-1의 트리거 유형 3종. 상한 초과 처리와 예산 계층이 이 축으로 갈림."""

    SYNC_REQUEST = "sync_request"
    SCHEDULED_BATCH = "scheduled_batch"
    EVENT = "event"


TRIGGER_FAMILY_BY_KIND: dict[TriggerKind, TriggerFamily] = {
    TriggerKind.SYNC_RECOMMEND: TriggerFamily.SYNC_REQUEST,
    TriggerKind.SYNC_SUBSCRIBE: TriggerFamily.SYNC_REQUEST,
    TriggerKind.SYNC_CANCEL: TriggerFamily.SYNC_REQUEST,
    TriggerKind.SYNC_INSIGHT: TriggerFamily.SYNC_REQUEST,
    TriggerKind.BATCH_PREFERENCE_LEARNING: TriggerFamily.SCHEDULED_BATCH,
    TriggerKind.BATCH_CANCEL_EXPIRY: TriggerFamily.SCHEDULED_BATCH,
    TriggerKind.EVENT_PIPELINE: TriggerFamily.EVENT,
    TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION: TriggerFamily.EVENT,
}


class SubscriptionState(StrEnum):
    FREE = "무료"
    PREMIUM = "프리미엄"


class PgCancelStatus(StrEnum):
    DONE = "중지완료"
    PENDING = "확인 중"
    FAILED = "실패"


PAYMENT_RESULT_PENDING = "확인 중"

EpochMillis = int
PrecheckResult = dict[str, Any]
ContextFragment = dict[str, Any]
ContextBundle = dict[str, Any]
CandidatePlace = dict[str, Any]
RecommendationSet = dict[str, Any]
VerificationResult = dict[str, Any]
RetryCountByStep = dict[str, int]
ErrorRecord = dict[str, Any]
ResumeCursor = dict[str, Any]
ApprovalEvidence = dict[str, Any]
PaymentResult = dict[str, Any]
CancelSchedule = dict[str, Any]
DisclosureRecord = dict[str, Any]
InsightAggregate = dict[str, Any]
ConsistencyCheck = dict[str, Any]


def merge_last_wins_by_key(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> dict[str, Any]:
    """키 단위로 합치고 같은 키는 나중 값이 이김."""
    return {**(left or {}), **(right or {})}


class LunchPickState(TypedDict, total=False):
    trigger_kind: TriggerKind
    deadline_at: EpochMillis
    precheck_result: PrecheckResult
    partial_context: Annotated[list[ContextFragment], operator.add]
    context_bundle: ContextBundle
    candidate_set: list[CandidatePlace]
    recommendation_set: RecommendationSet
    verification_result: VerificationResult
    fallback_reason: str
    retry_count_by_step: Annotated[RetryCountByStep, merge_last_wins_by_key]
    iteration_count: int
    error_history: Annotated[list[ErrorRecord], operator.add]
    resume_cursor: ResumeCursor
    preference_vector_ref: str
    subscription_state: SubscriptionState
    approval_evidence: ApprovalEvidence
    payment_idempotency_key: str
    payment_result: PaymentResult
    cancel_schedule: CancelSchedule
    disclosure_record: DisclosureRecord
    insight_aggregate: InsightAggregate
    consistency_check: ConsistencyCheck
    pg_cancel_status: PgCancelStatus


# `from __future__ import annotations` 때문에 `__annotations__`는 문자열임.
# 흐름 프레임워크도 이 함수로 병합 규칙을 읽으므로 같은 방법으로 풀어서 봄.
_RESOLVED_HINTS: dict[str, Any] = get_type_hints(LunchPickState, include_extras=True)

STATE_FIELDS: tuple[str, ...] = tuple(_RESOLVED_HINTS)

MERGED_FIELDS: frozenset[str] = frozenset(
    name for name, hint in _RESOLVED_HINTS.items() if getattr(hint, "__metadata__", ())
)

SINGLE_WRITER_FIELDS: frozenset[str] = frozenset(STATE_FIELDS) - MERGED_FIELDS


def reducer_of(field: str) -> Any | None:
    """그 필드에 실제로 붙은 병합 함수를 돌려줌. 안 붙었으면 `None`."""
    metadata = getattr(_RESOLVED_HINTS[field], "__metadata__", ())
    return metadata[0] if metadata else None
