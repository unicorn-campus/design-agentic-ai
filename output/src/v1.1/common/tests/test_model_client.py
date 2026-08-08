"""모델 어댑터 시험. 바깥 호출은 전부 대역으로 바꿈."""

from __future__ import annotations

from typing import Any

import pytest

from common.config import Settings, load_settings
from common.model_client import (
    InvalidModelCallSpec,
    ModelCallSpec,
    ModelReply,
    UnsupportedProvider,
    build_model_client,
    spec_from_settings,
)


def test_spec_carries_settings_values_without_hardcoding(settings: Settings) -> None:
    spec = spec_from_settings(settings)
    assert spec.model == "test-model-id"
    assert spec.api_key == "test-key"
    assert spec.thinking is None
    assert spec.max_output_tokens is None


def test_thinking_off_with_low_effort_is_allowed() -> None:
    spec = ModelCallSpec(model="m", api_key="k", thinking="off", effort="low")
    assert spec.thinking_disabled is True


@pytest.mark.parametrize("effort", ["xhigh", "max"])
def test_thinking_off_with_deep_effort_is_rejected_before_the_call(effort: str) -> None:
    with pytest.raises(InvalidModelCallSpec):
        ModelCallSpec(model="m", api_key="k", thinking="off", effort=effort)


def test_unknown_thinking_value_is_rejected() -> None:
    with pytest.raises(InvalidModelCallSpec):
        ModelCallSpec(model="m", api_key="k", thinking="enabled")


def test_unknown_provider_raises_instead_of_falling_back(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    monkeypatch.setenv("LUNCHPICK_LLM_PROVIDER", "없는벤더")
    with pytest.raises(UnsupportedProvider):
        build_model_client(load_settings())


def test_adapter_is_chosen_by_the_provider_setting(settings: Settings) -> None:
    client = build_model_client(settings)
    assert client.spec.model == settings.llm_model


class _StubMessages:
    def __init__(self) -> None:
        self.seen: dict[str, Any] | None = None

    async def create(self, **payload: Any) -> Any:
        self.seen = payload

        class _Block:
            type = "text"
            text = "추천 3건"

        class _Usage:
            input_tokens = 11
            output_tokens = 22

        class _Response:
            id = "msg_stub"
            content = [_Block()]
            usage = _Usage()

        return _Response()


class _StubClient:
    def __init__(self) -> None:
        self.messages = _StubMessages()


async def test_adapter_maps_spec_onto_the_vendor_payload() -> None:
    from common.model_adapters.anthropic_adapter import AnthropicAdapter

    stub = _StubClient()
    spec = ModelCallSpec(
        model="test-model-id",
        api_key="k",
        thinking="off",
        effort="low",
        max_output_tokens=2048,
    )
    adapter = AnthropicAdapter(spec=spec, client=stub)  # type: ignore[arg-type]

    reply = await adapter.complete(system="너는 추천 담당임", messages=[{"role": "user", "content": "점심"}])

    assert isinstance(reply, ModelReply)
    assert reply.text == "추천 3건"
    assert reply.call_id == "msg_stub"
    assert reply.input_tokens == 11
    assert stub.messages.seen is not None
    assert stub.messages.seen["model"] == "test-model-id"
    assert stub.messages.seen["max_tokens"] == 2048
    assert stub.messages.seen["thinking"] == {"type": "disabled"}
    assert stub.messages.seen["output_config"] == {"effort": "low"}


async def test_adapter_omits_fields_that_settings_left_empty() -> None:
    from common.model_adapters.anthropic_adapter import AnthropicAdapter

    stub = _StubClient()
    adapter = AnthropicAdapter(
        spec=ModelCallSpec(model="m", api_key="k"), client=stub  # type: ignore[arg-type]
    )
    await adapter.complete(system=None, messages=[{"role": "user", "content": "x"}])

    assert stub.messages.seen is not None
    assert "thinking" not in stub.messages.seen
    assert "output_config" not in stub.messages.seen
    assert "max_tokens" not in stub.messages.seen
    assert "system" not in stub.messages.seen


async def test_adapter_passes_output_schema_as_structured_output() -> None:
    from common.model_adapters.anthropic_adapter import AnthropicAdapter

    stub = _StubClient()
    adapter = AnthropicAdapter(
        spec=ModelCallSpec(model="m", api_key="k"), client=stub  # type: ignore[arg-type]
    )
    schema = {"type": "object", "properties": {}, "additionalProperties": False}
    await adapter.complete(system=None, messages=[], output_schema=schema)

    assert stub.messages.seen is not None
    assert stub.messages.seen["output_config"]["format"] == {
        "type": "json_schema",
        "schema": schema,
    }
