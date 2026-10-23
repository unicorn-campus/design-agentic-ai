"""K8 커뮤니티 요약 확인: 묶음마다 문서 종류 구성, 거시 질문(Q23 ~ Q25)으로 찾은 상위 3개 보고서를 result.json에 씀.

v0 활성 세대를 읽기만 함. 실행: ../../indexer/graphrag/v0/.venv/Scripts/python.exe probe.py
(Neo4j 비밀번호는 v0와 같은 규칙: 환경변수 NEO4J_PASSWORD, 없으면 hybrid-ai-lab/neo4j/.env)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V0 = HERE.parents[1] / "indexer" / "graphrag" / "v0"
sys.path.insert(0, str(V0))

import neo4j  # noqa: E402

import config  # noqa: E402
from common import embed, load_json  # noqa: E402
from orchestrator import neo4j_password  # noqa: E402

QUESTIONS = ["Q23", "Q24", "Q25"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    g = load_json(config.ACTIVE_FILE)["generation"]
    evalset = {q["id"]: q for q in load_json(HERE.parents[1] / "ragas" / "eval-set.json")["questions"]}
    drv = neo4j.GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, neo4j_password()),
                               notifications_min_severity="OFF")
    with drv:
        rec, _, _ = drv.execute_query(
            "MATCH (c:Community {generation: $g})<-[:IN_COMMUNITY]-(e) "
            "OPTIONAL MATCH (e)-[:FROM_CHUNK]->(k:Chunk) "
            "WITH c, collect(DISTINCT e) AS es, collect(DISTINCT k.doc_type) AS types, collect(DISTINCT k.doc_id) AS docs "
            "RETURN c.community_id AS id, c.title AS title, c.summary AS summary, c.findings AS findings, "
            "c.size AS size, types, docs, [x IN es | [l IN labels(x) WHERE NOT l STARTS WITH '__'][0]] AS labels "
            "ORDER BY c.size DESC, c.community_id", g=g)
        comms = [dict(r) for r in rec]
        for c in comms:
            c["labels"] = dict(Counter(c["labels"]))
        hits = {}
        vecs = embed([evalset[q]["question"] for q in QUESTIONS])
        for q, v in zip(QUESTIONS, vecs):
            rec, _, _ = drv.execute_query(
                "CALL db.index.vector.queryNodes('kg_community_embedding', 20, $v) YIELD node, score "
                "WHERE node.generation = $g RETURN node.community_id AS id, node.title AS title, score "
                "ORDER BY score DESC LIMIT 3", v=v, g=g)
            hits[q] = [dict(r) for r in rec]
    mixed = [c["id"] for c in comms if len(c["types"]) > 1]
    out = {"generation": g, "communities": comms, "mixed_doc_type_communities": mixed,
           "by_doc_type_count": dict(Counter("+".join(sorted(c["types"])) for c in comms)),
           "macro_top3": {q: {"question": evalset[q]["question"], "ground_truth": evalset[q]["ground_truth"],
                              "top3": hits[q]} for q in QUESTIONS}}
    (HERE / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("세대", g, "| 커뮤니티", len(comms), "| 문서 종류가 섞인 묶음", len(mixed))
    print("문서 종류 구성", out["by_doc_type_count"])
    for c in comms:
        print(f"- [{c['size']:2}] {'+'.join(sorted(c['types'])):28} {c['title']}")
    for q in QUESTIONS:
        print(q, evalset[q]["question"])
        for h in hits[q]:
            print(f"   {h['score']:.3f} {h['title']}")


if __name__ == "__main__":
    main()
