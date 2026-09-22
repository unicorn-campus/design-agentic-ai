"""벡터 검색 전략과 저장소 공통 MMR 선택 규칙."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence


VectorSearchStrategy = Literal["similarity", "mmr"]


@dataclass(frozen=True)
class VectorSearchOptions:
    """저장소가 동일한 의미로 적용할 벡터 후보 선택 옵션."""

    strategy: VectorSearchStrategy = "similarity"
    fetch_multiplier: int = 2
    lambda_mult: float = 0.5

    def __post_init__(self) -> None:
        if self.strategy not in {"similarity", "mmr"}:
            raise ValueError("벡터 검색 전략은 similarity 또는 mmr이어야 함")
        if (
            isinstance(self.fetch_multiplier, bool)
            or not isinstance(self.fetch_multiplier, int)
            or self.fetch_multiplier <= 0
        ):
            raise ValueError("MMR 후보 확장 배수는 양의 정수여야 함")
        if (
            isinstance(self.lambda_mult, bool)
            or not isinstance(self.lambda_mult, (int, float))
            or not math.isfinite(self.lambda_mult)
            or not 0.0 <= self.lambda_mult <= 1.0
        ):
            raise ValueError("MMR lambda 값은 0 이상 1 이하여야 함")

    def fetch_k(self, k: int) -> int:
        """MMR 계산 전에 유사도로 가져올 후보 수를 반환함."""

        if isinstance(k, bool) or not isinstance(k, int) or k < 0:
            raise ValueError("벡터 검색 결과 수는 0 이상의 정수여야 함")
        if self.strategy == "similarity":
            return k
        return max(k, k * self.fetch_multiplier)


DEFAULT_VECTOR_SEARCH_OPTIONS = VectorSearchOptions()


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("질의와 후보 임베딩 차원이 일치해야 함")
    if len(left) == 0:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    denominator = left_norm * right_norm
    return 0.0 if denominator == 0.0 else dot / denominator


def maximal_marginal_relevance_indices(
    query_embedding: Sequence[float],
    candidate_embeddings: Sequence[Sequence[float]],
    *,
    k: int,
    lambda_mult: float,
) -> list[int]:
    """질의 관련성과 이미 선택한 후보와의 차이를 함께 고려해 인덱스를 선택함."""

    if isinstance(k, bool) or not isinstance(k, int):
        raise ValueError("MMR 선택 수는 정수여야 함")
    if (
        isinstance(lambda_mult, bool)
        or not isinstance(lambda_mult, (int, float))
        or not math.isfinite(lambda_mult)
        or not 0.0 <= lambda_mult <= 1.0
    ):
        raise ValueError("MMR lambda 값은 0 이상 1 이하여야 함")
    if k <= 0 or len(query_embedding) == 0 or len(candidate_embeddings) == 0:
        return []

    query_similarities = [
        _cosine_similarity(query_embedding, candidate)
        for candidate in candidate_embeddings
    ]
    remaining = list(range(len(candidate_embeddings)))
    first = max(remaining, key=lambda index: (query_similarities[index], -index))
    selected = [first]
    remaining.remove(first)

    while remaining and len(selected) < min(k, len(candidate_embeddings)):
        def score(index: int) -> tuple[float, int]:
            redundancy = max(
                _cosine_similarity(
                    candidate_embeddings[index],
                    candidate_embeddings[selected_index],
                )
                for selected_index in selected
            )
            mmr_score = (
                lambda_mult * query_similarities[index]
                - (1.0 - lambda_mult) * redundancy
            )
            return mmr_score, -index

        chosen = max(remaining, key=score)
        selected.append(chosen)
        remaining.remove(chosen)

    return selected
