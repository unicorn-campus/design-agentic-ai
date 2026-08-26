from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Header
from pydantic import ValidationError
from fastapi.responses import StreamingResponse
from help_desk_api import (
    ErrorBody,
    GuardrailBoundary,
    HealthBody,
    InquiryBody,
    InquiryResumeBody,
    PublicApiError,
    final_event_stream,
    install_error_handlers,
)
from help_desk_runtime.api_contracts import InquiryRequest, InquiryResponse
from help_desk_runtime.budget import RuntimeDeadline
from help_desk_workflow.contracts import InquiryResult

InquiryRunner = Callable[[InquiryRequest, RuntimeDeadline], Awaitable[InquiryResponse]]
ResumeRunner = Callable[[str, dict[str, Any]], Awaitable[InquiryResponse]]
ReadinessProbe = Callable[[], Awaitable[bool]]


def create_app(
    inquiry_runner: InquiryRunner | None = None,
    resume_runner: ResumeRunner | None = None,
    boundary: GuardrailBoundary | None = None,
    readiness_probe: ReadinessProbe | None = None,
    budget_ms: int | None = None,
) -> FastAPI:
    app = FastAPI(title="Help Desk Inquiry API", version="0.1.0")
    install_error_handlers(app)

    def require_boundary() -> GuardrailBoundary:
        if boundary is None:
            raise PublicApiError(503, "service_not_ready", "서비스 준비가 완료되지 않음")
        return boundary

    @app.post(
        "/v1/inquiries",
        response_model=InquiryResult,
        response_model_exclude_none=True,
        responses={400: {"model": ErrorBody}, 503: {"model": ErrorBody}},
    )
    async def submit_inquiry(
        body: InquiryBody,
        accept: str | None = Header(default=None),
    ) -> Any:
        if inquiry_runner is None or budget_ms is None:
            raise PublicApiError(503, "service_not_ready", "서비스 준비가 완료되지 않음")
        guard = require_boundary()
        guard.inspect_input("IN-W1-R2", body.inquiry_text, "받는 즉시")
        deadline = RuntimeDeadline.from_budget_ms(budget_ms)
        result = await inquiry_runner(body.model_dump(), deadline)
        validated = InquiryResult.model_validate(result).model_dump(exclude_none=True)
        if accept and "text/event-stream" in accept:
            truncated = (
                validated.get("result_type") == "safe_stop"
                and validated.get("request_status") == "failed"
            )
            return StreamingResponse(
                final_event_stream(
                    validated,
                    lambda value: guard.sanitize_output("W-1", value),
                    truncated=truncated,
                ),
                media_type="text/event-stream",
                headers={"X-Result-Completeness": "truncated" if truncated else "complete"},
            )
        safe = guard.sanitize_output("W-1", validated)
        return InquiryResult.model_validate(safe)

    @app.post(
        "/v1/inquiries/{request_id}/decisions",
        response_model=InquiryResult,
        response_model_exclude_none=True,
    )
    async def resume_inquiry(request_id: str, body: InquiryResumeBody) -> InquiryResult:
        if resume_runner is None:
            raise PublicApiError(503, "service_not_ready", "서비스 준비가 완료되지 않음")
        guard = require_boundary()
        guard.inspect_input("IN-W1-R9", body.model_dump(), "프롬프트 조립 직전")
        result = await resume_runner(request_id, body.model_dump(exclude_none=True))
        safe = guard.sanitize_output("W-1", result)
        return InquiryResult.model_validate(safe)

    @app.get("/health/live", response_model=HealthBody)
    async def live() -> HealthBody:
        return HealthBody(status="ok")

    @app.get("/health/ready", response_model=HealthBody)
    async def ready() -> HealthBody:
        is_ready = False if readiness_probe is None else await readiness_probe()
        if not is_ready:
            raise PublicApiError(503, "service_not_ready", "서비스 준비가 완료되지 않음")
        return HealthBody(status="ok")

    return app


def create_runtime_app() -> FastAPI:
    """설정을 읽어 W-1 그래프까지 연결된 앱을 만듦.

    체크포인트 저장소는 비동기 문맥 관리자라서 lifespan 안에서 열고 닫음.
    실행기는 시작 시점에 만들어져 `holder`에 담기며, 그 전에 들어온 요청은
    준비 미완료로 응답함.
    """
    from contextlib import asynccontextmanager

    from help_desk_api import build_boundary
    from help_desk_runtime.checkpoint import create_checkpointer
    from help_desk_runtime.settings import RuntimeSettings
    from help_desk_tools import ConnectorSettings

    from .runtime import InquiryRuntime

    settings = RuntimeSettings()
    connector_settings = ConnectorSettings()
    boundary = build_boundary(settings)
    holder: dict[str, InquiryRuntime] = {}

    def require_runtime() -> InquiryRuntime:
        runtime = holder.get("runtime")
        if runtime is None:
            raise PublicApiError(503, "service_not_ready", "서비스 준비가 완료되지 않음")
        return runtime

    async def run_inquiry(payload: Any, deadline: RuntimeDeadline) -> Any:
        return await require_runtime().run(payload, deadline)

    async def resume_inquiry(request_id: str, decision: dict[str, Any]) -> Any:
        try:
            return await require_runtime().resume(request_id, decision)
        except KeyError as error:
            raise PublicApiError(
                404, "approval_not_found", "승인 대기 중인 요청이 없음"
            ) from error

    async def probe_ready() -> bool:
        runtime = holder.get("runtime")
        return runtime is not None and await runtime.ready()

    runtime_app = create_app(
        run_inquiry,
        resume_inquiry,
        boundary,
        probe_ready,
        settings.w1_total_budget_ms,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Any:
        async with create_checkpointer(
            settings.checkpoint_backend, settings.checkpoint_uri
        ) as checkpointer:
            holder["runtime"] = InquiryRuntime(
                settings, connector_settings, boundary, checkpointer
            )
            try:
                yield
            finally:
                holder.clear()

    runtime_app.router.lifespan_context = lifespan
    return runtime_app


def _build_module_app() -> FastAPI:
    """설정이 갖춰졌으면 연결된 앱을, 아니면 준비 미완료 앱을 내보냄.

    설정 없이 모듈을 가져오는 시험에서도 임포트가 깨지지 않게 하되,
    준비 미완료로 떨어진 사유는 시작 로그에 남김.
    """
    try:
        return create_runtime_app()
    except ValidationError as error:
        logging.getLogger(__name__).error(
            "설정이 없어 W-1 워크플로우를 연결하지 못함. 모든 요청이 준비 미완료로 응답함: %s",
            error,
        )
        return create_app()


app = _build_module_app()
