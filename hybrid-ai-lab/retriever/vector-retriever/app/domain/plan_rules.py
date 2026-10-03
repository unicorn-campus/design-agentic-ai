"""질문 분석(C-01) 응답을 형식·개수·조건 보존 규칙으로 검사해 검색 대상을 확정하는 규칙임(S-R2 ⑤)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from .models import QTYPE_CHITCHAT, QTYPE_COMPLEX, QTYPE_SIMPLE


@dataclass(frozen=True)
class PlanDecision:
    """검사를 통과한 질문 분석 결과."""

    question_type: str
    sub_question_texts: tuple[str, ...] = ()  # complex일 때만 1 ~ 3개. simple이면 비어 있고 원 질문 1개로 검색
    chitchat_reply: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


def fallback_simple(warning: str) -> PlanDecision:
    """C-01 실패·시간 부족·형식 오류 때의 대체 경로: 단순 질문으로 보고 원 질문 1개로 검색함."""

    return PlanDecision(QTYPE_SIMPLE, (), "", (warning,))


def apply_plan_rules(
    *,
    question: str,
    question_type: str,
    sub_questions: Sequence[str],
    chitchat_reply: str,
    max_sub_questions: int,
    condition_terms_of: Callable[[str], set[str]],
) -> PlanDecision:
    """C-01 응답을 서버 규칙으로 확정함.

    인자: condition_terms_of는 문장에서 상품명(카드명·별칭 통일)·기간·금액 같은 조건 낱말을 뽑는 함수임.
    방법: ① 알 수 없는 유형 → 단순 ② 잡담인데 응답문이 비면 → 단순(검색해 보는 쪽이 안전함)
    ③ 복합인데 하위 질문이 없으면 → 단순 ④ 3개 초과면 앞 3개만 쓰고 경고
    ⑤ 하위 질문들이 원 질문의 조건을 빠뜨리거나 없는 조건을 만들면 → 단순(원 질문 1개)으로 대체함.
    반환값: PlanDecision. 규칙이 결과를 바꾼 이유는 warnings에 담음.
    """

    if question_type not in (QTYPE_CHITCHAT, QTYPE_SIMPLE, QTYPE_COMPLEX):
        return fallback_simple(f"알 수 없는 질문 유형 → 단순 처리: {question_type}")
    if question_type == QTYPE_CHITCHAT:
        reply = str(chitchat_reply).strip()
        if not reply:
            return fallback_simple("잡담 응답문이 비어 단순 질문으로 처리")
        return PlanDecision(QTYPE_CHITCHAT, (), reply)
    if question_type == QTYPE_SIMPLE:
        return PlanDecision(QTYPE_SIMPLE)

    texts = [" ".join(str(text).split()) for text in sub_questions if str(text).strip()]
    texts = list(dict.fromkeys(texts))
    warnings: list[str] = []
    if not texts:
        return fallback_simple("복합 판정인데 하위 질문이 없어 단순 질문으로 처리")
    if len(texts) > max_sub_questions:
        warnings.append(f"하위 질문 {len(texts)}개 중 앞 {max_sub_questions}개만 사용")
        texts = texts[:max_sub_questions]
    if len(texts) == 1:
        # 하위 질문이 하나뿐이면 분해가 아니므로 원 질문으로 검색함(원 질문 보존, 이론 13장)
        return PlanDecision(QTYPE_SIMPLE, (), "", (*warnings, "하위 질문이 1개라 단순 질문으로 처리"))

    original_terms = condition_terms_of(question)
    sub_terms = [condition_terms_of(text) for text in texts]
    union = set().union(*sub_terms)
    lost = original_terms - union
    invented = union - original_terms
    if lost or invented:
        detail = []
        if lost:
            detail.append(f"빠진 조건 {sorted(lost)}")
        if invented:
            detail.append(f"새로 생긴 조건 {sorted(invented)}")
        return fallback_simple("하위 질문 조건 검사 실패 → 단순 처리: " + ", ".join(detail))
    return PlanDecision(QTYPE_COMPLEX, tuple(texts), "", tuple(warnings))
