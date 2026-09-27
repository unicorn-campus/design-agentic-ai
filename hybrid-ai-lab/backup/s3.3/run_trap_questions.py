"""슬라이드 34의 함정 질문 5건을 현재 검색·답변 경로로 실행함."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.adaptive_search import select_and_transform
from src.answering import answer_with_condition_prompt
from src.groq_client import ask_groq
from src.hybrid_search_ref import search_hybrid
from src.rerank_ref import rerank_each_query_and_merge
from src.s32_bridge import S32_ROOT, ask_llm, configure_s32, get_search


BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "results/slide34_trap_questions_actual.json"

CASES = [
    {
        "id": "t1",
        "type": "약어",
        "question": "무할 조건이 어떻게 되나요?",
        "expected": "무이자할부 조항 검색",
        "expected_chunk_ids": [],
    },
    {
        "id": "t2",
        "type": "오탈자",
        "question": "연회비 몐제 조건은요?",
        "expected": "D1_0010",
        "expected_chunk_ids": ["D1_0010"],
    },
    {
        "id": "t3",
        "type": "다중 조건",
        "question": "연회비 5만원 이상 카드 3장 이상 보유하고 3개월 미사용이면 안내할 대체 카드 조건은?",
        "expected": "D1과 D2의 직접 근거가 모두 있어야 답변",
        "expected_chunk_ids": [],
    },
    {
        "id": "t4",
        "type": "개정 전후",
        "question": "2027-01-15 시행 전 면제 기준은?",
        "expected": "현재 데이터에 이전 버전이 없으므로 확인 필요",
        "expected_chunk_ids": [],
    },
    {
        "id": "t5",
        "type": "범위 밖",
        "question": "타사 카드 해지 위약금은요?",
        "expected": "확인 필요",
        "expected_chunk_ids": [],
    },
]


def build_groups(question: str, technique: str | None, queries: list[str]):
    """원 질문과 변환 질문의 Hybrid Top-10을 각각 생성함."""
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
    parser = argparse.ArgumentParser(description="슬라이드 34 함정 질문 실행")
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--provider", choices=("groq", "claude"), default="groq")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        raise ValueError("threshold는 0과 1 사이여야 함")

    configure_s32(
        db_path=S32_ROOT / "data/chroma/group1",
        collection="card_docs_ref",
        model="nlpai-lab/KURE-v1",
    )
    vector_search = get_search(reference=True)
    ask_fn = ask_groq if args.provider == "groq" else ask_llm
    rows = []
    for case in CASES:
        vector_hits = vector_search(case["question"], 10, None, "agent")
        top1_score = vector_hits[0].score if vector_hits else None
        gate_sufficient = top1_score is not None and top1_score >= args.threshold
        route_calls = 0
        if gate_sufficient:
            action, technique, queries, reason = "gate_pass", None, [], ""
        else:
            decision = select_and_transform(case["question"], ask_fn=ask_fn)
            route_calls = 1
            action = decision.action
            technique = decision.technique
            queries = list(decision.queries)
            reason = decision.reason or decision.error

        groups = build_groups(case["question"], technique, queries)
        hits = rerank_each_query_and_merge(
            groups,
            technique=("decomposition" if technique == "decomposition" else None),
            top_n=5,
            decomposition_original_weight=0.1,
        )
        answer, llm_response = answer_with_condition_prompt(
            case["question"],
            hits,
            ask_fn=ask_fn,
            return_debug=True,
        )
        top_ids = [hit.metadata.get("chunk_id", "") for hit in hits]
        expected_ids = case["expected_chunk_ids"]
        rows.append({
            **case,
            "baseline_top1": {
                "chunk_id": vector_hits[0].metadata.get("chunk_id", ""),
                "similarity": round(top1_score, 4),
            } if vector_hits else None,
            "gate_sufficient": gate_sufficient,
            "route_action": action,
            "technique": technique,
            "transformed_queries": queries,
            "route_reason": reason,
            "top_hits": [
                {
                    "rank": rank,
                    "chunk_id": hit.metadata.get("chunk_id", ""),
                    "location": hit.metadata.get("clause_no", ""),
                    "card_name": hit.metadata.get("card_name", ""),
                    "preview": hit.text.replace("\n", " ")[:240],
                }
                for rank, hit in enumerate(hits, start=1)
            ],
            "expected_ranks": {
                chunk_id: (top_ids.index(chunk_id) + 1 if chunk_id in top_ids else None)
                for chunk_id in expected_ids
            },
            "answer": answer,
            "llm_response": llm_response,
            "llm_calls": route_calls + llm_response.get("attempt_count", 1),
        })
        print(
            f"{case['id']} {case['type']}: gate={gate_sufficient}, "
            f"technique={technique}, top1={top_ids[0] if top_ids else '-'}, "
            f"answer={answer['conclusion']}"
        )

    result = {
        "provider": args.provider,
        "model": rows[0]["llm_response"].get("model", "") if rows else "",
        "threshold": args.threshold,
        "hybrid_weights": {"bm25": 0.4, "vector": 0.6},
        "rerank_top_n": 5,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"saved={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
