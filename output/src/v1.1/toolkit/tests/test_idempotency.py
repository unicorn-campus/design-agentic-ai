"""시험 4 — 같은 중복 방지 키로 두 번 부르면 바깥 호출이 **1회만** 일어남."""

from __future__ import annotations

import pytest

from common.config import Settings
from services import registry
from toolkit.errors import IdempotencyKeyMissing
from toolkit.idempotency import (
    InMemoryResultStore,
    connector_idempotency_key,
    key_fingerprint,
)
from toolkit.settings import ToolSettings

from .support import context_for

C12_PAYLOAD = {
    "pg_payment_id": "pg-1",
    "cancel_schedule_id": "cancel-1",
    "pg_cancel_idempotency_key": "C-12:member-1:2026-09-08",
}
C12_CONTEXT_KWARGS = {
    "completed_steps": ("S-C5", "S-C7"),
    "approval_evidence": {"S-C5": True, "S-C7": True},
}


async def test_same_key_twice_calls_outward_once(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    store = InMemoryResultStore(ttl_hours=tool_settings.idempotency_ttl_hours)
    tool = registry.build_tool("C-12", tool_settings, runtime_settings, result_store=store)

    canned_calls = 0
    original = tool.adapter.canned

    def counting(payload):  # type: ignore[no-untyped-def]
        nonlocal canned_calls
        canned_calls += 1
        return original(payload)

    tool.adapter.canned = counting  # type: ignore[method-assign]

    first = await tool.call(C12_PAYLOAD, context_for(**C12_CONTEXT_KWARGS))
    second = await tool.call(C12_PAYLOAD, context_for(**C12_CONTEXT_KWARGS))

    assert canned_calls == 1, "바깥 호출이 두 번 일어남"
    assert first.outward_calls == 1
    assert second.outward_calls == 0
    assert second.replayed is True
    assert dict(second.output) == dict(first.output)


async def test_different_key_calls_outward_again(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    store = InMemoryResultStore(ttl_hours=tool_settings.idempotency_ttl_hours)
    tool = registry.build_tool("C-12", tool_settings, runtime_settings, result_store=store)

    await tool.call(C12_PAYLOAD, context_for(**C12_CONTEXT_KWARGS))
    other = {**C12_PAYLOAD, "pg_cancel_idempotency_key": "C-12:member-1:2026-10-08"}
    result = await tool.call(other, context_for(**C12_CONTEXT_KWARGS))

    assert result.replayed is False
    assert result.outward_calls == 1
    assert len(store) == 2


async def test_write_tool_refuses_empty_idempotency_key(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    tool = registry.build_tool("C-12", tool_settings, runtime_settings)
    payload = {**C12_PAYLOAD, "pg_cancel_idempotency_key": ""}
    with pytest.raises(IdempotencyKeyMissing) as caught:
        await tool.call(payload, context_for(**C12_CONTEXT_KWARGS))
    assert caught.value.report.offending_keys == ("pg_cancel_idempotency_key",)
    assert caught.value.report.attempts == 0


async def test_registration_and_stop_keys_are_different_values(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """⑤ 6절 — 등록 키와 중지 키는 **다른 값**이어야 함."""
    register_key = connector_idempotency_key("C-9", "member-1", "2026-08-08")
    stop_key = connector_idempotency_key("C-12", "member-1", "2026-08-08")
    assert register_key != stop_key
    assert register_key.startswith("C-9:")
    assert stop_key.startswith("C-12:")


def test_key_assembly_has_a_single_place() -> None:
    """조립 함수를 1개만 두었음 — `common`의 조립기를 그대로 씀."""
    from common.checkpointer import build_idempotency_key

    assert connector_idempotency_key("C-9", "a", "b") == build_idempotency_key("C-9", "a", "b")


def test_fingerprint_hides_the_key_itself() -> None:
    """기록에는 키 원문을 남기지 않고 해시만 남김(⑤ `F-17`)."""
    key = "C-12:member-1:2026-09-08"
    fingerprint = key_fingerprint(key)
    assert key not in fingerprint
    assert len(fingerprint) == 16
