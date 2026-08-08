"""③ 4-1절 동기 요청 `S-R` — 노드 16개. **노드 1개 = ③ 단계 1개.**

함수 이름에 ③의 단계 식별자를 남김(`S-R2` → `node_S_R2_...`) — 장애 때 로그의 단계 이름과
함수를 바로 이을 수 있게 함.

담당자 — `S-R11`은 `R-1`, `S-R1` · `S-R14`는 계약 대상 밖, 나머지 13개는 `R-2`임.
"""

from __future__ import annotations

from typing import Any

from common.budget import compute_deadline_at
from common.state import LunchPickState, TriggerKind

from ..recommendation_history_service.agents import (
    r1_recommendation_sentence as r1,
    r2_recommendation_request as r2,
)
from ._common import (
    LandingReason,
    base_record_fields,
    call_context_of,
    check_deadline,
    connector_failure_update,
    halt_to_landing,
    merged,
    note_failure,
    now_ms,
    record_step,
)
from .context import FlowContext

__all__ = ["NODE_FUNCTIONS"]


# --- S-R1 추천 요청 발생(사용자 → 프론트엔드 · 계약 대상 밖) --------------------
async def node_S_R1_user_request(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """단말 구간이라 API 예산 밖임. 기록만 남기고 지나감."""
    record_step(context.recorder, "S-R1", base_record_fields("S-R1", state, context))
    return {}


# --- S-R2 추천 요청 접수 · 마감 시각 산정(진입 노드 · L-1 반복 진입) -------------
async def node_S_R2_receive_request(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """마감선을 넣는 **단 하나의 자리**이며 `iteration_count`를 올리는 자리이기도 함.

    마감선 값은 `01`의 설정에서 읽음 — 이 파일에 숫자가 없음.
    """
    verdict = check_deadline("S-R2", state, context)
    trigger = TriggerKind.SYNC_RECOMMEND
    iteration = int(state.get("iteration_count") or 0)
    deadline_at = state.get("deadline_at")
    if deadline_at is None:
        deadline_at = compute_deadline_at(trigger, now_ms(), context.settings)
    else:
        iteration += 1  # 되돌아온 간선임(L-1 재진입)

    payload = r2.assemble_request(
        request_id=context.input_of("request_id", context.request_id),
        member_id=context.input_of("member_id", ""),
        origin_lat=float(context.input_of("origin_lat", 0.0)),
        origin_lng=float(context.input_of("origin_lng", 0.0)),
        requested_at=int(context.input_of("requested_at", now_ms())),
        deadline_at=int(deadline_at),
        trigger_kind=trigger.value,
        reject_reason=context.input_of("reject_reason"),
        rejected_place_ids=context.input_of("rejected_place_ids") or (),
    )
    record_step(
        context.recorder,
        "S-R2",
        base_record_fields("S-R2", state, context, deadline_at=int(deadline_at)),
    )
    return merged(
        verdict.update,
        {
            "trigger_kind": trigger,
            "deadline_at": int(deadline_at),
            "iteration_count": iteration,
            "partial_context": [{"step_id": "S-R2", "K-1": payload}],
        },
    )


# --- S-R3 동의·사전 조건 확인 --------------------------------------------------
async def node_S_R3_check_precondition(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """미통과면 **안전 종료** — 위치 미확인 안내 + 수동 입력 경로(③ 4-1절 「초과 시 처리」)."""
    verdict = check_deadline("S-R3", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R3", base_record_fields("S-R3", state, context))
        return verdict.update

    result = r2.check_precondition(
        consent_rows=context.source_of("consent_log", ()),
        diet_restriction=context.source_of("diet_restriction"),
        excluded_ingredient_codes=context.source_of("excluded_ingredient_codes", ()),
    )
    context.hooks.inspector.inspect("S-R3", dict(result))
    record_step(context.recorder, "S-R3", base_record_fields("S-R3", state, context))
    update: dict[str, Any] = {"precheck_result": result}
    if not result["precheck_passed"]:
        update = merged(
            update, halt_to_landing("S-R3", LandingReason.PRECHECK_FAILED, result)
        )
    return update


# --- S-R4 ~ S-R7 병렬 컨텍스트 수집 -------------------------------------------
# 네 노드가 **같은 상태 필드를 쓰지 않음** — 전부 `partial_context`(누적 리듀서)에만 붙임.
async def node_S_R4_collect_meal_history(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """부분 결과로 계속 — 이력 없이 계산함(③ 4-1절)."""
    verdict = check_deadline("S-R4", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R4", base_record_fields("S-R4", state, context))
        return verdict.update
    fragment = r2.collect_meal_history(
        meal_history_rows=context.source_of("meal_history")
    )
    record_step(context.recorder, "S-R4", base_record_fields("S-R4", state, context))
    return {"partial_context": [{"step_id": "S-R4", **fragment}]}


async def node_S_R5_collect_preference_vector(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """부분 결과로 계속 — 콜드스타트 경로(③ 4-1절)."""
    verdict = check_deadline("S-R5", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R5", base_record_fields("S-R5", state, context))
        return verdict.update
    fragment = r2.collect_preference_vector(
        preference_vector_row=context.source_of("preference_vector")
    )
    record_step(context.recorder, "S-R5", base_record_fields("S-R5", state, context))
    return {"partial_context": [{"step_id": "S-R5", **fragment}]}


async def node_S_R6_fetch_weather(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`C-7` 현재 날씨 조회. 실패하면 부분 결과로 계속 — 날씨 가중치 제외(③ 4-1절)."""
    verdict = check_deadline("S-R6", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R6", base_record_fields("S-R6", state, context))
        return verdict.update

    result = await r2.fetch_weather(
        origin_lat=float(context.input_of("origin_lat", 0.0)),
        origin_lng=float(context.input_of("origin_lng", 0.0)),
        tool=context.tool("C-7"),
        call_context=call_context_of(state, context, completed_steps=("S-R3",)),
    )
    record_step(
        context.recorder,
        "S-R6",
        base_record_fields(
            "S-R6",
            state,
            context,
            **{
                "도구명": "C-7",
                "소요시간": None,
                "error.type": result.error_class.value if result.error_class else None,
                "응답 필드 수": len(result.output),
                "재시도 횟수": result.attempts,
            },
        ),
    )
    fragment = {"step_id": "S-R6", "ok": result.ok, **dict(result.output)}
    return merged(
        {"partial_context": [fragment]},
        {} if result.ok else connector_failure_update("S-R6", result, to_landing=False),
    )


async def node_S_R7_fetch_nearby_places(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`C-4` 주변 식당 조회. **안전 종료** — 후보 0건이면 추천을 만들지 않음(③ 4-1절)."""
    verdict = check_deadline("S-R7", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R7", base_record_fields("S-R7", state, context))
        return verdict.update

    result = await r2.fetch_nearby_places(
        origin_lat=float(context.input_of("origin_lat", 0.0)),
        origin_lng=float(context.input_of("origin_lng", 0.0)),
        radius_m=int(context.settings.knowledge_radius_m or 0),
        tool=context.tool("C-4"),
        call_context=call_context_of(state, context, completed_steps=("S-R3",)),
    )
    places = list(result.output.get("places", ()) or ())
    record_step(
        context.recorder,
        "S-R7",
        base_record_fields(
            "S-R7",
            state,
            context,
            **{
                "도구명": "C-4",
                "소요시간": None,
                "error.type": result.error_class.value if result.error_class else None,
                "응답 필드 수": len(result.output),
                "재시도 횟수": result.attempts,
            },
        ),
    )
    fragment = {"step_id": "S-R7", "ok": result.ok, "nearby_restaurants": places}
    if not result.ok or not places:
        return merged(
            {"partial_context": [fragment]},
            halt_to_landing("S-R7", LandingReason.CANDIDATE_EMPTY, {"count": len(places)}),
        )
    return {"partial_context": [fragment]}


# --- S-R8 영업 상태 필터 조회(합류 지점) --------------------------------------
async def node_S_R8_fetch_business_status(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """병렬 4단계의 **합류 지점**임.

    합류 규칙(되묻기 2로 정함) — **즉시 진행 + 빠진 값을 결과에 표기.**
    한쪽이 실패해도 기다리지 않고, 빠진 단계 이름을 `collect_errors`에 적어 다음 단계로 넘김.
    """
    verdict = check_deadline("S-R8", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R8", base_record_fields("S-R8", state, context))
        return verdict.update

    fragments = list(state.get("partial_context") or ())
    missing = [
        str(frag.get("step_id"))
        for frag in fragments
        if frag.get("ok") is False or frag.get("collect_errors")
    ]
    places = _places_of(fragments)
    result = await r2.fetch_business_status(
        place_ids=[str(p.get("place_id", "")) for p in places],
        tool=context.tool("C-8"),
        call_context=call_context_of(state, context, completed_steps=("S-R3", "S-R7")),
    )
    record_step(
        context.recorder,
        "S-R8",
        base_record_fields(
            "S-R8",
            state,
            context,
            **{
                "도구명": "C-8",
                "소요시간": None,
                "error.type": result.error_class.value if result.error_class else None,
                "응답 필드 수": len(result.output),
                "재시도 횟수": result.attempts,
            },
        ),
    )
    fragment = {
        "step_id": "S-R8",
        "ok": result.ok,
        "business_status_by_place": dict(result.output.get("business_status_by_place", {}) or {}),
        "business_filter_applied": bool(result.ok),
        "collect_errors": missing,
    }
    return merged(
        {"partial_context": [fragment]},
        {}
        if result.ok
        else note_failure("S-R8", LandingReason.STEP_EXHAUSTED, {"missing": missing}),
    )


# --- S-R9 알레르기·식이제한 하드 필터 ----------------------------------------
async def node_S_R9_apply_hard_filter(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """**안전 종료** — 불확실 시 해당 식당 전체 제외 후 후보 0건이면 중단(`V-10` 5번)."""
    verdict = check_deadline("S-R9", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R9", base_record_fields("S-R9", state, context))
        return verdict.update

    fragments = list(state.get("partial_context") or ())
    precheck = dict(state.get("precheck_result") or {})
    status = _first_value(fragments, "business_status_by_place") or {}
    result = r2.apply_hard_filter(
        nearby_restaurants=_places_of(fragments),
        excluded_ingredient_codes=precheck.get("excluded_ingredient_codes", ()),
        business_status_by_place=status,
        business_filter_applied=bool(_first_value(fragments, "business_filter_applied")),
        rejected_place_ids=context.input_of("rejected_place_ids") or (),
        mapping_failsafe=bool(context.source_of("allergen_mapping_failsafe", False)),
    )
    record_step(context.recorder, "S-R9", base_record_fields("S-R9", state, context))
    update: dict[str, Any] = {"candidate_set": result["candidate_places"]}
    if result["hard_filter_result"] == "후보0건":
        update = merged(
            update, halt_to_landing("S-R9", LandingReason.CANDIDATE_EMPTY, result)
        )
    elif result["hard_filter_result"] == "불확실":
        update = merged(
            update, note_failure("S-R9", LandingReason.HARD_FILTER_UNCERTAIN, result)
        )
    return merged(update, {"partial_context": [{"step_id": "S-R9", "K-5": result}]})


# --- S-R10 컨텍스트 파라미터 집합 구성 ---------------------------------------
async def node_S_R10_build_context_bundle(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`K-6` 모델 입력 집합을 만듦. 규격 밖 이름이 섞이면 `03-knowledge`가 막음."""
    verdict = check_deadline("S-R10", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R10", base_record_fields("S-R10", state, context))
        return verdict.update

    fragments = list(state.get("partial_context") or ())
    precheck = dict(state.get("precheck_result") or {})
    bundle = r2.build_context_bundle(
        context_tags=context.source_of("context_tags", ()),
        region_label=str(context.source_of("region_label", "")),
        weekday=str(context.input_of("weekday", "")),
        time_slot=str(context.input_of("time_slot", "")),
        preference_vector=context.source_of("preference_vector_values", ()),
        candidate_places=list(state.get("candidate_set") or ()),
        excluded_ingredient_codes=precheck.get("excluded_ingredient_codes", ()),
        correlation_key=str(context.input_of("correlation_key", context.request_id)),
        weather_temp_c=_first_value(fragments, "weather_temp_c"),
        recent_menu_names=context.source_of("recent_menu_names"),
    )
    bundle = dict(context.hooks.inspector.inspect("S-R10", dict(bundle)))
    record_step(context.recorder, "S-R10", base_record_fields("S-R10", state, context))
    return {"context_bundle": bundle}


# --- S-R11 개인화 추천 생성 호출(`R-1` · 모델 사용) ---------------------------
async def node_S_R11_generate_recommendation(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """`C-2` 추천 생성 커넥터 1곳으로만 모델을 부름.

    ③ 4-1절의 **조건부 1회 재시도**는 커넥터 계층이 설정에서 읽어 씀 —
    이 노드에 재시도 루프가 0건임(붙이면 횟수가 곱해짐).
    실패하면 **부분 결과로 계속** — 캐시 폴백(`S-R16`)으로 감.
    """
    verdict = check_deadline("S-R11", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R11", base_record_fields("S-R11", state, context))
        return verdict.update

    bundle = dict(state.get("context_bundle") or {})
    overlap = r1.excluded_overlap(
        candidate_places=bundle.get("candidate_places", ()),
        excluded_ingredient_codes=bundle.get("excluded_ingredient_codes", ()),
    )
    if overlap:
        # ④ 3-1절 중단 조건 ⓐ — 모델을 부르지 않고 멈춤(⑥ `B-1`).
        record_step(context.recorder, "S-R11", base_record_fields("S-R11", state, context))
        return halt_to_landing(
            "S-R11", LandingReason.GUARDRAIL_BLOCKED, {"overlap_place_ids": list(overlap)}
        )

    result = await r1.generate_recommendation_set(
        tool=context.tool("C-2"),
        call_context=call_context_of(state, context, completed_steps=("S-R9",)),
        **{key: bundle.get(key) for key in r1.K6_KEYS},
    )
    record_step(
        context.recorder,
        "S-R11",
        base_record_fields(
            "S-R11",
            state,
            context,
            **{
                "프롬프트 버전": r1.SYSTEM_PROMPT_FILE.name,
                "gen_ai.usage.input_tokens": None,
                "gen_ai.usage.output_tokens": None,
                "건당 환산 금액": None,
                "일일 누적 콜 수": None,
                "일일 콜 수": None,
                "일일 환산 금액": None,
                "임계 도달 여부": False,
            },
        ),
    )
    if not result.ok:
        return connector_failure_update("S-R11", result, to_landing=True)
    return {"recommendation_set": dict(result.output)}


# --- S-R12 확신 스코어 검증 · 안전망 대체 판정 -------------------------------
async def node_S_R12_verify_confidence(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """부분 결과로 계속 — 안전망 추천 + 학습 중 안내(③ 4-1절 · `V-10` 6번)."""
    verdict = check_deadline("S-R12", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R12", base_record_fields("S-R12", state, context))
        return verdict.update

    recommendations = list(
        (state.get("recommendation_set") or {}).get("recommendations", ()) or ()
    )
    result = r2.verify_confidence(
        recommendations=recommendations,
        confidence_threshold=context.source_of("confidence_threshold"),
    )
    record_step(
        context.recorder,
        "S-R12",
        base_record_fields(
            "S-R12",
            state,
            context,
            **{
                "확신 스코어": [row.get("confidence_score") for row in recommendations],
                "임계 통과 여부": result["confidence_threshold_met"],
                "안전망 대체 여부": result["safety_net_applied"],
            },
        ),
    )
    update: dict[str, Any] = {"verification_result": result}
    if result["safety_net_applied"]:
        update = merged(
            update,
            note_failure(
                "S-R12",
                LandingReason.GUARDRAIL_BLOCKED,
                {"fallback_reason": result["fallback_reason"]},
            ),
        )
    return update


# --- S-R13 추천 카드 3장 응답 송출 -------------------------------------------
async def node_S_R13_send_cards(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """출력측 검사·가리기를 지난 뒤에만 밖으로 나감(⑥ `O-C1` ~ `O-C3`)."""
    verdict = check_deadline("S-R13", state, context)
    if verdict.blocked:
        record_step(context.recorder, "S-R13", base_record_fields("S-R13", state, context))
        return verdict.update

    verification = dict(state.get("verification_result") or {})
    response = r2.build_response_cards(
        recommendations=(state.get("recommendation_set") or {}).get("recommendations", ()),
        candidate_places=state.get("candidate_set") or (),
        context_tags=(state.get("context_bundle") or {}).get("context_tags", ()),
        safety_net_applied=bool(verification.get("safety_net_applied")),
        fallback_reason=verification.get("fallback_reason"),
    )
    response = dict(context.hooks.redactor.redact("S-R13", response))
    record_step(
        context.recorder,
        "S-R13",
        base_record_fields(
            "S-R13",
            state,
            context,
            **{
                "출력측 검사 결과 3종": ["O-C1", "O-C2", "O-C3"],
                "3필드 완전성": bool(response.get("cards")),
                "fallback_reason": verification.get("fallback_reason"),
            },
        ),
    )
    return {"partial_context": [{"step_id": "S-R13", "K-9": response}]}


# --- S-R14 추천 카드 화면 표시(프론트엔드 → 사용자 · 계약 대상 밖) -------------
async def node_S_R14_render_cards(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """단말 구간이라 API 예산 밖임."""
    record_step(context.recorder, "S-R14", base_record_fields("S-R14", state, context))
    return {}


# --- S-R15 직전 추천 결과 캐시 적재(응답 후) ---------------------------------
async def node_S_R15_store_cache(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """응답을 닫은 뒤 도는 후처리라 어느 마감선에도 들어가지 않음."""
    fragments = list(state.get("partial_context") or ())
    cards = (_first_value(fragments, "K-9") or {}).get("cards", ())
    entry = r2.build_cache_entry(
        member_id=str(context.input_of("member_id", "")),
        cards=cards,
        cache_created_at=now_ms(),
    )
    record_step(
        context.recorder,
        "S-R15",
        base_record_fields(
            "S-R15",
            state,
            context,
            **{
                "도구명": "S-5",
                "입력 요약": {"card_count": len(entry["cards"])},
                "결과": "적재",
                "소요시간": None,
                "동의 시각·버전": None,
                "멱등성 키 해시": None,
            },
        ),
    )
    return {"partial_context": [{"step_id": "S-R15", "cache_entry": entry}]}


# --- S-R16 착지 — 캐시 폴백 추천 제시 ----------------------------------------
async def node_S_R16_landing_cache_fallback(
    state: LunchPickState, context: FlowContext
) -> dict[str, Any]:
    """착지 노드 — ③ 8-1절이 동기 요청에 고른 값 1개(`부분 결과로 계속`)대로 만듦.

    **여기서 상한을 다시 쓰지 않음** — 모델 호출 0건 · 재시도 0건 · 재조회 0건임.
    `fallback_reason`을 쓰는 자리는 이 노드 1개뿐임(③ 6절 9번).
    """
    from .signals import landing_reason_of

    reason = landing_reason_of(state) or LandingReason.STEP_EXHAUSTED.value
    cached = context.source_of("recommendation_cache") or {}
    response = r2.build_fallback_response(
        cached_cards=cached.get("cards"),
        fallback_reason=reason,
        cache_created_at=cached.get("cache_created_at"),
    )
    response = dict(context.hooks.redactor.redact("S-R16", response))
    record_step(
        context.recorder,
        "S-R16",
        base_record_fields(
            "S-R16",
            state,
            context,
            **{
                "fallback_reason": reason,
                "캐시 나이(초)": None,
                "착지 사유": reason,
            },
        ),
    )
    return {
        "fallback_reason": reason,
        "partial_context": [{"step_id": "S-R16", "K-10": response}],
    }


# --- 조각 -------------------------------------------------------------------
def _places_of(fragments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for fragment in reversed(fragments):
        places = fragment.get("nearby_restaurants")
        if places:
            return list(places)
    return []


def _first_value(fragments: list[dict[str, Any]], key: str) -> Any:
    for fragment in reversed(fragments):
        if key in fragment and fragment[key] is not None:
            return fragment[key]
    return None


NODE_FUNCTIONS: dict[str, Any] = {
    "S-R1": node_S_R1_user_request,
    "S-R2": node_S_R2_receive_request,
    "S-R3": node_S_R3_check_precondition,
    "S-R4": node_S_R4_collect_meal_history,
    "S-R5": node_S_R5_collect_preference_vector,
    "S-R6": node_S_R6_fetch_weather,
    "S-R7": node_S_R7_fetch_nearby_places,
    "S-R8": node_S_R8_fetch_business_status,
    "S-R9": node_S_R9_apply_hard_filter,
    "S-R10": node_S_R10_build_context_bundle,
    "S-R11": node_S_R11_generate_recommendation,
    "S-R12": node_S_R12_verify_confidence,
    "S-R13": node_S_R13_send_cards,
    "S-R14": node_S_R14_render_cards,
    "S-R15": node_S_R15_store_cache,
    "S-R16": node_S_R16_landing_cache_fallback,
}
