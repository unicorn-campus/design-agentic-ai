"""읽기 함수 모음 — ⑤ 3절 「정형 접근 경로」 행 1개당 함수 1개임.

함수 수와 경로 표 행 수가 같아야 함. `READ_FUNCTIONS`가 그 대조에 쓰임.
표를 합치거나 쪼갠 함수는 없음.
"""

from __future__ import annotations

from collections.abc import Callable

from ..source_port import ReadResult
from .member import (
    read_consent_log,
    read_diet_restriction,
    read_member_profile,
)
from .payment import (
    read_expiring_subscription_batch,
    read_payment_fail_log,
    read_subscription_for_cancel,
    read_subscription_for_history_limit,
    read_subscription_plan_master,
)
from .recommendation_history import (
    read_accept_reject_log,
    read_insight_aggregate,
    read_meal_history_calendar,
    read_meal_history_memory_limit,
    read_meal_history_recent_week,
    read_preference_vector,
    read_previous_day_feedback,
    read_recommendation_cache,
    read_recommendation_reason,
    read_weekly_insight_aggregate,
)

# 경로 식별자 → 읽기 함수. 이 표의 행 수가 ⑤ 3절 행 수와 같아야 함.
READ_FUNCTIONS: dict[str, Callable[..., ReadResult]] = {
    "T-1": read_member_profile,
    "T-2": read_diet_restriction,
    "T-3": read_consent_log,
    "T-4": read_meal_history_recent_week,
    "T-5": read_meal_history_calendar,
    "T-6": read_previous_day_feedback,
    "T-7": read_recommendation_reason,
    "T-8": read_accept_reject_log,
    "T-9": read_insight_aggregate,
    "T-10": read_preference_vector,
    "T-11": read_recommendation_cache,
    "T-12": read_subscription_for_history_limit,
    "T-13": read_weekly_insight_aggregate,
    "T-14": read_subscription_plan_master,
    "T-15": read_subscription_for_cancel,
    "T-16": read_expiring_subscription_batch,
    "T-17": read_meal_history_memory_limit,
    "T-18": read_payment_fail_log,
}

__all__ = [
    "READ_FUNCTIONS",
    "read_accept_reject_log",
    "read_consent_log",
    "read_diet_restriction",
    "read_expiring_subscription_batch",
    "read_insight_aggregate",
    "read_meal_history_calendar",
    "read_meal_history_memory_limit",
    "read_meal_history_recent_week",
    "read_member_profile",
    "read_payment_fail_log",
    "read_preference_vector",
    "read_previous_day_feedback",
    "read_recommendation_cache",
    "read_recommendation_reason",
    "read_subscription_for_cancel",
    "read_subscription_for_history_limit",
    "read_subscription_plan_master",
    "read_weekly_insight_aggregate",
]
