"""운영 어댑터가 Retriever 포트를 명시적으로 구현하는지 검증함."""

import inspect

import pytest

from app.application.graph import _BudgetedLLM, _LazyHuggingFaceEmbedder
from app.application.ports import (
    BM25Port,
    CorpusPort,
    EmbedderPort,
    LLMPort,
    RerankerPort,
    TransformCachePort,
    VectorCatalogPort,
    VectorSearchPort,
    VectorStorePort,
)
from app.infrastructure.bm25_index import BM25Index
from app.infrastructure.chroma_store import ChromaVectorStore, MemoryVectorStore
from app.infrastructure.corpus_store import VersionedCorpusStore
from app.infrastructure.llm_client import LangChainLLMClient
from app.infrastructure.reranker import CrossEncoderReranker
from app.infrastructure.transform_cache import TransformCache


PORTS = (
    EmbedderPort,
    VectorSearchPort,
    VectorCatalogPort,
    VectorStorePort,
    CorpusPort,
    BM25Port,
    RerankerPort,
    LLMPort,
    TransformCachePort,
)

IMPLEMENTATIONS = (
    (_LazyHuggingFaceEmbedder, EmbedderPort),
    (_BudgetedLLM, LLMPort),
    (MemoryVectorStore, VectorStorePort),
    (ChromaVectorStore, VectorStorePort),
    (VersionedCorpusStore, CorpusPort),
    (BM25Index, BM25Port),
    (CrossEncoderReranker, RerankerPort),
    (LangChainLLMClient, LLMPort),
    (TransformCache, TransformCachePort),
)


@pytest.mark.parametrize("port", PORTS)
def test_incomplete_explicit_port_implementation_cannot_be_instantiated(port) -> None:
    incomplete = type(f"Incomplete{port.__name__}", (port,), {})

    with pytest.raises(TypeError, match="abstract"):
        incomplete()


@pytest.mark.parametrize(("implementation", "port"), IMPLEMENTATIONS)
def test_operational_implementation_explicitly_completes_port(
    implementation,
    port,
) -> None:
    assert port in implementation.__mro__
    assert not inspect.isabstract(implementation)

