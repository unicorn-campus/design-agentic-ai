from __future__ import annotations

from collections.abc import Awaitable, Callable

from help_desk_api import ConsultationClosedBody, GuardrailBoundary
from help_desk_runtime.api_contracts import ConsultationClosedResponse
from help_desk_workflow.contracts import ConsultationClosedResult

EventRunner = Callable[[dict[str, object]], Awaitable[ConsultationClosedResponse]]


class ConsultationClosedSubscriber:
    def __init__(self, runner: EventRunner, boundary: GuardrailBoundary) -> None:
        self._runner = runner
        self._boundary = boundary

    async def handle(self, raw_event: dict[str, object]) -> ConsultationClosedResult:
        body = ConsultationClosedBody.model_validate(raw_event)
        payload = body.model_dump(mode="json")
        self._boundary.inspect_input("IN-W3-E1", payload, "받는 즉시")
        result = await self._runner(payload)
        safe = self._boundary.sanitize_output("W-3", result)
        return ConsultationClosedResult.model_validate(safe)
