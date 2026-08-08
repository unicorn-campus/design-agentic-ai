"""비용 카운터 자리. 실제로 세고 막는 코드는 `05-guardrail.md` 몫임."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .config import Settings

__all__ = ["CostCounter", "NoOpCostCounter", "CostLimitUnset", "request_limit_krw"]


class CostLimitUnset(RuntimeError):
    """건당 비용 상한이 설정에 없음."""


@runtime_checkable
class CostCounter(Protocol):
    def add_model_call(self, request_id: str, krw: float) -> None: ...

    def spent_krw(self, request_id: str) -> float: ...

    def over_limit(self, request_id: str) -> bool: ...


@dataclass(slots=True)
class NoOpCostCounter(CostCounter):
    """자리만 잡아 두는 것. 아무것도 세지 않고 아무것도 막지 않음."""

    limit_krw: float | None = None
    _spent: dict[str, float] = field(default_factory=dict)

    def add_model_call(self, request_id: str, krw: float) -> None:
        self._spent[request_id] = self._spent.get(request_id, 0.0) + krw

    def spent_krw(self, request_id: str) -> float:
        return self._spent.get(request_id, 0.0)

    def over_limit(self, request_id: str) -> bool:
        if self.limit_krw is None:
            return False
        return self.spent_krw(request_id) > self.limit_krw


def request_limit_krw(settings: Settings) -> float:
    limit = settings.cost_limit_krw_per_request
    if limit is None:
        raise CostLimitUnset("요청 1건당 비용 상한이 설정에 없음")
    return limit
