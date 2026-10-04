"""상담 검색 회원 필터 규칙 — 회원번호 형식 검사와 색인과 같은 가명 계산, 조각이 그 회원 범위에 드는지 판정."""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Iterable, Sequence

from .models import Candidate, Chunk

CONSULT_DOC_TYPE = "consult_log"  # 상담 이력 문서 종류(색인 메타데이터 doc_type)
MEMBER_ID_PATTERN = re.compile(r"^M-[0-9]{1,20}$")  # 상담 화면 회원번호 꼴(예: M-1042)
PSEUDONYM_PREFIX = "m"  # 인덱서가 회원 가명에 붙이는 구분값
PSEUDONYM_LENGTH = 16  # SHA-256 앞 몇 자리를 쓰는지 — 인덱서 text_rules.pseudonym과 같아야 함


def validate_member_id(member_id: str) -> str:
    """앞뒤 공백을 걷은 회원번호를 돌려줌.

    예외: 꼴이 'M-숫자'가 아니면 ValueError — 오타로 다른 값을 해시하면 오류 없이 결과만 비게 되므로 먼저 막음.
    """

    value = member_id.strip() if isinstance(member_id, str) else ""
    if not MEMBER_ID_PATTERN.fullmatch(value):
        raise ValueError("회원번호 형식이 올바르지 않습니다(예: M-1042).")
    return value


def member_pseudonym(member_id: str) -> str:
    """회원번호를 색인 메타데이터의 member_pseudo_id와 같은 가명으로 바꿈.

    방법: 인덱서와 같은 식 'm_' + SHA-256(회원번호) 앞 16자리. DB 조회 없이 계산만 함.
    예시: "M-1042" → "m_59853c3d8e1e3c25"(색인 값과 대조한 시험으로 두 프로그램을 묶음).
    주의: 비밀키 없는 해시라 보안 장치가 아님 — 남의 기록을 막는 일은 역할(열람 등급) 검사가 맡음.
    """

    digest = sha256(validate_member_id(member_id).encode("utf-8")).hexdigest()
    return f"{PSEUDONYM_PREFIX}_{digest[:PSEUDONYM_LENGTH]}"


def member_id_terms(member_id: str) -> frozenset[str]:
    """질문 속 회원번호가 핵심어 후보로 뽑힐 때의 낱말 꼴(소문자 전체 · 숫자 부분)을 돌려줌.

    목적: 상담 본문에는 회원번호 대신 가명만 있어 회원번호를 핵심어로 두면 채점이 항상 '불확실'이 됨
    (실측 2026-10-05: Q15 1위 0.763 · 격차 0.73인데 missing_keywords=['m-1042', '1042']로 탈락).
    예시: "M-1042" → {"m-1042", "1042"}.
    예외: 꼴이 틀리면 validate_member_id의 ValueError.
    """

    value = validate_member_id(member_id)
    return frozenset({value.lower(), value.split("-", 1)[1]})


def member_allows(chunk_member: str | None, requested: str | None) -> bool:
    """조각이 요청한 회원 범위에 드는지 판정함.

    규칙: 회원 필터가 없으면 모두 통과. 있으면 회원 가명이 없는 조각(약관 · 혜택 안내)은 통과,
    회원 가명이 있는 조각(상담 이력)은 같은 회원일 때만 통과 — 상담만 그 회원 것으로 좁힘(사용자 결정 2026-10-04).
    """

    if not requested or not chunk_member:
        return True
    return chunk_member == requested


def is_member_consult(chunk: Chunk, member: str | None) -> bool:
    """조각이 요청한 회원의 상담 이력인지 판정함. 회원 필터가 없으면 언제나 거짓."""

    return bool(member) and chunk.source.doc_type == CONSULT_DOC_TYPE and chunk.member_pseudo_id == member


def consult_leads(candidates: Sequence[Candidate], member: str | None) -> bool:
    """융합 점수 1위 후보가 그 회원의 상담 이력인지 판정함(상담 이력 판정 규칙, 사용자 결정 2026-10-05).

    목적: 리랭커는 '질문에 직접 답하는 문장'을 재는데 상담 질문은 해석이 필요해 정답 조각도 0 ~ 0.02점이 나옴
    (실측: Q17 정답 줄 0.002 — 같은 줄을 직접 묻는 질문은 0.990). 회원 필터로 범위가 그 회원 상담 몇 건으로 좁혀진
    뒤라 융합 1위가 상담이면 상담을 묻는 질문으로 보고, 리랭크 점수 대신 이 사실로 판정함.
    반환값: 후보가 없거나 회원 필터가 없으면 거짓.
    """

    if not member or not candidates:
        return False
    top = max(candidates, key=lambda c: c.fused_score)
    return is_member_consult(top.chunk, member)


def chronological(chunks: Iterable[Chunk]) -> list[Chunk]:
    """상담 이력 조각을 상담 날짜 → 상담ID → 조각ID 순으로 정렬함(날짜 없는 조각은 맨 앞)."""

    return sorted(chunks, key=lambda c: (c.source.consult_date or "", c.source.record_id or "", c.chunk_id))
