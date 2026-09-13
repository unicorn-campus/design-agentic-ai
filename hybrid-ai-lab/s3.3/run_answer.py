"""슬라이드 28-1의 Groq 조건 확인 답변 프롬프트 실행기."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from src.answering import answer_with_condition_prompt, build_answer_prompt
from src.evaluation import load_cases
from src.hybrid_search_ref import search_hybrid
from src.rerank_ref import rerank_each_query_and_merge
from src.s32_bridge import S32_ROOT, configure_s32


BASE = Path(__file__).resolve().parent
QUESTIONS = BASE / "templates/baseline_questions.json"
DEFAULT_CACHE = BASE / "results/q6_practical_transform_cache.json"
DEFAULT_OUTPUT = BASE / "results/slide28_1_answer_actual.json"


def load_cached_decision(cache_path: Path, question: str) -> dict:
    """저장된 질문 변환 기법과 변환 질문을 읽음."""
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if question not in cache:
        raise KeyError("변환 캐시에서 질문을 찾지 못함")
    return cache[question]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="슬라이드 28-1 조건 확인 답변")
    parser.add_argument("--case-id", default="q6")
    parser.add_argument("--transform-cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--prompt-only", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    configure_s32(
        db_path=S32_ROOT / "data/chroma/group1",
        collection="card_docs_ref",
        model="nlpai-lab/KURE-v1",
    )
    cases = load_cases(QUESTIONS)
    case = next((item for item in cases if item.case_id == args.case_id), None)
    if case is None:
        raise ValueError(f"질문 파일에서 {args.case_id}을 찾지 못함")
    decision = load_cached_decision(args.transform_cache, case.question)
    queries = list(decision.get("queries", []))
    technique = decision.get("technique")
    original_weight = 0.1 if technique == "decomposition" else 0.5
    transformed_weight = (1 - original_weight) / len(queries) if queries else 0

    groups = [(
        "original",
        case.question,
        search_hybrid(case.question, top_k=10),
        original_weight if queries else 1.0,
    )]
    groups.extend(
        (
            f"transformed_{index}",
            query,
            search_hybrid(query, top_k=10),
            transformed_weight,
        )
        for index, query in enumerate(queries, start=1)
    )
    hits = rerank_each_query_and_merge(
        groups,
        technique="decomposition" if technique == "decomposition" else None,
        top_n=args.top_n,
        decomposition_original_weight=0.1,
    )
    prompt = build_answer_prompt(case.question, hits)
    answer = None
    llm_response = {}
    if not args.prompt_only:
        answer, llm_response = answer_with_condition_prompt(
            case.question,
            hits,
            return_debug=True,
        )
    result = {
        "question": case.question,
        "technique": technique,
        "transformed_queries": queries,
        "hybrid_weights": {"bm25": 0.4, "vector": 0.6},
        "final_k": args.top_n,
        "top_hits": [
            {
                "rank": rank,
                "chunk_id": hit.metadata.get("chunk_id", ""),
                "card_name": hit.metadata.get("card_name", ""),
                "source": hit.metadata.get("source", ""),
                "location": hit.metadata.get("clause_no", ""),
            }
            for rank, hit in enumerate(hits, start=1)
        ],
        "prompt": prompt,
        "answer": answer,
        "llm_response": llm_response,
        "llm_calls": (
            0
            if args.prompt_only
            else llm_response.get("attempt_count", 1)
        ),
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
