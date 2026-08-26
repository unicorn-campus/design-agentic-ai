from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from help_desk_guardrails.approval import ApprovalGate
from help_desk_observability.telemetry import NodeTelemetryCallback
from help_desk_runtime.budget import RuntimeDeadline
from help_desk_runtime.model import ModelClientAdapter
from help_desk_runtime.settings import RuntimeSettings
from pydantic import BaseModel, ConfigDict

JsonObject = dict[str, Any]
AsyncOperation = Callable[[JsonObject], Awaitable[JsonObject]]


class StrictResult(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InquiryResult(StrictResult):
    result_type: str
    answer: JsonObject | None = None
    handoff_ref: str | None = None
    request_status: str


class FaqDecisionResult(StrictResult):
    approval_id: str | None = None
    decision_status: str
    resume_stage: str


class ConsultationClosedResult(StrictResult):
    accepted: bool
    duplicate: bool
    processing_ref: str


class CrmReviewDecisionResult(StrictResult):
    approval_id: str | None = None
    decision_status: str
    resume_stage: str


class RouteDecisionOutput(StrictResult):
    route_decision: Literal["handoff", "structured", "composite"]


class SqlCandidateOutput(StrictResult):
    sql_candidate: str


class EvidenceRefsOutput(StrictResult):
    evidence_refs: list[str]


class AnswerDraftOutput(StrictResult):
    answer_draft: JsonObject


class TopicEvidenceOutput(StrictResult):
    topic_evidence: list[JsonObject]


class FaqCandidatesOutput(StrictResult):
    faq_candidates: list[JsonObject]


class SummaryDraftOutput(StrictResult):
    summary_draft: JsonObject


class ModelInvoker(Protocol):
    async def __call__(
        self,
        stage_id: str,
        system_prompt: str,
        user_prompt: str,
    ) -> JsonObject: ...


class ModelAdapterInvoker:
    def __init__(self, adapter: ModelClientAdapter) -> None:
        self._adapter = adapter

    async def __call__(
        self,
        stage_id: str,
        system_prompt: str,
        user_prompt: str,
    ) -> JsonObject:
        model = self._adapter.create()
        messages = [("system", system_prompt), ("human", user_prompt)]
        if hasattr(model, "ainvoke"):
            response = await model.ainvoke(messages)
        else:
            response = model.invoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, dict):
            return content
        parsed = json.loads(str(content))
        if not isinstance(parsed, dict):
            raise TypeError(f"{stage_id} 모델 응답이 object가 아님")
        return parsed


@dataclass(frozen=True)
class WorkflowDependencies:
    settings: RuntimeSettings
    deadline: RuntimeDeadline
    operations: Mapping[str, AsyncOperation]
    model_invoke: ModelInvoker
    approval_gate: ApprovalGate
    telemetry: NodeTelemetryCallback | None = None
    max_iterations: Mapping[str, int] | None = None

    def max_iter(self, loop_id: str) -> int:
        if self.max_iterations is None or loop_id not in self.max_iterations:
            raise RuntimeError(f"01 런타임 반복 상한 설정 누락: {loop_id}")
        return self.max_iterations[loop_id]

    def ensure_time(self, stage_id: str) -> None:
        budget = self.settings.stage_budgets[stage_id]
        self.deadline.ensure_stage_can_start(budget.timeout_ms)

    def record(self, workflow_id: str, stage_id: str, values: JsonObject) -> None:
        if self.telemetry is not None:
            self.telemetry.on_node_end(workflow_id, stage_id, values)
