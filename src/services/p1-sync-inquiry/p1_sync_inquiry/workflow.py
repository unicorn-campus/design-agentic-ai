from __future__ import annotations

from typing import Any, NotRequired

from help_desk_runtime.api_contracts import InquiryRequest, InquiryResponse
from help_desk_runtime.checkpoint import build_thread_id
from help_desk_runtime.state import InquiryState
from help_desk_workflow.contracts import WorkflowDependencies
from help_desk_workflow.engine import (
    ensure_stage_or_land,
    set_control,
    stage_data,
    stage_inputs,
    stage_result,
)
from help_desk_workflow.roles import (
    CustomerAnswerApprover,
    DeterministicRole,
    LlmGenerationRole,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

WORKFLOW_ID = "W-1"
RECURSION_LIMIT = 24


class InquiryGraphState(InquiryState, total=False):
    inquiry_text: NotRequired[str]
    channel: NotRequired[str]
    result_type: NotRequired[str]
    answer: NotRequired[dict[str, Any]]
    handoff_ref: NotRequired[str]
    request_status: NotRequired[str]
    _workflow: NotRequired[dict[str, Any]]


def build_customer_inquiry_graph(
    deps: WorkflowDependencies, checkpointer: Any = None
) -> Any:
    llm = LlmGenerationRole(deps.model_invoke)
    deterministic = DeterministicRole(deps.operations)
    human = CustomerAnswerApprover(deps.approval_gate)

    async def node_w1_s_r1_input_gate(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R1"):
            return landing
        raw = await deterministic.run(
            "S-R1",
            stage_inputs(
                state, "request_id", "auth_session_ref", "inquiry_text", "channel"
            ),
        )
        return stage_result(
            state,
            deps,
            WORKFLOW_ID,
            "S-R1",
            raw,
            ("request_id", "auth_session_ref", "customer_ref", "safe_inquiry_text"),
        )

    async def node_w1_s_r2_route_inquiry(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R2"):
            return landing
        raw = await llm.run(
            "S-R2", stage_inputs(state, "request_id", "safe_inquiry_text")
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-R2", raw, ("route_decision",))

    async def node_w1_s_r3_write_sql(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R3"):
            return landing
        raw = await llm.run("S-R3", stage_inputs(state, "safe_inquiry_text"))
        return stage_result(state, deps, WORKFLOW_ID, "S-R3", raw, ("sql_candidate",))

    async def node_w1_s_r4_validate_query(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R4"):
            return landing
        try:
            raw = await deterministic.run("S-R4", stage_inputs(state, "sql_candidate"))
        except (RuntimeError, TypeError, ValueError) as error:
            control = dict(state.get("_workflow", {}))
            count = int(control.get("r1_iter", 0)) + 1
            return set_control(state, r1_iter=count, r1_error=type(error).__name__)
        result = stage_result(state, deps, WORKFLOW_ID, "S-R4", raw, ())
        control = dict(result["_workflow"])
        control.pop("r1_error", None)
        result["_workflow"] = control
        return result

    async def node_w1_s_r5_internal_evidence(
        state: InquiryGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R5"):
            return landing
        control = state.get("_workflow", {})
        if control.get("r1_error") and int(control.get("r1_iter", 0)) > deps.max_iter(
            "R-1"
        ):
            result = stage_result(
                state,
                deps,
                WORKFLOW_ID,
                "S-R5",
                {"evidence_refs": []},
                ("evidence_refs",),
            )
            result["_workflow"] = {
                **result["_workflow"],
                "flow_status": "safe_stop",
                "landing_reason": "R-1:max_iter_exhausted",
            }
            return result
        raw = await llm.run(
            "S-R5",
            {
                **stage_inputs(state, "safe_inquiry_text"),
                "query_result": stage_data(state, "S-R4"),
            },
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-R5", raw, ("evidence_refs",))

    async def node_w1_s_r6_external_evidence(
        state: InquiryGraphState,
    ) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R6"):
            return landing
        raw = await deterministic.run(
            "S-R6", stage_inputs(state, "safe_inquiry_text", "evidence_refs")
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-R6", raw, ())

    async def node_w1_s_r7_risk_route(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R7"):
            return landing
        raw = await deterministic.run(
            "S-R7", stage_inputs(state, "customer_ref", "evidence_refs")
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-R7", raw, ("risk_result",))

    async def node_w1_s_r8_answer_draft(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R8"):
            return landing
        raw = await llm.run(
            "S-R8",
            {
                **stage_inputs(
                    state, "safe_inquiry_text", "evidence_refs", "risk_result"
                ),
                "external_evidence": stage_data(state, "S-R6"),
            },
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-R8", raw, ("answer_draft",))

    def node_w1_s_r9_human_approval(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R9"):
            return landing
        raw = human.review(
            stage_inputs(
                state, "request_id", "evidence_refs", "risk_result", "answer_draft"
            )
        )
        return stage_result(state, deps, WORKFLOW_ID, "S-R9", raw, ("approval_result",))

    async def node_w1_s_r10_deliver_answer(state: InquiryGraphState) -> dict[str, Any]:
        if landing := ensure_stage_or_land(state, deps, "S-R10"):
            return {**landing, "result_type": "safe_stop", "request_status": "failed"}
        raw = await deterministic.run(
            "S-R10",
            stage_inputs(state, "request_id", "answer_draft", "approval_result"),
        )
        return stage_result(
            state,
            deps,
            WORKFLOW_ID,
            "S-R10",
            raw,
            ("result_type", "answer", "handoff_ref", "request_status"),
        )

    def after_s_r2(state: InquiryGraphState) -> str:
        if state.get("_workflow", {}).get("flow_status") == "safe_stop":
            return "__end__"
        if state.get("route_decision") == "handoff":
            return "S-R9"
        return "S-R3"

    def after_s_r4(state: InquiryGraphState) -> str:
        if state.get("_workflow", {}).get("flow_status") == "safe_stop":
            return "__end__"
        count = int(state.get("_workflow", {}).get("r1_iter", 0))
        if state.get("_workflow", {}).get("r1_error") and count <= deps.max_iter("R-1"):
            return "S-R3"
        if state.get("route_decision") == "structured" and not state.get(
            "_workflow", {}
        ).get("r1_error"):
            return "S-R7"
        return "S-R5"

    def after_s_r8(state: InquiryGraphState) -> str:
        if state.get("_workflow", {}).get("flow_status") == "safe_stop":
            return "__end__"
        risk = state.get("risk_result", {})
        return (
            "S-R9"
            if risk.get("level") == "high" or not state.get("evidence_refs")
            else "S-R10"
        )

    graph = StateGraph(InquiryGraphState)
    nodes = {
        "S-R1": node_w1_s_r1_input_gate,
        "S-R2": node_w1_s_r2_route_inquiry,
        "S-R3": node_w1_s_r3_write_sql,
        "S-R4": node_w1_s_r4_validate_query,
        "S-R5": node_w1_s_r5_internal_evidence,
        "S-R6": node_w1_s_r6_external_evidence,
        "S-R7": node_w1_s_r7_risk_route,
        "S-R8": node_w1_s_r8_answer_draft,
        "S-R9": node_w1_s_r9_human_approval,
        "S-R10": node_w1_s_r10_deliver_answer,
    }
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.add_edge(START, "S-R1")
    graph.add_conditional_edges(
        "S-R1",
        lambda state: (
            "__end__"
            if state.get("_workflow", {}).get("flow_status") == "safe_stop"
            else "S-R2"
        ),
        {"S-R2": "S-R2", "__end__": END},
    )
    graph.add_conditional_edges(
        "S-R2", after_s_r2, {"S-R3": "S-R3", "S-R9": "S-R9", "__end__": END}
    )
    graph.add_conditional_edges(
        "S-R3",
        lambda state: (
            "__end__"
            if state.get("_workflow", {}).get("flow_status") == "safe_stop"
            else "S-R4"
        ),
        {"S-R4": "S-R4", "__end__": END},
    )
    graph.add_conditional_edges(
        "S-R4",
        after_s_r4,
        {"S-R3": "S-R3", "S-R5": "S-R5", "S-R7": "S-R7", "__end__": END},
    )
    for source, target in (
        ("S-R5", "S-R6"),
        ("S-R6", "S-R7"),
        ("S-R7", "S-R8"),
        ("S-R9", "S-R10"),
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
        "S-R8", after_s_r8, {"S-R9": "S-R9", "S-R10": "S-R10", "__end__": END}
    )
    graph.add_edge("S-R10", END)
    return graph.compile(checkpointer=checkpointer)


async def run_customer_inquiry(
    graph: Any,
    request: InquiryRequest,
    customer_ref: str,
) -> InquiryResponse:
    thread_id = build_thread_id(
        WORKFLOW_ID,
        customer_ref=customer_ref,
        request_id=request["request_id"],
    )
    result = await graph.ainvoke(
        dict(request),
        {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT},
    )
    if "__interrupt__" in result:
        # S-R9에서 사람 승인을 기다리는 중임. 안전 종료와 구분해서 알림.
        return {"result_type": "pending_approval", "request_status": "pending"}
    if "request_status" not in result:
        return {
            "result_type": "safe_stop",
            "handoff_ref": request["request_id"],
            "request_status": "failed",
        }
    return {
        key: result[key]
        for key in ("result_type", "answer", "handoff_ref", "request_status")
        if key in result
    }


async def resume_customer_inquiry(
    graph: Any, thread_id: str, approval: dict[str, Any]
) -> InquiryResponse:
    result = await graph.ainvoke(
        Command(resume=approval),
        {"configurable": {"thread_id": thread_id}, "recursion_limit": RECURSION_LIMIT},
    )
    return {
        key: result[key]
        for key in ("result_type", "answer", "handoff_ref", "request_status")
        if key in result
    }


async def cancel_customer_inquiry(graph: Any, thread_id: str, reason: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await graph.aget_state(config)
    control = dict(snapshot.values.get("_workflow", {}))
    control.update(
        {"flow_status": "safe_stop", "landing_reason": f"S-R9:cancelled:{reason}"}
    )
    await graph.aupdate_state(
        config,
        {
            "approval_result": {"decision": "중단", "reason": reason},
            "_workflow": control,
        },
        as_node="S-R9",
    )


async def redefine_customer_answer(
    graph: Any,
    thread_id: str,
    approval_result: dict[str, Any],
) -> None:
    await graph.aupdate_state(
        {"configurable": {"thread_id": thread_id}},
        {"approval_result": approval_result},
        as_node="S-R9",
    )
