"""결제 서비스가 읽는 경로 5개 — ⑤ 3절 `T-12` · `T-14` ~ `T-16` · `T-18`.

다섯 경로 전부 읽기 전용임. 구독 상태 갱신 · 해지 예약 등록 · 결제 식별자 적재 같은 손대는 일은
이 계층이 아니라 결제 서비스의 쓰기 통로로 나감.
"""

from __future__ import annotations

from common.config import Settings

from ..source_port import ReadResult, SourceReader, read_path

__all__ = [
    "read_expiring_subscription_batch",
    "read_payment_fail_log",
    "read_subscription_for_cancel",
    "read_subscription_for_history_limit",
    "read_subscription_plan_master",
]


def read_subscription_for_history_limit(
    reader: SourceReader,
    member_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-12 구독 플랜 · 다음 결제일 — 이력 기간 제한 판정."""
    return read_path("T-12", reader, {"member_id": member_id}, limit, settings)


def read_subscription_plan_master(
    reader: SourceReader,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-14 판매 중 플랜 마스터 — 플랜 비교표 표시값."""
    return read_path("T-14", reader, {}, limit, settings)


def read_subscription_for_cancel(
    reader: SourceReader,
    member_id: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-15 해지 사전 조건 — 활성 여부 · 남은 기간 · 전환 예정일 · 복귀 제안 소진 여부."""
    return read_path("T-15", reader, {"member_id": member_id}, limit, settings)


def read_expiring_subscription_batch(
    reader: SourceReader,
    run_on: str,
    cursor: str | None = None,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-16 만료 전환 대상 — 전환 예정일 도달 + 상태 `해지예약`. 커서로 나눠 읽음."""
    return read_path("T-16", reader, {"run_on": run_on, "cursor": cursor}, limit, settings)


def read_payment_fail_log(
    reader: SourceReader,
    member_id: str,
    billing_cycle_started_on: str,
    limit: int | None = None,
    settings: Settings | None = None,
) -> ReadResult:
    """T-18 결제 실패 사유 · 누적 실패 횟수. 결제 식별자 열은 이 경로에서 읽지 않음."""
    return read_path(
        "T-18",
        reader,
        {"member_id": member_id, "billing_cycle_started_on": billing_cycle_started_on},
        limit,
        settings,
    )
