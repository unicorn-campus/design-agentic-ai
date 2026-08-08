"""도구 계층 설정. 주소 · 자격 · 판본 · 대역 여부를 코드에 박지 않고 전부 여기서 읽음.

이름 규격은 `D-12` — `LUNCHPICK_{영역}_{항목}` · 대문자 · 밑줄.
시간 상한과 재시도 값은 여기에 없음 — ③이 주인이고 `common.config.Settings`가 읽음.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConnectorNotConfigured

__all__ = [
    "ConnectorMode",
    "EndpointConfig",
    "ToolSettings",
    "load_tool_settings",
    "get_tool_settings",
    "reset_tool_settings_cache",
]


class ConnectorMode(StrEnum):
    """대역인가 실물인가. **값의 주인은 ② 논리아키텍처 4절**이며 코드에 박지 않고 설정으로 받음."""

    LIVE = "live"
    MOCK = "mock"


class EndpointConfig(BaseModel):
    """주소 · 경로 · 판본 · 인증 헤더 이름. 전부 설정에서 옴."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: str
    path: str
    method: str = "POST"
    api_version: str | None = None
    auth_header: str | None = None
    secondary_auth_header: str | None = None
    idempotency_header: str | None = None


class ToolSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LUNCHPICK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    connector_mode: dict[str, ConnectorMode] = Field(
        description="커넥터 식별자 → 대역·실물. ② 4절 · ⑤ 「Mock·실물 구분」 값을 옮겨 담음",
    )
    connector_endpoint: dict[str, EndpointConfig] = Field(
        default_factory=dict,
        description="커넥터 식별자 → 주소·경로·판본. 실물 모드 커넥터만 있으면 됨",
    )
    connector_max_calls: dict[str, int] = Field(
        default_factory=dict,
        description="요청 1건에서 그 도구를 몇 번까지 부를 수 있나. 실제로 세는 코드는 05 몫",
    )
    idempotency_ttl_hours: int | None = Field(
        default=None,
        description="중복 방지 키 보관 기간(시간). 되묻기 확정값 24를 `.env`에 넣음",
    )

    # --- 비밀값 (⑦ 6절 항목 이름과 1:1) ------------------------------------
    map_api_key: str | None = Field(default=None, description="⑦ K-09 지도 API 키 — C-4")
    weather_api_key: str | None = Field(
        default=None, description="⑦ K-10 날씨 API 키 — C-7"
    )
    mfds_api_key: str | None = Field(
        default=None, description="⑦ K-11 식약처 공공 API 인증키 — C-8(대역 판에는 주입 안 함)"
    )
    pg_merchant_id: str | None = Field(
        default=None, description="⑦ K-12 PG 가맹점 식별자 — C-9 · C-12"
    )
    pg_api_secret: str | None = Field(
        default=None, description="⑦ K-12 PG API 시크릿 — C-9 · C-12"
    )

    # --- 읽기 도우미 -------------------------------------------------------
    def mode_of(self, connector_id: str) -> ConnectorMode:
        try:
            return self.connector_mode[connector_id]
        except KeyError as exc:
            raise ConnectorNotConfigured(
                f"{connector_id}의 대역·실물 구분이 설정에 없음"
                " — ② 4절 판정을 LUNCHPICK_CONNECTOR_MODE에 넣음"
            ) from exc

    def endpoint_of(self, connector_id: str) -> EndpointConfig:
        try:
            return self.connector_endpoint[connector_id]
        except KeyError as exc:
            raise ConnectorNotConfigured(
                f"{connector_id}의 주소가 설정에 없음 — 코드에 박지 않으므로 여기서 멈춤"
            ) from exc

    def max_calls_of(self, connector_id: str) -> int | None:
        return self.connector_max_calls.get(connector_id)

    def secret(self, field_name: str, connector_id: str) -> str:
        value = getattr(self, field_name, None)
        if not value:
            raise ConnectorNotConfigured(
                f"{connector_id}의 자격이 설정에 없음: LUNCHPICK_{field_name.upper()}"
            )
        return value


def load_tool_settings(**overrides: Any) -> ToolSettings:
    try:
        return ToolSettings(**overrides)
    except ValidationError as exc:
        raise ConnectorNotConfigured(str(exc)) from exc


@functools.lru_cache(maxsize=1)
def get_tool_settings() -> ToolSettings:
    return load_tool_settings()


def reset_tool_settings_cache() -> None:
    get_tool_settings.cache_clear()


def mode_summary(settings: ToolSettings) -> Mapping[str, str]:
    return {key: mode.value for key, mode in settings.connector_mode.items()}
