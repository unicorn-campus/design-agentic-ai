"""Retriever HTTP 서버 진입점."""

import argparse

from app.settings import load_settings


def main(argv: list[str] | None = None) -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Retriever 로컬 HTTP API 서버")
    parser.add_argument("--host", default=settings.API_HOST)
    parser.add_argument("--port", type=int, default=settings.API_PORT)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run(
        "app.presentation.api:app",
        host=args.host,
        port=args.port,
        workers=1,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
