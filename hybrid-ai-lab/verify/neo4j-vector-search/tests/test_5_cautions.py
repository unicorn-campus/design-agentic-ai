"""장표 2 주의 3 · 4를 실제로 재현: 저장기 CREATE 중복, 병합 범위를 안 좁히면 세대가 섞임.

공용 세대(gen-A · gen-B)를 건드리지 않게 따로 이름 붙인 작은 세대로만 시험함.
"""

from __future__ import annotations

import pytest

import neo4j_store as store
from llms import FakeCardLLM


def _small(data, card: str, n: int = 3):
    picked = [c for c in data["chunks"] if card in c["text"]][:n]
    assert len(picked) >= 2, f"'{card}'가 든 청크가 부족함"
    return picked


@pytest.fixture(scope="module")
def card(data):
    """본문에 가장 자주 나오는 카드명(병합이 일어나야 하는 이름)."""

    names = sorted({c["card_name"] for c in data["chunks"] if c["card_name"]}, key=len, reverse=True)
    counts = {n: sum(1 for c in data["chunks"] if n in c["text"]) for n in names}
    return max(counts, key=counts.get)


def test_writer_create_duplicates_on_rerun(driver, data, world, card_names, card):
    """같은 세대를 두 번 저장하면 청크가 2배로 생김 → 검증이 실패해 게시되지 않음."""

    chunks = _small(data, card)
    llm = FakeCardLLM(card_names)
    store.write_generation(driver, llm, chunks, "dup")
    store.write_generation(driver, llm, chunks, "dup")
    report = store.verify_generation(driver, "dup", {c["chunk_id"] for c in chunks})
    assert report["count"] == 2 * len(chunks) and report["unique"] == len(chunks)
    assert not report["ok"]


def test_unscoped_resolver_mixes_generations(driver, data, world, card_names, card):
    """병합 범위를 세대로 좁히지 않으면, 두 세대의 같은 이름 엔티티가 한 노드로 합쳐져 세대가 섞임."""

    chunks = _small(data, card)
    llm = FakeCardLLM(card_names)
    store.write_generation(driver, llm, chunks, "risk-1")
    store.write_generation(driver, llm, chunks, "risk-2")
    # '세대 범위 없음'을 흉내 냄 — 공용 세대는 건드리지 않게 risk-* 두 세대만 한 범위로 묶어 병합
    import asyncio
    from neo4j_graphrag.components.resolver import SinglePropertyExactMatchResolver
    asyncio.run(SinglePropertyExactMatchResolver(driver, filter_query="WHERE entity.generation STARTS WITH 'risk-'").run())
    records, _, _ = driver.execute_query(
        "MATCH (e:Card {name: $n}) WHERE e.generation STARTS WITH 'risk-' "
        "MATCH (e)-[:FROM_CHUNK]->(c:Chunk) RETURN count(DISTINCT e) AS nodes, collect(DISTINCT c.generation) AS gens",
        n=card)
    row = records[0]
    assert row["nodes"] == 1
    assert sorted(row["gens"]) == ["risk-1", "risk-2"]  # 한 엔티티가 두 세대 청크에 동시에 매달림
