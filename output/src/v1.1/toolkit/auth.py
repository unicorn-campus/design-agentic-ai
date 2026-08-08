"""인증 자격을 한 겹 감싸 **바깥에서 부르는 이름을 하나로** 둠.

자격을 어디에 두고 언제 갱신하는지는 이 파일과 어댑터 안에서만 알게 함.
자격 값은 `headers()`가 만든 사전 안에서만 살고, 로그 · 오류 메시지 · 프롬프트로 나가지 않음.

용어 1줄 — **최소 권한** = 그 커넥터가 실제로 쓰는 동작만 요청하고 넓은 범위를 편의로 받지 않는 원칙임.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .errors import ConnectorNotConfigured
from .settings import EndpointConfig, ToolSettings

__all__ = [
    "Credential",
    "ApiKeyCredential",
    "ServiceAccountCredential",
    "ModelKeyCredential",
    "NoCredential",
    "OnBehalfOf",
    "CREDENTIAL_ENV_FIELD",
    "REQUESTED_SCOPES",
    "build_credential",
]


@runtime_checkable
class Credential(Protocol):
    """자격 1개. `headers()`만 바깥으로 내놓고 값 자체는 절대 돌려주지 않음."""

    kind_label: str

    async def headers(self) -> dict[str, str]: ...

    def invalidate(self) -> None: ...

    @property
    def refreshed_count(self) -> int: ...


@dataclass(slots=True)
class OnBehalfOf:
    """누구를 대신해 부르는지. 전역 자격 하나로 모든 사용자의 일을 처리하지 않게 인자로 받음.

    ④가 회원 식별자 칸을 두지 않은 커넥터가 있어(`R-10` 3-10절) **승인 증거 식별자**를 주체로 씀.
    이 값은 감사 기록에만 남고 바깥 요청 본문에는 ④가 정한 키로만 실림.
    """

    subject_kind: str
    subject_id: str

    def as_record(self) -> dict[str, str]:
        return {"on_behalf_of_kind": self.subject_kind, "on_behalf_of_id": self.subject_id}


@dataclass(slots=True)
class ApiKeyCredential:
    """제공자가 준 열쇠 1개를 헤더에 실음. 만료가 없어 갱신은 설정 재읽기임."""

    connector_id: str
    settings: ToolSettings
    settings_field: str
    header_name: str
    kind_label: str = "API 키"
    _cached: str | None = None
    _refreshed: int = 0

    async def headers(self) -> dict[str, str]:
        if self._cached is None:
            self._cached = self.settings.secret(self.settings_field, self.connector_id)
        return {self.header_name: self._cached}

    def invalidate(self) -> None:
        """인증 오류를 만나면 캐시를 버림. 다음 시도가 설정에서 다시 읽음(만료 전 갱신에 해당)."""
        self._cached = None
        self._refreshed += 1

    @property
    def refreshed_count(self) -> int:
        return self._refreshed


@dataclass(slots=True)
class ServiceAccountCredential:
    """가맹점 식별자 + 시크릿 2항목을 함께 싣는 자격(⑦ K-12)."""

    connector_id: str
    settings: ToolSettings
    id_header: str
    secret_header: str
    kind_label: str = "서비스 자격"
    _cached: dict[str, str] | None = None
    _refreshed: int = 0

    async def headers(self) -> dict[str, str]:
        if self._cached is None:
            self._cached = {
                self.id_header: self.settings.secret("pg_merchant_id", self.connector_id),
                self.secret_header: self.settings.secret(
                    "pg_api_secret", self.connector_id
                ),
            }
        return dict(self._cached)

    def invalidate(self) -> None:
        self._cached = None
        self._refreshed += 1

    @property
    def refreshed_count(self) -> int:
        return self._refreshed


@dataclass(slots=True)
class NoCredential:
    """대역이 쓰는 자리. 자격이 없고 헤더도 없음 — 대역은 아무 곳에도 붙지 않으므로 필요 없음."""

    connector_id: str
    kind_label: str = "자격 없음(대역)"
    _refreshed: int = 0

    async def headers(self) -> dict[str, str]:
        return {}

    def invalidate(self) -> None:
        self._refreshed += 1

    @property
    def refreshed_count(self) -> int:
        return self._refreshed


@dataclass(slots=True)
class ModelKeyCredential:
    """모델 API 열쇠. 어댑터(`common.model_client`)가 이미 열쇠를 물고 있어 헤더가 비어 있음."""

    connector_id: str
    kind_label: str = "API 키"
    _refreshed: int = 0

    async def headers(self) -> dict[str, str]:
        return {}

    def invalidate(self) -> None:
        self._refreshed += 1

    @property
    def refreshed_count(self) -> int:
        return self._refreshed


# 커넥터 → 설정 필드 이름(=⑦ 비밀값 항목). 값이 아니라 **이름**만 적음.
CREDENTIAL_ENV_FIELD: Mapping[str, str] = {
    "C-2": "(common) llm_api_key",
    "C-3": "(common) llm_api_key",
    "C-4": "map_api_key",
    "C-7": "weather_api_key",
    "C-8": "mfds_api_key",
    "C-9": "pg_merchant_id + pg_api_secret",
    "C-12": "pg_merchant_id + pg_api_secret",
}

# 최소 권한 — 그 커넥터가 실제로 쓰는 동작만 적음. 제공자의 실제 scope 문자열은 `[확인필요]`임.
REQUESTED_SCOPES: Mapping[str, tuple[str, ...]] = {
    "C-2": ("model.messages.create",),
    "C-3": ("model.embedding.create",),
    "C-4": ("places.nearby.read",),
    "C-7": ("weather.current.read",),
    "C-8": ("business_status.read",),
    "C-9": ("billing.subscription.register",),
    "C-12": ("billing.subscription.stop",),
}


def build_credential(
    connector_id: str,
    settings: ToolSettings,
    endpoint: EndpointConfig | None,
) -> Credential:
    """커넥터마다 자격을 한 종류만 만듦. 헤더 이름도 설정에서 옴."""
    if connector_id in ("C-2", "C-3"):
        return ModelKeyCredential(connector_id=connector_id)
    if endpoint is None:
        raise ConnectorNotConfigured(f"{connector_id}의 주소 설정이 없어 자격을 만들 수 없음")
    if connector_id in ("C-9", "C-12"):
        if not endpoint.auth_header or not endpoint.secondary_auth_header:
            raise ConnectorNotConfigured(
                f"{connector_id}: 서비스 자격 헤더 이름 2개가 설정에 없음"
                " — 코드에 박지 않으므로 여기서 멈춤"
            )
        return ServiceAccountCredential(
            connector_id=connector_id,
            settings=settings,
            id_header=endpoint.auth_header,
            secret_header=endpoint.secondary_auth_header,
        )
    field_name = CREDENTIAL_ENV_FIELD.get(connector_id)
    if field_name is None or not endpoint.auth_header:
        raise ConnectorNotConfigured(
            f"{connector_id}: 자격 항목 또는 인증 헤더 이름이 설정에 없음"
        )
    return ApiKeyCredential(
        connector_id=connector_id,
        settings=settings,
        settings_field=field_name,
        header_name=endpoint.auth_header,
    )
