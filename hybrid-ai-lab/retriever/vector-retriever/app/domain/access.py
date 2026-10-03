"""역할(role)을 열람 등급(access_level) 목록으로 바꾸는 권한 규칙임."""

from __future__ import annotations

# 설계 ⑥-7 사용자 결정: agent는 public만, auditor는 public + restricted(상담 이력 D3)를 볼 수 있음.
# 색인 계약상 권한 축은 access_level(public·restricted) 하나뿐이라 역할도 이 두 값으로만 바꿈.
ROLE_ACCESS_LEVELS: dict[str, tuple[str, ...]] = {
    "agent": ("public",),
    "auditor": ("public", "restricted"),
}


def access_levels_for(role: str | None) -> tuple[str, ...]:
    """역할에 허용된 열람 등급 목록을 반환함.

    인자: role은 서버가 로그인 정보(게이트웨이 헤더)에서 받은 값이며 요청 본문 값이 아님.
    반환값: 정해진 순서의 열람 등급 튜플임.
    예외: 역할이 없거나 정의되지 않은 값이면 ValueError를 발생시킴.
    """

    key = str(role or "").strip().lower()
    if key not in ROLE_ACCESS_LEVELS:
        raise ValueError(f"허용되지 않은 역할입니다: {role!r}")
    return ROLE_ACCESS_LEVELS[key]
