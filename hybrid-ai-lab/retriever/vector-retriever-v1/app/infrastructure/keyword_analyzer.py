"""활성 BM25 세대의 질의 토크나이저와 corpus 통계로 핵심어 분석을 제공하는 어댑터."""

from __future__ import annotations

from threading import Lock
from typing import Iterable

from ..application.ports import CorpusPort, KeywordAnalyzerPort
from ..domain.keywords import TermObservation
from .bm25_index import BM25Index


class BM25KeywordAnalyzer(KeywordAnalyzerPort):
    """BM25 색인이 쓰는 질의 토크나이저와 같은 토큰으로 질문·결과를 분석함.

    BM25 색인과 corpus 포트를 주입받으며, 자체 Kiwi 인스턴스나 사전을 따로 만들지 않음.
    문서빈도 표는 활성 세대가 바뀔 때만 다시 계산해 질의마다 전체 corpus를 다시 자르지 않음.
    """

    def __init__(self, index: BM25Index, corpus: CorpusPort) -> None:
        """BM25 색인과 활성 세대를 읽을 corpus 포트를 주입받음.

        부수효과: 없음. 색인 로딩은 첫 분석 호출 시 수행함.
        """

        self.index = index
        self.corpus = corpus
        self._generation: str | None = None
        self._document_frequency: dict[str, int] = {}
        self._total_documents = 0
        self._lock = Lock()

    def observe(self, text: str) -> tuple[TermObservation, ...]:
        """질문을 색인과 같은 토큰으로 자르고 품사·고유이름 여부를 붙여 반환함."""

        if not str(text).strip():
            return ()
        self.index.warm()
        return self.index.tokenizer.observe(str(text))

    def index_tokens(self, text: str) -> frozenset[str]:
        """검색 결과 본문을 같은 분석기로 잘라 중복 없는 토큰 집합으로 반환함."""

        if not str(text).strip():
            return frozenset()
        self.index.warm()
        return frozenset(self.index.tokenizer.tokenize(str(text)))

    def corpus_statistics(self, tokens: Iterable[str]) -> tuple[int, dict[str, int]]:
        """색인 전체 청크 수와 요청한 토큰별 문서빈도를 반환함."""

        requested = {str(token) for token in tokens}
        self._refresh()
        with self._lock:
            total = self._total_documents
            table = {token: self._document_frequency.get(token, 0) for token in requested}
        return total, table

    def _refresh(self) -> None:
        """활성 세대가 바뀌었을 때만 전체 corpus를 다시 잘라 문서빈도 표를 만듦."""

        generation = self.corpus.active_generation()
        with self._lock:
            if generation is not None and generation == self._generation:
                return
        self.index.warm()
        snapshot = self.corpus.load_active()
        if snapshot is None:
            with self._lock:
                self._generation, self._document_frequency, self._total_documents = None, {}, 0
            return
        tokenizer = self.index.tokenizer
        table: dict[str, int] = {}
        # BM25 색인이 머리말을 포함한 색인용 텍스트로 만들어지므로 문서빈도도 같은 텍스트로 세야 맞음.
        # index_text가 없는 이전 세대 레코드는 text가 곧 색인용 텍스트임.
        for tokens in tokenizer.tokenize_many(
            str(row.get("index_text") or row["text"]) for row in snapshot.records
        ):
            for token in set(tokens):
                table[token] = table.get(token, 0) + 1
        with self._lock:
            self._generation = snapshot.generation
            self._document_frequency = table
            self._total_documents = len(snapshot.records)


__all__ = ["BM25KeywordAnalyzer"]
