from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

BatchRunner = Callable[[str, date, str], Awaitable[dict[str, Any]]]


async def run_scheduled_batch(
    runner: BatchRunner,
    batch_id: str,
    batch_date: date,
    data_version: str,
) -> dict[str, Any]:
    return await runner(batch_id, batch_date, data_version)
