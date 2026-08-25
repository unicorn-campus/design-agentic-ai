from typing import get_args, get_origin, get_type_hints, Annotated

from help_desk_runtime.state import (
    ConsultationClosedState,
    InquiryState,
    KnowledgeBatchState,
    merge_mapping,
)


def _has_reducer(field_type: object) -> bool:
    return get_origin(field_type) is Annotated and len(get_args(field_type)) > 1


def test_single_writer_fields_have_no_reducer() -> None:
    for state_type, reducer_fields in (
        (InquiryState, {"approval_result"}),
        (KnowledgeBatchState, {"review_decision"}),
        (ConsultationClosedState, {"review_decision"}),
    ):
        hints = get_type_hints(state_type, include_extras=True)
        assert all(not _has_reducer(value) for key, value in hints.items() if key not in reducer_fields)


def test_multiple_writer_mapping_keeps_both_updates() -> None:
    assert merge_mapping({"reviewer": "human"}, {"decision": "approved"}) == {
        "reviewer": "human",
        "decision": "approved",
    }


def test_state_field_counts_match_design() -> None:
    assert len(InquiryState.__annotations__) == 10
    assert len(KnowledgeBatchState.__annotations__) == 9
    assert len(ConsultationClosedState.__annotations__) == 9
