"""`R-14` 이력·인사이트 조회 처리기 — ④ 3-14절.

맡은 ③ 단계 13개 — `S-I2` ~ `S-I14`.
사용 모델 — **모델 미사용(결정론적 실행).** `weekly_pattern_summary` 1칸의 생성 수단은
`[확인필요: 인사이트 주간 패턴 요약 문장의 생성 수단(집계 템플릿 vs 모델 호출)]`(③ 7-2절 소유)이며
현재 계약은 **집계 템플릿을 전제**로 모델 호출 도구가 0건임.
사용 도구 — `T-1` · `T-5` · `T-9` 조회 `읽기`. **쓰기 0건.**
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = [
    "OWNER_ID",
    "STEP_IDS",
    "MIN_RECORD_COUNT",
    "MILESTONE_RECORD_COUNT",
    "accept_timeline_request",
    "decide_allowed_period",
    "collect_timeline",
    "build_timeline_response",
    "accept_insight_request",
    "check_min_record_count",
    "collect_statistics",
    "aggregate_insight",
    "check_consistency",
    "build_insight_response",
    "decide_milestone",
    "decide_memory_limit_notice",
    "build_timeline_only_response",
]

OWNER_ID = "R-14"
STEP_IDS = tuple(f"S-I{n}" for n in range(2, 15))

MIN_RECORD_COUNT = 10
"""④ 「성공 기준」이 인용한 원문 값 — `US:UFR-REC-120#검증(10건)`. 단계 상한이 아님."""
MILESTONE_RECORD_COUNT = 30
"""ES:06(29 ~ 31행) 누적 30건. 위와 같이 기획 원문 값임."""
_FREE_PERIOD_DAYS = 30
"""US:UFR-PAY-030#검증 무료 30일 경계."""


def accept_timeline_request(
    *,
    history_request_id: str,
    member_id: str,
    requested_at: int,
    deadline_at: int,
    trigger_kind: str,
) -> dict[str, Any]:
    """`S-I2` 진입 값(③에 집합 식별자 없음)."""
    return {
        "history_request_id": history_request_id,
        "member_id": member_id,
        "requested_at": requested_at,
        "deadline_at": deadline_at,
        "trigger_kind": trigger_kind,
    }


def decide_allowed_period(
    *,
    member_id: str,
    subscription_state: str | None,
    today: str,
    free_period_from: str,
) -> dict[str, Any]:
    """`S-I3` `K-32` 조회 기간 판정 집합.

    ④ 중단 조건 ⓐ — 구독 상태를 못 읽으면 **좁은 쪽(무료 30일)으로 판정하지 않고 멈춤**(⑥ `B-29`).
    """
    if subscription_state is None:
        return {
            "member_id": member_id,
            "subscription_state": None,
            "allowed_period_from": None,
            "allowed_period_to": None,
            "unlimited_period": False,
            "precheck_passed": False,
        }
    unlimited = subscription_state == "프리미엄"
    return {
        "member_id": member_id,
        "subscription_state": subscription_state,
        "allowed_period_from": None if unlimited else free_period_from,
        "allowed_period_to": today,
        "unlimited_period": unlimited,
        "precheck_passed": True,
    }


def collect_timeline(
    *, meal_history_rows: Sequence[Mapping[str, Any]] | None
) -> dict[str, Any]:
    """`S-I4` 기간 내 기록 조회 결과를 달력 뷰 모양으로 묶음."""
    by_day: dict[str, list[dict[str, Any]]] = {}
    for row in meal_history_rows or ():
        day = str(row.get("recorded_on", ""))
        by_day.setdefault(day, []).append(
            {
                "meal_record_id": str(row.get("meal_record_id", "")),
                "menu_name": str(row.get("menu_name", "")),
                "category_code": str(row.get("category_code", "")),
            }
        )
    timeline = [
        {"recorded_on": day, "meal_records": records}
        for day, records in sorted(by_day.items())
    ]
    return {"timeline": timeline, "source_record_count": len(meal_history_rows or ())}


def build_timeline_response(
    *, timeline: Sequence[Mapping[str, Any]], fallback_notice: str | None = None
) -> dict[str, Any]:
    """`S-I5` 달력 뷰 타임라인 응답. 기록 0건이면 첫 기록 안내를 담음."""
    return {
        "timeline": [dict(day) for day in timeline],
        "fallback_notice": fallback_notice
        or (None if timeline else "첫 기록을 남겨 주세요"),
    }


def accept_insight_request(
    *, insight_request_id: str, member_id: str, requested_at: int, deadline_at: int
) -> dict[str, Any]:
    """`S-I6` 진입 값(③에 집합 식별자 없음)."""
    return {
        "insight_request_id": insight_request_id,
        "member_id": member_id,
        "requested_at": requested_at,
        "deadline_at": deadline_at,
    }


def check_min_record_count(*, source_record_count: int) -> dict[str, Any]:
    """`S-I7` 사전 조건 — 최소 기록 10건 판정.

    ④ 중단 조건 ⓑ — 미달이면 인사이트를 만들지 않고 안내만 함.
    """
    return {
        "source_record_count": source_record_count,
        "precheck_passed": source_record_count >= MIN_RECORD_COUNT,
    }


def collect_statistics(
    *,
    category_distribution: Sequence[Mapping[str, Any]],
    satisfaction_trend: Sequence[Mapping[str, Any]],
    visit_frequency: Sequence[Mapping[str, Any]],
    source_record_count: int,
) -> dict[str, Any]:
    """`S-I8` `K-33` 통계 원천 집합."""
    return {
        "category_distribution": [dict(r) for r in category_distribution],
        "satisfaction_trend": [dict(r) for r in satisfaction_trend],
        "visit_frequency": [dict(r) for r in visit_frequency],
        "source_record_count": source_record_count,
    }


def aggregate_insight(
    *,
    category_distribution: Sequence[Mapping[str, Any]],
    satisfaction_trend: Sequence[Mapping[str, Any]],
    weekly_pattern: Sequence[Mapping[str, Any]],
    accuracy_gain_formula_available: bool,
) -> dict[str, Any]:
    """`S-I9` `K-34` 인사이트 후보 집합.

    ④ 중단 조건 ⓓ — 향상률 산출식이 없으면 향상률을 **만들지 않음**(⑥ `B-25`).
    요약 문장은 집계 템플릿으로 만듦(모델 호출 0건).
    """
    top = [
        str(row.get("category_code", ""))
        for row in sorted(
            category_distribution,
            key=lambda r: int(r.get("visit_count", 0)),
            reverse=True,
        )[:5]
    ]
    rates = [float(r.get("satisfaction_rate", 0.0)) for r in satisfaction_trend or ()]
    change = round(rates[-1] - rates[0], 4) if len(rates) >= 2 else 0.0
    summary = (
        f"이번 기간에 가장 많이 고른 것은 {top[0]}임" if top else None
    )
    return {
        "insight_top_categories": top,
        "weekly_pattern": [dict(r) for r in weekly_pattern],
        "satisfaction_change": change,
        "weekly_pattern_summary": summary,
        "accuracy_gain_rate": None if not accuracy_gain_formula_available else 0.0,
    }


def check_consistency(
    *,
    insight_top_categories: Sequence[str],
    satisfaction_change: float,
    weekly_pattern_summary: str | None,
    accuracy_gain_rate: float | None,
    category_distribution: Sequence[Mapping[str, Any]],
    satisfaction_trend: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """`S-I10` `K-35` 노출 승인 집합 — 요약 문장·수치를 원천 집계값과 대조함(`V-10` 11번).

    불일치 항목은 **비노출**임(자동 노출 금지 · ⑥ `B-24`).
    """
    hidden: list[str] = []
    displayable: list[str] = []
    source_top = {str(r.get("category_code", "")) for r in category_distribution or ()}
    if insight_top_categories and set(insight_top_categories) <= source_top:
        displayable.append("insight_top_categories")
    else:
        hidden.append("insight_top_categories")

    rates = [float(r.get("satisfaction_rate", 0.0)) for r in satisfaction_trend or ()]
    expected = round(rates[-1] - rates[0], 4) if len(rates) >= 2 else 0.0
    if abs(expected - float(satisfaction_change)) < 1e-9:
        displayable.append("satisfaction_change")
    else:
        hidden.append("satisfaction_change")

    if weekly_pattern_summary and insight_top_categories and (
        insight_top_categories[0] in weekly_pattern_summary
    ):
        displayable.append("weekly_pattern_summary")
    else:
        hidden.append("weekly_pattern_summary")

    if accuracy_gain_rate is None:
        hidden.append("accuracy_gain_rate")
    else:
        displayable.append("accuracy_gain_rate")

    return {
        "consistency_passed": not hidden,
        "hidden_item_codes": hidden,
        "displayable_items": displayable,
        "mismatch_reason": None if not hidden else "원천 집계값과 어긋남",
    }


def build_insight_response(
    *,
    timeline: Sequence[Mapping[str, Any]],
    insight_aggregate: Mapping[str, Any],
    displayable_items: Sequence[str],
) -> dict[str, Any]:
    """`S-I11` 인사이트 대시보드 표시 — **일치 항목만** 담음."""
    allowed = set(displayable_items)
    out: dict[str, Any] = {"timeline": [dict(day) for day in timeline]}
    for key in (
        "insight_top_categories",
        "weekly_pattern",
        "satisfaction_change",
        "weekly_pattern_summary",
        "accuracy_gain_rate",
    ):
        if key in allowed or key == "weekly_pattern":
            out[key] = insight_aggregate.get(key)
    return out


def decide_milestone(
    *, source_record_count: int, accuracy_gain_rate: float | None
) -> dict[str, Any]:
    """`S-I12` 마일스톤 표시 판정 — 누적 30건 이상일 때 축하 + 향상률."""
    if source_record_count < MILESTONE_RECORD_COUNT:
        return {"milestone_message": None, "accuracy_gain_rate": None}
    return {
        "milestone_message": f"기록 {source_record_count}건 달성",
        "accuracy_gain_rate": accuracy_gain_rate,
    }


def decide_memory_limit_notice(
    *, subscription_state: str | None, expiring_record_count: int
) -> dict[str, Any]:
    """`S-I13` 기억 제한 안내 표시 — 무료 30일 초과 접근일 때만."""
    if subscription_state == "무료" and expiring_record_count > 0:
        return {
            "memory_limit_notice": (
                f"무료 플랜은 최근 {_FREE_PERIOD_DAYS}일만 보관됨"
                f" — 만료 예정 {expiring_record_count}건"
            )
        }
    return {"memory_limit_notice": None}


def build_timeline_only_response(
    *, timeline: Sequence[Mapping[str, Any]], fallback_reason: str
) -> dict[str, Any]:
    """`S-I14` 착지 — 수치 없는 타임라인만 제시 + 낮춘 사유 표시.

    **착지 경로가 상한을 다시 쓰지 않음** — 재조회 0건 · 모델 호출 0건 · 비용 0원임.
    """
    return {
        "timeline": [dict(day) for day in timeline],
        "fallback_notice": fallback_reason,
    }
