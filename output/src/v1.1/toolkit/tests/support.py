"""시험 도우미 — 바깥을 부르는 자리를 전부 대역으로 갈아 끼움.

실제 주소로 나가는 시험은 이 파일을 쓰지 않고 `live_call` 표식으로 갈라 둠(D-07).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from common.budget import now_ms
from toolkit.runner import CallContext

__all__ = ["RequestSpy", "spy_client_factory", "context_for", "always"]


@dataclass(slots=True)
class RequestSpy:
    """바깥으로 나간 요청을 세는 자리. 주소와 헤더 이름을 시험이 직접 확인함."""

    urls: list[str] = field(default_factory=list)
    headers: list[Mapping[str, str]] = field(default_factory=list)
    bodies: list[bytes] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.urls)


def spy_client_factory(
    spy: RequestSpy, responder: Callable[[int], httpx.Response]
) -> Callable[[str], httpx.AsyncClient]:
    """`httpx.MockTransport`로 바깥을 흉내 냄(확인일 2026-08-08 · context7로 사양 확인)."""

    def handler(request: httpx.Request) -> httpx.Response:
        spy.urls.append(str(request.url))
        spy.headers.append(dict(request.headers))
        spy.bodies.append(request.content)
        return responder(spy.count)

    def factory(base_url: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=base_url, transport=httpx.MockTransport(handler))

    return factory


def always(status_code: int, body: Mapping[str, Any] | None = None):
    """어느 시도에서든 같은 응답을 주는 응답기."""

    def responder(_attempt: int) -> httpx.Response:
        return httpx.Response(status_code, json=dict(body or {}))

    return responder


def context_for(
    *,
    completed_steps: tuple[str, ...] = (),
    approval_evidence: Mapping[str, Any] | None = None,
    request_id: str = "req-test",
    slack_ms: int = 60_000,
) -> CallContext:
    """마감선을 넉넉히 줘서 시간 상한 시험과 섞이지 않게 함."""
    return CallContext(
        deadline_at=now_ms() + slack_ms,
        completed_steps=completed_steps,
        approval_evidence=dict(approval_evidence or {}),
        request_id=request_id,
    )
