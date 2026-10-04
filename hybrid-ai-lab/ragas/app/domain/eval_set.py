"""사람용 평가셋(eval-set.md)을 기계용 문항 목록으로 바꾸는 규칙과 평가셋 지문 계산."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

NO_ANSWER_PREFIX = "확인 필요"  # 답 없음 문항의 정답 머리말 — 이 글자로 시작하면 answerable=False
HASH_LENGTH = 12  # 평가셋 지문 길이(설계 가정 — 충돌 확률만 고려한 값)

_HEADING = re.compile(r"^###\s+(Q\d+)\.\s*(.+?)\s*$")
_ANSWER = re.compile(r"^-\s+\*\*정답\*\*:\s*(.+?)\s*$")
_EVIDENCE = re.compile(r"^-\s+\*\*근거\*\*:\s*(.+?)\s*$")
_NO_ANSWER_RULE = re.compile(r"^-\s+\*\*답이 없음을 확인한 기준\*\*")
_FILTERS = re.compile(r"^-\s+\*\*filters\*\*:\s*`(.+)`\s*$")
_FRAGMENT = re.compile(r"^\s+-\s+「(.+)」\s*$")
_TERM_GROUP = re.compile(r"^\s+-\s+(.+?)\s*$")
_SOURCE = re.compile(r"`([^`]+)`")


class EvalSetFormatError(ValueError):
    """eval-set.md가 약속한 꼴과 달라 문항을 만들 수 없음을 나타냄."""


def _parse_evidence(line_text: str, question_id: str) -> dict[str, Any]:
    """근거 줄 하나를 근거 단위(출처 파일 · 위치 · 원문 조각 목록)로 바꿈.

    목적: 근거 줄 1개 = 근거 단위 1개(변환 규칙 R1). Recall 분모가 이 단위 수가 됨.
    방법: 백틱 안 파일명을 출처로, 마지막 ' · ' 뒤 조각을 위치로 씀.
    예시: "D3 … `D3_S02_….txt` · M-1042(장기 보유) · C-20260302-001" → location "C-20260302-001"(R6).
    """

    source = _SOURCE.search(line_text)
    if source is None:
        raise EvalSetFormatError(f"{question_id}: 근거 줄에 백틱으로 감싼 출처 파일명이 없습니다.")
    location = line_text.split(" · ")[-1].strip()
    return {"source": source.group(1).strip(), "location": location, "any_of": []}


def parse_eval_set_markdown(text: str) -> list[dict[str, Any]]:
    """eval-set.md의 「정답과 근거」 절을 읽어 문항 dict 목록을 만듦.

    방법: '### Q01.' 제목마다 정답 · 근거 · 원문 조각 · filters · 답 없음 낱말 묶음을 줄 단위로 모음.
    반환값: id · question · answerable · ground_truth · filters · relevance(+ 답 없음이면 no_answer_*) dict 목록.
    예외: 제목만 있고 정답이 없거나, 근거 없이 원문 조각이 나오면 EvalSetFormatError.
    """

    questions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    mode = ""  # 들여쓴 불릿이 원문 조각(evidence)인지 답 없음 낱말 묶음(no_answer)인지 구분함
    for raw in text.splitlines():
        line = raw.rstrip()
        heading = _HEADING.match(line)
        if heading:
            current = {"id": heading.group(1), "question": heading.group(2), "answerable": True,
                       "ground_truth": "", "filters": [], "relevance": []}
            questions.append(current)
            mode = ""
            continue
        if current is None:
            continue  # 머리말 · 구성 표 · 문항 표는 사람용이라 건너뜀
        if match := _ANSWER.match(line):
            current["ground_truth"] = match.group(1)
            if match.group(1).startswith(NO_ANSWER_PREFIX):
                # 답 없음 문항은 근거를 비우고 「확인 필요」로 끝나야 정답(R3)
                current.update(answerable=False, ground_truth=NO_ANSWER_PREFIX,
                               no_answer_reason="문서에 답이 없음 — 「확인 필요」로 끝나야 정답", no_answer_terms=[])
            mode = ""
        elif match := _EVIDENCE.match(line):
            current["relevance"].append(_parse_evidence(match.group(1), current["id"]))
            mode = "evidence"
        elif _NO_ANSWER_RULE.match(line):
            mode = "no_answer"
        elif match := _FILTERS.match(line):
            # filters 값은 고치지 않고 그대로 옮김(R4) — 리트리버는 역할 판정에만 씀
            current["filters"] = json.loads(match.group(1))
            mode = ""
        elif mode == "evidence" and (match := _FRAGMENT.match(line)):
            current["relevance"][-1]["any_of"].append(match.group(1))
        elif mode == "no_answer" and (match := _TERM_GROUP.match(line)):
            current["no_answer_terms"].append([term.strip() for term in match.group(1).split(" + ")])
        elif line.startswith("- **"):
            mode = ""  # 사람 검토 메모 등 다른 항목이 시작되면 들여쓴 불릿 모으기를 멈춤
    for question in questions:
        if not question["ground_truth"]:
            raise EvalSetFormatError(f"{question['id']}: 정답 줄이 없습니다.")
    return questions


def build_eval_set_document(questions: list[dict[str, Any]], source_name: str) -> dict[str, Any]:
    """문항 목록을 리트리버 평가가 읽는 JSON 문서 모양으로 감쌈.

    evaluation_mode는 기록용임 — evaluate_retriever.py는 이 블록을 읽지 않고 실행 인자로 Top-k를 정함.
    """

    return {
        "schema_version": 1,
        "source": source_name,
        "evaluation_mode": {"top_k": 5, "answer_generation": True, "note": "기록용 — 실제 값은 실행 인자가 정함"},
        "questions": questions,
    }


def eval_set_hash(questions: list[dict[str, Any]]) -> str:
    """questions 블록을 키 정렬 · 공백 없는 JSON으로 만들어 SHA-256 앞 12자를 냄.

    목적: 버전끼리 같은 평가셋으로 쟀는지 확인함. 머리말 · 기록용 블록이 바뀌어도 지문은 같음.
    """

    canonical = json.dumps(questions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:HASH_LENGTH]
