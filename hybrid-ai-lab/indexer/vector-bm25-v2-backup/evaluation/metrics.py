"""청크 경계와 무관하게 원문의 근거 조각을 비교함."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize(text: str) -> str:
    """표기 차이가 근거 판정을 흐리지 않도록 유니코드와 공백을 정규화함."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text)))


def supports(hit: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """검색 청크가 지정한 원문 출처와 근거 조각을 함께 만족하는지 판정함.

    인자: evidence에는 source와 하나 이상의 any_of 원문 조각이 필요함.
    반환값: 출처가 맞고 대체 근거 중 하나가 청크 본문에 있으면 True임.
    예외: any_of가 비어 있으면 평가 기준 오류를 뜻하는 ValueError를 발생시킴.
    부수효과: 없음.
    """
    metadata = hit.get("metadata", {})
    source = str(hit.get("source") or metadata.get("source", ""))
    if evidence.get("source") and evidence["source"] not in source:
        return False
    # 위치 설명은 청크 방식에 따라 달라질 수 있어 판정 조건에서 제외함.
    # 인덱서 간 공정한 비교를 위해 원문 출처와 사전 지정 근거 조각만 관련성 기준으로 사용함.
    text = normalize(hit.get("text", ""))
    alternatives = evidence.get("any_of", [])
    if not alternatives:
        raise ValueError("평가 근거에는 하나 이상의 원문 조각이 필요합니다.")
    return any(normalize(fragment) in text for fragment in alternatives)


def score(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """질문 한 건의 Top-5 원문 근거 회수율과 첫 근거 순위를 계산함.

    인자: answerable 문항은 하나 이상의 relevance 근거 단위를 포함해야 함.
    반환값: 하나라도 찾았는지(Hit), 근거 단위 회수율(Recall), 첫 관련 순위의 역수(MRR),
    상위 5개 중 관련 청크 비율(Precision)과 근거별 회수 여부를 담은 dict임.
    근거 없음 문항은 검색 건수만 기록하고 네 품질 지표를 None으로 반환함.
    예외: 정답이 있는 문항에 근거가 없으면 ValueError를 발생시킴.
    부수효과: 없음.
    """
    evidence = question.get("relevance", [])
    if not question["answerable"]:
        return {"answerable": False, "returned_count": len(hits), "hit_at_5": None,
                "evidence_recall_at_5": None, "mrr_at_5": None, "precision_at_5": None}
    if not evidence:
        raise ValueError(f"정답이 있는 질문의 평가 근거가 없습니다: {question['id']}")
    matrix = [[supports(hit, unit) for unit in evidence] for hit in hits[:5]]
    ranks = [rank for rank, row in enumerate(matrix, 1) if any(row)]
    covered = [any(row[column] for row in matrix) for column in range(len(evidence))]
    return {"answerable": True, "returned_count": len(hits), "hit_at_5": int(bool(ranks)),
            "evidence_recall_at_5": sum(covered) / len(evidence),
            "mrr_at_5": 1 / ranks[0] if ranks else 0.0,
            "precision_at_5": len(ranks) / 5, "covered_units": covered,
            "relevant_ranks": ranks}


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """평가 행을 정답 근거가 있는 문항 기준의 평균 지표로 집계함.

    목적: 근거 없음 문항이 검색 회수 지표의 분모를 왜곡하지 않도록 분리함.
    반환값: 문항 수·근거 유무별 수·평균 품질 지표·검색 시간 중앙값을 담은 dict임.
    부수효과: 없음.
    """
    positive = [row for row in rows if row["metrics"]["answerable"]]
    result: dict[str, Any] = {"questions": len(rows), "answerable_questions": len(positive),
                              "no_answer_questions": len(rows) - len(positive)}
    for metric in ("hit_at_5", "evidence_recall_at_5", "mrr_at_5", "precision_at_5"):
        result[metric] = sum(row["metrics"][metric] for row in positive) / len(positive) if positive else None
    times = sorted(row["search_ms"] for row in rows)
    result["search_ms_median"] = (times[(len(times)-1)//2] + times[len(times)//2]) / 2 if times else 0
    return result
