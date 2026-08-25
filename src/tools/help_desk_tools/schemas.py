from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LlmRequest(ContractModel):
    model: str
    input: list[dict[str, Any]]
    max_output_tokens: int


class LlmUsage(ContractModel):
    total_tokens: int


class LlmResponse(ContractModel):
    id: str
    output_text: str
    usage: LlmUsage


class AnalyticsRequest(ContractModel):
    statement: str
    parameters: dict[str, Any]
    max_rows: int


class AnalyticsResponse(ContractModel):
    query_id: str
    rows: list[dict[str, Any]]
    row_count: int


class SearchRequest(ContractModel):
    query: str
    source_type: Literal["web", "video"]
    period_days: int
    sort: str
    max_results: int
    include_content: bool | None = None
    include_transcript: bool | None = None


class SearchResult(ContractModel):
    title: str
    url: str
    retrieved_at: str
    content_excerpt: str | None = None
    transcript_range: str | None = None


class SearchResponse(ContractModel):
    results: list[SearchResult]


class CrmRequest(ContractModel):
    consultation_ref: str
    approval_id: str
    summary: dict[str, Any]
    idempotency_key: str


class CrmResponse(ContractModel):
    record_id: str
    status: str


class SurveyRequest(ContractModel):
    customer_ref: str
    consultation_ref: str
    consent_ref: str
    idempotency_key: str


class SurveyResponse(ContractModel):
    send_id: str
    status: str


class ApprovalProof(ContractModel):
    approval_id: str
    approver_role: str
    subject: Literal["S-E6", "S-E7"]


class ToolDefinition(ContractModel):
    name: str
    side_effect: Literal["읽기", "쓰기(되돌림 가능)", "쓰기(되돌림 불가)"]
    use_when: str
    connector_id: str
    approval_required: bool
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
