"""회원 서비스가 읽는 경로 3개 — ⑤ 3절 `T-1` · `T-2` · `T-3`."""

from __future__ import annotations

from common.config import Settings

from ..source_port import ReadResult, SourceReader, read_path

__all__ = ["read_consent_log", "read_diet_restriction", "read_member_profile"]


def read_member_profile(
    reader: SourceReader,
    member_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-1 회원 프로파일 — 회원ID · 닉네임 · 알림설정 · 구독 상태."""
    return read_path("T-1", reader, {"member_id": member_id}, limit, settings)


def read_diet_restriction(
    reader: SourceReader,
    member_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-2 식이 제한 — 알레르겐 라벨 목록 · 식이 유형.

    두 값은 우리 시스템 안에서만 씀. 모델 벤더 · 외부 조회로는 내보내지 않음.
    """
    return read_path("T-2", reader, {"member_id": member_id}, limit, settings)


def read_consent_log(
    reader: SourceReader,
    member_id: str,
    consent_kind: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-3 동의 이력 — 위치 · 건강 민감정보 동의의 최신 상태."""
    return read_path(
        "T-3", reader, {"member_id": member_id, "consent_kind": consent_kind}, limit, settings
    )
