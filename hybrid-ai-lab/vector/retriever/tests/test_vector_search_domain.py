"""저장소 공통 벡터 검색 옵션과 MMR 선택 알고리즘 시험."""

import numpy as np
import pytest

from app.domain.vector_search import (
    VectorSearchOptions,
    maximal_marginal_relevance_indices,
)


def test_mmr_balances_relevance_and_diversity_in_selection_order() -> None:
    selected = maximal_marginal_relevance_indices(
        [1.0, 0.0],
        [[1.0, 0.0], [0.99, 0.1], [0.0, 1.0]],
        k=2,
        lambda_mult=0.3,
    )

    assert selected == [0, 2]


def test_mmr_ties_use_original_candidate_order_and_zero_vectors_are_safe() -> None:
    selected = maximal_marginal_relevance_indices(
        [0.0, 0.0],
        [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
        k=5,
        lambda_mult=0.5,
    )

    assert selected == [0, 1, 2]


def test_mmr_accepts_chroma_numpy_candidate_embeddings() -> None:
    selected = maximal_marginal_relevance_indices(
        np.asarray([1.0, 0.0], dtype=np.float32),
        np.asarray(
            [[1.0, 0.0], [0.99, 0.1], [0.0, 1.0]],
            dtype=np.float32,
        ),
        k=2,
        lambda_mult=0.3,
    )

    assert selected == [0, 2]


def test_mmr_empty_inputs_and_non_positive_k_return_no_selection() -> None:
    assert maximal_marginal_relevance_indices([], [[1.0]], k=1, lambda_mult=0.5) == []
    assert maximal_marginal_relevance_indices([1.0], [], k=1, lambda_mult=0.5) == []
    assert maximal_marginal_relevance_indices([1.0], [[1.0]], k=0, lambda_mult=0.5) == []


def test_mmr_rejects_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="차원"):
        maximal_marginal_relevance_indices(
            [1.0, 0.0],
            [[1.0]],
            k=1,
            lambda_mult=0.5,
        )


def test_fetch_k_never_falls_below_requested_result_count() -> None:
    similarity = VectorSearchOptions()
    mmr = VectorSearchOptions(strategy="mmr", fetch_multiplier=3)

    assert similarity.fetch_k(4) == 4
    assert mmr.fetch_k(4) == 12
    assert mmr.fetch_k(0) == 0
