"""용어사전 — 여러 이름으로 불리는 것을 **대표어 하나로 묶는 표**임.

사전은 파일 1벌만 둠. 코드 안에 같은 매핑을 또 적지 않음.
사전에 없는 낱말은 **조용히 버리지 않고 원문을 그대로 넘기고 기록에 남김.**

어디에 끼울지는 여기서 정하지 않음 — 적용 지점은 검색 쪽 몫임.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from common.config import Settings, get_settings

__all__ = [
    "DEFAULT_GLOSSARY_DIR",
    "AllergenMapping",
    "CanonicalResult",
    "Glossary",
    "GlossaryKind",
    "GlossaryTerm",
    "UnmappedTerm",
    "allergen_codes_for",
    "glossary_dir",
    "load_glossary",
    "to_canonical",
    "unmapped_report",
]

DEFAULT_GLOSSARY_DIR = Path(__file__).resolve().parent / "config"
_LOGGER = logging.getLogger("common.dataset.glossary")
_OPEN_TAG_HEAD = "[확인필요"


class GlossaryKind(StrEnum):
    """사전 2종. 파일이 따로이고 충돌 처리 규칙도 다름."""

    FOOD_TAG = "food_tags"
    ALLERGEN_CODE = "allergen_codes"


_FILE_NAME: dict[GlossaryKind, str] = {
    GlossaryKind.FOOD_TAG: "glossary_food_tags.csv",
    GlossaryKind.ALLERGEN_CODE: "glossary_allergen_codes.csv",
}


@dataclass(frozen=True, slots=True)
class GlossaryTerm:
    """사전 1행."""

    canonical: str
    synonyms: tuple[str, ...]
    kind: str
    collision_rule: str
    status: str
    source: str
    excluded_ingredient_codes: tuple[str, ...] = ()

    @property
    def is_open(self) -> bool:
        """대표어 자리가 아직 비어 있는 행인가."""
        return self.canonical.startswith(_OPEN_TAG_HEAD)


@dataclass(frozen=True, slots=True)
class UnmappedTerm:
    """사전에 없던 낱말 1건. 사전을 늘릴 근거로 씀."""

    term: str
    glossary: GlossaryKind
    handling: str


@dataclass(frozen=True, slots=True)
class CanonicalResult:
    """바꿔 본 결과. 못 바꿨으면 원문이 그대로 들어 있음."""

    given: str
    matched: bool
    canonical_terms: tuple[str, ...]
    passthrough: str
    unmapped: UnmappedTerm | None = None


@dataclass
class Glossary:
    """사전 1벌. 미등록어 기록을 스스로 모음."""

    kind: GlossaryKind
    terms: tuple[GlossaryTerm, ...]
    source_file: Path
    unmapped_log: list[UnmappedTerm] = field(default_factory=list)

    @property
    def open_row_count(self) -> int:
        return sum(1 for term in self.terms if term.is_open)

    @property
    def usable_terms(self) -> tuple[GlossaryTerm, ...]:
        return tuple(term for term in self.terms if not term.is_open)

    def lookup(self, term: str) -> tuple[GlossaryTerm, ...]:
        """한 낱말이 두 대표어에 걸리면 **둘 다** 돌려줌. 여기서 하나로 줄이지 않음."""
        needle = _normalise(term)
        hits = [
            row
            for row in self.usable_terms
            if needle == _normalise(row.canonical)
            or needle in {_normalise(name) for name in row.synonyms}
        ]
        return tuple(hits)


def _normalise(text: str) -> str:
    return text.strip().lstrip("#").lower()


def _split_list(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split("|") if part.strip())


def glossary_dir(settings: Settings | None = None) -> Path:
    conf = settings if settings is not None else get_settings()
    if conf.dataset_glossary_dir:
        return Path(conf.dataset_glossary_dir)
    return DEFAULT_GLOSSARY_DIR


def load_glossary(kind: GlossaryKind, settings: Settings | None = None) -> Glossary:
    """사전 파일을 읽음. 파일이 없으면 지어내지 않고 실패함."""
    path = glossary_dir(settings) / _FILE_NAME[kind]
    if not path.exists():
        raise FileNotFoundError(f"사전 파일이 없음: {path}")
    rows: list[GlossaryTerm] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            rows.append(
                GlossaryTerm(
                    canonical=(record.get("canonical") or "").strip(),
                    synonyms=_split_list(record.get("synonyms") or ""),
                    kind=(record.get("kind") or "").strip(),
                    collision_rule=(record.get("collision_rule") or "").strip(),
                    status=(record.get("status") or "").strip(),
                    source=(record.get("source") or "").strip(),
                    excluded_ingredient_codes=_split_list(
                        record.get("excluded_ingredient_codes") or ""
                    ),
                )
            )
    return Glossary(kind=kind, terms=tuple(rows), source_file=path)


def to_canonical(glossary: Glossary, term: str) -> CanonicalResult:
    """낱말 하나를 대표어로 바꿈.

    - 걸리는 대표어가 여럿이면 **모두** 돌려줌(어느 하나로 줄이지 않음)
    - 걸리는 것이 없으면 원문을 그대로 넘기고 기록을 1건 남김
    """
    hits = glossary.lookup(term)
    if hits:
        return CanonicalResult(
            given=term,
            matched=True,
            canonical_terms=tuple(row.canonical for row in hits),
            passthrough=term,
        )

    handling = (
        "원문 그대로 넘기고 필터에 넣지 않음"
        if glossary.kind is GlossaryKind.FOOD_TAG
        else "원문 그대로 넘기고 페일세이프 — 해당 식당 전체 제외"
    )
    record = UnmappedTerm(term=term, glossary=glossary.kind, handling=handling)
    glossary.unmapped_log.append(record)
    _LOGGER.warning(
        "사전에 없는 낱말임", extra={"glossary": glossary.kind.value, "term": term}
    )
    return CanonicalResult(
        given=term,
        matched=False,
        canonical_terms=(),
        passthrough=term,
        unmapped=record,
    )


@dataclass(frozen=True, slots=True)
class AllergenMapping:
    """알레르겐 라벨을 제외 식재료 코드로 바꾼 결과."""

    labels: tuple[str, ...]
    codes: tuple[str, ...]
    failsafe: bool
    reason: str


def allergen_codes_for(glossary: Glossary, labels: Iterable[str]) -> AllergenMapping:
    """라벨 목록을 코드 합집합으로 바꿈. 하나라도 못 바꾸면 페일세이프임."""
    if glossary.kind is not GlossaryKind.ALLERGEN_CODE:
        raise ValueError("알레르겐 사전이 아님")
    given = tuple(labels)
    codes: set[str] = set()
    unresolved: list[str] = []
    for label in given:
        result = to_canonical(glossary, label)
        if not result.matched:
            unresolved.append(label)
            continue
        for row in glossary.lookup(label):
            usable = [
                code for code in row.excluded_ingredient_codes
                if not code.startswith(_OPEN_TAG_HEAD)
            ]
            if usable:
                codes.update(usable)
            else:
                unresolved.append(label)
    if unresolved:
        return AllergenMapping(
            labels=given,
            codes=tuple(sorted(codes)),
            failsafe=True,
            reason=(
                "코드로 바꾸지 못한 라벨이 있음 — "
                f"{sorted(set(unresolved))} · [확인필요: 제외 식재료 코드 체계]"
            ),
        )
    return AllergenMapping(labels=given, codes=tuple(sorted(codes)), failsafe=False, reason="")


def unmapped_report(glossaries: Sequence[Glossary]) -> tuple[UnmappedTerm, ...]:
    """모아 둔 미등록어 기록. 사전을 늘릴 때 이 목록을 봄."""
    return tuple(record for glossary in glossaries for record in glossary.unmapped_log)
