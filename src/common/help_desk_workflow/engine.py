from __future__ import annotations

from typing import Any

from help_desk_runtime.budget import DeadlineExceeded

from .contracts import JsonObject, WorkflowDependencies


def stage_result(
    state: dict[str, Any],
    deps: WorkflowDependencies,
    workflow_id: str,
    stage_id: str,
    raw: JsonObject,
    state_keys: tuple[str, ...],
) -> JsonObject:
    control = dict(state.get("_workflow", {}))
    stage_results = dict(control.get("stage_results", {}))
    stage_results[stage_id] = raw
    completed = list(control.get("completed_stages", []))
    if stage_id not in completed:
        completed.append(stage_id)
    control.update({"stage_results": stage_results, "completed_stages": completed})
    updates = {key: raw[key] for key in state_keys if key in raw}
    updates["_workflow"] = control
    deps.record(workflow_id, stage_id, {**state, **updates})
    return updates


def stage_inputs(state: dict[str, Any], *keys: str) -> JsonObject:
    return {key: state[key] for key in keys if key in state}


def stage_data(state: dict[str, Any], stage_id: str) -> JsonObject:
    return dict(state.get("_workflow", {}).get("stage_results", {}).get(stage_id, {}))


def set_control(state: dict[str, Any], **values: Any) -> JsonObject:
    control = dict(state.get("_workflow", {}))
    control.update(values)
    return {"_workflow": control}


def completed(state: dict[str, Any], stage_id: str) -> bool:
    return stage_id in state.get("_workflow", {}).get("completed_stages", [])


def ensure_stage_or_land(
    state: dict[str, Any],
    deps: WorkflowDependencies,
    stage_id: str,
) -> JsonObject | None:
    try:
        deps.ensure_time(stage_id)
    except DeadlineExceeded:
        result = set_control(
            state,
            landing_reason=f"{stage_id}:deadline_insufficient",
            flow_status="safe_stop",
        )
        workflow_id = {"R": "W-1", "B": "W-2", "E": "W-3"}[stage_id[2]]
        deps.record(workflow_id, stage_id, {**state, **result})
        return result
    return None


def next_unless_landed(state: dict[str, Any], next_node: str) -> str:
    if state.get("_workflow", {}).get("flow_status") == "safe_stop":
        return "__end__"
    return next_node
