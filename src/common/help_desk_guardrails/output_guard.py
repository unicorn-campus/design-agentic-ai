from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from .policy import GuardrailPolicy


@dataclass(frozen=True)
class OutputDecision:
    allowed: bool
    value: Any
    hits: tuple[str, ...]


class OutputGuard:
    def __init__(self, policy: GuardrailPolicy) -> None:
        self._rules = {row.id: row for row in policy.output_rules}

    def inspect(self, rule_id: str, value: Any) -> OutputDecision:
        rule = self._rules[rule_id]
        kind = rule.model_extra["kind"]
        action = rule.model_extra["action"]
        result = copy.deepcopy(value)
        hit = False
        if kind == "pattern":
            pattern = re.compile(rule.model_extra["pattern"])
            if isinstance(result, str):
                hit = bool(pattern.search(result))
                if hit and action == "가림":
                    result = pattern.sub("[가림]", result)
        elif kind == "field":
            hit = _path_exists(result, rule.model_extra["path"])
        elif kind == "label":
            current = _path_value(result, rule.model_extra["path"])
            hit = current not in rule.model_extra["allowed"]
        else:
            raise ValueError(f"지원하지 않는 출력 검사 방식: {kind}")
        return OutputDecision(
            allowed=not (hit and action == "중단"),
            value=result,
            hits=(rule_id,) if hit else (),
        )


def _path_value(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _path_exists(value: Any, path: str) -> bool:
    return _path_value(value, path) is not None
