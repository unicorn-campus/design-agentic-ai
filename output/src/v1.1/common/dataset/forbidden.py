"""만들지 말아야 할 필드 목록.

두 갈래를 **섞어 적지 않음** — 층이 다름.

- `FORBIDDEN_FIELDS`: 어디서도 만들지 않는 필드. 스냅샷 · 시드 · 매핑 파일에 **0건**이어야 함
- `BOUNDARY_SCOPED_FIELDS`: 우리 시스템 안에서는 읽으나 특정 경계 밖으로는 내보내지 않는 필드.
  경계에서 빼는 일은 이 모듈의 몫이 아님 — 검색·가리기 쪽이 함
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "BOUNDARY_SCOPED_FIELDS",
    "FORBIDDEN_FIELDS",
    "ForbiddenFieldFound",
    "BoundaryScope",
    "assert_no_forbidden_field",
    "forbidden_fields_in",
]


class ForbiddenFieldFound(ValueError):
    """만들지 않기로 한 필드가 값 안에 들어왔음. 조용히 지우지 않고 바로 드러냄."""


@dataclass(frozen=True, slots=True)
class BoundaryScope:
    """이 필드를 어느 경계 밖으로 내보내지 않기로 했나."""

    field: str
    not_crossing: tuple[str, ...]
    source: str


# 어디서도 만들지 않는 필드 → 근거는 ⑤ 4절 금지 컬럼 `D-1` ~ `D-9`와
# ② 판정 2-2에서 `우리 시스템 내부 전체`로 적힌 항목임.
FORBIDDEN_FIELDS: dict[str, str] = {
    "email": "⑤ 4절 D-1 · ② 판정 2-2 이메일",
    "kakao_id": "⑤ 4절 D-2 · ② 판정 2-2 카카오 ID",
    "push_token": "⑤ 4절 D-3",
    "allergy_free_text": "⑤ 4절 D-4 — 자유 입력 문자열",
    "lat": "⑤ 4절 D-5 · ② 판정 2-2 정확 좌표",
    "lng": "⑤ 4절 D-6 · ② 판정 2-2 정확 좌표",
    "latitude": "⑤ 4절 D-5와 같은 값의 다른 이름",
    "longitude": "⑤ 4절 D-6과 같은 값의 다른 이름",
    "payment_id": "⑤ 4절 D-8 — 예외는 해지 예약 처리기 1명뿐이며 이 계층 대상이 아님",
    "pg_payment_id": "⑤ 4절 D-8과 같은 값의 다른 이름",
    "accept_latency_ms": "⑤ 4절 D-9",
    "card_number": "② 판정 2-2 — 우리 시스템 내부 전체에 칸이 없음",
    "card_expiry": "② 판정 2-2 — 같음",
    "cvc": "② 판정 2-2 — 같음",
    "payment_token": "② 판정 2-2 — 단말에서 결제 게이트웨이로 직접 보냄",
    "kakao_access_token": "② 판정 2-2 인증 토큰",
    "access_token": "② 판정 2-2 인증 토큰",
    "refresh_token": "② 판정 2-2 인증 토큰",
    "jwt": "② 판정 2-2 인증 토큰",
}

# 표 전체가 담당자 조회 대상이 아닌 경우 → 경로 자체를 만들지 않음(⑤ 4절 `D-7`).
FORBIDDEN_TABLES: dict[str, str] = {
    "audit_log": "⑤ 4절 D-7 — 전 열. 감사 목적 전용이라 담당자가 못 봄",
    "location_history": "⑤ 4절 D-5 · D-6 — 정확 좌표만 담긴 표",
}

# 안에서는 읽으나 특정 경계 밖으로 내보내지 않는 필드.
# ⑤ 3절이 이 값을 읽어 오라고 적어 두었으므로 **읽기 자체는 막지 않음**.
BOUNDARY_SCOPED_FIELDS: tuple[BoundaryScope, ...] = (
    BoundaryScope(
        field="allergen_labels",
        not_crossing=("TB-2",),
        source="② 판정 2-2 알레르겐 원문 라벨 · ⑤ 3절 T-2가 읽으라고 적음",
    ),
    BoundaryScope(
        field="diet_type",
        not_crossing=("TB-3",),
        source="② 판정 2-2 식이 유형 · ⑤ 3절 T-2가 읽으라고 적음",
    ),
    BoundaryScope(
        field="nickname",
        not_crossing=("TB-2",),
        source="② 판정 2-2 닉네임 · ⑤ 3절 T-1이 읽으라고 적음",
    ),
)


def _normalise(name: str) -> str:
    return name.strip().lower()


def forbidden_fields_in(names: object) -> tuple[str, ...]:
    """이름 묶음 안에 금지 필드가 있으면 그 이름을 돌려줌."""
    if isinstance(names, str):
        candidates = [names]
    elif isinstance(names, dict):
        candidates = list(names)
    else:
        candidates = list(names)  # type: ignore[arg-type]
    found = {_normalise(str(name)) for name in candidates} & set(FORBIDDEN_FIELDS)
    return tuple(sorted(found))


def assert_no_forbidden_field(names: object, where: str) -> None:
    found = forbidden_fields_in(names)
    if found:
        reasons = " / ".join(f"{name}({FORBIDDEN_FIELDS[name]})" for name in found)
        raise ForbiddenFieldFound(f"{where}에 만들지 않기로 한 필드가 있음 — {reasons}")
