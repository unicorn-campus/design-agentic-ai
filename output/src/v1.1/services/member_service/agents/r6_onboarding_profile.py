"""`R-6` 온보딩 프로파일 생성 처리기 — ④ 3-6절.

맡은 ③ 단계 3개 — `S-E5` ~ `S-E7`.
사용 모델 — **모델 미사용(결정론적 실행).** 초기 벡터 생성 수단이
`[확인필요: 온보딩 스와이프 결과 조회 경로와 초기 취향 벡터 생성 수단]`이라 모델 호출 도구가 0건임.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "MIN_SWIPE_COUNT",
    "TOP_CATEGORY_COUNT",
    "check_swipe_count",
    "build_initial_profile",
    "build_onboarding_reply",
]

OWNER_ID = "R-6"
STEP_IDS = ("S-E5", "S-E6", "S-E7")

MIN_SWIPE_COUNT = 7
"""④ 「성공 기준」이 인용한 기획 원문 값 — `ES:01#최소7장`. 단계 상한이 아님."""
TOP_CATEGORY_COUNT = 3
"""`US:UFR-MBR-020#처리결과` Top 3. 위와 같이 기획 원문 값임."""


def check_swipe_count(
    *, swipe_count: int, health_consent: bool, diet_value_present: bool
) -> dict[str, Any]:
    """`S-E5` 최소 7장 스와이프 완료 확인.

    ④ 중단 조건 ⓐ — 7장 미만이면 벡터를 만들지 않고 멈춤(온보딩 계속 안내).
    ④ 중단 조건 ⓑ — 건강 민감정보 동의가 없는데 식이제한 값이 들어오면 그 값을 받지 않고 멈춤.
    """
    consent_violation = diet_value_present and not health_consent
    return {
        "swipe_count": swipe_count,
        "health_consent": health_consent,
        "consent_violation": consent_violation,
        "precheck_passed": swipe_count >= MIN_SWIPE_COUNT and not consent_violation,
    }


def build_initial_profile(
    *,
    member_id: str,
    onboarding_round: int,
    swipe_results: Sequence[Mapping[str, Any]],
    swipe_count: int,
    health_consent: bool,
    idempotency_key: str,
) -> dict[str, Any]:
    """`S-E6` `K-16` 초기 프로파일 집합.

    ④ 중단 조건 ⓒ — 중복 방지 키가 이미 처리된 건이면 적재하지 않음(판정은 흐름 쪽 저장소가 함).
    """
    if swipe_count < MIN_SWIPE_COUNT:
        raise ValueError(f"스와이프 {MIN_SWIPE_COUNT}장 미만 — 초기 벡터를 만들지 않음")
    if not idempotency_key:
        raise ValueError("중복 방지 키가 빔 — 적재하지 않음")
    liked = [row for row in swipe_results if row.get("liked")]
    counted: dict[str, int] = {}
    for row in liked:
        code = str(row.get("category_code", row.get("card_id", "")))
        counted[code] = counted.get(code, 0) + 1
    top = [
        code
        for code, _ in sorted(counted.items(), key=lambda kv: kv[1], reverse=True)[
            :TOP_CATEGORY_COUNT
        ]
    ]
    # 초기 벡터 생성 수단이 미확정이라 **좋아한 비율만** 담은 결정론 벡터를 둠.
    total = len(swipe_results) or 1
    vector = [round(len(liked) / total, 6)]
    return {
        "member_id": member_id,
        "onboarding_round": onboarding_round,
        "initial_preference_vector": vector,
        "top_categories": top,
        "swipe_count": swipe_count,
        "idempotency_key": idempotency_key,
    }


def build_onboarding_reply(
    *,
    member_id: str,
    onboarding_round: int,
    initial_preference_vector: Sequence[float],
    top_categories: Sequence[str],
    swipe_count: int,
    idempotency_key: str,
) -> dict[str, Any]:
    """`S-E7` 온보딩 완료 응답 · 취향 요약 카드 전달. `K-16` 키를 그대로 냄."""
    return {
        "member_id": member_id,
        "onboarding_round": onboarding_round,
        "initial_preference_vector": list(initial_preference_vector),
        "top_categories": list(top_categories),
        "swipe_count": swipe_count,
        "idempotency_key": idempotency_key,
    }
