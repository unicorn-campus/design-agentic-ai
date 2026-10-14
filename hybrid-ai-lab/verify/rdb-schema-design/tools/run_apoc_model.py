"""시험용 Neo4j에서 apoc.model.jdbc를 실행해 RDB 구조(테이블, 열, FK)를 JSON으로 저장하는 스크립트임.

왜 따로 저장하나: 다음 단계(바이브 코딩 툴 프롬프트)의 입력 형식을 파일로 고정하기 위함. write: false라 Neo4j에는 아무것도 남기지 않음.

실행(검증 가상환경 재사용):
    RDB_JDBC_URL=jdbc:postgresql://host.docker.internal:5432/cardlab RDB_USER=cardlab RDB_PASSWORD=... \
    NEO4J_PASSWORD=... ../neo4j-vector-search/.venv/Scripts/python tools/run_apoc_model.py
출력: output/apoc_model.json — 노드(라벨, 속성)와 관계(타입, 시작, 끝, 속성). 계정 값은 저장하지 않음.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "apoc_model.json"


def to_plain(value):
    """Neo4j 값(날짜 등)을 JSON으로 저장할 수 있는 값으로 바꿈."""

    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def main() -> None:
    driver = GraphDatabase.driver(os.environ.get("NEO4J_URI", "bolt://localhost:17687"),
                                  auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]))
    config = {
        "schema": os.environ.get("RDB_SCHEMA", "public"),
        "credentials": {"user": os.environ["RDB_USER"], "password": os.environ["RDB_PASSWORD"]},
        "write": False,
    }
    records, _, _ = driver.execute_query(
        "CALL apoc.model.jdbc($url, $config) YIELD nodes, relationships RETURN nodes, relationships",
        url=os.environ["RDB_JDBC_URL"], config=config)
    driver.close()
    record = records[0]
    nodes = [{"id": n.element_id, "labels": sorted(n.labels), "properties": to_plain(dict(n))} for n in record["nodes"]]
    rels = [{"type": r.type, "start": r.start_node.element_id, "end": r.end_node.element_id,
             "properties": to_plain(dict(r))} for r in record["relationships"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": {"jdbc_url": os.environ["RDB_JDBC_URL"], "schema": config["schema"], "procedure": "apoc.model.jdbc",
                   "apoc_extended": "2026.04.0", "neo4j": "2026.09.0"},
        "nodes": nodes, "relationships": rels,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    labels = {}
    for n in nodes:
        key = "/".join(n["labels"])
        labels[key] = labels.get(key, 0) + 1
    types = {}
    for r in rels:
        types[r["type"]] = types.get(r["type"], 0) + 1
    print(f"저장: {OUT}")
    print(f"노드 {len(nodes)}개 {labels} / 관계 {len(rels)}개 {types}")


if __name__ == "__main__":
    main()
