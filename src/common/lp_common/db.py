"""저장소 접근. ⑦ 5-2절 — DB1 ~ DB6은 **전부 런타임 밖**이며 영속임.

⑤ 3절 `쓰기 금지 규칙`을 계정으로 강제함: 조회 경로는 `ro` 풀만 쓰고,
쓰기 경로는 `rw` 풀을 쓰며, 관측 기록은 쓰기 전용 `obs` 풀을 씀.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg

from .config import DbAccount, Settings

log = logging.getLogger("lp.db")

_pools: dict[str, asyncpg.Pool] = {}


async def _create_pool(account: DbAccount, *, min_size: int, max_size: int) -> asyncpg.Pool:
    last_error: Exception | None = None
    for attempt in range(30):
        try:
            return await asyncpg.create_pool(
                dsn=account.dsn(),
                min_size=min_size,
                max_size=max_size,
                command_timeout=5.0,
            )
        except Exception as exc:  # 컨테이너 기동 순서 때문에 초기 재시도가 필요함
            last_error = exc
            await asyncio.sleep(1.0)
    raise RuntimeError(f"저장소 연결 실패(30회 시도): {type(last_error).__name__}")


async def init_pools(settings: Settings, *, roles: tuple[str, ...]) -> None:
    """이미지가 실제로 쓰는 역할만 풀을 엶. 안 쓰는 계정은 아예 열지 않음."""
    # `US:NFR-SYS-020` DB 커넥션 풀 최대 100 — 역할별로 나눠 배정함
    sizing = {"ro": (2, 60), "rw": (2, 30), "obs": (1, 10)}
    for role in roles:
        if role in _pools:
            continue
        account = {"ro": settings.ro, "rw": settings.rw, "obs": settings.obs}[role]()
        min_size, max_size = sizing[role]
        _pools[role] = await _create_pool(account, min_size=min_size, max_size=max_size)
        log.info("저장소 풀 준비됨 role=%s user=%s", role, account.user)


async def close_pools() -> None:
    for role, pool in list(_pools.items()):
        await pool.close()
        _pools.pop(role, None)


def pool(role: str) -> asyncpg.Pool:
    if role not in _pools:
        raise RuntimeError(f"열지 않은 저장소 역할임: {role}")
    return _pools[role]


async def fetch(role: str, sql: str, *args: Any, limit_guard: int = 500) -> list[asyncpg.Record]:
    """⑤ 3절 `행 수 상한` — 1회 응답 행 수에 반드시 상한을 걺.

    `[확인필요: 이력 조회 1회 응답 행 수 상한]`이 닫히지 않아 기본 500으로 둠.
    """
    rows = await pool(role).fetch(sql, *args)
    if len(rows) > limit_guard:
        log.warning("행 수 상한 초과로 잘라 냄 rows=%d guard=%d", len(rows), limit_guard)
        return rows[:limit_guard]
    return rows


async def fetchrow(role: str, sql: str, *args: Any) -> asyncpg.Record | None:
    return await pool(role).fetchrow(sql, *args)


async def execute(role: str, sql: str, *args: Any) -> str:
    if role == "ro":
        raise PermissionError("⑤ 3절 쓰기 금지 규칙 — 읽기 전용 계정으로 쓰기 시도임")
    return await pool(role).execute(sql, *args)
