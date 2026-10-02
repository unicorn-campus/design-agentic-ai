"""config 폴더의 JSON 파일에서 문서 프로필·메타데이터 규칙을 읽는 어댑터."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.application.ports import IndexConfigPort


class JsonIndexConfig(IndexConfigPort):
    """IndexConfigPort 구현: 호출할 때마다 파일을 새로 읽음."""

    def __init__(self, config_dir: str | Path) -> None:
        self._config_dir = Path(config_dir)  # document_profiles.json·metadata_schema.json이 있는 폴더

    def load_profiles(self) -> dict[str, Any]:
        return json.loads((self._config_dir / "document_profiles.json").read_text(encoding="utf-8"))

    def load_schema(self) -> dict[str, Any]:
        return json.loads((self._config_dir / "metadata_schema.json").read_text(encoding="utf-8"))
