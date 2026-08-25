from __future__ import annotations

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConnectorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HELP_DESK_",
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    connector_mode: Literal["mock", "real"] = "mock"
    c_a1_base_url: str | None = None
    c_a2_base_url: str | None = None
    c_a3_base_url: str | None = None
    c_a4_base_url: str | None = None
    c_a5_base_url: str | None = None
    c_a1_credential: SecretStr | None = None
    c_a2_credential: SecretStr | None = None
    c_a3_credential: SecretStr | None = None
    c_a4_credential: SecretStr | None = None
    c_a5_credential: SecretStr | None = None
    idempotency_sqlite_uri: str | None = None
    idempotency_ttl_seconds: int
    connector_jitter_ratio: float

    def base_url(self, connector_id: str) -> str:
        value = getattr(self, f"{connector_id.lower().replace('-', '_')}_base_url")
        if not value:
            raise ValueError(f"{connector_id} 실물 베이스 URL 설정이 없음")
        return value
