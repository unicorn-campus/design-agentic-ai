from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from help_desk_guardrails.approval import ApprovalGate
from help_desk_guardrails.policy import load_policy
from help_desk_runtime.budget import (
    RuntimeDeadline,
    StageBudget,
    calculate_worst_case_ms,
)
from help_desk_workflow.contracts import WorkflowDependencies
from help_desk_workflow.roles import (
    DeterministicRole,
    LlmGenerationRole,
    SurveyConsentController,
)
from langgraph.checkpoint.memory import InMemorySaver
from p1_sync_inquiry.workflow import (
    build_customer_inquiry_graph,
    cancel_customer_inquiry,
    redefine_customer_answer,
    run_customer_inquiry,
)
from p2_knowledge_improvement_batch.workflow import (
    build_knowledge_batch_graph,
    resume_knowledge_batch,
    run_knowledge_batch,
)
from p3_conversation_closed_event.workflow import (
    build_consultation_closed_graph,
    resume_consultation_closed,
    run_consultation_closed,
)

STAGE_IDS = (
    *(f"S-R{i}" for i in range(1, 11)),
    *(f"S-B{i}" for i in range(1, 11)),
    *(f"S-E{i}" for i in range(1, 8)),
)

TIMEOUTS = {
    "S-R1": 200,
    "S-R2": 700,
    "S-R3": 400,
    "S-R4": 700,
    "S-R5": 1000,
    "S-R6": 1000,
    "S-R7": 300,
    "S-R8": 1200,
    "S-R9": 600000,
    "S-R10": 300,
    "S-B1": 600000,
    "S-B2": 600000,
    "S-B3": 120000,
    "S-B4": 300000,
    "S-B5": 1200000,
    "S-B6": 900000,
    "S-B7": 120000,
    "S-B8": 900000,
    "S-B9": 3600000,
    "S-B10": 300000,
    "S-E1": 200,
    "S-E2": 500,
    "S-E3": 3000,
    "S-E4": 300,
    "S-E5": 30000,
    "S-E6": 5000,
    "S-E7": 3000,
}
RETRIES = {
    "S-R1": 1,
    "S-R2": 1,
    "S-R8": 1,
    "S-R10": 1,
    "S-B2": 1,
    "S-B5": 1,
    "S-B6": 1,
    "S-B8": 1,
    "S-B10": 1,
    "S-E3": 1,
    "S-E6": 2,
    "S-E7": 1,
}


def fake_settings() -> Any:
    return SimpleNamespace(
        stage_budgets={
            stage: StageBudget(TIMEOUTS[stage], RETRIES.get(stage, 0))
            for stage in STAGE_IDS
        }
    )


async def fake_model(
    stage_id: str, system_prompt: str, user_prompt: str
) -> dict[str, Any]:
    assert "JSON object" in system_prompt
    assert "<workflow_input>" in user_prompt
    values = {
        "S-R2": {"route_decision": "composite"},
        "S-R3": {"sql_candidate": "SELECT allowed_column FROM allowed_view"},
        "S-R5": {"evidence_refs": ["doc:1", "graph:1"]},
        "S-R8": {"answer_draft": {"answer": "근거 답변", "next_action": "완료"}},
        "S-B3": {"sql_candidate": "SELECT topic_code FROM allowed_view"},
        "S-B5": {"topic_evidence": [{"topic": "결제", "evidence_refs": ["doc:2"]}]},
        "S-B8": {
            "faq_candidates": [{"candidate_id": "faq-1", "evidence_refs": ["doc:2"]}]
        },
        "S-E3": {
            "summary_draft": {
                "reason": "문의",
                "checked": "확인",
                "guidance": "안내",
                "next_action": "완료",
            }
        },
    }
    return values[stage_id]


def fake_operations(fail_r4: int = 0) -> tuple[dict[str, Any], dict[str, int]]:
    calls: dict[str, int] = {}

    def operation(stage_id: str, result: dict[str, Any]):
        async def run(inputs: dict[str, Any]) -> dict[str, Any]:
            calls[stage_id] = calls.get(stage_id, 0) + 1
            if stage_id == "S-R4" and calls[stage_id] <= fail_r4:
                raise ValueError("금지 SQL")
            return dict(result)

        return run

    values = {
        "S-R1": {
            "request_id": "req-1",
            "auth_session_ref": "auth-ref",
            "customer_ref": "customer-ref",
            "safe_inquiry_text": "이용 내역 문의",
        },
        "S-R4": {"rows": [{"allowed_column": "value"}]},
        "S-R6": {"results": [{"url": "https://official.test"}]},
        "S-R7": {"risk_result": {"level": "low", "score": 0.1}},
        "S-R10": {
            "result_type": "answer",
            "answer": {"text": "근거 답변"},
            "request_status": "completed",
        },
        "S-B1": {"batch_id": "batch-1", "batch_date": date(2026, 8, 25)},
        "S-B2": {"masked_consultation_refs": ["consultation:1"]},
        "S-B4": {"rows": [{"topic_code": "payment"}]},
        "S-B6": {"results": [{"url": "https://official.test"}]},
        "S-B7": {"priority_result": [{"candidate_id": "faq-1", "score": 1.0}]},
        "S-B10": {"registration_result": {"candidate_id": "faq-1", "status": "queued"}},
        "S-E1": {
            "event_id": "event-1",
            "consultation_ref": "consultation-ref",
            "survey_consent_ref": "consent-ref",
            "accepted": True,
            "duplicate": False,
            "processing_ref": "process-1",
        },
        "S-E2": {"masked_transcript": "[마스킹된 상담]"},
        "S-E4": {"risk_result": {"level": "low", "score": 0.1}},
        "S-E6": {"crm_result": {"record_id": "crm-1", "status": "saved"}},
        "S-E7": {"survey_result": {"send_id": "survey-1", "status": "sent"}},
    }
    return {stage: operation(stage, result) for stage, result in values.items()}, calls


def dependencies(fail_r4: int = 0) -> tuple[WorkflowDependencies, dict[str, int]]:
    operations, calls = fake_operations(fail_r4)
    return WorkflowDependencies(
        settings=fake_settings(),
        deadline=RuntimeDeadline.from_budget_ms(20_000_000),
        operations=operations,
        model_invoke=fake_model,
        approval_gate=ApprovalGate(load_policy()),
        max_iterations={"R-1": 1, "R-2": 1},
    ), calls


ROLE_CONTRACTS = [
    *((stage, "R-L1") for stage in sorted(LlmGenerationRole.STAGES)),
    *((stage, "R-D1") for stage in sorted(DeterministicRole.STAGES)),
    ("S-R9", "R-H1"),
    ("S-B9", "R-H2"),
    ("S-B10", "R-H2"),
    ("S-E5", "R-H3"),
    ("S-E6", "R-H3"),
    ("S-E7", "R-H4"),
]


@pytest.mark.parametrize(("stage_id", "role_id"), ROLE_CONTRACTS)
def test_each_success_criterion_has_one_owner(stage_id: str, role_id: str) -> None:
    owners = [owner for stage, owner in ROLE_CONTRACTS if stage == stage_id]
    assert owners == [role_id]


def test_w1_nodes_and_loop_landing_are_bounded() -> None:
    asyncio.run(_test_w1_nodes_and_loop_landing_are_bounded())


async def _test_w1_nodes_and_loop_landing_are_bounded() -> None:
    deps, calls = dependencies(fail_r4=2)
    graph = build_customer_inquiry_graph(deps, InMemorySaver())
    result = await run_customer_inquiry(
        graph,
        {
            "request_id": "req-1",
            "auth_session_ref": "auth-ref",
            "inquiry_text": "문의",
            "channel": "web",
        },
        "customer-ref",
    )
    assert result["request_status"] == "failed"
    assert calls["S-R4"] == 2
    state = await graph.aget_state(
        {"configurable": {"thread_id": "W-1:customer-ref:req-1"}}
    )
    assert state.values["_workflow"]["r1_iter"] == 2
    assert state.values["_workflow"]["completed_stages"][-1] == "S-R5"
    assert state.values["_workflow"]["landing_reason"] == "R-1:max_iter_exhausted"


def test_w1_low_risk_path_delivers_answer() -> None:
    asyncio.run(_test_w1_low_risk_path_delivers_answer())


async def _test_w1_low_risk_path_delivers_answer() -> None:
    deps, calls = dependencies()
    graph = build_customer_inquiry_graph(deps, InMemorySaver())
    result = await run_customer_inquiry(
        graph,
        {
            "request_id": "req-1",
            "auth_session_ref": "auth-ref",
            "inquiry_text": "문의",
            "channel": "web",
        },
        "customer-ref",
    )
    assert result["request_status"] == "completed"
    assert calls["S-R10"] == 1


def test_w1_deadline_shortage_lands_without_calling_external_operation() -> None:
    deps, calls = dependencies()
    expired = WorkflowDependencies(
        settings=deps.settings,
        deadline=RuntimeDeadline(deadline_monotonic_ms=0),
        operations=deps.operations,
        model_invoke=deps.model_invoke,
        approval_gate=ApprovalGate(load_policy()),
        max_iterations=deps.max_iterations,
    )
    graph = build_customer_inquiry_graph(expired, InMemorySaver())
    result = asyncio.run(
        run_customer_inquiry(
            graph,
            {
                "request_id": "req-expired",
                "auth_session_ref": "auth-ref",
                "inquiry_text": "문의",
                "channel": "web",
            },
            "customer-ref",
        )
    )
    assert result["result_type"] == "safe_stop"
    assert calls == {}


def test_w1_has_separate_cancel_and_post_redefinition_paths() -> None:
    asyncio.run(_test_w1_has_separate_cancel_and_post_redefinition_paths())


async def _test_w1_has_separate_cancel_and_post_redefinition_paths() -> None:
    deps, _ = dependencies()
    operations = dict(deps.operations)

    async def high_risk(inputs: dict[str, Any]) -> dict[str, Any]:
        return {"risk_result": {"level": "high", "score": 0.9}}

    operations["S-R7"] = high_risk
    selected = WorkflowDependencies(
        settings=deps.settings,
        deadline=deps.deadline,
        operations=operations,
        model_invoke=deps.model_invoke,
        approval_gate=ApprovalGate(load_policy()),
        max_iterations=deps.max_iterations,
    )
    graph = build_customer_inquiry_graph(selected, InMemorySaver())
    config = {"configurable": {"thread_id": "W-1:customer-ref:req-1"}}
    first = await graph.ainvoke(
        {
            "request_id": "req-1",
            "auth_session_ref": "auth-ref",
            "inquiry_text": "문의",
            "channel": "web",
        },
        {**config, "recursion_limit": 24},
    )
    assert "__interrupt__" in first
    await redefine_customer_answer(
        graph,
        "W-1:customer-ref:req-1",
        {"decision": "수정", "answer": {"text": "수정 답변"}},
    )
    await cancel_customer_inquiry(graph, "W-1:customer-ref:req-1", "운영자 중단")
    snapshot = await graph.aget_state(config)
    assert snapshot.values["approval_result"]["decision"] == "중단"
    assert snapshot.values["_workflow"]["flow_status"] == "safe_stop"


def test_w2_human_interrupt_resume_and_idempotent_boundary() -> None:
    asyncio.run(_test_w2_human_interrupt_resume_and_idempotent_boundary())


async def _test_w2_human_interrupt_resume_and_idempotent_boundary() -> None:
    deps, calls = dependencies()
    graph = build_knowledge_batch_graph(deps, InMemorySaver())
    first = await run_knowledge_batch(graph, "batch-1", date(2026, 8, 25), "v1")
    assert "__interrupt__" in first
    thread_id = "W-2:2026-08-25:v1"
    result = await resume_knowledge_batch(
        graph,
        thread_id,
        {
            "approval_id": "approval-1",
            "decision_status": "approved",
            "resume_stage": "S-B10",
        },
    )
    assert result["registration_result"]["status"] == "queued"
    assert calls["S-B1"] == 1
    assert calls["S-B10"] == 1


def test_w2_loop_exhaustion_lands_without_model_reentry() -> None:
    asyncio.run(_test_w2_loop_exhaustion_lands_without_model_reentry())


async def _test_w2_loop_exhaustion_lands_without_model_reentry() -> None:
    deps, calls = dependencies()

    async def fail_b4(inputs: dict[str, Any]) -> dict[str, Any]:
        calls["S-B4"] = calls.get("S-B4", 0) + 1
        raise ValueError("금지 SQL")

    operations = dict(deps.operations)
    operations["S-B4"] = fail_b4
    failed = WorkflowDependencies(
        settings=deps.settings,
        deadline=deps.deadline,
        operations=operations,
        model_invoke=deps.model_invoke,
        approval_gate=ApprovalGate(load_policy()),
        max_iterations=deps.max_iterations,
    )
    graph = build_knowledge_batch_graph(failed, InMemorySaver())
    result = await run_knowledge_batch(graph, "batch-1", date(2026, 8, 25), "v1")
    assert calls["S-B4"] == 2
    assert result["_workflow"]["landing_reason"] == "R-2:max_iter_exhausted"
    assert result["_workflow"]["completed_stages"][-1] == "S-B5"


def test_w3_approval_precedes_external_writes_and_resume() -> None:
    asyncio.run(_test_w3_approval_precedes_external_writes_and_resume())


async def _test_w3_approval_precedes_external_writes_and_resume() -> None:
    deps, calls = dependencies()
    graph = build_consultation_closed_graph(deps, InMemorySaver())
    first = await run_consultation_closed(
        graph,
        {
            "event_id": "event-1",
            "consultation_ref": "consultation-ref",
            "ended_at": datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
            "transcript": "상담 원문",
            "survey_consent_ref": "consent-ref",
        },
        "consultation_closed",
    )
    assert first["accepted"] is True
    assert calls.get("S-E6", 0) == 0
    assert calls.get("S-E7", 0) == 0
    result = await resume_consultation_closed(
        graph,
        "W-3:event-1:consultation_closed",
        {
            "approval_id": "approval-2",
            "decision_status": "approved",
            "resume_stage": "S-E6",
        },
    )
    assert result["crm_result"]["status"] == "saved"
    assert result["survey_result"]["status"] == "sent"


def test_irreversible_survey_is_default_denied_without_consent() -> None:
    with pytest.raises(PermissionError, match="수신 동의"):
        SurveyConsentController(ApprovalGate(load_policy())).authorize("")


def test_worst_case_budgets_fit_design_totals() -> None:
    budgets = fake_settings().stage_budgets
    w1 = calculate_worst_case_ms([budgets[f"S-R{i}"] for i in range(1, 11)])
    w1 += budgets["S-R3"].worst_case_ms + budgets["S-R4"].worst_case_ms
    w2 = calculate_worst_case_ms([budgets[f"S-B{i}"] for i in range(1, 11)])
    w2 += budgets["S-B3"].worst_case_ms + budgets["S-B4"].worst_case_ms
    w3 = calculate_worst_case_ms([budgets[f"S-E{i}"] for i in range(1, 8)])
    measured = (w1, w2, w3)
    design_worst = (609_300, 12_960_000, 58_000)
    total_budgets = (615_000, 14_400_000, 60_000)
    assert measured == design_worst
    assert all(
        value <= budget for value, budget in zip(measured, total_budgets, strict=True)
    )


def test_workflow_and_role_counts_match_design() -> None:
    deps, _ = dependencies()
    graphs = (
        build_customer_inquiry_graph(deps),
        build_knowledge_batch_graph(deps),
        build_consultation_closed_graph(deps),
    )
    expected = (
        {*(f"S-R{i}" for i in range(1, 11))},
        {*(f"S-B{i}" for i in range(1, 11))},
        {*(f"S-E{i}" for i in range(1, 8))},
    )
    for graph, stage_ids in zip(graphs, expected, strict=True):
        actual = set(graph.get_graph().nodes) - {"__start__", "__end__"}
        assert actual == stage_ids
    assert len(LlmGenerationRole.STAGES) == 8
    assert len(DeterministicRole.STAGES) == 13
    assert 8 + 13 + 1 + 2 + 2 + 1 == 27


def test_no_parallel_state_writers_are_defined() -> None:
    deps, _ = dependencies()
    for graph in (
        build_customer_inquiry_graph(deps),
        build_knowledge_batch_graph(deps),
        build_consultation_closed_graph(deps),
    ):
        drawable = graph.get_graph()
        outgoing: dict[str, list[str]] = {}
        for edge in drawable.edges:
            if not edge.conditional:
                outgoing.setdefault(edge.source, []).append(edge.target)
        assert all(len(set(targets)) <= 1 for targets in outgoing.values())
        assert not any(
            edge.source == "__start__" and edge.target == "__end__"
            for edge in drawable.edges
        )
