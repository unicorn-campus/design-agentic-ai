"""상담 레코드 분리와 가명화 도메인 규칙."""

from __future__ import annotations

import hashlib
import json
import re

from langchain_core.documents import Document


HEADER = re.compile(
    r"^\[상담ID\]\s+(C-\d{8}-\d{3})\s*\|\s*(\d{4}-\d{2}-\d{2})"
    r"\s*\|\s*채널:\s*([^|\n]+)\|\s*회원번호:\s*(M-\d+)\s*$",
    re.M,
)
PHONE = re.compile(r"(?<!\d)0(?:1[016789]|2|[3-6]\d)[ -]?\d{3,4}[ -]?\d{4}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PAN = re.compile(r"(?<!\d)(?:\d{4}[ -]){3}\d{4}(?!\d)|(?<!\d)\d{16}(?!\d)")
MEMBER = re.compile(r"\bM-\d+\b")


class ConsultationError(ValueError):
    """상담 경계 또는 가명화 입력이 불완전함."""


class PseudonymizeError(ConsultationError):
    """일부 개인정보만 제거된 상태로 진행하지 않도록 중단함."""


def to_pseudo(value: str, prefix: str = "m") -> str:
    if not isinstance(value, str) or not value.strip():
        raise PseudonymizeError("가명화 입력은 빈 문자열이 아닌 ID여야 함")
    if prefix not in {"m", "a"}:
        raise PseudonymizeError("가명 ID 접두사는 m 또는 a만 허용함")
    digest = hashlib.sha256(value.strip().encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _fields(block: str, label: str) -> dict[str, str]:
    match = re.search(r"^\[" + re.escape(label) + r"\]\s*(.*)$", block, re.M)
    if not match:
        return {}
    return {
        key.strip(): value.strip()
        for part in match.group(1).split("|")
        if ":" in part
        for key, value in [part.split(":", 1)]
    }


def _clean(text: str, intake: dict[str, str], identity: dict[str, str], member: str, age_band: str) -> str:
    for key in ("고객명", "상담사명", "전화", "이메일"):
        if value := intake.get(key, "").strip():
            text = text.replace(value, "[삭제]")
    birth = identity.get("생년월일", "").strip()
    if birth:
        parts = birth.split("-")
        variants = {birth, birth.replace("-", ""), birth.replace("-", "."), birth.replace("-", "/")}
        if len(parts) == 3:
            variants.add(f"{parts[0]}년 {int(parts[1])}월 {int(parts[2])}일")
        for variant in sorted(variants, key=len, reverse=True):
            text = text.replace(variant, age_band or "[연령 미상]")
    pan = identity.get("가상 카드번호", identity.get("카드번호", "")).strip()
    if pan:
        digits = re.sub(r"\D", "", pan)
        text = re.sub(r"(?<!\d)" + r"[ -]?".join(digits) + r"(?!\d)", "[삭제]", text)
    last4 = identity.get("끝4자리", "").strip()
    if last4:
        text = re.sub(r"(?<![\d,./-])" + re.escape(last4) + r"(?![\d,./-]|\s*원)", "[삭제]", text)
    text = PHONE.sub("[삭제]", text)
    text = EMAIL.sub("[삭제]", text)
    text = PAN.sub("[삭제]", text)
    text = re.sub(r"(?:끝\s*4자리|끝\s*네\s*자리|마지막\s*4자리)\s*(?:는|가|:)?\s*\d{4}", "끝4자리 [삭제]", text)
    text = re.sub(r"가상고객\d+|가상상담사\d+", "[삭제]", text)
    text = MEMBER.sub(lambda match: to_pseudo(match.group(0)), text)
    return re.sub(
        r"(?<!\d)(?:만\s*)?(\d{1,3})\s*세",
        lambda match: "60대 이상" if int(match.group(1)) >= 60 else f"{int(match.group(1)) // 10 * 10}대",
        text,
    )


def _assert_pseudonymized(content: str, metadata: dict[str, object]) -> None:
    """가명화 직후 원본 식별 정보가 남지 않았는지 확인함."""

    serialized = json.dumps({"page_content": content, "metadata": metadata}, ensure_ascii=False)
    if (
        metadata.get("pseudonymized") is not True
        or "member_id" in metadata
        or any(pattern.search(serialized) for pattern in (PHONE, EMAIL, PAN, MEMBER))
    ):
        raise PseudonymizeError("가명화 결과에 연락처·카드번호·원본 회원 ID가 남아 있음")


def parse_consultations(text: str, source: str) -> list[Document]:
    """머리글을 정본 경계로 상담을 나누며 가명화를 항상 적용함."""

    
    # lstrip(문자열)은 문자열 앞쪽에 있는 지정 문자를 제거함.
    # "\ufeff"는 파일 맨 앞에 붙을 수 있는 UTF-8 BOM 표식으로, 머리글 정규식 매칭 전에 제거함.
    text = text.replace("\r\n", "\n").lstrip("\ufeff")

    # HEADER 패턴에 맞는 모든 상담 머리글을 찾아, 위치·내용을 가진 매치 객체 목록으로 만듦.
    headers = list(HEADER.finditer(text))
    # re.findall은 패턴과 일치하는 모든 텍스트를 찾아 목록으로 반환하고, len은 그 개수를 셈.
    # r"..."의 r은 역슬래시를 그대로 해석하는 원시 문자열 표기임.
    # re.M은 여러 줄 모드로, ^가 전체 문자열뿐 아니라 각 줄의 시작도 찾게 함.
    # 따라서 ^\[상담ID\]는 각 줄 맨 앞의 [상담ID] 머리글 수를 세는 패턴임.
    if not headers or len(headers) != len(re.findall(r"^\[상담ID\]", text, re.M)):
        raise ConsultationError("상담 머리글 형식 또는 분리 건수가 올바르지 않음")
    documents: list[Document] = []
    # 이미 처리한 상담 ID를 중복 없이 저장하는 빈 집합임.
    seen: set[str] = set()

    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)

        # 원본 D3_S01 상담 파일의 첫 block 앞부분 예임.
        # [상담ID] C-20260314-001 | 2026-03-14 | 채널: 앱 채팅 | 회원번호: M-1001
        # [기록정보] 문서종류: consult_log | 공개등급: restricted | 작성일: 2026-03-14 | 소관부서: customer_service | 버전: v2
        # [접수정보] 고객명: 가상고객0001 | 전화: 010-0000-0001 | 이메일: customer0001@example.invalid | 상담사명: 가상상담사02
        # [본인확인] 가상 카드번호: 0000-0000-0001-0017 | 끝 4자리: 0017 | 생년월일: 1991-01-02 | 나이: 만 35세
        # [상담주제] 앱 인증 불편 완화
        # 고객: 인증이 안 되면 제가 뭘 잘못했나 싶어서 불안해요. 제 이름은 가상고객0001입니다.
        # 상담사: 어떤 단계에서 안내가 멈추나요?
        # 현재 [상담ID] 줄부터 다음 [상담ID] 줄 직전까지 담으며, 그 사이의 빈 줄과 구분선(====)도 포함함.
        # 마지막 상담은 다음 머리글이 없으므로 파일 끝까지 담음.
        block = text[header.start():end]

        # HEADER 정규표현식의 (...) 괄호 4개가 상담 ID·날짜·채널·회원번호를 순서대로 기억함.
        # groups()는 기억한 4개 값을 튜플로 꺼내고, 왼쪽의 변수들이 같은 순서로 하나씩 받음.
        record_id, consult_date, channel, member = header.groups()
        if record_id in seen:
            raise ConsultationError(f"중복 상담 ID: {record_id}")
        seen.add(record_id)
        info = _fields(block, "기록정보")
        intake = _fields(block, "접수정보")
        identity = _fields(block, "본인확인")
        if "끝 4자리" in identity:
            identity["끝4자리"] = identity.pop("끝 4자리")
        age = re.search(r"\d+", identity.get("나이", ""))
        age_band = (
            "60대 이상" if age and int(age.group()) >= 60
            else f"{int(age.group()) // 10 * 10}대" if age else ""
        )
        required = {
            **{key: intake.get(key) for key in ("고객명", "전화", "이메일", "상담사명")},
            **{key: identity.get(key) for key in ("가상 카드번호", "끝4자리", "생년월일", "나이")},
        }
        missing = [key for key, value in required.items() if not value]
        if missing or not age_band:
            raise PseudonymizeError(f"가명화 필수 항목 누락: {record_id} ({', '.join(missing)})")
        topic_match = re.search(r"^\[상담주제\]\s*(.*)$", block, re.M)
        metadata = {
            "source": source,
            "record_id": record_id,
            "consult_date": consult_date,
            "channel": channel.strip(),
            "doc_type": info.get("문서종류", ""),
            "created_at": info.get("작성일", ""),
            "version": info.get("버전", ""),
            "owner_dept": info.get("소관부서", ""),
            "access_level": info.get("공개등급", ""),
            "pseudonymized": True,
            "topic": topic_match.group(1).strip() if topic_match else "",
        }

        lines: list[str] = []
        in_dialogue = False
        for line in block.splitlines()[1:]:
            if re.match(r"^(고객|상담사):", line):
                in_dialogue = True
                lines.append(line)
            elif line.startswith("[") or re.fullmatch(r"=+", line.strip()):
                in_dialogue = False
            elif in_dialogue and line.strip():
                lines.append(line)
        content = "\n".join(lines)
        if not content:
            raise ConsultationError(f"대화가 없는 상담: {record_id}")
        metadata.update(
            member_pseudo_id=to_pseudo(member),
            agent_pseudo_id=to_pseudo(intake["상담사명"], "a"),
            age_band=age_band,
        )
        metadata["topic"] = _clean(metadata["topic"], intake, identity, member, age_band)
        content = _clean(content, intake, identity, member, age_band)
        _assert_pseudonymized(content, metadata)
        documents.append(Document(page_content=content, metadata=metadata))
    return documents
