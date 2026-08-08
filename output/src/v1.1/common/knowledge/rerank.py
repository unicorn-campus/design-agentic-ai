"""재정렬 — 뽑아온 후보를 다시 줄 세우기.

⑤ K-1 「리랭킹 여부」가 **씀**이라 만들었음. 기준 4축도 ⑤가 적은 것을 그대로 씀 —
취향 유사도 · 거리 · 반복 방지 · 확신 스코어.

**가중치는 ⑤에 값이 없음** → 설정이 비어 있으면 순서를 바꾸지 않고 사유를 남김.
숫자를 지어내지 않음(`[확인필요: 재정렬 가중치]`).
재정렬 전후 순위는 기록으로 남길 자리에 담음 — 실제 기록은 검사·기록 묶음이 끼움.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from common.config import Settings, get_settings

from .result import (
    Candidate,
    RetrievalKind,
    RetrievalResult,
    RetrievalTrace,
    ScoreKind,
)

__all__ = [
    "RERANK_AXES",
    "RERANK_WEIGHTS_OPEN_TAG",
    "RerankFactors",
    "rerank",
]

# ⑤ K-1 「리랭킹 여부」 칸이 적은 기준 4축. 이름을 늘리거나 줄이지 않았음.
RERANK_AXES: tuple[str, ...] = (
    "preference_similarity",
    "distance",
    "repeat_avoidance",
    "confidence",
)

RERANK_WEIGHTS_OPEN_TAG = "[확인필요: 재정렬 가중치 — ⑤ K-1에 축은 있고 가중치가 없음]"


@dataclass(frozen=True, slots=True)
class RerankFactors:
    """후보 1건의 축 값. 값이 없는 축은 `None`으로 두고 채워 넣지 않음."""

    preference_similarity: float | None = None
    distance: float | None = None
    repeat_avoidance: float | None = None
    confidence: float | None = None

    def as_map(self) -> dict[str, float | None]:
        return {
            "preference_similarity": self.preference_similarity,
            "distance": self.distance,
            "repeat_avoidance": self.repeat_avoidance,
            "confidence": self.confidence,
        }


def _key_of(candidate: Candidate) -> str:
    return candidate.source.locator


def rerank(
    result: RetrievalResult,
    factors: Mapping[str, RerankFactors] | None = None,
    settings: Settings | None = None,
) -> RetrievalResult:
    """후보를 다시 줄 세움. 설정이 없거나 비어 있으면 순서를 바꾸지 않음."""
    conf = settings if settings is not None else get_settings()
    before = tuple(_key_of(candidate) for candidate in result.candidates)

    if result.is_empty:
        return result
    if conf.knowledge_rerank_enabled is not True:
        return RetrievalResult(
            route_id=result.route_id,
            kind=result.kind,
            candidates=result.candidates,
            notes=(*result.notes, "재정렬을 쓰지 않기로 설정돼 있음 — 순서를 그대로 둠"),
            traces=result.traces,
        )

    weights = conf.knowledge_rerank_weights
    unknown = sorted(set(weights) - set(RERANK_AXES))
    if unknown:
        raise ValueError(f"⑤ K-1에 없는 재정렬 축임 — {unknown}")
    if not weights:
        return RetrievalResult(
            route_id=result.route_id,
            kind=result.kind,
            candidates=result.candidates,
            notes=(*result.notes, f"순서를 바꾸지 않았음 — {RERANK_WEIGHTS_OPEN_TAG}"),
            traces=(
                *result.traces,
                RetrievalTrace(stage="재정렬", before=before, after=before, detail={}),
            ),
        )

    given = dict(factors or {})
    missing = sorted(key for key in before if key not in given)

    def _score(candidate: Candidate) -> float:
        axis_values = given[_key_of(candidate)].as_map()
        total = 0.0
        for axis, weight in weights.items():
            value = axis_values.get(axis)
            if value is None:
                continue
            total += weight * value
        return total

    if missing:
        return RetrievalResult(
            route_id=result.route_id,
            kind=result.kind,
            candidates=result.candidates,
            notes=(
                *result.notes,
                f"축 값이 없는 후보가 있어 순서를 바꾸지 않았음 — {missing}",
            ),
            traces=(
                *result.traces,
                RetrievalTrace(stage="재정렬", before=before, after=before, detail={}),
            ),
        )

    ranked = sorted(result.candidates, key=_score, reverse=True)
    keep = conf.knowledge_rerank_keep
    if keep is not None:
        ranked = ranked[:keep]
    rescored = tuple(
        Candidate(
            payload=candidate.payload,
            source=candidate.source,
            score=_score(candidate),
            score_kind=ScoreKind.RERANK,
        )
        for candidate in ranked
    )
    after = tuple(_key_of(candidate) for candidate in rescored)
    trace = RetrievalTrace(
        stage="재정렬",
        before=before,
        after=after,
        detail={"weights": dict(weights), "keep": keep},
    )
    return RetrievalResult.of(
        result.route_id,
        RetrievalKind(result.kind),
        rescored,
        reason_when_empty="재정렬 뒤 남은 후보가 0건임",
        notes=(*result.notes, f"재정렬로 {len(before)}건 → {len(after)}건이 됨"),
        traces=(*result.traces, trace),
    )
