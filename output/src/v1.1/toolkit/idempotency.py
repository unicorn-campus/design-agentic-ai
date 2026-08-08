"""중복 방지 키. 조립 함수를 **1개만** 두고 여기저기서 만들지 않음.

용어 1줄 — **중복 방지 키(멱등성 키)** = 같은 요청이 두 번 와도 한 번만 처리되게 하는 표식임.
같은 키가 다시 오면 바깥을 부르지 않고 먼저 낸 결과를 그대로 돌려줌.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from common.checkpointer import build_idempotency_key

from .errors import ConnectorNotConfigured

__all__ = [
    "connector_idempotency_key",
    "key_fingerprint",
    "ResultStore",
    "InMemoryResultStore",
    "StoredResult",
    "build_result_store",
    "TTL_UNSET",
]

TTL_UNSET = None


def connector_idempotency_key(connector_id: str, *parts: str) -> str:
    """커넥터 호출용 중복 방지 키를 만드는 **단 하나의 자리**.

    `common.checkpointer.build_idempotency_key`를 그대로 씀 — 조립 규칙을 두 벌 만들지 않음.
    """
    return build_idempotency_key(connector_id, *parts)


def key_fingerprint(key: str) -> str:
    """기록에는 키 원문을 남기지 않고 해시만 남김(⑤ `F-17` 분류)."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class StoredResult:
    output: Mapping[str, Any]
    stored_at_ms: int
    unresolved: bool = False


@runtime_checkable
class ResultStore(Protocol):
    """중복 방지 키 → 먼저 낸 결과. 저장소·보관 기간은 설정에서 옴."""

    async def get(self, key: str) -> StoredResult | None: ...

    async def put(self, key: str, result: StoredResult) -> None: ...


@dataclass(slots=True)
class InMemoryResultStore(ResultStore):
    """프로세스 안에서만 사는 구현. 보관 기간이 설정에 있으면 지난 항목을 내보내지 않음."""

    ttl_hours: int | None = None
    _rows: dict[str, StoredResult] = field(default_factory=dict)

    def _now(self) -> int:
        return int(time.time() * 1000)

    async def get(self, key: str) -> StoredResult | None:
        row = self._rows.get(key)
        if row is None:
            return None
        if self.ttl_hours is not None:
            age_ms = self._now() - row.stored_at_ms
            if age_ms > self.ttl_hours * 3600 * 1000:
                del self._rows[key]
                return None
        return row

    async def put(self, key: str, result: StoredResult) -> None:
        self._rows[key] = result

    def __len__(self) -> int:
        return len(self._rows)


def build_result_store(ttl_hours: int | None, backend: str = "memory") -> ResultStore:
    """저장소를 고름.

    `D-08`이 정한 데이터베이스 구현은 **이번 판에 없음** —
    `[확인필요: 중복 방지 키 저장소의 데이터베이스 구현]`. 메모리 구현만 있고
    프로세스가 다시 뜨면 먼저 낸 결과가 사라짐(반쪽짜리임을 숨기지 않음).
    """
    if backend == "memory":
        return InMemoryResultStore(ttl_hours=ttl_hours)
    raise ConnectorNotConfigured(
        f"중복 방지 키 저장소 백엔드 {backend!r}는 이번 판에 구현이 없음"
        " — [확인필요: 중복 방지 키 저장소의 데이터베이스 구현]"
    )
