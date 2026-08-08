"""API 경계 스키마. 내부 LangGraph 상태를 외부에 직접 노출하지 않음."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecommendationRequest(StrictModel):
    member_id: str = Field(min_length=1, max_length=100)
    region_label: str = Field(min_length=1, max_length=100)
    excluded_ingredient_codes: list[str] = Field(default_factory=list, max_length=30)
    alternative_requested: bool = False


class RecommendationCard(StrictModel):
    recommendation_id: str
    menu_name: str
    place_name: str
    distance_m: int = Field(ge=0)
    walk_minutes: int = Field(ge=0)
    reason_line: str
    confidence_score: float = Field(ge=0, le=100)
    context_tags: list[str]
    signature_menu: str | None = None
    price: int | None = Field(default=None, ge=0)
    address: str | None = None
    reason_detail: str | None = None


class RecommendationResponse(StrictModel):
    cards: list[RecommendationCard]
    card_count: int = Field(ge=0, le=3)
    fallback_notice: str | None = None
    correlation_id: str


class MealRecordRequest(StrictModel):
    member_id: str = Field(min_length=1, max_length=100)
    recommendation_id: str = Field(min_length=1, max_length=100)


class MealRecordResponse(StrictModel):
    meal_record_id: str
    recorded_on: date
    undo_until_epoch_ms: int


class ProfileResponse(StrictModel):
    member_id: str
    nickname: str
    email_masked: str
    plan: str
    meal_count: int


class ProfileUpdateRequest(StrictModel):
    nickname: str = Field(min_length=2, max_length=20, pattern=r"^[가-힣a-zA-Z0-9 _-]+$")


class InsightResponse(StrictModel):
    top_categories: list[dict[str, int | str]]
    weekly_pattern_summary: str
    satisfaction_average: float
    accuracy_gain_rate: float


class SubscriptionRequest(StrictModel):
    member_id: str = Field(min_length=1, max_length=100)
    approved: bool = False
    idempotency_key: str = Field(min_length=8, max_length=120)


class SubscriptionResponse(StrictModel):
    status: str
    plan: str
    message: str


class ErrorBody(StrictModel):
    code: str
    message: str
    correlation_id: str
