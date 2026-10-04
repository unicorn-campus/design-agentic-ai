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
    # 별칭은 (별칭 표면형, 정식 카드 토큰) 쌍이며, 별칭 산출물이 없는 이전 세대에서는 비어 있음.
    card_aliases: tuple[tuple[str, str], ...] = ()
    card_aliases_sha256: str | None = None

    def alias_mapping(self) -> dict[str, str]:
        """질의 토크나이저에 넘길 별칭 치환표를 반환함."""

        return dict(self.card_aliases)
