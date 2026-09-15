"""실제 KURE 색인으로 4개 검색 조합의 Top-5 동등성을 평가함.

답변 LLM은 prompt-only로 차단하고, 질문 변환은 확정된 s3.3 결과를
TransformCache 계약으로 변환하여 외부 LLM 호출 없이 재현함.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any
from uuid import uuid4


APP_ROOT = Path(__file__).resolve().parent
LAB_ROOT = APP_ROOT.parents[1]
DEFAULT_QUESTIONS = LAB_ROOT / "s3.3" / "templates" / "baseline_questions.json"
DEFAULT_TRANSFORMS = LAB_ROOT / "s3.3" / "results" / "adaptive_top1_070_updated.json"
DEFAULT_OUTPUT = APP_ROOT / "data" / "equivalence_run1.json"
DEFAULT_CACHE = APP_ROOT / "data" / "equivalence_transform_cache.json"
TOP_K = 5
MISSING_RANK_PENALTY = TOP_K + 1

METHODS = (
    ("vector_top5", "vector", "off", 6, 2.125),
    ("hybrid_top5", "hybrid", "off", 6, 2.375),
    ("tuned_transform_hybrid_top5", "hybrid", "auto", 7, 1.125),
    (
        "tuned_transform_hybrid_rerank_top5",
        "hybrid_rerank",
        "auto",
        7,
        1.375,
    ),
)


class ForbiddenLLM:
    """평가 중 실수로 외부 LLM 경로에 진입하면 즉시 실패시킴."""

    def complete_structured(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("동등성 평가는 외부 LLM을 호출할 수 없음")


def load_scored_cases(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    cases = value.get("cases", [])
    return [case for case in cases if case.get("expected_chunk_ids")]


def build_transform_cache(source: Path, output: Path) -> dict[str, Any]:
    """기존 확정 RouteDecision을 질문 문자열 키의 새 캐시 형식으로 변환함."""

    value = json.loads(source.read_text(encoding="utf-8"))
    cache: dict[str, Any] = {}
    for row in value.get("rows", []):
        queries = list(row.get("transformed_queries", []))
        technique = row.get("technique")
        action = "transform" if technique and queries else (
            "clarify" if row.get("route_action") == "clarify" else "keep"
        )
        cache[str(row["question"]).strip()] = {
            "action": action,
            "technique": technique if action == "transform" else None,
            "queries": queries if action == "transform" else [],
            "reason": str(row.get("route_reason", "")),
            "clarification": str(row.get("clarification", "")),
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output.chmod(0o600)
    return cache


def _rank_of(chunk_id: str, hits: list[Any]) -> int | None:
    return next(
        (rank for rank, hit in enumerate(hits, start=1) if hit.chunk_id == chunk_id),
        None,
    )


def make_row(case: dict[str, Any], result: Any, elapsed_ms: float) -> dict[str, Any]:
    ranks = {
        chunk_id: _rank_of(chunk_id, result.hits)
        for chunk_id in case["expected_chunk_ids"]
    }
    passed = all(rank is not None and rank <= TOP_K for rank in ranks.values())
    rerank_ms = float(result.timings.get("rerank", 0))
    return {
        "id": case["id"],
        "question": case["question"],
        "expected_chunk_ids": list(case["expected_chunk_ids"]),
        "technique": result.route.technique,
        "transformed_queries": list(result.route.transformed_queries),
        "final_top5": [hit.chunk_id for hit in result.hits[:TOP_K]],
        "ranks": ranks,
        "scorable": True,
        "passed": passed,
        "top_hits": [
            {
                "rank": rank,
                "chunk_id": hit.chunk_id,
                "score": hit.score,
                "vector_score": hit.vector_score,
                "rerank_score": hit.rerank_score,
                "source": hit.source,
                "location": hit.location,
            }
            for rank, hit in enumerate(result.hits[:TOP_K], start=1)
        ],
        "route": result.route.model_dump(mode="json"),
        "llm_calls": result.llm_calls,
        "status": result.status,
        "new_vector_transform_gate_score": None,
        "legacy_hybrid_transform_gate_score": None,
        "timing_ms": {
            "hybrid_search": round(max(0.0, elapsed_ms - rerank_ms), 1),
            "rerank": round(rerank_ms, 1),
            "total": round(elapsed_ms, 1),
        },
    }


def summarize(
    rows: list[dict[str, Any]],
    *,
    baseline_passed: int,
    baseline_rank: float,
) -> dict[str, Any]:
    rank_values = [
        rank if rank is not None else MISSING_RANK_PENALTY
        for row in rows
        for rank in row["ranks"].values()
    ]
    passed_count = sum(bool(row["passed"]) for row in rows)
    average_rank = round(mean(rank_values), 3)
    meets_baseline = passed_count >= baseline_passed and average_rank <= baseline_rank
    return {
        "scored_count": len(rows),
        "passed_count": passed_count,
        "inclusion_rate": round(passed_count / len(rows), 4),
        "mean_expected_chunk_rank": average_rank,
        "mean_timing_ms": {
            key: round(mean(row["timing_ms"][key] for row in rows), 1)
            for key in ("hybrid_search", "rerank", "total")
        },
        "baseline": {
            "passed_count": baseline_passed,
            "scored_count": 7,
            "mean_expected_chunk_rank": baseline_rank,
        },
        "meets_baseline": meets_baseline,
        "failed_question_ids": [row["id"] for row in rows if not row["passed"]],
        "rows": rows,
    }


def run(
    *,
    questions_path: Path,
    transforms_path: Path,
    cache_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    from app.application.graph import answer_question, check_health, load_resources
    from app.application.state import RetrieverRequest
    from app.settings import load_settings

    cases = load_scored_cases(questions_path)
    if len(cases) != 7:
        raise RuntimeError(f"평가 가능 질문은 7건이어야 함: {len(cases)}")
    cache = build_transform_cache(transforms_path, cache_path)
    settings = load_settings({"TRANSFORM_CACHE_PATH": cache_path})
    resources = load_resources(settings=settings, llm=ForbiddenLLM())
    health = check_health(resources)
    if health.collection_count != 485 or health.embedding_dimension != 1024:
        raise RuntimeError(
            "동등성 평가 전제 불충족: "
            f"count={health.collection_count}, dimension={health.embedding_dimension}"
        )

    run_id = uuid4().hex[:12]
    methods: dict[str, Any] = {}
    vector_gate_scores: dict[str, float | None] = {}
    hybrid_gate_scores: dict[str, float | None] = {}
    total_llm_calls = 0

    for method_name, mode, transform, baseline_passed, baseline_rank in METHODS:
        rows = []
        for index, case in enumerate(cases, start=1):
            started = perf_counter()
            result = answer_question(
                RetrieverRequest(
                    query=case["question"],
                    top_k=TOP_K,
                    mode=mode,
                    transform=transform,
                    role="agent",
                    thread_id=f"equivalence-{run_id}-{method_name}-{case['id']}",
                    prompt_only=True,
                    max_llm_calls=8,
                ),
                resources,
            )
            elapsed_ms = (perf_counter() - started) * 1000
            # 최종 1위의 원 벡터 점수가 답변 관문보다 낮으면 그래프는
            # 프롬프트 생성 전에 needs_check로 안전 종료함. 검색 결과는
            # 이미 확정되었으므로 동등성 채점 대상으로 인정함.
            if result.status not in {"prompt_only", "needs_check"}:
                raise RuntimeError(
                    f"prompt-only 경로 실패: {method_name}/{case['id']}={result.status}"
                )
            if result.llm_calls != 0:
                raise RuntimeError(
                    f"LLM 호출이 발생함: {method_name}/{case['id']}={result.llm_calls}"
                )
            row = make_row(case, result, elapsed_ms)
            rows.append(row)
            total_llm_calls += result.llm_calls
            if method_name == "vector_top5":
                vector_gate_scores[case["id"]] = (
                    result.hits[0].vector_score if result.hits else None
                )
            elif method_name == "hybrid_top5":
                hybrid_gate_scores[case["id"]] = (
                    result.hits[0].score if result.hits else None
                )
            print(
                json.dumps(
                    {
                        "method": method_name,
                        "case": case["id"],
                        "progress": f"{index}/{len(cases)}",
                        "passed": row["passed"],
                        "ranks": row["ranks"],
                        "elapsed_ms": round(elapsed_ms, 1),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        methods[method_name] = summarize(
            rows,
            baseline_passed=baseline_passed,
            baseline_rank=baseline_rank,
        )

    for method in methods.values():
        for row in method["rows"]:
            row["new_vector_transform_gate_score"] = vector_gate_scores.get(row["id"])
            row["legacy_hybrid_transform_gate_score"] = hybrid_gate_scores.get(row["id"])

    output = {
        "experiment": "vector_final_equivalence_actual",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "controls": {
            "query_transformation": "reuse_saved_result_via_transform_cache",
            "transform_source": str(transforms_path),
            "transform_cache_entries": len(cache),
            "llm_calls": total_llm_calls,
            "answer_llm_calls": 0,
            "router_llm_calls": 0,
            "hybrid_weights": {"bm25": 0.4, "vector": 0.6},
            "decomposition_weights": {"original": 0.1, "transformed": 0.9},
            "final_k": TOP_K,
            "candidate_multiplier": int(settings.CANDIDATE_MULTIPLIER),
            "unscorable_case": "q7",
            "missing_rank_penalty": MISSING_RANK_PENALTY,
            "prompt_only": True,
        },
        "index": health.model_dump(mode="json"),
        "collection": str(settings.CHROMA_COLLECTION),
        "embedding_model": str(settings.EMBED_MODEL),
        "rerank_model": str(settings.RERANK_MODEL),
        "methods": methods,
        "all_methods_meet_baseline": all(
            method["meets_baseline"] for method in methods.values()
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retriever 4조합 동등성 평가")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--transforms", type=Path, default=DEFAULT_TRANSFORMS)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run(
        questions_path=args.questions,
        transforms_path=args.transforms,
        cache_path=args.cache,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "all_methods_meet_baseline": result["all_methods_meet_baseline"],
                "methods": {
                    name: {
                        key: value[key]
                        for key in (
                            "passed_count",
                            "scored_count",
                            "mean_expected_chunk_rank",
                            "meets_baseline",
                            "failed_question_ids",
                        )
                    }
                    for name, value in result["methods"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["all_methods_meet_baseline"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
