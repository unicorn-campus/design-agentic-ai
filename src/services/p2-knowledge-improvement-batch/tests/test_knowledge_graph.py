from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from neo4j import GraphDatabase, RoutingControl

from help_desk_knowledge.graph import GraphRetriever, load_role_bindings
from help_desk_knowledge.graph_ingestion import (
    Relationship,
    validate_human_accuracy,
    validate_structure,
)
from help_desk_knowledge.specs import GraphSpec


class _Driver:
    def __init__(self, roles: list[str], paths: list[dict[str, object]] | None = None) -> None:
        self.roles = roles
        self.paths = paths or []
        self.queries: list[tuple[str, object]] = []

    def verify_connectivity(self) -> None:
        return None

    def execute_query(self, query: str, **kwargs: object):
        self.queries.append((query, kwargs))
        if query.startswith("SHOW CURRENT USER"):
            return ([{"roles": self.roles}], None, None)
        return (self.paths, None, None)


def _spec(tmp_path: Path) -> GraphSpec:
    role_map = tmp_path / "role_map.json"
    role_map.write_text(
        json.dumps(
            {
                "bindings": [
                    {"actor_id": "R-L1", "workflow_id": "W-1", "role": "helpdesk_w1_graph_reader"},
                    {"actor_id": "R-L1", "workflow_id": "W-2", "role": "helpdesk_w2_graph_reader"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return GraphSpec(
        uri="neo4j://example.invalid",
        user="reader",
        password="secret",
        database="neo4j",
        product="Neo4j",
        version="5.26 LTS",
        max_hops=3,
        result_limit=200,
        role_map_path=role_map,
        human_sample_size=50,
        human_accuracy=0.95,
    )


def test_role_mapping_has_one_entry_per_access_filter_row(tmp_path: Path) -> None:
    assert len(load_role_bindings(_spec(tmp_path))) == 2


def test_service_refuses_to_start_without_expected_role(tmp_path: Path) -> None:
    retriever = GraphRetriever(_Driver(["PUBLIC"]), _spec(tmp_path))
    with pytest.raises(RuntimeError, match="필수 그래프 role"):
        retriever.startup_verify("R-L1", "W-1")


def test_query_condition_is_bound_from_w1_state(tmp_path: Path) -> None:
    driver = _Driver(
        ["helpdesk_w1_graph_reader"],
        [{"path_ref": "p-1", "path_evidence": "고객-카드", "score": 1.0}],
    )
    result = GraphRetriever(driver, _spec(tmp_path)).search(
        "R-L1", "W-1", {"customer_ref": "hashed-customer"}
    )
    query, kwargs = driver.queries[-1]
    assert "$scope_value" in query
    assert kwargs["parameters_"]["scope_value"] == "hashed-customer"
    assert len(result.evidence_refs) == 1


def test_query_condition_cannot_be_omitted_or_defaulted(tmp_path: Path) -> None:
    retriever = GraphRetriever(_Driver(["helpdesk_w2_graph_reader"]), _spec(tmp_path))
    with pytest.raises(ValueError, match="batch_date"):
        retriever.search("R-L1", "W-2", {})


def test_unauthorized_node_relationship_and_two_hop_paths_are_hidden() -> None:
    visible = {
        "helpdesk_w1_graph_reader": {"고객-보유함-카드"},
        "helpdesk_w2_graph_reader": {"문의-대상거래-거래"},
        "PUBLIC": set(),
    }
    assert "내부원문-비밀관계-고객" not in visible["helpdesk_w1_graph_reader"]
    assert "고객-허용관계-내부원문-허용관계-카드" not in visible["helpdesk_w1_graph_reader"]
    assert visible["PUBLIC"] == set()


def test_conflicting_pair_is_separate_structural_failure() -> None:
    rows = [
        Relationship("c1", "분쟁제기함", "t1"),
        Relationship("c1", "분쟁제기하지않음", "t1"),
    ]
    decision = validate_structure(rows, "해당 원천 미적재")
    assert not decision.accepted
    assert "상충 관계 쌍" in decision.reason
    accuracy = validate_human_accuracy(48, 50, 50, 0.95, "수동 정의로 전환")
    assert accuracy.accepted


@pytest.mark.live_call
@pytest.mark.skipif(not os.environ.get("HELP_DESK_RUN_NEO4J_LIVE"), reason="실 Neo4j 미지정")
def test_live_roles_hide_unauthorized_elements_and_intermediate_hops() -> None:
    required = {
        name: os.environ[name]
        for name in (
            "HELP_DESK_KNOWLEDGE_GRAPH_URI",
            "HELP_DESK_KNOWLEDGE_GRAPH_DATABASE",
            "HELP_DESK_NEO4J_W1_USER",
            "HELP_DESK_NEO4J_W1_PASSWORD",
            "HELP_DESK_NEO4J_W2_USER",
            "HELP_DESK_NEO4J_W2_PASSWORD",
            "HELP_DESK_NEO4J_NO_ROLE_USER",
            "HELP_DESK_NEO4J_NO_ROLE_PASSWORD",
        )
    }
    allowed_nodes = {"고객", "카드", "상품", "거래", "문의", "분쟁"}
    allowed_relations = {
        "보유함", "연결상품", "발생거래", "문의함", "대상거래",
        "분쟁제기함", "분쟁제기하지않음",
    }
    for prefix in ("W1", "W2"):
        with GraphDatabase.driver(
            required["HELP_DESK_KNOWLEDGE_GRAPH_URI"],
            auth=(required[f"HELP_DESK_NEO4J_{prefix}_USER"], required[f"HELP_DESK_NEO4J_{prefix}_PASSWORD"]),
        ) as driver:
            records, _, _ = driver.execute_query(
                "MATCH p=(a)-[*1..2]-(b) RETURN labels(a) AS a_labels, "
                "labels(b) AS b_labels, [r IN relationships(p) | type(r)] AS rel_types LIMIT 200",
                database_=required["HELP_DESK_KNOWLEDGE_GRAPH_DATABASE"],
                routing_=RoutingControl.READ,
            )
            assert all(set(row["a_labels"]) <= allowed_nodes for row in records)
            assert all(set(row["b_labels"]) <= allowed_nodes for row in records)
            assert all(set(row["rel_types"]) <= allowed_relations for row in records)
    with GraphDatabase.driver(
        required["HELP_DESK_KNOWLEDGE_GRAPH_URI"],
        auth=(required["HELP_DESK_NEO4J_NO_ROLE_USER"], required["HELP_DESK_NEO4J_NO_ROLE_PASSWORD"]),
    ) as driver:
        record = driver.execute_query(
            "MATCH (n) RETURN count(n) AS count",
            database_=required["HELP_DESK_KNOWLEDGE_GRAPH_DATABASE"],
            routing_=RoutingControl.READ,
            result_transformer_=lambda result: result.single(strict=True),
        )
        assert record["count"] == 0
