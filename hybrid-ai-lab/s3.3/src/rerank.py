"""검색 후보를 BAAI/bge-reranker-v2-m3로 다시 정렬함."""

from __future__ import annotations

import os

import torch
from sentence_transformers import CrossEncoder

from .adaptive_search import weighted_rrf


RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# 모델은 프로그램 시작 때 한 번만 읽음. 질의마다 다시 읽으면 매우 느려짐.
RERANKER = CrossEncoder(RERANK_MODEL, max_length=512)

DECOMPOSITION_ORIGINAL_WEIGHT = 0.1
DECOMPOSITION_PER_QUERY_TOP_K = 3


def rerank(query: str, hits: list, top_n: int = 5) -> list:
    """질문과 후보를 함께 읽고 관련성이 높은 후보만 반환함."""
    if not query.strip():
        raise ValueError("질문이 비어 있음")
    if top_n <= 0:
        raise ValueError("top_n은 양수여야 함")
    if not hits:
        return []

    # Cross-Encoder는 (질문, 청크) 쌍을 입력으로 받음.
    pairs = [(query, hit.text) for hit in hits]
    scores = RERANKER.predict(
        pairs,
        activation_fn=torch.nn.Sigmoid(),
        show_progress_bar=False,
    )

    for hit, score in zip(hits, scores):
        # 기존 검색 점수는 보존하고 리랭커 점수만 별도 필드에 저장함.
        hit.rerank_score = float(score)

    return sorted(
        hits,
        key=lambda hit: (-hit.rerank_score, -hit.score),
    )[:top_n]


def rerank_each_query_and_merge(
    query_groups: list[tuple[str, str, list, float]],
    *,
    technique: str | None = None,
    top_n: int = 5,
    rrf_k: int = 60,
    decomposition_original_weight: float = DECOMPOSITION_ORIGINAL_WEIGHT,
    decomposition_per_query_top_k: int = DECOMPOSITION_PER_QUERY_TOP_K,
) -> list:
    """원 질문과 변환 질문을 각각 리랭킹한 뒤 기법에 맞게 병합함."""
    if top_n <= 0:
        raise ValueError("top_n은 양수여야 함")
    reranked_lists = []
    for label, search_query, hits, weight in query_groups:
        reranked = rerank(search_query, hits, top_n=len(hits)) if hits else []
        reranked_lists.append((label, reranked, weight))

    if technique == "decomposition":
        # 복합 질문은 하위 질문마다 답이 있을 수 있으므로, RRF만 사용하면
        # 한 하위 질문의 정답이 반복 등장하는 다른 청크에 밀릴 수 있음.
        # 하위 질문별 상위 후보를 보장한 뒤 리랭커 점수의 최댓값으로 병합함.
        original = reranked_lists[0][1] if reranked_lists else []
        transformed = [items[1] for items in reranked_lists[1:]]
        by_id: dict[str, dict] = {}

        def add_hit(hit, *, transformed_score: float | None = None,
                    original_score: float | None = None):
            chunk_id = str(hit.metadata.get("chunk_id", "")).strip()
            if not chunk_id:
                return
            item = by_id.setdefault(
                chunk_id,
                {"hit": hit, "transformed_scores": [], "original_score": 0.0},
            )
            if transformed_score is not None:
                item["transformed_scores"].append(transformed_score)
            if original_score is not None:
                item["original_score"] = max(item["original_score"], original_score)

        # 원 질문 결과는 0.1 가중치의 보조 후보로 사용함.
        for hit in original:
            add_hit(hit, original_score=float(hit.rerank_score))
        # 하위 질문마다 Top3를 후보로 보장함.
        for hits in transformed:
            for hit in hits[:decomposition_per_query_top_k]:
                add_hit(hit, transformed_score=float(hit.rerank_score))

        scored = []
        for item in by_id.values():
            transformed_score = max(item["transformed_scores"], default=0.0)
            original_score = item["original_score"]
            if transformed_score:
                merge_score = (
                    (1 - decomposition_original_weight) * transformed_score
                    + decomposition_original_weight * original_score
                )
            else:
                merge_score = decomposition_original_weight * original_score
            item["merge_score"] = merge_score
            item["hit"].merge_score = float(merge_score)
            scored.append(item)

        scored.sort(
            key=lambda item: (
                -item["merge_score"],
                -max(item["transformed_scores"], default=0.0),
                str(item["hit"].metadata.get("chunk_id", "")),
            )
        )

        return [item["hit"] for item in scored[:top_n]]

    merged = weighted_rrf(reranked_lists, rrf_k=rrf_k)
    return [item["hit"] for item in merged[:top_n]]
