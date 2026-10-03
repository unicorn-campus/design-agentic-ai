"""LLM 없이 점수 규칙으로 검색 결과를 정확·불확실·부정확으로 나누는 채점 규칙임(설계 ⑥-8, S-R5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Iterable, Sequence

from .models import (
    GRADE_CORRECT,
    GRADE_INCORRECT,
    GRADE_UNCERTAIN,
    Candidate,
    GradeSignals,
)


@dataclass(frozen=True)
class GradeThresholds:
    """판정 기준값. 모두 설계 가정 초깃값이며 평가셋으로 검증해 조정함(설계 ⑥-8 '결정 필요')."""

    upper: float = 0.7  # 주 점수 상한. 이상이면 정확 후보
    lower: float = 0.3  # 주 점수 하한. 미만이면 부정확
    min_gap: float = 0.05  # 1·2위 최소 격차
    min_overlap: int = 1  # 벡터·BM25 상위 k 최소 겹침 수
    # 주 점수가 이 값 이상이면 겹침 조건을 면제함(사용자 결정 2026-10-03, 설계 가정 0.9).
    # 평가셋 실측: 1위 0.915 · 0.92 · 0.961인데 겹침 0이라 불확실이던 정답 문항이 있었고, 0.877(1위 오답)은 막아야 했음
    overlap_waiver_score: float = 0.9


def score_band(main_score: float | None, thresholds: GradeThresholds, *, result_count: int) -> str:
    """주 점수를 상한·하한으로 나눈 구간 이름을 반환함."""

    if result_count == 0:
        return "none"
    if main_score is None:
        return "unknown"
    if main_score >= thresholds.upper:
        return "high"
    if main_score < thresholds.lower:
        return "low"
    return "middle"


def build_signals(
    candidates: Sequence[Candidate],
    *,
    keywords: Iterable[str],
    result_terms: Collection[str],
    vector_top_ids: Sequence[str],
    keyword_top_ids: Sequence[str],
    top_k: int,
    thresholds: GradeThresholds,
) -> GradeSignals:
    """검색 후보에서 판정 근거(신호값)를 계산함.

    인자: candidates는 최종 순위 순서의 후보, result_terms는 후보 조각들을 같은 분석기로 자른 낱말 집합임.
    인자: vector_top_ids·keyword_top_ids는 검색기별 상위 조각ID 목록이며 앞에서 top_k개만 비교함.
    반환값: GradeSignals. 리랭크 점수가 하나라도 없으면 리랭크 실패로 보고 주 점수를 None으로 둠.
    """

    count = len(candidates)
    reranked = count > 0 and all(c.rerank_score is not None for c in candidates)
    scores = sorted((float(c.rerank_score) for c in candidates if c.rerank_score is not None), reverse=True)
    main = scores[0] if reranked and scores else None
    gap = None
    if main is not None:
        gap = main - (scores[1] if len(scores) > 1 else 0.0)
    selected = tuple(dict.fromkeys(keywords))
    missing = tuple(term for term in selected if term not in result_terms)
    overlap = len(set(vector_top_ids[:top_k]) & set(keyword_top_ids[:top_k]))
    return GradeSignals(
        result_count=count,
        reranked=reranked,
        main_score=main,
        score_band=score_band(main, thresholds, result_count=count),
        gap=gap,
        keywords=selected,
        missing_keywords=missing,
        overlap=overlap,
    )


def overlap_satisfied(signals: GradeSignals, thresholds: GradeThresholds) -> bool:
    """검색기 합의 조건을 만족하는지 반환함. 겹침이 기준 미만이어도 주 점수가 면제 기준 이상이면 만족으로 봄."""

    if signals.overlap >= thresholds.min_overlap:
        return True
    return signals.main_score is not None and signals.main_score >= thresholds.overlap_waiver_score


def evidence_worthy(candidates: Sequence[Candidate], thresholds: GradeThresholds) -> list[Candidate]:
    """'정확' 판정된 결과 중 근거 묶음에 넣을 조각만 고름(사용자 결정 2026-10-03).

    목적: 상위 top_k를 모두 넣으면 다른 카드 조각(리랭크 0.02 ~ 0.03)까지 근거·답변 재료로 섞임.
    방법: 리랭크 점수가 하한(부정확 기준) 이상인 조각만 남김. 정확 판정이면 1위는 상한 이상이라 최소 1건은 남음.
    """

    return [c for c in candidates if c.rerank_score is not None and c.rerank_score >= thresholds.lower]


def grade(signals: GradeSignals, thresholds: GradeThresholds) -> str:
    """판정 근거로 정확·불확실·부정확 중 하나를 반환함(설계 ⑥-8 판정 규칙).

    방법: 부정확(하나라도: 0건 · 1위 < 하한) → 정확(모두: 리랭크 성공 · 1위 ≥ 상한 · 핵심어 포함 ·
    격차 충족 · 겹침 충족 또는 1위 ≥ 겹침 면제 기준) → 나머지는 불확실 순서로 판정함.
    예시: 리랭크가 실패하면 점수로 하한을 잴 수 없으므로 결과가 있는 한 최대 불확실임(사용자 결정).
    """

    if signals.result_count == 0:
        return GRADE_INCORRECT
    if signals.main_score is not None and signals.main_score < thresholds.lower:
        return GRADE_INCORRECT
    if (
        signals.reranked
        and signals.main_score is not None
        and signals.main_score >= thresholds.upper
        and signals.keyword_match
        and signals.gap is not None
        and signals.gap >= thresholds.min_gap
        and overlap_satisfied(signals, thresholds)
    ):
        return GRADE_CORRECT
    return GRADE_UNCERTAIN
