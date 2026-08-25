from help_desk_runtime.api_contracts import (
    ConsultationClosedRequest,
    ConsultationClosedResponse,
    CrmReviewDecisionRequest,
    CrmReviewDecisionResponse,
    FaqDecisionRequest,
    FaqDecisionResponse,
    InquiryRequest,
    InquiryResponse,
)


def test_process_api_keys_match_design() -> None:
    assert set(InquiryRequest.__annotations__) == {
        "request_id", "auth_session_ref", "inquiry_text", "channel",
    }
    assert set(InquiryResponse.__annotations__) == {
        "result_type", "answer", "handoff_ref", "request_status",
    }
    assert set(FaqDecisionRequest.__annotations__) == {
        "candidate_id", "decision", "reviewer_ref", "revised_candidate",
    }
    assert set(FaqDecisionResponse.__annotations__) == {
        "approval_id", "decision_status", "resume_stage",
    }
    assert set(ConsultationClosedRequest.__annotations__) == {
        "event_id", "consultation_ref", "ended_at", "transcript", "survey_consent_ref",
    }
    assert set(ConsultationClosedResponse.__annotations__) == {
        "accepted", "duplicate", "processing_ref",
    }
    assert set(CrmReviewDecisionRequest.__annotations__) == {
        "review_id", "decision", "reviewer_ref", "revised_summary",
    }
    assert set(CrmReviewDecisionResponse.__annotations__) == {
        "approval_id", "decision_status", "resume_stage",
    }
