"""I-2 `lp-recommend` — ② 4절 FIL + AGT + HIS 세 단계를 담은 배포 단위.

⑦ 2절 I-2: 3초 예산 때문에 홉을 늘리지 않으려고 **묶음**이고, 피크
12 ~ 13시 부하가 이 경로에만 몰려 독립 스케일링이 필요해 **쪼갬**임.
포트 8080(클러스터 내부만) · `/health` 필수 · 외부 인터넷 노출 **안 함**(⑦ 3절).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from lp_common import db
from lp_common.budget import (
    SR,
    SR10_MEASUREMENT_NOTE,
    SR_TOTAL_BUDGET_MS,
    llm_call_cap,
    sr10_override_ms,
    sr_p95_total_ms,
    sr_worst_total_ms,
)
from lp_common.config import get_settings
from lp_common.errors import REASON_CODES, LunchpickError
from lp_common.observability import setup_logging, span, write_span, SpanRecord
from lp_common.output_check import check_recommendation_payload

from .agents import a2_reason_gen as a2
from .connectors.c6_push import PushConnector
from .graph.recommend_graph import RecommendRuntime, build_graph, initial_state

log = logging.getLogger("lp.recommend")
KST = timezone(timedelta(hours=9))
settings = get_settings("lp-recommend")
runtime: RecommendRuntime | None = None
graph = None
push = PushConnector(mode=settings.push_mode)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runtime, graph
    setup_logging("lp-recommend")
    # I-2가 실제로 쓰는 계정만 엶: DB 조회는 읽기 전용, 이력 쓰기는 rw, 관측은 obs
    await db.init_pools(settings, roles=("ro", "rw", "obs"))
    runtime = RecommendRuntime(settings)
    graph = build_graph(runtime)
    log.info(
        "예산 점검 — p95 합계 %dms / 최악값 %dms / 총 예산 %dms",
        sr_p95_total_ms(),
        sr_worst_total_ms(),
        SR_TOTAL_BUDGET_MS,
    )
    override = sr10_override_ms()
    if override:
        # 설계값을 덮어쓴 상태로 도는 것을 조용히 넘기지 않음
        adjusted = sr_p95_total_ms() - SR["S-R10"].p95_ms + override
        log.warning(
            "S-R10 타임아웃을 설계값 %dms → %dms로 덮어씀. "
            "이 상태의 p95 합계는 약 %dms이며 ① Q-1 `p95 3초`가 성립하지 않음. %s",
            SR["S-R10"].timeout_ms, override, adjusted, SR10_MEASUREMENT_NOTE,
        )
    yield
    await db.close_pools()


app = FastAPI(title="런치픽 추천·이력 서비스 (I-2)", lifespan=lifespan)


# ══════════════════════════════════════════════════════════════════════════
# 요청·응답 모델 — ④ 11절 최종 출력 형식
# ══════════════════════════════════════════════════════════════════════════
class RecommendRequest(BaseModel):
    member_ref: str
    lat: float | None = None
    lng: float | None = None
    manual_area_code: str | None = None
    at: datetime | None = None
    reject_history: list[str] = Field(default_factory=list)
    refresh_count: int = 0


class HealthOut(BaseModel):
    status: str
    service: str
    llm_mode: str
    budget_p95_ms: int
    budget_worst_ms: int


@app.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    """⑦ 3절 — 모든 런타임 이미지에 `/health` 필수."""
    return HealthOut(
        status="ok",
        service="lp-recommend",
        llm_mode=settings.llm_mode,
        budget_p95_ms=sr_p95_total_ms(),
        budget_worst_ms=sr_worst_total_ms(),
    )


# ══════════════════════════════════════════════════════════════════════════
# S-R 동기 요청 — 오늘의 추천 조회
# ══════════════════════════════════════════════════════════════════════════
@app.post("/v1/recommendations")
async def create_recommendation(
    req: RecommendRequest, x_trace_id: str | None = Header(default=None)
) -> dict[str, Any]:
    """`S-R1` ~ `S-R13`. 총 예산 3,000ms(① 4절 Q-1)."""
    return await _run_recommendation(req, x_trace_id)


async def _run_recommendation(
    req: RecommendRequest, x_trace_id: str | None = None
) -> dict[str, Any]:
    """경로 본문. L-1·L-2 루프가 **핸들러가 아니라 이 함수를** 다시 부름.

    핸들러를 직접 부르면 FastAPI의 `Header(...)` 기본값 객체가 그대로 인자로
    들어가 직렬화에서 터짐. 루프 재실행은 같은 계약을 다시 밟는 것이지
    HTTP 요청을 다시 만드는 것이 아님(③ 3절 J-6 흡수 판정).
    """
    trace_id = x_trace_id or f"T-{uuid.uuid4().hex[:12]}"
    started = time.perf_counter()
    at = req.at or datetime.now(KST)

    # ⑥ G-3 — 요청당 모델 호출 상한. L-2 상한에서 파생됨
    cap = llm_call_cap(settings.max_refresh_iter)
    if req.refresh_count > settings.max_refresh_iter:
        # 상한 소진 → ④ 10절 L-2 착지 노드(안전 종료)
        return _safe_landing(trace_id, "NO_CANDIDATE", started)

    if req.lat is None or req.lng is None:
        if not req.manual_area_code:
            raise HTTPException(
                status_code=400,
                detail={"reason_code": "LOCATION_UNKNOWN",
                        "message": REASON_CODES["LOCATION_UNKNOWN"].user_message},
            )
        from .connectors.c3_weather import _REGION_CENTER

        center = _REGION_CENTER.get(req.manual_area_code)
        if center is None:
            raise HTTPException(status_code=400, detail={"reason_code": "LOCATION_UNKNOWN"})
        lat, lng = center
    else:
        lat, lng = req.lat, req.lng

    state = initial_state(
        member_ref=req.member_ref,
        lat=lat,
        lng=lng,
        at=at,
        manual_area_code=req.manual_area_code,
        reject_history=req.reject_history,
        refresh_count=req.refresh_count,
        trace_id=trace_id,
    )

    assert graph is not None
    try:
        result = await graph.ainvoke(state)
    except LunchpickError as exc:
        # L-3 캐시 폴백 — 외부 API 오류·지연 시 캐시된 이전 추천을 표시함.
        # `S-R10` ~ `S-R12`가 빠져 예산 안으로 들어옴(④ 9-1절 폴백 표)
        if exc.code in ("EXTERNAL_API_ERROR",):
            cached = await _cache_fallback(req.member_ref, trace_id, started)
            if cached is not None:
                return cached
        return _error_landing(exc, trace_id, started)
    except Exception as exc:  # noqa: BLE001
        log.exception("추천 경로 미분류 오류")
        await write_span(
            SpanRecord(
                point="O-5", span_name="error", step="S-R", trace_id=trace_id,
                is_error=True, attributes={"error_type": type(exc).__name__},
            )
        )
        raise HTTPException(status_code=500, detail={"reason_code": "REASON_GEN_FAIL"}) from exc

    payload = await _render_cards(result, trace_id, started, cap)
    return payload


async def _render_cards(
    result: dict[str, Any], trace_id: str, started: float, cap: int
) -> dict[str, Any]:
    """`S-R13` 추천 카드 3건 제시 + ⑥ 8절 출력측 검사."""
    by_id = {c["restaurant_id"]: c for c in result.get("candidates", [])}
    items = []
    for pick in result.get("picks", []):
        cand = by_id.get(pick["restaurant_id"], {})
        items.append(
            {
                "restaurant_id": pick["restaurant_id"],
                "restaurant_name": cand.get("display_name", ""),
                "signature_menu": cand.get("signature_menu", ""),
                "reason_text": pick["reason_text"],
                "confidence": round(float(pick["confidence"]), 2),
                "distance_m": int(cand.get("distance_m", 0)),
                "walk_min": int(cand.get("walk_minutes", 0)),
                "evidence": list(pick.get("context_tags") or []),
            }
        )

    payload: dict[str, Any] = {
        "recommendation_id": result.get("recommendation_id"),
        "items": items,
        "coldstart_notice": (
            "아직 취향을 학습 중이에요" if result.get("coldstart") else None
        ),
        "learning_notice": result.get("learning_notice"),
        "fallback_reason": result.get("fallback_reason"),
        "trace_id": trace_id,
    }

    # ⑥ 8절 L-1 ~ L-4 — 추천 카드 반환 직전 검사(⑥ G-8 실행 자리)
    default_reasons = {
        c["restaurant_id"]: f"걸어서 {c['walk_minutes']}분 거리라 다녀오기 좋아요"
        for c in result.get("candidates", [])
    }
    checked = check_recommendation_payload(payload, default_reason_for=default_reasons)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    await write_span(
        SpanRecord(
            point="O-7",
            span_name="S-R13",
            step="S-R13",
            trace_id=trace_id,
            latency_ms=elapsed_ms,
            attributes={
                "reject_count": len(result.get("reject_history") or []),
                "refresh_count": result.get("refresh_count", 0),
                "llm_call_count_per_request": result.get("llm_call_count", 0),
                "llm_call_cap": cap,
                "landing_node": result.get("fallback_reason") or "normal",
                "output_violations": checked.violations,
                "total_latency_ms": elapsed_ms,
                "budget_ms": SR_TOTAL_BUDGET_MS,
                "within_budget": elapsed_ms <= SR_TOTAL_BUDGET_MS,
                "excluded_count": result.get("excluded_count", 0),
                "block_stats": result.get("block_stats", {}),
            },
        )
    )
    out = checked.payload
    out["latency_ms"] = elapsed_ms
    out["output_violations"] = checked.violations
    return out


async def _cache_fallback(member_ref: str, trace_id: str, started: float) -> dict[str, Any] | None:
    """L-3 캐시 폴백 — 캐시된 이전 추천을 그대로 표시함.

    `S-R10` ~ `S-R12`가 실제로 빠지므로 이 경로만 "더 빨라짐"이 맞음(④ 9-3절).
    """
    row = await db.fetchrow(
        "ro",
        """
        SELECT r.recommendation_id
        FROM recommendation r
        WHERE r.member_ref = $1 AND r.generation_status <> 'SEEDED'
        ORDER BY r.created_at DESC LIMIT 1
        """,
        member_ref,
    )
    if row is None:
        return None
    items = await db.fetch(
        "ro",
        """
        SELECT i.restaurant_id, i.reason_text, i.confidence, i.context_tags,
               c.display_name, c.signature_menu, c.walk_minutes
        FROM recommendation_item i
        LEFT JOIN restaurant_cache c USING (restaurant_id)
        WHERE i.recommendation_id = $1 ORDER BY i.rank
        """,
        row["recommendation_id"],
        limit_guard=10,
    )
    payload = {
        "recommendation_id": row["recommendation_id"],
        "items": [
            {
                "restaurant_id": i["restaurant_id"],
                "restaurant_name": i["display_name"] or "",
                "signature_menu": i["signature_menu"] or "",
                "reason_text": i["reason_text"],
                "confidence": float(i["confidence"]),
                "distance_m": 0,
                "walk_min": int(i["walk_minutes"] or 0),
                "evidence": list(i["context_tags"] or []),
            }
            for i in items
        ],
        "coldstart_notice": None,
        "learning_notice": None,
        # `US:UFR-REC-010#처리결과` "최신 추천을 불러오고 있어요"
        "fallback_reason": "EXTERNAL_API_ERROR",
        "trace_id": trace_id,
    }
    checked = check_recommendation_payload(payload)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await write_span(
        SpanRecord(
            point="O-6", span_name="L-3", step="S-R13", trace_id=trace_id,
            latency_ms=elapsed_ms,
            attributes={"cache_fallback_used": True, "total_latency_ms": elapsed_ms},
        )
    )
    out = checked.payload
    out["latency_ms"] = elapsed_ms
    return out


def _safe_landing(trace_id: str, code: str, started: float) -> dict[str, Any]:
    """④ 10절 착지 노드 — 안전 종료. 상한 소진 시 안내로 끝냄."""
    return {
        "recommendation_id": None,
        "items": [],
        "coldstart_notice": None,
        "learning_notice": None,
        "fallback_reason": code,
        "message": REASON_CODES[code].user_message,
        "trace_id": trace_id,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


def _error_landing(exc: LunchpickError, trace_id: str, started: float) -> dict[str, Any]:
    payload = _safe_landing(trace_id, exc.code, started)
    payload["reason_code"] = exc.code
    payload["message"] = exc.user_message
    if exc.code == "CONSENT_REQUIRED":
        payload["manual_location_required"] = True
    return payload


# ══════════════════════════════════════════════════════════════════════════
# L-1 개별 거절 → 대체 추천 / L-2 전체 거절 → 새 3건 (④ 10절)
# ══════════════════════════════════════════════════════════════════════════
class RejectRequest(BaseModel):
    member_ref: str
    reject_history: list[str]
    refresh_count: int = 0
    lat: float | None = None
    lng: float | None = None
    manual_area_code: str | None = None
    # 루프 재실행도 **같은 요청 시각**으로 밟아야 함. 이 칸이 없으면 서버가
    # 현재 시각으로 다시 계산해 영업 시간 필터(B-3)가 다른 결과를 냄 —
    # 거절 한 번에 후보가 통째로 사라지는 형태로 드러났음
    at: datetime | None = None
    reason_code: str | None = None


@app.post("/v1/recommendations/reject")
async def reject_and_replace(req: RejectRequest) -> dict[str, Any]:
    """L-1 — 거절된 식당을 뺀 뒤 차순위 1건 제시.

    상한은 `[확인필요: 개별 거절 반복 상한]`(원문 부재)이며 환경변수로 둠.
    소진 시 착지: "주변에 더 추천할 곳이 없어요. 거리를 넓혀볼까요?"
    """
    if len(req.reject_history) > settings.max_reject_iter:
        return _safe_landing(f"T-{uuid.uuid4().hex[:12]}", "NO_CANDIDATE", time.perf_counter())
    return await _run_recommendation(
        RecommendRequest(
            member_ref=req.member_ref,
            lat=req.lat,
            lng=req.lng,
            manual_area_code=req.manual_area_code,
            at=req.at,
            reject_history=req.reject_history,
            refresh_count=req.refresh_count,
        )
    )


@app.post("/v1/recommendations/refresh")
async def refresh_all(req: RejectRequest) -> dict[str, Any]:
    """L-2 — 3건 전부 거절 시 새 3건 생성. **반복 1회마다 C-1 호출이 1건 늘어남.**

    이것은 시간 예산이 아니라 **비용 예산**을 깎는 경로임(④ 10절).
    상한이 열려 있으면 요청당 단가에 천장이 없어지므로 ⑥ G-3이 상한을 걺.
    """
    return await _run_recommendation(
        RecommendRequest(
            member_ref=req.member_ref,
            lat=req.lat,
            lng=req.lng,
            manual_area_code=req.manual_area_code,
            at=req.at,
            reject_history=req.reject_history,
            refresh_count=req.refresh_count + 1,
        )
    )


# ══════════════════════════════════════════════════════════════════════════
# S-E 이벤트 — 식사 기록·피드백·리마인더 (④ 3-3절)
# ══════════════════════════════════════════════════════════════════════════
class MealRequest(BaseModel):
    member_ref: str
    restaurant_id: str
    recommendation_id: str | None = None
    eaten_at: datetime | None = None


@app.post("/v1/meals")
async def record_meal(req: MealRequest) -> dict[str, Any]:
    """`S-E1` 원탭 기록 · `S-E2` 중복 기록·식사 시간대 검증."""
    trace_id = f"T-{uuid.uuid4().hex[:12]}"
    eaten = req.eaten_at or datetime.now(KST)
    async with span("O-3", "S-E2", trace_id, span_name="invoke_agent HIS") as attrs:
        cand = await db.fetchrow(
            "ro",
            "SELECT category_code FROM restaurant_cache WHERE restaurant_id = $1",
            req.restaurant_id,
        )
        if cand is None:
            raise HTTPException(status_code=404, detail={"reason_code": "NO_CANDIDATE"})
        dup = await db.fetchrow(
            "ro",
            "SELECT meal_id FROM meal_record WHERE member_ref=$1 AND restaurant_id=$2 "
            "AND eaten_at BETWEEN $3 AND $4",
            req.member_ref,
            req.restaurant_id,
            eaten - timedelta(hours=3),
            eaten + timedelta(hours=3),
        )
        if dup is not None:
            attrs.update(duplicate=True)
            return {
                "reason_code": "DUPLICATE_RECORD",
                "message": REASON_CODES["DUPLICATE_RECORD"].user_message,
                "meal_id": dup["meal_id"],
            }
        meal_id = f"ML-{uuid.uuid4().hex[:10]}"
        await db.execute(
            "rw",
            "INSERT INTO meal_record (meal_id, member_ref, restaurant_id, category_code, eaten_at) "
            "VALUES ($1,$2,$3,$4,$5)",
            meal_id,
            req.member_ref,
            req.restaurant_id,
            cand["category_code"],
            eaten,
        )
        if req.recommendation_id:
            await db.execute(
                "rw",
                "UPDATE recommendation_item SET accepted = TRUE, responded_at = now() "
                "WHERE recommendation_id = $1 AND restaurant_id = $2",
                req.recommendation_id,
                req.restaurant_id,
            )
        attrs.update(meal_id=meal_id)
        # S-E3 피드백 요청 표시
        return {"meal_id": meal_id, "feedback_prompt": "오늘 식사 어떠셨어요?"}


class FeedbackRequest(BaseModel):
    meal_id: str
    member_ref: str
    liked: bool | None = None  # None = 스킵 → 중립 적용(FEEDBACK_SKIP)
    keyword_codes: list[str] = Field(default_factory=list)


@app.post("/v1/feedback")
async def submit_feedback(req: FeedbackRequest) -> dict[str, Any]:
    """`S-E4` 피드백 제출·유효성 검증 · `S-E5` 스냅샷 적재.

    **A-3을 깨우지 않음**(J-9). 저장소에 적재하고 A-3이 03:00에 `S-B2`로 읽음.
    두 경로의 예산이 섞이지 않는 이유가 이것임.
    """
    trace_id = f"T-{uuid.uuid4().hex[:12]}"
    async with span("O-3", "S-E5", trace_id, span_name="invoke_agent HIS") as attrs:
        meal = await db.fetchrow(
            "ro", "SELECT category_code FROM meal_record WHERE meal_id = $1", req.meal_id
        )
        if meal is None:
            raise HTTPException(status_code=404, detail={"reason_code": "DUPLICATE_RECORD"})
        await db.execute(
            "rw",
            """
            INSERT INTO feedback (feedback_id, meal_id, member_ref, category_code,
                                  liked, keyword_codes, context_snapshot)
            VALUES ($1,$2,$3,$4,$5,$6,'{}'::jsonb)
            ON CONFLICT DO NOTHING
            """,
            f"FB-{uuid.uuid4().hex[:10]}",
            req.meal_id,
            req.member_ref,
            meal["category_code"],
            req.liked,
            req.keyword_codes,
        )
        attrs.update(skipped=req.liked is None)
        if req.liked is None:
            return {"reason_code": "FEEDBACK_SKIP", "applied": "NEUTRAL"}
        return {"applied": "OK"}


@app.post("/v1/reminders/run")
async def run_reminders() -> dict[str, Any]:
    """`S-E6` 미응답 1시간 경과 리마인더 **1회만** 발송(재시도 0회).

    ⑥ 11절 A-8: 사람 승인을 붙이면 1시간 후 리마인더가 성립하지 않으므로
    자동 실행하되 발송 1건·재시도 0회의 제한 장치로 대체함.
    """
    trace_id = f"T-{uuid.uuid4().hex[:12]}"
    rows = await db.fetch(
        "ro",
        """
        SELECT m.meal_id, m.member_ref
        FROM meal_record m
        LEFT JOIN feedback f ON f.meal_id = m.meal_id
        WHERE f.feedback_id IS NULL
          AND m.created_at < now() - INTERVAL '1 hour'
          AND m.created_at > now() - INTERVAL '1 day'
        """,
        limit_guard=200,
    )
    sent, violations_total = 0, []
    for row in rows:
        result, violations = await push.send(
            f"tok-{row['member_ref']}", "점심 어떠셨어요? 한 번만 눌러 알려주세요"
        )
        violations_total.extend(violations)
        if result == "SENT":
            sent += 1
    await write_span(
        SpanRecord(
            point="O-2", span_name="execute_tool C-6", step="S-E6", trace_id=trace_id,
            attributes={"sent": sent, "output_violations": violations_total},
        )
    )
    return {"sent": sent, "output_violations": violations_total}


# ══════════════════════════════════════════════════════════════════════════
# K-3 취향 인사이트 — 고정 집계 쿼리(읽기 전용). NL2SQL 미채택(⑤ 2절)
# ══════════════════════════════════════════════════════════════════════════
@app.get("/v1/insights/{member_ref}")
async def insights(member_ref: str) -> dict[str, Any]:
    """K-3 — 화면이 던지는 질문이 3종으로 고정이라 SQL 생성이 불필요함(⑤ 2절).

    등급별 조회 범위: 무료 30일 / 프리미엄 무제한(`BM:2-가격계층`).
    **물리 삭제를 걸지 않고 조회 시 범위 제한으로 처리함**(⑦ 5-3 문제 2).
    """
    plan = await db.fetchrow("ro", "SELECT plan_type FROM member WHERE member_ref=$1", member_ref)
    if plan is None:
        raise HTTPException(status_code=404, detail={"reason_code": "AUTH_FAIL"})
    window_days = 30 if plan["plan_type"] == "FREE" else 3650

    top = await db.fetch(
        "ro",
        """
        SELECT category_code, count(*) AS cnt FROM meal_record
        WHERE member_ref=$1 AND eaten_at >= now() - ($2 || ' days')::interval
        GROUP BY category_code ORDER BY cnt DESC LIMIT 5
        """,
        member_ref,
        str(window_days),
        limit_guard=5,
    )
    total = await db.fetchrow(
        "ro",
        "SELECT count(*) AS n FROM meal_record WHERE member_ref=$1 "
        "AND eaten_at >= now() - ($2 || ' days')::interval",
        member_ref,
        str(window_days),
    )
    if int(total["n"]) < 10:
        # ⑤ 10절 — 추측한 인사이트를 만들지 않고 없다고 말함
        return {
            "available": False,
            "message": "10끼 이상 기록하면 취향 인사이트가 열려요!",
            "recorded": int(total["n"]),
        }
    satisfy = await db.fetchrow(
        "ro",
        """
        SELECT count(*) FILTER (WHERE liked) AS liked,
               count(*) FILTER (WHERE liked IS NOT NULL) AS answered
        FROM feedback WHERE member_ref=$1
        """,
        member_ref,
    )
    answered = int(satisfy["answered"] or 0)
    return {
        "available": True,
        "plan_type": plan["plan_type"],
        "window_days": window_days,
        "top_categories": [{"category_code": r["category_code"], "count": int(r["cnt"])} for r in top],
        "satisfy_rate": round(int(satisfy["liked"] or 0) / answered, 3) if answered else None,
        "recorded": int(total["n"]),
    }
