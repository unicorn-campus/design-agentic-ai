"""② 판정 2-2 「경계 미통과 항목」 — 가리는 대상이 아니라 **칸 자체를 안 만드는** 대상임.

여기 적힌 이름이 도구 스키마에 나타나면 등록 시점에 바로 실패함.
시험에서만 보는 표가 아니라 코드가 실제로 막는 자리임.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

__all__ = [
    "GLOBAL_FORBIDDEN_KEYS",
    "FORBIDDEN_KEYS_BY_BOUNDARY",
    "forbidden_keys_for",
    "assert_no_forbidden_keys",
]

# 어느 커넥터에도 만들지 않는 칸 — ② 판정 2-2의 `우리 시스템 내부 전체` · `TB-2 · TB-3 · TB-6`행.
GLOBAL_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        # 카드번호 · 유효기간 · CVC — 시스템 내부 어디에도 칸이 없음
        "card_number",
        "card_expiry",
        "cvc",
        "cardNumber",
        "cardExpiry",
        # 인증 토큰(JWT · 카카오 토큰) — 외부 호출 규격에 칸을 만들지 않음
        "jwt",
        "access_token",
        "kakao_access_token",
        "authorization_token",
        # 이메일 · 카카오 ID — 요청 상관용 익명 키만 둠
        "email",
        "kakao_id",
    }
)

# 경계마다 더 막는 칸 — ② 판정 2-2에서 `TB-2 모델 벤더`에만 걸린 항목들임.
FORBIDDEN_KEYS_BY_BOUNDARY: Mapping[str, frozenset[str]] = {
    "TB-2": frozenset(
        {
            "allergyItems",  # 알레르겐 원문 라벨 — `excluded_ingredient_codes`로 대체
            "allergy_items",
            "origin_lat",  # 정확 위치 좌표 — `region_label`로 대체
            "origin_lng",
            "dest_lat",
            "dest_lng",
            "nickname",  # 닉네임 — 인사 문구는 응답을 받은 뒤 시스템이 붙임
            "diet_type",
            "dietType",
        }
    ),
    "TB-3": frozenset({"diet_type", "dietType", "allergyItems", "allergy_items"}),
    "TB-5": frozenset({"diet_type", "dietType", "nickname"}),
    "TB-6": frozenset({"diet_type", "dietType"}),
}


def forbidden_keys_for(trust_boundary: str) -> frozenset[str]:
    return GLOBAL_FORBIDDEN_KEYS | FORBIDDEN_KEYS_BY_BOUNDARY.get(
        trust_boundary, frozenset()
    )


def assert_no_forbidden_keys(
    connector_id: str, trust_boundary: str, key_names: Iterable[str]
) -> None:
    """도구 스키마 등록 시점에 부름. 걸리면 프로그램이 뜨는 시점에 실패함."""
    blocked = forbidden_keys_for(trust_boundary)
    hits = sorted(name for name in key_names if name in blocked)
    if hits:
        raise ValueError(
            f"{connector_id}({trust_boundary}) 스키마에 경계 미통과 항목이 있음: {hits}"
            " — ② 판정 2-2는 칸 자체를 만들지 않는 것으로 정했음"
        )
