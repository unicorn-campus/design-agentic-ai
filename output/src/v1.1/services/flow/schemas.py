"""구조화 출력 스키마 — 형 정의 **1벌**임. `07-api-ui.md`가 여기서 가져다 씀.

키 이름은 ④ 5-1 · 5-1-2절이 확정한 이름을 **글자 그대로** 씀. 짧게 줄이거나 표기법을 바꾸지 않음.
필수·선택 표기도 ④ 표기를 그대로 옮김(`조건 필수`는 기본값 `None`으로 둠).

모델을 쓰는 담당자(`R-1`)의 반환값은 자유 문장이 아니라 여기 정한 형으로 받음 —
그 형은 `toolkit`의 `C-2` 출력 규격과 같은 ④ `K-7` 키를 씀(같은 형을 두 번 정의하지 않기 위해
커넥터 쪽 모델을 그대로 다시 내보냄).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from services.recommendation_history_service.tools.c2_recommendation_generate import (
    Recommendation,
    RecommendationGenerateOutput,
)

__all__ = [
    "Recommendation",
    "RecommendationGenerateOutput",
    "RecommendationCard",
    "RecommendationResponse",
    "PlanComparisonRow",
    "PlanViewResponse",
    "PaymentResponse",
    "CancelScheduleResponse",
    "TimelineDay",
    "TimelineRecord",
    "InsightResponse",
    "BatchResultResponse",
    "ExpiryBatchResponse",
    "RetentionApplyResponse",
    "LearningTransferResponse",
    "OnboardingProfileResponse",
    "MemoryLimitNoticeResponse",
    "WeeklyPatternRow",
    "OUTPUT_SCHEMAS",
]


class _Strict(BaseModel):
    """④에 칸이 없는 이름이 끼어들면 실패함 — 경계 미통과 7건이 새어 나갈 자리를 막음."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# ③ 7절 출력 스키마 — 케이스 1(추천 카드 3장)
# ---------------------------------------------------------------------------
class RecommendationCard(_Strict):
    """④ `K-9`의 `cards` 안쪽 키 10개."""

    recommendation_id: str
    menu_name: str
    place_name: str
    distance_m: int
    walk_minutes: int
    reason_line: str
    confidence_score: float
    context_tags: list[str]
    signature_menu: str | None = None
    """③ 7절 `[확인필요: 대표 메뉴·가격 제공 원천]` — 원천 미확정이라 조건 필수임."""
    price: int | None = None
    """위와 같음."""


class RecommendationResponse(_Strict):
    """④ `K-9` 집합. `S-R13`이 내보내는 형이며 `S-R16` 착지도 같은 형으로 냄."""

    cards: list[RecommendationCard]
    card_count: int
    reason_detail: str | None = None
    fallback_notice: str | None = None
    learning_notice: str | None = None


# ---------------------------------------------------------------------------
# ③ 7-2절 출력 스키마 — 케이스 2(화면 산출물 4종)
# ---------------------------------------------------------------------------
class PlanComparisonRow(_Strict):
    plan_type: str
    feature_labels: list[str]


class PlanViewResponse(_Strict):
    """④ 3-12절 `R-12` 출력."""

    plan_comparison: list[PlanComparisonRow]
    price_monthly_krw: int
    price_yearly_monthly_krw: int
    current_plan: str
    next_billing_date: str | None = None
    price_source: str
    fallback_notice: str | None = None


class PaymentResponse(_Strict):
    """④ `K-23` 집합. `payment_result`만 필수이고 나머지는 결제 성공일 때 조건 필수임."""

    payment_result: str
    subscription_started_on: str | None = None
    next_billing_date: str | None = None
    withdrawal_notice: str | None = None


class CancelScheduleResponse(_Strict):
    """④ `K-27` 집합."""

    cancel_schedule_id: str
    cancel_state: str
    scheduled_downgrade_on: str
    remaining_days: int
    retention_notice: str
    cancel_idempotency_key: str


class TimelineRecord(_Strict):
    meal_record_id: str
    menu_name: str
    category_code: str


class TimelineDay(_Strict):
    recorded_on: str
    meal_records: list[TimelineRecord]


class WeeklyPatternRow(_Strict):
    weekday: str
    category_code: str


class InsightResponse(_Strict):
    """④ 3-14절 `R-14` 출력. `timeline`만 필수이고 나머지는 조건 필수임."""

    timeline: list[TimelineDay]
    insight_top_categories: list[str] | None = None
    weekly_pattern: list[WeeklyPatternRow] | None = None
    satisfaction_change: float | None = None
    weekly_pattern_summary: str | None = None
    milestone_message: str | None = None
    accuracy_gain_rate: float | None = None
    memory_limit_notice: str | None = None
    fallback_notice: str | None = None


class BatchResultResponse(_Strict):
    """④ `K-14` 집합(`S-B9` → 스케줄러) · `R-11` 종료 값과 같은 규격을 쓰지 않음(별 형)."""

    batch_run_id: str
    updated_member_count: int
    mean_vector_delta: float
    skipped_member_ids: list[str] | None = None
    learning_applied_message: str | None = None
    batch_status: str


class ExpiryBatchResponse(_Strict):
    """④ 3-11절 `R-11` 종료 값(③에 집합 식별자 없음)."""

    batch_run_id: str
    downgraded_member_count: int
    skipped_member_ids: list[str] | None = None
    batch_status: str


class RetentionApplyResponse(_Strict):
    """④ 3-16절 `R-16` 출력(`S-N7` 회신 · `S-X6` 회신 공통)."""

    member_id: str
    retention_policy: str
    applied_at: int
    retention_result: str


class LearningTransferResponse(_Strict):
    """④ `K-15` 집합(`S-E2` → `S-E3`)."""

    transfer_id: str
    member_id: str
    meal_record_id: str
    satisfaction: str
    feedback_keyword: str | None = None
    context_snapshot: dict
    idempotency_key: str


class OnboardingProfileResponse(_Strict):
    """④ `K-16` 집합(`S-E6` → `S-E7`) — 이벤트 흐름 구획 2의 마지막 응답 형임."""

    member_id: str
    onboarding_round: int
    initial_preference_vector: list[float]
    top_categories: list[str]
    swipe_count: int
    idempotency_key: str


class MemoryLimitNoticeResponse(_Strict):
    """④ `K-28` 집합."""

    memory_limit_notice_id: str
    member_id: str
    total_record_count: int
    expiring_record_count: int
    accuracy_gain_rate: float | None = None
    notice_idempotency_key: str


OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "S-R": RecommendationResponse,
    "S-B": BatchResultResponse,
    "S-E": OnboardingProfileResponse,
    "S-S": PaymentResponse,
    "S-C": CancelScheduleResponse,
    "S-I": InsightResponse,
    "S-X": ExpiryBatchResponse,
    "S-N": MemoryLimitNoticeResponse,
}
