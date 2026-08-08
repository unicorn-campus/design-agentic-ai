"""단위 환산만 두는 곳. 설계서가 소유한 값은 여기에 없음."""

from __future__ import annotations

from typing import Final

__all__ = ["MS_PER_SECOND", "ms_to_seconds"]

MS_PER_SECOND: Final[int] = 1000


def ms_to_seconds(milliseconds: int | float) -> float:
    return milliseconds / MS_PER_SECOND
