"""⑤ 「커넥터 검증 기준」의 호출 순서와, 시간 상한을 넘겼을 때의 처리를 확인함.

시간 상한 초과의 뜻(되묻기 2번) — **되돌릴 수 없는 도구는 취소를 성공으로 보고하지 않음.**
결과를 `확인 중`으로 두고 사람 확인으로 올림.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from common.budget import DeadlineTooTight, now_ms
from common.config import Settings, load_settings
from services import registry
from toolkit.errors import ErrorClass, PreconditionNotMet
from toolkit.runner import CallContext
from toolkit.settings import ToolSettings, load_tool_settings

from .conftest import CONNECTOR_ENDPOINT, live_mode
from .support import context_for

# ⑤ 6절 「커넥터 검증 기준」 · ⑤ 「커넥터 ↔ ③ 단계 대조」에서 옮긴 값
ORDER_TABLE = {
    "C-2": (("S-R9",), True),
    "C-3": (("S-B3",), True),
    "C-4": (("S-R3",), False),
    "C-7": (("S-R3",), False),
    "C-8": (("S-R7",), True),
    "C-9": (("S-S7", "S-S8"), True),
    "C-12": (("S-C5", "S-C7"), True),
}

PAYLOADS = {
    "C-8": {"place_ids": ["p1"]},
    "C-12": {
        "pg_payment_id": "pg-1",
        "cancel_schedule_id": "cancel-1",
        "pg_cancel_idempotency_key": "C-12:member-1:2026-09-08",
    },
    "C-9": {
        "payment_token": "tok-test",
        "amount_krw": 4900,
        "billing_cycle": "monthly",
        "idempotency_key": "C-9:member-1:2026-08-08",
        "user_approval_id": "approval-1",
    },
}


def test_preconditions_match_the_design_verification_table() -> None:
    for connector_id, (steps, strict) in ORDER_TABLE.items():
        spec = registry.TOOL_SPECS[connector_id]
        assert spec.preconditions == steps, connector_id
        assert spec.strict_order is strict, connector_id


async def test_business_status_refuses_before_candidate_lookup(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """⑤ `C-8` — 후보 조회(`S-R7`) 앞에서 부르면 막힘."""
    tool = registry.build_tool("C-8", tool_settings, runtime_settings)
    with pytest.raises(PreconditionNotMet) as caught:
        await tool.call(PAYLOADS["C-8"], context_for(completed_steps=()))
    assert caught.value.report.offending_keys == ("S-R7",)


async def test_parallel_allowed_connector_does_not_require_each_other(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """⑤ `C-4` · `C-7`은 서로를 기다리지 않음(`strict_order=False`)."""
    for connector_id in ("C-4", "C-7"):
        spec = registry.TOOL_SPECS[connector_id]
        assert "S-R6" not in spec.preconditions
        assert "S-R7" not in spec.preconditions


class _SlowMock:
    """시간 상한을 일부러 넘기는 대역. 실제 주소를 부르지 않음."""

    def __init__(self, adapter, delay_s: float) -> None:
        self._adapter = adapter
        self._delay_s = delay_s

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        return getattr(self._adapter, name)

    async def call(self, payload):  # type: ignore[no-untyped-def]
        await asyncio.sleep(self._delay_s)
        return await self._adapter.call(payload)


async def test_timeout_on_irreversible_write_is_not_reported_as_success(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """`C-9` — 시간 상한을 넘기면 `확인 중`으로 두고 사람 확인으로 올림. `성공` 아님."""
    tool = registry.build_tool("C-9", tool_settings, runtime_settings)
    timeout_ms = runtime_settings.timeout_ms("S-S9")
    tool.adapter = _SlowMock(tool.adapter, (timeout_ms / 1000) + 0.2)  # type: ignore[assignment]

    result = await tool.call(
        PAYLOADS["C-9"],
        context_for(completed_steps=("S-S7", "S-S8"), approval_evidence={"S-S7": True}),
    )

    assert result.ok is False
    assert result.unresolved is True
    assert result.escalate_to_human is True
    assert result.output == {"payment_result": "확인 중"}
    assert result.error_class is ErrorClass.TRANSIENT
    assert result.error_report.extra["timed_out"] is True


async def test_timeout_on_stop_connector_marks_pending_not_done(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """`C-12` — 예약을 되돌리지 않고 `확인 중`으로 둠(③ 4-6절)."""
    tool = registry.build_tool("C-12", tool_settings, runtime_settings)
    timeout_ms = runtime_settings.timeout_ms("S-C10")
    tool.adapter = _SlowMock(tool.adapter, (timeout_ms / 1000) + 0.2)  # type: ignore[assignment]

    result = await tool.call(
        PAYLOADS["C-12"],
        context_for(
            completed_steps=("S-C5", "S-C7"),
            approval_evidence={"S-C5": True, "S-C7": True},
            slack_ms=90_000,
        ),
    )
    assert result.ok is False
    assert result.output == {"pg_cancel_status": "확인 중"}
    assert result.escalate_to_human is True


async def test_stop_connector_reports_failure_when_pg_refuses(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """응답을 받고 거절당한 경우는 `실패`임 — `확인 중`과 갈라 적음(③ 6절 23번 3값)."""
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_MODE", json.dumps(live_mode(**{"C-12": "live"})))
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", json.dumps(CONNECTOR_ENDPOINT))
    tool_settings, runtime_settings = load_tool_settings(), load_settings()

    from .support import RequestSpy, always, spy_client_factory

    spy = RequestSpy()
    tool = registry.build_tool(
        "C-12",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(403)),
    )
    result = await tool.call(
        PAYLOADS["C-12"],
        context_for(
            completed_steps=("S-C5", "S-C7"),
            approval_evidence={"S-C5": True, "S-C7": True},
        ),
    )
    assert result.ok is False
    assert result.output == {"pg_cancel_status": "실패"}
    assert result.error_class is ErrorClass.PERMISSION
    assert spy.count == 1


async def test_deadline_too_tight_is_raised_not_swallowed(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """마감선이 모자라면 부르지 않고 위로 올림 — 상한 초과 처리는 ③ 소유 · 06 몫임."""
    tool = registry.build_tool("C-8", tool_settings, runtime_settings)
    context = CallContext(deadline_at=now_ms() + 10, completed_steps=("S-R7",))
    with pytest.raises(DeadlineTooTight):
        await tool.call(PAYLOADS["C-8"], context)
