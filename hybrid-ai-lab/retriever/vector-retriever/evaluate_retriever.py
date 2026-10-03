"""W-1 인덱서의 검색 평가셋(group2_questions.json)으로 리트리버의 검색 품질과 최종 응답을 재는 평가 스크립트임.

두 층을 따로 잼.
- 검색 품질: 첫 검색(S-R4) 상위 5개. 인덱서 평가와 같은 판정·지표(Hit@5·근거 Recall@5·MRR@5·Precision@5)
- 최종 응답: 워크플로우 전체(S-R1 ~ S-R9)를 돌린 응답 상태와, 채점 관문을 통과한 근거 목록의 같은 지표
  답 없음 문항은 '확인 필요(needs_confirmation)'로 끝나야 정답으로 셈(지어내지 않음)

평가셋의 filters(card_id·member_pseudo_id 등)는 설계 입력에 없어 쓰지 않음. 필터에 기대는 문항은 결과에 표시함.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any
import unicodedata

from app.application.models import SearchRequest

ROOT = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = ROOT.parent.parent / "indexer" / "vector-bm25" / "evaluation" / "group2_questions.json"
# 회원별 상담 이력 문항은 restricted(D3)를 봐야 하므로 감사자로, 나머지는 상담원(agent)으로 물음
AUDITOR_FILTER_KEYS = {"member_pseudo_id"}
ANSWERED_STATUSES = {"answered", "retrieved"}


# ---------------------------------------------------------------- 판정·지표(인덱서 evaluation/metrics.py와 같은 기준)


def _normalize(text: str) -> str:
    """유니코드·공백 차이가 근거 판정을 흐리지 않도록 정규화함."""

    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text)))


def _supports(source: str, text: str, unit: dict[str, Any]) -> bool:
    """조각이 평가 근거 단위(출처 + any_of 원문 조각 중 하나)를 만족하는지 판정함."""

    if unit.get("source") and unit["source"] not in source:
        return False
    body = _normalize(text)
    return any(_normalize(fragment) in body for fragment in unit.get("any_of", []))


def score_hits(question: dict[str, Any], hits: list[tuple[str, str]]) -> dict[str, Any]:
    """상위 5개 (출처, 본문) 목록으로 Hit@5·근거 Recall@5·MRR@5·Precision@5를 계산함.

    반환값: 답 없음 문항은 네 지표가 None인 dict임.
    """

    units = question.get("relevance") or []
    if not question["answerable"]:
        return {"hit": None, "recall": None, "mrr": None, "precision": None}
    matrix = [[_supports(source, text, unit) for unit in units] for source, text in hits[:5]]
    ranks = [rank for rank, row in enumerate(matrix, 1) if any(row)]
    covered = [any(row[col] for row in matrix) for col in range(len(units))]
    return {
        "hit": int(bool(ranks)),
        "recall": sum(covered) / len(units),
        "mrr": 1 / ranks[0] if ranks else 0.0,
        "precision": len(ranks) / 5,
    }


def mean_metrics(rows: list[dict[str, Any]], key: str) -> dict[str, float | None]:
    """답 있음 문항만 모아 지표 평균을 냄(답 없음 문항이 분모를 흐리지 않게 함)."""

    positive = [row[key] for row in rows if row["answerable"]]
    if not positive:
        return {name: None for name in ("hit", "recall", "mrr", "precision")}
    return {name: round(sum(m[name] for m in positive) / len(positive), 3)
            for name in ("hit", "recall", "mrr", "precision")}


# ---------------------------------------------------------------- 실행


def evaluate(questions: list[dict[str, Any]], *, generate_answer: bool) -> list[dict[str, Any]]:
    """문항마다 첫 검색과 전체 워크플로우를 실행해 결과 행을 만듦.

    부수효과: 서비스 조립(색인·모델 적재), Groq 호출, 감사 로그 기록.
    """

    from app.bootstrap import create_service  # 조립은 bootstrap 한 곳에서만 함

    service = create_service()
    steps = service.workflow.steps  # 첫 검색만 따로 재려고 단계 객체의 진단용 검색을 씀
    rows = []
    for question in questions:
        filter_keys = {key for item in question.get("filters") or [] for key in item}
        role = "auditor" if filter_keys & AUDITOR_FILTER_KEYS else "agent"
        access = ["public", "restricted"] if role == "auditor" else ["public"]
        top5 = steps.search_once(question["question"], access_levels=access, top_k=5)
        started = time.perf_counter()
        response = service.execute(
            SearchRequest(query=question["question"], generate_answer=generate_answer, top_k=5), role
        )
        elapsed = time.perf_counter() - started
        final_hits = [(item.source, item.text) for item in response.evidence]
        rows.append({
            "id": question["id"],
            "question": question["question"],
            "answerable": bool(question["answerable"]),
            "role": role,
            "uses_filters": sorted(filter_keys),
            "search": score_hits(question, [(c.chunk.source.source, c.chunk.text) for c in top5]),
            "search_top1_rerank": None if not top5 or top5[0].rerank_score is None else round(top5[0].rerank_score, 3),
            "status": response.status,
            "question_type": response.question_type,
            "final": score_hits(question, final_hits),
            "evidence_count": len(response.evidence),
            "unresolved": [item.reason for item in response.unresolved],
            "clarify_question": response.clarify_question,
            "answer": [sentence.text for sentence in response.answer or []],
            "ground_truth": question.get("ground_truth", ""),
            "llm_calls": response.llm_calls,
            "seconds": round(elapsed, 2),
            "warnings": response.warnings,
        })
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """전체·필터 없는 문항 기준으로 검색 지표와 최종 응답 정답률을 집계함."""

    def block(subset: list[dict[str, Any]]) -> dict[str, Any]:
        positive = [r for r in subset if r["answerable"]]
        negative = [r for r in subset if not r["answerable"]]
        return {
            "questions": len(subset),
            "answerable": len(positive),
            "no_answer": len(negative),
            "search_top5": mean_metrics(subset, "search"),
            "final_evidence": mean_metrics(subset, "final"),
            # 답 있음 문항이 근거를 들고 끝났는지, 그 근거에 정답 조각이 있는지
            "answerable_returned": sum(r["status"] in ANSWERED_STATUSES for r in positive),
            "answerable_returned_with_relevant": sum(
                r["status"] in ANSWERED_STATUSES and bool(r["final"]["hit"]) for r in positive),
            # 답 없음 문항은 확인 필요로 끝나야 정답(지어내지 않음)
            "no_answer_refused": sum(r["status"] == "needs_confirmation" for r in negative),
            "status_counts": {s: sum(r["status"] == s for r in subset) for s in sorted({r["status"] for r in subset})},
            "seconds_median": statistics.median([r["seconds"] for r in subset]) if subset else None,
            "llm_calls_mean": round(statistics.mean([r["llm_calls"] for r in subset]), 2) if subset else None,
        }

    return {"all": block(rows), "without_filters": block([r for r in rows if not r["uses_filters"]])}


def main(argv: list[str] | None = None) -> int:
    """평가를 실행하고 요약을 출력·저장함. 반환값은 종료 코드(정상 0)."""

    parser = argparse.ArgumentParser(description="검색 평가셋으로 리트리버를 평가함")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS, help="평가셋 JSON 경로")
    parser.add_argument("--generate-answer", action="store_true", help="답변 생성까지 켜고 평가")
    parser.add_argument("--out", type=Path, default=None, help="결과 JSON 저장 경로(기본 logs/eval-시각.json)")
    args = parser.parse_args(argv)

    questions = json.loads(args.questions.read_text(encoding="utf-8"))["questions"]
    rows = evaluate(questions, generate_answer=args.generate_answer)
    summary = summarize(rows)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or ROOT / "logs" / f"eval-{stamp}{'-answer' if args.generate_answer else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"questions_file": str(args.questions), "generate_answer": args.generate_answer,
                               "summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'ID':4} {'답':2} {'역할':7} {'필터':5} {'검색Hit':7} {'1위':6} {'상태':19} {'최종Hit':7} {'LLM':3} 초")
    for r in rows:
        hit = "-" if r["search"]["hit"] is None else r["search"]["hit"]
        final = "-" if r["final"]["hit"] is None else r["final"]["hit"]
        print(f"{r['id']:4} {'O' if r['answerable'] else 'X':2} {r['role']:7} {'있음' if r['uses_filters'] else '':5} "
              f"{hit!s:7} {r['search_top1_rerank']!s:6} {r['status']:19} {final!s:7} "
              f"{r['llm_calls']:<3} {r['seconds']}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"결과 저장: {out}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
