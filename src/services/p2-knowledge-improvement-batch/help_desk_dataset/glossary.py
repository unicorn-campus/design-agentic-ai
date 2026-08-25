from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NormalizationResult:
    original: str
    canonical_terms: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class Glossary:
    name: str
    conflict_policy: str
    unknown_policy: str
    aliases: dict[str, tuple[str, ...]]

    def normalize(self, term: str) -> NormalizationResult:
        canonical_terms = self.aliases.get(term)
        if canonical_terms is None:
            LOGGER.warning("glossary_unknown_term", extra={"lexicon_name": self.name, "term": term})
            return NormalizationResult(term, (), self.unknown_policy)
        if len(canonical_terms) > 1:
            LOGGER.warning("glossary_conflict", extra={"lexicon_name": self.name, "term": term})
            return NormalizationResult(term, canonical_terms, self.conflict_policy)
        return NormalizationResult(term, canonical_terms, "정규화")


def load_glossary(path: Path) -> Glossary:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    spec = data["사전 운영 스펙"]
    aliases: dict[str, list[str]] = {}
    for entry in data["대표어별 동의어"]:
        canonical = entry["대표어"]
        aliases.setdefault(canonical, []).append(canonical)
        for alias in entry["동의어"]:
            aliases.setdefault(alias, []).append(canonical)
    return Glossary(
        name=spec["사전 이름"],
        conflict_policy=spec["1:N 충돌 처리"],
        unknown_policy=spec["미등록어 처리"],
        aliases={alias: tuple(values) for alias, values in aliases.items()},
    )
