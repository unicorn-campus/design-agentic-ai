"""③ 단계 수와 노드 수 · ④ 담당자 수와 모듈 수를 **숫자로** 맞춰 봄."""

from __future__ import annotations

import importlib
import inspect

from common.guardrail.rules import load_rulebook

from services.flow import graphs, steps

# ③ 4절 머리 숫자와 각 절의 행 수.
PATTERN_STEP_COUNT = 90
STEPS_PER_TRIGGER = {
    "S-R": 16, "S-B": 10, "S-E": 8, "S-S": 13, "S-C": 11, "S-I": 14, "S-X": 8, "S-N": 10,
}
OWNER_COUNT = 16
ASSIGNED_STEP_COUNT = 85
OUT_OF_CONTRACT_STEP_COUNT = 5


def test_pattern_step_count_matches_node_count() -> None:
    assert len(steps.STEP_IDS) == PATTERN_STEP_COUNT
    assert len(graphs.NODE_FUNCTIONS) == PATTERN_STEP_COUNT
    assert set(graphs.NODE_FUNCTIONS) == set(steps.STEP_IDS)


def test_step_count_per_trigger_matches_design_rows() -> None:
    counted = {
        kind.value: len(step_ids) for kind, step_ids in steps.STEPS_BY_TRIGGER.items()
    }
    assert counted == STEPS_PER_TRIGGER


def test_pattern_steps_match_guardrail_rulebook() -> None:
    """⑤⑥이 인용한 ③ 90단계 목록과 글자 하나까지 같아야 함."""
    book = load_rulebook()
    assert tuple(book.pattern_steps) == steps.STEP_IDS


def test_every_node_function_keeps_the_step_identifier() -> None:
    """노드 함수 이름에 ③ 단계 식별자가 남아 있는 비율 100%."""
    misses = [
        (step_id, fn.__name__)
        for step_id, fn in graphs.NODE_FUNCTIONS.items()
        if f"{steps.node_symbol_of(step_id)}_" not in fn.__name__
    ]
    assert misses == []


def test_owner_count_matches_module_count() -> None:
    """④ 담당자 16명 = 모듈 16개. `그리고`·`및`로 쪼갠 건 0건."""
    assert len(steps.OWNER_NAMES) == OWNER_COUNT
    modules = {
        owner: importlib.import_module(
            f"services.{steps.OWNER_SERVICE[owner]}.agents.{_module_name(owner)}"
        )
        for owner in steps.OWNER_NAMES
    }
    assert len(modules) == OWNER_COUNT
    for owner, module in modules.items():
        assert module.OWNER_ID == owner
        assert tuple(module.STEP_IDS) == steps.STEPS_BY_OWNER[owner]


def test_assigned_and_out_of_contract_steps_sum_to_90() -> None:
    assigned = sum(len(v) for v in steps.STEPS_BY_OWNER.values())
    assert assigned == ASSIGNED_STEP_COUNT
    assert len(steps.TERMINAL_STEPS) == OUT_OF_CONTRACT_STEP_COUNT
    assert assigned + len(steps.TERMINAL_STEPS) == PATTERN_STEP_COUNT
    assert set(steps.OWNER_BY_STEP) | steps.TERMINAL_STEPS == set(steps.STEP_IDS)


def test_no_step_has_two_owners() -> None:
    seen: dict[str, str] = {}
    for owner, owned in steps.STEPS_BY_OWNER.items():
        for step_id in owned:
            assert step_id not in seen, f"{step_id}를 {seen.get(step_id)}·{owner}가 함께 맡음"
            seen[step_id] = owner


def test_node_functions_take_state_and_context_only() -> None:
    """노드는 상태와 부품 묶음만 받음. 상태에서 값을 꺼내는 일은 노드가 함."""
    for step_id, fn in graphs.NODE_FUNCTIONS.items():
        params = list(inspect.signature(fn).parameters)
        assert params == ["state", "context"], f"{step_id} 시그니처가 다름: {params}"


def _module_name(owner: str) -> str:
    mapping = {
        "R-1": "r1_recommendation_sentence",
        "R-2": "r2_recommendation_request",
        "R-3": "r3_batch_learning",
        "R-4": "r4_vector_commit",
        "R-5": "r5_learning_transfer",
        "R-6": "r6_onboarding_profile",
        "R-7": "r7_payment_request",
        "R-8": "r8_pg_register",
        "R-9": "r9_cancel_schedule",
        "R-10": "r10_pg_stop",
        "R-11": "r11_expiry_downgrade",
        "R-12": "r12_plan_view",
        "R-13": "r13_subscription_state",
        "R-14": "r14_history_insight",
        "R-15": "r15_memory_limit_notice",
        "R-16": "r16_retention_policy",
    }
    return mapping[owner]
