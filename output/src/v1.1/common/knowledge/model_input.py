"""모델에 넘기는 입력 규격 — **칸이 없으면 값이 갈 길이 없음.**

칸 이름은 ④ 「입출력 형식」 `K-6` 10개를 문자 그대로 옮긴 것임. 새 이름을 짓지 않았음.
결정론 선행 필터가 맡은 판정의 원문 필드는 **주석으로 「안 씀」이라 적지 않고 칸 자체를 없앰**.
그 자리에는 필터가 만든 코드 배열(`excluded_ingredient_codes`)만 들어감.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "MODEL_INPUT_KEYS",
    "REMOVED_INPUT_FIELDS",
    "RemovedFieldPresent",
    "UnknownInputField",
    "build_model_input",
]

# ④ 「입출력 형식」 `K-6` — 이 10개가 규격의 전부임.
MODEL_INPUT_KEYS: tuple[str, ...] = (
    "context_tags",
    "region_label",
    "weekday",
    "time_slot",
    "weather_temp_c",
    "recent_menu_names",
    "preference_vector",
    "candidate_places",
    "excluded_ingredient_codes",
    "correlation_key",
)

# 규격에서 지운 필드와 그 이유. 이 이름이 들어오면 조용히 버리지 않고 바로 드러냄.
REMOVED_INPUT_FIELDS: dict[str, str] = {
    "allergyItems": "⑤ 판정 2 Q6 — 결정론 선행 필터가 대신함. 코드 배열만 넘김",
    "allergen_labels": "⑤ 판정 2 Q6 — 원문 라벨은 칸이 없음",
    "allergy_free_text": "⑤ 4절 D-4 — 자유 입력 문자열",
    "diet_type": "② 경계 미통과 — 후보 조회·모델 규격에 칸 없음",
    "dietType": "② 경계 미통과 — 같음",
    "nickname": "② 경계 미통과 — 인사 문구는 응답을 받은 뒤 붙임",
    "email": "⑤ 4절 D-1",
    "kakao_id": "⑤ 4절 D-2",
    "push_token": "⑤ 4절 D-3",
    "origin_lat": "② 경계 미통과 — 정확 좌표 대신 region_label만 넘김",
    "origin_lng": "② 경계 미통과 — 같음",
    "lat": "⑤ 4절 D-5",
    "lng": "⑤ 4절 D-6",
    "payment_id": "⑤ 4절 D-8",
    "pg_payment_id": "⑤ 4절 D-8",
    "accept_latency_ms": "⑤ 4절 D-9",
    "card_number": "② 경계 미통과 — 시스템 안에 칸이 없음",
    "card_expiry": "② 경계 미통과 — 같음",
    "cvc": "② 경계 미통과 — 같음",
    "payment_token": "② 경계 미통과 — 단말에서 결제 게이트웨이로 직접 감",
    "kakao_access_token": "② 경계 미통과 — 인증 토큰",
    "access_token": "② 경계 미통과 — 인증 토큰",
    "refresh_token": "② 경계 미통과 — 인증 토큰",
    "idempotency_key": "⑤ 7절 F-17 — 모델 규격에 칸을 만들지 않음",
    "swipe_results": "⑤ 7절 F-18 — 파생 벡터만 넘김",
}


class RemovedFieldPresent(ValueError):
    """규격에서 지운 필드를 넣으려 했음. 값이 갈 칸이 없음."""


class UnknownInputField(ValueError):
    """규격에 없는 이름임. 새 칸을 만들지 않음."""


def build_model_input(**fields: Any) -> dict[str, Any]:
    """모델 입력 1벌을 만듦. `MODEL_INPUT_KEYS` 밖 이름은 받지 않음."""
    removed = sorted(name for name in fields if name in REMOVED_INPUT_FIELDS)
    if removed:
        reasons = " / ".join(f"{name}({REMOVED_INPUT_FIELDS[name]})" for name in removed)
        raise RemovedFieldPresent(f"규격에서 지운 필드임 — {reasons}")
    unknown = sorted(set(fields) - set(MODEL_INPUT_KEYS))
    if unknown:
        raise UnknownInputField(f"④ 「입출력 형식」 K-6에 없는 이름임 — {unknown}")
    return {name: fields[name] for name in MODEL_INPUT_KEYS if name in fields}
