"""문서 검색 리트리버 API 서버 실행 진입점임."""

from __future__ import annotations

import argparse
import sys

import uvicorn

# 실행 스크립트는 계층 밖이라 설정 로더를 직접 부름(주소·포트 기본값 출처를 설정 한 곳으로 모음)
from app.infrastructure.settings import load_settings


def main(argv: list[str] | None = None) -> int:
    """API 서버를 띄움. 주소·포트 기본값은 설정에서 읽고 인자로 덮어쓸 수 있음.

    반환값: uvicorn이 끝난 뒤의 종료 코드(정상 0)임.
    부수효과: 포트를 열고 요청을 받기 시작함. 색인·모델 적재는 앱 시작(lifespan) 때 1회 일어남.
    """

    settings = load_settings()
    parser = argparse.ArgumentParser(description="문서 검색(Agentic RAG) 리트리버 API 서버")
    parser.add_argument("--host", default=settings.api_host, help="듣는 주소(기본값은 설정 API_HOST)")
    parser.add_argument("--port", type=int, default=settings.api_port, help="포트(기본값은 설정 API_PORT)")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("포트는 1 ~ 65535 범위여야 합니다.")
    # 문자열 경로로 넘겨 uvicorn이 앱을 import하게 함(모듈 import 시점이 아니라 서버 시작 때 조립됨)
    uvicorn.run("app.presentation.api:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
