from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .settings import RuntimeSettings


class ModelClientAdapter:
    def __init__(
        self,
        settings: RuntimeSettings,
        initializer: Callable[..., Any] | None = None,
    ) -> None:
        if initializer is None:
            from langchain.chat_models import init_chat_model

            initializer = init_chat_model
        self._settings = settings
        self._initializer = initializer

    def create(self) -> Any:
        settings = self._settings
        optional: dict[str, Any] = {}
        if settings.llm_temperature is not None:
            optional["temperature"] = settings.llm_temperature
        if settings.llm_max_tokens is not None:
            optional["max_tokens"] = settings.llm_max_tokens
        return self._initializer(
            model=settings.llm_model,
            model_provider=settings.llm_provider,
            api_key=settings.llm_api_key.get_secret_value(),
            reasoning=settings.llm_reasoning_enabled,
            **optional,
        )
