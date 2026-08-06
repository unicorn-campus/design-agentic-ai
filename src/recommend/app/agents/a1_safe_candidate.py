"""A-1 「안전 후보 선별」 — ③ 4-1절 계약 7칸.

사용 모델: **모델 미사용(결정론적 실행)**
  배정 이유 — 하드필터 위반 0건은 확률적 모델로 보장 불가하므로 LLM을 쓰지
  않음. 모델 단가·지연이 0이므로 Q-1 3초 예산을 깎지 않음(③ 4-1).

성공 기준(③ 4-1):
  · 알레르겐 포함 식당의 후보 잔존 0건
  · 최근 3일 내 동일 식당 후보 0건
  · 필터 판정이 불확실한 식당을 뺀 기록 100% 저장
  · 출력 `filter_ruleset_version` 값이 비지 않음

**중단 조건 ②의 착지(③ 4-1 아래 표)** — 알레르겐 원천이 아예 없으면 반경 내
식당이 모두 빠져 `no_candidate`로 중단함. 이때 성공 기준은 통과하면서
추천이 0개가 되므로, 그 둘을 가르는 신호로 `excluded_count`와
`no_candidate`를 씀. 이것이 이번 설계에서 가장 무거운 지점임.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from lp_common import db
from lp_common.codes import (
    FILTER_RULESET_VERSION,
    daypart_of,
    resolve_blocked_ingredients,
)
from lp_common.errors import LunchpickError

log = logging.getLogger("lp.a1")

COLDSTART_FEEDBACK_THRESHOLD = 5  # `US:UFR-REC-030` 누적 피드백 5건 미만
RECENT_HISTORY_DAYS = 7  # A-1 입력: 최근 7일 카테고리 이력
REPEAT_BLOCK_DAYS = 3  # ⑥ B-4: 최근 3일 내 동일 식당 제외
SEARCH_RADIUS_M = 500  # `BM:6-GTM#Launch` 반경 500m


@dataclass
class A1Output:
    """③ 4-1절 출력 형식. `공유` 표시 키 6종이 ④ 상태 스키마의 씨앗임."""

    candidates: list[dict[str, Any]] = field(default_factory=list)  # 공유
    filter_applied: bool = False  # 공유
    filter_ruleset_version: str = ""  # 공유
    excluded_count: int = 0
    context_tags: list[str] = field(default_factory=list)  # 공유
    coldstart: bool = False  # 공유
    weekday_code: str = ""  # 공유 (J-8 추가)
    prior_source: str | None = None
    # 아래는 A-1 출력 키가 아니라 ④ 상태·⑥ 관측으로 나가는 부속 값임
    daypart_code: str = ""
    preference_codes: list[str] = field(default_factory=list)
    recent_category_codes: list[str] = field(default_factory=list)
    block_stats: dict[str, int] = field(default_factory=dict)
    unresolved_terms: list[str] = field(default_factory=list)
    no_candidate: bool = False


async def load_member_context(member_ref: str) -> dict[str, Any]:
    """`S-R3` 회원·취향·식이제한 조회.

    F-1(알레르기 항목명)은 **A-1만 읽음**. A-2·A-3은 제외임(⑤ 8절 F-1).
    """
    row = await db.fetchrow(
        "ro",
        """
        SELECT m.member_ref, m.region_code, m.job_cluster_code, m.plan_type,
               p.category_scores, p.feedback_count,
               d.allergen_names, d.diet_types
        FROM member m
        JOIN preference_profile p USING (member_ref)
        JOIN dietary_restriction d USING (member_ref)
        WHERE m.member_ref = $1
        """,
        member_ref,
    )
    if row is None:
        raise LunchpickError("AUTH_FAIL", "회원을 찾지 못함")
    return dict(row)


async def load_history(member_ref: str, at: datetime) -> dict[str, Any]:
    """`S-R4` 최근 7일 식사 이력 · 최근 3일 추천 식당 조회.

    식당명·메뉴명 원문 이력은 읽지 않음 — **카테고리 코드만**(⑤ 8절 F-4).
    """
    recent_categories = await db.fetch(
        "ro",
        """
        SELECT DISTINCT category_code
        FROM meal_record
        WHERE member_ref = $1 AND eaten_at >= $2
        """,
        member_ref,
        at - timedelta(days=RECENT_HISTORY_DAYS),
        limit_guard=64,
    )
    recent_restaurants = await db.fetch(
        "ro",
        """
        SELECT DISTINCT i.restaurant_id
        FROM recommendation r
        JOIN recommendation_item i USING (recommendation_id)
        WHERE r.member_ref = $1 AND r.created_at >= $2
        """,
        member_ref,
        at - timedelta(days=REPEAT_BLOCK_DAYS),
        limit_guard=200,
    )
    return {
        "recent_category_codes": [r["category_code"] for r in recent_categories],
        "recent_restaurant_ids": {r["restaurant_id"] for r in recent_restaurants},
    }


async def load_radius_candidates(
    region_code: str, lat: float, lng: float, hour: int
) -> list[dict[str, Any]]:
    """`S-R5` 반경 후보 조회 — **식당 캐시(DB4)만 읽고 지도 API를 부르지 않음**(J-6).

    근거 2건: 지도 API 월 50만 원 상한(`BM:3-비용구조#변동비용`)과
    ① G-1 `3초` 예산에서 외부 왕복 1홉 제거(② 4절 판정 J-6).
    """
    # 대략적 반경 필터를 SQL에서 걸고 정확 거리는 파이썬에서 계산함
    delta = SEARCH_RADIUS_M / 111_000 * 1.6
    rows = await db.fetch(
        "ro",
        """
        SELECT restaurant_id, display_name, signature_menu, category_code,
               lat, lng, walk_minutes, rating, business_status,
               open_from_hour, open_to_hour, allergen_codes, collected_at
        FROM restaurant_cache
        WHERE region_code = $1
          AND expired = FALSE
          AND lat BETWEEN $2 AND $3
          AND lng BETWEEN $4 AND $5
        """,
        region_code,
        lat - delta,
        lat + delta,
        lng - delta,
        lng + delta,
        limit_guard=400,
    )
    out = []
    for row in rows:
        distance = _distance_m(lat, lng, row["lat"], row["lng"])
        if distance > SEARCH_RADIUS_M:
            continue
        item = dict(row)
        item["distance_m"] = int(distance)
        out.append(item)
    return out


def apply_hard_filter(
    raw_candidates: list[dict[str, Any]],
    *,
    allergen_names: list[str],
    diet_types: list[str],
    recent_restaurant_ids: set[str],
    hour: int,
    read_allergens: bool,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    """`S-R8` 하드필터. ⑥ 9절 B-1 ~ B-4를 순서대로 적용함.

    **차단이 점수를 이김**(⑥ 9-1절). 여기서 걸러진 식당은 뒤에서 취향 점수가
    아무리 높아도 되살아나지 않음 — 불리언 거름망이지 가중치가 아님.

    Args:
        read_allergens: 민감정보 별도 동의가 확인됐는지. False면 F-1을 읽지
            않았다는 뜻이므로 필터를 걸 수 없음 → 호출 쪽이 중단해야 함.
    """
    if not read_allergens and (allergen_names or diet_types):
        raise LunchpickError(
            "SENSITIVE_CONSENT_REQUIRED",
            "식이제한이 설정된 회원인데 민감정보 별도 동의가 확인되지 않음(③ 중단 조건 ⑤)",
        )

    blocked_ingredients, unresolved = resolve_blocked_ingredients(allergen_names, diet_types)
    stats = {"B-1": 0, "B-2": 0, "B-3": 0, "B-4": 0, "closed_hour": 0}
    survivors: list[dict[str, Any]] = []

    for cand in raw_candidates:
        # B-3 폐업·영업 종료 식당 — 필수
        if cand["business_status"] != "OPEN":
            stats["B-3"] += 1
            continue
        if not (cand["open_from_hour"] <= hour < cand["open_to_hour"]):
            stats["closed_hour"] += 1
            continue

        # B-2 알레르겐 판정 불확실 — **페일세이프. 원천이 없으면 그 식당 전체 제외**
        # `US:UFR-MBR-040#검증요구사항` "필터 적용 불확실 시 해당 식당 전체 제외"
        codes = cand.get("allergen_codes")
        if blocked_ingredients and codes is None:
            stats["B-2"] += 1
            continue

        # B-1 알레르겐 포함 식당 — 필수. 결정론 교집합 판정
        if blocked_ingredients and set(codes or ()) & blocked_ingredients:
            stats["B-1"] += 1
            continue

        # B-4 최근 3일 내 추천된 동일 식당 — 권고
        if cand["restaurant_id"] in recent_restaurant_ids:
            stats["B-4"] += 1
            continue

        survivors.append(cand)

    return survivors, stats, unresolved


def rank_candidates(
    candidates: list[dict[str, Any]],
    *,
    category_scores: dict[str, float],
    recent_category_codes: list[str],
    coldstart: bool,
    prior_scores: dict[str, float] | None,
) -> list[dict[str, Any]]:
    """취향 코드 가중 정렬 — ⑤ 2절 K-1 채택 경로.

    콜드스타트면 개인 벡터가 없는 상태이므로 직군 클러스터 Prior +
    지역 인기(평점)로 대체함(⑤ 2절 K-4 · `US:UFR-REC-030`).
    """
    recent = set(recent_category_codes)
    scores = prior_scores if coldstart else category_scores

    def key(item: dict[str, Any]) -> tuple[float, float]:
        base = float((scores or {}).get(item["category_code"], 0.0))
        # 최근 먹은 종류는 뒤로 — `US:UFR-REC-010#검증요구사항` 반복 방지
        if item["category_code"] in recent:
            base -= 0.4
        # 거리·평점 보정: 가까울수록 · 평점 높을수록 유리
        base += (1.0 - min(item["distance_m"], 500) / 500) * 0.25
        base += (float(item["rating"]) - 3.0) / 10.0
        return (base, float(item["rating"]))

    return sorted(candidates, key=key, reverse=True)


async def load_prior_scores(job_cluster_code: str | None, region_code: str) -> dict[str, float]:
    """콜드스타트용 직군 클러스터 Prior 조회.

    `[확인필요: 직군 데이터 수집 경로]`(③ 8절) — 직군 코드가 없으면 지역
    인기만으로 반쪽 동작함. 그 사실을 `prior_source`로 밖에 알림.
    """
    code = job_cluster_code or "UNKNOWN"
    rows = await db.fetch(
        "ro",
        "SELECT category_code, prior_score FROM job_cluster_prior "
        "WHERE job_cluster_code = $1 AND region_code = $2",
        code,
        region_code,
        limit_guard=64,
    )
    return {r["category_code"]: float(r["prior_score"]) for r in rows}


def build_context_tags(
    *, weather_code: str, recent_category_codes: list[str], coldstart: bool
) -> list[str]:
    """A-1이 확정한 반영 컨텍스트 태그. A-2 출력 태그와 대조되는 기준값임.

    D-16 한계: A-2 성공 기준은 `출력 태그 = 입력 태그`만 보므로 **A-1이 태그를
    잘못 붙인 오류는 잡히지 않음**. 그래서 ④ `S-R12`가 원시 컨텍스트를 함께
    저장하고 ⑥이 그걸로 채점함.
    """
    tags: list[str] = []
    if weather_code in ("RAIN", "SNOW", "COLD", "HOT"):
        tags.append("날씨")
    if recent_category_codes:
        tags.append("이력")
    if not coldstart:
        tags.append("취향")
    tags.extend(["요일", "시간대"])
    return tags


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """평면 근사 거리. 반경 500m 규모에서는 오차가 무시할 수준임."""
    import math

    mean_lat = math.radians((lat1 + lat2) / 2)
    dx = (lng2 - lng1) * 111_320 * math.cos(mean_lat)
    dy = (lat2 - lat1) * 110_540
    return math.hypot(dx, dy)


def weekday_code_of(at: datetime) -> str:
    from lp_common.codes import WEEKDAY_CODES

    return WEEKDAY_CODES[at.weekday()]


def daypart_code_of(at: datetime) -> str:
    return daypart_of(at.hour)
