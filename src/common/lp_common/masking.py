"""⑤ 8절 민감 필드 분류표(F-1 ~ F-11) + ⑥ 5-2절 관측 마스킹(M-1 ~ M-4).

민감 필드 ID의 단일 출처는 ⑤ 8절임(J-1 확정). ③·④·⑥은 이 번호를 인용만 함.
F-8(관측 기록에 남는 원문)의 값 주인은 ⑥이며 여기 구현이 그 자리임.
"""

from __future__ import annotations

import re
from typing import Any

from .codes import ALLERGEN_LABEL_RE

# ⑥ 8절 L-3 — 이메일 패턴. `신설`이며 `[확인필요: 이메일 검사 정규식 확정]`
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# ⑤ 8절 민감 필드 분류표 — 필드 ID → (이름, 민감도, 변환 방식)
SENSITIVE_FIELDS: dict[str, tuple[str, str, str]] = {
    "F-1": ("알레르기·식이제한 항목명", "상(건강)", "전송 제외"),
    "F-2": ("정확 좌표(위도·경도)", "상(위치정보법)", "TB-2 제외 · TB-3 원본"),
    "F-3": ("회원 식별자·이메일·닉네임", "상", "전송 제외 · 저장 암호화"),
    "F-4": ("식당명·메뉴명 원문 이력", "중", "카테고리 코드 치환"),
    "F-5": ("추천 근거 문장·반영 컨텍스트 태그", "중", "출력측 검사"),
    "F-6": ("결제 수단 정보", "상", "보관하지 않음"),
    "F-7": ("회원 단말 토큰", "중", "변환 없음 · 문구 검사"),
    "F-8": ("관측 기록·오류 로그에 남는 원문", "상", "적재 전 코드값·제외"),
    "F-9": ("회원 참조키", "중(준식별자)", "전송 제외"),
    "F-10": ("취향 벡터", "중", "상위 카테고리 코드 치환"),
    "F-11": ("좋아요/별로 이진 피드백", "하", "변환 없음"),
}

# 관측 기록에서 이름만 보고 지울 키 — F-1·F-2·F-3·F-9 대응
_OBS_DROP_KEYS = {
    "allergen_names",
    "diet_types",
    "geo_point",
    "lat",
    "lng",
    "email",
    "nickname",
    "member_id",
    "access_token",
    "device_token",
    "password",
    "authorization",
    "api_key",
}
# 관측 기록에서 값을 가려 남길 키 — 준식별자(F-9)
_OBS_HASH_KEYS = {"member_ref"}


def mask_text(text: str) -> str:
    """M-1 — 자유 문자열에서 이메일·알레르겐 항목명을 가림.

    ⑦ 4-3 위반 예시 3번(접속 문자열이 로그에 남음)도 여기서 막음.
    """
    masked = EMAIL_RE.sub("[EMAIL]", text)
    masked = ALLERGEN_LABEL_RE.sub("[ALLERGEN]", masked)
    # DB 접속 문자열 형태를 통째로 가림
    masked = re.sub(r"postgres(?:ql)?://[^\s'\"]+", "[DSN]", masked)
    return masked


def _pseudonym(value: str) -> str:
    """준식별자를 되돌릴 수 없게 줄임. 관측 기록 상관관계만 유지함."""
    import hashlib

    return "ref:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def mask_record(payload: Any) -> Any:
    """M-1 ~ M-4 — 관측 기록 적재 **직전**에 적용함(⑤ F-8 변환 지점).

    이름 기준으로 지우고, 남는 문자열은 패턴·라벨로 한 번 더 가림.
    """
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = key.lower()
            if lowered in _OBS_DROP_KEYS:
                out[key] = "[REDACTED]"
            elif lowered in _OBS_HASH_KEYS and isinstance(value, str):
                out[key] = _pseudonym(value)
            else:
                out[key] = mask_record(value)
        return out
    if isinstance(payload, list):
        return [mask_record(v) for v in payload]
    if isinstance(payload, str):
        return mask_text(payload)
    return payload
