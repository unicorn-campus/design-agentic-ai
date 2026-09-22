"""질문 변환 판정·가중 RRF·분해 질의 커버리지 규칙."""

from __future__ import annotations

from typing import Any

from ..application.state import Hit, RouteDecision


TECHNIQUES = {"rewrite", "multi", "hyde", "stepback", "decomposition"}
ROUTER_SYSTEM_PROMPT = """[목표]
한국어 카드 상담 질문에 가장 적합한 검색 질의 처리 방식을 결정함.

[역할]
카드 상품·혜택·약관 문서를 검색하기 위한 질의 라우터임.

[맥락]
최초 벡터 검색 점수가 기준보다 낮아 검색 질의를 그대로 유지할지, 확인할지, 변환할지 검토하는 단계임.

[처리]
1. 대상이나 필수 조건이 불명확해 유효한 검색 질의를 만들기 어려우면 clarify 선택함.
2. 한 번의 검색으로 의도와 조건을 충분히 표현한 질문이면 keep 선택함.
3. 질의를 바꾸거나 나누면 검색 가능성이 높아지는 질문이면 transform과 한 가지 기법을 선택함.
4. 단일 의도를 검색 친화적으로 정리할 때 rewrite 선택함.
5. 같은 단일 의도를 서로 다른 표현으로 검색할 때 multi 선택함.
6. 예상 답변이나 문서에 나타날 표현으로 검색할 때 hyde 선택함.
7. 지나치게 구체적인 질문을 관련 원칙이나 상위 개념으로 넓힐 때 stepback 선택함.
8. 서로 독립적인 대상·조건·비교 항목을 각각 검색해야 할 때 decomposition 선택함.

[출력]
RouteDecision 스키마만 구조화 출력함.
- action: clarify, keep, transform 중 하나임.
- technique: transform이면 선택한 기법, clarify·keep이면 null임.
- queries: transform이면 변환 질의 목록, clarify·keep이면 빈 목록임.
- reason: action과 technique 선택 근거를 나타내는 간결한 문장임.
- clarification: clarify이면 사용자에게 필요한 확인 질문, 그 외에는 빈 문자열임.

[제약조건]
- 원 질문의 상품명, 기간, 금액, 수치, 조건, 의도를 모두 보존함.
- 원 질문에 없는 상품, 혜택, 수치, 조건 등 새로운 사실을 만들지 않음.
- transform의 queries는 서로 중복되지 않으며 원 질문 자체를 포함하지 않음.
- 구조화 출력 외의 설명을 출력하지 않음."""

ROUTER_USER_PROMPT = """[입력]
<원질문>
{query}
</원질문>

[처리]
- 시스템의 판단 기준에 따라 action과 필요한 경우 technique을 결정함.
- multi는 서로 다른 표현 3개를 생성함.
- decomposition은 서로 다른 답의 대상별 질의 2~4개를 생성함.
- rewrite·hyde·stepback은 질의 1개를 생성함.
- 생성 질의끼리 중복하지 않고 원 질문 자체를 반복하지 않음."""


def assess_transform_gate(
    *,
    transform_mode: str,
    top_vector_score: float | None,
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
    if top_vector_score is not None and top_vector_score >= gate_threshold:
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
    transform_gate_vector_score: float | None,
    gate_threshold: float,
    router=None,
    cache=None,
    max_tokens: int = 500,
) -> dict[str, Any]:
    """기존 호출자를 위한 변환 관문·계획 결합 호환 함수임."""

    gate = assess_transform_gate(
        transform_mode=transform_mode,
        top_vector_score=transform_gate_vector_score,
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

# 원 질문 검색 결과와 각 변환 질문 검색 결과를 RRF 점수별로 졍렬하여 리턴
def weighted_rrf(ranked_lists: list[tuple[str, list[Hit], float]], *, rrf_k: int) -> list[dict[str, Any]]:
    if rrf_k < 0:
        raise ValueError("rrf_k는 0 이상이어야 함")

    merged: dict[str, dict[str, Any]] = {}
    for label, hits, weight in ranked_lists:    # 원질문과 각 변환 질문의 검색결과에 대해 수행
        if weight <= 0:
            raise ValueError("RRF 가중치는 양수여야 함")

        # 검색결과가 유사도 점수 순으로 정렬되어 있으므로 position은 랭킹값임
        for position, hit in enumerate(hits, start=1):
            item = merged.setdefault(  # chunk_id가 있으면 기존 값을, 없으면 기본값을 저장한 뒤 반환함
                hit.chunk_id,
                {"hit": hit, "rrf_score": 0.0, "source_ranks": {}},
            )

            # RRF score: 가중치 / (RRF 상수 + 랭킹)
            item["rrf_score"] += weight / (rrf_k + position)

            # 목적: 한 청크가 각 검색 결과 그룹에서 몇 위였는지 source_ranks에 그룹별로 누적함.
            # 예시: A, B가 검색 결과 청크
            # original      → A: 1위, B: 2위
            # transformed_1 → B: 1위, C: 2위
            item["source_ranks"][label] = position  # 첫 []로 내부 딕셔너리를 꺼내고 두 번째 [label]에 순위를 저장함

    return sorted(
        merged.values(),  # 정렬할 청크별 RRF 누적 정보
        key=lambda item: (
            -item["rrf_score"],  # RRF 점수가 큰 항목부터 정렬
            min(item["source_ranks"].values()),  # 동점이면 검색 그룹들 중 가장 좋은 순위부터 정렬
            _hit_id(item["hit"]),  # 앞의 두 기준도 같으면 chunk_id 오름차순 정렬
        ),
    )

# 목적: 복합 질문의 일부 하위 질문 결과가 RRF 순위 경쟁에서 모두 밀려나는 것을 방지함.
# 작업: 각 하위 질문의 상위 per_query_top_k개를 먼저 배치하고, 중복을 뺀 나머지 RRF 결과를 기존 순서로 이어 붙임.
def ensure_decomposition_coverage(
    ranked: list[dict[str, Any]],    # RRF 점수로 정렬된 병합된 검색 결과 리스트
    hit_groups: list[list[Hit]],     # 변환 질문 검색결과 리스트
    *,
    per_query_top_k: int = 1,       # 각 변환 질문의 검색 결과 중 상위 몇개를 이용할 지
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


# 가중 RRF 병합 결과를 만들며, decomposition이면 하위 질문별 상위 결과를 앞에 배치함
def merge_query_groups(
    baseline_hits: list[Hit],                   # 원 질문 검색 결과
    transformed_hit_groups: list[list[Hit]],    # 변환 질문 검색 결과
    *,
    technique: str | None,                      # 질문 변환 테크닉
    rrf_k: int,                                 # 원 질문과 변환 질문의 검색 결과 병합 시 순위 차이가 RRF 점수에 미치는 정도를 완화하는 상수(클 수록 많이 완화. 기본은 60)
    original_weight: float,                     # 원 질문에 부여할 기여 가중치
    decomposition_original_weight: float,       # decomposition 기법일 때 원 질문에 부여할 기여 가중치
    decomposition_per_query_top_k: int,         # decomposition의 각 하위 질문의 검색 결과 수
    top_k: int,                                 # 최종 검색 결과 수
) -> tuple[list[Hit], dict[str, float], bool]:

    if not transformed_hit_groups:
        return baseline_hits[:top_k], {}, False
    weight = decomposition_original_weight if technique == "decomposition" else original_weight
    each_weight = (1.0 - weight) / len(transformed_hit_groups)

    """
    lists 객체의 결과
    [
        ("original", baseline_hits, weight),       # 첫 번째 리스트에서 온 튜플
        ("transformed_1", hits1, each_weight),            # 두 번째 리스트에서 만든 튜플들...
        ("transformed_2", hits2, each_weight),
        ...
    ]
    """
    lists = [("original", baseline_hits, weight)] + [
        (f"transformed_{index}", hits, each_weight)
        for index, hits in enumerate(transformed_hit_groups, start=1)
    ]

    # 원 질문 검색 결과와 각 변환 질문 검색 결과를 RRF 점수별로 졍렬하여 리턴
    ranked = weighted_rrf(lists, rrf_k=rrf_k)

    decomposition_coverage_applied = technique == "decomposition"

    if decomposition_coverage_applied:
        
        # 목적: 복합 질문의 일부 하위 질문 결과가 RRF 순위 경쟁에서 모두 밀려나는 것을 방지함.
        # 작업: 각 하위 질문의 상위 per_query_top_k개를 먼저 배치하고, 중복을 뺀 나머지 RRF 결과를 기존 순서로 이어 붙임.
        ranked = ensure_decomposition_coverage(
            ranked,                     # RRF 점수로 정렬된 병합된 검색 결과 리스트
            transformed_hit_groups,     # 변환 질문 검색결과 리스트
            per_query_top_k=decomposition_per_query_top_k,  # 각 변환 질문의 검색 결과 중 상위 몇개를 이용할 지
        )

    weights = {"original": weight, "transformed_each": each_weight}

    return (
        [item["hit"].model_copy(update={"score": round(item["rrf_score"], 6)}) for item in ranked[:top_k]],
        weights,
        decomposition_coverage_applied,
    )


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
    """각 후보군을 해당 후보군을 만든 질문으로 리랭킹한 뒤 최종 결과를 병합함.

    Args:
        query_groups: ``(그룹명, 질문, 검색 결과, 가중치)``로 구성된 원 질문·변환 질문 후보군 목록임.
        reranker: 질문과 각 검색 결과 본문의 관련성 점수를 계산하는 ``TimedReranker`` 객체임.
        technique: ``rewrite``, ``multi``, ``hyde``, ``stepback``, ``decomposition`` 중 적용 기법임.
        top_n: 최종 반환할 검색 결과의 최대 개수임.
        rrf_k: decomposition 이외 기법에서 순위 차이의 영향을 완화하는 RRF 상수임.
        decomposition_original_weight: decomposition에서 원 질문 리랭킹 점수의 기여 가중치임.
        decomposition_per_query_top_k: decomposition에서 각 하위 질문별로 병합에 포함할 상위 후보 수임.

    Returns:
        ``decomposition``이면 하위 질문별 상위 후보를 먼저 확보하고, 동일 청크의 가장 높은 하위 질문
        리랭킹 점수에 원 질문 점수를 보조적으로 더한 결과를 반환함. 그 외 기법이면 각 후보군에서
        리랭킹된 순위를 가중 RRF로 합산한 결과를 반환함.

    Examples:
        원 질문 결과가 ``A=0.80, B=0.70``, 하위 질문 1이 ``B=0.95, C=0.90``, 하위 질문 2가
        ``D=0.92, B=0.85``이고 ``top_n=3``이라고 가정함.

        - decomposition, 원 질문 가중치 0.1: B는 ``0.9×0.95 + 0.1×0.70 = 0.925``가 되고,
          D는 0.828, C는 0.810이 되어 ``[B, D, C]``를 반환함.
        - 그 외 기법: 0.95나 0.92 같은 원점수를 직접 합산하지 않고 각 목록의 1위·2위 순위를
          ``가중치 / (rrf_k + 순위)``로 합산하므로, 예시 가중치에 따라 ``[B, A, D]``처럼 반환될 수 있음.
    """
    
    # 원 질문과 검색결과 텍스트　＋　각 변환 질문과　검색결과로　리랭킹　점수를　산출하고　그　점수순으로　정렬　　
    reranked_lists = []
    for label, query, hits, weight in query_groups:
        # graph.py의 _run_reranker의 score함수가 호출됨. 결국 reranker.py의 score 함수가 호출됨 
        
        # 현재 query(원 질문 또는 각 변환 질의)와 검색 결과 텍스트를 갖고 Cross Ranking 수행하여 점수 리턴  
        scores = reranker.score(query, [hit.text for hit in hits]) if hits else []
        
        updated = [hit.model_copy(update={"rerank_score": float(score)}) for hit, score in zip(hits, scores)]
        
        # reranking 점수로 정렬 
        updated.sort(key=lambda hit: (-float(hit.rerank_score), -hit.score, hit.chunk_id))
        reranked_lists.append((label, updated, weight))
    
    if technique == "decomposition":
        # 복합 질문은 각 하위 질문의 Top-N을 후보로 보장하고, 같은 청크가
        # 여러 하위 질문에 등장하면 가장 높은 리랭커 점수를 사용함.
        # 원 질문 점수는 계획서대로 0.1 가중치의 보조 신호로만 사용함.
        original = reranked_lists[0][1] if reranked_lists else []  # 원 질문 리랭킹 결과
        transformed = [items for _, items, _ in reranked_lists[1:]] # 변환 질문 리랭킹 결과
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

        # 원 질문 검색 결과 점수와 변환 질문 검색 결과 점수를 가중치를 곱한 후 더함
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
        
        # 가중합 점수별로 정렬함     
        scored.sort(key=lambda item: (-item[0], -item[1], item[2].chunk_id))

        """decomposition 반환 예시.

        ``decomposition_original_weight=0.1``이고 각 하위 질문에서 상위 2개를 포함한다고 가정함.
        원 질문 결과는 ``A=0.80, B=0.70``, 하위 질문 결과는 ``B=0.95, C=0.90``과
        ``D=0.92, B=0.85``임.

        동일한 B가 여러 하위 질문에 있으면 가장 높은 변환 질문 점수 0.95를 사용함.
        B의 병합 점수는 ``0.9×0.95 + 0.1×0.70 = 0.925``임. 원 질문 결과에 없는 D와 C는
        각각 ``0.9×0.92 = 0.828``, ``0.9×0.90 = 0.810``임. 하위 질문 결과에 없는 A는
        ``0.1×0.80 = 0.080``임.

        따라서 정렬 결과는 ``B, D, C, A``이며 ``top_n=3``이면 ``[B, D, C]``를 반환함.
        ``scored``의 각 항목은 ``(병합 점수, 변환 질문 최고 점수, Hit)``이므로 ``item[2]``로
        최종 Hit 객체를 꺼냄. 반환되는 Hit의 ``rerank_score``에는 계산된 병합 점수가 저장됨.
        """
        return [item[2] for item in scored[:top_n]]

    """decomposition 이외 기법의 반환 예시.

    원 질문 가중치가 0.5이고 정렬 결과가 ``A 1위, B 2위``, 두 변환 질문의 가중치가 각각
    0.25이며 결과가 ``B 1위, C 2위``와 ``D 1위, B 2위``라고 가정함.
    ``rrf_k=60``이면 후보별 가중 RRF 점수는 다음과 같음.

    - B: ``0.5/62 + 0.25/61 + 0.25/62 ≈ 0.01620``
    - A: ``0.5/61 ≈ 0.00820``
    - D: ``0.25/61 ≈ 0.00410``
    - C: ``0.25/62 ≈ 0.00403``

    따라서 RRF 정렬 결과는 ``B, A, D, C``이며 ``top_n=3``이면 ``[B, A, D]``를 반환함.
    ``weighted_rrf()``의 각 항목은 Hit와 누적 RRF 정보를 담은 딕셔너리이므로
    ``item["hit"]``로 최종 Hit 객체만 꺼냄. 이 경로는 원래 리랭커 점수의 크기를 직접 더하지 않고
    각 후보군 안에서의 순위와 그룹 가중치만 최종 순서 계산에 사용함.
    """
    return [item["hit"] for item in weighted_rrf(reranked_lists, rrf_k=rrf_k)[:top_n]]
