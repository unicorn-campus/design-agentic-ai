from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


SERVICE_COMMANDS = {
    "p1": ("p1_sync_inquiry.api:app", "HELP_DESK_HTTP_PORT"),
    "p2": ("p2_knowledge_improvement_batch.api:app", "HELP_DESK_P2_INTERNAL_PORT"),
    "p3": ("p3_conversation_closed_event.api:app", "HELP_DESK_P3_INTERNAL_PORT"),
}


def inventory_path() -> Path:
    return Path(__file__).resolve().parents[1] / "secret_inventory.json"


def required_secret_names(service: str, path: Path | None = None) -> tuple[str, ...]:
    document = json.loads((path or inventory_path()).read_text(encoding="utf-8"))
    return tuple(
        item["key"]
        for item in document["items"]
        if item["required"] and service in item["services"]
    )


def missing_required_secrets(service: str, path: Path | None = None) -> tuple[str, ...]:
    return tuple(name for name in required_secret_names(service, path) if not os.environ.get(name))


def validate_port(name: str) -> int:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"필수 설정 누락: {name}")
    try:
        port = int(value)
    except ValueError as error:
        raise SystemExit(f"포트 설정이 정수가 아님: {name}") from error
    if not 1 <= port <= 65535:
        raise SystemExit(f"포트 설정 범위 오류: {name}")
    return port


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=SERVICE_COMMANDS)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    missing = missing_required_secrets(args.service)
    if missing:
        raise SystemExit(f"필수 비밀값 누락: {', '.join(missing)}")

    module, port_name = SERVICE_COMMANDS[args.service]
    port = validate_port(port_name)
    if args.check_only:
        print(f"startup-check=ok service={args.service}")
        return 0

    argv = [
        "python",
        "-m",
        "uvicorn",
        module,
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    os.execvp(argv[0], argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
