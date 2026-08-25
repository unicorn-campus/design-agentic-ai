from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class CostLimitExceeded(RuntimeError):
    def __init__(self, action: str, notify: str) -> None:
        super().__init__(action)
        self.action = action
        self.notify = notify


@dataclass
class CostCounter:
    amount_limit: Decimal
    token_limit: int | None
    action: str
    notify: str
    amount: Decimal = Decimal("0")
    tokens: int = 0

    def add(self, amount: Decimal, tokens: int, worst_multiplier: Decimal = Decimal("1")) -> None:
        self.amount += amount * worst_multiplier
        self.tokens += tokens * int(worst_multiplier)
        amount_exceeded = self.amount >= self.amount_limit
        token_exceeded = self.token_limit is not None and self.tokens >= self.token_limit
        if amount_exceeded or token_exceeded:
            raise CostLimitExceeded(self.action, self.notify)
