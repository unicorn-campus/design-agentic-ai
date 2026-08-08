"""상태 정의 시험. 반드시 넣을 시험 1번·2번이 여기 있음."""

from __future__ import annotations

import pytest

from common.state import (
    MERGED_FIELDS,
    SINGLE_WRITER_FIELDS,
    STATE_FIELDS,
    TRIGGER_FAMILY_BY_KIND,
    LunchPickState,
    PgCancelStatus,
    TriggerKind,
    merge_last_wins_by_key,
    reducer_of,
)

EXPECTED_FIELDS = (
    "trigger_kind",
    "deadline_at",
    "precheck_result",
    "partial_context",
    "context_bundle",
    "candidate_set",
    "recommendation_set",
    "verification_result",
    "fallback_reason",
    "retry_count_by_step",
    "iteration_count",
    "error_history",
    "resume_cursor",
    "preference_vector_ref",
    "subscription_state",
    "approval_evidence",
    "payment_idempotency_key",
    "payment_result",
    "cancel_schedule",
    "disclosure_record",
    "insight_aggregate",
    "consistency_check",
    "pg_cancel_status",
)


def test_field_count_matches_design() -> None:
    assert len(STATE_FIELDS) == 23
    assert STATE_FIELDS == EXPECTED_FIELDS


@pytest.mark.parametrize("field", sorted(SINGLE_WRITER_FIELDS))
def test_single_writer_fields_have_no_merge_rule(field: str) -> None:
    """시험 1 — 갱신 주체가 1명인 필드에 병합 규칙이 없음."""
    assert reducer_of(field) is None, f"{field}에 병합 규칙이 붙어 값이 쌓임"


def test_merge_rule_count_is_exactly_three() -> None:
    attached = {name for name in STATE_FIELDS if reducer_of(name) is not None}
    assert attached == MERGED_FIELDS
    assert MERGED_FIELDS == {"partial_context", "retry_count_by_step", "error_history"}


@pytest.mark.parametrize("field", ["partial_context", "error_history"])
def test_list_merge_keeps_both_writes(field: str) -> None:
    """시험 2 — 갱신 주체가 2명 이상인 목록 필드에 두 번 넣으면 둘 다 남음."""
    reducer = reducer_of(field)
    assert reducer is not None
    merged = reducer([{"from": "first"}], [{"from": "second"}])
    assert merged == [{"from": "first"}, {"from": "second"}]


def test_dict_merge_keeps_both_keys_and_prefers_later_value() -> None:
    """시험 2 — 값형은 나중 값이 이기고 다른 키는 둘 다 남음."""
    reducer = reducer_of("retry_count_by_step")
    assert reducer is merge_last_wins_by_key
    merged = reducer({"S-R4": 1}, {"S-R6": 1})
    assert merged == {"S-R4": 1, "S-R6": 1}
    assert reducer({"S-R4": 1}, {"S-R4": 2}) == {"S-R4": 2}


def test_merge_handles_missing_side() -> None:
    assert merge_last_wins_by_key(None, {"S-R4": 1}) == {"S-R4": 1}
    assert merge_last_wins_by_key({"S-R4": 1}, None) == {"S-R4": 1}


def test_pg_cancel_status_values_match_design() -> None:
    assert {member.value for member in PgCancelStatus} == {"중지완료", "확인 중", "실패"}


def test_every_trigger_kind_has_a_family() -> None:
    assert set(TRIGGER_FAMILY_BY_KIND) == set(TriggerKind)


def test_state_accepts_partial_updates() -> None:
    state: LunchPickState = {"trigger_kind": TriggerKind.SYNC_RECOMMEND}
    assert state["trigger_kind"] is TriggerKind.SYNC_RECOMMEND
