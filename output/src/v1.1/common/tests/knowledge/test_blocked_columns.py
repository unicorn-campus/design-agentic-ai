"""반드시 넣을 시험 1 — ⑤ 4절 「정형 접근 금지 컬럼」 전건에 대해 조회가 **실패**함.

가려서 통과되는 길이 없음을 함께 확인함(값을 읽어 놓고 별표로 바꾸는 함수가 0건임).
"""

from __future__ import annotations

import pytest

from common.dataset import spec_of
from common.knowledge.column_policy import (
    BLOCKED_COLUMNS,
    ColumnBlocked,
    assert_columns_allowed,
    blocked_columns_of_table,
)

# ⑤ 4절 `D-1` ~ `D-9` 9건 전건. 열 이름을 시험에 직접 적어 두어 표와 어긋나면 드러나게 함.
BLOCKED_CASES: tuple[tuple[str, str, str], ...] = (
    ("D-1", "member_profile", "email"),
    ("D-2", "member_profile", "kakao_id"),
    ("D-3", "member_profile", "push_token"),
    ("D-4", "diet_restriction", "allergy_free_text"),
    ("D-5", "location_history", "lat"),
    ("D-6", "location_history", "lng"),
    ("D-7", "audit_log", "*"),
    ("D-8", "subscription", "payment_id"),
    ("D-9", "accept_reject_log", "accept_latency_ms"),
)


def test_blocked_list_row_count_matches_design() -> None:
    """차단 목록 행 수가 ⑤ 4절 9건과 같음."""
    assert len(BLOCKED_COLUMNS) == len(BLOCKED_CASES)


@pytest.mark.parametrize(
    ("rule_id", "table", "column"), BLOCKED_CASES, ids=[case[0] for case in BLOCKED_CASES]
)
def test_blocked_column_makes_lookup_fail(rule_id: str, table: str, column: str) -> None:
    """시험 1 — 금지 열을 넣으면 조회를 만들다 말고 실패함."""
    with pytest.raises(ColumnBlocked) as caught:
        assert_columns_allowed("R-2", table, (column,))
    assert rule_id in str(caught.value)


def test_blocked_table_fails_even_without_naming_a_column() -> None:
    """`D-7`처럼 표 전체가 막힌 경우 열을 안 적어도 실패함."""
    with pytest.raises(ColumnBlocked):
        assert_columns_allowed("R-2", "audit_log", ())


def test_exception_agent_passes_only_for_its_own_rule() -> None:
    """`D-8` 예외는 해지 예약 처리기 1명뿐임. 다른 담당자는 그대로 막힘."""
    assert_columns_allowed("R-9", "subscription", ("payment_id",))
    with pytest.raises(ColumnBlocked):
        assert_columns_allowed("R-7", "subscription", ("payment_id",))


def test_exception_agent_still_blocked_on_other_rules() -> None:
    """예외 담당자라도 다른 금지 열은 그대로 막힘."""
    with pytest.raises(ColumnBlocked):
        assert_columns_allowed("R-9", "member_profile", ("email",))


def test_learning_batch_only_exception_on_behaviour_log() -> None:
    """`D-9`는 학습 배치만 예외임 — 요청 경로 담당자는 막힘."""
    assert_columns_allowed("R-3", "accept_reject_log", ("accept_latency_ms",))
    with pytest.raises(ColumnBlocked):
        assert_columns_allowed("R-2", "accept_reject_log", ("accept_latency_ms",))


@pytest.mark.parametrize(
    ("rule_id", "table", "column"), BLOCKED_CASES, ids=[case[0] for case in BLOCKED_CASES]
)
def test_blocked_column_is_not_in_any_path_spec_columns(
    rule_id: str, table: str, column: str
) -> None:
    """금지 열이 ⑤ 3절 경로 표의 열 목록에도 들어 있지 않음(읽어 올 자리 자체가 없음)."""
    from common.dataset import PATH_IDS

    for path_id in PATH_IDS:
        spec = spec_of(path_id)
        if spec.logical_table != table:
            continue
        assert column not in spec.columns, f"{path_id}에 {rule_id} 금지 열이 있음"


def test_no_masking_helper_exists() -> None:
    """금지 열을 조회한 뒤 가려서 내보내는 함수가 이 묶음에 0건임."""
    import common.knowledge as knowledge

    masking_like = [
        name
        for name in knowledge.__all__
        if any(word in name.lower() for word in ("mask", "redact", "star", "asterisk"))
    ]
    assert masking_like == []


def test_blocked_columns_of_table_narrows_for_exception_agent() -> None:
    for_r7 = blocked_columns_of_table("subscription", "R-7")
    for_r9 = blocked_columns_of_table("subscription", "R-9")
    assert [rule.rule_id for rule in for_r7] == ["D-8"]
    assert for_r9 == ()
