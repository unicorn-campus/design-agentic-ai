"""LLM 없이 점수 규칙으로 검색 결과를 정확·불확실·부정확으로 나누는 채점 규칙임(설계 ⑥-8, S-R5)."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Collection, Iterable, Sequence
import unicodedata

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


# 조각 본문의 조항 머리 '제N조(…' · '제N조의M(…'. 괄호가 붙은 것만 봐서 '제10조에 따릅니다' 같은 참조는 빼고 셈
_ARTICLE_HEAD = re.compile(r"제\s*\d+\s*조(?:의\s*\d+)?\s*\(")


def card_token(name: str | None) -> str | None:
    """카드명을 질문 쪽 대상 토큰과 같은 꼴(공백 없음 · 소문자 · NFKC)로 바꿈. 카드명이 없으면 None."""

    if not name:
        return None
    return unicodedata.normalize("NFKC", name).replace(" ", "").lower() or None


def target_keys(candidate: Candidate) -> frozenset[str]:
    """후보가 가리키는 대상(카드 · 조항)을 반환함. 같은 대상을 가리키는 후보끼리는 1·2위 경쟁자로 보지 않음.

    목적: 오버랩으로 겹친 이웃 조각이나 같은 카드의 다른 조각은 1·2위 점수가 거의 같아도 '모호함'이 아님.
    방법: 카드 코드가 있으면 그 카드, 없으면 본문에 든 조항 머리 집합, 둘 다 없으면 조각 자신을 대상으로 봄.
    """

    source = candidate.chunk.source
    if source.card_id:
        return frozenset({f"card:{source.card_id}"})
    heads = {re.sub(r"[\s(]", "", m.group(0)) for m in _ARTICLE_HEAD.finditer(candidate.chunk.text)}
    if heads:
        return frozenset(f"clause:{head}" for head in heads)
    return frozenset({f"chunk:{candidate.chunk_id}"})


def build_signals(
    candidates: Sequence[Candidate],
    *,
    keywords: Iterable[str],
    result_terms: Collection[str],
    vector_top_ids: Sequence[str],
    keyword_top_ids: Sequence[str],
    top_k: int,
    thresholds: GradeThresholds,
    question_targets: Collection[str] = (),
) -> GradeSignals:
    """검색 후보에서 판정 근거(신호값)를 계산함.

    인자: candidates는 최종 순위 순서의 후보, result_terms는 후보 조각들을 같은 분석기로 자른 낱말 집합임.
    인자: vector_top_ids·keyword_top_ids는 검색기별 상위 조각ID 목록이며 앞에서 top_k개만 비교함.
    인자: question_targets는 질문이 지정한 카드 대상 토큰(카드명 사전으로 통일, 없으면 빈 값)임.
    반환값: GradeSignals. 리랭크 점수가 하나라도 없으면 리랭크 실패로 보고 주 점수를 None으로 둠.

    격차(사용자 결정 2026-10-04): 1위와 '다른 대상'인 후보 중 최고 점수와의 차이로 잼. 같은 카드 · 같은 조항 조각과
    질문이 지정하지 않은 카드는 경쟁자가 아님 — 평가셋 v1에서 정답 1위인데 이웃 조각 · 같은 문구의 다른 카드가
    0.0004 ~ 0.04 차이로 2위라 막히던 문항(8건)이 있었음. 질문의 카드가 아닌 조각이 1위면 target_match가 거짓이 됨.
    """

    count = len(candidates)
    reranked = count > 0 and all(c.rerank_score is not None for c in candidates)
    ranked = sorted((c for c in candidates if c.rerank_score is not None),
                    key=lambda c: float(c.rerank_score), reverse=True)
    main = float(ranked[0].rerank_score) if reranked and ranked else None
    targets = {t for t in (card_token(x) for x in question_targets) if t}
    gap = None
    target_match = True
    if main is not None:
        top = ranked[0]
        top_keys = target_keys(top)
        top_card = card_token(top.chunk.source.card_name)
        target_match = not (targets and top_card and top_card not in targets)

        def competes(c: Candidate) -> bool:
            if target_keys(c) & top_keys:
                return False
            card = card_token(c.chunk.source.card_name)
            return not (targets and card and card not in targets)

        runner_up = next((float(c.rerank_score) for c in ranked[1:] if competes(c)), 0.0)
        gap = main - runner_up
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
        target_match=target_match,
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
    질문이 지정한 카드와 1위 일치 · 다른 대상과의 격차 충족 · 겹침 충족 또는 1위 ≥ 겹침 면제 기준)
    → 나머지는 불확실 순서로 판정함.
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
        and signals.target_match
        and signals.gap is not None
        and signals.gap >= thresholds.min_gap
        and overlap_satisfied(signals, thresholds)
    ):
        return GRADE_CORRECT
    return GRADE_UNCERTAIN
