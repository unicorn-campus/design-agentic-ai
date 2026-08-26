from __future__ import annotations

from typing import Any, NotRequired

from help_desk_runtime.api_contracts import (
    ConsultationClosedRequest,
    ConsultationClosedResponse,
)
from help_desk_runtime.checkpoint import build_thread_id
from help_desk_runtime.state import ConsultationClosedState
from help_desk_workflow.contracts import CrmReviewDecisionResult, WorkflowDependencies
from help_desk_workflow.engine import ensure_stage_or_land, stage_inputs, stage_result
from help_desk_workflow.roles import (
    ConsultationPostprocessor,
    DeterministicRole,
    LlmGenerationRole,
    SurveyConsentController,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

WORKFLOW_ID = "W-3"
RECURSION_LIMIT = 9


class ConsultationClosedGraphState(ConsultationClosedState, total=False):
    ended_at: NotRequired[Any]
    transcript: NotRequired[str]
    accepted: NotRequired[bool]
    duplicate: NotRequired[bool]
    processing_ref: NotRequired[str]
    approval_id: NotRequired[str]
    decision_status: NotRequired[str]
    resume_stage: NotRequired[str]
    _workflow: NotRequired[dict[str, Any]]


def build_consultation_closed_graph(
    deps: WorkflowDependencies, checkpointer: Any = None
) -> Any:
    llm = LlmGenerationRole(deps.model_invoke)
    deterministic = DeterministicRole(deps.operations)
    postprocessor = ConsultationPostprocessor(deps.approval_gate)
    consent = SurveyConsentController(deps.approval_gate)

    async def node_w3_s_e1_validate_event(
        state: ConsultationClosedGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-E1"):
            return landing
        raw = await deterministic.run(
            "S-E1",
            stage_inputs(
                state,
                "event_id",
                "consultation_ref",
                "ended_at",
                "transcript",
                "survey_consent_ref",
            ),
        )
        return stage_result(
            state,
            deps,
            WORKFLOW_ID,
            "S-E1",
            raw,
            (
                "event_id",
                "consultation_ref",
                "survey_consent_ref",
                "accepted",
                "duplicate",
                "processing_ref",
            ),
        )

    async def node_w3_s_e2_mask_transcript(
        state: ConsultationClosedGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-E2"):
            return landing
        raw = await deterministic.run(
            "S-E2", stage_inputs(state, "event_id", "consultation_ref", "transcript")
        )
        return stage_result(
            state, deps, WORKFLOW_ID, "S-E2", raw, ("masked_transcript",)
        )

    async def node_w3_s_e3_write_summary(
        state: ConsultationClosedGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-E3"):
            return landing
        raw = await llm.run("S-E3", stage_inputs(state, "masked_transcript"))
        return stage_result(state, deps, WORKFLOW_ID, "S-E3", raw, ("summary_draft",))

    async def node_w3_s_e4_calculate_risk(
        state: ConsultationClosedGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-E4"):
            return landing
        raw = await deterministic.run("S-E4", stage_inputs(state, "summary_draft"))
        return stage_result(state, deps, WORKFLOW_ID, "S-E4", raw, ("risk_result",))

    def node_w3_s_e5_review_crm(state: ConsultationClosedGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-E5"):
            return landing
        raw = postprocessor.review(
            stage_inputs(state, "event_id", "summary_draft", "risk_result")
        )
        result = CrmReviewDecisionResult.model_validate(raw)
        return stage_result(
            state,
            deps,
            WORKFLOW_ID,
            "S-E5",
            result.model_dump(exclude_none=True),
            ("approval_id", "decision_status", "resume_stage"),
        ) | {"review_decision": raw}

    async def node_w3_s_e6_save_crm(
        state: ConsultationClosedGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-E6"):
            return landing
        payload = postprocessor.crm_payload(state.get("review_decision", {}))
        raw = await deps.operations["S-E6"](
            {
                **payload,
                **stage_inputs(state, "event_id", "consultation_ref", "summary_draft"),
            }
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-E6", raw, ("crm_result",))

    async def node_w3_s_e7_send_survey(
        state: ConsultationClosedGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-E7"):
            return landing
        proof = consent.authorize(state.get("survey_consent_ref", ""))
        raw = await deps.operations["S-E7"](
            {
                **proof,
                **stage_inputs(
                    state,
                    "event_id",
                    "consultation_ref",
                    "survey_consent_ref",
                    "crm_result",
                ),
            }
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-E7", raw, ("survey_result",))

    def after_s_e1(state: ConsultationClosedGraphState) -> str:
        if state.get("_workflow", {}).get("flow_status") == "safe_stop":
            return "__end__"
        if state.get("duplicate") or not state.get("accepted"):
            return "__end__"
        return "S-E2"

    graph = StateGraph(ConsultationClosedGraphState)
    nodes = {
        "S-E1": node_w3_s_e1_validate_event,
        "S-E2": node_w3_s_e2_mask_transcript,
        "S-E3": node_w3_s_e3_write_summary,
        "S-E4": node_w3_s_e4_calculate_risk,
        "S-E5": node_w3_s_e5_review_crm,
        "S-E6": node_w3_s_e6_save_crm,
        "S-E7": node_w3_s_e7_send_survey,
    }
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.add_edge(START, "S-E1")
    graph.add_conditional_edges("S-E1", after_s_e1, {"S-E2": "S-E2", "__end__": END})
    for source, target in (
        ("S-E2", "S-E3"),
        ("S-E3", "S-E4"),
        ("S-E4", "S-E5"),
        ("S-E5", "S-E6"),
        ("S-E6", "S-E7"),
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
    graph.add_edge("S-E7", END)
    return graph.compile(checkpointer=checkpointer)


async def run_consultation_closed(
    graph: Any,
    request: ConsultationClosedRequest,
    job_type: str,
) -> ConsultationClosedResponse:
    thread_id = build_thread_id(
        WORKFLOW_ID, event_id=request["event_id"], job_type=job_type
    )
    result = await graph.ainvoke(
        dict(request),
        {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT},
    )
    if "accepted" not in result:
        return {
            "accepted": False,
            "duplicate": False,
            "processing_ref": request["event_id"],
        }
    return {
        "accepted": result["accepted"],
        "duplicate": result["duplicate"],
        "processing_ref": result["processing_ref"],
    }


async def resume_consultation_closed(
    graph: Any, thread_id: str, decision: dict[str, Any]
) -> dict[str, Any]:
    return await graph.ainvoke(
        Command(resume=decision),
        {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT},
    )


async def redefine_crm_review(
    graph: Any,
    thread_id: str,
    review_decision: dict[str, Any],
) -> None:
    await graph.aupdate_state(
        {"configurable": {"thread_id": thread_id}},
        {"review_decision": review_decision},
        as_node="S-E5",
    )
