"""K-3 용어사전 — **적용 지점만** 만듦. 사전 파일과 읽는 코드는 데이터 준비 묶음에 이미 있음.

여기서 사전을 다시 만들지 않음. `common.dataset`의 `load_glossary` · `to_canonical` ·
`allergen_codes_for`를 그대로 부름.

⑤ K-3이 정한 적용 지점 2곳만 둠.

| 사전 | 적용 지점 | 이 파일의 함수 |
|------|----------|--------------|
| ⓐ 음식 카테고리 · 맛 태그 | 질의 확장 · 출력 표기 | `expand_query_tags` · `display_labels` |
| ⓑ 알레르겐 라벨 → 제외 식재료 코드 | **결정론 단계 앞** | `to_excluded_ingredient_codes` |

ⓑ는 모델 호출 앞에서 라벨을 코드로 바꾸는 자리임. 원문 라벨은 모델 입력 규격에 칸이 없음.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from common.config import Settings, get_settings
from common.dataset import (
    AllergenMapping,
    Glossary,
    GlossaryKind,
    allergen_codes_for,
    load_glossary,
    to_canonical,
)

from .prefilter import PrefilterVerdict, allergen_hard_filter
from .result import RetrievalTrace

__all__ = [
    "APPLY_POINT_KEYS",
    "AllergenGate",
    "QueryExpansion",
    "display_labels",
    "expand_query_tags",
    "load_food_tag_glossary",
    "load_allergen_glossary",
    "to_excluded_ingredient_codes",
]

APPLY_POINT_KEYS: tuple[str, ...] = ("food_tag", "allergen_code")


@dataclass(frozen=True, slots=True)
class QueryExpansion:
    """질의 확장 결과 — 바꾼 낱말과 바꾸지 못한 낱말을 갈라 담음."""

    given: tuple[str, ...]
    expanded: tuple[str, ...]
    unmapped: tuple[str, ...]
    applied: bool
    note: str

    def trace(self) -> RetrievalTrace:
        return RetrievalTrace(
            stage="질의 확장",
            before=self.given,
            after=self.expanded,
            detail={"unmapped": list(self.unmapped), "applied": self.applied},
        )


@dataclass(frozen=True, slots=True)
class AllergenGate:
    """ⓑ 사전을 지난 결과 + 그 뒤에 붙는 결정론 필터 판정."""

    mapping: AllergenMapping
    verdict: PrefilterVerdict

    @property
    def excluded_ingredient_codes(self) -> tuple[str, ...]:
        """모델 입력 규격에 실을 유일한 칸의 값임(원문 라벨은 칸이 없음)."""
        return self.mapping.codes


def load_food_tag_glossary(settings: Settings | None = None) -> Glossary:
    return load_glossary(GlossaryKind.FOOD_TAG, settings)


def load_allergen_glossary(settings: Settings | None = None) -> Glossary:
    return load_glossary(GlossaryKind.ALLERGEN_CODE, settings)


def _apply_point(key: str, settings: Settings | None = None) -> str | None:
    conf = settings if settings is not None else get_settings()
    return conf.knowledge_glossary_apply_points.get(key)


def expand_query_tags(
    tags: Iterable[str],
    glossary: Glossary,
    settings: Settings | None = None,
) -> QueryExpansion:
    """ⓐ 적용 지점 — 온보딩 태그를 후보 카테고리 대표어로 넓힘.

    - 한 태그가 대표어 2개에 걸리면 **양쪽을 모두 남김**(줄이지 않고 재정렬에 맡김)
    - 사전에 없는 태그는 **필터에 넣지 않고** 기록만 남김
    """
    conf = settings if settings is not None else get_settings()
    given = tuple(str(tag) for tag in tags)
    if conf.knowledge_query_expansion_enabled is not True:
        return QueryExpansion(
            given=given,
            expanded=given,
            unmapped=(),
            applied=False,
            note="질의 확장을 쓰지 않기로 설정돼 있음 — 원문을 그대로 넘김",
        )

    expanded: list[str] = []
    unmapped: list[str] = []
    for tag in given:
        result = to_canonical(glossary, tag)
        if result.matched:
            expanded.extend(result.canonical_terms)
        else:
            unmapped.append(result.passthrough)
    point = _apply_point("food_tag", conf) or "[확인필요: 용어사전 적용 지점]"
    return QueryExpansion(
        given=given,
        expanded=tuple(dict.fromkeys(expanded)),
        unmapped=tuple(unmapped),
        applied=True,
        note=f"적용 지점 — {point}",
    )


def display_labels(
    canonical_terms: Iterable[str],
    glossary: Glossary,
) -> tuple[str, ...]:
    """ⓐ 출력 표기 — 사전에 있는 대표어만 화면 표기로 내보냄."""
    usable = {term.canonical for term in glossary.usable_terms}
    return tuple(term for term in canonical_terms if term in usable)


def to_excluded_ingredient_codes(
    allergen_labels: Sequence[str],
    glossary: Glossary,
    place_ingredient_codes: Iterable[str] | None = None,
) -> AllergenGate:
    """ⓑ 적용 지점 — 모델 호출 **앞**에서 라벨을 코드로 바꾸고 결정론 필터를 지남.

    라벨을 하나라도 코드로 못 바꾸면 사전이 페일세이프로 표시하고,
    그 값을 받은 결정론 필터가 그 식당을 **차단**함.
    """
    mapping = allergen_codes_for(glossary, allergen_labels)
    verdict = allergen_hard_filter(
        excluded_ingredient_codes=mapping.codes,
        place_ingredient_codes=place_ingredient_codes,
        mapping_failsafe=mapping.failsafe,
    )
    return AllergenGate(mapping=mapping, verdict=verdict)
