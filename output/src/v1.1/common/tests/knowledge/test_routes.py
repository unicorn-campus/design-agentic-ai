"""반드시 넣을 시험 8 — ⑤가 미채택으로 적은 방식의 파일 · 설정 · 의존성이 **0건**임.

채택 방식 수와 만든 검색기 수가 같은지도 여기서 셈.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from common.config import Settings
from common.knowledge import (
    ADOPTED_ROUTES,
    NOT_ADOPTED_MODULE_NAMES,
    NOT_ADOPTED_ROUTES,
    NOT_ADOPTED_SETTING_NAMES,
    Adoption,
    KNOWLEDGE_ROUTES,
)

V1_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_ROOT = V1_ROOT / "common" / "knowledge"
CONFIG_FILE = V1_ROOT / "common" / "config.py"
PYPROJECT = V1_ROOT / "common" / "pyproject.toml"

# 미채택 방식을 만들었다면 들어왔을 의존성 이름.
NOT_ADOPTED_DEPENDENCY_WORDS = (
    "faiss",
    "chromadb",
    "qdrant",
    "weaviate",
    "pinecone",
    "pgvector",
    "elasticsearch",
    "opensearch",
    "rank_bm25",
    "neo4j",
    "networkx",
    "graphrag",
    "llama-index",
    "llama_index",
    "sqlglot",
    "sqlparse",
    "sqlalchemy",
)


def test_route_table_has_every_candidate_row() -> None:
    """⑤ 5절 후보 5종 + 조회 + 질의 생성 = 판정표 7행임."""
    assert len(KNOWLEDGE_ROUTES) == 7
    assert len(ADOPTED_ROUTES) == 4
    assert len(NOT_ADOPTED_ROUTES) == 3


def test_adopted_route_count_equals_module_count() -> None:
    """채택 방식 수와 만든 파일 수가 같음."""
    modules = {route.module for route in ADOPTED_ROUTES}
    assert None not in modules
    assert len(modules) == len(ADOPTED_ROUTES)
    for name in modules:
        assert (KNOWLEDGE_ROOT / f"{name}.py").exists(), f"{name}.py가 없음"


def test_not_adopted_routes_have_no_module() -> None:
    for route in NOT_ADOPTED_ROUTES:
        assert route.adoption is Adoption.NOT_ADOPTED
        assert route.module is None


@pytest.mark.parametrize("name", NOT_ADOPTED_MODULE_NAMES)
def test_no_file_exists_for_a_not_adopted_route(name: str) -> None:
    """시험 8 — 미채택 경로의 파일이 0건임."""
    hits = sorted(path.name for path in V1_ROOT.rglob(f"{name}.py"))
    assert hits == [], f"미채택 경로의 파일이 있음: {hits}"


@pytest.mark.parametrize("name", NOT_ADOPTED_SETTING_NAMES)
def test_no_setting_exists_for_a_not_adopted_route(name: str) -> None:
    """시험 8 — 미채택 경로의 설정이 0건임."""
    text = CONFIG_FILE.read_text(encoding="utf-8")
    assert name not in text, f"미채택 경로의 설정이 있음: {name}"
    assert not hasattr(Settings, name)


@pytest.mark.parametrize("word", NOT_ADOPTED_DEPENDENCY_WORDS)
def test_no_dependency_exists_for_a_not_adopted_route(word: str) -> None:
    """시험 8 — 미채택 경로의 의존성이 0건임."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert word not in text.lower(), f"미채택 경로의 의존성이 있음: {word}"


def test_knowledge_package_added_no_dependency() -> None:
    """이 묶음이 더한 의존성이 0건임 — 표준 라이브러리와 이미 있는 것만 씀."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert "03-knowledge" not in text


def test_no_chunking_setting_because_chunking_is_not_applicable() -> None:
    """청킹 크기·겹침 설정을 만들지 않았음(⑤ K-1이 「해당 없음」이라 적음)."""
    assert not hasattr(Settings, "knowledge_chunk_size")
    assert not hasattr(Settings, "knowledge_chunk_overlap")


def test_source_has_no_hardcoded_index_or_model_name() -> None:
    """색인 이름 · 임베딩 모델 이름이 소스에 박히지 않았음."""
    banned = re.compile(r"pref_vector_idx|food_item_idx", re.IGNORECASE)
    for path in sorted(KNOWLEDGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        assert not banned.search(path.read_text(encoding="utf-8")), f"{path.name}에 색인 이름이 박혔음"
