"""식당 데이터 동기화 워커 — ④ 3-3절 `S-B9` ~ `S-B15`. ⑥ R-2로 신설된 경로.

**`C-2 반경 식당 조회`의 사용 주체가 이 경로임**(J-6 이후 추천 경로는 캐시를
읽고 지도 API를 부르지 않음). 이 경로는 **3초 예산 밖**이며 사용자가 기다리지
않음.

**`S-B11`이 ⑥ G-2의 근본 차단 지점임.** ⑥ 1판은 ④에 적재 단계가 없어 읽기
시점(`S-R5`)에 임시로 걸었으나, 캐시에 이미 들어온 값은 읽기 검사로 지울 수
없음. 적재 **전**에 막는 자리를 ④가 만들었고 여기가 그 구현임.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from lp_common import db
from lp_common.config import Settings
from lp_common.observability import span

from lp_common.guardrails import inspect_external_string, is_fresh

log = logging.getLogger("lp.sync")
KST = timezone(timedelta(hours=9))


async def run(settings: Settings, *, region_code: str | None = None) -> dict[str, Any]:
    """`S-B9` ~ `S-B15`. 주기 갱신 — 주기 값은 ⑤ `[확인필요: 식당 캐시 갱신 주기]`."""
    now = datetime.now(KST)
    trace_id = f"SY-{now.strftime('%Y%m%d%H%M%S')}"
    state: dict[str, Any] = {
        "sync_run_at": now,
        "fetched_restaurants": [],
        "blocked_string_count": 0,
        "expired_count": 0,
        "loaded_count": 0,
        "closed_filtered_count": 0,
        "trace_id": trace_id,
    }

    # ── S-B10 대상 지역 식당 목록 조회 (C-2) ────────────────────────────────
    async with span("O-11", "S-B10", trace_id, span_name="execute_tool C-2") as attrs:
        fetched = await _fetch_places(settings, region_code)
        state["fetched_restaurants"] = fetched
        attrs.update(fetched_count=len(fetched), places_mode=settings.places_mode)

    blocked_examples: list[str] = []
    # ── S-B11 적재 전 내용 검사 → S-B12 폐업 필터 → S-B13 적재 ───────────────
    async with span("O-11", "S-B11", trace_id, span_name="execute_tool gate") as attrs:
        passed: list[dict[str, Any]] = []
        for place in fetched:
            name_clean, name_violations = inspect_external_string(
                str(place.get("display_name", "")), max_len=settings.display_name_max_len
            )
            menu_clean, menu_violations = inspect_external_string(
                str(place.get("signature_menu", "")), max_len=settings.display_name_max_len
            )
            violations = name_violations + menu_violations
            if violations:
                # B-9 — 그 건을 적재하지 않고 차단 기록을 남김
                state["blocked_string_count"] += 1
                blocked_examples.append(
                    f"{place.get('restaurant_id')}:{','.join(sorted(set(violations)))}"
                )
                continue
            place["display_name"] = name_clean
            place["signature_menu"] = menu_clean
            passed.append(place)
        attrs.update(
            blocked_string_count=state["blocked_string_count"],
            blocked_examples=blocked_examples,
            passed_count=len(passed),
        )

    async with span("O-11", "S-B12", trace_id, span_name="execute_tool filter") as attrs:
        # S-B12 폐업·영업 상태 필터 — `ES:규제표#식품위생법`
        open_only = [p for p in passed if p.get("business_status") == "OPEN"]
        state["closed_filtered_count"] = len(passed) - len(open_only)
        attrs.update(closed_filtered_count=state["closed_filtered_count"])

    async with span("O-11", "S-B13", trace_id, span_name="execute_tool cache_load") as attrs:
        for place in open_only:
            await db.execute(
                "rw",
                """
                INSERT INTO restaurant_cache
                  (restaurant_id, display_name, signature_menu, category_code, lat, lng,
                   walk_minutes, rating, business_status, allergen_codes, region_code,
                   source, collected_at, expired)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'C-2',$12,FALSE)
                ON CONFLICT (restaurant_id) DO UPDATE SET
                  display_name = EXCLUDED.display_name,
                  signature_menu = EXCLUDED.signature_menu,
                  business_status = EXCLUDED.business_status,
                  allergen_codes = EXCLUDED.allergen_codes,
                  source = 'C-2',
                  collected_at = EXCLUDED.collected_at,
                  expired = FALSE
                """,
                place["restaurant_id"],
                place["display_name"],
                place["signature_menu"],
                place["category_code"],
                float(place["lat"]),
                float(place["lng"]),
                int(place["walk_minutes"]),
                float(place.get("rating", 0)),
                place["business_status"],
                place.get("ingredients"),
                place.get("region_code", region_code or "SEOUL-GANGNAM"),
                now,  # 출처·수집 시각을 함께 남김(⑥ G-2)
            )
        state["loaded_count"] = len(open_only)
        attrs.update(loaded_count=len(open_only))

    # ── S-B14 신선도 상한 초과 값 만료 ──────────────────────────────────────
    async with span("O-11", "S-B14", trace_id, span_name="execute_tool expire") as attrs:
        cutoff = now - timedelta(seconds=settings.cache_freshness_max_sec)
        result = await db.execute(
            "rw",
            "UPDATE restaurant_cache SET expired = TRUE "
            "WHERE collected_at < $1 AND expired = FALSE",
            cutoff,
        )
        state["expired_count"] = int(result.split()[-1]) if result.startswith("UPDATE") else 0
        oldest = await db.fetchrow(
            "ro", "SELECT min(collected_at) AS oldest FROM restaurant_cache WHERE expired = FALSE"
        )
        oldest_age = (
            int((now - oldest["oldest"]).total_seconds()) if oldest and oldest["oldest"] else 0
        )
        attrs.update(
            expired_count=state["expired_count"],
            cache_max_age_sec=oldest_age,
            freshness_limit_sec=settings.cache_freshness_max_sec,
            # J-6이 만든 새 위험: 캐시 신선도가 곧 폐업 오류의 수명임(⑦ 4-2-1절)
            stale_within_limit=is_fresh(
                oldest["oldest"] if oldest and oldest["oldest"] else now,
                now,
                max_age_sec=settings.cache_freshness_max_sec,
            ),
        )

    log.info(
        "S-B15 동기화 완료 — 조회 %d · 차단 %d · 폐업제외 %d · 적재 %d · 만료 %d",
        len(fetched),
        state["blocked_string_count"],
        state["closed_filtered_count"],
        state["loaded_count"],
        state["expired_count"],
    )
    return state


async def _fetch_places(settings: Settings, region_code: str | None) -> list[dict[str, Any]]:
    """C-2 반경 식당 조회. ⑤ 7절 입력 규격 `lat` · `lng` · `radius_m`.

    로컬 테스트는 `LP_PLACES_MODE=mock`이며 합성 원시 응답 표를 읽음.
    실물 경로는 지도 API 월 50만 원 상한 때문에 호출을 이 1곳으로 모음(⑥ G-4).
    """
    if settings.places_mode != "mock":
        raise NotImplementedError(
            "C-2 실물 경로는 지도 API 쿼터 소모가 있어 로컬 테스트 범위 밖임(⑥ G-4)"
        )
    rows = await db.fetch(
        "ro",
        "SELECT id, region_code, payload FROM raw_place_feed WHERE consumed = FALSE"
        + (" AND region_code = $1" if region_code else ""),
        *( [region_code] if region_code else [] ),
        limit_guard=50,
    )
    places: list[dict[str, Any]] = []
    for row in rows:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        for place in payload:
            place.setdefault("region_code", row["region_code"])
            places.append(place)
        await db.execute("rw", "UPDATE raw_place_feed SET consumed = TRUE WHERE id = $1", row["id"])
    return places
