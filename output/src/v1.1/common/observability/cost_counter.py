"""비용 카운터 — 금액과 상한 숫자를 코드에 박지 않음.

건당 단가(원)는 ① 소유이므로 환경변수(`LUNCHPICK_COST_LIMIT_KRW_PER_REQUEST`)에서 읽음.
콜 수·일일 금액·월 누적 임계는 ⑥ 7-3절 소유이므로 검사 규칙 설정 파일에서 읽음.
재시도와 반복을 곱한 **최악값**도 함께 세어 상한과 비교함 — 배수의 주인은 ③이라 설정에서 읽음.

`common.cost.CostCounter` 계약을 그대로 채움(01-runtime이 마련한 자리).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config import Settings, SettingsMissing
from ..cost import CostCounter
from ..guardrail.errors import BlockDecision
from ..guardrail.rules import RuleBook, get_rulebook

__all__ = ["CostVerdict", "WorstCase", "RuleCostCounter"]


@dataclass(frozen=True, slots=True)
class CostVerdict:
    """비용 판정 1건. 넘겼으면 어느 규칙에 걸렸는지 함께 담음."""

    within_limit: bool
    warned: bool
    decision: BlockDecision | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    """`O-10` 항목 이름으로 담음 — 일일 콜 수 · 일일 환산 금액 · 임계 도달 여부."""


@dataclass(frozen=True, slots=True)
class WorstCase:
    """재시도 × 반복을 곱한 최악값. 숫자는 전부 ③ 설정에서 옴."""

    retry_multiplier: int
    loop_multiplier: int
    calls_per_request: int
    krw_per_request: float | None
    over_per_request_cap: bool
    unconfirmed: tuple[str, ...] = ()


class RuleCostCounter(CostCounter):
    """요청당·일일·월 누적을 세고 ⑥ 7-3절 임계와 견줌."""

    def __init__(self, settings: Settings, book: RuleBook | None = None) -> None:
        self._settings = settings
        self._book = book or get_rulebook()
        self._cost = self._book.cost
        self._spent: dict[str, float] = {}
        self._calls: dict[str, int] = {}
        self._daily_calls: dict[str, int] = {}
        self._daily_krw: dict[str, float] = {}
        self._monthly_krw: dict[str, float] = {}

    # --- common.cost.CostCounter 계약 --------------------------------------
    def add_model_call(self, request_id: str, krw: float) -> None:
        self._spent[request_id] = self._spent.get(request_id, 0.0) + krw
        self._calls[request_id] = self._calls.get(request_id, 0) + 1

    def spent_krw(self, request_id: str) -> float:
        return self._spent.get(request_id, 0.0)

    def over_limit(self, request_id: str) -> bool:
        limit = self._settings.cost_limit_krw_per_request
        if limit is None:
            # 단가 정본이 없으면 금액으로는 못 재고 **콜 수 상한으로만** 막음
            return self.calls(request_id) > self.per_request_call_cap
        return self.spent_krw(request_id) > limit

    # --- 세는 값 -----------------------------------------------------------
    def calls(self, request_id: str) -> int:
        return self._calls.get(request_id, 0)

    def add_daily(self, day_key: str, krw: float, calls: int = 1) -> None:
        self._daily_calls[day_key] = self._daily_calls.get(day_key, 0) + calls
        self._daily_krw[day_key] = self._daily_krw.get(day_key, 0.0) + krw

    def add_monthly(self, month_key: str, krw: float) -> None:
        self._monthly_krw[month_key] = self._monthly_krw.get(month_key, 0.0) + krw

    # --- 설정에서 읽는 임계 -------------------------------------------------
    @property
    def per_request_call_cap(self) -> int:
        return int(self._cost["per_request_model_call_cap"])

    @property
    def sync_daily_call_cap(self) -> int:
        return int(self._cost["sync_daily_call_cap"])

    @property
    def sync_daily_krw_cap(self) -> float:
        return float(self._cost["sync_daily_krw_cap"])

    @property
    def monthly_krw_cap(self) -> float:
        return float(self._cost["monthly_krw_cap"])

    @property
    def warning_ratio(self) -> float:
        return float(self._cost["warning_ratio"])

    @property
    def over_limit_action(self) -> str:
        """상한을 넘겼을 때의 행동. 3단계 되묻기 답이 설정에 들어 있음."""
        return str(self._book.answers["cost_over_limit_action"])

    # --- 판정 -------------------------------------------------------------
    def check_request(self, request_id: str, *, step_id: str | None = None) -> CostVerdict:
        """요청 1건의 모델 호출 상한(`B-11`)을 봄."""
        calls = self.calls(request_id)
        metrics = {"요청당 콜 수": calls, "상한": self.per_request_call_cap}
        if calls > self.per_request_call_cap:
            return CostVerdict(
                within_limit=False,
                warned=False,
                decision=self._decision("B-11", step_id),
                metrics=metrics,
            )
        return CostVerdict(within_limit=True, warned=False, metrics=metrics)

    def check_daily(self, day_key: str, *, step_id: str | None = None) -> CostVerdict:
        """일일 콜 수·금액 임계(`B-10`)를 봄. 80% 지점에서는 경보만."""
        calls = self._daily_calls.get(day_key, 0)
        krw = self._daily_krw.get(day_key, 0.0)
        metrics = {
            "일일 콜 수": calls,
            "일일 환산 금액": krw,
            "임계 도달 여부": False,
        }
        reached = calls >= self.sync_daily_call_cap or krw >= self.sync_daily_krw_cap
        warned = (
            calls >= self.sync_daily_call_cap * self.warning_ratio
            or krw >= self.sync_daily_krw_cap * self.warning_ratio
        )
        if reached:
            metrics["임계 도달 여부"] = True
            return CostVerdict(
                within_limit=False,
                warned=True,
                decision=self._decision("B-10", step_id),
                metrics=metrics,
            )
        return CostVerdict(within_limit=True, warned=warned, metrics=metrics)

    def check_monthly(self, month_key: str, *, step_id: str | None = None) -> CostVerdict:
        krw = self._monthly_krw.get(month_key, 0.0)
        metrics = {"월 누적 금액": krw, "임계 도달 여부": krw >= self.monthly_krw_cap}
        if krw >= self.monthly_krw_cap:
            return CostVerdict(
                within_limit=False,
                warned=True,
                decision=self._decision("B-10", step_id),
                metrics=metrics,
            )
        return CostVerdict(within_limit=True, warned=False, metrics=metrics)

    # --- 최악값 -----------------------------------------------------------
    def worst_case(self) -> WorstCase:
        """재시도 배수 × 루프 배수. 값이 없으면 지어내지 않고 `[확인필요]`로 돌려줌."""
        spec = self._cost["worst_case"]
        unconfirmed: list[str] = []
        try:
            retry = 1 + self._settings.retry_count(str(spec["retry_source_step"]))
        except SettingsMissing:
            retry = 1
            unconfirmed.append(f"③ 재시도 값 — 단계 {spec['retry_source_step']}")
        try:
            loop = 1 + self._settings.max_iter(str(spec["loop_source_id"]))
        except SettingsMissing:
            loop = 1
            unconfirmed.append(f"③ 반복 상한 — 루프 {spec['loop_source_id']}")
        calls = retry * loop
        unit = self._settings.cost_limit_krw_per_request
        if unit is None:
            unconfirmed.append("① 건당 단가 정본")
        return WorstCase(
            retry_multiplier=retry,
            loop_multiplier=loop,
            calls_per_request=calls,
            krw_per_request=None if unit is None else calls * unit,
            over_per_request_cap=calls > self.per_request_call_cap,
            unconfirmed=tuple(unconfirmed),
        )

    def _decision(self, rule_id: str, step_id: str | None) -> BlockDecision:
        row = self._book.block_rule(rule_id)
        return BlockDecision(
            rule_id=rule_id,
            action=str(row["action"]),
            point=str(row["point"]),
            signal=str(row["signal"]),
            notify=tuple(row.get("notify", ())),
            step_id=step_id,
            detail={"over_limit_action": self.over_limit_action},
        )
