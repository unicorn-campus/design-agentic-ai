"""검색기 점수 정규화·가중합·RRF로 여러 결과를 하나의 순위로 합치는 규칙임(설계 ⑥-6)."""

from __future__ import annotations

from typing import Mapping, Sequence

# RRF(여러 검색 결과의 순위를 합치는 방식) 상수. 원 논문 권장값으로 순위 차이를 완만하게 만듦.
RRF_K = 60


def min_max_normalize(scores: Mapping[str, float]) -> dict[str, float]:
    """점수를 0 ~ 1로 다시 펴서 반환함.

    목적: 코사인 점수와 BM25 점수는 범위가 달라 그대로 더하면 한쪽이 결과를 좌우함.
    반환값: 모든 값이 같으면(후보 1건 포함) 0으로 나누지 않도록 전부 1.0으로 둠. 입력이 비면 빈 dict임.
    """

    if not scores:
        return {}
    low, high = min(scores.values()), max(scores.values())
    if high == low:
        return {key: 1.0 for key in scores}
    span = high - low
    return {key: (float(value) - low) / span for key, value in scores.items()}


def weighted_hybrid(
    vector_scores: Mapping[str, float],
    keyword_scores: Mapping[str, float],
    *,
    vector_weight: float,
    keyword_weight: float,
) -> dict[str, float]:
    """두 검색기 점수를 각각 정규화한 뒤 비중대로 더함(벡터 0.6 : BM25 0.4, 설계 ⑥-6).

    반환값: 조각ID → 융합 점수. 한쪽 검색기에만 있는 조각은 다른 쪽 점수를 0으로 봄.
    """

    vector_norm = min_max_normalize(vector_scores)
    keyword_norm = min_max_normalize(keyword_scores)
    keys = set(vector_norm) | set(keyword_norm)
    return {
        key: vector_weight * vector_norm.get(key, 0.0) + keyword_weight * keyword_norm.get(key, 0.0)
        for key in keys
    }


def rrf_merge(rankings: Sequence[Sequence[str]], *, k: int = RRF_K) -> dict[str, float]:
    """여러 순위 목록을 RRF 점수(1 / (k + 순위))의 합으로 합침.

    목적: 점수 분포가 다른 결과(원 질문 + 변환 질의, 하위 질문별 결과)를 점수 대신 순위로 공정하게 합침.
    반환값: 조각ID → RRF 점수. 순위는 1부터 셈.
    """

    merged: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            merged[key] = merged.get(key, 0.0) + 1.0 / (k + rank)
    return merged


def equal_weight_merge(score_maps: Sequence[Mapping[str, float]]) -> dict[str, float]:
    """Multi-Query 결과를 질의별 같은 가중치(1/질의 수)로 더함(설계 ⑥-6, 설계 가정).

    반환값: 조각ID → 가중합 점수. 어떤 질의 결과에 없는 조각은 그 질의 점수를 0으로 봄.
    """

    if not score_maps:
        return {}
    weight = 1.0 / len(score_maps)
    merged: dict[str, float] = {}
    for scores in score_maps:
        for key, value in scores.items():
            merged[key] = merged.get(key, 0.0) + weight * float(value)
    return merged


def rank_keys(scores: Mapping[str, float], tie_breakers: Sequence[Mapping[str, float]] = ()) -> list[str]:
    """점수 내림차순 → 보조 점수 내림차순 → 조각ID 오름차순으로 정렬한 키 목록을 반환함.

    목적: 같은 점수일 때도 실행마다 같은 순서를 내도록 정렬 기준을 끝까지 고정함(설계 ⑥-7).
    """

    def sort_key(key: str) -> tuple:
        """정렬 열쇠: 점수 내림차순 → 보조 점수 내림차순 → 조각ID."""

        extras = tuple(-float(scores_map.get(key, 0.0)) for scores_map in tie_breakers)
        return (-float(scores[key]), *extras, key)

    return sorted(scores, key=sort_key)
