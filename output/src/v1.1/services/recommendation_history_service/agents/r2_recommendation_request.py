"""`R-2` 추천 요청 조립·검증 처리기 — ④ 3-2절.

맡은 ③ 단계 13개 — `S-R2` ~ `S-R10` · `S-R12` · `S-R13` · `S-R15` · `S-R16`.
사용 모델 — **모델 미사용(결정론적 실행).** 모델 어댑터를 부르지 않고 프롬프트 파일도 없음.
사용 도구 — `T-2` · `T-3` · `T-4` · `T-8` · `T-10` · `T-11` 조회 · `C-4` · `C-7` · `C-8` 커넥터 ·
`S-5` 캐시 적재 · `S-6` 감사 로그 적재.

함수는 **상태 전체를 받지 않음.** ④ 「입출력 형식」의 자기 입력 키만 받음.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from common.knowledge import build_model_input
from common.knowledge.prefilter import FilterOutcome, allergen_hard_filter
from toolkit.runner import CallContext, ConnectorResult, ConnectorTool

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "assemble_request",
    "check_precondition",
    "collect_meal_history",
    "collect_preference_vector",
    "fetch_weather",
    "fetch_nearby_places",
    "fetch_business_status",
    "apply_hard_filter",
    "build_context_bundle",
    "verify_confidence",
    "build_response_cards",
    "build_cache_entry",
    "build_fallback_response",
]

OWNER_ID = "R-2"
STEP_IDS = (
    "S-R2", "S-R3", "S-R4", "S-R5", "S-R6", "S-R7", "S-R8", "S-R9", "S-R10",
    "S-R12", "S-R13", "S-R15", "S-R16",
)

_CARD_COUNT = 3
"""④ 「입출력 형식」 `K-9`의 `card_count`가 `3 고정`이라고 적은 값임(단계 상한이 아님)."""


# --- S-R2 요청 접수 · 마감 시각 산정 -----------------------------------------
def assemble_request(
    *,
    request_id: str,
    member_id: str,
    origin_lat: float,
    origin_lng: float,
    requested_at: int,
    deadline_at: int,
    trigger_kind: str,
    reject_reason: str | None = None,
    rejected_place_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """`K-1` 요청 접수 집합을 냄. 앞 7개 필수 · 뒤 2개는 거절 후 대체 추천일 때 조건 필수."""
    return {
        "request_id": request_id,
        "member_id": member_id,
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "requested_at": requested_at,
        "deadline_at": deadline_at,
        "trigger_kind": trigger_kind,
        "reject_reason": reject_reason,
        "rejected_place_ids": list(rejected_place_ids or ()),
    }


# --- S-R3 동의·사전 조건 확인 -------------------------------------------------
def check_precondition(
    *,
    consent_rows: Sequence[Mapping[str, Any]],
    diet_restriction: Mapping[str, Any] | None,
    excluded_ingredient_codes: Sequence[str],
) -> dict[str, Any]:
    """`K-2` 사전조건 결과 집합을 냄.

    ④ 중단 조건 ⓐ — 위치 동의가 거절이거나 좌표를 확인할 수 없으면 `precheck_passed`가 거짓임.
    """
    granted = {
        str(row.get("consent_kind")): bool(row.get("consent_granted"))
        for row in consent_rows or ()
    }
    location_consent = granted.get("위치", False)
    health_consent = granted.get("건강", False)
    diet_type = str((diet_restriction or {}).get("diet_type", "없음"))
    return {
        "location_consent": location_consent,
        "health_consent": health_consent,
        "excluded_ingredient_codes": list(excluded_ingredient_codes),
        "diet_type": diet_type,
        "precheck_passed": location_consent,
    }


# --- S-R4 ~ S-R7 병렬 컨텍스트 수집 -------------------------------------------
# 병렬 4단계는 `K-3` 안에서 **서로 다른 키만** 채움. 같은 키를 두 단계가 쓰지 않음.
def collect_meal_history(
    *, meal_history_rows: Sequence[Mapping[str, Any]] | None
) -> dict[str, Any]:
    """`K-3`의 `recent_meal_history`(선택) 1칸만 채움."""
    if meal_history_rows is None:
        return {"recent_meal_history": None, "collect_errors": ["S-R4"]}
    return {"recent_meal_history": list(meal_history_rows), "collect_errors": []}


def collect_preference_vector(
    *, preference_vector_row: Mapping[str, Any] | None
) -> dict[str, Any]:
    """`K-3`의 `preference_vector_ref`(선택) 1칸만 채움. 콜드스타트면 비움."""
    if not preference_vector_row:
        return {"preference_vector_ref": None, "collect_errors": ["S-R5"]}
    return {
        "preference_vector_ref": str(preference_vector_row.get("preference_vector_ref", "")),
        "collect_errors": [],
    }


async def fetch_weather(
    *,
    origin_lat: float,
    origin_lng: float,
    tool: ConnectorTool,
    call_context: CallContext,
) -> ConnectorResult:
    """`C-7` 현재 날씨 조회. `K-3`의 `weather_temp_c` · `weather_condition`을 채움."""
    return await tool.call(
        {"origin_lat": origin_lat, "origin_lng": origin_lng}, call_context
    )


async def fetch_nearby_places(
    *,
    origin_lat: float,
    origin_lng: float,
    radius_m: int,
    tool: ConnectorTool,
    call_context: CallContext,
) -> ConnectorResult:
    """`C-4` 주변 식당 조회. `K-3`의 `nearby_restaurants`(필수)를 채움."""
    return await tool.call(
        {"origin_lat": origin_lat, "origin_lng": origin_lng, "radius_m": radius_m},
        call_context,
    )


# --- S-R8 영업 상태 필터 조회 -------------------------------------------------
async def fetch_business_status(
    *,
    place_ids: Sequence[str],
    tool: ConnectorTool,
    call_context: CallContext,
) -> ConnectorResult:
    """`C-8` 영업 상태 조회 → `K-4`."""
    return await tool.call({"place_ids": list(place_ids)}, call_context)


# --- S-R9 알레르기·식이제한 하드 필터 ----------------------------------------
def apply_hard_filter(
    *,
    nearby_restaurants: Sequence[Mapping[str, Any]],
    excluded_ingredient_codes: Sequence[str],
    business_status_by_place: Mapping[str, str] | None,
    business_filter_applied: bool,
    rejected_place_ids: Sequence[str] = (),
    mapping_failsafe: bool = False,
) -> dict[str, Any]:
    """`K-5` 후보 확정 집합을 냄.

    ④ 중단 조건 ⓒ — 판정이 불확실하면 그 식당 **전체를 제외**함(페일세이프).
    남은 후보가 0건이면 `hard_filter_result`가 `후보0건`이 되어 흐름이 멈춤.
    """
    rejected = set(rejected_place_ids or ())
    status = dict(business_status_by_place or {})
    kept: list[dict[str, Any]] = []
    excluded = 0
    uncertain = False
    for place in nearby_restaurants or ():
        place_id = str(place.get("place_id", ""))
        if place_id in rejected:
            excluded += 1
            continue
        if business_filter_applied and status.get(place_id) in {"폐업", "정지"}:
            excluded += 1
            continue
        verdict = allergen_hard_filter(
            excluded_ingredient_codes=excluded_ingredient_codes,
            place_ingredient_codes=place.get("ingredient_codes"),
            mapping_failsafe=mapping_failsafe,
        )
        if verdict.outcome is FilterOutcome.BLOCK:
            excluded += 1
            uncertain = uncertain or "알 수 없" in verdict.reason or mapping_failsafe
            continue
        kept.append(dict(place))
    if not kept:
        result = "후보0건"
    elif uncertain:
        result = "불확실"
    else:
        result = "적용"
    return {
        "candidate_places": kept,
        "hard_filter_result": result,
        "excluded_place_count": excluded,
    }


# --- S-R10 컨텍스트 파라미터 집합 구성 ---------------------------------------
def build_context_bundle(
    *,
    context_tags: Sequence[str],
    region_label: str,
    weekday: str,
    time_slot: str,
    preference_vector: Sequence[float],
    candidate_places: Sequence[Mapping[str, Any]],
    excluded_ingredient_codes: Sequence[str],
    correlation_key: str,
    weather_temp_c: float | None = None,
    recent_menu_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """`K-6` 모델 입력 집합을 냄. 규격 밖 이름이 섞이면 `03-knowledge`가 막음."""
    fields: dict[str, Any] = {
        "context_tags": list(context_tags),
        "region_label": region_label,
        "weekday": weekday,
        "time_slot": time_slot,
        "preference_vector": list(preference_vector),
        "candidate_places": [dict(place) for place in candidate_places],
        "excluded_ingredient_codes": list(excluded_ingredient_codes),
        "correlation_key": correlation_key,
    }
    if weather_temp_c is not None:
        fields["weather_temp_c"] = weather_temp_c
    if recent_menu_names is not None:
        fields["recent_menu_names"] = list(recent_menu_names)
    return build_model_input(**fields)


# --- S-R12 확신 스코어 검증 · 안전망 대체 판정 -------------------------------
def verify_confidence(
    *,
    recommendations: Sequence[Mapping[str, Any]],
    confidence_threshold: float | None,
) -> dict[str, Any]:
    """`K-8` 검증 결과 집합을 냄.

    ④ 중단 조건 ⓓ — 임계값이 `[확인필요]`라 없으면 통과로 단정하지 않고 안전망으로 갈아탐.
    """
    scores = [float(row.get("confidence_score", 0.0)) for row in recommendations or ()]
    complete = bool(recommendations) and all(
        row.get("reason_line") and row.get("confidence_score") is not None
        for row in recommendations
    )
    if confidence_threshold is None:
        return {
            "verification_passed": False,
            "confidence_threshold_met": False,
            "safety_net_applied": True,
            "fallback_reason": "[확인필요: 확신 스코어 노출 임계값]",
        }
    met = bool(scores) and min(scores) >= confidence_threshold
    return {
        "verification_passed": complete and met,
        "confidence_threshold_met": met,
        "safety_net_applied": not met,
        "fallback_reason": None if met else "confidence_below_threshold",
    }


# --- S-R13 추천 카드 3장 응답 송출 -------------------------------------------
def build_response_cards(
    *,
    recommendations: Sequence[Mapping[str, Any]],
    candidate_places: Sequence[Mapping[str, Any]],
    context_tags: Sequence[str],
    safety_net_applied: bool,
    fallback_reason: str | None = None,
    reason_detail: str | None = None,
) -> dict[str, Any]:
    """`K-9` 응답 카드 집합을 냄. `card_count`는 `3 고정`임."""
    by_place = {str(p.get("place_id", "")): p for p in candidate_places or ()}
    cards: list[dict[str, Any]] = []
    for row in list(recommendations or ())[:_CARD_COUNT]:
        place = by_place.get(str(row.get("place_id", "")), {})
        cards.append(
            {
                "recommendation_id": str(row.get("recommendation_id", "")),
                "menu_name": str(row.get("menu_name", "")),
                "place_name": str(place.get("place_name", "")),
                "distance_m": int(place.get("distance_m", 0)),
                "walk_minutes": int(place.get("walk_minutes", 0)),
                "reason_line": str(row.get("reason_line", "")),
                "confidence_score": float(row.get("confidence_score", 0.0)),
                "context_tags": list(context_tags),
                "signature_menu": place.get("signature_menu"),
                "price": place.get("price"),
            }
        )
    return {
        "cards": cards,
        "card_count": _CARD_COUNT,
        "reason_detail": reason_detail,
        "fallback_notice": fallback_reason,
        "learning_notice": "학습 중" if safety_net_applied else None,
    }


# --- S-R15 직전 추천 결과 캐시 적재(응답 후) ---------------------------------
def build_cache_entry(
    *, member_id: str, cards: Sequence[Mapping[str, Any]], cache_created_at: int
) -> dict[str, Any]:
    """`S-5` 추천 캐시에 넣을 값. 덮어쓰기만 함(⑥ `R-2` 제한 장치 `overwrite_only`)."""
    return {
        "member_id": member_id,
        "cards": [dict(card) for card in cards],
        "cache_created_at": cache_created_at,
    }


# --- S-R16 착지 — 캐시 폴백 추천 제시 ----------------------------------------
def build_fallback_response(
    *,
    cached_cards: Sequence[Mapping[str, Any]] | None,
    fallback_reason: str,
    cache_created_at: int | None,
) -> dict[str, Any]:
    """`K-10` 폴백 카드 집합을 냄.

    **착지 경로가 상한을 다시 쓰지 않음** — 모델 호출 0건 · 재조회 0건 · 재시도 0건임.
    캐시도 없으면 카드 0장으로 안내만 냄.
    """
    return {
        "cards": [dict(card) for card in cached_cards or ()],
        "fallback_reason": fallback_reason,
        "cache_created_at": cache_created_at,
    }
