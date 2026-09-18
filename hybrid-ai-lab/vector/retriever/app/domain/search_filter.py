"""벡터 DB 문법과 무관한 검색 필터 계약."""

from collections.abc import Collection, Mapping
from dataclasses import dataclass


MetadataValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class MetadataFilter:
    """허용 목록과 일치 조건을 불변 값으로 표현함."""

    allowed_values: tuple[tuple[str, tuple[MetadataValue, ...]], ...] = ()
    equalities: tuple[tuple[str, MetadataValue], ...] = ()

    @classmethod
    def from_parts(
        cls,
        *,
        allowed_values: Mapping[str, Collection[MetadataValue]] | None = None,
        equalities: Mapping[str, MetadataValue] | None = None,
    ) -> "MetadataFilter":
        normalized_allowed = tuple(
            (key, tuple(sorted(values, key=lambda value: (type(value).__name__, repr(value)))))
            for key, values in sorted((allowed_values or {}).items())
        )
        normalized_equalities = tuple(sorted((equalities or {}).items()))
        return cls(allowed_values=normalized_allowed, equalities=normalized_equalities)
