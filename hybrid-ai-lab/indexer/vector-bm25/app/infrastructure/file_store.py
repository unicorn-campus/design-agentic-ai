"""UTF-8 JSON/JSONL 원자적 파일 저장 어댑터."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable


class FileStore:
    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8-sig")

    def load_jsonl(self, path: Path) -> list[dict]:
        return [json.loads(line) for line in self.read_text(path).splitlines() if line.strip()]

    def save_jsonl(self, path: Path, rows: Iterable[dict]) -> None:
        payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        self._replace(path, payload)

    def save_json(self, path: Path, value: Any) -> None:
        self._replace(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def ensure_output_outside_input(input_path: Path, output_path: Path) -> None:
        source, target = input_path.resolve(), output_path.resolve()
        if target == source or target.is_relative_to(source):
            raise ValueError("출력 폴더는 원문 폴더 밖이어야 함")

    @staticmethod
    def _replace(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ValueError("심볼릭 링크 출력은 허용하지 않음")
        descriptor, temporary = tempfile.mkstemp(prefix=".vector-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
