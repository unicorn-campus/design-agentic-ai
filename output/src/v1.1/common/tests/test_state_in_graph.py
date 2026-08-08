"""병합 규칙이 실제 흐름 프레임워크 안에서 그렇게 도는지 확인함.

타입 메타데이터만 보는 시험(`test_state.py`)과 달리 여기서는 그래프를 실제로 조립해 돌림.
흐름 설계는 `06-workflow.md` 몫이며 이 그래프는 병합 규칙 확인용 최소 골격임.
"""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import InvalidUpdateError
from langgraph.graph import END, START, StateGraph

from common.checkpointer import thread_config
from common.state import LunchPickState, TriggerKind


def _fan_out_graph(*, also_write_single_writer_field: bool = False) -> StateGraph:
    builder: StateGraph = StateGraph(LunchPickState)

    def entry(_state: LunchPickState) -> LunchPickState:
        return {"trigger_kind": TriggerKind.SYNC_RECOMMEND, "deadline_at": 1}

    def collector(tag: str) -> object:
        def node(_state: LunchPickState) -> LunchPickState:
            update: LunchPickState = {
                "partial_context": [{"source": tag.lower()}],
                "error_history": [{"step_id": tag}],
                "retry_count_by_step": {tag: 1},
            }
            if also_write_single_writer_field:
                update["fallback_reason"] = tag.lower()
            return update

        return node

    collector_a = collector("A")
    collector_b = collector("B")

    builder.add_node("entry", entry)
    builder.add_node("collector_a", collector_a)
    builder.add_node("collector_b", collector_b)
    builder.add_edge(START, "entry")
    builder.add_edge("entry", "collector_a")
    builder.add_edge("entry", "collector_b")
    builder.add_edge("collector_a", END)
    builder.add_edge("collector_b", END)
    return builder


def test_parallel_writes_accumulate_on_merged_list_fields() -> None:
    """시험 2 — 병렬 노드 둘이 넣은 값이 둘 다 남음."""
    graph = _fan_out_graph().compile()
    result = graph.invoke({})

    assert sorted(item["source"] for item in result["partial_context"]) == ["a", "b"]
    assert sorted(item["step_id"] for item in result["error_history"]) == ["A", "B"]


def test_parallel_writes_merge_by_key_on_merged_dict_field() -> None:
    """시험 2 — 값형은 키 단위로 합쳐져 둘 다 남음."""
    graph = _fan_out_graph().compile()
    result = graph.invoke({})

    assert result["retry_count_by_step"] == {"A": 1, "B": 1}


def test_single_writer_field_refuses_two_writers_in_one_step() -> None:
    """시험 1 — 병합 규칙이 없으니 두 노드가 같이 쓰면 프레임워크가 막음.

    값이 쌓이지 않는다는 것을 넘어 애초에 두 명이 쓸 수 없음을 확인함.
    """
    graph = _fan_out_graph(also_write_single_writer_field=True).compile()
    with pytest.raises(InvalidUpdateError) as caught:
        graph.invoke({})
    assert "fallback_reason" in str(caught.value)


def test_single_writer_field_keeps_the_single_value_it_was_given() -> None:
    graph = _fan_out_graph().compile()
    result = graph.invoke({"fallback_reason": "캐시 폴백"})

    assert result["fallback_reason"] == "캐시 폴백"
    assert not isinstance(result["fallback_reason"], list)


def test_checkpointer_resumes_the_same_thread() -> None:
    saver = InMemorySaver()
    graph = _fan_out_graph().compile(checkpointer=saver)
    config = thread_config("mbr_001:recommend:2026-08-08T03:14:15Z")

    graph.invoke({}, config=config)
    snapshot = graph.get_state(config)

    assert snapshot.values["trigger_kind"] is TriggerKind.SYNC_RECOMMEND
    assert len(snapshot.values["partial_context"]) == 2
