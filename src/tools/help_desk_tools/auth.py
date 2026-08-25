from __future__ import annotations

from typing import Protocol

from .errors import ConnectorError, ErrorCategory


class CredentialProvider(Protocol):
    async def should_refresh(self, acting_user_ref: str | None) -> bool: ...

    async def refresh(self, acting_user_ref: str | None) -> None: ...

    async def headers(self, acting_user_ref: str | None) -> dict[str, str]: ...


class AuthenticationManager:
    def __init__(self, provider: CredentialProvider) -> None:
        self._provider = provider

    async def request_headers(self, acting_user_ref: str | None = None) -> dict[str, str]:
        try:
            if await self._provider.should_refresh(acting_user_ref):
                await self._provider.refresh(acting_user_ref)
            return await self._provider.headers(acting_user_ref)
        except Exception as exc:
            raise ConnectorError(
                ErrorCategory.AUTHENTICATION,
                "외부 자격 갱신에 실패함",
            ) from exc

    async def refresh_after_rejection(self, acting_user_ref: str | None = None) -> None:
        try:
            await self._provider.refresh(acting_user_ref)
        except Exception as exc:
            raise ConnectorError(
                ErrorCategory.AUTHENTICATION,
                "외부 자격 갱신에 실패함",
            ) from exc
