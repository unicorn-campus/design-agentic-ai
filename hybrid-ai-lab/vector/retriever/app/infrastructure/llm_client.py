"""3사 LLM Structured Output 호출과 재시도 정책을 캡슐화함."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, TypeVar

from pydantic import BaseModel, SecretStr

from app.application.ports import LLMPort
from app.settings import LLMConfigError, Settings


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)
ModelBuilder = Callable[..., Any]

MAX_TRANSMISSION_ATTEMPTS = 3
MAX_DEADLINE_SECONDS = 180.0
MIN_RETRY_WINDOW_SECONDS = 5.0
BACKOFF_INITIAL_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_JITTER_LOW = 0.8
BACKOFF_JITTER_HIGH = 1.2


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


@dataclass(frozen=True)
class StructuredResult:
    """LangChain include_raw 결과를 제공자와 무관한 모양으로 정규화함."""

    parsed: BaseModel | None
    raw: Any
    parsing_error: str | None
    attempts: int


class LLMCallCounter:
    """프로세스 안에서 서버 누적 전송 횟수를 원자적으로 집계함."""

    def __init__(self, limit: int):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise LLMConfigError("MAX_LLM_CALLS_TOTAL은 양의 정수여야 함")
        self.limit = limit
        self._used = 0
        self._lock = threading.Lock()

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.limit - self._used)

    def add(self, count: int) -> int:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("LLM 호출 증가량은 0 이상의 정수여야 함")
        with self._lock:
            if self._used + count > self.limit:
                raise LLMCallLimitError(scope="total", limit=self.limit, used=self._used)
            self._used += count
            return self._used


def _provider_class(provider: str) -> type:
    """선택한 제공자의 패키지만 지연 import함."""

    try:
        if provider == "groq":
            from langchain_groq import ChatGroq

            return ChatGroq
        if provider == "claude":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI
    except ImportError as error:
        raise LLMConfigError(f"{provider} LLM 패키지 설치 필요") from error
    raise LLMConfigError("LLM_PROVIDER는 groq, claude, openai 중 하나여야 함")


def _required_secret(settings: Settings, name: str) -> SecretStr:
    value = settings.get(name)
    if not isinstance(value, SecretStr) or not value.get_secret_value().strip():
        raise LLMConfigError(f"{name} 설정 필요")
    return value


def _required_text(settings: Settings, name: str) -> str:
    value = settings.get(name)
    if not isinstance(value, str) or not value.strip():
        raise LLMConfigError(f"{name} 설정 필요")
    return value.strip()


def create_chat_model(
    settings: Settings,
    *,
    max_tokens: int,
    timeout: float | None = None,
    provider_classes: Mapping[str, type] | None = None,
) -> Any:
    """네트워크 요청 없이 선택한 LangChain 채팅 클라이언트를 생성함."""

    provider = _required_text(settings, "LLM_PROVIDER").lower()
    if provider not in {"groq", "claude", "openai"}:
        raise LLMConfigError("LLM_PROVIDER는 groq, claude, openai 중 하나여야 함")

    names = {
        "groq": ("GROQ_API_KEY", "GROQ_MODEL"),
        "claude": ("CLAUDE_API_KEY", "CLAUDE_MODEL"),
        "openai": ("OPENAI_API_KEY", "OPENAI_MODEL"),
    }
    key_name, model_name = names[provider]
    api_key = _required_secret(settings, key_name)
    model = _required_text(settings, model_name)
    client_type = (
        dict(provider_classes).get(provider)
        if provider_classes is not None
        else _provider_class(provider)
    )
    if client_type is None:
        raise LLMConfigError(f"{provider} LLM 클라이언트 구현이 없음")

    # client_type은 위에서 만들어진 ChatOpenAI, ChatAnthropic, ChatGroq 중 하나임
    return client_type(
        model=model,
        api_key=api_key,
        timeout=float(timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS),
        max_retries=0,
        max_tokens=max_tokens,
    )


def _status_code(error: BaseException) -> int | None:
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def classify_llm_error(error: BaseException) -> LLMError:
    """SDK 종류를 import하지 않고 상태 코드·공통 속성·이름 순으로 분류함."""

    if isinstance(error, LLMError):
        return error
    status = _status_code(error)
    if status in {401, 403}:
        return LLMAuthError("LLM 인증 또는 권한 확인 필요", status_code=status)
    if status == 408 or status == 429 or (status is not None and status >= 500):
        return LLMRetryableError("LLM 일시 장애", status_code=status)
    if status is not None and 400 <= status < 500:
        return LLMRequestError("LLM 요청 확인 필요", status_code=status)

    if getattr(error, "is_retryable", False) is True:
        return LLMRetryableError("LLM 일시 장애")

    names = " ".join(type_.__name__.lower() for type_ in type(error).__mro__)
    if "authentication" in names or "permissiondenied" in names:
        return LLMAuthError("LLM 인증 또는 권한 확인 필요")
    if any(token in names for token in ("badrequest", "notfound", "contextoverflow", "unprocessable")):
        return LLMRequestError("LLM 요청 확인 필요")
    if any(token in names for token in ("ratelimit", "connection", "connecterror", "timeout")):
        return LLMRetryableError("LLM 일시 장애")
    return LLMRequestError("LLM 요청 처리 실패")


def _parsing_error_text(error: Any) -> str | None:
    if error is None:
        return None
    return f"{type(error).__name__}: structured output parsing failed"


class LangChainLLMClient(LLMPort):
    """자체 3시도·180초 마감 안에서 Structured Output을 호출함."""

    def __init__(
        self,
        settings: Settings,
        *,
        model_builder: ModelBuilder = create_chat_model,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        uniform: Callable[[float, float], float] = random.uniform,
    ):
        self.settings = settings
        self._model_builder = model_builder
        self._monotonic = monotonic
        self._sleep = sleeper
        self._uniform = uniform

    def complete_structured(
        self,
        system: str,
        user: str,
        schema: type[StructuredModel],
        *,
        max_tokens: int,
        deadline_seconds: float | None = None,
        max_attempts: int = MAX_TRANSMISSION_ATTEMPTS,
    ) -> StructuredResult:
        """전송 시도 횟수를 결과 또는 예외의 attempts에 항상 기록함."""

        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
            raise LLMConfigError("max_attempts는 정수여야 함")
        if max_attempts <= 0:
            raise LLMCallLimitError(scope="request", limit=0, used=0)
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            raise LLMConfigError("max_tokens는 양의 정수여야 함")
        
        allowed_attempts = min(MAX_TRANSMISSION_ATTEMPTS, int(max_attempts))
        timeout = float(self.settings.LLM_TIMEOUT_SECONDS)
        hard_budget = min(timeout * MAX_TRANSMISSION_ATTEMPTS, MAX_DEADLINE_SECONDS)
        if deadline_seconds is not None:
            hard_budget = min(hard_budget, max(0.0, float(deadline_seconds)))
        deadline = self._monotonic() + hard_budget
        last_retryable: LLMRetryableError | None = None

        for attempt in range(1, allowed_attempts + 1):
            remaining = deadline - self._monotonic()
            if remaining < MIN_RETRY_WINDOW_SECONDS:
                break
            attempt_timeout = min(timeout, remaining)
            try:
                model = self._model_builder(
                    self.settings,
                    max_tokens=max_tokens,
                    timeout=attempt_timeout,
                )
                kwargs: dict[str, Any] = {
                    "method": "json_schema",
                     # 이 파라미터가 true라서 결과는 schema 타입이 아니라 아래와 같이 리턴됨
                     # { "raw": {모델의 원본 메시지}, "parsed": {schema타입 결과}, parsing_error: {파싱오류} }
                    "include_raw": True,   
                }
                if self.settings.LLM_PROVIDER in {"groq", "openai"}:
                    kwargs["strict"] = True
                runnable = model.with_structured_output(schema, **kwargs)
            except LLMConfigError:
                raise
            except Exception as error:
                classified = classify_llm_error(error)
                classified.attempts = 0
                raise classified from error
            
            try:
                output = runnable.invoke([("system", system), ("human", user)])
                if not isinstance(output, Mapping):
                    output = {"parsed": output, "raw": output, "parsing_error": None}
                parsed = output.get("parsed")
                parsing_error = output.get("parsing_error")
                try:
                    parsed_model = None if parsed is None else schema.model_validate(parsed)
                except Exception as error:
                    parsed_model = None
                    parsing_error = error
                    
                return StructuredResult(
                    parsed=parsed_model,
                    raw=output.get("raw"),
                    parsing_error=_parsing_error_text(parsing_error),
                    attempts=attempt,
                )
            except Exception as error:
                classified = classify_llm_error(error)
                classified.attempts = attempt
                if not isinstance(classified, LLMRetryableError):
                    raise classified from error
                last_retryable = classified
                if attempt >= allowed_attempts:
                    break
                delay = (
                    BACKOFF_INITIAL_SECONDS
                    * BACKOFF_MULTIPLIER ** (attempt - 1)
                    * self._uniform(BACKOFF_JITTER_LOW, BACKOFF_JITTER_HIGH)
                )
                if deadline - self._monotonic() - delay < MIN_RETRY_WINDOW_SECONDS:
                    break
                self._sleep(delay)

        if last_retryable is not None:
            raise last_retryable
        raise LLMRetryableError("LLM 호출 마감 시간이 부족함", attempts=0)


__all__ = [
    "LLMAuthError",
    "LLMCallCounter",
    "LLMCallLimitError",
    "LLMConfigError",
    "LLMError",
    "LLMRequestError",
    "LLMRetryableError",
    "LangChainLLMClient",
    "StructuredResult",
    "classify_llm_error",
    "create_chat_model",
]
