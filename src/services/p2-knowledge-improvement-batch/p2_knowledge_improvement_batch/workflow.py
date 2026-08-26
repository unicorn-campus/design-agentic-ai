from __future__ import annotations

from datetime import date
from typing import Any, NotRequired

from help_desk_runtime.checkpoint import build_thread_id
from help_desk_runtime.state import KnowledgeBatchState
from help_desk_workflow.contracts import FaqDecisionResult, WorkflowDependencies
from help_desk_workflow.engine import (
    ensure_stage_or_land,
    set_control,
    stage_data,
    stage_inputs,
    stage_result,
)
from help_desk_workflow.roles import (
    DeterministicRole,
    FaqCandidateReviewer,
    LlmGenerationRole,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

WORKFLOW_ID = "W-2"
RECURSION_LIMIT = 24


class KnowledgeBatchGraphState(KnowledgeBatchState, total=False):
    data_version: NotRequired[str]
    decision_status: NotRequired[str]
    approval_id: NotRequired[str]
    resume_stage: NotRequired[str]
    _workflow: NotRequired[dict[str, Any]]


def build_knowledge_batch_graph(
    deps: WorkflowDependencies, checkpointer: Any = None
) -> Any:
    llm = LlmGenerationRole(deps.model_invoke)
    deterministic = DeterministicRole(deps.operations)
    human = FaqCandidateReviewer(deps.approval_gate)

    async def node_w2_s_b1_start_batch(
        state: KnowledgeBatchGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B1"):
            return landing
        raw = await deterministic.run(
            "S-B1", stage_inputs(state, "batch_id", "batch_date", "data_version")
        )
        return stage_result(
            state, deps, WORKFLOW_ID, "S-B1", raw, ("batch_id", "batch_date")
        )

    async def node_w2_s_b2_load_consultations(
        state: KnowledgeBatchGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B2"):
            return landing
        raw = await deterministic.run(
            "S-B2", stage_inputs(state, "batch_id", "batch_date")
        )
        return stage_result(
            state, deps, WORKFLOW_ID, "S-B2", raw, ("masked_consultation_refs",)
        )

    async def node_w2_s_b3_write_sql(state: KnowledgeBatchGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B3"):
            return landing
        raw = await llm.run(
            "S-B3", stage_inputs(state, "batch_date", "masked_consultation_refs")
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-B3", raw, ("sql_candidate",))

    async def node_w2_s_b4_validate_query(
        state: KnowledgeBatchGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B4"):
            return landing
        try:
            raw = await deterministic.run("S-B4", stage_inputs(state, "sql_candidate"))
        except (RuntimeError, TypeError, ValueError) as error:
            count = int(state.get("_workflow", {}).get("r2_iter", 0)) + 1
            return set_control(state, r2_iter=count, r2_error=type(error).__name__)
        result = stage_result(state, deps, WORKFLOW_ID, "S-B4", raw, ())
        control = dict(result["_workflow"])
        control.pop("r2_error", None)
        result["_workflow"] = control
        return result

    async def node_w2_s_b5_extract_topics(
        state: KnowledgeBatchGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B5"):
            return landing
        control = state.get("_workflow", {})
        if control.get("r2_error") and int(control.get("r2_iter", 0)) > deps.max_iter(
            "R-2"
        ):
            result = stage_result(
                state,
                deps,
                WORKFLOW_ID,
                "S-B5",
                {"topic_evidence": []},
                ("topic_evidence",),
            )
            result["_workflow"] = {
                **result["_workflow"],
                "flow_status": "safe_stop",
                "landing_reason": "R-2:max_iter_exhausted",
            }
            return result
        raw = await llm.run(
            "S-B5",
            {
                **stage_inputs(state, "masked_consultation_refs"),
                "statistics": stage_data(state, "S-B4"),
            },
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-B5", raw, ("topic_evidence",))

    async def node_w2_s_b6_verify_external(
        state: KnowledgeBatchGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B6"):
            return landing
        raw = await deterministic.run("S-B6", stage_inputs(state, "topic_evidence"))
        return stage_result(state, deps, WORKFLOW_ID, "S-B6", raw, ())

    async def node_w2_s_b7_rank_priority(
        state: KnowledgeBatchGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B7"):
            return landing
        raw = await deterministic.run("S-B7", stage_inputs(state, "topic_evidence"))
        return stage_result(state, deps, WORKFLOW_ID, "S-B7", raw, ("priority_result",))

    async def node_w2_s_b8_write_faq(state: KnowledgeBatchGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B8"):
            return landing
        raw = await llm.run(
            "S-B8",
            {
                **stage_inputs(state, "topic_evidence", "priority_result"),
                "external_evidence": stage_data(state, "S-B6"),
            },
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-B8", raw, ("faq_candidates",))

    def node_w2_s_b9_review_faq(state: KnowledgeBatchGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B9"):
            return landing
        raw = human.review(
            stage_inputs(state, "batch_id", "faq_candidates", "priority_result")
        )
        result = FaqDecisionResult.model_validate(raw)
        return stage_result(
            state,
            deps,
            WORKFLOW_ID,
            "S-B9",
            result.model_dump(exclude_none=True),
            ("review_decision", "approval_id", "decision_status", "resume_stage"),
        ) | {"review_decision": raw}

    async def node_w2_s_b10_register_faq(
        state: KnowledgeBatchGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-B10"):
            return landing
        payload = human.registration_payload(state.get("review_decision", {}))
        raw = await deps.operations["S-B10"](
            {**payload, **stage_inputs(state, "batch_id", "faq_candidates")}
        )
        return stage_result(
            state, deps, WORKFLOW_ID, "S-B10", raw, ("registration_result",)
        )

    def after_s_b4(state: KnowledgeBatchGraphState) -> str:
        if state.get("_workflow", {}).get("flow_status") == "safe_stop":
            return "__end__"
        count = int(state.get("_workflow", {}).get("r2_iter", 0))
        if state.get("_workflow", {}).get("r2_error") and count <= deps.max_iter("R-2"):
            return "S-B3"
        return "S-B5"

    graph = StateGraph(KnowledgeBatchGraphState)
    nodes = {
        "S-B1": node_w2_s_b1_start_batch,
        "S-B2": node_w2_s_b2_load_consultations,
        "S-B3": node_w2_s_b3_write_sql,
        "S-B4": node_w2_s_b4_validate_query,
        "S-B5": node_w2_s_b5_extract_topics,
        "S-B6": node_w2_s_b6_verify_external,
        "S-B7": node_w2_s_b7_rank_priority,
        "S-B8": node_w2_s_b8_write_faq,
        "S-B9": node_w2_s_b9_review_faq,
        "S-B10": node_w2_s_b10_register_faq,
    }
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.add_edge(START, "S-B1")
    for source, target in (
        ("S-B1", "S-B2"),
        ("S-B2", "S-B3"),
        ("S-B3", "S-B4"),
        ("S-B5", "S-B6"),
        ("S-B6", "S-B7"),
        ("S-B7", "S-B8"),
        ("S-B8", "S-B9"),
        ("S-B9", "S-B10"),
    ):
        graph.add_conditional_edges(
            source,
            lambda state, target=target: (
                "__end__"
                if state.get("_workflow", {}).get("flow_status") == "safe_stop"
                else target
            ),
            {target: target, "__end__": END},
        )
    graph.add_conditional_edges(
        "S-B4", after_s_b4, {"S-B3": "S-B3", "S-B5": "S-B5", "__end__": END}
    )
    graph.add_edge("S-B10", END)
    return graph.compile(checkpointer=checkpointer)


async def run_knowledge_batch(
    graph: Any,
    batch_id: str,
    batch_date: date,
    data_version: str,
) -> dict[str, Any]:
    thread_id = build_thread_id(
        WORKFLOW_ID, batch_date=batch_date, data_version=data_version
    )
    return await graph.ainvoke(
        {"batch_id": batch_id, "batch_date": batch_date, "data_version": data_version},
        {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT},
    )


async def resume_knowledge_batch(
    graph: Any, thread_id: str, decision: dict[str, Any]
) -> dict[str, Any]:
    return await graph.ainvoke(
        Command(resume=decision),
        {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT},
    )


async def redefine_faq_decision(
    graph: Any,
    thread_id: str,
    review_decision: dict[str, Any],
) -> None:
    await graph.aupdate_state(
        {"configurable": {"thread_id": thread_id}},
        {"review_decision": review_decision},
        as_node="S-B9",
    )
