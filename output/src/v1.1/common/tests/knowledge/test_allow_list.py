"""반드시 넣을 시험 2 — ④ 「접근 가능한 정보 항목」에 없는 열을 넣으면 **거부**됨.

허용 목록이 없는 담당자·경로 짝은 **비운 채로 열지 않음**도 함께 확인함.
"""

from __future__ import annotations

import pytest

from common.config import Settings
from common.dataset import PATH_IDS, spec_of
from common.knowledge import lookup
from common.knowledge.column_policy import (
    AGENT_ALLOWED_COLUMNS,
    UNASSIGNED_PATHS,
    AllowListMissing,
    ColumnNotAllowed,
    allowed_columns_for,
    resolve_columns,
)


def test_allow_list_columns_all_exist_in_path_spec() -> None:
    """허용 목록의 열 이름이 ⑤ 3절 경로 표에 실제로 있는 이름임."""
    unknown: list[str] = []
    for agent_id, by_path in AGENT_ALLOWED_COLUMNS.items():
        for path_id, columns in by_path.items():
            spec = spec_of(path_id)
            for column in columns:
                if column not in spec.columns:
                    unknown.append(f"{agent_id}·{path_id}·{column}")
    assert unknown == [], f"⑤ 3절 열 목록에 없는 이름임: {unknown}"


def test_column_outside_allow_list_is_refused() -> None:
    """시험 2 — 허용 목록 밖 열을 지목하면 거부됨."""
    with pytest.raises(ColumnNotAllowed):
        resolve_columns("R-14", "T-1", "member_profile", spec_of("T-1").columns, ("nickname",))


def test_column_inside_allow_list_passes() -> None:
    columns = resolve_columns(
        "R-14", "T-1", "member_profile", spec_of("T-1").columns, ("subscription_state",)
    )
    assert columns == ("subscription_state",)


def test_default_columns_are_the_intersection_of_allow_list_and_path() -> None:
    columns = resolve_columns("R-14", "T-1", "member_profile", spec_of("T-1").columns)
    assert columns == ("member_id", "subscription_state")
    assert "nickname" not in columns


def test_unknown_column_name_is_refused_even_if_allowed_elsewhere() -> None:
    with pytest.raises(ColumnNotAllowed):
        resolve_columns(
            "R-14", "T-1", "member_profile", spec_of("T-1").columns, ("no_such_column",)
        )


def test_agent_without_any_lookup_path_cannot_open() -> None:
    """④가 「정형 조회 경로 0건」으로 적은 담당자는 허용 목록이 없어 못 엶."""
    with pytest.raises(AllowListMissing):
        allowed_columns_for("R-1", "T-1")


@pytest.mark.parametrize("path_id", sorted(UNASSIGNED_PATHS), ids=sorted(UNASSIGNED_PATHS))
def test_unassigned_path_refuses_to_open(path_id: str) -> None:
    """④에 허용 열이 없는 경로는 비운 채로 열지 않고 사유와 함께 실패함."""
    with pytest.raises(AllowListMissing) as caught:
        allowed_columns_for("R-14", path_id)
    assert "확인필요" in str(caught.value)


def test_assigned_and_unassigned_paths_cover_all_rows() -> None:
    """배정된 경로와 미배정 경로를 합치면 ⑤ 3절 18행이 됨."""
    assigned = {
        path_id for by_path in AGENT_ALLOWED_COLUMNS.values() for path_id in by_path
    }
    assert assigned.isdisjoint(UNASSIGNED_PATHS)
    assert assigned | set(UNASSIGNED_PATHS) == set(PATH_IDS)


def test_lookup_projects_result_to_allowed_columns_only(
    knowledge_settings: Settings, seed_reader
) -> None:
    """결과에도 허용 목록 밖 열이 남지 않음."""
    result = lookup("T-1", "R-14", seed_reader, params={"member_id": "M000000"},
                    settings=knowledge_settings)
    assert not result.is_empty
    for payload in result.payloads():
        assert set(payload) <= {"member_id", "subscription_state"}


def test_lookup_does_not_call_reader_when_column_is_refused(
    knowledge_settings: Settings, seed_reader
) -> None:
    """거부되면 읽기 함수를 **부르지 않음**."""
    before = dict(seed_reader.notes_by_path)
    with pytest.raises(ColumnNotAllowed):
        lookup("T-1", "R-14", seed_reader, columns=("nickname",), settings=knowledge_settings)
    assert seed_reader.notes_by_path == before
