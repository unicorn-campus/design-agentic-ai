"""경로 표 — 설계서 ⑤ 3절 「정형 접근 경로」 18행을 1:1로 옮긴 것.

행을 합치거나 쪼개지 않음. 행 수 상한은 여기에 숫자로 두지 않고 설정에서만 읽음.
열 이름은 논리 이름임 — 물리 표·열 이름은 아직 정해지지 않았음.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "PATHS",
    "PATH_IDS",
    "PathSpec",
    "StorageKind",
    "UnknownPath",
    "columns_of",
    "spec_of",
]


class UnknownPath(KeyError):
    """경로 표에 없는 이름을 불렀음. 없는 경로를 만들어 주지 않음."""


class StorageKind(StrEnum):
    """저장소 종류. ⑤ 12절 「⑦ 배포가 바로 쓸 저장소 종류 목록」에서 옮김."""

    RELATIONAL = "관계형"
    VECTOR = "벡터 인덱스"
    CACHE = "키·값 캐시"


@dataclass(frozen=True, slots=True)
class PathSpec:
    """경로 1개의 정의. `⑤ 3절 행 1개 = 이 객체 1개 = 읽기 함수 1개`임."""

    path_id: str
    logical_table: str
    storage_id: str
    storage_kind: StorageKind
    owner_service: str
    gets: str
    filter_params: tuple[str, ...]
    columns: tuple[str, ...]
    key_columns: tuple[str, ...]
    required_columns: tuple[str, ...]
    error_rate_row: str
    design_row: str


_SPECS: tuple[PathSpec, ...] = (
    PathSpec(
        path_id="T-1",
        logical_table="member_profile",
        storage_id="S-1",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="member-service",
        gets="회원ID · 닉네임 · 알림설정 · 구독 상태",
        filter_params=("member_id",),
        columns=("member_id", "nickname", "notify_enabled", "subscription_state"),
        key_columns=("member_id",),
        required_columns=("member_id", "subscription_state"),
        error_rate_row="E-1",
        design_row="⑤ 3절 T-1",
    ),
    PathSpec(
        path_id="T-2",
        logical_table="diet_restriction",
        storage_id="S-1",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="member-service",
        gets="알레르겐 라벨 목록 · 식이 유형",
        filter_params=("member_id",),
        columns=("member_id", "allergen_labels", "diet_type"),
        key_columns=("member_id",),
        required_columns=("member_id", "diet_type"),
        error_rate_row="E-1",
        design_row="⑤ 3절 T-2",
    ),
    PathSpec(
        path_id="T-3",
        logical_table="consent_log",
        storage_id="S-1",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="member-service",
        gets="위치 동의 · 건강 민감정보 동의의 최신 상태",
        filter_params=("member_id", "consent_kind"),
        columns=("member_id", "consent_kind", "consent_state", "consented_at"),
        key_columns=("member_id", "consent_kind", "consented_at"),
        required_columns=("member_id", "consent_kind", "consent_state"),
        error_rate_row="E-1",
        design_row="⑤ 3절 T-3",
    ),
    PathSpec(
        path_id="T-4",
        logical_table="meal_history",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="recommendation-history-service",
        gets="최근 7일 식사 목록(반복 방지 입력)",
        filter_params=("member_id", "since_on"),
        columns=("member_id", "eaten_at", "restaurant_id", "restaurant_name", "category_code"),
        key_columns=("member_id", "eaten_at", "restaurant_id"),
        required_columns=("member_id", "eaten_at", "restaurant_id"),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-4",
    ),
    PathSpec(
        path_id="T-5",
        logical_table="meal_history",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="recommendation-history-service",
        gets="30일 달력 뷰용 일별 기록 + 카테고리 태그",
        filter_params=("member_id", "since_on", "until_on"),
        columns=("member_id", "eaten_on", "restaurant_name", "category_code"),
        key_columns=("member_id", "eaten_on", "restaurant_name"),
        required_columns=("member_id", "eaten_on"),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-5",
    ),
    PathSpec(
        path_id="T-6",
        logical_table="feedback",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="daily-learning-batch",
        gets="전일 전체 피드백(만족도 · 키워드) — 배치 입력",
        filter_params=("target_on", "cursor"),
        columns=(
            "feedback_id",
            "member_id",
            "recommendation_id",
            "satisfaction",
            "keyword",
            "created_at",
        ),
        key_columns=("feedback_id",),
        required_columns=("feedback_id", "member_id", "satisfaction"),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-6",
    ),
    PathSpec(
        path_id="T-7",
        logical_table="recommendation",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="recommendation-history-service",
        gets="추천 이유 1줄 · 이유 상세 · 확신 스코어 · 컨텍스트 태그",
        filter_params=("recommendation_id",),
        columns=(
            "recommendation_id",
            "reason_line",
            "reason_detail",
            "confidence_score",
            "context_tags",
        ),
        key_columns=("recommendation_id",),
        required_columns=(
            "recommendation_id",
            "reason_line",
            "confidence_score",
            "context_tags",
        ),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-7",
    ),
    PathSpec(
        path_id="T-8",
        logical_table="accept_reject_log",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="recommendation-history-service",
        gets="수락 · 거절 이력(거절 사유)",
        filter_params=("member_id", "since_on"),
        columns=("member_id", "recommendation_id", "action", "reject_reason", "created_at"),
        key_columns=("member_id", "recommendation_id", "action"),
        required_columns=("member_id", "recommendation_id", "action"),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-8",
    ),
    PathSpec(
        path_id="T-9",
        logical_table="insight_agg",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="recommendation-history-service",
        gets="선호 카테고리 Top 5 · 만족도 추이 · 방문 빈도",
        filter_params=("member_id",),
        columns=("member_id", "metric", "bucket", "value"),
        key_columns=("member_id", "metric", "bucket"),
        required_columns=("member_id", "metric", "bucket", "value"),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-9",
    ),
    PathSpec(
        path_id="T-10",
        logical_table="preference_vector",
        storage_id="S-4",
        storage_kind=StorageKind.VECTOR,
        owner_service="recommendation-history-service",
        gets="회원 취향 벡터 1건(추천 입력)",
        filter_params=("member_id",),
        columns=("member_id", "vector", "generation", "updated_at"),
        key_columns=("member_id", "generation"),
        required_columns=("member_id", "vector", "generation"),
        error_rate_row="E-3",
        design_row="⑤ 3절 T-10",
    ),
    PathSpec(
        path_id="T-11",
        logical_table="recommendation_cache",
        storage_id="S-5",
        storage_kind=StorageKind.CACHE,
        owner_service="recommendation-history-service",
        gets="직전 추천 결과(LLM 지연 · 오류 시 폴백)",
        filter_params=("member_id",),
        columns=("member_id", "cached_at", "recommendation_set"),
        key_columns=("member_id",),
        required_columns=("member_id", "cached_at", "recommendation_set"),
        error_rate_row="[확인필요: E 행 미배정]",
        design_row="⑤ 3절 T-11",
    ),
    PathSpec(
        path_id="T-12",
        logical_table="subscription",
        storage_id="S-7",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="payment-service",
        gets="구독 플랜 · 다음 결제일(이력 기간 제한 판정)",
        filter_params=("member_id",),
        columns=("member_id", "plan_code", "next_billing_on"),
        key_columns=("member_id",),
        required_columns=("member_id", "plan_code"),
        error_rate_row="E-13",
        design_row="⑤ 3절 T-12",
    ),
    PathSpec(
        path_id="T-13",
        logical_table="insight_weekly_agg",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="recommendation-history-service",
        gets="요일 · 시간대별 식사 패턴 + 누적 기록 수(마일스톤 판정 입력)",
        filter_params=("member_id", "allowed_since_on"),
        columns=("member_id", "metric", "bucket", "value"),
        key_columns=("member_id", "metric", "bucket"),
        required_columns=("member_id", "metric", "bucket", "value"),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-13",
    ),
    PathSpec(
        path_id="T-14",
        logical_table="subscription_plan",
        storage_id="S-7",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="payment-service",
        gets="플랜 유형 · 가격 · 결제 주기 · 혜택(플랜 비교표 표시값)",
        filter_params=(),
        columns=("plan_code", "plan_type", "price_krw", "billing_cycle", "benefits"),
        key_columns=("plan_code",),
        required_columns=("plan_code", "plan_type", "price_krw", "billing_cycle"),
        error_rate_row="E-13",
        design_row="⑤ 3절 T-14",
    ),
    PathSpec(
        path_id="T-15",
        logical_table="subscription",
        storage_id="S-7",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="payment-service",
        gets="해지 사전 조건 — 구독 활성 여부 · 남은 기간 · 전환 예정일 · 복귀 제안 소진 여부",
        filter_params=("member_id",),
        columns=(
            "member_id",
            "is_active",
            "remaining_days",
            "downgrade_scheduled_on",
            "winback_offer_used",
        ),
        key_columns=("member_id",),
        required_columns=("member_id", "is_active"),
        error_rate_row="E-13",
        design_row="⑤ 3절 T-15",
    ),
    PathSpec(
        path_id="T-16",
        logical_table="subscription",
        storage_id="S-7",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="payment-service",
        gets="만료 전환 대상 — 상태 `해지예약` + 전환 예정일 도달",
        filter_params=("run_on", "cursor"),
        columns=("member_id", "status", "downgrade_scheduled_on"),
        key_columns=("member_id",),
        required_columns=("member_id", "status", "downgrade_scheduled_on"),
        error_rate_row="E-13",
        design_row="⑤ 3절 T-16",
    ),
    PathSpec(
        path_id="T-17",
        logical_table="meal_history",
        storage_id="S-3",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="recommendation-history-service",
        gets="기억 제한 판정 — 누적 기록 수 · 무료 30일 만료 예정 기록 수",
        filter_params=("member_id", "free_tier_boundary_on"),
        columns=("member_id", "metric", "value"),
        key_columns=("member_id", "metric"),
        required_columns=("member_id", "metric", "value"),
        error_rate_row="E-2",
        design_row="⑤ 3절 T-17",
    ),
    PathSpec(
        path_id="T-18",
        logical_table="payment_fail_log",
        storage_id="S-7",
        storage_kind=StorageKind.RELATIONAL,
        owner_service="payment-service",
        gets="결제 실패 사유 · 누적 실패 횟수",
        filter_params=("member_id", "billing_cycle_started_on"),
        columns=("member_id", "fail_reason_code", "fail_count", "billing_cycle_started_on"),
        key_columns=("member_id", "fail_reason_code"),
        required_columns=("member_id", "fail_reason_code", "fail_count"),
        error_rate_row="E-13",
        design_row="⑤ 3절 T-18",
    ),
)

PATHS: dict[str, PathSpec] = {spec.path_id: spec for spec in _SPECS}
PATH_IDS: tuple[str, ...] = tuple(PATHS)


def spec_of(path_id: str) -> PathSpec:
    try:
        return PATHS[path_id]
    except KeyError as exc:
        raise UnknownPath(f"경로 표에 없는 이름임: {path_id}") from exc


def columns_of(path_id: str) -> tuple[str, ...]:
    return spec_of(path_id).columns
