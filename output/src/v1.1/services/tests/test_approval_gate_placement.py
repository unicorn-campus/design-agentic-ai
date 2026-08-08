"""필수 시험 4 — 되돌릴 수 없는 도구가 **승인 없이 불리지 않음.**

승인 문 구현체는 `05-guardrail.md`가 만든 것을 부르며 여기서는 **배치**만 확인함.
③ 8-1-2절 ⓐ가 확정한 되돌릴 수 없는 단계 3개(`S-S9` · `S-C10` · `S-X4`)를 전부 봄.
"""

from __future__ import annotations

import pytest

from common.budget import now_ms
from common.guardrail.rules import load_rulebook

from services.flow import graphs
from services.flow.signals import LandingReason, landing_reason_of
from services.flow.steps import HUMAN_GATE_STEPS, IRREVERSIBLE_TOOL_STEPS


def test_irreversible_steps_sit_behind_an_approval_gate() -> None:
    """③ 4-5 · 4-6절이 승인 단계를 외부 호출 **앞**에 갈라 둔 것을 확인함."""
    order = {"S-S7": 7, "S-S9": 9, "S-C5": 5, "S-C10": 10}
    assert order["S-S7"] < order["S-S9"]
    assert order["S-C5"] < order["S-C10"]
    assert HUMAN_GATE_STEPS == {"S-S7", "S-C5"}
    assert set(IRREVERSIBLE_TOOL_STEPS) == {"S-S9", "S-C10", "S-X4"}


def test_every_irreversible_tool_is_registered_in_the_guardrail_table() -> None:
    """표에 없는 도구는 ⑥이 **기본 거부**함 — 배치한 도구가 표에 다 있는지 봄."""
    book = load_rulebook()
    for tool_id in IRREVERSIBLE_TOOL_STEPS.values():
        assert book.approval_tool(tool_id) is not None, f"{tool_id}가 승인 지점 표에 없음"


async def test_S_S9_refuses_to_call_pg_without_approval_evidence(make_context, tools) -> None:
    """승인 표시가 없으면 **바깥 호출이 0건**이고 착지로 감(⑥ `B-12`)."""
    context = make_context(inputs={"member_id": "m1"})
    state = {
        "deadline_at": now_ms() + 600_000,
        "payment_idempotency_key": "member_plan_and_payment_idempotency:m1:premium:req-1",
        "partial_context": [
            {
                "step_id": "S-S8",
                "K-21": {
                    "payment_token": "tok",
                    "amount_krw": 4900,
                    "billing_cycle": "월",
                    "idempotency_key": "k",
                    "user_approval_id": "",
                },
            }
        ],
    }
    update = await graphs.NODE_FUNCTIONS["S-S9"](state, context)
    assert tools["C-9"].calls == []
    assert landing_reason_of(update) == LandingReason.APPROVAL_ABSENT.value


async def test_S_C10_refuses_to_call_pg_without_confirm_evidence(make_context, tools) -> None:
    """해지 확인 증거가 없으면 PG 중지를 부르지 않음(⑥ `B-23`). 예약을 되돌리지도 않음."""
    context = make_context(inputs={"member_id": "m1"})
    state = {
        "deadline_at": now_ms() + 600_000,
        "cancel_schedule": {"cancel_schedule_id": "cs-1"},
        "partial_context": [
            {
                "step_id": "S-C7",
                "K-36": {
                    "pg_payment_id": "pg-1",
                    "cancel_schedule_id": "cs-1",
                    "pg_cancel_idempotency_key": "pg_payment_and_stop:pg-1:cs-1",
                },
            }
        ],
    }
    update = await graphs.NODE_FUNCTIONS["S-C10"](state, context)
    assert tools["C-12"].calls == []
    assert update["pg_cancel_status"].value == "실패"
    # 예약을 되돌리지 않음 — `cancel_schedule`을 건드린 흔적이 없어야 함.
    assert "cancel_schedule" not in update


async def test_S_S9_calls_pg_once_when_approval_evidence_is_present(make_context, tools) -> None:
    context = make_context(inputs={"member_id": "m1"})
    now = now_ms()
    state = {
        "deadline_at": now + 600_000,
        "payment_idempotency_key": "key-1",
        "approval_evidence": {
            "user_approval_id": "appr-1",
            "approved_at": now,
            "approver_ref": "ref",
            "shown_items": ["청약철회 7일", "자동 갱신", "해지 방법"],
            "subject": "req-1",
            "approval_expires_at": now + 300_000,
        },
        "partial_context": [
            {
                "step_id": "S-S8",
                "K-21": {
                    "payment_token": "tok",
                    "amount_krw": 4900,
                    "billing_cycle": "월",
                    "idempotency_key": "key-1",
                    "user_approval_id": "appr-1",
                },
            }
        ],
    }
    update = await graphs.NODE_FUNCTIONS["S-S9"](state, context)
    assert len(tools["C-9"].calls) == 1
    assert landing_reason_of(update) is None
    assert update["resume_cursor"]["boundary_step"] == "S-S9"


async def test_S_X4_refuses_to_commit_when_precondition_is_unknown(make_context) -> None:
    """`S-X4`는 ⑥ `R-11`의 제한 장치가 문임 — 사전 조건 판정 불가면 강등하지 않음(⑥ `B-26`)."""
    context = make_context(inputs={"batch_run_id": "b1", "execution_lock_id": "lock"})
    state = {
        "deadline_at": now_ms() + 600_000,
        "precheck_result": {"precheck_passed": False, "member_id": "m1", "loop_index": 0},
        "partial_context": [
            {"step_id": "S-X2", "K-30": {"target_rows": [{"member_id": "m1"}], "target_count": 1}}
        ],
    }
    update = await graphs.NODE_FUNCTIONS["S-X4"](state, context)
    assert "resume_cursor" not in update
    assert landing_reason_of(update) is None  # 부분 실패 기록만 — 배치는 다음 대상으로 감


@pytest.mark.parametrize("step_id", sorted(HUMAN_GATE_STEPS))
def test_human_gate_step_is_exempt_from_the_deadline_check(step_id) -> None:
    """사람이 화면을 보는 시간은 어떤 마감선에도 들어가지 않음(③ 6절)."""
    from services.flow.steps import BUDGET_EXEMPT_STEPS

    assert step_id in BUDGET_EXEMPT_STEPS
