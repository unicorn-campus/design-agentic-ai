"""역할별 열람 등급을 검색 전·융합 후 같은 규칙으로 적용함."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .search_filter import MetadataFilter, MetadataValue


ROLE_ACCESS = {
    "agent": frozenset({"public", "internal"}),
    "auditor": frozenset({"public", "internal", "restricted"}),
}


def is_known_role(role: str) -> bool:
    return role in ROLE_ACCESS


def allowed_levels(role: str) -> frozenset[str]:
    try:
        return ROLE_ACCESS[role]
    except KeyError as error:
        raise ValueError(f"알 수 없는 role: {role}") from error


def build_filter(
    role: str,
    filters: dict[str, MetadataValue] | None = None,
) -> MetadataFilter:
    return MetadataFilter.from_parts(
        allowed_values={"access_level": allowed_levels(role)},
        equalities=filters,
    )


def _metadata(candidate: Any) -> dict:
    if isinstance(candidate, dict):
        return candidate.get("metadata", candidate)
    return getattr(candidate, "metadata", {})


def filter_candidates(candidates: Iterable[Any], role: str, filters: dict[str, Any] | None = None) -> list[Any]:
    levels = allowed_levels(role)
    result = []
    for candidate in candidates:
        metadata = _metadata(candidate)
        if metadata.get("access_level") not in levels:
            continue
        if filters and any(metadata.get(key) != value for key, value in filters.items()):
            continue
        result.append(candidate)
    return result
