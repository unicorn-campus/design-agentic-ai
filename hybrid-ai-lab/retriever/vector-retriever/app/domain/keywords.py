"""질문에서 채점용 핵심어(드물게 나오는 명사·숫자·코드)를 고르는 규칙임(설계 ⑥-8 핵심어 일치)."""

from __future__ import annotations

from typing import Mapping


def select_rare_terms(
    term_document_frequency: Mapping[str, int],
    *,
    num_docs: int,
    max_df_ratio: float,
) -> tuple[str, ...]:
    """명사·숫자·코드 후보 중 문서 빈도가 낮은 낱말만 핵심어로 고름.

    목적: '혜택'·'카드'처럼 거의 모든 조각에 나오는 낱말은 결과에 있어도 관련성을 말해 주지 못하므로 뺌.
    인자: term_document_frequency는 같은 분석기·사전으로 통일한 후보 낱말 → 그 낱말이 나오는 조각 수임.
    인자: max_df_ratio는 '드묾'의 기준(조각 수 대비 비율). 설계는 'IDF 높음'까지만 정해 초깃값은 설계 가정임.
    반환값: 입력 순서를 지킨 핵심어 튜플임. 색인에 한 번도 없는 낱말(빈도 0)도 드문 낱말로 봄.
    """

    if num_docs <= 0:
        return ()
    limit = float(max_df_ratio) * float(num_docs)
    return tuple(term for term, frequency in term_document_frequency.items() if float(frequency) <= limit)
