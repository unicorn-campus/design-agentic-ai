"""검사에 걸렸을 때 던지는 것과, 실패 사유 이름.

**오류 분류 이름의 주인은 `04-connector.md`임.** 여기서 새 이름을 짓지 않고 그 4종을 그대로 적음.
`04-connector.md`가 어댑터를 만들 때는 **이 열거형을 가져다 써야 함** — 같은 이름을 두 곳에
정의하면 어느 쪽이 진짜인지 모르게 됨.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "ToolErrorClass",
    "GuardrailBlocked",
    "BlockDecision",
    "RETRYABLE_CLASSES",
]


class ToolErrorClass(StrEnum):
    """실패 사유 4종. 이름의 주인은 `04-connector.md` 10단계 오류 분류표임."""

    AUTH = "인증 오류"
    INPUT = "입력 오류"
    TRANSIENT = "일시 장애"
    PERMISSION = "권한 부족"


RETRYABLE_CLASSES = frozenset({ToolErrorClass.TRANSIENT})
"""재시도를 붙여도 되는 분류. 입력 오류·권한 부족은 재시도 0회이며 인증 오류는 갱신 후 1회임."""


@dataclass(frozen=True, slots=True)
class BlockDecision:
    """거름망 판정 1건. 어느 규칙에 걸렸고 무엇을 하기로 했나."""

    rule_id: str
    """⑥ 차단 규칙 식별자(`B-n`)."""
    action: str
    """⑥ 「행동」 칸을 옮긴 이름."""
    point: str
    """`input` · `tool` · `output` · `cost` · `all`."""
    signal: str
    notify: tuple[str, ...] = ()
    step_id: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    """가려진 값만 담음. 원문을 넣지 않음."""

    @property
    def user_reason_code(self) -> str:
        """사용자에게 보이는 값. **사유 구분 값만** 보이고 원문은 안 보임(3단계 되묻기 기본값)."""
        return f"{self.rule_id}:{self.action}"


class GuardrailBlocked(Exception):
    """검사에 걸려 더 못 가는 상태. 사용자에게는 `user_reason_code`만 보임."""

    def __init__(self, decision: BlockDecision) -> None:
        super().__init__(decision.user_reason_code)
        self.decision = decision

    @property
    def user_reason_code(self) -> str:
        return self.decision.user_reason_code
