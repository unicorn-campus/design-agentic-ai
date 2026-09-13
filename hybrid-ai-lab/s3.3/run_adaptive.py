"""8개 고정 질문으로 적응형 검색 흐름을 실행하고 결과를 저장함."""

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

from src.adaptive_search import adaptive_search
from src.evaluation import load_cases
from src.s32_bridge import S32_ROOT, configure_s32, get_search


BASE = Path(__file__).resolve().parent


def _hit_row(item: dict, rank: int) -> dict:
    hit = item["hit"]
    return {
        "rank": rank,
        "chunk_id": hit.metadata.get("chunk_id", ""),
        "similarity": hit.score,
        "rrf_score": (
            round(item["rrf_score"], 8) if item["rrf_score"] is not None else None
        ),
        "source": hit.metadata.get("source", ""),
        "location": hit.metadata.get("clause_no", ""),
        "source_ranks": item["source_ranks"],
    }


def run_cases(args) -> dict:
    config = configure_s32(
        db_path=args.db_path,
        collection=args.collection,
        model=args.model,
    )
    search_fn = get_search(reference=True)
    cases = load_cases(args.questions)
    if args.case_id:
        requested = set(args.case_id)
        cases = [case for case in cases if case.case_id in requested]
        if not cases:
            raise ValueError(f"질문 파일에서 {', '.join(args.case_id)}을 찾지 못함")
    rows = []
    passed = 0
    scored = 0

    for case in cases:
        started = perf_counter()
        result = adaptive_search(
            case.question,
            search_fn,
            threshold=args.threshold,
            retrieve_k=args.retrieve_k,
            user_role=args.role,
            rrf_k=args.rrf_k,
        )
        final_hits = [
            _hit_row(item, rank)
            for rank, item in enumerate(result["ranked_hits"][:args.judge_k], start=1)
        ]
        baseline_ids = [
            str(hit.metadata.get("chunk_id", "")) for hit in result["baseline_hits"]
        ]
        baseline_ranks = {
            chunk_id: (
                baseline_ids.index(chunk_id) + 1 if chunk_id in baseline_ids else None
            )
            for chunk_id in case.expected_chunk_ids
        }
        all_ids = [
            str(item["hit"].metadata.get("chunk_id", ""))
            for item in result["ranked_hits"]
        ]
        ranks = {
            chunk_id: (all_ids.index(chunk_id) + 1 if chunk_id in all_ids else None)
            for chunk_id in case.expected_chunk_ids
        }
        scorable = bool(case.expected_chunk_ids)
        success = scorable and all(
            rank is not None and rank <= args.judge_k for rank in ranks.values()
        )
        if scorable:
            scored += 1
            passed += int(success)
        rows.append({
            "id": case.case_id,
            "question": case.question,
            "expected_chunk_ids": list(case.expected_chunk_ids),
            "expected_location": case.expected_location,
            "baseline_top1": (
                {
                    "chunk_id": result["baseline_hits"][0].metadata.get("chunk_id", ""),
                    "similarity": result["baseline_top1_score"],
                }
                if result["baseline_hits"] else None
            ),
            "baseline_ranks": baseline_ranks,
            "gate_sufficient": result["gate_sufficient"],
            "route_action": result["route_action"],
            "technique": result["technique"],
            "transformed_queries": result["transformed_queries"],
            "route_reason": result["route_reason"],
            "route_error": result["route_error"],
            "clarification": result["clarification"],
            "coverage_applied": result["coverage_applied"],
            "merge_weights": result.get("merge_weights", {
                "original": 1.0,
                "transformed_total": 0.0,
                "transformed_each": 0.0,
            }),
            "llm_calls": result["llm_calls"],
            "final_hits": final_hits,
            "ranks": ranks,
            "scorable": scorable,
            "top_k_included": success if scorable else None,
            "note": case.note,
            "elapsed_ms": round((perf_counter() - started) * 1000, 1),
        })

    return {
        "method": "top1_gate_single_technique_weighted_rrf_with_decomposition_coverage",
        "threshold": args.threshold,
        "rrf_k": args.rrf_k,
        "weights": {
            "default_original": 0.5,
            "decomposition_original": 0.1,
            "decomposition_transformed_total": 0.9,
        },
        "retrieve_k": args.retrieve_k,
        "judge_k": args.judge_k,
        "case_count": len(cases),
        "scored_count": scored,
        "passed_count": passed,
        "inclusion_rate": round(passed / scored, 4) if scored else None,
        "gate_pass_count": sum(row["gate_sufficient"] for row in rows),
        "gate_fail_count": sum(not row["gate_sufficient"] for row in rows),
        "llm_call_count": sum(row["llm_calls"] for row in rows),
        "config": {
            "db_path": str(config.db_path),
            "collection": config.collection,
            "model": config.model,
        },
        "rows": rows,
    }


def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def render_markdown(result: dict) -> str:
    judge_label = f"Top-{result['judge_k']}"
    lines = [
        "# Top-1 관문 기반 적응형 검색 결과",
        "",
        f"- 관문: 원 질문 Top-1 코사인 유사도 ≥ `{result['threshold']:.2f}`",
        f"- 관문 통과/실패: {result['gate_pass_count']}/{result['gate_fail_count']}",
        f"- LLM 호출: {result['llm_call_count']}회",
        "- 병합: 일반 변환은 원 질문 0.5 + 변환 전체 0.5, Decomposition은 원 질문 0.1 + 하위 질문 전체 0.9",
        "- Decomposition: 하위 질문별 1위 청크를 한 건씩 보존한 뒤 RRF 순위 적용",
        f"- {judge_label} 통과: {result['passed_count']}/{result['scored_count']}",
        "",
        f"| # | 질문 | Baseline Top-1 | Baseline 정답 순위 | 관문 | 선택 기법 | 변환 질문 | 최종 {judge_label} | 최종 정답 순위 | 판정 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in result["rows"]:
        baseline = row["baseline_top1"]
        baseline_text = (
            f"{baseline['chunk_id']} ({baseline['similarity']:.3f})" if baseline else "없음"
        )
        gate = "충분" if row["gate_sufficient"] else "부족"
        baseline_rank_text = ", ".join(
            f"{chunk_id}:{rank or 'Top-10 밖'}"
            for chunk_id, rank in row["baseline_ranks"].items()
        ) or "정답 미매핑"
        technique = row["technique"] or {
            "clarify": "사용자 확인",
            "keep": "원 결과 유지",
            "gate_pass": "미적용",
        }.get(row["route_action"], "미적용")
        transformed = "<br>".join(row["transformed_queries"]) or "-"
        top_ids = ", ".join(hit["chunk_id"] for hit in row["final_hits"]) or "없음"
        rank_text = ", ".join(
            f"{chunk_id}:{rank or '없음'}" for chunk_id, rank in row["ranks"].items()
        ) or "정답 미매핑"
        verdict = "○" if row["top_k_included"] else (
            "×" if row["scorable"] else "평가 제외"
        )
        values = [
            row["id"], row["question"], baseline_text, baseline_rank_text, gate, technique,
            transformed, top_ids, rank_text, verdict,
        ]
        lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Top-1 관문 기반 적응형 검색 평가")
    parser.add_argument("--questions", type=Path, default=BASE / "templates/baseline_questions.json")
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--retrieve-k", type=int, default=10)
    parser.add_argument("--judge-k", type=int, default=3)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--db-path", type=Path, default=S32_ROOT / "data/chroma/group1")
    parser.add_argument("--collection", default="card_docs_ref")
    parser.add_argument("--model", default="nlpai-lab/KURE-v1")
    parser.add_argument("--role", choices=("agent", "auditor"), default="agent")
    parser.add_argument(
        "--case-id",
        action="append",
        help="지정한 질문 ID만 실행함. 여러 번 지정 가능: --case-id q3 --case-id q6",
    )
    parser.add_argument("--output", type=Path, default=BASE / "results/adaptive_top1_070.md")
    parser.add_argument("--json-output", type=Path, default=BASE / "results/adaptive_top1_070.json")
    args = parser.parse_args()

    try:
        result = run_cases(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(result), encoding="utf-8")
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(render_markdown(result))
        print(f"Markdown 저장: {args.output}")
        print(f"JSON 저장: {args.json_output}")
        return 0
    except (ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"실행 중단: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
