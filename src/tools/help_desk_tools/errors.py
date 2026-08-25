from __future__ import annotations

from enum import StrEnum

import httpx


class ErrorCategory(StrEnum):
    AUTHENTICATION = "인증 오류"
    INPUT = "입력 오류"
    TRANSIENT = "일시 장애"
    PERMISSION = "권한 부족"
    UNKNOWN = "분류 불가"


class ConnectorError(RuntimeError):
    def __init__(
        self,
        category: ErrorCategory,
        message: str,
        *,
        field_name: str | None = None,
        requested_scope: str | None = None,
        required_scope: str | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.field_name = field_name
        self.requested_scope = requested_scope
        self.required_scope = required_scope


class ApprovalRequired(PermissionError):
    pass


def classify_http_failure(response: httpx.Response) -> ConnectorError:
    status = response.status_code
    if status == httpx.codes.UNAUTHORIZED:
        return ConnectorError(ErrorCategory.AUTHENTICATION, "외부 자격 인증이 거부됨")
    if status in (httpx.codes.BAD_REQUEST, httpx.codes.UNPROCESSABLE_ENTITY):
        return ConnectorError(ErrorCategory.INPUT, "외부 요청 규격이 거부됨")
    if status == httpx.codes.FORBIDDEN:
        return ConnectorError(ErrorCategory.PERMISSION, "외부 요청 권한이 부족함")
    if status in (
        httpx.codes.REQUEST_TIMEOUT,
        httpx.codes.TOO_MANY_REQUESTS,
        httpx.codes.INTERNAL_SERVER_ERROR,
        httpx.codes.BAD_GATEWAY,
        httpx.codes.SERVICE_UNAVAILABLE,
        httpx.codes.GATEWAY_TIMEOUT,
    ):
        return ConnectorError(ErrorCategory.TRANSIENT, "외부 시스템이 일시적으로 응답하지 않음")
    return ConnectorError(ErrorCategory.UNKNOWN, "외부 실패를 분류할 수 없음")
