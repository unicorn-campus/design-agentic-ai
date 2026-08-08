"""검사·가리기·기록이 끼어들 자리(훅)만 남겨 둠. 실제 규칙은 `05-guardrail.md` 몫임."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "InputInspector",
    "OutputRedactor",
    "AuditRecorder",
    "HookSet",
    "PassThroughHooks",
]


@runtime_checkable
class InputInspector(Protocol):
    def inspect(self, step_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class OutputRedactor(Protocol):
    def redact(self, step_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class AuditRecorder(Protocol):
    def record(self, step_id: str, fields: dict[str, Any]) -> None: ...


@dataclass(frozen=True, slots=True)
class HookSet:
    inspector: InputInspector
    redactor: OutputRedactor
    recorder: AuditRecorder


class _PassThroughInspector(InputInspector):
    def inspect(self, step_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


class _PassThroughRedactor(OutputRedactor):
    def redact(self, step_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


class _SilentRecorder(AuditRecorder):
    def record(self, step_id: str, fields: dict[str, Any]) -> None:
        return None


def PassThroughHooks() -> HookSet:  # noqa: N802 - 만드는 함수라 이름을 타입처럼 씀
    return HookSet(
        inspector=_PassThroughInspector(),
        redactor=_PassThroughRedactor(),
        recorder=_SilentRecorder(),
    )
