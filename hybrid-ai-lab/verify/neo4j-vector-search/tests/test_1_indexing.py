"""장표 1 ① 인덱싱: 기존 청크가 Neo4j에 설계대로 담기는지."""

from __future__ import annotations

import neo4j_store as store
from conftest import GEN_A


def test_chunk_count_and_ids_persist(driver, data, world):
    """청크 218개가 그대로 들어가고, chunk_id는 속성으로 남고 임시 ID(uid)는 지워짐."""

    records, _, _ = driver.execute_query(
        "MATCH (c:Chunk {generation: $g}) RETURN count(c) AS n, count(DISTINCT c.chunk_id) AS ids, "
        "count(c.__tmp_internal_id) AS tmp", g=GEN_A)
    row = records[0]
    assert row["n"] == len(data["chunks"]) == data["chunk_count"]
    assert row["ids"] == row["n"]
    assert row["tmp"] == 0


def test_existing_vectors_reused(driver, data, world):
    """metadata['embedding']로 넣은 기존 벡터가 768차원 그대로 저장됨(다시 임베딩하지 않음)."""

    sample = {c["chunk_id"]: c["embedding"] for c in data["chunks"][:20]}
    records, _, _ = driver.execute_query(
        "MATCH (c:Chunk {generation: $g}) WHERE c.chunk_id IN $ids RETURN c.chunk_id AS id, c.embedding AS v",
        g=GEN_A, ids=list(sample))
    assert len(records) == len(sample)
    for record in records:
        stored = list(record["v"])
        assert len(stored) == store.DIMENSION
        assert max(abs(a - b) for a, b in zip(stored, sample[record["id"]])) < 1e-6


def test_lexical_graph_shape(driver, data, world):
    """Document · FROM_DOCUMENT · NEXT_CHUNK가 기본 이름으로 생김(장표 'Neo4j에 담긴 모습')."""

    sources = {c["source"] for c in data["chunks"]}
    records, _, _ = driver.execute_query(
        "MATCH (d:Document {generation: $g}) WITH count(d) AS docs "
        "MATCH (:Chunk {generation: $g})-[r:FROM_DOCUMENT]->(:Document) WITH docs, count(r) AS fd "
        "MATCH (:Chunk {generation: $g})-[n:NEXT_CHUNK]->(:Chunk) RETURN docs, fd, count(n) AS nc", g=GEN_A)
    row = records[0]
    assert row["docs"] == len(sources)
    assert row["fd"] == len(data["chunks"])
    assert row["nc"] == len(data["chunks"]) - len(sources)


def test_vector_index_online(driver, world):
    assert store.index_state(driver) == "ONLINE"
