"""장표 2 검색 세대: 검증 → 포인터 교체 → 전환 · 되돌리기, 그리고 병합 범위."""

from __future__ import annotations

import pytest

import neo4j_store as store
from conftest import GEN_A, GEN_B


def _search_via_pointer(driver, pointer_path, question):
    """검색기처럼 요청 처음에 포인터를 한 번 읽고 그 세대로 검색함."""

    generation = store.read_pointer(pointer_path)["neo4j"]["generation"]
    return [cid for cid, _ in store.vector_search(driver, question["vector"], generation=generation,
                                                  access_levels=["public"], k=10)]


def test_publish_switch_and_rollback(driver, data, world, removed_ids, tmp_path):
    pointer = tmp_path / "active_generation.json"
    questions = data["questions"][:3]

    store.publish(pointer, GEN_A, "generations/gen-A/search_indexes", store.verify_generation(driver, GEN_A,
                                                                                                world["ids_a"]))
    first = [_search_via_pointer(driver, pointer, q) for q in questions]
    assert removed_ids <= {cid for ids in first for cid in ids}  # gen-A엔 뺄 청크가 1위로 있음

    report_b = store.verify_generation(driver, GEN_B, world["ids_b"])
    assert report_b["ok"], report_b
    store.publish(pointer, GEN_B, "generations/gen-B/search_indexes", report_b)
    p = store.read_pointer(pointer)
    assert p["generation"] == p["neo4j"]["generation"] == GEN_B and "gen-B" in p["search_index_root"]
    second = [_search_via_pointer(driver, pointer, q) for q in questions]
    assert not removed_ids & {cid for ids in second for cid in ids}
    assert all(set(ids) <= world["ids_b"] for ids in second)

    store.publish(pointer, GEN_A, "generations/gen-A/search_indexes", store.verify_generation(driver, GEN_A,
                                                                                                world["ids_a"]))
    assert [_search_via_pointer(driver, pointer, q) for q in questions] == first  # 되돌리면 그대로 돌아옴


def test_publish_refuses_failed_check(driver, world, tmp_path):
    """검증이 실패하면(청크 집합 불일치) 포인터를 바꾸지 않음."""

    pointer = tmp_path / "active_generation.json"
    store.publish(pointer, GEN_A, "generations/gen-A/search_indexes", store.verify_generation(driver, GEN_A,
                                                                                                world["ids_a"]))
    bad = store.verify_generation(driver, GEN_B, world["ids_a"])  # gen-B엔 빠진 청크가 있음
    assert not bad["ok"] and not bad["ids_match"]
    with pytest.raises(ValueError):
        store.publish(pointer, GEN_B, "generations/gen-B/search_indexes", bad)
    assert store.read_pointer(pointer)["generation"] == GEN_A


def test_scoped_resolver_keeps_generations_apart(driver, world):
    """세대 범위(filter_query)로 병합하면: gen-A 병합이 gen-B를 건드리지 않고, 병합 뒤 세대마다 이름당 노드 1개."""

    assert world["dup_b_before"] > 0
    assert world["dup_b_after_a"] == world["dup_b_before"]
    records, _, _ = driver.execute_query(
        "MATCH (e:Card) WHERE e.generation IN [$a, $b] WITH e.name AS name, e.generation AS g, count(*) AS n "
        "RETURN max(n) AS max_per_gen, count(DISTINCT name) AS names", a=GEN_A, b=GEN_B)
    assert records[0]["max_per_gen"] == 1
    records, _, _ = driver.execute_query(
        "MATCH (e:Card {name: $n}) RETURN collect(e.generation) AS gens", n=_a_shared_card(driver))
    assert sorted(records[0]["gens"]) == [GEN_A, GEN_B]  # 같은 카드도 세대마다 따로 있음


def _a_shared_card(driver) -> str:
    records, _, _ = driver.execute_query(
        "MATCH (a:Card {generation: $a}), (b:Card {generation: $b}) WHERE a.name = b.name RETURN a.name AS n LIMIT 1",
        a=GEN_A, b=GEN_B)
    return records[0]["n"]
