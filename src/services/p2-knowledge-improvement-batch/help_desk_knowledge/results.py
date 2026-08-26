from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    content: str
    source: str
    score: float
    original_term: str | None = None
    canonical_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchResult:
    evidence_refs: tuple[Evidence, ...]
    reason: str | None = None

    @classmethod
    def empty(cls, reason: str) -> "SearchResult":
        return cls(evidence_refs=(), reason=reason)
