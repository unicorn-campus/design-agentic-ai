from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any


async def final_event_stream(
    value: Any,
    sanitize: Callable[[Any], Any],
    truncated: bool = False,
) -> AsyncIterator[str]:
    safe = sanitize(value)
    event = "truncated" if truncated else "final"
    payload = json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    yield f"event: {event}\ndata: {payload}\n\n"
