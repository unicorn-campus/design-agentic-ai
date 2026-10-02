"""카드 정식명에서 검색용 별칭을 만들고 자동 제외 기준을 적용하는 순수 규칙임."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence


# 제외 사유 코드. 검수 파일과 시험이 함께 쓰는 값이라 문자열을 한 곳에서만 정의함.
REASON_TOO_SHORT = "too_short"
REASON_AMBIGUOUS = "ambiguous"
REASON_COMMON_NOUN = "common_noun"
REASON_EXCLUDED_BY_OVERRIDE = "excluded_by_override"

ORIGIN_PREFIX_STRIPPED = "prefix_stripped"
ORIGIN_PREFIX_STRIPPED_WITH_SUFFIX = "prefix_stripped_with_suffix"
ORIGIN_WITH_SUFFIX = "with_suffix"
ORIGIN_OVERRIDE = "override"


def compact(name: str) -> str:
    """공백을 모두 없앤 검색 토큰 형태를 반환함.

    인자: name은 호출자가 이미 소문자·NFKC로 정규화한 카드명 또는 별칭임.
    반환값: 토크나이저가 내보내는 토큰과 같은 모양의 문자열임.
    """

    return "".join(str(name).split())


@dataclass(frozen=True)
class AliasRules:
    """별칭 후보를 만들 때 적용할 접두어·접미어·최소 길이 규칙임."""

    brand_prefixes: tuple[str, ...] = ()  # 카드명 맨 앞에서 떼어 낼 브랜드 낱말
    suffixes: tuple[str, ...] = ()  # 사람들이 뒤에 덧붙여 부르는 낱말(예: 카드)
    min_length: int = 3  # 공백을 뺀 글자 수의 하한. 너무 짧은 별칭은 아무 문서나 끌어옴


@dataclass(frozen=True)
class AliasOverrides:
    """사람이 검수해 확정한 별칭 추가·제외 목록임."""

    include: tuple[tuple[str, str], ...] = ()  # (별칭, 정식 카드명) 쌍. 정식명은 띄어 쓴 원래 이름임
    exclude: frozenset[str] = frozenset()  # 자동 생성되더라도 쓰지 않을 별칭

    @classmethod
    def from_mapping(
        cls,
        include: Mapping[str, str] | None = None,
        exclude: Iterable[str] | None = None,
    ) -> "AliasOverrides":
        """설정 파일에서 읽은 dict·list를 불변 승인 목록으로 바꿈."""

        return cls(
            include=tuple(sorted((str(key), str(value)) for key, value in dict(include or {}).items())),
            exclude=frozenset(str(value) for value in (exclude or ())),
        )

    def include_items(self) -> tuple[tuple[str, str], ...]:
        """추가 별칭을 정렬된 (별칭, 정식명) 쌍으로 반환함."""

        return tuple(sorted(self.include))


@dataclass(frozen=True)
class AliasCandidate:
    """검색 질의에서 정식 카드 토큰으로 바꿔 줄 별칭 한 건임."""

    alias: str  # 공백을 뺀 별칭 키. 형태소 분석 결과 토큰과 맞대 보는 값임
    canonical: str  # 공백을 뺀 정식 카드명 토큰
    source_name: str  # 별칭을 만든 띄어 쓴 원래 카드명
    origin: str  # 별칭을 만든 규칙 이름
    # 형태소 분석기에 등록할 표면형. 원래 카드명의 띄어쓰기를 살린 형태이며 공백이 없으면 alias와 같음.
    # Kiwi는 사용자 단어를 공백과 무관하게 한 항목으로 보므로, 띄어 쓴 형태 하나만 등록하면
    # "가게모음 프리미엄"과 "가게모음프리미엄"이 모두 같은 단어로 잡힘(kiwipiepy 0.23.2에서 실측).
    surface: str = ""

    def registered_surface(self) -> str:
        """형태소 분석기에 등록할 표면형을 반환하며, 값이 없으면 별칭 키를 그대로 씀."""

        return self.surface or self.alias


@dataclass(frozen=True)
class RejectedAlias:
    """자동 생성했으나 쓰지 않기로 한 별칭과 그 사유임."""

    alias: str
    reason: str
    source_names: tuple[str, ...]  # 같은 별칭을 만든 정식 카드명 전체


@dataclass(frozen=True)
class AliasPlan:
    """이번 색인 세대에 쓸 별칭과 검수 대상 제외 목록을 함께 담음."""

    accepted: tuple[AliasCandidate, ...]
    rejected: tuple[RejectedAlias, ...]

    def mapping(self) -> dict[str, str]:
        """분석 결과 토큰(공백 제거)에서 정식 카드 토큰으로 가는 치환표를 반환함."""

        return {candidate.alias: candidate.canonical for candidate in self.accepted}

    def surface_mapping(self) -> dict[str, str]:
        """형태소 분석기에 등록할 표면형에서 정식 카드 토큰으로 가는 표를 반환함.

        반환값: 표면형 오름차순 dict임. 표면형의 공백을 지우면 mapping()의 키와 같음.
        """

        return {
            candidate.registered_surface(): candidate.canonical
            for candidate in sorted(self.accepted, key=lambda item: item.registered_surface())
        }


def generate_candidates(
    card_names: Iterable[str],
    rules: AliasRules,
) -> tuple[AliasCandidate, ...]:
    """정식 카드명마다 규칙으로 만들 수 있는 별칭 후보를 모두 만듦.

    목적: 사람들이 브랜드 낱말을 빼고 부르거나 뒤에 "카드"를 붙여 묻는 말을 정식명으로 잇기 위함.
    방법: 접두어를 뗀 형태, 접두어를 뗀 형태에 접미어를 붙인 형태, 전체에 접미어를 붙인 형태를 만듦.
    인자: card_names는 소문자·NFKC로 정규화하고 공백을 한 칸으로 줄인 띄어 쓴 카드명임.
    반환값: 별칭·정식 토큰 순으로 정렬한 후보 목록임. 정식 토큰과 같은 후보는 치환할 것이 없어 제외함.
    부수효과: 없음.
    """

    candidates: dict[tuple[str, str, str], AliasCandidate] = {}
    for raw_name in card_names:
        name = " ".join(str(raw_name).split())
        canonical = compact(name)
        if not canonical:
            continue
        for alias, surface, origin in _candidate_forms(name, canonical, rules):
            if not alias or alias == canonical:
                continue
            key = (alias, canonical, origin)
            candidates.setdefault(key, AliasCandidate(alias, canonical, name, origin, surface))
    return tuple(
        sorted(candidates.values(), key=lambda item: (item.alias, item.canonical, item.origin))
    )


def _candidate_forms(
    name: str,
    canonical: str,
    rules: AliasRules,
) -> list[tuple[str, str, str]]:
    """카드명 하나에서 만들 수 있는 (별칭 키, 등록 표면형, 규칙 이름)을 모음.

    접두어를 뗀 형태만 원래 띄어쓰기를 살린 표면형으로 등록함. 접미어를 붙인 형태는 띄어 쓴 표면형을
    따로 두지 않아도 접두어 제거 형태가 먼저 잡혀 같은 결과가 나오므로 붙여 쓴 형태만 둠.
    """

    forms: list[tuple[str, str, str]] = []
    for suffix in rules.suffixes:
        joined = canonical + compact(suffix)
        forms.append((joined, joined, ORIGIN_WITH_SUFFIX))
    for prefix in rules.brand_prefixes:
        head = " ".join(str(prefix).split())
        if not head or not name.startswith(f"{head} "):
            continue
        spaced_rest = name[len(head):].strip()
        rest = compact(spaced_rest)
        if not rest:
            continue
        forms.append((rest, spaced_rest, ORIGIN_PREFIX_STRIPPED))
        for suffix in rules.suffixes:
            joined = rest + compact(suffix)
            forms.append((joined, joined, ORIGIN_PREFIX_STRIPPED_WITH_SUFFIX))
    return forms


def build_alias_plan(
    card_names: Sequence[str],
    *,
    rules: AliasRules,
    overrides: AliasOverrides,
    is_common_noun: Callable[[str], bool],
) -> AliasPlan:
    """규칙으로 만든 별칭 후보에 자동 제외 기준과 사람 승인 목록을 적용함.

    목적: 검색 품질을 떨어뜨리는 별칭이 사람 확인 없이 색인에 들어가지 않게 함.
    방법: 후보를 만들고 ① 중복 지시 ② 사람 제외 ③ 최소 길이 ④ 일반명사 충돌 순으로 거른 뒤,
      사람이 승인한 추가 별칭을 마지막에 덮어씀.
    인자: card_names는 정규화된 띄어 쓴 카드명이며, overrides의 별칭도 같은 규칙으로 정규화되어 있어야 함.
    인자: is_common_noun은 사용자 사전 없이 분석했을 때 별칭이 일반명사 한 개인지 판정하는 함수임.
    반환값: 채택한 별칭과 제외 사유가 붙은 후보를 함께 담은 AliasPlan임.
    예외: 승인 목록의 정식명이 카드명 목록에 없거나 같은 별칭을 추가와 제외에 함께 넣으면 ValueError를 발생시킴.
    부수효과: 없음. is_common_noun 구현체의 부수효과는 호출자가 책임짐.
    """

    names = [" ".join(str(name).split()) for name in card_names]
    canonical_tokens = {compact(name) for name in names if compact(name)}
    canonical_by_name = {name: compact(name) for name in names}

    sources_by_alias: dict[str, list[AliasCandidate]] = {}
    for candidate in generate_candidates(names, rules):
        sources_by_alias.setdefault(candidate.alias, []).append(candidate)

    accepted: dict[str, AliasCandidate] = {}
    rejected: list[RejectedAlias] = []
    for alias in sorted(sources_by_alias):
        group = sources_by_alias[alias]
        source_names = tuple(sorted({item.source_name for item in group}))
        targets = {item.canonical for item in group}
        reason = _rejection_reason(
            alias,
            targets,
            overrides=overrides,
            rules=rules,
            canonical_tokens=canonical_tokens,
            is_common_noun=is_common_noun,
        )
        if reason is not None:
            rejected.append(RejectedAlias(alias, reason, source_names))
            continue
        # 같은 별칭을 여러 규칙이 만들면 짧은 쪽(접두어만 뗀 형태)을 대표로 남겨 사유 추적을 단순하게 함.
        accepted[alias] = sorted(group, key=lambda item: (item.origin, item.source_name))[0]

    for raw_alias, raw_name in overrides.include_items():
        # 승인 목록에는 띄어 쓴 별칭도 적을 수 있으므로 적힌 모양은 등록용 표면형으로, 공백을 뺀 값은 키로 씀.
        surface = " ".join(str(raw_alias).split())
        alias = compact(surface)
        if alias in overrides.exclude:
            raise ValueError(f"승인 목록의 별칭이 제외 목록에도 있습니다: {surface}")
        name = " ".join(str(raw_name).split())
        if name not in canonical_by_name:
            raise ValueError(f"승인 목록의 정식 카드명을 찾을 수 없습니다: {raw_name}")
        canonical = canonical_by_name[name]
        if not alias or alias == canonical:
            raise ValueError(f"별칭과 정식 토큰이 같아 치환할 것이 없습니다: {surface}")
        accepted[alias] = AliasCandidate(alias, canonical, name, ORIGIN_OVERRIDE, surface)
        rejected = [item for item in rejected if item.alias != alias]

    return AliasPlan(
        accepted=tuple(sorted(accepted.values(), key=lambda item: item.alias)),
        rejected=tuple(sorted(rejected, key=lambda item: (item.alias, item.reason))),
    )


def _rejection_reason(
    alias: str,
    targets: set[str],
    *,
    overrides: AliasOverrides,
    rules: AliasRules,
    canonical_tokens: set[str],
    is_common_noun: Callable[[str], bool],
) -> str | None:
    """별칭 후보 하나의 자동 제외 사유를 판정하고 통과하면 None을 반환함."""

    if alias in overrides.exclude:
        return REASON_EXCLUDED_BY_OVERRIDE
    if len(targets) > 1 or alias in canonical_tokens:
        # 한 별칭이 여러 카드를 가리키면 질문이 어느 카드를 말하는지 고를 수 없어 오히려 검색이 나빠짐.
        return REASON_AMBIGUOUS
    if len(alias) < int(rules.min_length):
        return REASON_TOO_SHORT
    if is_common_noun(alias):
        # 대중교통·장보기처럼 일반명사이기도 한 별칭은 카드와 무관한 문서까지 끌어옴.
        return REASON_COMMON_NOUN
    return None


__all__ = [
    "AliasCandidate",
    "AliasOverrides",
    "AliasPlan",
    "AliasRules",
    "RejectedAlias",
    "build_alias_plan",
    "compact",
    "generate_candidates",
]
