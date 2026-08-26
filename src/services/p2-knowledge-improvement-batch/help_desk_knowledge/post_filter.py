from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from .results import Evidence, SearchResult


def filter_evidence(
    evidence: Iterable[Evidence],
    minimum_score: float,
    official_domains: frozenset[str] | None = None,
) -> SearchResult:
    kept = []
    for item in evidence:
        if item.score < minimum_score:
            continue
        if official_domains is not None:
            hostname = urlparse(item.source).hostname
            if hostname not in official_domains:
                continue
        kept.append(item)
    if not kept:
        return SearchResult.empty("후보 수 0건")
    return SearchResult(evidence_refs=tuple(kept))
