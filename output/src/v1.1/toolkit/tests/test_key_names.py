"""시험 2 — 도구 입출력 키 이름이 ④ 「입출력 형식」과 어긋난 건수 0건.

기대값은 ④ 5-1절(`K-6` · `K-7`) · ④ 5-2절(`C-3` · `C-4` · `C-7` · `C-8` · `C-9`) ·
④ 3-10절(`R-10` = `C-12`)에서 **글자 그대로** 옮긴 것임. ⑤가 아니라 ④를 따랐음(`G-12`).
"""

from __future__ import annotations

from services import registry

EXPECTED_INPUT_KEYS: dict[str, tuple[str, ...]] = {
    # ④ 5-1절 `K-6` 10개
    "C-2": (
        "context_tags",
        "region_label",
        "weekday",
        "time_slot",
        "weather_temp_c",
        "recent_menu_names",
        "preference_vector",
        "candidate_places",
        "excluded_ingredient_codes",
        "correlation_key",
    ),
    # ④ 5-2절 `C-3` 4개
    "C-3": (
        "correlation_key",
        "recent_feedback",
        "meal_history_summary",
        "current_preference_vector",
    ),
    # ④ 5-2절 `C-4` 3개
    "C-4": ("origin_lat", "origin_lng", "radius_m"),
    # ④ 5-2절 `C-7` 2개
    "C-7": ("origin_lat", "origin_lng"),
    # ④ 5-2절 `C-8` 1개
    "C-8": ("place_ids",),
    # ④ 5-2절 `C-9` 5개(=`K-21`)
    "C-9": (
        "payment_token",
        "amount_krw",
        "billing_cycle",
        "idempotency_key",
        "user_approval_id",
    ),
    # ④ 3-10절 `R-10` 입력 3개(=`K-36`)
    "C-12": ("pg_payment_id", "cancel_schedule_id", "pg_cancel_idempotency_key"),
}

EXPECTED_OUTPUT_KEYS: dict[str, tuple[str, ...]] = {
    # ④ 5-1절 `K-7` 2개
    "C-2": ("recommendations", "model_call_id"),
    "C-3": ("candidate_vector", "vector_model_version"),
    "C-4": ("places",),
    "C-7": ("weather_temp_c", "weather_condition"),
    "C-8": ("business_status_by_place",),
    "C-9": ("payment_result", "payment_id", "next_billing_date"),
    # ④ 3-10절 출력 3개 — `cancel_schedule_id`를 되돌려 보내는 키로 하나 더 둠
    "C-12": ("pg_cancel_status", "pg_cancel_requested_at", "cancel_schedule_id"),
}

# ④ 5-1절 `K-7` `recommendations` 안쪽 키 6개 · ④ 5-2절 `C-4` `places` 안쪽 키 4개
EXPECTED_NESTED_KEYS: dict[tuple[str, str], tuple[str, ...]] = {
    ("C-2", "recommendations"): (
        "recommendation_id",
        "menu_name",
        "place_id",
        "reason_line",
        "reason_detail",
        "confidence_score",
    ),
    ("C-4", "places"): ("place_id", "place_name", "distance_m", "rating"),
}


def test_input_key_names_match_role_contract() -> None:
    mismatches: list[str] = []
    for connector_id, expected in EXPECTED_INPUT_KEYS.items():
        actual = registry.TOOL_SPECS[connector_id].input_key_names
        if set(actual) != set(expected):
            mismatches.append(f"{connector_id}: {sorted(set(actual) ^ set(expected))}")
    assert mismatches == [], f"④와 어긋난 입력 키: {mismatches}"


def test_output_key_names_match_role_contract() -> None:
    mismatches: list[str] = []
    for connector_id, expected in EXPECTED_OUTPUT_KEYS.items():
        actual = registry.TOOL_SPECS[connector_id].output_key_names
        if set(actual) != set(expected):
            mismatches.append(f"{connector_id}: {sorted(set(actual) ^ set(expected))}")
    assert mismatches == [], f"④와 어긋난 출력 키: {mismatches}"


def test_nested_key_names_match_role_contract() -> None:
    from services.recommendation_history_service.tools import (
        c2_recommendation_generate,
        c4_nearby_places,
    )

    assert set(c2_recommendation_generate.Recommendation.model_fields) == set(
        EXPECTED_NESTED_KEYS[("C-2", "recommendations")]
    )
    assert set(c4_nearby_places.Place.model_fields) == set(
        EXPECTED_NESTED_KEYS[("C-4", "places")]
    )


def test_no_extra_key_is_added_for_convenience() -> None:
    """설계서에 없는 필드를 편의상 더하지 않았음 — 개수가 정확히 같음."""
    for connector_id, expected in EXPECTED_INPUT_KEYS.items():
        assert len(registry.TOOL_SPECS[connector_id].input_key_names) == len(expected)
    for connector_id, expected in EXPECTED_OUTPUT_KEYS.items():
        assert len(registry.TOOL_SPECS[connector_id].output_key_names) == len(expected)
