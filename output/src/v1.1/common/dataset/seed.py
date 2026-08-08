"""합성 시드 생성기 — 실제 데이터가 없을 때 **형태만 같게** 만들어 두는 연습용 데이터.

세 가지를 지킴.

- 난수 씨앗을 설정에서 받아 고정함. 같은 씨앗이면 같은 데이터가 나옴
- 모든 행에 합성 표식 `_synthetic`을 1개 붙임. 실데이터와 섞여도 구분됨
- 읽는 사람 모양이 실접속과 **같음.** 뒤 프롬프트가 부르는 이름이 달라지지 않음

만들 수 없는 경로는 **지어내지 않고 0행으로 두고 이유를 남김.**
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from typing import Any

from common.config import Settings, get_settings
from common.state import SubscriptionState

from .forbidden import assert_no_forbidden_field
from .paths import PathSpec, spec_of
from .source_port import Origin

__all__ = [
    "SEED_MARK",
    "SeedSourceReader",
    "seed_blocked_reason",
    "seed_rows_for",
]

SEED_MARK = "_synthetic"

# 기준 날짜를 고정해 둠. 씨앗이 같으면 날짜까지 같아야 평가 결과를 견줄 수 있음.
_BASE_DATE = date(2026, 1, 1)
_BASE_TIME = datetime(2026, 1, 1, 12, 30)

# 아래 값들은 기획 원문에서 확인된 것만 씀. 전체 목록이 없는 항목은 `_OPEN` 표식을 붙임.
_OPEN = "[확인필요]"

_CATEGORY_CODES = ("한식", "국물", "매운맛")  # 원문 확인 3종(⑤ 5절 K-3 ⓐ). 전체 목록은 미확정
_DIET_TYPES = ("일반", "채식", "비건", "할랄", "기타")  # ⑤ 5절 K-3 ⓑ 식이 유형 5종
_ALLERGEN_LABELS = ("땅콩", "갑각류")  # 골든셋 GS-19 · GS-20 확인값. 나머지 6종은 미확정
_CONSENT_KINDS = ("위치", "건강")  # ⑤ 3절 T-3 「거르는 조건」
_CONSENT_STATES = ("동의", "거부")
_SATISFACTIONS = ("좋았어요", "별로였어요")  # US:UFR-REC-090 2택
_CONTEXT_TAGS = ("날씨", "이력", "취향")  # 골든셋 GS-14 3종
_ACTIONS = ("수락", "거절")
_REJECT_REASONS = ("너무 멀어요",)  # 골든셋 GS-18 확인값
_FAIL_REASON_CODES = ("카드한도초과", "카드유효기간만료", "잔액부족")
_SUBSCRIPTION_STATUSES = ("활성", "해지예약")
_INSIGHT_METRICS = ("top_category", "satisfaction_trend", "visit_frequency")
_WEEKLY_METRICS = ("weekday_pattern", "time_slot_pattern", "cumulative_count")
_MEMORY_METRICS = ("cumulative_count", "expiring_count")

# 판매 중 플랜 — 값이 기획 원문에 있는 유일한 마스터임(골든셋 GS-29 · US:UFR-PAY-010).
_PLANS: tuple[dict[str, Any], ...] = (
    {
        "plan_code": "MONTHLY",
        "plan_type": "월 결제",
        "price_krw": 4900,
        "billing_cycle": "월",
        "benefits": "무제한 이력 · 인사이트",
    },
    {
        "plan_code": "YEARLY",
        "plan_type": "연 결제",
        "price_krw": 3900,
        "billing_cycle": "월(연 결제)",
        "benefits": "무제한 이력 · 인사이트",
    },
)

# 시드를 만들 수 없는 경로와 그 이유. 짐작으로 채우지 않고 0행으로 둠.
_BLOCKED: dict[str, str] = {
    "T-10": "취향 벡터의 차원 수를 모름 — [확인필요: 벡터 인덱스 제품·임베딩 모델명·버전]",
}


def seed_blocked_reason(path_id: str) -> str | None:
    """이 경로의 시드를 못 만드는 이유. 만들 수 있으면 `None`임."""
    return _BLOCKED.get(path_id)


def _member_id(index: int) -> str:
    return f"M{index:06d}"


def _cycle(values: Sequence[Any], index: int) -> Any:
    return values[index % len(values)]


def _value_for(column: str, index: int, spec: PathSpec, rng: random.Random) -> Any:
    if column == "member_id":
        return _member_id(index)
    if column == "nickname":
        return f"손님{index}"
    if column == "notify_enabled":
        return index % 2 == 0
    if column == "subscription_state":
        return _cycle(tuple(state.value for state in SubscriptionState), index)
    if column == "allergen_labels":
        return [_cycle(_ALLERGEN_LABELS, index)]
    if column == "diet_type":
        return _cycle(_DIET_TYPES, index)
    if column == "consent_kind":
        return _cycle(_CONSENT_KINDS, index)
    if column == "consent_state":
        return _cycle(_CONSENT_STATES, index)
    if column == "restaurant_id":
        return f"R{index:06d}"
    if column == "restaurant_name":
        return f"식당{index}"
    if column == "category_code":
        return _cycle(_CATEGORY_CODES, index)
    if column == "feedback_id":
        return f"FB{index:08d}"
    if column == "recommendation_id":
        return f"RC{index:08d}"
    if column == "satisfaction":
        return _cycle(_SATISFACTIONS, index)
    if column == "keyword":
        return f"키워드{index}"
    if column == "reason_line":
        return f"합성 이유 문장 {index}"
    if column == "reason_detail":
        return f"합성 이유 상세 {index}"
    if column == "confidence_score":
        return round(rng.random(), 3)
    if column == "context_tags":
        return list(_CONTEXT_TAGS)
    if column == "action":
        return _cycle(_ACTIONS, index)
    if column == "reject_reason":
        return _cycle(_REJECT_REASONS, index)
    if column == "cached_at":
        return (_BASE_TIME + timedelta(minutes=index)).isoformat()
    if column == "recommendation_set":
        # 캐시 1건의 **겉모양**만 만듦. 카드 수는 추천 생성 쪽이 정하므로 여기서 정하지 않음.
        return [{"recommendation_id": f"RC{index:08d}", "reason_line": f"합성 이유 문장 {index}"}]
    if column == "plan_code":
        return _cycle(tuple(plan["plan_code"] for plan in _PLANS), index)
    if column == "is_active":
        return index % 2 == 0
    if column == "remaining_days":
        return index % 7
    if column == "winback_offer_used":
        return index % 3 == 0
    if column == "status":
        return _cycle(_SUBSCRIPTION_STATUSES, index)
    if column == "fail_reason_code":
        return _cycle(_FAIL_REASON_CODES, index)
    if column == "fail_count":
        return index % 3 + 1
    if column == "generation":
        return index
    if column.endswith("_at"):
        return (_BASE_TIME + timedelta(minutes=index)).isoformat()
    if column.endswith("_on"):
        return (_BASE_DATE + timedelta(days=index)).isoformat()
    if column == "value":
        return round(rng.random(), 3)
    return f"{spec.logical_table}.{column}#{index}"


def _metric_rows(
    spec: PathSpec, metrics: Sequence[str], count: int, seed: int
) -> list[dict[str, Any]]:
    """집계 경로 — `회원 + 지표 + 구간`이 겹치지 않게 만듦."""
    rows: list[dict[str, Any]] = []
    rng = random.Random(f"{seed}:{spec.path_id}:metric")
    for index in range(count):
        metric = metrics[index % len(metrics)]
        bucket_no = index // len(metrics)
        row: dict[str, Any] = {"member_id": _member_id(0), "metric": metric}
        if "bucket" in spec.columns:
            row["bucket"] = f"{metric}-{bucket_no}"
        row["value"] = round(rng.random(), 3)
        rows.append(row)
    return rows


def seed_rows_for(
    path_id: str, count: int, seed: int
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """경로 1개의 시드를 만듦. 돌려주는 두 번째 값은 남길 말임."""
    spec = spec_of(path_id)
    blocked = seed_blocked_reason(path_id)
    if blocked:
        return [], (f"시드 0행 — {blocked}",)
    if count < 0:
        raise ValueError("시드 건수를 음수로 만들 수 없음")

    notes: list[str] = []
    rows: list[dict[str, Any]]

    if path_id == "T-9":
        rows = _metric_rows(spec, _INSIGHT_METRICS, count, seed)
    elif path_id == "T-13":
        rows = _metric_rows(spec, _WEEKLY_METRICS, count, seed)
    elif path_id == "T-17":
        made = min(count, len(_MEMORY_METRICS))
        rows = _metric_rows(spec, _MEMORY_METRICS, made, seed)
        if made < count:
            notes.append(f"지표가 {len(_MEMORY_METRICS)}종뿐이라 {made}행만 만듦")
    elif path_id == "T-14":
        made = min(count, len(_PLANS))
        rows = [dict(_PLANS[index]) for index in range(made)]
        if made < count:
            notes.append(
                f"기획 원문에 확인된 판매 중 플랜이 {len(_PLANS)}종뿐이라 {made}행만 만듦"
            )
    else:
        rng = random.Random(f"{seed}:{path_id}")
        rows = [
            {column: _value_for(column, index, spec, rng) for column in spec.columns}
            for index in range(count)
        ]

    for row in rows:
        row[SEED_MARK] = True
        assert_no_forbidden_field(row, f"{path_id} 시드 행")

    if "category_code" in spec.columns:
        notes.append(f"카테고리 전체 목록이 없어 원문 확인 {len(_CATEGORY_CODES)}종만 돌려 씀 {_OPEN}")
    if "allergen_labels" in spec.columns:
        notes.append(f"8대 알레르겐 중 원문 확인 {len(_ALLERGEN_LABELS)}종만 돌려 씀 {_OPEN}")
    return rows, tuple(notes)


class SeedSourceReader:
    """합성 시드 1벌. 실접속과 같은 모양이라 나중에 그대로 갈아 끼울 수 있음."""

    origin = Origin.SEED

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings if settings is not None else get_settings()
        self.notes_by_path: dict[str, tuple[str, ...]] = {}

    @property
    def seed(self) -> int:
        return self._settings.dataset_seed

    def fetch(
        self, spec: PathSpec, params: Mapping[str, Any], row_cap: int
    ) -> Sequence[Mapping[str, Any]]:
        wanted = min(self._settings.dataset_seed_row_count(spec.path_id), row_cap)
        rows, notes = seed_rows_for(spec.path_id, wanted, self.seed)
        self.notes_by_path[spec.path_id] = notes
        return rows
