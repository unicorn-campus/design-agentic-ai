"""④ 7절 상태 스키마 — 필드 23종.

`A03`의 3출처로 위치를 판정함: 요청마다 바뀌는 값은 `Runtime Context`,
단계 간에 흐르는 값은 `State`, 세션을 넘길 값은 `Store`임.
**필드마다 갱신 주체를 1개만 둠.**

병렬 구간(`S-R5` ∥ `S-R6`)은 애초에 서로 다른 필드에 쓰도록 갈라 뒀으므로
겹치는 필드가 없음 — `raw_candidates`(S-R5) / `weather_code`(S-R6).
누적만이 필요한 필드는 루프가 만드는 2개임(`reject_history`·`retry_count_by_layer`).
"""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, Any

from typing_extensions import TypedDict


def _merge_counts(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    """계층별로 분리해 누적함(④ 9-3절 L-1 ~ L-4)."""
    out = dict(left)
    for key, value in right.items():
        out[key] = out.get(key, 0) + value
    return out


class RecommendState(TypedDict, total=False):
    # ── Runtime Context (갱신 주체: API 게이트웨이) ────────────────────────────
    member_ref: str
    geo_point: dict[str, float]  # F-2 — TB-2로 넘어가지 않음
    at: datetime
    manual_area_code: str | None
    trace_id: str

    # ── State — S-R5 단독 ────────────────────────────────────────────────────
    raw_candidates: list[dict[str, Any]]
    # ── State — S-R6 단독 ────────────────────────────────────────────────────
    weather_code: str

    # ── State — A-1 갱신 ─────────────────────────────────────────────────────
    weekday_code: str  # J-8 추가
    daypart_code: str  # J-8 확정
    candidates: list[dict[str, Any]]
    filter_applied: bool
    filter_ruleset_version: str
    context_tags: list[str]
    coldstart: bool
    excluded_count: int

    # ── State — A-2 갱신 ─────────────────────────────────────────────────────
    picks: list[dict[str, Any]]
    generation_status: str

    # ── State — 오케스트레이터 1개만 ──────────────────────────────────────────
    reject_history: Annotated[list[str], operator.add]  # 누적만
    refresh_count: int  # 덮어쓰기(증가) — 주체가 1개라 누적 규칙 대상 아님
    retry_count_by_layer: Annotated[dict[str, int], _merge_counts]  # 누적만

    # ── 부속 값(에이전트 계약 밖 · ⑥ 관측과 착지에 씀) ────────────────────────
    preference_codes: list[str]
    recent_category_codes: list[str]
    recent_restaurant_ids: list[str]
    region_code: str
    member_ctx: dict[str, Any]
    block_stats: dict[str, int]
    unresolved_terms: list[str]
    no_candidate: bool
    fallback_reason: str | None
    llm_call_count: int
    coldstart_notice: str | None
    learning_notice: str | None
    prior_source: str | None
    output_violations: list[str]
    recommendation_id: str
    error_code: str | None


class BatchState(TypedDict, total=False):
    """④ 7절 `S-B` ㉯ 동기화 배치 상태 4종."""

    sync_run_at: datetime  # Runtime Context
    fetched_restaurants: list[dict[str, Any]]  # S-B10 단독
    blocked_string_count: Annotated[int, operator.add]  # S-B11 단독 · 누적만
    expired_count: int  # S-B14 단독
    loaded_count: int
    closed_filtered_count: int
    trace_id: str
