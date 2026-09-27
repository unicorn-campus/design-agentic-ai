"""슬라이드 28의 튜닝된 Hybrid Search와 Re-ranking을 실측함.

저장된 Query Transformation 결과를 재사용하므로 LLM은 호출하지 않음.
Hybrid 가중치는 BM25 0.4, Vector 0.6을 사용함.
Decomposition은 원 질문 0.1, 하위 질문 전체 0.9로 검색함.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from src.adaptive_search import ensure_decomposition_coverage, weighted_rrf
from src.evaluation import load_cases
from src.hybrid_search_ref import search_hybrid
from src.rerank_ref import RERANK_MODEL, rerank, rerank_each_query_and_merge
from src.s32_bridge import S32_ROOT, configure_s32, get_search


BASE = Path(__file__).resolve().parent
QUESTIONS = BASE / "templates/baseline_questions.json"
TRANSFORM_RESULT = BASE / "results/adaptive_top1_070_updated.json"
OUTPUT = BASE / "results/slide28_rerank_actual.json"
JUDGE_K = 5
RETRIEVE_K = 10


def ensure_agent_access(hits):
    """상담원에게 허용되지 않은 restricted 청크가 없는지 확인함."""
    restricted = [
        hit.metadata.get("chunk_id", "")
        for hit in hits
        if hit.metadata.get("access_level") == "restricted"
    ]
    if restricted:
        raise RuntimeError(f"권한 필터를 통과한 restricted 청크: {restricted}")
    return hits


def load_transform_decisions() -> dict[str, dict]:
    """앞 단계에서 저장한 기법과 변환 질문을 질문 ID별로 읽음."""
    data = json.loads(TRANSFORM_RESULT.read_text(encoding="utf-8"))
    return {
        row["id"]: {
            "technique": row.get("technique"),
            "queries": list(row.get("transformed_queries", [])),
        }
        for row in data["rows"]
    }


def rank_of(chunk_id: str, hits: list) -> int | None:
    """최종 결과에서 정답 청크의 1부터 시작하는 순위를 반환함."""
    return next(
        (
            rank
            for rank, hit in enumerate(hits, start=1)
            if hit.metadata.get("chunk_id") == chunk_id
        ),
        None,
    )


def make_row(case, hits: list, *, search_ms: float, rerank_ms: float,
             technique: str | None = None, transformed_queries=None) -> dict:
    """질문 한 건의 순위·판정·지연을 기록함."""
    ranks = {
        chunk_id: rank_of(chunk_id, hits)
        for chunk_id in case.expected_chunk_ids
    }
    scorable = bool(case.expected_chunk_ids)
    passed = scorable and all(rank is not None for rank in ranks.values())
    return {
        "id": case.case_id,
        "question": case.question,
        "expected_chunk_ids": list(case.expected_chunk_ids),
        "technique": technique,
        "transformed_queries": list(transformed_queries or []),
        "final_top5": [hit.metadata.get("chunk_id", "") for hit in hits],
        "ranks": ranks,
        "scorable": scorable,
        "passed": passed if scorable else None,
        "timing_ms": {
            "hybrid_search": round(search_ms, 1),
            "rerank": round(rerank_ms, 1),
            "total": round(search_ms + rerank_ms, 1),
        },
    }


def summarize(rows: list[dict]) -> dict:
    """질문별 결과에서 포함률·평균 순위·평균 지연을 계산함."""
    scorable_rows = [row for row in rows if row["scorable"]]
    passed_count = sum(bool(row["passed"]) for row in scorable_rows)
    rank_values = [
        rank if rank is not None else JUDGE_K + 1
        for row in scorable_rows
        for rank in row["ranks"].values()
    ]
    return {
        "scored_count": len(scorable_rows),
        "passed_count": passed_count,
        "inclusion_rate": round(passed_count / len(scorable_rows), 4),
        "mean_expected_chunk_rank": round(mean(rank_values), 3),
        "mean_timing_ms": {
            key: round(mean(row["timing_ms"][key] for row in rows), 1)
            for key in ("hybrid_search", "rerank", "total")
        },
        "rows": rows,
    }


def build_query_groups(case, decision: dict) -> list[tuple[str, str, list, float]]:
    """원 질문과 변환 질문을 튜닝된 가중치로 각각 Hybrid 검색함."""
    transformed_queries = decision["queries"]
    technique = decision["technique"]
    original_weight = 0.1 if technique == "decomposition" else (
        0.5 if transformed_queries else 1.0
    )
    groups = [(
        "original",
        case.question,
        ensure_agent_access(search_hybrid(case.question, top_k=RETRIEVE_K)),
        original_weight,
    )]
    if transformed_queries:
        transformed_weight = (1 - original_weight) / len(transformed_queries)
        groups.extend(
            (
                f"transformed_{index}",
                query,
                ensure_agent_access(search_hybrid(query, top_k=RETRIEVE_K)),
                transformed_weight,
            )
            for index, query in enumerate(transformed_queries, start=1)
        )
    return groups


def merge_hybrid(groups, technique: str | None) -> list:
    """질문별 Hybrid 결과를 가중 RRF로 병합함."""
    if len(groups) == 1:
        return groups[0][2][:JUDGE_K]
    merged = weighted_rrf([
        (label, hits, weight) for label, _, hits, weight in groups
    ])
    if technique == "decomposition":
        merged = ensure_decomposition_coverage(
            merged,
            [group[2] for group in groups[1:]],
        )
    return [item["hit"] for item in merged[:JUDGE_K]]


def run() -> dict:
    """기준 검색과 튜닝된 최종 경로를 같은 8개 질문으로 실행함."""
    config = configure_s32(
        db_path=S32_ROOT / "data/chroma/group1",
        collection="card_docs_ref",
        model="nlpai-lab/KURE-v1",
    )
    cases = load_cases(QUESTIONS)
    decisions = load_transform_decisions()
    vector_search = get_search(reference=True)

    # 최초 모델 로딩과 BM25 인덱스 생성을 지연 측정에서 제외함.
    warm_vector = vector_search(cases[0].question, RETRIEVE_K, None, "agent")
    search_hybrid(cases[0].question, top_k=RETRIEVE_K)
    rerank(cases[0].question, warm_vector, top_n=JUDGE_K)

    vector_rows = []
    hybrid_rows = []
    tuned_hybrid_rows = []
    tuned_rerank_rows = []
    for case in cases:
        started = perf_counter()
        vector_hits = ensure_agent_access(
            vector_search(case.question, JUDGE_K, None, "agent")
        )
        vector_ms = (perf_counter() - started) * 1000
        vector_rows.append(make_row(
            case, vector_hits, search_ms=vector_ms, rerank_ms=0.0
        ))

        started = perf_counter()
        hybrid_hits = ensure_agent_access(
            search_hybrid(case.question, top_k=JUDGE_K)
        )
        hybrid_ms = (perf_counter() - started) * 1000
        hybrid_rows.append(make_row(
            case, hybrid_hits, search_ms=hybrid_ms, rerank_ms=0.0
        ))

        decision = decisions[case.case_id]
        started = perf_counter()
        groups = build_query_groups(case, decision)
        groups_search_ms = (perf_counter() - started) * 1000
        merged_hybrid = merge_hybrid(groups, decision["technique"])
        tuned_hybrid_rows.append(make_row(
            case,
            merged_hybrid,
            search_ms=groups_search_ms,
            rerank_ms=0.0,
            technique=decision["technique"],
            transformed_queries=decision["queries"],
        ))

        started = perf_counter()
        reranked = rerank_each_query_and_merge(
            groups,
            technique=(
                "decomposition"
                if decision["technique"] == "decomposition"
                else None
            ),
            top_n=JUDGE_K,
            decomposition_original_weight=0.1,
        )
        rerank_ms = (perf_counter() - started) * 1000
        tuned_rerank_rows.append(make_row(
            case,
            reranked,
            search_ms=groups_search_ms,
            rerank_ms=rerank_ms,
            technique=decision["technique"],
            transformed_queries=decision["queries"],
        ))

    return {
        "experiment": "slide28_tuned_hybrid_reranking_actual",
        "controls": {
            "query_transformation": "reuse_saved_result",
            "transform_source": str(TRANSFORM_RESULT),
            "llm_calls": 0,
            "hybrid_weights": {"bm25": 0.4, "vector": 0.6},
            "decomposition_weights": {"original": 0.1, "transformed": 0.9},
            "retrieve_k_for_rerank": RETRIEVE_K,
            "final_k": JUDGE_K,
            "warm_measurement": True,
            "unscorable_case": "q7",
            "missing_rank_penalty": JUDGE_K + 1,
            "empty_input_returns_empty": rerank("빈 결과", [], top_n=JUDGE_K) == [],
        },
        "db_path": str(config.db_path),
        "collection": config.collection,
        "embedding_model": config.model,
        "rerank_model": RERANK_MODEL,
        "methods": {
            "vector_top5": summarize(vector_rows),
            "hybrid_top5": summarize(hybrid_rows),
            "tuned_transform_hybrid_top5": summarize(tuned_hybrid_rows),
            "tuned_transform_hybrid_rerank_top5": summarize(tuned_rerank_rows),
        },
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
        "controls": result["controls"],
        "methods": {
            name: {
                key: value[key]
                for key in (
                    "passed_count",
                    "scored_count",
                    "inclusion_rate",
                    "mean_expected_chunk_rank",
                    "mean_timing_ms",
                )
            }
            for name, value in result["methods"].items()
        },
    }, ensure_ascii=False, indent=2))
