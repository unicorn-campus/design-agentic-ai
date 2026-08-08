"""후보 결과의 반환 형태 — 이 묶음이 소유하는 값.

결과 1건은 **내용 · 출처 · 점수** 3가지를 함께 가짐. 출처 없는 결과는 만들 수 없음
(만들려 하면 `MissingProvenance`로 바로 드러남).

후보가 0건이면 **빈 결과 + 사유**를 돌려줌. 없는 근거를 채워 넣지 않음.
낱개 값의 키 이름은 ④ 「입출력 형식」이 주인이며 여기서 새로 짓지 않음.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

__all__ = [
    "Candidate",
    "MissingProvenance",
    "Provenance",
    "RetrievalKind",
    "RetrievalResult",
    "RetrievalTrace",
    "ScoreKind",
]


class MissingProvenance(ValueError):
    """출처가 없는 후보를 만들려 했음. 근거를 되짚을 수 없는 결과를 돌려주지 않음."""


class RetrievalKind(StrEnum):
    """어느 경로가 낸 결과인가. 경로를 섞지 않으려고 결과마다 적어 둠."""

    STRUCTURED = "조회"
    VECTOR_SIMILARITY = "벡터 유사도"
    ATTRIBUTE_FILTER = "속성 필터 검색"
    GLOSSARY = "용어사전"


class ScoreKind(StrEnum):
    """점수 칸에 무엇이 들어 있나. 뜻이 다른 점수를 한 칸에 섞지 않음."""

    NONE = "점수 없음"
    COSINE_SIMILARITY = "코사인 유사도"
    RERANK = "재정렬 점수"
    DISTANCE_ASC = "거리 오름차순 순위값"


@dataclass(frozen=True, slots=True)
class Provenance:
    """이 후보가 어디서 왔나. 어느 경로 · 어느 자리 · 실물인지 합성인지를 담음."""

    route_id: str
    locator: str
    design_row: str
    origin: str
    read_at: datetime

    def describe(self) -> str:
        return f"{self.route_id} · {self.locator} · {self.design_row} · {self.origin}"


@dataclass(frozen=True, slots=True)
class Candidate:
    """후보 1건. `payload`의 키 이름은 ④가 주인이며 이 묶음이 새로 짓지 않음."""

    payload: Mapping[str, Any]
    source: Provenance
    score: float | None = None
    score_kind: ScoreKind = ScoreKind.NONE

    def __post_init__(self) -> None:
        if not isinstance(self.source, Provenance):
            raise MissingProvenance("후보에 출처가 없음 — 출처 없는 결과를 돌려주지 않음")
        if self.score is None and self.score_kind is not ScoreKind.NONE:
            raise ValueError("점수가 없는데 점수 종류를 적었음")


@dataclass(frozen=True, slots=True)
class RetrievalTrace:
    """변환 전후 · 재정렬 전후를 남길 자리. 실제 기록은 검사·기록 묶음이 끼움."""

    stage: str
    before: tuple[str, ...]
    after: tuple[str, ...]
    detail: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """검색 1회의 결과. 경로가 여럿이면 이 그릇을 경로마다 따로 돌려줌."""

    route_id: str
    kind: RetrievalKind
    candidates: tuple[Candidate, ...] = ()
    empty_reason: str | None = None
    notes: tuple[str, ...] = ()
    traces: tuple[RetrievalTrace, ...] = ()

    def __post_init__(self) -> None:
        if self.candidates and self.empty_reason:
            raise ValueError("후보가 있는데 빈 결과 사유를 적었음")
        if not self.candidates and not self.empty_reason:
            raise ValueError("후보가 0건이면 사유를 반드시 적음 — 조용히 비우지 않음")

    @property
    def is_empty(self) -> bool:
        return not self.candidates

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @classmethod
    def empty(
        cls,
        route_id: str,
        kind: RetrievalKind,
        reason: str,
        notes: Iterable[str] = (),
        traces: Iterable[RetrievalTrace] = (),
    ) -> RetrievalResult:
        """빈 결과 + 사유. 「모른다」고 답하게 하는 자리임."""
        return cls(
            route_id=route_id,
            kind=kind,
            candidates=(),
            empty_reason=reason,
            notes=tuple(notes),
            traces=tuple(traces),
        )

    @classmethod
    def of(
        cls,
        route_id: str,
        kind: RetrievalKind,
        candidates: Iterable[Candidate],
        reason_when_empty: str,
        notes: Iterable[str] = (),
        traces: Iterable[RetrievalTrace] = (),
    ) -> RetrievalResult:
        """후보가 0건으로 나오면 자동으로 빈 결과 + 사유가 됨."""
        rows = tuple(candidates)
        if not rows:
            return cls.empty(route_id, kind, reason_when_empty, notes, traces)
        return cls(
            route_id=route_id,
            kind=kind,
            candidates=rows,
            notes=tuple(notes),
            traces=tuple(traces),
        )

    def payloads(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(candidate.payload for candidate in self.candidates)

    def sources(self) -> tuple[Provenance, ...]:
        return tuple(candidate.source for candidate in self.candidates)


def now_utc() -> datetime:
    return datetime.now(UTC)
