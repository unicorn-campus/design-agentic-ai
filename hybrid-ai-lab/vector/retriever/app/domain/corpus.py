"""검색 인덱스 세대에서 읽은 불변 corpus 스냅샷."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CorpusSnapshot:
    generation: str
    corpus_sha256: str
    records: tuple[dict[str, Any], ...]
    bm25_path: Path
    manifest: dict[str, Any]
    card_dictionary_words: tuple[tuple[str, str, float], ...] = ()
    card_dictionary_sha256: str | None = None
