"""공용 준비: 시험 자료 읽기 · Neo4j 연결 · 세대 2개(gen-A 전체, gen-B 일부 제외) 적재.

시험 전용 Neo4j 컨테이너(README 참조)만 대상으로 함 — 시작할 때 DB를 비움.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import neo4j_store as store  # noqa: E402
from llms import FakeCardLLM  # noqa: E402

FIXTURE = ROOT / "fixtures" / "retriever_fixture.json"
GEN_A, GEN_B = "gen-A", "gen-B"


def _load_env() -> None:
    """.env(없으면 .env.example)의 KEY=VALUE를 환경변수로 올림. 이미 있는 값은 두고 감."""

    for name in (".env", ".env.example"):
        path = ROOT / name
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
            return


@pytest.fixture(scope="session")
def data() -> dict:
    if not FIXTURE.exists():
        pytest.skip("fixtures/retriever_fixture.json 없음 — tools/export_fixture.py를 먼저 실행")
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def driver():
    _load_env()
    drv = store.connect()
    try:
        drv.verify_connectivity()
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"시험용 Neo4j에 연결 못 함: {error}")
    yield drv
    drv.close()


@pytest.fixture(scope="session")
def card_names(data) -> list[str]:
    return sorted({c["card_name"] for c in data["chunks"] if c["card_name"]})


@pytest.fixture(scope="session")
def removed_ids(data) -> set[str]:
    """gen-B에서 뺄 청크 — 앞 질문 3개의 agent 벡터 1위(세대가 바뀌면 결과가 달라지게 고름)."""

    return {q["results"]["agent"]["vector"][0][0] for q in data["questions"][:3]}


@pytest.fixture(scope="session")
def world(driver, data, card_names, removed_ids) -> dict:
    """DB를 비우고 gen-A(전체)·gen-B(일부 제외)를 저장 → 세대별 병합 → 벡터 인덱스."""

    store.reset_db(driver)
    llm = FakeCardLLM(card_names)
    chunks_a = data["chunks"]
    chunks_b = [c for c in data["chunks"] if c["chunk_id"] not in removed_ids]
    store.write_generation(driver, llm, chunks_a, GEN_A)
    store.write_generation(driver, llm, chunks_b, GEN_B)
    store.ensure_vector_index(driver)
    # gen-B 병합 전 상태를 기록해 두고(병합 범위 시험용), gen-A만 먼저 병합
    before_b = _duplicate_names(driver, GEN_B)
    store.resolve(driver, GEN_A)
    after_a_b = _duplicate_names(driver, GEN_B)
    store.resolve(driver, GEN_B)
    return {"ids_a": {c["chunk_id"] for c in chunks_a}, "ids_b": {c["chunk_id"] for c in chunks_b},
            "dup_b_before": before_b, "dup_b_after_a": after_a_b, "llm_calls": llm.calls}


def _duplicate_names(driver, generation: str) -> int:
    """그 세대에서 (라벨, 이름)이 같은 엔티티가 2개 이상인 묶음 수."""

    records, _, _ = driver.execute_query(
        "MATCH (e:__Entity__ {generation: $g}) WITH [l IN labels(e) WHERE NOT l STARTS WITH '__'] AS ls, e.name AS name, "
        "count(*) AS n WHERE n > 1 RETURN count(*) AS groups", g=generation)
    return int(records[0]["groups"])
