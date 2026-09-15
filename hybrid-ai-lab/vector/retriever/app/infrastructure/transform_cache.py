"""질문 변환 결정을 원자적으로 저장하는 JSON 캐시."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.application.state import RouteDecision


class TransformCacheError(RuntimeError):
    """캐시 파일을 안전하게 읽거나 쓸 수 없는 오류."""


class TransformCache:
    """주입된 파일 경로 하나에 질문별 RouteDecision을 저장함."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()

    @staticmethod
    def _query_key(query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("변환 캐시 질문이 비어 있음")
        return query.strip()

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        if not self.path.is_file():
            raise TransformCacheError("변환 캐시 경로가 파일이 아님")
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise TransformCacheError("변환 캐시 JSON을 읽을 수 없음") from error
        if not isinstance(value, dict):
            raise TransformCacheError("변환 캐시 최상위 값은 JSON 객체여야 함")
        return value

    def get(self, query: str) -> RouteDecision | None:
        """질문이 없으면 None, 손상된 결정이면 명시적 캐시 오류를 반환함."""

        key = self._query_key(query)
        with self._lock:
            value = self._read_unlocked().get(key)
        if value is None:
            return None
        try:
            return RouteDecision.model_validate(value)
        except ValidationError as error:
            raise TransformCacheError("변환 캐시 결정 스키마가 올바르지 않음") from error

    def put(self, query: str, decision: RouteDecision) -> None:
        """같은 디렉터리의 임시 파일을 fsync한 뒤 os.replace로 교체함."""

        key = self._query_key(query)
        validated = RouteDecision.model_validate(decision)
        with self._lock:
            cache = self._read_unlocked()
            cache[key] = validated.model_dump(mode="json")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
            )
            temporary_path = Path(temporary_name)
            try:
                os.chmod(temporary_path, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump(cache, handle, ensure_ascii=False, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, self.path)
            except Exception as error:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                temporary_path.unlink(missing_ok=True)
                raise TransformCacheError("변환 캐시를 원자적으로 저장할 수 없음") from error


__all__ = ["TransformCache", "TransformCacheError"]
