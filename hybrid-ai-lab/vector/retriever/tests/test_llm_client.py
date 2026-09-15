from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, SecretStr

from app.infrastructure.llm_client import (
    LLMAuthError,
    LLMCallCounter,
    LLMCallLimitError,
    LLMConfigError,
    LLMRequestError,
    LLMRetryableError,
    LangChainLLMClient,
    classify_llm_error,
    create_chat_model,
)
from app.settings import Settings


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str


def _settings(provider: str = "groq", **changes: Any) -> Settings:
    values = {
        "LLM_PROVIDER": provider,
        "GROQ_API_KEY": SecretStr("fake-groq-key"),
        "GROQ_MODEL": "groq-model",
        "CLAUDE_API_KEY": SecretStr("fake-claude-key"),
        "CLAUDE_MODEL": "claude-model",
        "OPENAI_API_KEY": SecretStr("fake-openai-key"),
        "OPENAI_MODEL": "openai-model",
        "LLM_TIMEOUT_SECONDS": 60.0,
    }
    values.update(changes)
    return Settings(MappingProxyType(values), MappingProxyType({}))


class FakeProvider:
    last_kwargs: dict[str, Any] = {}

    def __init__(self, **kwargs: Any):
        type(self).last_kwargs = kwargs


@pytest.mark.parametrize(
    "provider,key_name,model",
    [
        ("groq", "GROQ_API_KEY", "groq-model"),
        ("claude", "CLAUDE_API_KEY", "claude-model"),
        ("openai", "OPENAI_API_KEY", "openai-model"),
    ],
)
def test_factory_passes_secret_timeout_and_disables_sdk_retries(
    provider: str,
    key_name: str,
    model: str,
) -> None:
    client = create_chat_model(
        _settings(provider),
        max_tokens=321,
        provider_classes={provider: FakeProvider},
    )
    assert isinstance(client, FakeProvider)
    assert FakeProvider.last_kwargs["model"] == model
    assert isinstance(FakeProvider.last_kwargs["api_key"], SecretStr)
    assert FakeProvider.last_kwargs["api_key"].get_secret_value() == _settings(provider).get(
        key_name
    ).get_secret_value()
    assert FakeProvider.last_kwargs["timeout"] == 60.0
    assert FakeProvider.last_kwargs["max_retries"] == 0
    assert FakeProvider.last_kwargs["max_tokens"] == 321


def test_missing_key_or_model_never_contains_secret_value() -> None:
    secret = "never-show-this-model-test-secret"
    with pytest.raises(LLMConfigError) as missing_key:
        create_chat_model(
            _settings("groq", GROQ_API_KEY=None),
            max_tokens=10,
            provider_classes={"groq": FakeProvider},
        )
    assert "GROQ_API_KEY" in str(missing_key.value)
    assert secret not in str(missing_key.value)

    with pytest.raises(LLMConfigError) as missing_model:
        create_chat_model(
            _settings("openai", OPENAI_API_KEY=SecretStr(secret), OPENAI_MODEL=None),
            max_tokens=10,
            provider_classes={"openai": FakeProvider},
        )
    assert "OPENAI_MODEL" in str(missing_model.value)
    assert secret not in str(missing_model.value)


class StatusError(RuntimeError):
    def __init__(self, status_code: int):
        super().__init__("provider body must not be copied")
        self.status_code = status_code


@pytest.mark.parametrize(
    "error,expected",
    [
        (StatusError(401), LLMAuthError),
        (StatusError(403), LLMAuthError),
        (StatusError(400), LLMRequestError),
        (StatusError(404), LLMRequestError),
        (StatusError(422), LLMRequestError),
        (StatusError(429), LLMRetryableError),
        (StatusError(503), LLMRetryableError),
        (TimeoutError(), LLMRetryableError),
        (ValueError(), LLMRequestError),
    ],
)
def test_error_classification(error: BaseException, expected: type) -> None:
    classified = classify_llm_error(error)
    assert isinstance(classified, expected)
    assert "provider body" not in str(classified)


@dataclass
class Script:
    outcomes: list[Any]
    structured_kwargs: list[dict[str, Any]]
    messages: list[Any]


class FakeRunnable:
    def __init__(self, script: Script, advance=None):
        self.script = script
        self.advance = advance

    def invoke(self, messages):
        self.script.messages.append(messages)
        outcome = self.script.outcomes.pop(0)
        if self.advance is not None:
            self.advance(outcome)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeModel:
    def __init__(self, script: Script, advance=None):
        self.script = script
        self.advance = advance

    def with_structured_output(self, schema, **kwargs):
        assert schema is Draft
        self.script.structured_kwargs.append(kwargs)
        return FakeRunnable(self.script, self.advance)


def test_structured_output_contract_and_strict_provider_options() -> None:
    script = Script(
        [{"parsed": {"answer": "ok"}, "raw": "raw", "parsing_error": None}],
        [],
        [],
    )
    client = LangChainLLMClient(
        _settings("groq"),
        model_builder=lambda *args, **kwargs: FakeModel(script),
    )
    result = client.complete_structured("system", "user", Draft, max_tokens=10)
    assert result.parsed == Draft(answer="ok")
    assert result.raw == "raw"
    assert result.parsing_error is None
    assert result.attempts == 1
    assert script.structured_kwargs == [
        {"method": "json_schema", "include_raw": True, "strict": True}
    ]
    assert script.messages == [[("system", "system"), ("human", "user")]]


def test_claude_does_not_receive_strict_option() -> None:
    script = Script([{"parsed": {"answer": "ok"}}], [], [])
    client = LangChainLLMClient(
        _settings("claude"),
        model_builder=lambda *args, **kwargs: FakeModel(script),
    )
    client.complete_structured("s", "u", Draft, max_tokens=10)
    assert "strict" not in script.structured_kwargs[0]


def test_parsing_failure_is_data_not_transport_exception() -> None:
    script = Script([{"parsed": {"unexpected": True}, "raw": "raw"}], [], [])
    client = LangChainLLMClient(
        _settings(),
        model_builder=lambda *args, **kwargs: FakeModel(script),
    )
    result = client.complete_structured("s", "u", Draft, max_tokens=10)
    assert result.parsed is None
    assert result.parsing_error == "ValidationError: structured output parsing failed"
    assert result.attempts == 1


def test_retry_deadline_shrinks_last_timeout_and_counts_transmissions() -> None:
    now = [0.0]
    timeouts: list[float] = []
    sleeps: list[float] = []
    script = Script(
        [StatusError(503), StatusError(429), {"parsed": {"answer": "ok"}}],
        [],
        [],
    )

    def advance(outcome: Any) -> None:
        if isinstance(outcome, BaseException):
            now[0] += 59.0

    def builder(*args, **kwargs):
        timeouts.append(kwargs["timeout"])
        return FakeModel(script, advance)

    def sleeper(delay: float) -> None:
        sleeps.append(delay)
        now[0] += delay

    client = LangChainLLMClient(
        _settings(),
        model_builder=builder,
        monotonic=lambda: now[0],
        sleeper=sleeper,
        uniform=lambda low, high: 1.0,
    )
    result = client.complete_structured("s", "u", Draft, max_tokens=10)
    assert result.attempts == 3
    assert timeouts == [60.0, 60.0, 59.0]
    assert sleeps == [1.0, 2.0]
    assert now[0] <= 180.0


def test_max_attempts_caps_actual_transmissions() -> None:
    script = Script([StatusError(503), StatusError(503), StatusError(503)], [], [])
    client = LangChainLLMClient(
        _settings(),
        model_builder=lambda *args, **kwargs: FakeModel(script),
        sleeper=lambda delay: None,
        uniform=lambda low, high: 1.0,
    )
    with pytest.raises(LLMRetryableError) as caught:
        client.complete_structured("s", "u", Draft, max_tokens=10, max_attempts=2)
    assert caught.value.attempts == 2
    assert len(script.outcomes) == 1


def test_zero_attempt_budget_stops_before_model_creation() -> None:
    built = []
    client = LangChainLLMClient(
        _settings(),
        model_builder=lambda *args, **kwargs: built.append(True),
    )
    with pytest.raises(LLMCallLimitError):
        client.complete_structured("s", "u", Draft, max_tokens=10, max_attempts=0)
    assert built == []


def test_missing_key_during_completion_remains_config_error_and_counts_zero() -> None:
    client = LangChainLLMClient(_settings(GROQ_API_KEY=None))
    with pytest.raises(LLMConfigError) as caught:
        client.complete_structured("s", "u", Draft, max_tokens=10)
    assert "GROQ_API_KEY" in str(caught.value)
    assert not hasattr(caught.value, "attempts")


def test_non_retryable_error_is_sent_once_and_preserves_cause() -> None:
    original = StatusError(401)
    script = Script([original, {"parsed": {"answer": "must not run"}}], [], [])
    client = LangChainLLMClient(
        _settings(),
        model_builder=lambda *args, **kwargs: FakeModel(script),
    )
    with pytest.raises(LLMAuthError) as caught:
        client.complete_structured("s", "u", Draft, max_tokens=10)
    assert caught.value.attempts == 1
    assert caught.value.__cause__ is original
    assert len(script.outcomes) == 1


def test_counter_enforces_total_limit_without_overcount() -> None:
    counter = LLMCallCounter(2)
    assert counter.add(1) == 1
    assert counter.remaining == 1
    with pytest.raises(LLMCallLimitError) as caught:
        counter.add(2)
    assert caught.value.detail == {"scope": "total", "limit": 2, "used": 1}
    assert counter.used == 1
