from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal, TypedDict


JsonObject = dict[str, Any]


def merge_mapping(left: JsonObject, right: JsonObject) -> JsonObject:
    return {**left, **right}


class InquiryState(TypedDict):
    request_id: str
    auth_session_ref: str
    customer_ref: str
    safe_inquiry_text: str
    route_decision: Literal["handoff", "structured", "composite"]
    sql_candidate: str
    evidence_refs: list[str]
    risk_result: JsonObject
    answer_draft: JsonObject
    approval_result: Annotated[JsonObject, merge_mapping]


class KnowledgeBatchState(TypedDict):
    batch_id: str
    batch_date: date
    masked_consultation_refs: list[str]
    sql_candidate: str
    topic_evidence: list[JsonObject]
    priority_result: list[JsonObject]
    faq_candidates: list[JsonObject]
    review_decision: Annotated[JsonObject, merge_mapping]
    registration_result: JsonObject


class ConsultationClosedState(TypedDict):
    event_id: str
    consultation_ref: str
    masked_transcript: str
    summary_draft: JsonObject
    risk_result: JsonObject
    review_decision: Annotated[JsonObject, merge_mapping]
    crm_result: JsonObject
    survey_consent_ref: str
    survey_result: JsonObject
