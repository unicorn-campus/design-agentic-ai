"""슬라이드 26의 Query Transformation + Hybrid Search를 질문별로 측정함."""

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
from src.s32_bridge import S32_ROOT, configure_s32, get_search


BASE = Path(__file__).resolve().parent
QUESTIONS = BASE / "templates/baseline_questions.json"
OUTPUT = BASE / "results/slide26_transform_hybrid_actual.json"
THRESHOLD = 0.70
RETRIEVE_K = 10
JUDGE_K = 3
W_BM25 = 0.4
W_VEC = 0.6
RRF_K = 60


def chunk_id(hit) -> str:
    return str(hit.metadata.get("chunk_id", ""))


def ranks_of(hits, expected_ids) -> dict[str, int | None]:
    ids = [chunk_id(hit) for hit in hits]
    return {
        expected: ids.index(expected) + 1 if expected in ids else None
        for expected in expected_ids
    }


def is_top3(ranks: dict[str, int | None], scorable: bool) -> bool | None:
    if not scorable:
        return None
    return all(rank is not None and rank <= JUDGE_K for rank in ranks.values())


def hybrid(query: str):
    hits = search_hybrid(
        query,
        top_k=RETRIEVE_K,
        w_bm25=W_BM25,
        w_vec=W_VEC,
        filters=None,
        user_role="agent",
    )
    restricted = [
        chunk_id(hit)
        for hit in hits
        if hit.metadata.get("access_level") == "restricted"
    ]
    if restricted:
        raise RuntimeError(f"권한 필터를 통과한 restricted 청크: {restricted}")
    return hits


def run() -> dict:
    config = configure_s32(
        db_path=S32_ROOT / "data/chroma/group1",
        collection="card_docs_ref",
        model="nlpai-lab/KURE-v1",
    )
    vector_search = get_search(reference=True)
    cases = load_cases(QUESTIONS)

    # 모델과 BM25 색인의 최초 로드 시간을 질문별 지연에서 제외함.
    vector_search(cases[0].question, RETRIEVE_K, None, "agent")
    hybrid(cases[0].question)

    rows = []
    for case in cases:
        baseline_started = perf_counter()
        baseline_hits = vector_search(
            case.question, RETRIEVE_K, None, "agent"
        )
        baseline_ms = (perf_counter() - baseline_started) * 1000
        baseline_top1 = baseline_hits[0].score if baseline_hits else None
        gate_sufficient = (
            baseline_top1 is not None and baseline_top1 >= THRESHOLD
        )

        if gate_sufficient:
            decision = None
            transform_ms = 0.0
        else:
            transform_started = perf_counter()
            decision = select_and_transform(case.question)
            transform_ms = (perf_counter() - transform_started) * 1000
        transformed_queries = list(decision.queries) if decision else []

        hybrid_started = perf_counter()
        original_hits = hybrid(case.question)
        transformed_groups = [hybrid(query) for query in transformed_queries]
        if transformed_groups:
            original_weight = (
                0.1
                if decision and decision.technique == "decomposition"
                else 0.5
            )
            transformed_weight = (1 - original_weight) / len(transformed_groups)
            ranked = weighted_rrf(
                [("original", original_hits, original_weight)]
                + [
                    (f"transformed_{index}", hits, transformed_weight)
                    for index, hits in enumerate(transformed_groups, start=1)
                ],
                rrf_k=RRF_K,
            )
            if decision and decision.technique == "decomposition":
                ranked = ensure_decomposition_coverage(
                    ranked, transformed_groups
                )
            final_hits = [item["hit"] for item in ranked[:RETRIEVE_K]]
        else:
            original_weight = 1.0
            transformed_weight = 0.0
            final_hits = original_hits
        hybrid_rrf_ms = (perf_counter() - hybrid_started) * 1000

        scorable = bool(case.expected_chunk_ids)
        baseline_ranks = ranks_of(baseline_hits, case.expected_chunk_ids)
        final_ranks = ranks_of(final_hits, case.expected_chunk_ids)
        rows.append({
            "id": case.case_id,
            "question": case.question,
            "expected_chunk_ids": list(case.expected_chunk_ids),
            "baseline": {
                "top3_chunk_ids": [chunk_id(hit) for hit in baseline_hits[:3]],
                "ranks": baseline_ranks,
                "top3_included": is_top3(baseline_ranks, scorable),
                "top1_similarity": baseline_top1,
            },
            "gate_sufficient": gate_sufficient,
            "route_action": "gate_pass" if decision is None else decision.action,
            "technique": None if decision is None else decision.technique,
            "transformed_queries": transformed_queries,
            "route_reason": "" if decision is None else decision.reason,
            "route_error": "" if decision is None else decision.error,
            "clarification": "" if decision is None else decision.clarification,
            "query_transform_hybrid": {
                "top3_chunk_ids": [chunk_id(hit) for hit in final_hits[:3]],
                "ranks": final_ranks,
                "top3_included": is_top3(final_ranks, scorable),
                "merge_weights": {
                    "original": original_weight,
                    "transformed_total": 1 - original_weight,
                    "transformed_each": transformed_weight,
                },
            },
            "timing_ms": {
                "baseline_gate": round(baseline_ms, 1),
                "query_transform": round(transform_ms, 1),
                "hybrid_and_rrf": round(hybrid_rrf_ms, 1),
                "total_query_transform_hybrid": round(
                    transform_ms + hybrid_rrf_ms, 1
                ),
            },
            "scorable": scorable,
            "note": case.note,
        })

    scored_rows = [row for row in rows if row["scorable"]]
    return {
        "experiment": "slide26_query_transformation_plus_hybrid",
        "controls": {
            "warm_run": True,
            "threshold": THRESHOLD,
            "retrieve_k": RETRIEVE_K,
            "judge_k": JUDGE_K,
            "w_bm25": W_BM25,
            "w_vec": W_VEC,
            "rrf_k": RRF_K,
            "decomposition_original_weight": 0.1,
            "decomposition_transformed_total": 0.9,
            "llm_answer_generation": False,
            "timing_scope": (
                "optional LLM query transformation + "
                "original/transformed hybrid searches + RRF; "
                "baseline gate excluded"
            ),
        },
        "config": {
            "db_path": str(config.db_path),
            "collection": config.collection,
            "model": config.model,
        },
        "case_count": len(rows),
        "scored_count": len(scored_rows),
        "baseline_passed": sum(
            row["baseline"]["top3_included"] for row in scored_rows
        ),
        "final_passed": sum(
            row["query_transform_hybrid"]["top3_included"]
            for row in scored_rows
        ),
        "llm_call_count": sum(not row["gate_sufficient"] for row in rows),
        "rows": rows,
    }


if __name__ == "__main__":
    result = run()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(OUTPUT),
        "baseline": f'{result["baseline_passed"]}/{result["scored_count"]}',
        "query_transform_hybrid": (
            f'{result["final_passed"]}/{result["scored_count"]}'
        ),
        "llm_calls": result["llm_call_count"],
        "times_ms": {
            row["id"]: row["timing_ms"]["total_query_transform_hybrid"]
            for row in result["rows"]
        },
    }, ensure_ascii=False, indent=2))
