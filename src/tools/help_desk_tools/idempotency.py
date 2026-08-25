from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Protocol


def build_idempotency_key(workflow_id: str, event_id: str, operation: str) -> str:
    canonical = json.dumps(
        [workflow_id, event_id, operation],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyStore(Protocol):
    def get(self, key: str) -> dict[str, Any] | None: ...

    def put(self, key: str, value: dict[str, Any]) -> None: ...


@dataclass
class _Entry:
    value: dict[str, Any]
    expires_at: datetime


class MemoryIdempotencyStore:
    def __init__(self, ttl: timedelta) -> None:
        self._ttl = ttl
        self._entries: dict[str, _Entry] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._entries.pop(key, None)
            return None
        return entry.value.copy()

    def put(self, key: str, value: dict[str, Any]) -> None:
        self._entries[key] = _Entry(value.copy(), datetime.now(UTC) + self._ttl)


class SqliteIdempotencyStore:
    def __init__(self, path: Path, ttl: timedelta) -> None:
        self._path = path
        self._ttl = ttl
        self._lock = Lock()
        self._prepare()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _prepare(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS connector_idempotency "
                "(key TEXT PRIMARY KEY, result_json TEXT NOT NULL, expires_at TEXT NOT NULL)"
            )

    def get(self, key: str) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT result_json, expires_at FROM connector_idempotency WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            if datetime.fromisoformat(row[1]) <= now:
                connection.execute("DELETE FROM connector_idempotency WHERE key = ?", (key,))
                return None
            return json.loads(row[0])

    def put(self, key: str, value: dict[str, Any]) -> None:
        expires_at = datetime.now(UTC) + self._ttl
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO connector_idempotency(key, result_json, expires_at) "
                "VALUES (?, ?, ?)",
                (key, payload, expires_at.isoformat()),
            )
