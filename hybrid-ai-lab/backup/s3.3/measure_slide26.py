"""슬라이드 26의 Vector baseline과 Hybrid Search를 같은 조건으로 측정함.

Query Transformation과 LLM 답변 생성은 호출하지 않음.
"""

import json
from pathlib import Path

from src.evaluation import evaluate_cases, load_cases
from src.hybrid_search_ref import search_hybrid
from src.s32_bridge import S32_ROOT, configure_s32, get_search


BASE = Path(__file__).resolve().parent
QUESTIONS = BASE / "templates/baseline_questions.json"
OUTPUT = BASE / "results/slide26_hybrid_actual.json"
WEIGHTS = ((0.4, 0.6), (0.6, 0.4), (0.2, 0.8))


def ensure_agent_access(hits):
    """상담원에게 허용되지 않은 restricted 청크가 있으면 측정을 중단함."""
    restricted = [
        hit.metadata.get("chunk_id", "")
        for hit in hits
        if hit.metadata.get("access_level") == "restricted"
    ]
    if restricted:
        raise RuntimeError(f"권한 필터를 통과한 restricted 청크: {restricted}")
    return hits


def run() -> dict:
    """원 질문만 사용하여 Baseline과 Hybrid 세 조합을 측정함."""
    config = configure_s32(
        db_path=S32_ROOT / "data/chroma/group1",
        collection="card_docs_ref",
        model="nlpai-lab/KURE-v1",
    )
    cases = load_cases(QUESTIONS)
    vector_search = get_search(reference=True)

    def baseline_search(query, top_k, filters, user_role):
        return ensure_agent_access(
            vector_search(query, top_k, filters, user_role)
        )

    baseline = evaluate_cases(
        cases,
        baseline_search,
        mode="baseline",
        retrieve_k=10,
        judge_k=3,
        user_role="agent",
    )

    hybrid_results = []
    for w_bm25, w_vec in WEIGHTS:
        def weighted_search(query, top_k, filters, user_role):
            return ensure_agent_access(
                search_hybrid(
                    query,
                    top_k=top_k,
                    w_bm25=w_bm25,
                    w_vec=w_vec,
                    filters=filters,
                    user_role=user_role,
                )
            )

        measured = evaluate_cases(
            cases,
            weighted_search,
            mode="baseline",  # 원 질문 1개만 전달하여 변환을 수행하지 않음
            retrieve_k=10,
            judge_k=3,
            user_role="agent",
        )
        measured["w_bm25"] = w_bm25
        measured["w_vec"] = w_vec
        hybrid_results.append(measured)

    return {
        "experiment": "slide26_hybrid_search_only",
        "controls": {
            "original_questions_only": True,
            "query_transformation": False,
            "llm_answer_generation": False,
            "retrieve_k": 10,
            "judge_k": 3,
            "user_role": "agent",
            "restricted_hits": 0,
            "unscorable_case": "q7",
        },
        "db_path": str(config.db_path),
        "collection": config.collection,
        "model": config.model,
        "baseline": baseline,
        "hybrid": hybrid_results,
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
        "baseline": {
            "passed": result["baseline"]["passed_count"],
            "scored": result["baseline"]["scored_count"],
        },
        "hybrid": [
            {
                "weights": f'{item["w_bm25"]}:{item["w_vec"]}',
                "passed": item["passed_count"],
                "scored": item["scored_count"],
            }
            for item in result["hybrid"]
        ],
    }, ensure_ascii=False, indent=2))
