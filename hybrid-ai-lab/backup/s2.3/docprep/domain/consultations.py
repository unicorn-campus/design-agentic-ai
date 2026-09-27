"""상담 레코드 경계와 교육용 개인정보 정제 규칙. 파일·DB 의존 없음."""
from __future__ import annotations

import hashlib
import re


HEADER = re.compile(r"^\[상담ID\]\s+(C-\d{8}-\d{3})\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*채널:\s*([^|\n]+)\|\s*회원번호:\s*(M-\d+)\s*$", re.M)
PHONE = re.compile(r"(?<!\d)0(?:1[016789]|2|[3-6]\d)[ -]?\d{3,4}[ -]?\d{4}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PAN = re.compile(r"(?<!\d)(?:\d{4}[ -]){3}\d{4}(?!\d)|(?<!\d)\d{16}(?!\d)")
MEMBER = re.compile(r"\bM-\d+\b")


def to_pseudo(value: str, prefix: str = "m") -> str:
    """정형 데이터와 문서가 공유할 교육용 SHA-256 변환. 접근 통제의 대체 수단 아님."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("가명화 입력은 빈 문자열이 아닌 ID여야 함")
    if prefix not in {"m", "a"}:
        raise ValueError("가명 ID 접두사는 m 또는 a만 허용")
    return prefix + "_" + hashlib.sha256(value.strip().encode("utf-8")).hexdigest()[:16]


def _fields(block: str, label: str) -> dict[str, str]:
    match = re.search(r"^\[" + re.escape(label) + r"\]\s*(.*)$", block, re.M)
    if not match:
        return {}
    return dict(part.strip().split(":", 1) for part in match[1].split("|") if ":" in part)


def _clean(text: str, intake: dict, identity: dict, member: str, age_band: str) -> str:
    """접수 값의 반복 노출과 대표 변형을 제거. 업무 날짜·금액은 보존."""
    for key in ("고객명", "상담사명", "전화", "이메일"):
        value = intake.get(key, "").strip()
        if value:
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
        pattern = r"(?<!\d)" + r"[ -]?".join(digits) + r"(?!\d)"
        text = re.sub(pattern, "[삭제]", text)
    # 끝 네 자리도 남기지 않되 금액·업무 날짜의 일부는 제거하지 않음.
    last4 = identity.get("끝4자리", "").strip()
    if last4:
        text = re.sub(r"(?<![\d,./-])" + re.escape(last4) + r"(?![\d,./-]|\s*원)", "[삭제]", text)
    text = PHONE.sub("[삭제]", text)
    text = EMAIL.sub("[삭제]", text)
    text = PAN.sub("[삭제]", text)
    text = re.sub(r"(?:끝\s*4자리|끝\s*네\s*자리|마지막\s*4자리)\s*(?:는|가|:)?\s*\d{4}", "끝4자리 [삭제]", text)
    text = re.sub(r"가상고객\d+|가상상담사\d+", "[삭제]", text)
    text = MEMBER.sub(lambda m: to_pseudo(m[0]), text)
    text = re.sub(r"(?<!\d)(?:만\s*)?(\d{1,3})\s*세",
                  lambda m: "60대 이상" if int(m[1]) >= 60 else f"{int(m[1]) // 10 * 10}대", text)
    return text


def parse_consultations(text: str, source: str, split_by: str = "header", pseudonymize: bool = False) -> list[dict]:
    """상담별 Document 사전 반환. 잘못된 경계는 조용히 유실하지 않고 실패 처리."""
    text = text.replace("\r\n", "\n").lstrip("\ufeff")
    headers = list(HEADER.finditer(text))
    if not headers:
        raise ValueError("상담 ID 머리줄을 찾을 수 없음: [상담ID] C-YYYYMMDD-NNN 확인")
    if len(headers) != len(re.findall(r"^\[상담ID\]", text, re.M)):
        raise ValueError("형식이 잘못된 상담 머리줄 존재")
    if split_by not in {"header", "rule", "date"}:
        raise ValueError("split_by는 header, rule, date 중 하나여야 함")
    if split_by == "date":
        count = len(re.findall(r"\d{4}-\d{2}-\d{2}", text))
        raise ValueError(f"날짜 경계 오류: 날짜 {count}곳, 상담 {len(headers)}건. 본문 날짜도 잘리므로 header 사용 필요")
    if split_by == "rule":
        chunks = re.split(r"^={3,}\s*$", text, flags=re.M)[1:]
        if not chunks or any(len(HEADER.findall(c)) != 1 for c in chunks):
            raise ValueError("구분선 경계 오류: 빈 조각 또는 상담 병합 발생. header 사용 필요")
    documents = []
    seen = set()
    for index, header in enumerate(headers):
        block = text[header.start():headers[index + 1].start() if index + 1 < len(headers) else len(text)]
        record_id, consult_date, channel, member = header.groups()
        if record_id in seen:
            raise ValueError(f"중복 상담 ID: {record_id}")
        seen.add(record_id)
        info = {k.strip(): v.strip() for k, v in _fields(block, "기록정보").items()}
        intake = {k.strip(): v.strip() for k, v in _fields(block, "접수정보").items()}
        identity = {k.strip(): v.strip() for k, v in _fields(block, "본인확인").items()}
        if "끝 4자리" in identity:
            identity["끝4자리"] = identity.pop("끝 4자리")
        topic = re.search(r"^\[상담주제\]\s*(.*)$", block, re.M)
        age = re.search(r"\d+", identity.get("나이", ""))
        age_band = ("60대 이상" if int(age[0]) >= 60 else f"{int(age[0]) // 10 * 10}대") if age else ""
        metadata = {"source": source, "record_id": record_id, "consult_date": consult_date,
                    "channel": channel.strip(), "doc_type": info.get("문서종류", ""),
                    "created_at": info.get("작성일", ""), "version": info.get("버전", ""),
                    "owner_dept": info.get("소관부서", ""), "access_level": info.get("공개등급", ""),
                    "pseudonymized": pseudonymize, "topic": topic[1].strip() if topic else ""}
        # 화자 줄 다음의 줄바꿈 발화도 유지하되, 설명 머리줄·구분선은 제외.
        lines, in_dialogue = [], False
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
            raise ValueError(f"대화가 없는 상담: {record_id}")
        if pseudonymize:
            required_intake = ("고객명", "전화", "이메일", "상담사명")
            required_identity = ("가상 카드번호", "끝4자리", "생년월일", "나이")
            missing = [key for key in required_intake if not intake.get(key)]
            missing += [key for key in required_identity if not identity.get(key)]
            if missing or not age_band:
                raise ValueError(f"정제에 필요한 접수·본인확인 항목 누락: {record_id} ({', '.join(missing)})")
            metadata.update(member_pseudo_id=to_pseudo(member),
                            agent_pseudo_id=to_pseudo(intake["상담사명"], "a"), age_band=age_band)
            metadata["topic"] = _clean(metadata["topic"], intake, identity, member, age_band)
            content = _clean(content, intake, identity, member, age_band)
        else:
            metadata["member_id"] = member
        documents.append({"page_content": content, "metadata": metadata})
    return documents
