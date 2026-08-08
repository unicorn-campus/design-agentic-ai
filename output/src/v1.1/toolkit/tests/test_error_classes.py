"""시험 5 — 입력 오류 · 권한 부족은 **재시도가 0회**임. 분류표 4종을 하나씩 확인함."""

from __future__ import annotations

import json

import pytest

from common.config import Settings, load_settings
from services import registry
from toolkit.errors import ConnectorCallFailed, ErrorClass
from toolkit.settings import ToolSettings, load_tool_settings
from toolkit.transport import classify_http_status, classify_transport_exception

from .conftest import CONNECTOR_ENDPOINT, live_mode
from .support import RequestSpy, always, context_for, spy_client_factory

C4_PAYLOAD = {"origin_lat": 37.5, "origin_lng": 127.0, "radius_m": 500}
C4_CONTEXT = {"completed_steps": ("S-R3",)}


def _live_c4(monkeypatch: pytest.MonkeyPatch) -> tuple[ToolSettings, Settings]:
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_MODE", json.dumps(live_mode()))
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", json.dumps(CONNECTOR_ENDPOINT))
    return load_tool_settings(), load_settings()


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (400, ErrorClass.INPUT),
        (401, ErrorClass.AUTH),
        (403, ErrorClass.PERMISSION),
        (404, ErrorClass.INPUT),
        (422, ErrorClass.INPUT),
        (429, ErrorClass.TRANSIENT),
        (500, ErrorClass.TRANSIENT),
        (503, ErrorClass.TRANSIENT),
        (418, ErrorClass.UNCLASSIFIED),
    ],
)
def test_status_codes_map_to_the_four_classes(status_code: int, expected: ErrorClass) -> None:
    assert classify_http_status(status_code) is expected


def test_timeout_is_transient_and_unknown_is_unclassified() -> None:
    assert classify_transport_exception(TimeoutError()) is ErrorClass.TRANSIENT
    assert classify_transport_exception(ValueError("모르는 실패")) is ErrorClass.UNCLASSIFIED


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(403, ErrorClass.PERMISSION), (400, ErrorClass.INPUT), (418, ErrorClass.UNCLASSIFIED)],
)
async def test_non_retryable_classes_call_outward_exactly_once(
    env_ready: None,
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected: ErrorClass,
) -> None:
    """③이 `S-R7`에 재시도 1회를 줬어도 이 3종은 **다시 때리지 않음**."""
    tool_settings, runtime_settings = _live_c4(monkeypatch)
    assert runtime_settings.retry_count("S-R7") == 1  # 재시도 예산이 있는데도

    spy = RequestSpy()
    tool = registry.build_tool(
        "C-4",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(status_code)),
    )
    result = await tool.call(C4_PAYLOAD, context_for(**C4_CONTEXT))

    assert result.ok is False
    assert result.error_class is expected
    assert spy.count == 1, "재시도가 0회여야 함"
    assert result.attempts == 1
    assert result.outward_calls == 1


async def test_input_error_names_the_offending_key(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """규격 불일치는 재시도하지 않고 **어느 키가 문제인지** 적어 올림."""
    tool = registry.build_tool("C-4", tool_settings, runtime_settings)
    with pytest.raises(ConnectorCallFailed) as caught:
        await tool.call({"origin_lat": 37.5, "radius_m": 500}, context_for(**C4_CONTEXT))
    report = caught.value.report
    assert report.error_class is ErrorClass.INPUT
    assert "origin_lng" in report.offending_keys
    assert report.attempts == 0


async def test_unknown_extra_key_is_an_input_error_not_a_silent_pass(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """규격에 없는 칸이 실려 오면 거부함 — 가리기로 대신하지 않음."""
    tool = registry.build_tool("C-4", tool_settings, runtime_settings)
    payload = {**C4_PAYLOAD, "diet_type": "vegan"}
    with pytest.raises(ConnectorCallFailed) as caught:
        await tool.call(payload, context_for(**C4_CONTEXT))
    assert caught.value.report.error_class is ErrorClass.INPUT
    assert "diet_type" in caught.value.report.offending_keys


async def test_permission_error_carries_requested_scopes(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """권한 부족은 **요청한 범위와 필요한 범위**를 적어 올림."""
    tool_settings, runtime_settings = _live_c4(monkeypatch)
    spy = RequestSpy()
    tool = registry.build_tool(
        "C-4",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(403)),
    )
    result = await tool.call(C4_PAYLOAD, context_for(**C4_CONTEXT))
    record = result.error_report.as_record()
    assert record["requested_scopes"] == ["places.nearby.read"]
    assert record["required_scope"].startswith("[확인필요")


async def test_auth_error_refreshes_once_then_stops(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """인증 오류 — 1회 갱신 후 재시도, 또 실패하면 즉시 멈추고 사람에게 알림."""
    tool_settings, runtime_settings = _live_c4(monkeypatch)
    spy = RequestSpy()
    tool = registry.build_tool(
        "C-4",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(401)),
    )
    result = await tool.call(C4_PAYLOAD, context_for(**C4_CONTEXT))

    assert result.ok is False
    assert result.error_class is ErrorClass.AUTH
    assert spy.count == 2, "갱신 후 1회만 다시 부름"
    assert tool.adapter.credential.refreshed_count >= 1
    record = result.error_report.as_record()
    assert record["credential_refreshed_at_ms"] is not None
    assert "사람 확인" in record["reason"]
