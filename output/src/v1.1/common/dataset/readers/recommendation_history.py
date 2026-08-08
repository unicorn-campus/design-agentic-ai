"""추천·이력 서비스와 일일 학습 배치가 읽는 경로 10개 —
⑤ 3절 `T-4` ~ `T-11` · `T-13` · `T-17`.
"""

from __future__ import annotations

from common.config import Settings

from ..source_port import ReadResult, SourceReader, read_path

__all__ = [
    "read_accept_reject_log",
    "read_insight_aggregate",
    "read_meal_history_calendar",
    "read_meal_history_memory_limit",
    "read_meal_history_recent_week",
    "read_preference_vector",
    "read_previous_day_feedback",
    "read_recommendation_cache",
    "read_recommendation_reason",
    "read_weekly_insight_aggregate",
]


def read_meal_history_recent_week(
    reader: SourceReader,
    member_id: str,
    since_on: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-4 최근 7일 식사 목록 — 반복 방지 입력."""
    return read_path(
        "T-4", reader, {"member_id": member_id, "since_on": since_on}, limit, settings
    )


def read_meal_history_calendar(
    reader: SourceReader,
    member_id: str,
    since_on: str,
    until_on: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-5 달력 뷰용 일별 기록 + 카테고리 태그."""
    return read_path(
        "T-5",
        reader,
        {"member_id": member_id, "since_on": since_on, "until_on": until_on},
        limit,
        settings,
    )


def read_previous_day_feedback(
    reader: SourceReader,
    target_on: str,
    cursor: str | None = None,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-6 전일 전체 피드백 — 배치 입력. 커서로 나눠 읽음."""
    return read_path(
        "T-6", reader, {"target_on": target_on, "cursor": cursor}, limit, settings
    )


def read_recommendation_reason(
    reader: SourceReader,
    recommendation_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-7 추천 이유 1줄 · 이유 상세 · 확신 스코어 · 컨텍스트 태그."""
    return read_path(
        "T-7", reader, {"recommendation_id": recommendation_id}, limit, settings
    )


def read_accept_reject_log(
    reader: SourceReader,
    member_id: str,
    since_on: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-8 수락 · 거절 이력. 반응 시간 열은 이 경로에서 읽지 않음."""
    return read_path(
        "T-8", reader, {"member_id": member_id, "since_on": since_on}, limit, settings
    )


def read_insight_aggregate(
    reader: SourceReader,
    member_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-9 선호 카테고리 · 만족도 추이 · 방문 빈도 집계."""
    return read_path("T-9", reader, {"member_id": member_id}, limit, settings)


def read_preference_vector(
    reader: SourceReader,
    member_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-10 회원 취향 벡터 1건. 벡터 인덱스 제품이 정해지기 전에는 읽을 수 없음."""
    return read_path("T-10", reader, {"member_id": member_id}, limit, settings)


def read_recommendation_cache(
    reader: SourceReader,
    member_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-11 직전 추천 결과 — 폴백용. 캐시 제품이 정해지기 전에는 읽을 수 없음."""
    return read_path("T-11", reader, {"member_id": member_id}, limit, settings)


def read_weekly_insight_aggregate(
    reader: SourceReader,
    member_id: str,
    allowed_since_on: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-13 요일 · 시간대별 패턴 + 누적 기록 수."""
    return read_path(
        "T-13",
        reader,
        {"member_id": member_id, "allowed_since_on": allowed_since_on},
        limit,
        settings,
    )


def read_meal_history_memory_limit(
    reader: SourceReader,
    member_id: str,
    free_tier_boundary_on: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-17 기억 제한 판정 — 누적 기록 수 · 만료 예정 기록 수."""
    return read_path(
        "T-17",
        reader,
        {"member_id": member_id, "free_tier_boundary_on": free_tier_boundary_on},
        limit,
        settings,
    )
