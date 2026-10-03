"""답변 인용이 근거 본문과 글자 그대로 맞는지 대조하는 근거 검증 규칙임(설계 ⑥-9, S-R8, Self-RAG ②)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Citation:
    """답변 문장 하나가 기대는 근거 인용."""

    chunk_id: str
    quote: str


@dataclass(frozen=True)
class AnswerSentence:
    """답변 문장 1개와 그 인용 목록."""

    text: str
    citations: tuple[Citation, ...]


def verify_answer(
    sentences: Sequence[AnswerSentence],
    evidence_texts: Mapping[str, str],
) -> list[str]:
    """답변 초안을 근거 묶음과 대조해 실패 사유 목록을 반환함.

    인자: evidence_texts는 이번 요청에서 모은 근거(권한 통과분)의 조각ID → 원래 본문(text)임.
    방법: ① 인용 조각ID가 근거 묶음에 있는지 ② 인용문이 그 본문에 글자 그대로 있는지 ③ 인용 없는 문장이 있는지 봄.
    반환값: 빈 목록이면 통과임. 사유는 C-04 재작성 입력으로 그대로 넘기므로 문장 번호를 1부터 적음.
    """

    failures: list[str] = []
    if not sentences:
        return ["답변 문장이 하나도 없습니다."]
    for number, sentence in enumerate(sentences, start=1):
        if not sentence.citations:
            failures.append(f"{number}번 문장에 인용이 없습니다: {sentence.text[:60]}")
            continue
        for citation in sentence.citations:
            body = evidence_texts.get(citation.chunk_id)
            if body is None:
                failures.append(f"{number}번 문장이 근거 묶음에 없는 조각ID를 인용했습니다: {citation.chunk_id}")
            elif not citation.quote.strip():
                failures.append(f"{number}번 문장의 인용문이 비어 있습니다: {citation.chunk_id}")
            elif citation.quote not in body:
                # 색인 계약: 대조 기준은 text임. index_text에는 본문에 없는 머리말이 있어 오탐이 남.
                failures.append(
                    f"{number}번 문장의 인용문이 조각 본문과 글자 그대로 일치하지 않습니다: "
                    f"{citation.chunk_id} \"{citation.quote[:60]}\""
                )
    return failures
