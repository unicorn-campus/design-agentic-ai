"""④ 3-1절 `S-R` 동기 요청 시퀀스를 LangGraph 그래프로 옮긴 것.

단계 13개(S-R1 ~ S-R13)와 도식이 1:1임. 상상해 넣은 단계는 없음.

**순서가 곧 안전 요건임**(④ 5-2절). `S-R8 → S-R9 → S-R10`을 고정 간선으로
두어 하드필터가 C-1보다 먼저 실행되게 함. 순서가 어긋나면 인자가 다 맞아도
0점임(⑤ 7절 `ToolCallAccuracy = 1.0` 엄격 순서 모드).

병렬 구간은 `S-R5`(캐시 조회) ∥ `S-R6`(C-3 날씨)뿐이며, 서로 다른 상태
필드에 쓰도록 갈라 뒀으므로 겹침이 없음(④ 7절).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from lp_common import db
from lp_common.budget import SR, sr10_override_ms, timeout_sec
from lp_common.codes import FILTER_RULESET_VERSION
from lp_common.errors import LunchpickError
from lp_common.observability import span, write_access_log

from ..agents import a1_safe_candidate as a1
from ..agents import a2_reason_gen as a2
from ..connectors.c1_reason import ReasonConnector
from ..connectors.c3_weather import WeatherConnector
from ..guardrails import checks
from .state import RecommendState

log = logging.getLogger("lp.graph")


class RecommendRuntime:
    """그래프가 쓰는 커넥터·설정 묶음. 노드는 이걸 클로저로 잡음."""

    def __init__(self, settings) -> None:  # noqa: ANN001
        self.settings = settings
        self.reason = ReasonConnector(
            mode=settings.llm_mode,
            api_key=settings.anthropic_api_key,
            model=settings.llm_model,
        )
        self.weather = WeatherConnector(
            mode=settings.weather_mode, api_key=settings.openweather_api_key
        )


def build_graph(rt: RecommendRuntime):
    """S-R1 ~ S-R13 그래프를 조립함."""

    # ── S-R2 동의 상태 확인 (④ 5-1절 · 신설 사전 조건 확인 노드) ───────────────
    async def s_r2_consent(state: RecommendState) -> dict[str, Any]:
        """온보딩 1회 동의와 **별개로 요청 시점의 동의 상태**를 확인함.

        동의는 철회될 수 있으므로 1회 획득이 상시 유효를 뜻하지 않음.
        저장소 조회 **전**에 두어 동의 없는 상태로 좌표·알레르기 항목명을
        읽지 않게 함(④ 5-1절).
        """
        async with span("O-3", "S-R2", state["trace_id"], span_name="invoke_agent gate") as attrs:
            row = await db.fetchrow(
                "ro",
                "SELECT location_consent, sensitive_consent FROM consent WHERE member_ref = $1",
                state["member_ref"],
            )
            if row is None:
                raise LunchpickError("AUTH_FAIL", "동의 기록이 없는 회원임")
            has_restriction = await db.fetchrow(
                "ro",
                "SELECT (allergen_names <> '{}' OR diet_types <> '{}') AS has "
                "FROM dietary_restriction WHERE member_ref = $1",
                state["member_ref"],
            )
            restricted = bool(has_restriction and has_restriction["has"])
            attrs.update(
                location_consent=row["location_consent"],
                sensitive_consent=row["sensitive_consent"],
                has_restriction=restricted,
            )

            # ③ A-1 중단 조건 ④ (D-18) — 위치정보 수집 동의
            if not row["location_consent"] and not state.get("manual_area_code"):
                raise LunchpickError("CONSENT_REQUIRED", "위치정보 수집 동의가 확인되지 않음")
            # ③ A-1 중단 조건 ⑤ (D-20) — 민감정보 별도 동의
            # **필터 없이 진행하지 않음** — 필터 미적용은 ① G-3 위반임(④ 5-1절)
            if restricted and not row["sensitive_consent"]:
                raise LunchpickError(
                    "SENSITIVE_CONSENT_REQUIRED", "식이제한 설정 회원인데 별도 동의가 없음"
                )
            return {"member_ctx": {"sensitive_consent": row["sensitive_consent"]}}

    # ── S-R3 회원·취향·식이제한 조회 ────────────────────────────────────────
    async def s_r3_profile(state: RecommendState) -> dict[str, Any]:
        async with span("O-3", "S-R3", state["trace_id"], span_name="invoke_agent A-1") as attrs:
            ctx = await a1.load_member_context(state["member_ref"])
            # O-9 개인정보 접근 로그 — 값은 남기지 않고 항목 종류만
            await write_access_log(
                actor="A-1",
                member_ref=state["member_ref"],
                field_ids=["F-1", "F-9", "F-10"],
                decrypt_called=bool(ctx["allergen_names"] or ctx["diet_types"]),
                trace_id=state["trace_id"],
            )
            scores = ctx["category_scores"] or {}
            if isinstance(scores, str):
                import json

                scores = json.loads(scores)
            coldstart = int(ctx["feedback_count"]) < a1.COLDSTART_FEEDBACK_THRESHOLD
            attrs.update(coldstart=coldstart, feedback_count=int(ctx["feedback_count"]))
            merged = dict(state.get("member_ctx") or {})
            merged.update(ctx)
            merged["category_scores"] = scores
            return {
                "member_ctx": merged,
                "region_code": ctx["region_code"],
                "coldstart": coldstart,
                "preference_codes": sorted(scores, key=scores.get, reverse=True)[:5],
            }

    # ── S-R4 이력 조회 ──────────────────────────────────────────────────────
    async def s_r4_history(state: RecommendState) -> dict[str, Any]:
        async with span("O-2", "S-R4", state["trace_id"], span_name="execute_tool history") as attrs:
            hist = await a1.load_history(state["member_ref"], state["at"])
            attrs.update(
                recent_categories=len(hist["recent_category_codes"]),
                recent_restaurants=len(hist["recent_restaurant_ids"]),
                cache_hit=False,
            )
            return {
                "recent_category_codes": hist["recent_category_codes"],
                "recent_restaurant_ids": sorted(hist["recent_restaurant_ids"]),
            }

    # ── S-R5 반경 후보 조회 (병렬) — 캐시 DB4만 읽음. 지도 API 아님(J-6) ───────
    async def s_r5_radius(state: RecommendState) -> dict[str, Any]:
        async with span("O-2", "S-R5", state["trace_id"], span_name="execute_tool cache") as attrs:
            geo = state["geo_point"]
            rows = await a1.load_radius_candidates(
                state["region_code"], geo["lat"], geo["lng"], state["at"].hour
            )
            # ⑥ 10-1절 잔여 검사 — 읽기 시점에 길이·제어문자만 얕게 봄
            shallow_hits = 0
            for row in rows:
                cleaned, changed = checks.shallow_read_check(
                    row["display_name"], max_len=rt.settings.display_name_max_len
                )
                if changed:
                    shallow_hits += 1
                    row["display_name"] = cleaned
            attrs.update(raw_count=len(rows), shallow_sanitized=shallow_hits)
            return {"raw_candidates": rows}

    # ── S-R6 날씨 조회 (병렬) — C-3. 서로 다른 필드에 씀 ────────────────────
    async def s_r6_weather(state: RecommendState) -> dict[str, Any]:
        async with span("O-2", "S-R6", state["trace_id"], span_name="execute_tool C-3") as attrs:
            budget = SR["S-R6"]
            attempt = 0
            last: Exception | None = None
            # L-1 커넥터 재시도 1회 — 계층별로 이름을 나눠 셈(④ 9-3절)
            while attempt <= budget.retries:
                try:
                    code = await asyncio.wait_for(
                        rt.weather.fetch(state["region_code"], timeout_sec=timeout_sec("S-R6")),
                        timeout=timeout_sec("S-R6"),
                    )
                    attrs.update(weather_code=code, connector_retry_count=attempt)
                    return {
                        "weather_code": code,
                        "retry_count_by_layer": {"L-1": attempt},
                    }
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    attempt += 1
            # 날씨 실패는 추천을 멈추지 않음 — 태그에서 날씨를 빼고 계속함
            log.warning("C-3 실패로 날씨 없이 진행함 err=%s", type(last).__name__)
            attrs.update(weather_code="UNKNOWN", connector_retry_count=attempt, degraded=True)
            return {"weather_code": "UNKNOWN", "retry_count_by_layer": {"L-1": attempt}}

    # ── S-R7 낱말 코드 고정 (용어사전) ───────────────────────────────────────
    async def s_r7_lexicon(state: RecommendState) -> dict[str, Any]:
        async with span("O-3", "S-R7", state["trace_id"], span_name="invoke_agent A-1") as attrs:
            weekday = a1.weekday_code_of(state["at"])
            daypart = a1.daypart_code_of(state["at"])
            attrs.update(weekday_code=weekday, daypart_code=daypart)
            return {"weekday_code": weekday, "daypart_code": daypart}

    # ── S-R8 하드필터 적용 — 결정론. LLM 앞단(② 5절 사유 2) ──────────────────
    async def s_r8_filter(state: RecommendState) -> dict[str, Any]:
        async with span("O-3", "S-R8", state["trace_id"], span_name="invoke_agent A-1") as attrs:
            ctx = state["member_ctx"]
            survivors, stats, unresolved = a1.apply_hard_filter(
                state["raw_candidates"],
                allergen_names=list(ctx.get("allergen_names") or []),
                diet_types=list(ctx.get("diet_types") or []),
                recent_restaurant_ids=set(state.get("recent_restaurant_ids") or []),
                hour=state["at"].hour,
                read_allergens=bool(ctx.get("sensitive_consent", True)),
            )
            # 거절 이력을 뺌 — L-1/L-2 루프 재실행 경로(③ 3절 흡수 판정)
            rejected = set(state.get("reject_history") or [])
            if rejected:
                survivors = [c for c in survivors if c["restaurant_id"] not in rejected]

            prior_scores: dict[str, float] | None = None
            prior_source = None
            if state.get("coldstart"):
                prior_scores = await a1.load_prior_scores(
                    ctx.get("job_cluster_code"), state["region_code"]
                )
                prior_source = "job_cluster_prior" if prior_scores else "region_popularity"

            ranked = a1.rank_candidates(
                survivors,
                category_scores=ctx.get("category_scores") or {},
                recent_category_codes=state.get("recent_category_codes") or [],
                coldstart=bool(state.get("coldstart")),
                prior_scores=prior_scores,
            )
            excluded = len(state["raw_candidates"]) - len(survivors)
            tags = a1.build_context_tags(
                weather_code=state.get("weather_code", "UNKNOWN"),
                recent_category_codes=state.get("recent_category_codes") or [],
                coldstart=bool(state.get("coldstart")),
            )
            # O-8 차단·필터 기록 — 페일세이프 발동 건수를 반드시 남김(⑥ M-Q5 100%)
            attrs.update(
                excluded_count=excluded,
                block_stats=stats,
                failsafe_count=stats["B-2"],
                unresolved_terms=unresolved,
                survivor_count=len(ranked),
            )
            return {
                "candidates": ranked,
                # 이 두 키가 ⑤ 5절 신설 장치임 — A-1 출력이 값의 주인
                "filter_applied": True,
                "filter_ruleset_version": FILTER_RULESET_VERSION,
                "excluded_count": excluded,
                "context_tags": tags,
                "block_stats": stats,
                "unresolved_terms": unresolved,
                "prior_source": prior_source,
                "no_candidate": len(ranked) == 0,
            }

    # ── S-R9 사전 조건 확인 — 안전 요건 (④ 5-2절) ───────────────────────────
    async def s_r9_gate(state: RecommendState) -> dict[str, Any]:
        async with span("O-3", "S-R9", state["trace_id"], span_name="invoke_agent gate") as attrs:
            attrs.update(
                filter_applied=state.get("filter_applied"),
                ruleset=state.get("filter_ruleset_version"),
            )
            # B-6 — filter_applied가 true가 아니면 C-1을 호출하지 않고 즉시 중단
            if state.get("filter_applied") is not True:
                raise LunchpickError("FILTER_NOT_APPLIED", "S-R9 filter_applied 확인 실패")
            if not state.get("filter_ruleset_version"):
                raise LunchpickError("FILTER_NOT_APPLIED", "S-R9 ruleset_version 확인 실패")
            # B-7 후보 0건 — 추천을 만들지 않고 안내로 착지함
            if state.get("no_candidate"):
                raise LunchpickError("NO_CANDIDATE", "하드필터 후 후보가 0건임")
            return {}

    # ── S-R10 근거·스코어 생성 (C-1) + L-2/L-3 폴백 ─────────────────────────
    async def s_r10_generate(state: RecommendState) -> dict[str, Any]:
        async with span(
            "O-1", "S-R10", state["trace_id"],
            span_name=f"chat {rt.settings.llm_model}",
        ) as attrs:
            override = sr10_override_ms()
            attrs.update(
                filter_applied=state.get("filter_applied"),
                filter_ruleset_version=state.get("filter_ruleset_version"),
                # 설계값(1,200ms)을 덮어썼으면 그 사실을 기록에 남김 —
                # ① Q-1 p95 3초 판정이 이 값에 걸려 있으므로 숨기지 않음
                sr10_timeout_ms=int(timeout_sec("S-R10") * 1000),
                sr10_design_ms=SR["S-R10"].timeout_ms,
                sr10_overridden=override is not None,
            )
            try:
                out = await asyncio.wait_for(
                    a2.generate_picks(
                        rt.reason,
                        candidates=state["candidates"],
                        filter_applied=state["filter_applied"],
                        filter_ruleset_version=state["filter_ruleset_version"],
                        context_tags=state["context_tags"],
                        preference_codes=state.get("preference_codes") or [],
                        recent_category_codes=state.get("recent_category_codes") or [],
                        weather_code=state.get("weather_code", "UNKNOWN"),
                        weekday_code=state["weekday_code"],
                        daypart_code=state["daypart_code"],
                        coldstart=bool(state.get("coldstart")),
                        timeout_sec=timeout_sec("S-R10"),
                    ),
                    timeout=timeout_sec("S-R10"),
                )
                attrs.update(
                    model=out.model,
                    input_tokens=out.input_tokens,
                    output_tokens=out.output_tokens,
                    llm_call_count_per_request=out.llm_calls,
                    path_fallback_used=False,
                )
                return {
                    "picks": out.picks,
                    "generation_status": out.generation_status,
                    "llm_call_count": state.get("llm_call_count", 0) + out.llm_calls,
                    "fallback_reason": None,
                }
            except LunchpickError as exc:
                if exc.code == "FILTER_NOT_APPLIED":
                    raise  # 안전 요건 위반은 폴백하지 않고 중단함
                return _fallback(state, exc.code, attrs)
            except (TimeoutError, asyncio.TimeoutError):
                return _fallback(state, "REASON_GEN_FAIL", attrs, note="timeout")
            except Exception as exc:  # noqa: BLE001
                return _fallback(state, "REASON_GEN_FAIL", attrs, note=type(exc).__name__)

    def _fallback(
        state: RecommendState, reason: str, attrs: dict[str, Any], note: str = ""
    ) -> dict[str, Any]:
        """L-2 경로 폴백 — 기본 추천 이유(거리·평점)로 대체하고 추천을 살림.

        타임아웃을 **소진한 뒤** 도는 경로이므로 조립 시간 150ms가 더해짐(D-2).
        1 ~ 2판이 "폴백은 더 빨라짐"이라 적었던 것은 틀렸고 L-3만 그러함.
        """
        out = a2.build_fallback_picks(state["candidates"], reason=reason)
        attrs.update(path_fallback_used=True, fallback_reason=reason, fallback_note=note)
        log.warning("L-2 경로 폴백 발동 reason=%s note=%s", reason, note)
        return {
            "picks": out.picks,
            "generation_status": out.generation_status,
            "llm_call_count": state.get("llm_call_count", 0),
            "fallback_reason": reason,
        }

    # ── S-R11 확신 스코어 임계값 검증 (B-5) ─────────────────────────────────
    async def s_r11_threshold(state: RecommendState) -> dict[str, Any]:
        async with span("O-3", "S-R11", state["trace_id"], span_name="invoke_agent A-2") as attrs:
            kept, dropped = checks.block_low_confidence(
                state["picks"], threshold=rt.settings.confidence_threshold
            )
            attrs.update(score_blocked_count=dropped, threshold=rt.settings.confidence_threshold)

            if not kept:
                # 전량 미달 → 안전망 경로로 전환(⑥ B-5 대체 처리)
                out = a2.build_fallback_picks(state["candidates"], reason="LOW_CONFIDENCE")
                attrs.update(topped_up=len(out.picks))
                return {
                    "picks": out.picks,
                    "generation_status": out.generation_status,
                    "fallback_reason": state.get("fallback_reason") or "LOW_CONFIDENCE",
                }

            # ⑥ B-5 대체 처리 — "남은 후보로 3건 채움".
            # 임계값에 걸려 3건 밑으로 내려간 것을 그대로 두면 ⑥ M-Q7
            # `후보 3개 채움`이 깨짐(콜드스타트는 확신 스코어가 낮게 나와
            # 실제로 자주 걸림). 차단은 유지하고 **모자란 만큼만** 채움.
            if len(kept) < 3:
                used = {p["restaurant_id"] for p in kept}
                spare = [c for c in state["candidates"] if c["restaurant_id"] not in used]
                filler = a2.build_fallback_picks(spare[: 3 - len(kept)], reason="LOW_CONFIDENCE")
                kept = kept + filler.picks
                attrs.update(topped_up=len(filler.picks))
            return {"picks": kept[:3]}

    # ── S-R12 추천 이력·근거·태그 + 원시 컨텍스트 저장 (D-16) ────────────────
    async def s_r12_persist(state: RecommendState) -> dict[str, Any]:
        async with span("O-3", "S-R12", state["trace_id"], span_name="invoke_agent A-2") as attrs:
            import json

            rec_id = f"RC-{uuid.uuid4().hex[:12]}"
            raw_context = {
                # D-16 — 출력 태그를 **실제 입력값**과 대조하려면 원본이 남아야 함.
                # 태그끼리만 비교하면 A-1이 태그를 잘못 붙인 오류가 안 잡힘
                "weather_code": state.get("weather_code"),
                "weekday_code": state.get("weekday_code"),
                "daypart_code": state.get("daypart_code"),
                "preference_codes": state.get("preference_codes"),
                "recent_category_codes": state.get("recent_category_codes"),
                "coldstart": state.get("coldstart"),
                "context_tags": state.get("context_tags"),
            }
            await db.execute(
                "rw",
                """
                INSERT INTO recommendation
                  (recommendation_id, member_ref, filter_applied, filter_ruleset_version,
                   excluded_count, coldstart, generation_status, fallback_reason,
                   llm_call_count, raw_context)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
                """,
                rec_id,
                state["member_ref"],
                state["filter_applied"],
                state["filter_ruleset_version"],
                state.get("excluded_count", 0),
                bool(state.get("coldstart")),
                state.get("generation_status", ""),
                state.get("fallback_reason"),
                state.get("llm_call_count", 0),
                json.dumps(raw_context, ensure_ascii=False),
            )
            for rank, pick in enumerate(state["picks"]):
                await db.execute(
                    "rw",
                    """
                    INSERT INTO recommendation_item
                      (recommendation_id, rank, restaurant_id, reason_text, confidence, context_tags)
                    VALUES ($1,$2,$3,$4,$5,$6)
                    """,
                    rec_id,
                    rank,
                    pick["restaurant_id"],
                    pick["reason_text"],
                    float(pick["confidence"]),
                    list(pick.get("context_tags") or []),
                )
            attrs.update(recommendation_id=rec_id, item_count=len(state["picks"]))
            return {"recommendation_id": rec_id}

    graph = StateGraph(RecommendState)
    graph.add_node("S-R2", s_r2_consent)
    graph.add_node("S-R3", s_r3_profile)
    graph.add_node("S-R4", s_r4_history)
    graph.add_node("S-R5", s_r5_radius)
    graph.add_node("S-R6", s_r6_weather)
    graph.add_node("S-R7", s_r7_lexicon)
    graph.add_node("S-R8", s_r8_filter)
    graph.add_node("S-R9", s_r9_gate)
    graph.add_node("S-R10", s_r10_generate)
    graph.add_node("S-R11", s_r11_threshold)
    graph.add_node("S-R12", s_r12_persist)

    graph.add_edge(START, "S-R2")
    graph.add_edge("S-R2", "S-R3")
    graph.add_edge("S-R3", "S-R4")
    # 병렬 구간 — 서로 결과를 쓰지 않음(④ 3-1절 par 블록)
    graph.add_edge("S-R4", "S-R5")
    graph.add_edge("S-R4", "S-R6")
    graph.add_edge("S-R5", "S-R7")
    graph.add_edge("S-R6", "S-R7")
    # 고정 간선 — 순서가 곧 안전 요건임(④ 5-2절)
    graph.add_edge("S-R7", "S-R8")
    graph.add_edge("S-R8", "S-R9")
    graph.add_edge("S-R9", "S-R10")
    graph.add_edge("S-R10", "S-R11")
    graph.add_edge("S-R11", "S-R12")
    graph.add_edge("S-R12", END)
    return graph.compile()


def initial_state(
    *,
    member_ref: str,
    lat: float,
    lng: float,
    at: datetime,
    manual_area_code: str | None,
    reject_history: list[str],
    refresh_count: int,
    trace_id: str,
) -> RecommendState:
    return {
        "member_ref": member_ref,
        "geo_point": {"lat": lat, "lng": lng},
        "at": at,
        "manual_area_code": manual_area_code,
        "trace_id": trace_id,
        "reject_history": list(reject_history),
        "refresh_count": refresh_count,
        "retry_count_by_layer": {},
        "llm_call_count": 0,
    }
