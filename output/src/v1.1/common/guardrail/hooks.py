"""`01-runtime`이 비워 둔 훅 자리를 채움.

`common.guardrail_hooks.HookSet`의 이름을 **그대로** 씀 — `InputInspector.inspect` ·
`OutputRedactor.redact` · `AuditRecorder.record`. 새 이름을 짓지 않음.
`06-workflow.md`는 `PassThroughHooks()` 대신 `build_guardrail_hooks()`를 부르면 됨.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from ..guardrail_hooks import AuditRecorder, HookSet, InputInspector, OutputRedactor
from .input_guard import InputGuard
from .masking import MaskPath
from .output_guard import OutputGuard
from .rules import RuleBook, get_rulebook

if TYPE_CHECKING:  # 관측 계층이 검사 계층을 쓰므로 여기서는 이름만 빌려 옴(맴돌이 수입 막기)
    from ..observability.audit import AuditLog
    from ..observability.record import StepRecorder

__all__ = [
    "GuardrailInspector",
    "GuardrailRedactor",
    "GuardrailAuditRecorder",
    "build_guardrail_hooks",
]


@dataclass(slots=True)
class GuardrailInspector(InputInspector):
    """입력측 훅. 걸리면 `GuardrailBlocked`를 던져 흐름이 그대로 못 가게 함."""

    guard: InputGuard
    boundary: str | None = None
    raise_on_block: bool = True

    def inspect(self, step_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        verdict = self.guard.inspect(
            step_id,
            payload,
            boundary=self.boundary,
            raise_on_block=self.raise_on_block,
        )
        return verdict.kept


@dataclass(slots=True)
class GuardrailRedactor(OutputRedactor):
    """출력측 훅. 밖으로 나가는 모든 경로가 이걸 지남."""

    guard: OutputGuard
    labels: Mapping[str, Sequence[str]] | None = None
    truth: Mapping[str, Any] | None = None
    path: MaskPath = MaskPath.RESPONSE

    def redact(self, step_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.guard.redact(
            step_id,
            payload,
            labels=self.labels,
            truth=self.truth,
            path=self.path,
        ).payload


@dataclass(slots=True)
class GuardrailAuditRecorder(AuditRecorder):
    """기록 훅. 관측 기록과 감사 기록 둘 다 가리기를 지난 뒤 남김."""

    recorder: "StepRecorder"
    audit: "AuditLog | None" = None

    def record(self, step_id: str, fields: dict[str, Any]) -> None:
        self.recorder.record(step_id, fields)


def build_guardrail_hooks(
    *,
    recorder: "StepRecorder",
    audit: "AuditLog | None" = None,
    book: RuleBook | None = None,
    boundary: str | None = None,
    labels: Mapping[str, Sequence[str]] | None = None,
    truth: Mapping[str, Any] | None = None,
) -> HookSet:
    """검사·가리기·기록을 한 벌로 세워 `HookSet`으로 돌려줌."""
    rules = book or get_rulebook()
    return HookSet(
        inspector=GuardrailInspector(guard=InputGuard(rules), boundary=boundary),
        redactor=GuardrailRedactor(guard=OutputGuard(rules), labels=labels, truth=truth),
        recorder=GuardrailAuditRecorder(recorder=recorder, audit=audit),
    )
