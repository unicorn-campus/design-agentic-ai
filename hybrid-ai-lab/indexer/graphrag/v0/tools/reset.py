"""v0가 만든 시험 데이터를 모두 지움: Neo4j의 v0 세대 노드, 검색엔진의 card_chunks-gen-* 인덱스, data 폴더의 세대 기록.

v0 세대만 지우려고 활성 세대 파일과 세대 폴더에 적힌 세대 ID만 대상으로 함(다른 실험 데이터는 건드리지 않음).
실행: python tools/reset.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import neo4j  # noqa: E402

import config  # noqa: E402
import search_index  # noqa: E402


def main() -> None:
    generations = sorted(p.name for p in config.GENERATIONS.glob("gen-*")) if config.GENERATIONS.exists() else []
    if not generations:
        print("지울 v0 세대가 없음")
        return
    with neo4j.GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, os.environ["NEO4J_PASSWORD"])) as d:
        for g in generations:
            n = d.execute_query("MATCH (n {generation: $g}) DETACH DELETE n RETURN count(*) AS n", g=g)[0][0]["n"]
            print(f"Neo4j 세대 {g}: 노드 {n}개 지움")
    client = search_index.client()
    for g in generations:
        index = search_index.index_name(g)
        if client.indices.exists(index=index):
            client.indices.delete(index=index)
            print(f"검색엔진 인덱스 {index} 지움")
    shutil.rmtree(config.GENERATIONS)
    config.ACTIVE_FILE.unlink(missing_ok=True)
    print("data/generations와 활성 세대 파일 지움")


if __name__ == "__main__":
    main()
