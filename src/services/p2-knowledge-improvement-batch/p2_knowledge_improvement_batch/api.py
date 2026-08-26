from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from help_desk_api import (
    FaqDecisionBody,
    GuardrailBoundary,
    HealthBody,
    PublicApiError,
    install_error_handlers,
)
from help_desk_runtime.api_contracts import FaqDecisionResponse
from help_desk_workflow.contracts import FaqDecisionResult

DecisionRunner = Callable[[str, dict[str, object]], Awaitable[FaqDecisionResponse]]
ReadinessProbe = Callable[[], Awaitable[bool]]


def create_internal_app(
    decision_runner: DecisionRunner | None = None,
    boundary: GuardrailBoundary | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> FastAPI:
    app = FastAPI(title="Help Desk FAQ Review API", version="0.1.0")
    install_error_handlers(app)

    @app.post(
        "/internal/faq-candidates/{candidate_id}/decisions",
        response_model=FaqDecisionResult,
        response_model_exclude_none=True,
    )
    async def decide(candidate_id: str, body: FaqDecisionBody) -> FaqDecisionResult:
        if decision_runner is None or boundary is None:
            raise PublicApiError(503, "service_not_ready", "서비스 준비가 완료되지 않음")
        payload = {"candidate_id": candidate_id, **body.model_dump(exclude_none=True)}
        boundary.inspect_input("IN-W2-B9", payload, "프롬프트 조립 직전")
        result = await decision_runner(candidate_id, payload)
        safe = boundary.sanitize_output("W-2", result)
        return FaqDecisionResult.model_validate(safe)

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
