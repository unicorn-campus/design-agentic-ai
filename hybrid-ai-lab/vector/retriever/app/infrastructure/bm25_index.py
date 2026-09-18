"""버전형 corpus와 BM25S 파일을 읽는 한국어 키워드 검색 어댑터."""

from __future__ import annotations

import logging
from threading import Lock, RLock
from typing import Any

from ..application.ports import CorpusPort
from ..application.state import Hit
from ..domain.korean_tokenizer import KoreanTokenizer
from ..domain.location import resolve_location


LOGGER = logging.getLogger(__name__)
_TYPO_RRF_K = 60


class BM25Index:
    """활성 세대가 바뀔 때 새 인덱스를 완성한 후 참조를 교체함."""

    def __init__(self, corpus_store: CorpusPort, tokenizer: KoreanTokenizer) -> None:
        self.corpus_store = corpus_store
        self._base_tokenizer = tokenizer
        self.tokenizer = tokenizer
        self._retriever: Any = None
        self._chunks: dict[str, Hit] = {}
        self._records: tuple[dict[str, Any], ...] = ()
        self._generation: str | None = None
        self._lock = RLock()
        self._warm_lock = Lock()

    def warm(self, *, force: bool = False) -> None:
        acquired = self._warm_lock.acquire(blocking=force)
        if not acquired:
            # 다른 요청이 새 버전을 준비 중이면 현재 활성 묶음으로 바로 검색함.
            return
        try:
            self._warm_active_generation(force=force)
        finally:
            self._warm_lock.release()

    def _warm_active_generation(self, *, force: bool) -> None:
        generation = self.corpus_store.active_generation()
        with self._lock:
            if not force and generation is not None and generation == self._generation:
                return
        snapshot = self.corpus_store.load_active()
        if snapshot is None:
            with self._lock:
                self.tokenizer = self._base_tokenizer
                self._retriever = None
                self._chunks = {}
                self._records = ()
                self._generation = None
            return
        manifest = snapshot.manifest
        if manifest.get("corpus_sha256") != snapshot.corpus_sha256:
            raise ValueError("corpus manifest와 실제 파일의 SHA-256이 일치하지 않음")

        tokenizer = self._base_tokenizer.with_additional_user_words(
            snapshot.card_dictionary_words
        )
        if (
            snapshot.card_dictionary_sha256 is not None
            and tokenizer.additional_user_words_sha256
            != snapshot.card_dictionary_sha256
        ):
            raise ValueError("카드명 사전 파일과 질의 토크나이저의 SHA-256이 일치하지 않음")
        if manifest.get("tokenizer_signature") != tokenizer.signature:
            raise ValueError("BM25 색인과 질의 토크나이저 서명이 일치하지 않음")

        try:
            import bm25s
        except ImportError as error:  # pragma: no cover - 설치 오류 안내 경로
            raise RuntimeError("BM25 검색을 사용하려면 bm25s가 필요함") from error

        retriever = bm25s.BM25.load(
            snapshot.bm25_path,
            load_corpus=False,
            mmap=False,
            show_progress=False,
        )
        if int(retriever.scores.get("num_docs", -1)) != len(snapshot.records):
            raise ValueError("BM25S 위치 색인과 외부 corpus의 문서 수가 일치하지 않음")
        chunks: dict[str, Hit] = {}
        for row in snapshot.records:
            chunk_id = str(row["chunk_id"])
            text = str(row["text"])
            metadata = {**dict(row.get("metadata") or {}), "chunk_id": chunk_id}
            chunks[chunk_id] = Hit(
                chunk_id=chunk_id,
                score=0.0,
                vector_score=None,
                access_level=str(metadata.get("access_level", "")),
                source=str(metadata.get("source", "")),
                location=str(resolve_location(metadata)),
                text=text,
                metadata=metadata,
            )
        if len(chunks) != len(snapshot.records):
            raise ValueError("corpus에 중복 chunk_id가 있음")

        # 검증이 끝난 같은 버전의 검색 구성요소를 잠금 안에서 한 번에 교체함.
        with self._lock:
            self.tokenizer = tokenizer
            self._retriever = retriever
            self._chunks = chunks
            self._records = snapshot.records
            self._generation = snapshot.generation

    def scores(
        self,
        query: str,
        *,
        allowed_access_levels: frozenset[str] | None = None,
        k: int,
    ) -> dict[str, float]:
        if k <= 0:
            return {}
        self.warm()
        with self._lock:
            retriever = self._retriever
            records = self._records
            tokenizer = self.tokenizer
        if retriever is None or not records:
            return {}

        import numpy as np

        mask = np.ones(len(records), dtype=np.float32)
        if allowed_access_levels is not None:
            mask = np.asarray(
                [
                    1.0
                    if str((row.get("metadata") or {}).get("access_level", ""))
                    in allowed_access_levels
                    else 0.0
                    for row in records
                ],
                dtype=np.float32,
            )
        allowed_count = int(np.count_nonzero(mask))
        if allowed_count == 0:
            return {}
        terms = tokenizer.tokenize(query)
        primary = self._retrieve(
            retriever,
            records,
            terms,
            mask,
            min(k, allowed_count, len(records)),
        )
        if primary:
            return primary

        # 상품 코드의 과교정을 피하기 위해 원 질의의 양수 결과가 없을 때만
        # Kiwi basic 오타 교정을 질의 측에 한 번 적용함.
        tokenization = tokenizer.tokenize_with_typo_fallback(query)
        if not tokenization.changed or not tokenization.corrected:
            return {}
        corrected = self._retrieve(
            retriever,
            records,
            list(tokenization.corrected),
            mask,
            min(k, allowed_count, len(records)),
        )
        if not corrected:
            return {}
        LOGGER.info("BM25 질의 전용 오타 교정 폴백 사용")
        return self._rrf_merge(primary, corrected, k=k)

    @staticmethod
    def _retrieve(
        retriever: Any,
        records: tuple[dict[str, Any], ...],
        terms: list[str],
        mask: Any,
        k: int,
    ) -> dict[str, float]:
        if not terms or k <= 0:
            return {}
        result = retriever.retrieve(
            [terms],
            k=k,
            weight_mask=mask,
            show_progress=False,
        )
        positions = result.documents[0].tolist()
        values = result.scores[0].tolist()
        return {
            str(records[int(position)]["chunk_id"]): float(score)
            for position, score in zip(positions, values)
            if mask[int(position)] > 0 and float(score) > 0.0
        }

    @staticmethod
    def _rrf_merge(*rankings: dict[str, float], k: int) -> dict[str, float]:
        merged: dict[str, float] = {}
        for scores in rankings:
            ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            for rank, (chunk_id, _score) in enumerate(ranked, start=1):
                merged[chunk_id] = merged.get(chunk_id, 0.0) + 1.0 / (_TYPO_RRF_K + rank)
        return dict(
            sorted(
                merged.items(),
                key=lambda item: (-item[1], item[0]),
            )[:k]
        )

    def chunks(self) -> dict[str, Hit]:
        self.warm()
        with self._lock:
            return dict(self._chunks)

    def is_ready(self) -> bool:
        self.warm()
        with self._lock:
            return self._retriever is not None and bool(self._chunks)
