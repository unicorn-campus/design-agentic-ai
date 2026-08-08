"""재개 진입점 시험 — 중단 전 단계는 다시 돌지 않고 같은 단계 식별자에서 이어짐."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt

from common.state import TriggerKind
from services.flow import graphs
from services.flow.resume import RESUME_BOUNDARIES, side_effect_steps
from services.flow.steps import STEPS_BY_TRIGGER


def _fake_subscribe_node(step_id: str):
    async def node(state, context):
        if step_id == "S-S5":
            return {"partial_context": [{"step_id": step_id, "marker": "before-gate"}]}
        if step_id == "S-S7":
            answer = interrupt(
                {
                    "step_id": step_id,
                    "resume_step_id": step_id,
                    "shown": {"amount_krw": 4900},
                }
            )
            return {"approval_evidence": dict(answer)}
        return {}

    node.__name__ = f"node_{step_id.replace('-', '_')}_resume_test"
    return node


@pytest.mark.asyncio
async def test_resume_continues_at_interrupt_without_rerunning_previous_steps(
    monkeypatch: pytest.MonkeyPatch,
    make_context,
) -> None:
    for step_id in STEPS_BY_TRIGGER[TriggerKind.SYNC_SUBSCRIBE]:
        monkeypatch.setitem(graphs.NODE_FUNCTIONS, step_id, _fake_subscribe_node(step_id))

    saver = InMemorySaver()
    context = make_context(inputs={"section": "결제"})
    first = await graphs.run_flow(
        TriggerKind.SYNC_SUBSCRIBE,
        context,
        member_id="m1",
        requested_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
        checkpointer=saver,
        workflow_name="subscribe",
    )

    assert first.interrupted is True
    assert first.interrupt_payload is not None
    assert first.interrupt_payload["step_id"] == "S-S7"
    assert [row["marker"] for row in first.state["partial_context"]] == ["before-gate"]

    resumed = await graphs.resume_flow(
        TriggerKind.SYNC_SUBSCRIBE,
        context,
        thread_id=first.thread_id,
        resume_value={"user_approval_id": "approval-1"},
        checkpointer=saver,
    )

    assert resumed.interrupted is False
    assert resumed.state["approval_evidence"] == {"user_approval_id": "approval-1"}
    assert [row["marker"] for row in resumed.state["partial_context"]] == ["before-gate"]


@pytest.mark.asyncio
async def test_resume_rejects_trigger_declared_as_no_resume(make_context) -> None:
    with pytest.raises(ValueError, match="재개 안 함"):
        await graphs.resume_flow(
            TriggerKind.SYNC_RECOMMEND,
            make_context(),
            thread_id="thread-1",
            resume_value={},
            checkpointer=InMemorySaver(),
        )


@pytest.mark.asyncio
async def test_resume_requires_a_checkpointer(make_context) -> None:
    with pytest.raises(ValueError, match="중간 저장 장치"):
        await graphs.resume_flow(
            TriggerKind.SYNC_SUBSCRIBE,
            make_context(),
            thread_id="thread-1",
            resume_value={},
            checkpointer=None,
        )


def test_every_side_effect_resume_boundary_has_an_idempotency_key_shape() -> None:
    assert len(RESUME_BOUNDARIES) == 9
    assert len(side_effect_steps()) == len(RESUME_BOUNDARIES)
    for boundary in RESUME_BOUNDARIES:
        assert boundary.side_effect is True
        assert boundary.idempotency_scope
        assert boundary.idempotency_parts
