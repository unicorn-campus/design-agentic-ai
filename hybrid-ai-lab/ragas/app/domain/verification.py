"""평가셋 검증 5검사(글자 대조 · 카드 블록 · 숫자 대조 · 답 없음 · 구조) 규칙."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from .text import normalize, numbers_in

_BENEFIT = re.compile(r"D2-C\d{3}-B\d+")
_QUESTION_ID = re.compile(r"^Q\d{2}$")
CHECK_NAMES = {
    1: "① 글자 대조",
    2: "② 카드 블록",
    3: "③ 숫자 대조",
    4: "④ 답 없음",
    5: "⑤ 구조",
}


@dataclass(frozen=True)
class Chunk:
    """검증이 읽는 색인 조각 한 개. 세대의 말뭉치에서 출처 · 본문 · 혜택 코드만 골라 옮긴 값."""

    chunk_id: str
    source: str  # 원천 파일 이름
    text: str  # 저장 본문(인용 · 표시용 원문)
    benefit_ids: tuple[str, ...] = ()  # 조각에 걸친 D2 혜택 코드(머리말이 잘린 조각의 대체 판정용)


@dataclass(frozen=True)
class Issue:
    """검사 하나가 실패한 이유."""

    question_id: str
    check: int  # 1 ~ 5 — CHECK_NAMES의 검사 번호
    reason: str


def _matching_chunks(chunks: Iterable[Chunk], source: str, fragment: str) -> list[Chunk]:
    """지정 출처 파일의 조각 중 원문 조각을 글자 그대로 담은 것만 고름."""

    target = normalize(fragment)
    return [chunk for chunk in chunks if source in chunk.source and target in normalize(chunk.text)]


def _benefit_at(chunk: Chunk, fragment: str) -> str | None:
    """조각 본문에서 원문 조각 바로 앞에 나온 혜택 코드를 찾음.

    목적: 카드 64종이 같은 문구를 공유하므로 '어느 혜택 블록 안의 문장인가'로 정답 위치를 확정함.
    방법: 정규화한 본문에서 조각 위치 앞쪽의 마지막 'D2-Cxxx-Byy'를 씀. 앞에 머리말이 없으면(조각이 블록 중간에서
    시작) 조각에 걸친 혜택 코드가 하나뿐일 때만 그 코드로 봄.
    """

    body = normalize(chunk.text)
    position = body.find(normalize(fragment))
    headers = [m for m in _BENEFIT.finditer(body) if m.start() < position]
    if headers:
        return headers[-1].group(0)
    return chunk.benefit_ids[0] if len(chunk.benefit_ids) == 1 else None


def check_structure(questions: list[dict[str, Any]]) -> list[Issue]:
    """⑤ 필수 칸 · id 중복 · 답 있음과 근거의 짝 · 위치 꼴을 검사함(색인 없이 평가셋만 봄)."""

    issues: list[Issue] = []
    seen: set[str] = set()
    for question in questions:
        qid = str(question.get("id", "?"))
        if not _QUESTION_ID.match(qid):
            issues.append(Issue(qid, 5, "id 꼴이 Q00이 아님"))
        if qid in seen:
            issues.append(Issue(qid, 5, "id가 겹침"))
        seen.add(qid)
        if not str(question.get("question", "")).strip():
            issues.append(Issue(qid, 5, "질문이 비었음"))
        relevance = question.get("relevance") or []
        if question.get("answerable"):
            if not relevance:
                issues.append(Issue(qid, 5, "답 있음 문항인데 근거가 없음"))
            for unit in relevance:
                if not unit.get("any_of"):
                    issues.append(Issue(qid, 5, f"근거 {unit.get('location')}에 원문 조각이 없음"))
                if unit.get("source", "").startswith("D2_") and not _BENEFIT.fullmatch(str(unit.get("location"))):
                    issues.append(Issue(qid, 5, f"D2 위치가 혜택 코드 꼴이 아님: {unit.get('location')}"))
        else:
            if relevance:
                issues.append(Issue(qid, 5, "답 없음 문항인데 근거가 있음"))
            if not question.get("no_answer_terms"):
                issues.append(Issue(qid, 5, "답 없음 문항인데 확인 낱말 묶음이 없음"))
        if not isinstance(question.get("filters", []), list):
            issues.append(Issue(qid, 5, "filters가 목록이 아님"))
    return issues


def check_against_index(questions: list[dict[str, Any]], chunks: list[Chunk]) -> list[Issue]:
    """① ② ③ ④를 색인 세대의 조각으로 검사함.

    ③ 숫자 대조는 '원문 조각을 담은 색인 조각' 전체에서 찾음 — 원문 조각은 핵심 문장만 옮겨 적어서
    정답의 월 한도 같은 숫자가 바로 옆 칸에 있는 경우가 있기 때문임(설계서의 「평가셋만」에서 바꾼 점).
    반환값: 실패 항목 목록. 비어 있으면 통과임.
    """

    issues: list[Issue] = []
    for question in questions:
        qid = question["id"]
        if not question.get("answerable"):
            for group in question.get("no_answer_terms") or []:
                terms = [normalize(term) for term in group]
                hit = next((c for c in chunks if all(t in normalize(c.text) for t in terms)), None)
                if hit is not None:
                    issues.append(Issue(qid, 4, f"낱말 묶음 {group}을 모두 담은 조각이 있음: {hit.chunk_id}"))
            continue
        evidence_chunks: list[Chunk] = []
        for unit in question.get("relevance") or []:
            for fragment in unit.get("any_of", []):
                found = _matching_chunks(chunks, unit["source"], fragment)
                if not found:
                    issues.append(Issue(qid, 1, f"색인 본문에 없음: 「{fragment}」"))
                    continue
                evidence_chunks.extend(found)
                location = str(unit.get("location", ""))
                if location.startswith("D2-C") and not any(_benefit_at(c, fragment) == location for c in found):
                    issues.append(Issue(qid, 2, f"「{fragment}」가 {location} 블록 안에 없음"))
        if evidence_chunks:
            body = "".join(normalize(c.text).replace(",", "") for c in evidence_chunks)
            for number in numbers_in(question["ground_truth"]):
                if number not in body:
                    issues.append(Issue(qid, 3, f"정답의 숫자 {number}가 근거 조각에 없음"))
    return issues
