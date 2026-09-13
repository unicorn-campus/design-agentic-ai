"""Hybrid 후보 10건을 BAAI 리랭커로 3건까지 줄이는 실행 예시."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from src.adaptive_search import (
    ensure_decomposition_coverage,
    select_and_transform,
    weighted_rrf,
)
from src.evaluation import load_cases
from src.hybrid_search_ref import search_hybrid
from src.rerank_ref import RERANK_MODEL, rerank_each_query_and_merge
from src.s32_bridge import S32_ROOT, configure_s32


BASE = Path(__file__).resolve().parent
TRANSFORM_CACHE = BASE / "results/query_transform_cache.json"


def save_transform(cache_path: Path, query: str, decision) -> None:
    """변환 결과를 JSON으로 저장하여 다음 실행에서 재사용함."""
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    cache[query] = {
        "action": decision.action,
        "technique": decision.technique,
        "queries": list(decision.queries),
        "reason": decision.reason,
        "clarification": decision.clarification,
        "error": decision.error,
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_transform(cache_path: Path, query: str):
    """캐시된 변환 결과를 읽음. 없으면 명확한 오류를 냄."""
    from src.adaptive_search import RouteDecision

    if not cache_path.exists():
        raise FileNotFoundError(f"변환 캐시가 없음: {cache_path}")
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    value = cache.get(query)
    if not value:
        raise KeyError("변환 캐시에서 현재 질문을 찾지 못함")
    return RouteDecision(
        action=value.get("action", "keep"),
        technique=value.get("technique"),
        queries=tuple(value.get("queries", [])),
        reason=value.get("reason", ""),
        clarification=value.get("clarification", ""),
        error=value.get("error", ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="S3.3 슬라이드 27 리랭킹 실행")
    parser.add_argument("--query", default="연회비 면제 조건은?")
    parser.add_argument(
        "--case-id",
        help="templates/baseline_questions.json에서 질문을 읽음(한글 인자 깨짐 방지)",
    )
    parser.add_argument("--retrieve-k", type=int, default=10)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument(
        "--query-transform",
        action="store_true",
        help="LLM으로 변환하고 결과를 캐시에 저장한 뒤 Hybrid 검색함",
    )
    parser.add_argument(
        "--reuse-transform",
        action="store_true",
        help="저장된 변환 질문을 읽어 LLM 없이 Hybrid 검색함",
    )
    parser.add_argument(
        "--merge-strategy",
        choices=("auto", "legacy", "coverage"),
        default="auto",
        help="복합 질문 병합 규칙: 기존 가중 RRF legacy, 하위 질문별 후보 보장 coverage",
    )
    parser.add_argument(
        "--transform-cache",
        type=Path,
        default=TRANSFORM_CACHE,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE / "results/rerank_slide27_actual.json",
    )
    args = parser.parse_args()

    query = args.query
    if args.case_id:
        cases = load_cases(BASE / "templates/baseline_questions.json")
        matched = [case.question for case in cases if case.case_id == args.case_id]
        if not matched:
            raise ValueError(f"질문 파일에서 {args.case_id}를 찾지 못함")
        query = matched[0]

    configure_s32(
        db_path=S32_ROOT / "data/chroma/group1",
        collection="card_docs_ref",
        model="nlpai-lab/KURE-v1",
    )

    if args.query_transform and args.reuse_transform:
        raise ValueError("--query-transform과 --reuse-transform은 함께 사용할 수 없음")

    transform_started = perf_counter()
    if args.query_transform:
        decision = select_and_transform(query)
        save_transform(args.transform_cache, query, decision)
    elif args.reuse_transform:
        decision = load_transform(args.transform_cache, query)
    else:
        decision = None
    transform_ms = (perf_counter() - transform_started) * 1000

    search_started = perf_counter()
    original_hits = search_hybrid(query, top_k=args.retrieve_k)
    transformed_queries = list(decision.queries) if decision else []
    transformed_groups = [
        search_hybrid(transformed_query, top_k=args.retrieve_k)
        for transformed_query in transformed_queries
    ]
    is_decomposition = bool(decision and decision.technique == "decomposition")
    strategy = args.merge_strategy
    if strategy == "auto":
        strategy = "coverage" if is_decomposition else "legacy"
    if strategy == "legacy":
        original_weight = 0.5
        rerank_technique = None
    else:
        original_weight = 0.1
        rerank_technique = "decomposition" if is_decomposition else None
    query_groups = [("original", query, original_hits, original_weight)]
    transformed_weight = (
        (1 - original_weight) / len(transformed_groups)
        if transformed_groups else 0
    )
    query_groups.extend(
        (f"transformed_{index}", transformed_query, hits, transformed_weight)
        for index, (transformed_query, hits)
        in enumerate(zip(transformed_queries, transformed_groups), start=1)
    )
    merged = weighted_rrf(
        [(label, hits, weight) for label, _, hits, weight in query_groups]
    )
    if is_decomposition and strategy != "legacy":
        merged = ensure_decomposition_coverage(merged, transformed_groups)
    candidates = [item["hit"] for item in merged[:args.retrieve_k]]
    search_ms = (perf_counter() - search_started) * 1000

    rerank_started = perf_counter()
    final_hits = rerank_each_query_and_merge(
        query_groups,
        technique=rerank_technique,
        top_n=args.top_n,
        decomposition_original_weight=original_weight,
    )
    rerank_ms = (perf_counter() - rerank_started) * 1000

    result = {
        "query": query,
        "model": RERANK_MODEL,
        "query_transform": {
            "enabled": args.query_transform,
            "reused": args.reuse_transform,
            "cache": str(args.transform_cache),
            "technique": decision.technique if decision else None,
            "queries": transformed_queries,
            "llm_calls": 1 if args.query_transform else 0,
        },
        "merge": {
            "original_weight": original_weight,
            "transformed_weight": transformed_weight,
            "strategy": (
                {
                    "legacy": "weighted_rrf",
                    "coverage": "decomposition_top3_max_rerank",
                }[strategy]
            ),
        },
        "candidate_count": len(candidates),
        "returned_count": len(final_hits),
        "timing_ms": {
            "hybrid_search": round(search_ms, 1),
            "query_transform": round(transform_ms, 1),
            "rerank": round(rerank_ms, 1),
            "total": round(transform_ms + search_ms + rerank_ms, 1),
        },
        "before": [
            {
                "rank": rank,
                "chunk_id": hit.metadata.get("chunk_id", ""),
                "search_score": hit.score,
            }
            for rank, hit in enumerate(candidates, start=1)
        ],
        "after": [
            {
                "rank": rank,
                "chunk_id": hit.metadata.get("chunk_id", ""),
                "search_score": hit.score,
                "rerank_score": hit.rerank_score,
                "merge_score": getattr(hit, "merge_score", None),
                "location": hit.metadata.get("clause_no", ""),
                "source": hit.metadata.get("source", ""),
            }
            for rank, hit in enumerate(final_hits, start=1)
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
