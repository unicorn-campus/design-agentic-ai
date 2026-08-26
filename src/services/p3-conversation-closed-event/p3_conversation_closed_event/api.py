from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from help_desk_api import (
    CrmReviewDecisionBody,
    GuardrailBoundary,
    HealthBody,
    PublicApiError,
    install_error_handlers,
)
from help_desk_runtime.api_contracts import CrmReviewDecisionResponse
from help_desk_workflow.contracts import CrmReviewDecisionResult

ReviewRunner = Callable[[str, dict[str, object]], Awaitable[CrmReviewDecisionResponse]]
ReadinessProbe = Callable[[], Awaitable[bool]]


def create_internal_app(
    review_runner: ReviewRunner | None = None,
    boundary: GuardrailBoundary | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> FastAPI:
    app = FastAPI(title="Help Desk CRM Review API", version="0.1.0")
    install_error_handlers(app)

    @app.post(
        "/internal/crm-record-reviews/{review_id}/decisions",
        response_model=CrmReviewDecisionResult,
        response_model_exclude_none=True,
    )
    async def decide(review_id: str, body: CrmReviewDecisionBody) -> CrmReviewDecisionResult:
        if review_runner is None or boundary is None:
            raise PublicApiError(503, "service_not_ready", "서비스 준비가 완료되지 않음")
        payload = {"review_id": review_id, **body.model_dump(exclude_none=True)}
        boundary.inspect_input("IN-W3-E5", payload, "프롬프트 조립 직전")
        result = await review_runner(review_id, payload)
        safe = boundary.sanitize_output("W-3", result)
        return CrmReviewDecisionResult.model_validate(safe)

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


app = create_internal_app()
