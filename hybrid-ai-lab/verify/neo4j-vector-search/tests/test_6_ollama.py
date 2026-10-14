"""실제 LLM 1회 확인: 로컬 Ollama로 청크 2개를 추출해 Native 추출기 형식(JSON → 노드·FROM_CHUNK)이 맞는지.

`-m ollama`로 따로 돌림. 품질(정답 엔티티)은 보지 않고 형식과 연결만 봄.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request

import pytest

import neo4j_store as store
from llms import OllamaHttpLLM

pytestmark = pytest.mark.ollama
GEN = "ollama-smoke"


@pytest.fixture(scope="module")
def model() -> str:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    name = os.environ.get("OLLAMA_MODEL", "hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL")
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=5) as response:
            names = [m["name"] for m in json.loads(response.read())["models"]]
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"Ollama에 연결 못 함: {error}")
    if name not in names:
        pytest.skip(f"모델 없음: {name}")
    return name


def test_real_llm_extraction_shape(driver, data, world, model, card_names):
    chunks = [c for c in data["chunks"] if c["doc_type"] == "benefit_guide" and any(n in c["text"] for n in card_names)][:2]
    started = time.perf_counter()
    store.write_generation(driver, OllamaHttpLLM(model), chunks, GEN)
    elapsed = time.perf_counter() - started
    records, _, _ = driver.execute_query(
        "MATCH (c:Chunk {generation: $g}) OPTIONAL MATCH (e:__Entity__)-[:FROM_CHUNK]->(c) "
        "RETURN c.chunk_id AS chunk, collect(DISTINCT [l IN labels(e) WHERE NOT l STARTS WITH '__'][0] + ':' + "
        "coalesce(e.name, e.id, '?')) AS entities", g=GEN)
    print(f"\n[ollama] model={model} chunks={len(chunks)} seconds={elapsed:.1f}")
    for record in records:
        print(f"  {record['chunk']}: {record['entities'][:8]}")
    assert len(records) == len(chunks)
    assert sum(len(r["entities"]) for r in records) > 0
