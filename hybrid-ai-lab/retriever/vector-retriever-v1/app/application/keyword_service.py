"""질문의 핵심어가 검색 결과에 들어 있는지 판정하는 업무 흐름."""

from __future__ import annotations

from typing import Mapping

from ..domain.keywords import KeywordReport, evaluate_coverage, select_keywords
from .ports import KeywordAnalyzerPort


class KeywordCoverageService:
    """질문 핵심어 선별과 결과 대조를 한 번에 제공함.

    분석·색인 통계는 생성자로 주입받은 KeywordAnalyzerPort에 맡기며, 구현체를 직접 만들지 않음.
    아직 검색 그래프나 API 응답에 연결하지 않은 독립 부품이며, 이후 근거 충분성 판정에서 사용함.
    """

    def __init__(
        self,
        analyzer: KeywordAnalyzerPort,
        *,
        max_document_ratio: float,
        top_keywords: int,
    ) -> None:
        """분석 포트와 핵심어 선별 기준을 주입받음.

        인자: max_document_ratio는 "전체 청크 중 이 비율 이상에 나오면 흔한 말로 보고 뺌"의 기준임.
        인자: top_keywords는 "상위 핵심어 미포함" 판정에 쓸 상위 몇 개를 볼지임.
        예외: 기준값 범위가 잘못되면 ValueError를 발생시킴.
        부수효과: 없음.
        """

        if not 0 < float(max_document_ratio) <= 1:
            raise ValueError("max_document_ratio는 0 초과 1 이하여야 함")
        if int(top_keywords) <= 0:
            raise ValueError("top_keywords는 양수여야 함")
        self.analyzer = analyzer
        self.max_document_ratio = float(max_document_ratio)
        self.top_keywords = int(top_keywords)

    def keywords(self, question: str) -> KeywordReport:
        """질문에서 핵심어만 골라 IDF 높은 순서로 반환함.

        반환값: coverage가 비어 있는 KeywordReport임. 결과 대조는 evaluate가 수행함.
        예외: 분석기 실행 실패 예외를 호출자에게 전달함.
        부수효과: 색인 통계를 처음 쓰는 세대이면 분석 포트가 통계를 다시 만듦.
        """

        observations = self.analyzer.observe(question)
        total, frequency = self.analyzer.corpus_statistics(
            observation.token for observation in observations
        )
        return select_keywords(
            observations,
            total_documents=total,
            document_frequency=frequency,
            max_document_ratio=self.max_document_ratio,
        )

    def evaluate(self, question: str, results: Mapping[str, str]) -> KeywordReport:
        """질문의 핵심어가 각 검색 결과 본문에 들어 있는지 대조함.

        인자: results는 결과 chunk_id에서 그 결과 본문으로 가는 매핑임.
        반환값: 핵심어·결과별 포함 여부·제외된 토큰을 담은 KeywordReport임.
        예외: 분석기 실행 실패 예외를 호출자에게 전달함.
        부수효과: 없음(분석 포트의 통계 캐시 갱신은 제외).
        """

        report = self.keywords(question)
        tokens_by_result = {
            str(chunk_id): self.analyzer.index_tokens(str(text))
            for chunk_id, text in results.items()
        }
        return evaluate_coverage(report, tokens_by_result)


__all__ = ["KeywordCoverageService"]
