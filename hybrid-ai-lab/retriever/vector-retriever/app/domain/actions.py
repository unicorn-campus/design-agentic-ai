"""S-R3에서 고를 수 있는 행동 목록·규칙 기본 행동·에이전트 선택 검사를 정하는 규칙임."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import SUB_PENDING, SUB_UNCERTAIN, SubQuestion

# C-02 응답 열거값(커넥터 설계 C-02). 상태의 next_action(search·transform·finish)과 1:1로 대응함.
ACTION_SEARCH = "search_docs"
ACTION_TRANSFORM = "transform_query"
ACTION_FINISH = "finish"


@dataclass(frozen=True)
class ActionChoice:
    """다음 행동 1개와 대상 하위 질문ID·선택 이유."""

    action: str
    target_qid: str
    reason: str
    by_rule: bool  # 참이면 LLM이 아니라 규칙이 고름


def search_targets(sub_questions: Sequence[SubQuestion]) -> list[str]:
    """아직 검색하지 않은 하위 질문ID 목록을 반환함."""

    return [sq.qid for sq in sub_questions if sq.status == SUB_PENDING]


def transform_targets(sub_questions: Sequence[SubQuestion]) -> list[str]:
    """채점이 불확실이고 아직 변환하지 않은 하위 질문ID 목록을 반환함."""

    return [sq.qid for sq in sub_questions if sq.status == SUB_UNCERTAIN and sq.transform_count == 0]


def allowed_actions(sub_questions: Sequence[SubQuestion]) -> list[str]:
    """규칙이 지금 허용하는 행동 목록을 만듦(S-R3 ②).

    방법: 검색 안 한 질문이 있으면 검색, 불확실이고 변환 전인 질문이 있으면 질문 변환, 수집 종료는 언제나 허용함.
    """

    actions: list[str] = []
    if search_targets(sub_questions):
        actions.append(ACTION_SEARCH)
    if transform_targets(sub_questions):
        actions.append(ACTION_TRANSFORM)
    actions.append(ACTION_FINISH)
    return actions


def default_action(sub_questions: Sequence[SubQuestion], reason: str) -> ActionChoice:
    """C-02를 못 쓰거나 응답이 틀렸을 때의 규칙 기본 행동을 반환함.

    방법: 검색 안 한 질문이 있으면 그 첫 질문을 검색하고, 없으면 수집 종료함(설계 ③ C-02 대체 경로).
    변환은 기본 행동에 넣지 않음 — LLM이 실패한 상황에서 또 LLM(C-03)을 부르지 않기 위함.
    """

    pending = search_targets(sub_questions)
    if pending:
        return ActionChoice(ACTION_SEARCH, pending[0], reason, by_rule=True)
    return ActionChoice(ACTION_FINISH, "", reason, by_rule=True)


def validate_choice(
    sub_questions: Sequence[SubQuestion],
    *,
    action: str,
    target_qid: str,
    reason: str,
) -> ActionChoice | None:
    """에이전트(C-02)가 고른 행동이 규칙 안에 있는지 검사함(S-R3 ④).

    반환값: 허용되면 ActionChoice, 목록 밖 행동·없는 ID·그 행동을 할 수 없는 질문이면 None(→ 규칙 기본 행동).
    """

    if action not in allowed_actions(sub_questions):
        return None
    if action == ACTION_FINISH:
        return ActionChoice(ACTION_FINISH, "", reason, by_rule=False)
    eligible = search_targets(sub_questions) if action == ACTION_SEARCH else transform_targets(sub_questions)
    if target_qid not in eligible:
        return None
    return ActionChoice(action, target_qid, reason, by_rule=False)
