"""질문의 핵심어를 고르고 검색 결과에 들어 있는지 판정하는 순수 규칙."""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Mapping, Sequence


# 형태소 분석에서 남길 품사. 동사·형용사·어미는 질문마다 흔해 핵심어 구실을 못 하므로 버림.
# SURFACE는 숫자·코드·날짜 표준형처럼 형태소가 아니라 표면형으로 보존한 토큰을 가리킴.
NOUN_TAGS = frozenset({"NNG", "NNP", "NNB", "NR", "SL", "SH", "SN", "SURFACE"})
PROPER_TAGS = frozenset({"NNP", "SL", "SH", "SN", "SURFACE"})


@dataclass(frozen=True)
class TermObservation:
    """질문을 색인과 같은 분석기로 자른 토큰 하나임."""

    token: str  # BM25 색인에 들어 있는 것과 같은 모양의 토큰
    tag: str  # Kiwi 기본 품사. 표면형 보존 토큰은 SURFACE
    proper: bool  # 고유이름(카드명·별칭·숫자·코드·날짜 표준형)인지

    @property
    def noun(self) -> bool:
        """명사·숫자·코드 계열이라 핵심어 후보가 될 수 있는지 반환함."""

        return self.tag in NOUN_TAGS


@dataclass(frozen=True)
class Keyword:
    """핵심어로 고른 토큰과 그 희소성 근거임."""

    token: str
    document_frequency: int  # 전체 청크 중 이 토큰이 나오는 청크 수
    idf: float  # 드문 정도. 클수록 핵심어일 가능성이 높음
    proper: bool


@dataclass(frozen=True)
class KeywordCoverage:
    """핵심어 하나가 어느 검색 결과에 들어 있는지임."""

    keyword: Keyword
    present_in: tuple[str, ...]  # 이 핵심어를 담은 결과 chunk_id

    @property
    def covered(self) -> bool:
        """검색 결과 어느 하나라도 이 핵심어를 담고 있는지 반환함."""

        return bool(self.present_in)


@dataclass(frozen=True)
class KeywordReport:
    """질문의 핵심어와 결과 포함 여부를 한 번에 담은 판정 결과임."""

    keywords: tuple[Keyword, ...]
    coverage: tuple[KeywordCoverage, ...]
    dropped: tuple[TermObservation, ...]  # 핵심어에서 빠진 토큰(사유 추적용)

    @property
    def missing(self) -> tuple[str, ...]:
        """어느 결과에도 없는 핵심어를 IDF 높은 순서로 반환함."""

        return tuple(item.keyword.token for item in self.coverage if not item.covered)

    def top_missing(self, count: int) -> tuple[str, ...]:
        """상위 핵심어 count개 중 결과에 없는 것만 반환함."""

        top = {item.token for item in self.keywords[: max(0, int(count))]}
        return tuple(token for token in self.missing if token in top)


def bm25_idf(total_documents: int, document_frequency: int) -> float:
    """BM25와 같은 방식으로 토큰의 드문 정도를 계산함.

    인자: total_documents는 색인 청크 수, document_frequency는 그 토큰이 나온 청크 수임.
    반환값: 0 이상의 실수이며, 색인이 비었으면 0.0임. df가 0이어도 정의되는 식을 씀.
    부수효과: 없음.
    """

    if total_documents <= 0:
        return 0.0
    frequency = max(0, min(int(document_frequency), int(total_documents)))
    return log(1.0 + (total_documents - frequency + 0.5) / (frequency + 0.5))


def select_keywords(
    observations: Sequence[TermObservation],
    *,
    total_documents: int,
    document_frequency: Mapping[str, int],
    max_document_ratio: float,
) -> KeywordReport:
    """명사 토큰 중 드문 말만 남겨 질문의 핵심어를 고름.

    목적: "어떻게·알려주세요" 같은 흔한 말을 빼고, 답을 가르는 말만 남겨 결과와 대조하기 위함.
    방법: ① 명사·숫자·코드만 남김 ② 색인에 없는(df=0) 말은 고유이름만 남김
      ③ 전체 청크의 max_document_ratio 이상에 나오는 흔한 말은 뺌 ④ IDF 높은 순으로 정렬함.
    인자: observations는 질문을 색인과 같은 분석기로 자른 토큰이며 순서는 질문 순서임.
    인자: max_document_ratio는 0 초과 1 이하이며, 1이면 흔하다는 이유로는 빼지 않음.
    반환값: 핵심어 목록과 제외된 토큰을 담은 KeywordReport임. 결과 대조 전이라 coverage는 비어 있음.
    부수효과: 없음.
    """

    ratio = float(max_document_ratio)
    if not 0 < ratio <= 1:
        raise ValueError("max_document_ratio는 0 초과 1 이하여야 함")
    seen: set[str] = set()
    keywords: list[Keyword] = []
    dropped: list[TermObservation] = []
    for observation in observations:
        if observation.token in seen:
            continue
        seen.add(observation.token)
        if not observation.noun:
            dropped.append(observation)
            continue
        frequency = int(document_frequency.get(observation.token, 0))
        if frequency == 0 and not observation.proper:
            # 색인에 없는 일반명사는 질문자가 쓴 다른 표현일 뿐이라 결과 대조 기준이 되지 못함.
            dropped.append(observation)
            continue
        if total_documents > 0 and frequency > 0 and frequency / total_documents >= ratio:
            # 거의 모든 청크에 나오는 말은 어느 결과를 골라도 들어 있어 판정에 쓸모가 없음.
            dropped.append(observation)
            continue
        keywords.append(
            Keyword(
                token=observation.token,
                document_frequency=frequency,
                idf=bm25_idf(total_documents, frequency),
                proper=observation.proper,
            )
        )
    keywords.sort(key=lambda item: (-item.idf, item.token))
    return KeywordReport(tuple(keywords), (), tuple(dropped))


def evaluate_coverage(
    report: KeywordReport,
    tokens_by_result: Mapping[str, frozenset[str]],
) -> KeywordReport:
    """고른 핵심어가 각 검색 결과에 들어 있는지 대조함.

    인자: tokens_by_result는 결과 chunk_id별로 같은 분석기로 자른 토큰 집합임.
    반환값: coverage가 채워진 새 KeywordReport임. 입력 보고서는 바꾸지 않음.
    부수효과: 없음.
    """

    coverage = tuple(
        KeywordCoverage(
            keyword=keyword,
            present_in=tuple(
                chunk_id
                for chunk_id, tokens in tokens_by_result.items()
                if keyword.token in tokens
            ),
        )
        for keyword in report.keywords
    )
    return KeywordReport(report.keywords, coverage, report.dropped)


__all__ = [
    "Keyword",
    "KeywordCoverage",
    "KeywordReport",
    "NOUN_TAGS",
    "PROPER_TAGS",
    "TermObservation",
    "bm25_idf",
    "evaluate_coverage",
    "select_keywords",
]
