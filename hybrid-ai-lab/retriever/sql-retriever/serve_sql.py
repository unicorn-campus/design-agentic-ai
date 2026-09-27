"""로컬 FastAPI 서버 진입점."""

from __future__ import annotations

import argparse
import os

import uvicorn
from dotenv import dotenv_values

from app.infrastructure.settings import LAB_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SQL Retriever API 서버")
    values = dotenv_values(LAB_ROOT / ".env", interpolate=False)
    default_port = os.getenv("SQL_RETRIEVER_PORT") or values.get("SQL_RETRIEVER_PORT") or "8012"
    parser.add_argument("--port", type=int, default=default_port)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("포트는 1~65535 범위여야 합니다.")
    uvicorn.run("app.presentation.api:app", host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
