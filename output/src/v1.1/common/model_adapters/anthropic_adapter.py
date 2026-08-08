"""Anthropic 벤더 어댑터. 모델 이름·사고 설정·출력 상한은 전부 `spec`으로 주입됨."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic

from ..model_client import ModelCallSpec, ModelClient, ModelReply

__all__ = ["AnthropicAdapter", "build"]


@dataclass(slots=True)
class AnthropicAdapter(ModelClient):
    spec: ModelCallSpec
    client: AsyncAnthropic

    async def complete(
        self,
        *,
        system: str | None,
        messages: Sequence[dict[str, Any]],
        output_schema: dict[str, Any] | None = None,
    ) -> ModelReply:
        payload: dict[str, Any] = {
            "model": self.spec.model,
            "messages": list(messages),
        }
        if self.spec.max_output_tokens is not None:
            payload["max_tokens"] = self.spec.max_output_tokens
        if system is not None:
            payload["system"] = system
        if self.spec.thinking is not None:
            payload["thinking"] = {
                "type": "disabled" if self.spec.thinking_disabled else "adaptive"
            }
        output_config: dict[str, Any] = {}
        if self.spec.effort is not None:
            output_config["effort"] = self.spec.effort
        if output_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": output_schema}
        if output_config:
            payload["output_config"] = output_config

        response = await self.client.messages.create(**payload)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(response, "usage", None)
        return ModelReply(
            text=text,
            call_id=response.id,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            raw=response,
        )


def build(spec: ModelCallSpec) -> ModelClient:
    kwargs: dict[str, Any] = {"api_key": spec.api_key}
    if spec.base_url is not None:
        kwargs["base_url"] = spec.base_url
    return AnthropicAdapter(spec=spec, client=AsyncAnthropic(**kwargs))
