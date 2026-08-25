from __future__ import annotations

import httpx


def create_http_client(base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        transport=transport,
        timeout=None,
        follow_redirects=False,
    )
