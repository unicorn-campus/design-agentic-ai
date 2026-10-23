"""그래프로 들어가는 두 입구 비교: 청크 입구(검색엔진) vs 엔티티 입구(K6 노드 벡터 인덱스).

질문마다 정답 엔티티(questions.json의 targets)를 찾았는지와, LLM에 넘길 후보 엔티티가 몇 개인지를 잼.
- 청크 입구: 검색엔진에서 BM25와 kNN 순위를 RRF로 합쳐 상위 k개 청크 → 같은 chunk_id의 청크 노드
  → FROM_CHUNK로 그 청크에서 나온 엔티티 전부가 후보
- 엔티티 입구: 질문 임베딩으로 kg_entity_embedding 상위 k개 엔티티가 후보

v0 활성 세대를 그대로 씀(새로 쓰는 것 없음). 실행: v0 가상환경으로
  NEO4J_PASSWORD=… ../../indexer/graphrag/v0/.venv/Scripts/python.exe compare.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V0 = HERE.parents[1] / "indexer" / "graphrag" / "v0"
sys.path.insert(0, str(V0))

import neo4j  # noqa: E402

import config  # noqa: E402
import search_index  # noqa: E402
from common import embed, load_json, save_json  # noqa: E402

RRF_K = 60            # RRF 순위 보정값(널리 쓰는 기본값)
CHUNK_KS = (1, 2)     # 청크 입구에서 가져올 청크 수
ENTITY_KS = (3, 5)    # 엔티티 입구에서 가져올 엔티티 수


def chunk_ranking(os_client, index: str, tokenizer, question: str, vector: list[float], total: int) -> list[str]:
    """BM25 순위와 kNN 순위를 RRF로 합친 청크 ID 순서."""

    bm25 = os_client.search(index=index, body={"size": total, "_source": ["chunk_id"],
                                               "query": {"match": {"text_tokens": " ".join(tokenizer.tokenize(question))}}})
    knn = os_client.search(index=index, body={"size": total, "_source": ["chunk_id"],
                                              "query": {"knn": {"embedding": {"vector": vector, "k": total}}}})
    score: dict[str, float] = {}
    for hits in (bm25["hits"]["hits"], knn["hits"]["hits"]):
        for rank, h in enumerate(hits, 1):
            cid = h["_source"]["chunk_id"]
            score[cid] = score.get(cid, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(score, key=score.get, reverse=True)


def main() -> None:
    active = load_json(config.ACTIVE_FILE)
    g, index = active["generation"], active["search_index"]
    questions = load_json(HERE / "questions.json")
    os_client = search_index.client()
    tokenizer = search_index.tokenizer_from_meta(search_index.tokenizer_meta_of(index))
    total = len(search_index.chunk_ids(index))
    vectors = embed([q["q"] for q in questions])

    driver = neo4j.GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, os.environ["NEO4J_PASSWORD"]))
    run = lambda cypher, **kw: [dict(r) for r in driver.execute_query(cypher, g=g, **kw)[0]]

    def target_ids(targets) -> set[str]:
        ids = set()
        for label, prop, text in targets:
            ids |= {r["id"] for r in run(f"MATCH (e:`{label}` {{generation: $g}}) WHERE e.`{prop}` CONTAINS $t "
                                         "RETURN elementId(e) AS id", t=text)}
        return ids

    rows = []
    for q, vec in zip(questions, vectors):
        want = target_ids(q["targets"])
        if not want:
            raise SystemExit(f"{q['id']}: 정답 엔티티를 그래프에서 못 찾음")
        ranking = chunk_ranking(os_client, index, tokenizer, q["q"], vec, total)
        row = {"id": q["id"], "doc": q["doc"], "q": q["q"], "targets": len(want)}
        for k in CHUNK_KS:
            got = {r["id"] for r in run(
                "MATCH (c:Chunk {generation: $g}) WHERE c.chunk_id IN $cids "
                "MATCH (e)-[:FROM_CHUNK]->(c) RETURN DISTINCT elementId(e) AS id", cids=ranking[:k])}
            row[f"chunk@{k}"] = {"hit": bool(want & got), "candidates": len(got)}
        hits = run("CALL db.index.vector.queryNodes('kg_entity_embedding', $n, $v) YIELD node, score "
                   "WHERE node.generation = $g RETURN elementId(node) AS id", n=max(ENTITY_KS) * 4, v=vec)
        order = [h["id"] for h in hits]
        rank = next((i + 1 for i, eid in enumerate(order) if eid in want), None)
        row["entity_rank"] = rank
        for k in ENTITY_KS:
            row[f"entity@{k}"] = {"hit": rank is not None and rank <= k, "candidates": k}
        rows.append(row)
    driver.close()

    summary = {}
    for key in [f"chunk@{k}" for k in CHUNK_KS] + [f"entity@{k}" for k in ENTITY_KS]:
        summary[key] = {"hit": sum(r[key]["hit"] for r in rows), "of": len(rows),
                        "avg_candidates": round(sum(r[key]["candidates"] for r in rows) / len(rows), 1)}
    both = sum(r["chunk@1"]["hit"] or r["entity@5"]["hit"] for r in rows)
    summary["chunk@1 + entity@5"] = {"hit": both, "of": len(rows)}
    summary["only_entity@5"] = [r["id"] for r in rows if r["entity@5"]["hit"] and not r["chunk@1"]["hit"]]
    summary["only_chunk@1"] = [r["id"] for r in rows if r["chunk@1"]["hit"] and not r["entity@5"]["hit"]]
    result = {"generation": g, "search_index": index, "chunks_in_index": total, "rrf_k": RRF_K,
              "summary": summary, "rows": rows}
    save_json(HERE / "result.json", result)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in rows:
        print(r["id"], "청크1", "O" if r["chunk@1"]["hit"] else "X", r["chunk@1"]["candidates"],
              "| 청크2", "O" if r["chunk@2"]["hit"] else "X", r["chunk@2"]["candidates"],
              "| 엔티티 순위", r["entity_rank"], "|", r["q"])


if __name__ == "__main__":
    main()
