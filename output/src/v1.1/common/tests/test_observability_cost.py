"""비용 카운터 — 상한을 넘기면 3단계에서 정한 행동이 일어나는지 확인함(시험 7번)."""

from __future__ import annotations

from common.observability.cost_counter import RuleCostCounter

DAY = "2026-08-08"
MONTH = "2026-08"


def test_over_per_request_call_cap_lands_fallback(settings, rulebook) -> None:
    """`B-11` — 요청당 모델 호출 상한을 넘기면 착지로 감."""
    counter = RuleCostCounter(settings, rulebook)
    cap = counter.per_request_call_cap
    for _ in range(cap):
        counter.add_model_call("REQ-1", 10.0)
    assert counter.check_request("REQ-1").within_limit
    counter.add_model_call("REQ-1", 10.0)
    verdict = counter.check_request("REQ-1", step_id="S-R11")
    assert not verdict.within_limit
    assert verdict.decision.rule_id == "B-11"
    assert verdict.decision.action == "land_fallback"


def test_over_daily_limit_downgrades_to_rule_based(settings, rulebook) -> None:
    """`B-10` — 일일 임계에 닿으면 규칙 기반 추천으로 낮춤."""
    counter = RuleCostCounter(settings, rulebook)
    counter.add_daily(DAY, krw=counter.sync_daily_krw_cap, calls=counter.sync_daily_call_cap)
    verdict = counter.check_daily(DAY, step_id="S-R11")
    assert not verdict.within_limit
    assert verdict.decision.rule_id == "B-10"
    assert verdict.decision.action == "downgrade_to_rule_based"
    assert verdict.metrics["임계 도달 여부"] is True


def test_warning_line_only_warns(settings, rulebook) -> None:
    """사전 경보선(80%)에서는 경보만 내고 차단하지 않음."""
    counter = RuleCostCounter(settings, rulebook)
    calls = int(counter.sync_daily_call_cap * counter.warning_ratio)
    counter.add_daily(DAY, krw=0.0, calls=calls)
    verdict = counter.check_daily(DAY)
    assert verdict.within_limit
    assert verdict.warned


def test_monthly_cap_stops_model_calls(settings, rulebook) -> None:
    counter = RuleCostCounter(settings, rulebook)
    counter.add_monthly(MONTH, counter.monthly_krw_cap)
    verdict = counter.check_monthly(MONTH)
    assert not verdict.within_limit


def test_over_limit_action_comes_from_the_asked_answer(settings, rulebook) -> None:
    """상한을 넘겼을 때의 행동은 3단계 되묻기 답임 — 코드에 박지 않음."""
    counter = RuleCostCounter(settings, rulebook)
    assert counter.over_limit_action == "abort_request_and_notify"
    assert counter.over_limit_action == rulebook.answers["cost_over_limit_action"]


def test_worst_case_multiplies_retry_and_loop(settings, rulebook) -> None:
    """재시도와 반복을 곱한 최악값을 함께 세어 상한과 비교함. 배수는 ③ 설정에서 옴."""
    counter = RuleCostCounter(settings, rulebook)
    worst = counter.worst_case()
    # 시험 대역은 S-R11 재시도 1회 · L-1 반복 상한 미설정
    assert worst.retry_multiplier == 1 + settings.retry_count("S-R11") == 2
    assert worst.loop_multiplier == 1  # 값이 없어 곱하지 않음
    assert worst.calls_per_request == 2
    assert not worst.over_per_request_cap
    assert "③ 반복 상한 — 루프 L-1" in worst.unconfirmed


def test_worst_case_reports_unconfirmed_instead_of_inventing(settings, rulebook) -> None:
    """값이 없으면 흔한 기본값으로 채우지 않고 `[확인필요]`로 돌려줌."""
    counter = RuleCostCounter(settings, rulebook)
    worst = counter.worst_case()
    assert "① 건당 단가 정본" in worst.unconfirmed
    assert worst.krw_per_request is None


def test_call_cap_guards_when_unit_price_is_unset(settings, rulebook) -> None:
    """단가 정본이 없으면 금액으로 못 재므로 **콜 수 상한으로만** 막음."""
    counter = RuleCostCounter(settings, rulebook)
    assert settings.cost_limit_krw_per_request is None
    for _ in range(counter.per_request_call_cap + 1):
        counter.add_model_call("REQ-1", 0.0)
    assert counter.over_limit("REQ-1")


def test_counter_fills_the_runtime_contract(settings, rulebook) -> None:
    """`01-runtime`이 마련한 `CostCounter` 자리를 그대로 채움."""
    from common.cost import CostCounter

    counter = RuleCostCounter(settings, rulebook)
    assert isinstance(counter, CostCounter)
