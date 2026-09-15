"""전체 청크에서 만드는 BM25 색인과 선택적 pickle 캐시."""

from __future__ import annotations

import math
from pathlib import Path
import pickle

from ..application.state import Hit


class BM25Index:
    def __init__(self, vector_store, cache_path: Path | None = None) -> None:
        self.vector_store = vector_store
        self.cache_path = cache_path
        self._chunks: dict[str, Hit] = {}
        self._tokens: dict[str, list[str]] = {}
        self._ready = False

    def warm(self, *, force: bool = False) -> None:
        if self._ready and not force:
            return
        records = self.vector_store.get_all()
        self._chunks, self._tokens = {}, {}
        for chunk_id, text, metadata in zip(records.get("ids", []), records.get("documents", []), records.get("metadatas", [])):
            metadata = {**dict(metadata or {}), "chunk_id": chunk_id}
            location = metadata.get("clause_no") or f"{metadata.get('record_id', '')} 턴 {metadata.get('turn_range', '')}".strip()
            self._chunks[chunk_id] = Hit(
                chunk_id=chunk_id,
                score=0.0,
                vector_score=None,
                access_level=str(metadata.get("access_level", "")),
                source=str(metadata.get("source", "")),
                location=str(location),
                text=text,
                metadata=metadata,
            )
            self._tokens[chunk_id] = text.split()
        self._ready = bool(self._chunks)
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("wb") as stream:
                pickle.dump({"tokens": self._tokens}, stream)

    def scores(self, query: str) -> dict[str, float]:
        if not self._ready:
            self.warm()
        if not self._chunks:
            return {}
        terms = query.split()
        document_count = len(self._tokens)
        average_length = sum(map(len, self._tokens.values())) / document_count
        document_frequency = {term: sum(term in tokens for tokens in self._tokens.values()) for term in set(terms)}
        output = {}
        for chunk_id, tokens in self._tokens.items():
            score = 0.0
            for term in terms:
                frequency = tokens.count(term)
                if not frequency:
                    continue
                inverse = math.log(1 + (document_count - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
                score += inverse * frequency * 2.5 / (frequency + 1.5 * (1 - 0.75 + 0.75 * len(tokens) / average_length))
            output[chunk_id] = score
        return output

    def chunks(self) -> dict[str, Hit]:
        if not self._ready:
            self.warm()
        return dict(self._chunks)

    def is_ready(self) -> bool:
        if not self._ready:
            self.warm()
        return self._ready
