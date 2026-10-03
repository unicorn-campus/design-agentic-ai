"""질문 변환(C-03) 응답에 서버가 강제하는 금지 규칙임(설계 ⑥-3, S-R6 ④ ~ ⑤)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Sequence

# C-03 선택지 7종(이론 13장): 5기법 + keep(그대로) + clarify(되묻기)
TECHNIQUES = ("rewrite", "multi", "hyde", "stepback", "decomposition")
KEEP = "keep"
CLARIFY = "clarify"
ALLOWED_TECHNIQUES = (*TECHNIQUES, KEEP, CLARIFY)
# HyDE·Step-Back은 질문을 크게 바꾸므로 원 질문도 함께 검색해야 함(이론 10·12장 — 필수)
ORIGINAL_REQUIRED = frozenset({"hyde", "stepback"})
MAX_QUERIES = 3

# 원인별 기법 가이드(설계 ⑥-3, LLM 참고용). 프롬프트 입력 technique_guide로 그대로 넘김.
TECHNIQUE_GUIDE: tuple[dict[str, str], ...] = (
    {"cause": "핵심어가 결과에 하나도 없음", "technique": "multi 또는 rewrite"},
    {"cause": "핵심어는 결과에 있는데 점수가 상한 미달, 질문이 상대적으로 짧음", "technique": "hyde"},
    {
        "cause": "구체 사례를 묻는데 상위 주제 문서만 검색됨. 사례를 정하는 상위 개념·원칙 문서를 찾아야 함",
        "technique": "stepback",
    },
    {"cause": "1·2위 격차가 작음(비슷한 대상끼리 경쟁)", "technique": "rewrite (대상명이 없으면 clarify)"},
    {"cause": "한 문장에 서로 다른 질문이 묶여 있음", "technique": "decomposition"},
    {"cause": "더 바꿀 여지가 없음", "technique": "keep"},
    {"cause": "어느 상품·대상을 묻는지 특정되지 않음", "technique": "clarify"},
)


@dataclass(frozen=True)
class TransformDecision:
    """금지 규칙을 통과한 최종 변환 결정."""

    technique: str
    queries: tuple[str, ...] = ()
    include_original: bool = False
    clarify_question: str = ""
    reason: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _normalize(text: str) -> str:
    """공백을 하나로 줄이고 소문자로 바꿔 '글자만 바꾼 같은 질의'를 비교할 수 있게 함."""

    return " ".join(str(text).lower().split())


def mixed_target_clarify(
    *,
    question_has_target: bool,
    result_card_ids: Sequence[str],
    result_card_names: Sequence[str],
) -> str | None:
    """'대상명 없음 + 대상 섞임'이면 서버가 만든 확인 질문을, 아니면 None을 반환함.

    대상은 카드임. 질문에 카드명·별칭이 없고, 검색 1위가 카드 조각이며, 결과에 서로 다른 카드가 둘 이상 있을 때만 섞임으로 봄.
    1위가 약관·상담처럼 카드와 무관한 조각이면 카드에 대한 질문이 아니므로 되묻지 않음
    (평가셋 E12 '연회비 면제 조건' — 약관이 1위인데 카드 조각이 섞여 잘못 되묻던 사례, 사용자 결정 2026-10-03).
    인자: question_has_target은 질문에 카드명·별칭이 있는지(같은 사전으로 판정)임.
    인자: result_card_ids는 결과 조각의 카드 코드를 **순위 순서대로** 담은 목록이며 카드가 없는 조각은 빈 문자열임.
    반환값: 위 조건을 모두 만족하면 되물을 1문장, 아니면 None임.
    """

    if question_has_target or not result_card_ids or not result_card_ids[0]:
        return None
    distinct = list(dict.fromkeys(card for card in result_card_ids if card))
    if len(distinct) < 2:
        return None
    names = list(dict.fromkeys(name for name in result_card_names if name))[:3]
    hint = f"(예: {', '.join(names)})" if names else ""
    return f"어느 카드에 대한 질문인지 알려 주시겠어요? {hint}".strip()


def apply_transform_rules(
    *,
    technique: str,
    queries: Sequence[str],
    include_original: bool,
    clarify_question: str,
    reason: str,
    target_question: str,
    previous_queries: Sequence[str],
    tokens_of: Callable[[str], Sequence[str]],
    forced_clarify: str | None,
) -> TransformDecision:
    """C-03 응답에 금지 규칙을 적용해 최종 결정을 만듦.

    인자: tokens_of는 BM25와 같은 분석기(날짜·별칭 통일 포함)로 질의를 낱말 목록으로 바꾸는 함수임.
    인자: forced_clarify는 '대상명 없음 + 대상 섞임' 규칙이 만든 확인 질문이며 있으면 LLM 응답과 상관없이 clarify임.
    방법: ① 대상 섞임 → clarify ② 7종 밖 → keep ③ 같은 질의 반복·날짜 표기·별칭만 바꾼 질의는 버림,
    남은 질의가 없으면 keep ④ hyde·stepback은 원 질문 함께 검색으로 덮어씀.
    반환값: TransformDecision. 규칙이 결정을 바꾼 이유는 warnings에 남김.
    """

    if forced_clarify:
        return TransformDecision(CLARIFY, (), False, forced_clarify, reason, ("대상명 없음 + 대상 섞임 → clarify",))
    if technique not in ALLOWED_TECHNIQUES:
        return TransformDecision(KEEP, (), False, "", reason, (f"허용 선택지 밖 기법 거부: {technique}",))
    if technique == KEEP:
        return TransformDecision(KEEP, (), False, "", reason)
    if technique == CLARIFY:
        question = str(clarify_question).strip()
        if not question:
            return TransformDecision(KEEP, (), False, "", reason, ("확인 질문이 비어 clarify 거부",))
        return TransformDecision(CLARIFY, (), False, question, reason)

    warnings: list[str] = []
    seen = {_normalize(target_question)} | {_normalize(query) for query in previous_queries}
    target_tokens = Counter(tokens_of(target_question))
    kept: list[str] = []
    for raw in queries:
        query = str(raw).strip()
        if not query:
            continue
        key = _normalize(query)
        if key in seen:
            warnings.append(f"같은 질의 반복 제외: {query[:40]}")
            continue
        if Counter(tokens_of(query)) == target_tokens:
            # 날짜 표기·카드 별칭은 분석기가 이미 통일하므로 낱말이 같으면 검색 결과도 같음(색인 계약)
            warnings.append(f"날짜 표기·별칭만 바꾼 질의 제외: {query[:40]}")
            continue
        seen.add(key)
        kept.append(query)
        if len(kept) == MAX_QUERIES:
            break
    if not kept:
        return TransformDecision(KEEP, (), False, "", reason, (*warnings, "쓸 수 있는 변환 질의 없음 → keep"))
    original = True if technique in ORIGINAL_REQUIRED else bool(include_original)
    return TransformDecision(technique, tuple(kept), original, "", reason, tuple(warnings))
