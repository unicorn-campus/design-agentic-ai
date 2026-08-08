"""시험 8 — `Mock`으로 적힌 커넥터가 실물 주소를 **부르지 않음**.

② 4절이 `Mock`으로 판정한 커넥터 중 ④에 배정된 것은 `C-8` · `C-9` · `C-12` 3종임
(`C-6` · `C-10`도 Mock이지만 **배정 0건**이라 도구로 만들지 않았음 — ⑤ 6절).
"""

from __future__ import annotations

import json

import httpx
import pytest

from common.config import Settings, load_settings
from services import registry
from toolkit.errors import ConnectorNotConfigured
from toolkit.settings import ConnectorMode, ToolSettings, load_tool_settings
from toolkit.transport import NullTransport

from .support import context_for

MOCK_CASES = {
    "C-8": (
        {"place_ids": ["p1", "p2"]},
        {"completed_steps": ("S-R7",)},
    ),
    "C-9": (
        {
            "payment_token": "tok-test",
            "amount_krw": 4900,
            "billing_cycle": "monthly",
            "idempotency_key": "C-9:member-1:2026-08-08",
            "user_approval_id": "approval-1",
        },
        {"completed_steps": ("S-S7", "S-S8"), "approval_evidence": {"S-S7": True}},
    ),
    "C-12": (
        {
            "pg_payment_id": "pg-1",
            "cancel_schedule_id": "cancel-1",
            "pg_cancel_idempotency_key": "C-12:member-1:2026-09-08",
        },
        {
            "completed_steps": ("S-C5", "S-C7"),
            "approval_evidence": {"S-C5": True, "S-C7": True},
        },
    ),
}


def test_design_mock_connectors_are_built_as_mock(tool_settings: ToolSettings) -> None:
    for connector_id in MOCK_CASES:
        assert tool_settings.mode_of(connector_id) is ConnectorMode.MOCK


@pytest.mark.parametrize("connector_id", sorted(MOCK_CASES))
async def test_mock_connector_makes_no_outward_http_call(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    connector_id: str,
) -> None:
    """`httpx.AsyncClient`가 아예 만들어지지 않음 — 주소를 읽을 일도 없음."""
    created: list[str] = []
    original = httpx.AsyncClient.__init__

    def spy_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        created.append(str(kwargs.get("base_url", "")))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", spy_init)

    payload, context_kwargs = MOCK_CASES[connector_id]
    tool = registry.build_tool(connector_id, tool_settings, runtime_settings)
    result = await tool.call(payload, context_for(**context_kwargs))

    assert created == [], f"대역인데 HTTP 클라이언트가 만들어짐: {created}"
    assert isinstance(tool.adapter.transport, NullTransport)
    assert result.audit["mode"] == "mock"
    assert result.audit["transport"] == "대역(바깥 호출 없음)"


@pytest.mark.parametrize("connector_id", sorted(MOCK_CASES))
async def test_mock_connector_needs_no_address_and_no_credential(
    env_ready: None, monkeypatch: pytest.MonkeyPatch, connector_id: str
) -> None:
    """주소와 자격을 **아예 지우고도** 대역이 돌아감(⑦ 6-1절: Mock 판에는 `K-11`을 주입 안 함)."""
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", "{}")
    for name in (
        "LUNCHPICK_MAP_API_KEY",
        "LUNCHPICK_WEATHER_API_KEY",
        "LUNCHPICK_MFDS_API_KEY",
        "LUNCHPICK_PG_MERCHANT_ID",
        "LUNCHPICK_PG_API_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)

    tool_settings, runtime_settings = load_tool_settings(), load_settings()
    payload, context_kwargs = MOCK_CASES[connector_id]
    tool = registry.build_tool(connector_id, tool_settings, runtime_settings)
    result = await tool.call(payload, context_for(**context_kwargs))
    assert result.ok is True


def test_live_mode_without_address_fails_loudly(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """실물인데 주소가 없으면 조용히 기본값을 쓰지 않고 멈춤 — 코드에 박지 않았다는 증거임."""
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", "{}")
    tool_settings, runtime_settings = load_tool_settings(), load_settings()
    with pytest.raises(ConnectorNotConfigured, match="주소가 설정에 없음"):
        registry.build_adapter("C-4", tool_settings, runtime_settings)


def test_mock_mode_requires_a_mock_implementation(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """②가 실물로 판정한 커넥터를 대역으로 돌리려 하면 막힘 — 판정 값을 바꿔 쓰지 않음."""
    modes = json.loads(json.dumps({**{"C-4": "mock"}}))
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_MODE", json.dumps(modes))
    tool_settings, runtime_settings = load_tool_settings(), load_settings()
    with pytest.raises(ConnectorNotConfigured, match="대역 구현이 없음"):
        registry.build_adapter("C-4", tool_settings, runtime_settings)


async def test_mock_payment_does_not_pretend_success(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """대역이 `성공` · `중지완료`로 꾸미지 않음 — 실제로 돈이 움직이지 않았음이 드러남."""
    payload, context_kwargs = MOCK_CASES["C-9"]
    tool = registry.build_tool("C-9", tool_settings, runtime_settings)
    result = await tool.call(payload, context_for(**context_kwargs))
    assert result.output["payment_result"] == "확인 중"

    payload, context_kwargs = MOCK_CASES["C-12"]
    stop = registry.build_tool("C-12", tool_settings, runtime_settings)
    stop_result = await stop.call(payload, context_for(**context_kwargs))
    assert stop_result.output["pg_cancel_status"] == "확인 중"


async def test_mock_business_status_does_not_invent_open_status(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """원천이 미확정이라 `영업`으로 꾸미지 않고 판정 자체를 비움."""
    payload, context_kwargs = MOCK_CASES["C-8"]
    tool = registry.build_tool("C-8", tool_settings, runtime_settings)
    result = await tool.call(payload, context_for(**context_kwargs))
    assert result.output["business_status_by_place"] == {}
