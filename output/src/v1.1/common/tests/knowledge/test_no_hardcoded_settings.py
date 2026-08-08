"""소스에 후보 수 · 크기 · 임계값 · 모델 이름 · 제품 이름이 박히지 않았는지 스스로 확인함."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

KNOWLEDGE_ROOT = Path(__file__).resolve().parents[2] / "knowledge"

# ⑤가 소유한 숫자. 소스에 이 값이 정수 상수로 나오면 안 됨.
DESIGN_OWNED_NUMBERS = {30, 500, 3, 5, 12, 20, 37, 13, 10, 1000, 100, 200, 50, 7}

PRODUCT_PATTERN = re.compile(
    r"faiss|chroma|qdrant|weaviate|pinecone|pgvector|elasticsearch|opensearch|milvus|redis",
    re.IGNORECASE,
)
MODEL_PATTERN = re.compile(
    r"text-embedding|embedding-\d|voyage|cohere|e5-|bge-", re.IGNORECASE
)


def _sources() -> list[Path]:
    return sorted(
        path for path in KNOWLEDGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts
    )


def test_sources_were_found() -> None:
    assert _sources()


@pytest.mark.parametrize("path", _sources(), ids=lambda p: p.name)
def test_no_design_owned_number_in_source(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = sorted(
        {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, int)
            and not isinstance(node.value, bool)
            and node.value in DESIGN_OWNED_NUMBERS
        }
    )
    assert not found, f"{path.name}에 설계서 소유 숫자가 박혀 있음: {found}"


@pytest.mark.parametrize("path", _sources(), ids=lambda p: p.name)
def test_no_index_product_name_in_source(path: Path) -> None:
    hits = PRODUCT_PATTERN.findall(path.read_text(encoding="utf-8"))
    assert not hits, f"{path.name}에 색인 제품 이름이 박혀 있음: {hits}"


@pytest.mark.parametrize("path", _sources(), ids=lambda p: p.name)
def test_no_embedding_model_name_in_source(path: Path) -> None:
    hits = MODEL_PATTERN.findall(path.read_text(encoding="utf-8"))
    assert not hits, f"{path.name}에 임베딩 모델 이름이 박혀 있음: {hits}"


def test_every_adopted_spec_field_has_a_setting() -> None:
    """⑤ 「채택 방식별 필수 스펙」의 칸마다 설정 이름이 1개씩 있음."""
    from common.config import Settings

    expected = {
        "knowledge_index_name",
        "knowledge_corpus_scope",
        "knowledge_corpus_as_of",
        "knowledge_chunking",
        "knowledge_embedding_model_version",
        "knowledge_search_mode",
        "knowledge_top_k",
        "knowledge_rerank_enabled",
        "knowledge_rerank_weights",
        "knowledge_rerank_keep",
        "knowledge_metadata_filter_keys",
        "knowledge_attribute_axes",
        "knowledge_radius_m",
        "knowledge_sort_primary",
        "knowledge_glossary_apply_points",
        "knowledge_query_expansion_enabled",
        "knowledge_index_build_suffix",
        "knowledge_result_merge",
        "knowledge_result_cache_ttl_s",
        "knowledge_low_confidence_signal",
        "knowledge_vector_index_product",
    }
    missing = sorted(name for name in expected if name not in Settings.model_fields)
    assert missing == [], f"설정으로 안 옮긴 스펙 칸이 있음: {missing}"


def test_embedding_model_name_setting_is_reused_not_duplicated() -> None:
    """임베딩 모델 이름은 공통 런타임의 설정을 그대로 씀 — 이름을 두 벌 만들지 않았음."""
    from common.config import Settings

    assert "embedding_model" in Settings.model_fields
    assert "knowledge_embedding_model" not in Settings.model_fields
