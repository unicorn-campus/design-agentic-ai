"""원천 파일을 읽어 청킹 전에 정제·가명처리를 마친 메모리 문서로 만드는 어댑터임."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

import pymupdf

from app.application.ports import DocumentLoaderPort, SourceCatalogPort
from app.domain.models import LoadedDocument, SourceRef, TextSpan
from app.domain.text_rules import apply_text_edits, normalize_spans, pseudonym
from app.infrastructure.pdf_layout import (
    LineJoiner,
    is_margin,
    margin_key,
    page_body,
    page_lines,
    repeated_margin_keys,
)


_RECORD = re.compile(r"(?m)^\[상담ID\].*?(?=^={8,}\s*$|\Z)", re.DOTALL)
_HEADER = re.compile(
    r"^\[상담ID\]\s*(?P<record>C-\d{8}-\d{3})\s*\|\s*"
    r"(?P<date>\d{4}-\d{2}-\d{2})\s*\|\s*채널:\s*(?P<channel>[^|]+)\|\s*"
    r"회원번호:\s*(?P<member>\S+)",
    re.MULTILINE,
)
_FIELD_LINE = re.compile(r"(?m)^\[(?P<section>[^]]+)\]\s*(?P<body>.*)$")
_PHONE = re.compile(r"(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PAN = re.compile(r"(?<!\d)(?:\d[ -]?){15}\d(?!\d)")
_MEMBER = re.compile(r"\bM-\d{4,}\b", re.IGNORECASE)


def _read_json(value: str | Path | dict[str, Any]) -> dict[str, Any]:
    """이미 읽은 설정은 그대로 쓰고 경로이면 UTF-8 JSON을 읽음."""

    if isinstance(value, dict):
        return value
    return json.loads(Path(value).read_text(encoding="utf-8"))


class FileSystemSourceCatalog(SourceCatalogPort):
    """설정의 파일 이름 규칙으로 입력 디렉터리에서 원천을 찾음.

    문서 정책을 주입받으며, 파일 본문을 해석하거나 문서를 분할하지 않음.
    """

    def __init__(self, policies: str | Path | dict[str, Any]) -> None:
        """문서 유형 판별에 사용할 파일 이름 정책을 설정함.

        부수효과: 정책 경로를 받으면 생성 시점에 JSON 파일을 읽음.
        """

        self._policies = _read_json(policies)["documents"]

    def discover(self, input_path: str, doc: str, segment: int | None) -> list[SourceRef]:
        """입력 경로에서 선택 조건에 맞는 원천과 SHA-256 지문을 찾음.

        인자: doc은 all 또는 문서 키이며, segment는 D3 파일명의 S번호 필터임.
        반환값: 경로·파일명·문서 키·원본 파일 해시를 담은 목록임.
        예외: 입력 경로를 읽을 수 없으면 pathlib 파일 예외가 전파됨.
        부수효과: 후보 파일 전체를 읽어 내용 해시를 계산함.
        """

        root = Path(input_path)
        candidates = [root] if root.is_file() else sorted(root.glob("*"))
        result: list[SourceRef] = []
        for path in candidates:
            if not path.is_file() or path.is_symlink() or "_instructor" in path.name.lower():
                continue
            doc_key = self._doc_key(path.name)
            if not doc_key or (doc.lower() != "all" and doc_key.lower() != doc.lower()):
                continue
            if segment is not None and doc_key == "D3" and f"_S{segment:02d}_" not in path.name:
                continue
            digest = sha256(path.read_bytes()).hexdigest()
            result.append(SourceRef(str(path.resolve()), path.name, doc_key, digest))
        return result

    def _doc_key(self, filename: str) -> str | None:
        """파일 이름과 처음 일치하는 정책의 문서 키를 반환함."""

        for key, policy in self._policies.items():
            if re.search(policy["file_regex"], filename, re.IGNORECASE):
                return key
        return None


class ConfiguredDocumentLoader(DocumentLoaderPort):
    """PDF는 한 문서로 연결하고 상담 파일은 상담 건별 문서로 읽으며, 정제·가명처리까지 끝냄.

    문서 정책과 메타데이터 프로필을 주입받으며, 청킹·저장은 수행하지 않음.
    """

    def __init__(
        self,
        policies: str | Path | dict[str, Any],
        profiles: str | Path | dict[str, Any],
    ) -> None:
        """파일 해석 정책과 문서 유형별 기본 메타데이터를 설정함.

        부수효과: 설정 경로를 받으면 생성 시점에 JSON 파일을 읽음.
        """

        self._policies = _read_json(policies)["documents"]
        self._profiles = _read_json(profiles)["documents"]

    def load(self, source: SourceRef) -> list[LoadedDocument]:
        """원천 형식에 맞춰 정제 본문과 그 본문 기준의 쪽·문맥 위치를 가진 문서를 만듦.

        반환값: PDF는 파일당 한 문서, D3 상담 파일은 상담 레코드당 한 문서의 목록임.
        예외: 지원하지 않는 파일 형식, 텍스트 없는 PDF, 잘못된 상담 형식이면 ValueError를 발생시킴.
        부수효과: 원천 파일을 읽지만 변경하지 않음.
        """

        if source.doc_key == "D3":
            return self._load_consultations(source)
        if Path(source.path).suffix.lower() == ".pdf":
            return [self._load_pdf(source)]
        raise ValueError(f"지원하지 않는 원천 형식입니다: {Path(source.path).suffix}")

    def _load_pdf(self, source: SourceRef) -> LoadedDocument:
        """PDF를 쪽마다 여백 제거·표 변환·줄 잇기까지 마친 뒤 연결하고 쪽·문맥 위치를 기록함.

        목적: 청킹 전에 정제를 끝내 분할기가 실제 저장될 글의 길이로 청크를 자르게 함.
        방법: 쪽 정제 본문을 빈 줄로 이으면서 각 쪽이 차지하는 정제 본문 구간을 기록함. 조항·카드 구간은
          연결한 정제 본문에서 찾음. 두 구간은 청크의 쪽·조항 메타데이터 계산에만 쓰고 저장하지 않음.
        """

        policy = self._policies[source.doc_key]
        with pymupdf.open(source.path) as pdf:
            # 텍스트 계층을 한 번만 읽어 여백 판정·표 변환·줄 잇기가 같은 좌표를 보게 함.
            pages = [(page, page.rect.height, page_lines(page.get_text("dict", sort=True))) for page in pdf]
            repeated = repeated_margin_keys(
                ((height, lines) for _, height, lines in pages), int(policy.get("margin_repeat_min", 2))
            )
            bodies = [
                [(bbox, line) for bbox, line in lines if not (is_margin(bbox, height) and margin_key(line) in repeated)]
                for _, height, lines in pages
            ]
            # 줄 잇기 기준(줄 안쪽 띄어쓰기, 본문 오른쪽 한계)은 문서 전체에서 한 번만 만듦.
            joiner = LineJoiner.for_document(bodies)
            borderless = bool(policy.get("borderless_tables", False))
            page_texts = [
                page_body(page, lines, joiner, borderless_tables=borderless)[0]
                for (page, _, _), lines in zip(pages, bodies)
            ]

        joined: list[str] = []
        page_spans: list[TextSpan] = []
        cursor = 0
        for number, page_text in enumerate(page_texts, start=1):
            if not page_text.strip():
                continue
            if joined:
                joined.append("\n\n")
                cursor += 2
            joined.append(page_text)
            page_spans.append(TextSpan(cursor, cursor + len(page_text), number))
            cursor += len(page_text)

        text = "".join(joined)
        if not text.strip():
            raise ValueError("PDF에 읽을 수 있는 텍스트 계층이 없습니다. OCR 원천 처리가 필요합니다.")
        profile = dict(self._profiles.get(source.doc_key, {}))
        metadata = {
            **profile,
            "doc_type": policy["doc_type"],
            "access_level": policy["access_level"],
            "source_sha256": source.sha256,
        }
        return LoadedDocument(
            document_id=f"{source.doc_key}:{sha256(source.source.encode('utf-8')).hexdigest()[:16]}",
            source=source.source,
            doc_key=source.doc_key,
            text=text,
            metadata=metadata,
            page_spans=tuple(page_spans),
            context_spans=_pdf_contexts(text, source.doc_key),
        )

    def _load_consultations(self, source: SourceRef) -> list[LoadedDocument]:
        """상담 레코드를 분리하고 구조 필드 줄 제거와 개인정보 치환을 레코드 전체에 적용함.

        개인정보 탐지는 레코드 전체를 봐야 접수 칸의 이름을 본문에서도 찾을 수 있음. 치환을 청킹 전에
        끝내므로 개인정보 처리 전 원문은 이 함수 밖으로 나가지 않음.
        """

        text = Path(source.path).read_text(encoding="utf-8").replace("\r\n", "\n")
        documents: list[LoadedDocument] = []
        records = list(_RECORD.finditer(text))
        if not records:
            raise ValueError("상담 파일에서 상담 레코드를 찾지 못했습니다.")
        for record_index, match in enumerate(records, start=1):
            block = match.group(0).rstrip()
            header = _HEADER.search(block)
            if not header:
                raise ValueError(f"상담 레코드 {record_index}의 머리글 형식이 올바르지 않습니다.")
            fields = _consult_fields(block)
            member_id = header.group("member")
            agent_name = fields.get("접수정보", {}).get("상담사명", "")
            age_band = _age_band(
                fields.get("본인확인", {}).get("생년월일", ""),
                header.group("date"),
            )
            metadata = {
                **self._profiles.get("D3", {}),
                "doc_type": "consult_log",
                "access_level": "restricted",
                "record_id": header.group("record"),
                "consult_date": header.group("date"),
                "created_at": header.group("date"),
                "version": fields.get("기록정보", {}).get(
                    "버전", self._profiles.get("D3", {}).get("version", "")
                ),
                "owner_dept": fields.get("기록정보", {}).get(
                    "소관부서", self._profiles.get("D3", {}).get("owner_dept", "")
                ),
                "channel": header.group("channel").strip(),
                "topic": fields.get("상담주제", {}).get("value", ""),
                "member_pseudo_id": pseudonym("m", member_id),
                "agent_pseudo_id": pseudonym("a", agent_name) if agent_name else "",
                "age_band": age_band,
                "source_sha256": source.sha256,
            }
            privacy = _privacy_spans(block, fields, member_id, age_band)
            cleaned = apply_text_edits(block, _consultation_removals(block), privacy)
            documents.append(
                LoadedDocument(
                    document_id=f"D3:{header.group('record')}",
                    source=source.source,
                    doc_key="D3",
                    text=cleaned,
                    metadata=metadata,
                    context_spans=(
                        TextSpan(
                            0,
                            len(cleaned),
                            {
                                "record_id": header.group("record"),
                                "section_label": metadata["topic"],
                            },
                        ),
                    ),
                    pseudonymized=bool(privacy),
                )
            )
        return documents


def _pdf_contexts(text: str, doc_key: str) -> tuple[TextSpan, ...]:
    """D1 조항 또는 D2 카드·혜택 표식의 범위와 검색 메타데이터를 만듦."""

    if doc_key == "D1":
        pattern = re.compile(r"(?m)^제\s*(\d+)조(?:의(\d+))?\s*\([^\n]+\)")
        matches = list(pattern.finditer(text))
        values = [
            {
                "clause_no": "제" + item.group(1) + "조" + ("의" + item.group(2) if item.group(2) else ""),
                "section_label": item.group(0).strip(),
            }
            for item in matches
        ]
    else:
        pattern = re.compile(r"(?m)^(D2-C\d{3})(?:-(B\d+))?(?:\s*[|·]\s*[^\n]+)?")
        matches = list(pattern.finditer(text))
        card_names: dict[str, str] = {}
        for item in matches:
            if item.group(2):
                continue
            following = text[item.end():].lstrip("\n").splitlines()
            if following and following[0].strip():
                card_names.setdefault(item.group(1), following[0].strip())
        values = []
        for item in matches:
            value = {
                "card_id": item.group(1),
                "product_id": item.group(1),
                "card_name": card_names.get(item.group(1), ""),
                "section_label": item.group(0).strip(),
            }
            if item.group(2):
                value["benefit_id"] = f"{item.group(1)}-{item.group(2)}"
            values.append(value)
    return tuple(
        TextSpan(item.start(), matches[index + 1].start() if index + 1 < len(matches) else len(text), values[index])
        for index, item in enumerate(matches)
    )


def _consult_fields(block: str) -> dict[str, dict[str, str]]:
    """상담 레코드의 대괄호 구역과 구역별 키·값을 해석함."""

    result: dict[str, dict[str, str]] = {}
    for match in _FIELD_LINE.finditer(block):
        section, body = match.group("section"), match.group("body")
        values: dict[str, str] = {}
        if section == "상담주제":
            values["value"] = body.strip()
        else:
            for part in body.split("|"):
                if ":" in part:
                    key, value = part.split(":", 1)
                    values[key.strip()] = value.strip()
        result[section] = values
    return result


def _consultation_removals(block: str) -> tuple[TextSpan, ...]:
    """검색 본문에서 제거할 상담 구조 필드 줄의 겹치지 않는 좌표를 만듦."""

    spans = [TextSpan(match.start(), match.end() + (match.end() < len(block) and block[match.end()] == "\n"), "record_header")
             for match in _FIELD_LINE.finditer(block)]
    return normalize_spans(spans, len(block))


def _privacy_spans(
    block: str,
    fields: dict[str, dict[str, str]],
    member_id: str,
    age_band: str,
) -> tuple[TextSpan, ...]:
    """명시 필드와 정규식 탐지 개인정보를 삭제 또는 연령대로 치환할 좌표를 만듦.

    생년월일과 나이는 연령대로 일반화하고 나머지 탐지 값은 ``[삭제]``로 치환함.
    """

    spans: list[TextSpan] = []
    explicit: set[str] = set()
    for section in ("접수정보", "본인확인"):
        explicit.update(value for value in fields.get(section, {}).values() if value)
    explicit.add(member_id)
    for value in sorted(explicit, key=len, reverse=True):
        replacement = age_band if re.fullmatch(r"\d{4}-\d{2}-\d{2}|만?\s*\d{1,3}세", value) else "[삭제]"
        spans.extend(TextSpan(match.start(), match.end(), replacement) for match in re.finditer(re.escape(value), block))
    for pattern in (_PHONE, _EMAIL, _PAN, _MEMBER):
        spans.extend(TextSpan(match.start(), match.end(), "[삭제]") for match in pattern.finditer(block))
    return normalize_spans(spans, len(block))


def _age_band(birth_date: str, reference_date: str) -> str:
    """상담일 연도와 생년 연도로 10년 단위 연령대를 계산함."""

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", birth_date):
        return ""
    age = int(reference_date[:4]) - int(birth_date[:4])
    if age < 20:
        return "10대 이하"
    if age >= 60:
        return "60대 이상"
    return f"{age // 10 * 10}대"
