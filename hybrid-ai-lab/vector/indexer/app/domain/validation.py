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
    metadata = {**document.metadata, **profile}
    return Document(id=document.id, page_content=document.page_content, metadata=metadata)


def validate_document(document: Document | dict, enum_overrides: dict | None = None) -> list[str]:
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
