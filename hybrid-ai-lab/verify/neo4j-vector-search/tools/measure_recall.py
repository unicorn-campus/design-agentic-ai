"""Neo4j 벡터검색 결과가 기존 Chroma 결과와 얼마나 같은지 설정별로 재는 측정 스크립트임(시험 자료 gen-A 사용).

실행(검증 가상환경, pytest로 gen-A를 적재한 뒤): .venv/Scripts/python tools/measure_recall.py [--no-quantization]
--no-quantization: 벡터 인덱스를 압축 없이 다시 만든 뒤 잼(인덱스만 바꾸고 노드는 그대로 둠).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import neo4j_store as store  # noqa: E402
from conftest import GEN_A, _load_env  # noqa: E402

SCENARIOS = ("agent", "auditor", "auditor_member")


class _Count(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.fallbacks = 0

    def emit(self, record: logging.LogRecord) -> None:
        if "falling back" in record.getMessage():
            self.fallbacks += 1


def recreate_index(driver, quantization: bool) -> str:
    """같은 이름·속성으로 인덱스를 다시 만들고 실제 압축 설정을 돌려줌."""

    driver.execute_query(f"DROP INDEX {store.INDEX_NAME} IF EXISTS")
    props = ", ".join(f"n.{p}" for p in store.FILTERABLE)
    config = "`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'"
    if not quantization:
        config += ", `vector.quantization.enabled`: false"
    driver.execute_query(f"CREATE VECTOR INDEX {store.INDEX_NAME} FOR (n:Chunk) ON n.embedding WITH [{props}] "
                         f"OPTIONS {{ indexConfig: {{ {config} }} }}")
    driver.execute_query("CALL db.awaitIndexes(300)")
    records, _, _ = driver.execute_query("SHOW VECTOR INDEXES YIELD name, options WHERE name = $n RETURN options",
                                         n=store.INDEX_NAME)
    return str(records[0]["options"]["indexConfig"].get("vector.quantization.type"))


def measure(driver, data, *, ratio: int, stock: bool) -> dict:
    handler = _Count()
    logging.getLogger("neo4j_graphrag").addHandler(handler)
    exact = total = 0
    overlap = 0.0
    for q in data["questions"]:
        for name in SCENARIOS:
            r = q["results"][name]
            expected = [cid for cid, _ in r["vector"]]
            original = store.FilterAwareVectorRetriever.get_search_results

            def patched(self, *a, **kw):
                kw["effective_search_ratio"] = ratio
                return original(self, *a, **kw)

            store.FilterAwareVectorRetriever.get_search_results = patched
            store.VectorRetriever.get_search_results = patched if stock else store.VectorRetriever.get_search_results
            try:
                got = [cid for cid, _ in store.vector_search(driver, q["vector"], generation=GEN_A,
                                                             access_levels=r["access_levels"], k=len(expected),
                                                             member=r["member_pseudo_id"], stock_retriever=stock)]
            finally:
                store.FilterAwareVectorRetriever.get_search_results = original
            total += 1
            exact += got == expected
            overlap += len(set(got) & set(expected)) / max(1, len(expected))
    logging.getLogger("neo4j_graphrag").removeHandler(handler)
    return {"ratio": ratio, "path": "전수 비교" if stock else "인덱스 안", "exact_order": f"{exact}/{total}",
            "overlap@10": round(overlap / total, 3), "fallback_warnings": handler.fallbacks}


def main() -> None:
    _load_env()
    data = json.loads((ROOT / "fixtures" / "retriever_fixture.json").read_text(encoding="utf-8"))
    driver = store.connect()
    quant = recreate_index(driver, quantization="--no-quantization" not in sys.argv)
    print(f"인덱스 압축 설정: {quant}")
    rows = [measure(driver, data, ratio=1, stock=True)]
    rows += [measure(driver, data, ratio=r, stock=False) for r in (1, 2, 4, 10)]
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    driver.close()


if __name__ == "__main__":
    main()
