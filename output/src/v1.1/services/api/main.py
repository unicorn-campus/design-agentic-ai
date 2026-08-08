"""FastAPI REST·SSE 진입점."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas import (
    ErrorBody,
    InsightResponse,
    MealRecordRequest,
    MealRecordResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    RecommendationRequest,
    RecommendationResponse,
    SubscriptionRequest,
    SubscriptionResponse,
)
from .service import ApprovalRequired, DemoLunchPickService


def _correlation_id(request: Request) -> str:
    return request.headers.get("x-correlation-id") or uuid.uuid4().hex


def _error(request: Request, code: str, message: str, http_status: int) -> JSONResponse:
    body = ErrorBody(code=code, message=message, correlation_id=_correlation_id(request))
    return JSONResponse(status_code=http_status, content=body.model_dump(mode="json"))


def create_app(service: DemoLunchPickService | None = None) -> FastAPI:
    runtime_service = service or DemoLunchPickService()
    cors_origins = [
        origin.strip()
        for origin in os.getenv("LUNCHPICK_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.ready = True
        yield
        app.state.ready = False

    app = FastAPI(
        title="LunchPick API",
        version="1.1.0",
        description="런치픽 추천·이력·구독 프로토타입 REST/SSE API",
        lifespan=lifespan,
    )
    app.state.service = runtime_service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["content-type", "x-correlation-id"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        del exc
        return _error(request, "invalid_request", "입력값 형식이 올바르지 않음", status.HTTP_422_UNPROCESSABLE_ENTITY)

    @app.exception_handler(ApprovalRequired)
    async def approval_handler(request: Request, exc: ApprovalRequired) -> JSONResponse:
        return _error(request, "approval_required", str(exc), status.HTTP_409_CONFLICT)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(request, "http_error", str(exc.detail), exc.status_code)

    router = APIRouter(prefix="/api/v1")

    @app.get("/health", tags=["operations"])
    async def health(request: Request) -> dict[str, str]:
        return {"status": "ok" if request.app.state.ready else "starting", "version": "1.1.0"}

    @router.post("/recommendations", response_model=RecommendationResponse)
    async def recommendations(request: Request, payload: RecommendationRequest) -> RecommendationResponse:
        return await request.app.state.service.recommend(payload, _correlation_id(request))

    @router.post("/recommendations/stream", response_class=StreamingResponse)
    async def recommendation_stream(request: Request, payload: RecommendationRequest) -> StreamingResponse:
        result = await request.app.state.service.recommend(payload, _correlation_id(request))

        async def events() -> AsyncIterator[str]:
            yield "event: status\ndata: {\"stage\":\"started\"}\n\n"
            for card in result.cards:
                if await request.is_disconnected():
                    return
                data = json.dumps(card.model_dump(mode="json"), ensure_ascii=False)
                yield f"event: recommendation\ndata: {data}\n\n"
                await asyncio.sleep(0)
            yield f"event: complete\ndata: {json.dumps({'correlation_id': result.correlation_id})}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @router.post("/meals", response_model=MealRecordResponse, status_code=status.HTTP_201_CREATED)
    async def meals(request: Request, payload: MealRecordRequest) -> MealRecordResponse:
        return await request.app.state.service.record_meal(payload)

    @router.get("/profile", response_model=ProfileResponse)
    async def profile(request: Request) -> ProfileResponse:
        return await request.app.state.service.profile()

    @router.patch("/profile", response_model=ProfileResponse)
    async def update_profile(request: Request, payload: ProfileUpdateRequest) -> ProfileResponse:
        return await request.app.state.service.update_profile(payload)

    @router.get("/insights", response_model=InsightResponse)
    async def insights(request: Request) -> InsightResponse:
        return await request.app.state.service.insights()

    @router.post("/subscriptions", response_model=SubscriptionResponse)
    async def subscribe(request: Request, payload: SubscriptionRequest) -> SubscriptionResponse:
        return await request.app.state.service.subscribe(payload)

    @router.post("/subscriptions/cancel", response_model=SubscriptionResponse)
    async def cancel_subscription(request: Request, payload: SubscriptionRequest) -> SubscriptionResponse:
        return await request.app.state.service.subscribe(payload, cancel=True)

    app.include_router(router)
    return app


app = create_app()
