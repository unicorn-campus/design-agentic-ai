"""W-1 인덱서의 검색 평가셋(group2_questions.json)으로 리트리버의 검색 품질과 최종 응답을 재는 평가 스크립트임.

두 층을 따로 잼.
- 검색 품질: 첫 검색(S-R4) 상위 5개. 인덱서 평가와 같은 판정·지표(Hit@5·근거 Recall@5·MRR@5·Precision@5)
  + 순위 품질 nDCG@5(RAGAS에 없어 따로 계산 — dev-prompt-guide §3.7)
- 최종 응답: 워크플로우 전체(S-R1 ~ S-R9)를 돌린 응답 상태와, 채점 관문을 통과한 근거 목록의 같은 지표
  답 없음 문항은 '확인 필요(needs_confirmation)'로 끝나야 정답으로 셈(지어내지 않음)

평가셋 filters 중 member_id(상담 문항의 회원번호)는 요청의 member_id로 넘김 — 상담 이력은 그 회원 것만 검색함.
card_id는 설계 입력에 없어 쓰지 않음. 필터를 가진 문항은 결과에 표시함.
결과 행에는 채점 관문을 통과한 근거 본문(evidence)도 남김 — evaluate_ragas.py가 이 로그를 읽어 RAGAS로 채점함.

버전 실험용 인자(품질평가 설계서 ④ 코드 채점): --top-k · --metric-k · --fixed-k · --version-label · --config-snapshot.
인자를 하나도 주지 않으면 top_k 5 · 지표 @5로 지금과 같은 값이 나옴. Top-k 버전끼리는 분모가 달라지므로
search 층은 @k(그 버전의 k)와 비교용 @fixed-k(기본 5)를 함께 남김. final 층은 채점 관문이 개수를 정해 @5 고정임.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any
import unicodedata

from app.application.models import SearchRequest
from app.domain.member import member_pseudonym

ROOT = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = ROOT.parent.parent / "indexer" / "vector-bm25" / "evaluation" / "group2_questions.json"
# 회원별 상담 이력 문항은 restricted(D3)를 봐야 하므로 감사자로, 나머지는 상담원(agent)으로 물음
AUDITOR_FILTER_KEYS = {"member_pseudo_id", "member_id"}
ANSWERED_STATUSES = {"answered", "retrieved"}


# ---------------------------------------------------------------- 판정·지표(인덱서 evaluation/metrics.py와 같은 기준)


def _normalize(text: str) -> str:
    """유니코드·공백 차이가 근거 판정을 흐리지 않도록 정규화함."""

    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text)))


def _supports(source: str, text: str, unit: dict[str, Any], card_id: str | None = None) -> bool:
    """조각이 평가 근거 단위(출처 + 카드 + any_of 원문 조각 중 하나)를 만족하는지 판정함.

    카드 혜택 문항(location이 'D2-C001-B01'처럼 카드 코드로 시작)은 그 카드의 조각만 관련으로 셈 —
    카드 64종이 같은 문구('대상 결제액의 1.2%를 적립함' 등)를 공유해, 다른 카드 조각까지 맞다고 세면
    Hit · Recall · nDCG가 부풀려짐(평가셋 v1 실측, 사용자 결정 2026-10-04).
    """

    if unit.get("source") and unit["source"] not in source:
        return False
    location = str(unit.get("location") or "")
    if location.startswith("D2-C") and card_id is not None and not location.startswith(card_id):
        return False
    body = _normalize(text)
    return any(_normalize(fragment) in body for fragment in unit.get("any_of", []))


METRIC_NAMES = ("hit", "recall", "mrr", "precision", "ndcg")


def _ndcg(ranks: list[int], unit_count: int, k: int = 5) -> float:
    """관련 조각의 순위(1부터) 목록으로 이진 관련도 nDCG@k를 계산함.

    색인 전체에서 관련 조각이 몇 개인지 모름(겹치는 조각이 같은 근거를 담기도 함). 그래서 이상적인 순위의 관련 개수를
    max(근거 단위 수, 실제로 찾은 관련 조각 수)로 두고 k에서 자름 — 값이 0 ~ 1을 넘지 않으면서 놓친 근거는 감점됨.
    """

    dcg = sum(1 / math.log2(rank + 1) for rank in ranks if rank <= k)
    ideal = min(max(unit_count, len(ranks)), k)
    idcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal + 1))
    return dcg / idcg if idcg else 0.0


def score_hits(question: dict[str, Any], hits: list[tuple[str, str, str | None]], k: int = 5) -> dict[str, Any]:
    """상위 k개 (출처, 본문, 카드 코드) 목록으로 Hit@k·근거 Recall@k·MRR@k·Precision@k·nDCG@k를 계산함.

    인자: k는 자르는 개수이자 Precision의 분모임. 조각이 k개보다 적어도 분모는 k임 — k칸을 쓸 수 있는데
    덜 채운 것도 정밀도에 반영하려는 것임(Top-k 3 버전을 @5로 잴 때 해당).
    반환값: 답 없음 문항은 다섯 지표가 None인 dict임.
    """

    units = question.get("relevance") or []
    if not question["answerable"]:
        return {name: None for name in METRIC_NAMES}
    matrix = [[_supports(source, text, unit, card_id) for unit in units] for source, text, card_id in hits[:k]]
    ranks = [rank for rank, row in enumerate(matrix, 1) if any(row)]
    covered = [any(row[col] for row in matrix) for col in range(len(units))]
    return {
        "hit": int(bool(ranks)),
        "recall": sum(covered) / len(units),
        "mrr": 1 / ranks[0] if ranks else 0.0,
        "precision": len(ranks) / k,
        "ndcg": round(_ndcg(ranks, len(units), k), 4),
    }


def mean_metrics(rows: list[dict[str, Any]], key: str) -> dict[str, float | None]:
    """답 있음 문항만 모아 지표 평균을 냄(답 없음 문항이 분모를 흐리지 않게 함)."""

    positive = [row[key] for row in rows if row["answerable"]]
    if not positive:
        return {name: None for name in METRIC_NAMES}
    return {name: round(sum(m[name] for m in positive) / len(positive), 3) for name in METRIC_NAMES}


# ---------------------------------------------------------------- 실행


def evaluate(questions: list[dict[str, Any]], *, generate_answer: bool, top_k: int = 5, metric_k: int | None = None,
             fixed_k: int = 5, version_label: str | None = None) -> list[dict[str, Any]]:
    """문항마다 첫 검색과 전체 워크플로우를 실행해 결과 행을 만듦.

    인자: top_k는 첫 검색과 워크플로우 요청 두 곳에 같이 넣음(1 ~ 10). metric_k를 비우면 top_k와 같음.
    반환값: 행마다 search(@metric_k) · search_fixed(@fixed_k) · final(@5) 지표를 담은 dict 목록임.
    부수효과: 서비스 조립(색인·모델 적재), Groq 호출, 감사 로그 기록.
    """

    from app.bootstrap import create_service  # 조립은 bootstrap 한 곳에서만 함

    metric_k = metric_k or top_k
    service = create_service()
    steps = service.workflow.steps  # 첫 검색만 따로 재려고 단계 객체의 진단용 검색을 씀
    rows = []
    for question in questions:
        filter_keys = {key for item in question.get("filters") or [] for key in item}
        role = "auditor" if filter_keys & AUDITOR_FILTER_KEYS else "agent"
        access = ["public", "restricted"] if role == "auditor" else ["public"]
        member_id = next((item["member_id"] for item in question.get("filters") or [] if "member_id" in item), None)
        member = member_pseudonym(member_id) if member_id else None
        first = steps.search_once(question["question"], access_levels=access, top_k=top_k, member_pseudo_id=member)
        started = time.perf_counter()
        response = service.execute(
            SearchRequest(query=question["question"], generate_answer=generate_answer, top_k=top_k,
                          member_id=member_id), role
        )
        elapsed = time.perf_counter() - started
        first_hits = [(c.chunk.source.source, c.chunk.text, c.chunk.source.card_id) for c in first]
        final_hits = [(item.source, item.text, item.card_id) for item in response.evidence]
        rows.append({
            "id": question["id"],
            "version": version_label,
            "top_k": top_k,
            "question": question["question"],
            "answerable": bool(question["answerable"]),
            "role": role,
            "uses_filters": sorted(filter_keys),
            "member_filter": member is not None,  # 회원 필터를 실어 검색했는지(원래 회원번호는 남기지 않음)
            "search": score_hits(question, first_hits, metric_k),
            # 버전끼리 같은 잣대로 비교하려고 k를 고정한 값도 함께 남김(Top-k 버전의 Δ는 이 값으로 계산)
            "search_fixed": score_hits(question, first_hits, fixed_k),
            "search_top1_rerank": None if not first or first[0].rerank_score is None else round(first[0].rerank_score, 3),
            "status": response.status,
            "question_type": response.question_type,
            "final": score_hits(question, final_hits),
            "evidence_count": len(response.evidence),
            # RAGAS 채점(evaluate_ragas.py)이 retrieved_contexts로 쓰려면 개수가 아니라 본문이 있어야 함
            "evidence": [{"source": source, "text": text, "card_id": card_id} for source, text, card_id in final_hits],
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
            # 키 이름은 기존 로그와 맞추려고 그대로 둠. 값은 @metric_k(기본 5)이며 머리의 metric_k로 확인함
            "search_top5": mean_metrics(subset, "search"),
            "search_fixed": mean_metrics(subset, "search_fixed"),
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
    # 아래 5개는 버전 실험용. 기본값은 위 3개만 쓸 때와 같은 결과가 나오게 둠
    parser.add_argument("--top-k", type=int, default=5, help="첫 검색 · 워크플로우 요청의 top_k(1 ~ 10, 기본 5)")
    parser.add_argument("--metric-k", type=int, default=None, help="search 층 지표의 k(기본 = --top-k)")
    parser.add_argument("--fixed-k", type=int, default=5, help="버전 비교용 고정 k(기본 5)")
    parser.add_argument("--version-label", default=None, help="결과 머리와 행에 남길 버전 이름")
    parser.add_argument("--config-snapshot", type=Path, default=None, help="적용 설정 JSON — 결과 머리에 복사함")
    args = parser.parse_args(argv)
    for name, value in (("--top-k", args.top_k), ("--metric-k", args.metric_k), ("--fixed-k", args.fixed_k)):
        # 후보 수가 top_k × 2 × 4라 10을 넘기면 리트리버 요청 검사(1 ~ 10)에 걸림
        if value is not None and not 1 <= value <= 10:
            parser.error(f"{name}는 1 ~ 10이어야 합니다: {value}")

    questions = json.loads(args.questions.read_text(encoding="utf-8"))["questions"]
    rows = evaluate(questions, generate_answer=args.generate_answer, top_k=args.top_k, metric_k=args.metric_k,
                    fixed_k=args.fixed_k, version_label=args.version_label)
    summary = summarize(rows)
    snapshot = json.loads(args.config_snapshot.read_text(encoding="utf-8")) if args.config_snapshot else None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or ROOT / "logs" / f"eval-{stamp}{'-answer' if args.generate_answer else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"questions_file": str(args.questions), "generate_answer": args.generate_answer,
                               "version": args.version_label, "top_k": args.top_k,
                               "metric_k": args.metric_k or args.top_k, "fixed_k": args.fixed_k,
                               "config_snapshot": snapshot, "summary": summary, "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")

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
