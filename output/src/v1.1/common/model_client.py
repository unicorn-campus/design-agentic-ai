"""모델 클라이언트 어댑터. 바깥에서 부르는 이름은 하나이고 벤더 차이는 어댑터가 흡수함."""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .config import Settings

__all__ = [
    "ModelCallSpec",
    "ModelReply",
    "ModelClient",
    "ModelAdapterFactory",
    "UnsupportedProvider",
    "InvalidModelCallSpec",
    "ADAPTER_MODULE_TEMPLATE",
    "ADAPTER_FACTORY_ATTR",
    "spec_from_settings",
    "build_model_client",
]

ADAPTER_MODULE_TEMPLATE = "common.model_adapters.{provider}_adapter"
ADAPTER_FACTORY_ATTR = "build"

_EFFORT_FORBIDDING_THINKING_OFF = frozenset({"xhigh", "max"})
_THINKING_OFF = "off"
_THINKING_ADAPTIVE = "adaptive"


class UnsupportedProvider(RuntimeError):
    """설정이 가리키는 벤더 어댑터가 없음."""


class InvalidModelCallSpec(ValueError):
    """벤더가 받지 않는 인자 조합임. 부르기 전에 막음."""


@dataclass(frozen=True, slots=True)
class ModelCallSpec:
    """④ 「사용 모델」 칸을 그대로 옮겨 담는 그릇. 값은 설정에서 옴."""

    model: str
    api_key: str
    thinking: str | None = None
    effort: str | None = None
    max_output_tokens: int | None = None
    base_url: str | None = None

    def __post_init__(self) -> None:
        if self.thinking is not None and self.thinking not in (
            _THINKING_OFF,
            _THINKING_ADAPTIVE,
        ):
            raise InvalidModelCallSpec(
                f"사고 설정은 {_THINKING_OFF} 또는 {_THINKING_ADAPTIVE}만 받음: {self.thinking!r}"
            )
        if (
            self.thinking == _THINKING_OFF
            and self.effort is not None
            and self.effort in _EFFORT_FORBIDDING_THINKING_OFF
        ):
            raise InvalidModelCallSpec(
                f"사고를 끈 상태에서는 사고 깊이 {self.effort!r}를 쓸 수 없음"
            )

    @property
    def thinking_disabled(self) -> bool:
        return self.thinking == _THINKING_OFF


@dataclass(frozen=True, slots=True)
class ModelReply:
    text: str
    call_id: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw: Any | None = None


@runtime_checkable
class ModelClient(Protocol):
    """④에 `모델 미사용`으로 적힌 담당자는 이걸 쓰지 않고 순수 함수로 둠."""

    async def complete(
        self,
        *,
        system: str | None,
        messages: Sequence[dict[str, Any]],
        output_schema: dict[str, Any] | None = None,
    ) -> ModelReply: ...


class ModelAdapterFactory(Protocol):
    def __call__(self, spec: ModelCallSpec) -> ModelClient: ...


def spec_from_settings(settings: Settings) -> ModelCallSpec:
    return ModelCallSpec(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        thinking=settings.llm_thinking,
        effort=settings.llm_effort,
        max_output_tokens=settings.llm_max_output_tokens,
        base_url=settings.llm_base_url,
    )


def _resolve_factory(provider: str) -> ModelAdapterFactory:
    module_name = ADAPTER_MODULE_TEMPLATE.format(provider=provider)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise UnsupportedProvider(f"벤더 어댑터를 찾지 못함: {module_name}") from exc
    try:
        return getattr(module, ADAPTER_FACTORY_ATTR)
    except AttributeError as exc:
        raise UnsupportedProvider(
            f"{module_name}에 {ADAPTER_FACTORY_ATTR} 함수가 없음"
        ) from exc


def build_model_client(settings: Settings) -> ModelClient:
    """설정이 가리키는 벤더의 어댑터를 골라 만듦. 벤더 이름이 이 파일에 없음."""
    factory = _resolve_factory(settings.llm_provider)
    return factory(spec_from_settings(settings))
