from __future__ import annotations

from dataclasses import dataclass

from .policy import GuardrailPolicy


@dataclass(frozen=True)
class KillSwitchResult:
    blocked: bool
    action: str
    escalated: bool
    notify: str | None


class KillSwitch:
    def __init__(self, policy: GuardrailPolicy) -> None:
        self._rules = {row.id: row for row in policy.kill_switches}
        self._counts: dict[tuple[str, str], int] = {}

    def trip(self, rule_id: str, scope_id: str, violated: bool) -> KillSwitchResult:
        if not violated:
            return KillSwitchResult(False, "통과", False, None)
        rule = self._rules[rule_id]
        key = (rule_id, scope_id)
        self._counts[key] = self._counts.get(key, 0) + 1
        threshold = rule.model_extra.get("violation_limit")
        escalated = threshold is not None and self._counts[key] >= threshold
        action = rule.model_extra["escalation"] if escalated else rule.model_extra["action"]
        return KillSwitchResult(True, action, escalated, rule.model_extra["notify"])
