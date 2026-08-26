from __future__ import annotations

import argparse
import os
from urllib.request import urlopen


PORT_NAMES = {
    "p1": "HELP_DESK_HTTP_PORT",
    "p2": "HELP_DESK_P2_INTERNAL_PORT",
    "p3": "HELP_DESK_P3_INTERNAL_PORT",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=PORT_NAMES)
    parser.add_argument("path", choices=("/health/live", "/health/ready"))
    args = parser.parse_args()
    port = int(os.environ[PORT_NAMES[args.service]])
    with urlopen(f"http://127.0.0.1:{port}{args.path}", timeout=2) as response:
        if response.status != 200:
            raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
