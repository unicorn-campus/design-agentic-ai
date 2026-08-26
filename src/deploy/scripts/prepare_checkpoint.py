from __future__ import annotations

import asyncio
import fcntl
import os
from pathlib import Path

from help_desk_runtime.checkpoint import create_checkpointer


async def prepare() -> bool:
    uri = os.environ.get("HELP_DESK_CHECKPOINT_URI")
    if not uri:
        raise SystemExit("필수 비밀값 누락: HELP_DESK_CHECKPOINT_URI")
    marker_dir = Path("/var/lib/help-desk")
    marker_dir.mkdir(parents=True, exist_ok=True)
    lock_path = marker_dir / ".checkpoint-schema.lock"
    marker_path = marker_dir / ".checkpoint-schema-v1"
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if marker_path.exists():
            return False
        async with create_checkpointer("sqlite", uri) as saver:
            await saver.setup()
        marker_path.touch(mode=0o600)
        return True


def main() -> int:
    changed = asyncio.run(prepare())
    print("checkpoint-schema=prepared" if changed else "checkpoint-schema=already-prepared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
