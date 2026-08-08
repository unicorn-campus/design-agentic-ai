"""필수 시험 3 — 병렬 노드가 **같은 상태 필드를 덮어쓰지 않음.**

겹치면 하나가 사라지므로 코드로 우회하지 않고 ③에 `변경요청`을 남기게 되어 있음.
이 시험은 실제로 병렬 갈래를 돌려 상태 업데이트 열쇠를 모아 봄.
"""

from __future__ import annotations

import pytest

from common.state import MERGED_FIELDS, SINGLE_WRITER_FIELDS

from services.flow import graphs
from services.flow.steps import PARALLEL_GROUPS


@pytest.mark.parametrize("group", sorted(PARALLEL_GROUPS))
async def test_parallel_nodes_share_no_single_writer_field(group, make_context) -> None:
    context = make_context(
        inputs={"origin_lat": 37.5, "origin_lng": 127.0},
        sources={"meal_history": [], "preference_vector": {"preference_vector_ref": "v1"}},
    )
    written: dict[str, set[str]] = {}
    for step_id in PARALLEL_GROUPS[group]:
        update = await graphs.NODE_FUNCTIONS[step_id]({"deadline_at": _far_future()}, context)
        written[step_id] = set(update)

    for field in SINGLE_WRITER_FIELDS:
        writers = [step for step, keys in written.items() if field in keys]
        assert len(writers) <= 1, f"{field}를 병렬 노드 {writers}가 함께 씀"


@pytest.mark.parametrize("group", sorted(PARALLEL_GROUPS))
async def test_parallel_nodes_only_write_merged_fields(group, make_context) -> None:
    """병렬 노드가 쓰는 필드는 전부 ③ 6절이 병합 규칙을 붙인 필드여야 함."""
    context = make_context(
        inputs={"origin_lat": 37.5, "origin_lng": 127.0},
        sources={"meal_history": [], "preference_vector": {"preference_vector_ref": "v1"}},
    )
    for step_id in PARALLEL_GROUPS[group]:
        update = await graphs.NODE_FUNCTIONS[step_id]({"deadline_at": _far_future()}, context)
        assert set(update) <= MERGED_FIELDS, f"{step_id}가 단독 갱신 필드를 씀: {set(update)}"


async def test_join_node_marks_the_missing_branch(make_context) -> None:
    """합류 규칙(되묻기 2) — **즉시 진행 + 빠진 값을 결과에 표기.**"""
    context = make_context(
        inputs={"origin_lat": 37.5, "origin_lng": 127.0},
        sources={"meal_history": None},
    )
    state = {
        "deadline_at": _far_future(),
        "partial_context": [
            {"step_id": "S-R4", "collect_errors": ["S-R4"]},
            {"step_id": "S-R7", "ok": True, "nearby_restaurants": [{"place_id": "p1"}]},
        ],
    }
    update = await graphs.NODE_FUNCTIONS["S-R8"](state, context)
    fragment = update["partial_context"][0]
    assert fragment["collect_errors"] == ["S-R4"]


def _far_future() -> int:
    from common.budget import now_ms

    return now_ms() + 600_000
