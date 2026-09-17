"""질문 변환 판정·가중 RRF·분해 질의 커버리지 규칙."""

from __future__ import annotations

from typing import Any

from ..application.state import Hit, RouteDecision


TECHNIQUES = {"rewrite", "multi", "hyde", "stepback", "decomposition"}
ROUTER_SYSTEM_PROMPT = """당신은 한국어 카드 상담 문서 검색용 질의 라우터임.
원 질문의 상품명, 기간, 금액, 수치, 조건, 의도를 빠뜨리거나 새 사실을 만들지 않음.
clarify, keep, transform 중 하나와 한 가지 기법만 구조화 출력함."""
ROUTER_USER_PROMPT = """원 질문: {query}
multi는 서로 다른 표현 3개, decomposition은 서로 다른 답의 대상별 2~4개,
rewrite·hyde·stepback은 1개 질의를 생성함. 원 질문을 queries에 반복하지 않음."""


def assess_transform_gate(
    *,
    transform_mode: str,
    gate_score: float | None,
    gate_threshold: float,
) -> dict[str, Any]:
    """질문 변환 계획을 실행할지 점수만으로 판정함."""

    if transform_mode == "off":
        return {
            "route_action": "off",
            "transform_review_required": False,
            "transformed_queries": [],
        }
    if transform_mode != "auto":
        raise ValueError("transform_mode는 off 또는 auto여야 함")
    if gate_score is not None and gate_score >= gate_threshold:
        return {
            "route_action": "gate_pass",
            "transform_review_required": False,
            "transformed_queries": [],
        }
    return {"transform_review_required": True}


def plan_query_transform(
    query: str,
    *,
    router=None,
    cache=None,
    max_tokens: int = 500,
) -> dict[str, Any]:
    """변환 검토가 필요하다고 판정된 질문의 계획을 캐시 또는 LLM으로 생성함."""

    decision = cache.get(query) if cache is not None else None
    cache_hit = decision is not None
    calls = 0
    if decision is None:
        if router is None:
            return {"route_action": "keep", "technique": None, "transformed_queries": [], "llm_calls": 0, "transform_cache_hit": False, "route_error": "라우터가 없음"}
        result = router.complete_structured(
            ROUTER_SYSTEM_PROMPT,
            ROUTER_USER_PROMPT.format(query=query),
            RouteDecision,
            max_tokens=max_tokens,
        )
        decision = getattr(result, "parsed", result)
        attempts = getattr(result, "attempts", 1)
        calls = int(attempts) if isinstance(attempts, int) and not isinstance(attempts, bool) and attempts >= 0 else 1
    try:
        validated = validate_route_decision(decision, query)
    except (TypeError, ValueError) as error:
        return {"route_action": "keep", "technique": None, "transformed_queries": [], "llm_calls": calls, "transform_cache_hit": cache_hit, "route_error": str(error)}
    if not cache_hit and cache is not None:
        cache.put(query, validated)
    return {
        "route_action": validated.action,
        "technique": validated.technique,
        "transformed_queries": list(validated.queries),
        "route_reason": validated.reason,
        "clarification": validated.clarification,
        "llm_calls": calls,
        "transform_cache_hit": cache_hit,
        "route_error": "",
    }


def route_query(
    query: str,
    *,
    transform_mode: str,
    gate_score: float | None,
    gate_threshold: float,
    router=None,
    cache=None,
    max_tokens: int = 500,
) -> dict[str, Any]:
    """기존 호출자를 위한 변환 관문·계획 결합 호환 함수임."""

    gate = assess_transform_gate(
        transform_mode=transform_mode,
        gate_score=gate_score,
        gate_threshold=gate_threshold,
    )
    if not gate.get("transform_review_required"):
        return {
            **gate,
            "technique": None,
            "llm_calls": 0,
            "transform_cache_hit": False,
        }
    return plan_query_transform(
        query,
        router=router,
        cache=cache,
        max_tokens=max_tokens,
    )


def validate_route_decision(decision: RouteDecision | dict[str, Any], original_query: str) -> RouteDecision:
    value = decision if isinstance(decision, RouteDecision) else RouteDecision.model_validate(decision)
    if value.action in {"keep", "clarify"}:
        if value.technique is not None or value.queries:
            raise ValueError(f"{value.action}은 technique과 queries가 없어야 함")
        if value.action == "clarify" and not value.clarification.strip():
            raise ValueError("clarify에는 확인 질문이 필요함")
        return value
    if value.technique not in TECHNIQUES:
        raise ValueError("지원하지 않는 질문 변환 기법")
    queries = [query.strip() for query in value.queries if query.strip()]
    if len(set(queries)) != len(queries) or original_query.strip() in queries:
        raise ValueError("변환 질의는 중복되거나 원 질문과 같을 수 없음")
    count = len(queries)
    if value.technique == "multi" and count != 3:
        raise ValueError("multi의 변환 질의 수는 정확히 3개여야 함")
    if value.technique == "decomposition" and not 2 <= count <= 4:
        raise ValueError("decomposition 하위 질문 수는 2~4개여야 함")
    if value.technique not in {"multi", "decomposition"} and count != 1:
        raise ValueError(f"{value.technique}의 변환 질의 수는 정확히 1개여야 함")
    return value.model_copy(update={"queries": queries})


def _hit_id(hit: Hit) -> str:
    return hit.chunk_id


def weighted_rrf(ranked_lists: list[tuple[str, list[Hit], float]], *, rrf_k: int) -> list[dict[str, Any]]:
    if rrf_k < 0:
        raise ValueError("rrf_k는 0 이상이어야 함")
    merged: dict[str, dict[str, Any]] = {}
    for label, hits, weight in ranked_lists:
        if weight <= 0:
            raise ValueError("RRF 가중치는 양수여야 함")
        for position, hit in enumerate(hits, start=1):
            item = merged.setdefault(hit.chunk_id, {"hit": hit, "rrf_score": 0.0, "source_ranks": {}})
            item["rrf_score"] += weight / (rrf_k + position)
            item["source_ranks"][label] = position
    return sorted(merged.values(), key=lambda item: (-item["rrf_score"], min(item["source_ranks"].values()), _hit_id(item["hit"])))


def ensure_decomposition_coverage(
    ranked: list[dict[str, Any]],
    hit_groups: list[list[Hit]],
    *,
    per_query_top_k: int = 1,
) -> list[dict[str, Any]]:
    """각 하위 질의의 상위 N개를 한 번씩 먼저 보존함."""

    if per_query_top_k <= 0:
        raise ValueError("per_query_top_k는 양수여야 함")
    by_id = {item["hit"].chunk_id: item for item in ranked}
    reserved, ids = [], set()
    for hits in hit_groups:
        for hit in hits[:per_query_top_k]:
            if hit.chunk_id in by_id and hit.chunk_id not in ids:
                reserved.append(by_id[hit.chunk_id])
                ids.add(hit.chunk_id)
    return reserved + [item for item in ranked if item["hit"].chunk_id not in ids]


def merge_query_groups(
    baseline_hits: list[Hit],
    transformed_hit_groups: list[list[Hit]],
    *,
    technique: str | None,
    rrf_k: int,
    original_weight: float,
    decomposition_original_weight: float,
    decomposition_per_query_top_k: int,
    top_k: int,
) -> tuple[list[Hit], dict[str, float], bool]:
    if not transformed_hit_groups:
        return baseline_hits[:top_k], {}, False
    weight = decomposition_original_weight if technique == "decomposition" else original_weight
    each = (1.0 - weight) / len(transformed_hit_groups)
    lists = [("original", baseline_hits, weight)] + [
        (f"transformed_{index}", hits, each)
        for index, hits in enumerate(transformed_hit_groups, start=1)
    ]
    ranked = weighted_rrf(lists, rrf_k=rrf_k)
    coverage = technique == "decomposition"
    if coverage:
        ranked = ensure_decomposition_coverage(
            ranked,
            transformed_hit_groups,
            per_query_top_k=decomposition_per_query_top_k,
        )
    weights = {"original": weight, "transformed_each": each}
    return [item["hit"].model_copy(update={"score": round(item["rrf_score"], 6)}) for item in ranked[:top_k]], weights, coverage


def rerank_each_query_and_merge(
    query_groups: list[tuple[str, str, list[Hit], float]],
    reranker,
    *,
    technique: str | None,
    top_n: int,
    rrf_k: int,
    decomposition_original_weight: float,
    decomposition_per_query_top_k: int,
) -> list[Hit]:
    """각 후보군을 그 후보군을 만든 질의로 점수화한 후 병합함."""

    reranked_lists = []
    for label, query, hits, weight in query_groups:
        scores = reranker.score(query, [hit.text for hit in hits]) if hits else []
        updated = [hit.model_copy(update={"rerank_score": float(score)}) for hit, score in zip(hits, scores)]
        updated.sort(key=lambda hit: (-float(hit.rerank_score), -hit.score, hit.chunk_id))
        reranked_lists.append((label, updated, weight))
    if technique == "decomposition":
        # 복합 질문은 각 하위 질문의 Top-N을 후보로 보장하고, 같은 청크가
        # 여러 하위 질문에 등장하면 가장 높은 리랭커 점수를 사용함.
        # 원 질문 점수는 계획서대로 0.1 가중치의 보조 신호로만 사용함.
        original = reranked_lists[0][1] if reranked_lists else []
        transformed = [items for _, items, _ in reranked_lists[1:]]
        by_id: dict[str, dict[str, Any]] = {}

        def add_hit(
            hit: Hit,
            *,
            transformed_score: float | None = None,
            original_score: float | None = None,
        ) -> None:
            item = by_id.setdefault(
                hit.chunk_id,
                {"hit": hit, "transformed_scores": [], "original_score": 0.0},
            )
            if transformed_score is not None:
                item["transformed_scores"].append(transformed_score)
            if original_score is not None:
                item["original_score"] = max(item["original_score"], original_score)

        for hit in original:
            add_hit(hit, original_score=float(hit.rerank_score or 0.0))
        for hits in transformed:
            for hit in hits[:decomposition_per_query_top_k]:
                add_hit(hit, transformed_score=float(hit.rerank_score or 0.0))

        scored: list[tuple[float, float, Hit]] = []
        for item in by_id.values():
            transformed_score = max(item["transformed_scores"], default=0.0)
            original_score = float(item["original_score"])
            if transformed_score:
                merge_score = (
                    (1.0 - decomposition_original_weight) * transformed_score
                    + decomposition_original_weight * original_score
                )
            else:
                merge_score = decomposition_original_weight * original_score
            merged_hit = item["hit"].model_copy(update={"rerank_score": merge_score})
            scored.append((merge_score, transformed_score, merged_hit))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2].chunk_id))
        return [item[2] for item in scored[:top_n]]
    return [item["hit"] for item in weighted_rrf(reranked_lists, rrf_k=rrf_k)[:top_n]]
