from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from time import monotonic
from typing import Protocol


@dataclass(frozen=True)
class Alert:
    axis: str
    target: str
    severity: str
    recipient: str
    value: float


class AlertSender(Protocol):
    def send(self, alert: Alert) -> None: ...


class StdoutAlertSender:
    def send(self, alert: Alert) -> None:
        print(json.dumps(asdict(alert), ensure_ascii=False, sort_keys=True))


class AlertMonitor:
    def __init__(self, sender: AlertSender) -> None:
        self._sender = sender
        self._last_sent: dict[tuple[str, str], float] = {}

    def observe(
        self,
        alert: Alert,
        threshold: float,
        suppression_seconds: float | None,
        now: float | None = None,
    ) -> bool:
        if alert.value < threshold:
            return False
        now = monotonic() if now is None else now
        key = (alert.axis, alert.target)
        last = self._last_sent.get(key)
        if suppression_seconds is not None and last is not None and now - last < suppression_seconds:
            return False
        self._sender.send(alert)
        self._last_sent[key] = now
        return True
