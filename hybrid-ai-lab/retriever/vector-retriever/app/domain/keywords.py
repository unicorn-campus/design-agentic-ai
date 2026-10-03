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


def select_common_domain_terms(
    term_document_frequency: Mapping[str, int],
    *,
    num_docs: int,
    min_df_ratio: float,
) -> tuple[str, ...]:
    """색인 조각의 일정 비율 이상에 나오는 명사(문서의 핵심 업무 어휘)를 고름.

    목적: C-01이 잡담으로 판정한 질문에 업무 낱말이 있는지 볼 때 씀(잡담 오분류 막기, 사용자 결정 2026-10-03).
    인자: min_df_ratio는 '업무 어휘'로 볼 최소 비율. 실측: '연회비' 163 · '고객' 56건, 인사말 낱말은 최대 '하루' 31건
    (전체 218건)이라 0.2(44건)를 설계 가정 초깃값으로 둠.
    반환값: 입력 순서를 지킨 낱말 튜플. 조각 수가 0이면 빈 튜플임.
    """

    if num_docs <= 0:
        return ()
    limit = float(min_df_ratio) * float(num_docs)
    return tuple(term for term, frequency in term_document_frequency.items() if float(frequency) >= limit)
