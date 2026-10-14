"""장표 1 ② 벡터검색: Neo4j 결과가 기존 Chroma 결과와 같은지, 필터가 인덱스 안에서 처리되는지."""

from __future__ import annotations

import logging

import pytest

import neo4j_store as store
from conftest import GEN_A

FALLBACK = "falling back to procedure-based vector search"
SCENARIOS = ("agent", "auditor", "auditor_member")


def _neo4j(driver, question, scenario, **kw):
    r = question["results"][scenario]
    return store.vector_search(driver, question["vector"], generation=GEN_A, access_levels=r["access_levels"],
                               k=len(r["vector"]), member=r["member_pseudo_id"], **kw)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_same_ranking_as_chroma(driver, data, world, scenario):
    """20문항 × 역할별로 Neo4j(gen-A만) 상위 10개 순위가 기존 Chroma 결과와 같음. 회원 필터는 앱에서 거름."""

    mismatches = []
    for q in data["questions"]:
        expected = [cid for cid, _ in q["results"][scenario]["vector"]]
        got = [cid for cid, _ in _neo4j(driver, q, scenario)]
        if got != expected:
            mismatches.append((q["id"], expected, got))
    assert not mismatches, mismatches


def test_score_is_rescaled_cosine(driver, data, world):
    """Neo4j 점수 = (1 + 코사인)/2, Chroma 점수 = 코사인 — 순위만 같고 값은 다름(가중합 정규화에서 상쇄)."""

    q = data["questions"][0]
    expected = dict(q["results"]["agent"]["vector"])
    for cid, score in _neo4j(driver, q, "agent"):
        assert abs(score - (1 + expected[cid]) / 2) < 1e-4


def test_generation_and_access_filters_stay_in_index(driver, data, world, caplog):
    """세대 · 열람 등급 · 회원 범위를 모두 $eq로 거르면 전수 비교 경고 없이 인덱스 안에서 처리됨(Neo4j 2026.01+)."""

    caplog.set_level(logging.WARNING)
    for scenario in SCENARIOS:
        _neo4j(driver, data["questions"][0], scenario)
    assert FALLBACK not in caplog.text


def test_stock_retriever_misses_filterable_properties(driver, data, world, caplog):
    """라이브러리 기본 VectorRetriever는 Neo4j 2026.09에서 걸러 낼 속성을 못 읽어 같은 필터도 전수 비교로 바뀜(불일치 재현)."""

    caplog.set_level(logging.WARNING)
    _neo4j(driver, data["questions"][0], "agent", stock_retriever=True)
    assert "not declared as filterable" in caplog.text


def test_member_or_filter_falls_back(driver, data, world, caplog):
    """회원 규칙을 $or로 Neo4j에 넘기면 전수 비교로 바뀜 — 결과는 2번 검색 후 합친 것과 같음(장표 주의 2)."""

    q = data["questions"][0]
    caplog.set_level(logging.WARNING)
    in_neo4j = _neo4j(driver, q, "auditor_member", member_strategy="or")
    assert FALLBACK in caplog.text
    caplog.clear()
    split = _neo4j(driver, q, "auditor_member")
    assert FALLBACK not in caplog.text
    assert [c for c, _ in in_neo4j] == [c for c, _ in split]


def test_oversample_misses_member_chunks(driver, data, world):
    """후보를 4배 받아 앱에서 거르는 방식은, 그 회원 조각이 후보 밖이면 빠져 Chroma와 달라짐(설계 수정 근거)."""

    missed = []
    for q in data["questions"]:
        expected = [cid for cid, _ in q["results"]["auditor_member"]["vector"]]
        got = [cid for cid, _ in _neo4j(driver, q, "auditor_member", member_strategy="oversample")]
        if got != expected:
            missed.append(q["id"])
    assert missed, "4배 후보로도 모두 맞음 — 이 데이터에선 차이가 재현되지 않음"
    print(f"\n[oversample 4x] Chroma와 다른 문항: {missed}")


def test_ne_filter_rejected_by_server(driver, data, world, caplog):
    """라이브러리는 $ne를 인덱스 안 처리로 분류하지만 Neo4j 2026.09 서버가 거부해 전수 비교로 바뀜(member_scope를 둔 이유)."""

    caplog.set_level(logging.WARNING)
    store.FilterAwareVectorRetriever(driver, store.INDEX_NAME).get_search_results(
        query_vector=data["questions"][0]["vector"], top_k=5,
        filters={"generation": {"$eq": GEN_A}, "doc_type": {"$ne": store.CONSULT_DOC_TYPE}})
    assert "SEARCH clause failed" in caplog.text


def test_in_filter_falls_back(driver, data, world, caplog):
    """$in 필터도 전수 비교로 바뀜 — 그래서 열람 등급은 $eq 또는 '조건 없음'으로만 표현함."""

    caplog.set_level(logging.WARNING)
    store.FilterAwareVectorRetriever(driver, store.INDEX_NAME).get_search_results(
        query_vector=data["questions"][0]["vector"], top_k=5,
        filters={"generation": {"$eq": GEN_A}, "access_level": {"$in": ["public", "restricted"]}})
    assert FALLBACK in caplog.text
