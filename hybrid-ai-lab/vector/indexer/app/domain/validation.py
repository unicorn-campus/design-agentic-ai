"""메타데이터, 프로필 덮어쓰기, 개인정보 잔존 검사."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict, ValidationError

from .consultations import EMAIL, MEMBER, PAN, PHONE


ALLOWED_DOC_TYPES = {"regulation", "benefit_guide", "consult_log"}
ALLOWED_ACCESS_LEVELS = {"public", "internal", "restricted"}
FORBIDDEN_PROFILE_KEYS = {
    "source", "doc_type", "page", "record_id", "consult_date", "pseudonymized"
}


class ProfileOverrideError(ValueError):
    pass


class MetadataError(ValueError):
    pass


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str
    doc_type: str
    created_at: str
    version: str
    owner_dept: str
    access_level: str


def apply_profile(document: Document, profile: dict[str, Any]) -> Document:
    """운영 프로필을 적용하되 출처·권한 판정 핵심 키 덮어쓰기를 차단함."""

    forbidden = sorted(FORBIDDEN_PROFILE_KEYS.intersection(profile))
    if forbidden:
        raise ProfileOverrideError(f"프로필 금지 키 덮어쓰기: {', '.join(forbidden)}")

    # **사전은 사전 안의 key=value 항목을 새 중괄호 안으로 하나씩 펼치는 문법임.
    # 먼저 document.metadata를 넣고, 이어서 profile을 넣음. 같은 key가 있으면 나중 profile 값이 남음.
    # 예: metadata={"access_level": "restricted"}, profile={"access_level": "public", "owner_dept": "benefit_ops"}
    # 결과: {"access_level": "public", "owner_dept": "benefit_ops"}. 단, 금지 key는 위에서 이미 막음.
    metadata = {**document.metadata, **profile}  # { }는 두 사전의 항목을 담을 새 메타데이터 사전을 만듦.
    return Document(id=document.id, page_content=document.page_content, metadata=metadata)


def validate_document(document: Document | dict, enum_overrides: dict | None = None) -> list[str]:
    """문서 본문과 메타데이터를 검사하고 발견한 오류 메시지 목록을 반환함.

    검사 목록:
    - 입력값이 LangChain ``Document`` 또는 ``page_content``·``metadata``를 가진 사전인지 확인함.
    - ``metadata``가 사전인지 확인함.
    - ``source``, ``doc_type``, ``created_at``, ``version``, ``owner_dept``, ``access_level``이
      필수 문자열로 들어 있는지 확인함.
    - ``page_content``가 비어 있지 않은 문자열인지 확인함.
    - ``doc_type``, ``access_level``, ``owner_dept``, ``channel``이 허용 목록의 값인지 확인함.
      ``enum_overrides``가 전달되면 해당 항목의 허용 목록을 교체함.
    - ``created_at``, ``effective_date``, ``consult_date``가 실제로 존재하는 ``YYYY-MM-DD`` 날짜인지 확인함.
    - 규정·혜택 문서는 ``effective_date``, ``supersedes``, ``page`` 키가 있는지 확인하고,
      ``page``가 1 이상의 정수인지 확인함.
    - 상담 문서는 ``record_id``, ``consult_date``, ``channel`` 필수값과 상담 ID 형식을 확인함.
    - 상담 문서의 작성일과 상담일이 같은지, 공개등급이 ``restricted``인지 확인함.
    - 상담 문서가 가명화되었는지와 회원·상담사 가명 ID가 정해진 형식인지 확인함.
    - 상담 본문과 메타데이터에 전화번호·이메일·카드번호·원본 회원 ID가 남았는지 확인함.

    오류가 없으면 빈 목록을 반환하고, 오류가 있으면 모든 오류 메시지를 목록으로 반환함.
    """
    if isinstance(document, Document):
        content, metadata = document.page_content, document.metadata
    elif isinstance(document, dict):
        content, metadata = document.get("page_content"), document.get("metadata")
    else:
        return ["Document 형식이 아님"]
    if not isinstance(metadata, dict):
        return ["metadata는 사전이어야 함"]
    errors: list[str] = []
    try:
        DocumentMetadata.model_validate(metadata)
    except ValidationError as error:
        errors.extend(f"{'.'.join(map(str, item['loc']))}: 필수 문자열 누락" for item in error.errors())
    for key in ("source", "doc_type", "created_at", "version", "owner_dept", "access_level"):
        if key in metadata and (not isinstance(metadata[key], str) or not metadata[key].strip()):
            errors.append(f"{key}: 필수 문자열 누락")
    if not isinstance(content, str) or not content.strip():
        errors.append("page_content: 본문이 비어 있음")
    enums = {
        "doc_type": ALLOWED_DOC_TYPES,
        "access_level": ALLOWED_ACCESS_LEVELS,
        "owner_dept": {"product_planning", "customer_service", "benefit_ops"},
        "channel": {"콜센터", "앱 채팅", "영업점"},
    }
    if enum_overrides:
        enums.update(enum_overrides)
    for key, allowed in enums.items():
        if key in metadata and metadata[key] not in allowed:
            errors.append(f"{key}: 허용 목록에 없는 값")
    for key in ("created_at", "effective_date", "consult_date"):
        if key in metadata:
            try:
                if not isinstance(metadata[key], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", metadata[key]):
                    raise ValueError
                date.fromisoformat(metadata[key])
            except ValueError:
                errors.append(f"{key}: 실제 YYYY-MM-DD 날짜 필요")
    kind = metadata.get("doc_type")
    if kind in {"regulation", "benefit_guide"}:
        for key in ("effective_date", "supersedes", "page"):
            if key not in metadata:
                errors.append(f"{key}: 규정·혜택 문서 필수 키 누락")
        if "page" in metadata and (type(metadata["page"]) is not int or metadata["page"] < 1):
            errors.append("page: 1 이상 정수 필요")
    if kind == "consult_log":
        for key in ("record_id", "consult_date", "channel"):
            if not isinstance(metadata.get(key), str) or not metadata[key]:
                errors.append(f"{key}: 상담 필수 문자열 누락")
        if not re.fullmatch(r"C-\d{8}-\d{3}", str(metadata.get("record_id", ""))):
            errors.append("record_id: C-YYYYMMDD-NNN 형식 필요")
        if metadata.get("created_at") != metadata.get("consult_date"):
            errors.append("created_at: 상담일과 작성일 불일치")
        if metadata.get("access_level") != "restricted":
            errors.append("access_level: 상담은 restricted 필요")
        if metadata.get("pseudonymized") is not True:
            errors.append("pseudonymized: true 필요")
        for key, prefix in (("member_pseudo_id", "m"), ("agent_pseudo_id", "a")):
            if not re.fullmatch(prefix + r"_[0-9a-f]{16}", str(metadata.get(key, ""))):
                errors.append(f"{key}: 가명 ID 형식 오류")
        serialized = json.dumps({"page_content": content, "metadata": metadata}, ensure_ascii=False)
        if "member_id" in metadata or any(pattern.search(serialized) for pattern in (PHONE, EMAIL, PAN, MEMBER)):
            errors.append("privacy: 연락처·카드번호·원문 회원 ID 잔존")
    return errors


def validate_documents(documents: list[Document], enum_overrides: dict | None = None) -> dict[str, Any]:
    rows = []
    for index, document in enumerate(documents):
        errors = validate_document(document, enum_overrides)
        rows.append({"index": index, "source": document.metadata.get("source", ""), "errors": errors})
    invalid = sum(bool(row["errors"]) for row in rows)
    return {"checked": len(documents), "valid": len(documents) - invalid, "invalid": invalid, "rows": rows}


def sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Chroma가 받는 원시값만 남기고 복합 값은 JSON 문자열로 보존함."""

    if metadata.get("access_level") not in ALLOWED_ACCESS_LEVELS:
        raise MetadataError("access_level 누락 또는 허용 밖 값")
    if metadata.get("doc_type") not in ALLOWED_DOC_TYPES:
        raise MetadataError("doc_type 누락 또는 허용 밖 값")

    result: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        result[key] = value if isinstance(value, (str, int, float, bool)) else json.dumps(value, ensure_ascii=False, sort_keys=True)

    return result
