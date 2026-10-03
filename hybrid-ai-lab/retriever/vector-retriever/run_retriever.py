"""문서 검색 리트리버 CLI 실행 진입점임."""

from __future__ import annotations

import sys

from app.presentation.cli import main

if __name__ == "__main__":
    # Windows 콘솔 기본 코드페이지(cp949)에서 한글·기호가 깨지므로 출력 스트림을 UTF-8로 바꿈
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
