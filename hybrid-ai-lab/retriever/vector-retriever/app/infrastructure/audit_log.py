"""감사 레코드를 JSON Lines 파일에 한 줄씩 덧붙이는 AuditLogPort 구현임."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Mapping

from app.application.ports import AuditLogPort

logger = logging.getLogger(__name__)

# 로그에 남기지 않는 키. 질문 원문은 서비스가 이미 해시·앞 20자로 바꿔 주지만 이중으로 막음(설계 ③ 로그 규칙)
FORBIDDEN_KEYS = frozenset({"query"})


class JsonlAuditLog(AuditLogPort):
    """감사 레코드 1건 = 파일 1줄(JSON)로 남기는 어댑터.

    여러 요청이 같은 파일에 동시에 쓰므로 잠금으로 줄이 섞이지 않게 함.
    기록 실패는 삼켜 검색 응답을 막지 않음(포트 계약).
    """

    def __init__(self, path: str | Path) -> None:
        """로그 파일 경로를 받음. 폴더는 처음 기록할 때 만듦."""

        self._path = Path(path)
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        """기록 중인 로그 파일 경로를 반환함(상태 확인·시험용)."""

        return self._path

    def write(self, record: Mapping[str, Any]) -> None:
        """감사 레코드 1건을 파일 끝에 한 줄로 덧붙임.

        방법: 금지 키를 지우고 JSON 1줄로 만든 뒤 잠금 안에서 덧붙임.
        인자: record 값에 JSON으로 바꿀 수 없는 객체가 있으면 문자열로 바꿔 담음.
        반환값: 없음.
        예외: 없음. 파일·직렬화 실패는 삼키고 디버그 로그만 남김(감사 로그 실패로 응답을 실패시키지 않음).
        부수효과: 파일에 한 줄을 덧붙이고 필요하면 상위 폴더를 만듦.
        """

        try:
            payload: dict[str, Any] = {
                key: value for key, value in record.items() if key not in FORBIDDEN_KEYS
            }
            line = json.dumps(payload, ensure_ascii=False, default=str)
            with self._lock:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as stream:
                    stream.write(line + "\n")
        except Exception:  # noqa: BLE001 - 포트 계약상 어떤 기록 실패도 응답을 막지 않음
            logger.debug("감사 로그 기록에 실패함", exc_info=True)
