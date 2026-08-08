"""바깥에서 온 실패를 4종으로 먼저 가른 뒤 처리함. 분류 이름이 그대로 관측 기록의 실패 사유가 됨.

용어 1줄 — **오류 분류** = 실패를 한 덩어리로 다루지 않고 종류별로 갈라, 다시 불러도 되는 실패와
다시 부르면 안 되는 실패를 구분하는 표임(`04-connector.md` 10단계).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "ErrorClass",
    "RETRYABLE_CLASSES",
    "ErrorReport",
    "ConnectorRetryable",
    "ConnectorCallFailed",
    "ApprovalMissing",
    "PreconditionNotMet",
    "IdempotencyKeyMissing",
    "ConnectorNotConfigured",
]


class ErrorClass(StrEnum):
    """10단계 오류 분류표의 4종 + `분류 불가`. 값은 관측 기록에 그대로 실림."""

    AUTH = "인증 오류"
    INPUT = "입력 오류"
    TRANSIENT = "일시 장애"
    PERMISSION = "권한 부족"
    UNCLASSIFIED = "분류 불가"


# 재시도를 붙이는 분류 — `일시 장애`와 `인증 오류` 2종뿐임.
# `인증 오류`는 자격을 버리고 한 번 더 부르는 것이며, 별도 계층을 만들지 않고
# `단계 재시도`(③ 8-3절) 예산 안에서만 일어남. 그래서 재시도 계층은 여전히 1개임.
RETRYABLE_CLASSES = frozenset({ErrorClass.TRANSIENT, ErrorClass.AUTH})


@dataclass(frozen=True, slots=True)
class ErrorReport:
    """위로 올릴 때 담는 것. 주소 · 자격 · 응답 본문 원문을 담지 않음."""

    connector_id: str
    step_id: str
    error_class: ErrorClass
    reason: str
    offending_keys: tuple[str, ...] = ()
    requested_scopes: tuple[str, ...] = ()
    attempts: int = 1
    last_backoff_ms: int = 0
    credential_refreshed_at_ms: int | None = None
    extra: Mapping[str, object] = field(default_factory=dict)

    @property
    def retryable(self) -> bool:
        return self.error_class in RETRYABLE_CLASSES

    def as_record(self) -> dict[str, object]:
        """관측 기록·상태 `error_history`에 그대로 얹는 모양. 자격 값이 들어갈 칸이 없음."""
        record: dict[str, object] = {
            "connector_id": self.connector_id,
            "step_id": self.step_id,
            "error_class": self.error_class.value,
            "reason": self.reason,
            "attempts": self.attempts,
        }
        if self.offending_keys:
            record["offending_keys"] = list(self.offending_keys)
        if self.error_class is ErrorClass.PERMISSION:
            record["requested_scopes"] = list(self.requested_scopes)
            record["required_scope"] = "[확인필요: 제공자별 권한 범위 표기]"
        if self.error_class is ErrorClass.TRANSIENT:
            record["last_backoff_ms"] = self.last_backoff_ms
        if self.error_class is ErrorClass.AUTH:
            record["credential_refreshed_at_ms"] = self.credential_refreshed_at_ms
        record.update(self.extra)
        return record


class ConnectorRetryable(Exception):
    """재시도해도 되는 실패. `common.external_call.call_with_limits`가 이것만 잡아 다시 부름."""

    def __init__(self, report: ErrorReport) -> None:
        super().__init__(f"{report.connector_id}/{report.step_id}: {report.error_class.value}")
        self.report = report


class ConnectorCallFailed(Exception):
    """커넥터가 호출자에게 던지는 단 하나의 실패 타입. 안에 분류표 한 줄이 들어 있음."""

    def __init__(self, report: ErrorReport) -> None:
        super().__init__(f"{report.connector_id}/{report.step_id}: {report.error_class.value}")
        self.report = report


class ApprovalMissing(ConnectorCallFailed):
    """승인 표시가 없어 호출 자체를 거부함. 바깥을 부르기 전에 막음(기본 거부)."""


class PreconditionNotMet(ConnectorCallFailed):
    """⑤ 「커넥터 검증 기준」이 요구한 앞선 단계가 안 끝났음. 순서를 어긴 호출을 막음."""


class IdempotencyKeyMissing(ConnectorCallFailed):
    """쓰기 도구인데 중복 방지 키가 없음.

    중복 방지 키 = 같은 요청이 두 번 와도 한 번만 처리되게 하는 표식임.
    """


class ConnectorNotConfigured(RuntimeError):
    """주소 · 자격 · 대역 여부가 설정에 없음. 코드에 박지 않으므로 여기서 멈춤."""
