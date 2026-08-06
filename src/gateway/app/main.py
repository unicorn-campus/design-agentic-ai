"""I-1 `lp-gateway` — ⑦ 2절 진입 이미지. **유일한 외부 진입 지점**.

쪼갠 이유: 전 요청이 지나므로 추천 피크 기준으로 늘리면 회원·결제 경로까지
함께 늘어남. 진입 검사(토큰 검증·요청 상한)를 한 곳에 모아 다른 이미지가
외부에 직접 열리지 않게 함(⑦ 2절 I-1).

⑦ 3절 포트: 내부 8080 · 외부 노출은 443(TLS 1.3) 1개만.
로컬 실행에서는 호스트 8080으로 매핑하고 TLS는 종단 프록시 몫으로 둠.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from lp_common.config import get_settings
from lp_common.observability import setup_logging

log = logging.getLogger("lp.gateway")
settings = get_settings("lp-gateway")

# `US:NFR-SYS-020` 진입 지점 전제 — 요청 상한을 게이트웨이에 모음
_RATE_WINDOW_SEC = 60
_RATE_MAX = 600
_hits: dict[str, list[float]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("lp-gateway")
    app.state.client = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.client.aclose()


app = FastAPI(title="런치픽 API 게이트웨이 (I-1)", lifespan=lifespan)

# 로컬 확인용 프런트(I-6 대체)가 브라우저에서 부를 수 있게 함
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8081"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def entry_checks(request: Request, call_next):
    """`S-R1` 게이트웨이 수신·인증 — 진입 검사를 한 곳에 모음."""
    if request.url.path == "/health":
        return await call_next(request)

    client_key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = [t for t in _hits.get(client_key, []) if now - t < _RATE_WINDOW_SEC]
    if len(window) >= _RATE_MAX:
        raise HTTPException(status_code=429, detail={"reason_code": "NETWORK"})
    window.append(now)
    _hits[client_key] = window

    trace_id = request.headers.get("x-trace-id") or f"T-{uuid.uuid4().hex[:12]}"
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    return response


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "lp-gateway"}


async def _proxy(request: Request, base_url: str, path: str) -> Any:
    body = await request.body()
    client: httpx.AsyncClient = request.app.state.client
    try:
        resp = await client.request(
            request.method,
            f"{base_url}{path}",
            content=body or None,
            params=dict(request.query_params),
            headers={
                "content-type": request.headers.get("content-type", "application/json"),
                "x-trace-id": request.state.trace_id,
            },
        )
    except httpx.HTTPError as exc:
        log.warning("상류 호출 실패 path=%s err=%s", path, type(exc).__name__)
        raise HTTPException(status_code=502, detail={"reason_code": "NETWORK"}) from exc
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=_safe_json(resp))
    return _safe_json(resp)


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text[:500]}


# ── 추천·이력 경로 → I-2 (인터넷에서 직접 불릴 수 없음 · ⑦ 3절) ────────────────
@app.post("/api/recommendations")
async def recommendations(request: Request) -> Any:
    return await _proxy(request, settings.recommend_base_url, "/v1/recommendations")


@app.post("/api/recommendations/reject")
async def reject(request: Request) -> Any:
    return await _proxy(request, settings.recommend_base_url, "/v1/recommendations/reject")


@app.post("/api/recommendations/refresh")
async def refresh(request: Request) -> Any:
    return await _proxy(request, settings.recommend_base_url, "/v1/recommendations/refresh")


@app.post("/api/meals")
async def meals(request: Request) -> Any:
    return await _proxy(request, settings.recommend_base_url, "/v1/meals")


@app.post("/api/feedback")
async def feedback(request: Request) -> Any:
    return await _proxy(request, settings.recommend_base_url, "/v1/feedback")


@app.post("/api/reminders/run")
async def reminders(request: Request) -> Any:
    return await _proxy(request, settings.recommend_base_url, "/v1/reminders/run")


@app.get("/api/insights/{member_ref}")
async def insights(member_ref: str, request: Request) -> Any:
    return await _proxy(request, settings.recommend_base_url, f"/v1/insights/{member_ref}")


# ── 회원 경로 → I-3 ───────────────────────────────────────────────────────────
@app.get("/api/members")
async def members(request: Request) -> Any:
    return await _proxy(request, settings.member_base_url, "/v1/members")


@app.get("/api/members/{member_ref}")
async def member_detail(member_ref: str, request: Request) -> Any:
    return await _proxy(request, settings.member_base_url, f"/v1/members/{member_ref}")


@app.post("/api/members/{member_ref}/consent")
async def member_consent(member_ref: str, request: Request) -> Any:
    return await _proxy(request, settings.member_base_url, f"/v1/members/{member_ref}/consent")
