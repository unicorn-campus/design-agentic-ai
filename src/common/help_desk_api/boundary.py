from __future__ import annotations

from typing import Any

from help_desk_guardrails import (
    GuardrailPolicy,
    InputGuard,
    OutputGuard,
    SensitiveDataMasker,
)


class BoundaryRejected(RuntimeError):
    pass


class GuardrailBoundary:
    def __init__(
        self,
        policy: GuardrailPolicy,
        masker: SensitiveDataMasker,
    ) -> None:
        self._policy = policy
        self._input = InputGuard(policy)
        self._output = OutputGuard(policy)
        self._masker = masker

    def inspect_input(self, rule_id: str, value: Any, checkpoint: str) -> None:
        decision = self._input.inspect(rule_id, value, checkpoint)
        if not decision.accepted:
            raise BoundaryRejected("입력 안전 검사에서 차단됨")

    def sanitize_output(self, workflow_id: str, value: Any) -> Any:
        result = value
        for rule in self._policy.output_rules:
            if rule.workflow != workflow_id:
                continue
            path = rule.model_extra.get("path")
            if path and not _has_path(result, path):
                continue
            decision = self._output.inspect(rule.id, result)
            if not decision.allowed:
                raise BoundaryRejected("출력 안전 검사에서 차단됨")
            result = decision.value
        return self._masker.sanitize(result, "access")


def _has_path(value: Any, path: str) -> bool:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True
