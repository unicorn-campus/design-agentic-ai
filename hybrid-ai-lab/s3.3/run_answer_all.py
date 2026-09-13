"""고정 질문 8건의 리랭킹 Top-5와 Groq 답변을 한 번에 실행함."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from src.answering import answer_with_condition_prompt
from src.evaluation import load_cases
from src.hybrid_search_ref import search_hybrid
from src.rerank_ref import rerank_each_query_and_merge
from src.s32_bridge import S32_ROOT, configure_s32


BASE = Path(__file__).resolve().parent
QUESTIONS = BASE / "templates/baseline_questions.json"
TRANSFORMS = BASE / "results/adaptive_top1_070_updated.json"
OUTPUT = BASE / "results/slide28_1_all_answers_actual.json"


def load_decisions(path: Path) -> dict[str, dict]:
    """저장된 질문 변환 결과를 질문 ID로 찾을 수 있게 바꿈."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row for row in data["rows"]}


def build_query_groups(question: str, decision: dict) -> list[tuple]:
    """원 질문과 변환 질문의 Hybrid Top-10 목록을 만듦."""
    queries = list(decision.get("transformed_queries", []))
    technique = decision.get("technique")
    original_weight = 0.1 if technique == "decomposition" else 0.5
    transformed_weight = (1 - original_weight) / len(queries) if queries else 0
    groups = [(
        "original",
        question,
        search_hybrid(question, top_k=10),
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
    return groups


def main() -> int:
    configure_s32(
        db_path=S32_ROOT / "data/chroma/group1",
        collection="card_docs_ref",
        model="nlpai-lab/KURE-v1",
    )
    decisions = load_decisions(TRANSFORMS)
    rows = []
    for case in load_cases(QUESTIONS):
        started = perf_counter()
        decision = decisions[case.case_id]
        groups = build_query_groups(case.question, decision)
        hits = rerank_each_query_and_merge(
            groups,
            technique=(
                "decomposition"
                if decision.get("technique") == "decomposition"
                else None
            ),
            top_n=5,
            decomposition_original_weight=0.1,
        )
        retrieval_ms = (perf_counter() - started) * 1000
        answer, llm_response = answer_with_condition_prompt(
            case.question,
            hits,
            return_debug=True,
        )
        expected = list(case.expected_chunk_ids)
        rank_by_id = {
            hit.metadata.get("chunk_id", ""): rank
            for rank, hit in enumerate(hits, start=1)
        }
        expected_ranks = {
            chunk_id: rank_by_id.get(chunk_id)
            for chunk_id in expected
        }
        rows.append({
            "id": case.case_id,
            "question": case.question,
            "technique": decision.get("technique"),
            "transformed_queries": decision.get("transformed_queries", []),
            "expected_chunk_ids": expected,
            "expected_ranks": expected_ranks,
            "rerank_correct": (
                all(rank is not None for rank in expected_ranks.values())
                if expected
                else None
            ),
            "top_hits": [
                {
                    "rank": rank,
                    "chunk_id": hit.metadata.get("chunk_id", ""),
                    "location": hit.metadata.get("clause_no", ""),
                    "card_name": hit.metadata.get("card_name", ""),
                }
                for rank, hit in enumerate(hits, start=1)
            ],
            "answer": answer,
            "llm_response": llm_response,
            "llm_calls": llm_response.get("attempt_count", 1),
            "retrieval_rerank_ms": round(retrieval_ms, 1),
        })
        print(
            f"{case.case_id}: rerank={expected_ranks or '평가 제외'}, "
            f"answer_valid={answer['verification']['automatic_valid']}, "
            f"llm_calls={llm_response.get('attempt_count', 1)}, "
            f"llm_ms={llm_response.get('elapsed_ms', 0)}"
        )

    result = {
        "model": "openai/gpt-oss-120b",
        "case_count": len(rows),
        "scored_count": sum(row["rerank_correct"] is not None for row in rows),
        "rerank_pass_count": sum(row["rerank_correct"] is True for row in rows),
        "automatic_answer_valid_count": sum(
            row["answer"]["verification"]["automatic_valid"] for row in rows
        ),
        "rows": rows,
    }
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"saved={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
