"""필수 시험 2 — 재시도를 포함한 **최악값 합계**가 ③ 「대조 2줄」의 목표 안에 있음.

최악값 계산은 `01`의 `common.budget.worst_case_total_ms`가 함(`시간 제한 × (1 + 재시도)`).
③이 응답 마감선을 `[확인필요]`로 남긴 트리거는 **판정 보류**임 — 통과라고 적지 않고
③이 스스로 낸 합계와 같은지만 확인함(값이 어긋나면 시험이 깨짐).
"""

from __future__ import annotations

import pytest

from common.budget import worst_case_total_ms
from common.state import TriggerKind

from services.flow.steps import LANDING_STEP_BY_TRIGGER, STEPS_BY_TRIGGER, TERMINAL_STEPS

# ③ 9절이 스스로 낸 최악값 합계. 시험은 이 값을 **인용**하며 새로 정하지 않음.
DESIGN_WORST_CASE_MS = {
    "S-R": 5350,   # ③ 9-1절 2줄 — S-R2 ~ S-R13 예산 대상 단계
    "S-E-구획1": 750,  # ③ 9-3절
    "S-E-구획2": 900,  # ③ 9-3절
    "S-S-플랜조회": 370,  # ③ 9-4절
}

DESIGN_S_R11_WORST_CASE_MS = 1900
"""③ 4-1절 `S-R11` 행의 최악값 — **조건부 1회**라 `1,800 × 2`가 아님."""

DESIGN_WORST_CASE_UNCONDITIONAL_MS = 7050
"""③ 9-1절이 직전 판에 적은 값 — 조건부 재시도를 반영하기 전의 합계임."""

# ③이 마감선을 `[확인필요]`로 남겨 판정을 닫을 수 없는 트리거.
DEADLINE_UNCONFIRMED = frozenset({"S-R", "S-B", "S-E", "S-S", "S-C", "S-I", "S-X", "S-N"})


def test_recommend_worst_case_matches_the_design_sum(settings) -> None:
    """③ 9-1절 2줄과 맞춰 봄.

    **어긋난 자리를 숨기지 않고 두 값을 함께 적음** — `01`의 최악값 함수는
    `시간 제한 × (1 + 재시도)`만 보므로 `S-R11`을 3,600ms로 셈. ③ 4-1절은 그 단계를
    **조건부 1회**로 못 박아 최악값을 1,900ms로 냈음. 그래서 합계가 7,050 대 5,350으로 갈림.
    """
    budget_steps = (
        "S-R2", "S-R3", "S-R4", "S-R5", "S-R6", "S-R7", "S-R8", "S-R9", "S-R10",
        "S-R11", "S-R12", "S-R13",
    )
    # ③ 9-1절은 병렬 4단계를 **가장 긴 갈래 1개**로 셈(동시에 돌기 때문임).
    serial = ("S-R2", "S-R3", "S-R8", "S-R9", "S-R10", "S-R11", "S-R12", "S-R13")
    parallel_worst = max(
        worst_case_total_ms((step,), settings) for step in ("S-R4", "S-R5", "S-R6", "S-R7")
    )
    naive_total = worst_case_total_ms(serial, settings) + parallel_worst
    assert naive_total == DESIGN_WORST_CASE_UNCONDITIONAL_MS

    # ③ 4-1절이 준 `S-R11` 최악값 1,900ms를 그대로 넣으면 ③ 9-1절 합계와 같아짐.
    without_model_step = worst_case_total_ms(
        tuple(step for step in serial if step != "S-R11"), settings
    )
    conditional_total = without_model_step + parallel_worst + DESIGN_S_R11_WORST_CASE_MS
    assert conditional_total == DESIGN_WORST_CASE_MS["S-R"]
    assert settings.is_retry_conditional("S-R11") is True
    assert set(serial) | {"S-R4", "S-R5", "S-R6", "S-R7"} == set(budget_steps)


def test_event_section_worst_cases_match_the_design_sums(settings) -> None:
    assert worst_case_total_ms(("S-E1", "S-E2", "S-E3", "S-E4"), settings) == (
        DESIGN_WORST_CASE_MS["S-E-구획1"]
    )
    assert worst_case_total_ms(("S-E5", "S-E6", "S-E7"), settings) == (
        DESIGN_WORST_CASE_MS["S-E-구획2"]
    )


def test_subscribe_plan_section_worst_case_matches_the_design_sum(settings) -> None:
    assert worst_case_total_ms(("S-S2", "S-S3", "S-S4"), settings) == (
        DESIGN_WORST_CASE_MS["S-S-플랜조회"]
    )


@pytest.mark.parametrize("trigger_kind", list(TriggerKind))
def test_worst_case_stays_within_the_entry_deadline_span(trigger_kind, settings) -> None:
    """진입선(= 총 예산 − 착지 경로) 안에 드는지 봄.

    마감선이 `[확인필요]`인 트리거는 시험용 총 예산으로 계산했으므로 **판정 보류**임 —
    여기서는 계산이 도는 것과 착지 경로가 진입선에서 이미 빠진 것만 확인함.
    """
    prefix = trigger_kind.value
    span = settings.entry_deadline_span_ms(prefix)
    assert span < settings.budget_total_ms[prefix]
    assert span == settings.budget_total_ms[prefix] - settings.budget_landing_ms[prefix]
    assert prefix in DEADLINE_UNCONFIRMED  # 판정 보류 — 통과로 적지 않음


@pytest.mark.parametrize("trigger_kind", list(TriggerKind))
def test_landing_path_is_not_counted_twice(trigger_kind, settings) -> None:
    """착지 경로 시간을 진입선에서 이미 뺐으므로 단계별 판정에 또 더하지 않음."""
    landing = LANDING_STEP_BY_TRIGGER[trigger_kind]
    landing_worst = worst_case_total_ms((landing,), settings)
    span = settings.entry_deadline_span_ms(trigger_kind.value)
    assert landing_worst > 0
    assert span + settings.budget_landing_ms[trigger_kind.value] == (
        settings.budget_total_ms[trigger_kind.value]
    )


def test_steps_without_timeout_are_only_the_budget_exempt_ones(settings) -> None:
    """시간 제한이 없는 단계는 ③이 `[확인필요]`로 남긴 9개뿐이며 전부 예산 밖 성격임."""
    missing = [
        step
        for steps in STEPS_BY_TRIGGER.values()
        for step in steps
        if step not in settings.step_timeout_ms
    ]
    assert sorted(missing) == sorted(
        ["S-C1", "S-C10", "S-C5", "S-I1", "S-R1", "S-R14", "S-S1", "S-S7", "S-S9"]
    )
    assert TERMINAL_STEPS <= set(missing)
