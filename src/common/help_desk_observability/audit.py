from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from help_desk_guardrails.masking import SensitiveDataMasker


@dataclass(frozen=True)
class AuditEntry:
    occurred_at: datetime
    actor: str
    tool: str
    approval_id: str
    result: str
    idempotency_key: str
    before: Any = None
    after: Any = None


class AuditRecorder:
    def __init__(self, masker: SensitiveDataMasker, retention_by_workflow: dict[str, str]) -> None:
        self._masker = masker
        self.retention_by_workflow = retention_by_workflow
        self._records: list[dict[str, Any]] = []

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._records)

    def append(self, entry: AuditEntry) -> None:
        self._records.append(self._masker.sanitize(asdict(entry), "audit"))
