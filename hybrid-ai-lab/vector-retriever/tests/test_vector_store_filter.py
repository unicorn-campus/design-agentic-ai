"""벡터 DB 중립 필터와 Chroma 변환 시험."""

import pytest

from app.domain.access import build_filter
from app.domain.search_filter import MetadataFilter
from app.domain.vector_search import VectorSearchOptions
from app.infrastructure.chroma_store import (
    ChromaVectorStore,
    MemoryVectorStore,
    _to_chroma_where,
    create_vector_store,
)


def test_chroma_where_conversion_stays_inside_adapter() -> None:
    metadata_filter = build_filter("agent", {"source": "D1.pdf"})

    assert _to_chroma_where(metadata_filter) == {
        "$and": [
            {"access_level": {"$in": ["internal", "public"]}},
            {"source": "D1.pdf"},
        ]
    }


def test_empty_filter_converts_to_no_chroma_constraint() -> None:
    assert _to_chroma_where(MetadataFilter()) == {}


def test_vector_store_factory_selects_backend_independently_from_embedder(tmp_path) -> None:
    store = create_vector_store(
        backend="memory",
        path=tmp_path,
        collection="unused",
        signature="test-signature",
    )
    assert isinstance(store, MemoryVectorStore)

    try:
        create_vector_store(
            backend="unsupported",
            path=tmp_path,
            collection="unused",
            signature="test-signature",
        )
    except ValueError as error:
        assert "벡터 저장소 백엔드" in str(error)
    else:
        raise AssertionError("지원하지 않는 저장소 백엔드는 실패해야 함")


def test_memory_store_applies_allowed_values_and_equality_together() -> None:
    store = MemoryVectorStore(signature="test")
    store.upsert(
        ids=["public-d1", "internal-d2", "restricted-d1"],
        texts=["공개 D1", "내부 D2", "제한 D1"],
        embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
        metadatas=[
            {"access_level": "public", "source": "D1.pdf"},
            {"access_level": "internal", "source": "D2.pdf"},
            {"access_level": "restricted", "source": "D1.pdf"},
        ],
    )

    hits = store.search([1.0, 0.0], 10, build_filter("agent", {"source": "D1.pdf"}))

    assert [hit.chunk_id for hit in hits] == ["public-d1"]
    assert hits[0].score == 1.0


def test_memory_store_mmr_preserves_similarity_scores_and_adds_diversity() -> None:
    store = MemoryVectorStore(signature="test")
    store.upsert(
        ids=["a", "b", "c"],
        texts=["가장 가까운 문서", "중복 문서", "다른 관점 문서"],
        embeddings=[[1.0, 0.0], [0.99, 0.1], [0.0, 1.0]],
        metadatas=[{"access_level": "public"}] * 3,
    )

    similarity_hits = store.search([1.0, 0.0], 2, build_filter("agent"))
    mmr_hits = store.search(
        [1.0, 0.0],
        2,
        build_filter("agent"),
        VectorSearchOptions(strategy="mmr", fetch_multiplier=2, lambda_mult=0.3),
    )

    assert [hit.chunk_id for hit in similarity_hits] == ["a", "b"]
    assert [hit.chunk_id for hit in mmr_hits] == ["a", "c"]
    assert [hit.vector_score for hit in mmr_hits] == [1.0, 0.0]
    assert [hit.score for hit in mmr_hits] == [1.0, 0.0]


def test_chroma_store_translates_filter_and_preserves_score_semantics() -> None:
    class RecordingCollection:
        def __init__(self) -> None:
            self.query_kwargs = {}

        def query(self, **kwargs):
            self.query_kwargs = kwargs
            return {
                "ids": [["public-d1"]],
                "documents": [["공개 D1"]],
                "metadatas": [[{"access_level": "public", "source": "D1.pdf"}]],
                "distances": [[0.25]],
            }

    collection = RecordingCollection()
    store = object.__new__(ChromaVectorStore)
    store._collection = collection

    hits = store.search([1.0, 0.0], 5, build_filter("agent", {"source": "D1.pdf"}))

    assert collection.query_kwargs["where"] == {
        "$and": [
            {"access_level": {"$in": ["internal", "public"]}},
            {"source": "D1.pdf"},
        ]
    }
    assert collection.query_kwargs["n_results"] == 5
    assert hits[0].score == 0.75
    assert hits[0].vector_score == 0.75


def test_chroma_store_mmr_uses_filtered_fetch_pool_and_selection_order() -> None:
    class RecordingCollection:
        def __init__(self) -> None:
            self.query_kwargs = {}

        def query(self, **kwargs):
            self.query_kwargs = kwargs
            # 요청한 fetch_k보다 실제 필터 통과 문서가 적은 경우도 안전하게 처리함.
            return {
                "ids": [["a", "b", "c"]],
                "documents": [["가장 가까운 문서", "중복 문서", "다른 관점 문서"]],
                "metadatas": [[{"access_level": "public"}] * 3],
                "distances": [[0.0, 0.005, 1.0]],
                "embeddings": [[[1.0, 0.0], [0.99, 0.1], [0.0, 1.0]]],
            }

    collection = RecordingCollection()
    store = object.__new__(ChromaVectorStore)
    store._collection = collection
    options = VectorSearchOptions(
        strategy="mmr",
        fetch_multiplier=2,
        lambda_mult=0.3,
    )

    hits = store.search(
        [1.0, 0.0],
        2,
        build_filter("agent", {"source": "D1.pdf"}),
        options,
    )

    assert collection.query_kwargs["n_results"] == 4
    assert collection.query_kwargs["include"] == [
        "documents",
        "metadatas",
        "distances",
        "embeddings",
    ]
    assert collection.query_kwargs["where"] == {
        "$and": [
            {"access_level": {"$in": ["internal", "public"]}},
            {"source": "D1.pdf"},
        ]
    }
    assert [hit.chunk_id for hit in hits] == ["a", "c"]
    assert [hit.vector_score for hit in hits] == [1.0, 0.0]


def test_vector_search_options_reject_invalid_direct_values() -> None:
    for kwargs in (
        {"strategy": "unknown"},
        {"fetch_multiplier": 0},
        {"fetch_multiplier": "2"},
        {"lambda_mult": -0.1},
        {"lambda_mult": 1.1},
        {"lambda_mult": True},
        {"lambda_mult": "0.5"},
    ):
        with pytest.raises(ValueError):
            VectorSearchOptions(**kwargs)
