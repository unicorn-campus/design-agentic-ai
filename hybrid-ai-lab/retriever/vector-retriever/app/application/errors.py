"""표현 계층과 하위 계층이 함께 쓰는 응용 오류 계약과 오류 요약 함수."""

from __future__ import annotations


class LLMConfigError(ValueError):
    """설정값이 없거나 안전하게 변환할 수 없을 때 발생함."""


class IndexUnavailableError(RuntimeError):
    """컬렉션이 비었거나 임베딩 서명이 맞지 않음을 나타냄."""


class LLMError(RuntimeError):
    """외부 LLM 오류의 공통 계약."""

    def __init__(self, message: str, *, attempts: int = 0, status_code: int | None = None):
        super().__init__(message)
        self.attempts = attempts
        self.status_code = status_code


class LLMRetryableError(LLMError):
    """429·5xx·연결·타임아웃처럼 제한적으로 재시도 가능한 오류."""


class LLMAuthError(LLMError):
    """키가 거부되거나 모델 사용 권한이 없는 오류."""


class LLMRequestError(LLMError):
    """요청 형식·모델·문맥 길이 문제처럼 재시도하면 안 되는 오류."""


class LLMCallLimitError(LLMError):
    """전송 전에 호출 예산이 소진된 오류."""

    def __init__(self, *, scope: str, limit: int, used: int):
        super().__init__("LLM 호출 상한에 도달함", attempts=0)
        self.scope = scope
        self.limit = limit
        self.used = used

    @property
    def detail(self) -> dict[str, int | str]:
        return {"scope": self.scope, "limit": self.limit, "used": self.used}


def describe_error(error: BaseException) -> str:
    """예외 연쇄를 따라가며 상태 코드와 공급자 메시지까지 한 줄로 요약함."""

    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen and len(parts) < 4:
        seen.add(id(current))
        piece = f"{type(current).__name__}: {current}".strip()
        status = getattr(current, "status_code", None)
        if status is not None:
            piece = f"{piece} (status={status})"
        parts.append(" ".join(piece.split())[:400])
        current = current.__cause__ or current.__context__
    return " <- ".join(parts)


__all__ = [
    "IndexUnavailableError",
    "LLMAuthError",
    "LLMCallLimitError",
    "LLMConfigError",
    "LLMError",
    "LLMRequestError",
    "LLMRetryableError",
    "describe_error",
]
