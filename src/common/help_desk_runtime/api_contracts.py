from __future__ import annotations

from datetime import datetime
from typing import Any, NotRequired, TypedDict


JsonObject = dict[str, Any]


class InquiryRequest(TypedDict):
    request_id: str
    auth_session_ref: str
    inquiry_text: str
    channel: str


class InquiryResponse(TypedDict):
    result_type: str
    answer: NotRequired[JsonObject]
    handoff_ref: NotRequired[str]
    request_status: str


class FaqDecisionRequest(TypedDict):
    candidate_id: str
    decision: str
    reviewer_ref: str
    revised_candidate: NotRequired[JsonObject]


class FaqDecisionResponse(TypedDict):
    approval_id: NotRequired[str]
    decision_status: str
    resume_stage: str


class ConsultationClosedRequest(TypedDict):
    event_id: str
    consultation_ref: str
    ended_at: datetime
    transcript: str
    survey_consent_ref: str


class ConsultationClosedResponse(TypedDict):
    accepted: bool
    duplicate: bool
    processing_ref: str


class CrmReviewDecisionRequest(TypedDict):
    review_id: str
    decision: str
    reviewer_ref: str
    revised_summary: NotRequired[JsonObject]


class CrmReviewDecisionResponse(TypedDict):
    approval_id: NotRequired[str]
    decision_status: str
    resume_stage: str
