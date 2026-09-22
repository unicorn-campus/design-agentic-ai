"""질문 10건을 네 가지 Retriever 검색 모드로 실행함."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

from app.application.graph import check_health, load_resources, search_documents
from app.application.state import RetrieverRequest


APP_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = APP_DIR / "tests" / "fixtures" / "retriever_10q_questions.json"
DEFAULT_OUTPUT = APP_DIR / "data" / "retriever_10q_4mode_results.json"
MODES = ("vector", "vector_rerank", "hybrid", "hybrid_rerank")


def _rank(chunk_id: str, hits: list[Any]) -> int | None:
    return next(
        (index for index, hit in enumerate(hits, start=1) if hit.chunk_id == chunk_id),
        None,
    )


def run_matrix(questions_path: Path, output_path: Path) -> dict[str, Any]:
    suite = json.loads(questions_path.read_text(encoding="utf-8"))
    cases = suite["cases"]
    top_k = int(suite.get("top_k", 5))
    role = str(suite.get("role", "auditor"))
    transform = str(suite.get("transform", "off"))

    resources = load_resources()
    health = check_health(resources)
    if not health.index_connected:
        raise RuntimeError("Retriever 인덱스 연결 실패")

    rows: list[dict[str, Any]] = []
    run_id = uuid4().hex[:12]
    started = monotonic()
    for case in cases:
        for mode in MODES:
            run_started = monotonic()
            result = search_documents(
                RetrieverRequest(
                    query=case["question"],
                    top_k=top_k,
                    mode=mode,
                    transform=transform,
                    role=role,
                    thread_id=f"matrix-{run_id}-{case['id']}-{mode}",
                    max_llm_calls=1,
                ),
                resources,
            )
            ranks = {
                chunk_id: _rank(chunk_id, result.hits)
                for chunk_id in case["expected_chunk_ids"]
            }
            rows.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "source_group": case["source_group"],
                    "mode": mode,
                    "expected_chunk_ids": case["expected_chunk_ids"],
                    "ranks": ranks,
                    "passed": all(rank is not None and rank <= top_k for rank in ranks.values()),
                    "top_hits": [
                        {
                            "rank": rank,
                            "chunk_id": hit.chunk_id,
                            "source": hit.source,
                            "location": hit.location,
                            "score": hit.score,
                            "vector_score": hit.vector_score,
                            "rerank_score": hit.rerank_score,
                        }
                        for rank, hit in enumerate(result.hits, start=1)
                    ],
                    "status": result.status,
                    "llm_calls": result.llm_calls,
                    "route": result.route.model_dump(mode="json"),
                    "timings": result.timings,
                    "wall_time_ms": round((monotonic() - run_started) * 1000, 1),
                }
            )
            print(
                f"{case['id']} {mode}: "
                f"{'PASS' if rows[-1]['passed'] else 'FAIL'} {ranks}",
                flush=True,
            )

    by_mode = {}
    for mode in MODES:
        selected = [row for row in rows if row["mode"] == mode]
        by_mode[mode] = {
            "passed": sum(bool(row["passed"]) for row in selected),
            "total": len(selected),
            "pass_rate": round(
                sum(bool(row["passed"]) for row in selected) / len(selected),
                4,
            ),
            "mean_wall_time_ms": round(
                sum(float(row["wall_time_ms"]) for row in selected) / len(selected),
                1,
            ),
            "failed_question_ids": [row["id"] for row in selected if not row["passed"]],
        }

    source_coverage = Counter(case["source_group"] for case in cases)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "questions_path": str(questions_path),
        "configuration": {
            "run_id": run_id,
            "questions": len(cases),
            "modes": list(MODES),
            "runs": len(rows),
            "top_k": top_k,
            "role": role,
            "transform": transform,
        },
        "health": health.model_dump(mode="json"),
        "source_coverage": dict(source_coverage),
        "summary_by_mode": by_mode,
        "total_wall_time_ms": round((monotonic() - started) * 1000, 1),
        "rows": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_matrix(args.questions.resolve(), args.output.resolve())
    print(json.dumps(report["summary_by_mode"], ensure_ascii=False, indent=2))
    print(f"결과 파일: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
