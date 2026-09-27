"""문서 메타데이터와 알려진 개인정보 형식 검사. 외부 라이브러리 의존 없음."""
import json
import re
from datetime import date

from .consultations import EMAIL, MEMBER, PAN, PHONE


def validate_document(doc: dict, enum_overrides: dict | None = None) -> list[str]:
    errors = []
    if not isinstance(doc, dict):
        return ["Document는 사전이어야 함"]
    meta = doc.get("metadata")
    content = doc.get("page_content")
    if not isinstance(meta, dict):
        return ["metadata는 사전이어야 함"]
    if not isinstance(content, str) or not content.strip():
        errors.append("page_content: 본문이 비어 있거나 문자열이 아님")
    common = {"source", "doc_type", "created_at", "version", "owner_dept", "access_level"}
    for key in common:
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            errors.append(f"{key}: 필수 문자열 누락")
    enums = {"doc_type": {"regulation", "benefit_guide", "consult_log"},
             "access_level": {"public", "internal", "restricted"},
             "owner_dept": {"product_planning", "customer_service", "benefit_ops"},
             "channel": {"콜센터", "앱 채팅", "영업점"}}
    if enum_overrides:
        enums.update(enum_overrides)
    for key, allowed in enums.items():
        if key in meta and (not isinstance(meta[key], str) or meta[key] not in allowed):
            errors.append(f"{key}: 허용 목록에 없는 값")
    for key in ("created_at", "effective_date", "consult_date"):
        if key in meta:
            try:
                if not isinstance(meta[key], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta[key]):
                    raise ValueError()
                date.fromisoformat(meta[key])
            except (TypeError, ValueError):
                errors.append(f"{key}: 실제 YYYY-MM-DD 날짜 필요")
    if "version" in meta and not re.fullmatch(r"v?\d+(?:\.\d+)*", str(meta["version"])):
        errors.append("version: 1.0, v1 또는 v1.0 형식 필요")
    if meta.get("doc_type") in ("regulation", "benefit_guide"):
        for key in ("effective_date", "supersedes", "page"):
            if key not in meta:
                errors.append(f"{key}: 규정·혜택 문서 필수 키 누락")
        if "page" in meta and (type(meta["page"]) is not int or meta["page"] < 1):
            errors.append("page: 1 이상 정수 필요")
        if "supersedes" in meta and meta["supersedes"] not in (None, "") and not re.fullmatch(r"v?\d+(?:\.\d+)*", str(meta["supersedes"])):
            errors.append("supersedes: 이전 버전 또는 빈 값 필요")
    if meta.get("doc_type") == "consult_log":
        for key in ("record_id", "consult_date", "channel"):
            if not isinstance(meta.get(key), str) or not meta[key]:
                errors.append(f"{key}: 상담 필수 문자열 누락")
        if not re.fullmatch(r"C-\d{8}-\d{3}", str(meta.get("record_id", ""))):
            errors.append("record_id: C-YYYYMMDD-NNN 형식 필요")
        if meta.get("created_at") != meta.get("consult_date"):
            errors.append("created_at: 상담일과 작성일 불일치")
        if meta.get("access_level") != "restricted":
            errors.append("access_level: 상담은 정제 후에도 restricted 필요")
        if not isinstance(meta.get("pseudonymized"), bool):
            errors.append("pseudonymized: 참/거짓 필요")
        if meta.get("pseudonymized") is True:
            for key, prefix in (("member_pseudo_id", "m"), ("agent_pseudo_id", "a")):
                if not re.fullmatch(prefix + r"_[0-9a-f]{16}", str(meta.get(key, ""))):
                    errors.append(f"{key}: 가명 ID 형식 오류")
            if not re.fullmatch(r"\d{1,3}대(?: 이상)?", str(meta.get("age_band", ""))):
                errors.append("age_band: 연령대 필요")
            serialized = json.dumps(doc, ensure_ascii=False)
            if any(pattern.search(serialized) for pattern in (PHONE, EMAIL, PAN, MEMBER)):
                errors.append("privacy: 연락처·카드번호·원문 회원 ID 잔존")
            if re.search(r"가상고객\d+|가상상담사\d+|(?:만\s*)?\d{1,3}\s*세", serialized):
                errors.append("privacy: 알려진 이름·정확한 나이 잔존")
            if "member_id" in meta:
                errors.append("privacy: 정제 결과의 member_id 키 금지")
        elif not re.fullmatch(r"M-\d+", str(meta.get("member_id", ""))):
            errors.append("member_id: 원문 회원 ID 누락")
    return errors
