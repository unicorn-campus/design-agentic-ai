"""장표 1 ② 하이브리드(기존 BM25) · 그래프 확장."""

from __future__ import annotations

import pytest

import neo4j_store as store
from conftest import GEN_A

SCENARIOS = ("agent", "auditor", "auditor_member")


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_hybrid_same_as_existing(driver, data, world, scenario):
    """벡터를 Chroma 대신 Neo4j로 바꿔도, 기존 BM25 결과와 기존 가중합(0.6 : 0.4)으로 합친 순위가 같음."""

    mismatches = []
    for q in data["questions"]:
        r = q["results"][scenario]
        neo = store.vector_search(driver, q["vector"], generation=GEN_A, access_levels=r["access_levels"],
                                  k=len(r["vector"]), member=r["member_pseudo_id"])
        expected = store.hybrid(r["vector"], r["keyword"], k=10)
        got = store.hybrid(neo, r["keyword"], k=10)
        if got != expected:
            mismatches.append((q["id"], expected, got))
    assert not mismatches, mismatches


def test_graph_expand_from_hybrid_hits(driver, data, world, card_names):
    """하이브리드로 찾은 청크에서 FROM_CHUNK로 엔티티를 모음 — 본문에 있는 카드명이 엔티티로 나오고 다른 세대는 섞이지 않음."""

    texts = {c["chunk_id"]: c["text"] for c in data["chunks"]}
    longest_first = sorted(card_names, key=len, reverse=True)
    checked = 0
    for q in data["questions"]:
        r = q["results"]["agent"]
        neo = store.vector_search(driver, q["vector"], generation=GEN_A, access_levels=r["access_levels"], k=10)
        hits = store.hybrid(neo, r["keyword"], k=10)
        by_chunk: dict[str, set[str]] = {}
        for row in store.graph_expand(driver, hits, GEN_A):
            by_chunk.setdefault(row["chunk_id"], set()).add(row["entity"])
        for cid in hits:
            rest, expected = texts[cid], set()
            for name in longest_first:
                if name in rest:
                    expected.add(name)
                    rest = rest.replace(name, " ")
            if expected:
                checked += 1
                assert expected <= by_chunk.get(cid, set()), (q["id"], cid, expected, by_chunk.get(cid))
    assert checked > 0, "상위 청크에 카드명이 하나도 없어 확장 시험이 비었음"
    records, _, _ = driver.execute_query(
        "MATCH (c:Chunk {generation: $g})<-[:FROM_CHUNK]-(e:__Entity__) WHERE e.generation <> $g RETURN count(e) AS n",
        g=GEN_A)
    assert records[0]["n"] == 0


def test_relationships_follow_entities(driver, world):
    """엔티티 사이 관계(HAS_FEE · MENTIONED_WITH)도 그래프 확장으로 따라갈 수 있음."""

    records, _, _ = driver.execute_query(
        "MATCH (:Card {generation: $g})-[r:HAS_FEE|MENTIONED_WITH]->() RETURN type(r) AS t, count(*) AS n", g=GEN_A)
    kinds = {r["t"]: r["n"] for r in records}
    assert kinds.get("HAS_FEE", 0) > 0
