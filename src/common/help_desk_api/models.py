from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InquiryBody(StrictBody):
    request_id: str = Field(min_length=1)
    auth_session_ref: str = Field(min_length=1)
    inquiry_text: str = Field(min_length=1)
    channel: str = Field(min_length=1)


class InquiryResumeBody(StrictBody):
    decision: str = Field(min_length=1)
    reviewer_ref: str = Field(min_length=1)
    revised_answer: dict[str, Any] | None = None


class FaqDecisionBody(StrictBody):
    decision: str = Field(min_length=1)
    reviewer_ref: str = Field(min_length=1)
    revised_candidate: dict[str, Any] | None = None


class ConsultationClosedBody(StrictBody):
    event_id: str = Field(min_length=1)
    consultation_ref: str = Field(min_length=1)
    ended_at: datetime
    transcript: str = Field(min_length=1)
    survey_consent_ref: str = Field(min_length=1)


class CrmReviewDecisionBody(StrictBody):
    decision: str = Field(min_length=1)
    reviewer_ref: str = Field(min_length=1)
    revised_summary: dict[str, Any] | None = None


class ErrorBody(StrictBody):
    code: str
    message: str


class HealthBody(StrictBody):
    status: Literal["ok", "not_ready"]
