"""표현 계층과 응용 계층 사이의 요청·응답 계약."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LabRequest:
    member_id: str
    base_date: str
    question: str
    offline: bool = False


@dataclass(frozen=True)
class LabResult:
    payload: Any
    notices: tuple[str, ...] = field(default_factory=tuple)
    exit_code: int = 0

