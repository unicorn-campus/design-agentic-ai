"""시험 3 — 승인 표시 없이 `쓰기(되돌림 불가)` 도구를 부르면 **거부됨**.

`쓰기(되돌림 불가)` 행 수(2건)와 이 파일의 거부 시험 수(2건)가 같아야 함.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from common.config import Settings
from services import registry
from toolkit.errors import ApprovalMissing, PreconditionNotMet
from toolkit.schema import SideEffect
from toolkit.settings import ToolSettings

from .support import context_for

C9_PAYLOAD = {
    "payment_token": "tok-test",
    "amount_krw": 4900,
    "billing_cycle": "monthly",
    "idempotency_key": "C-9:member-1:2026-08-08",
    "user_approval_id": "approval-1",
}

C12_PAYLOAD = {
    "pg_payment_id": "pg-1",
    "cancel_schedule_id": "cancel-1",
    "pg_cancel_idempotency_key": "C-12:member-1:2026-09-08",
}

IRREVERSIBLE_CASES = [
    pytest.param("C-9", C9_PAYLOAD, ("S-S7", "S-S8"), ("S-S7",), id="C-9 정기 결제 등록"),
    pytest.param(
        "C-12", C12_PAYLOAD, ("S-C5", "S-C7"), ("S-C5", "S-C7"), id="C-12 정기 결제 중지"
    ),
]


@pytest.mark.parametrize(("connector_id", "payload", "steps", "marks"), IRREVERSIBLE_CASES)
async def test_call_without_approval_mark_is_refused(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    connector_id: str,
    payload: dict[str, object],
    steps: tuple[str, ...],
    marks: tuple[str, ...],
) -> None:
    """승인 표시가 없으면 바깥을 부르기 전에 막힘 — 부작용 0건."""
    tool = registry.build_tool(connector_id, tool_settings, runtime_settings)
    context = context_for(completed_steps=steps, approval_evidence={})

    with pytest.raises(ApprovalMissing) as caught:
        await tool.call(payload, context)

    report = caught.value.report
    assert report.error_class.value == "권한 부족"
    assert report.attempts == 0
    assert set(report.offending_keys) == set(marks)
    assert report.extra["side_effect"] == "쓰기(되돌림 불가)"


@pytest.mark.parametrize(("connector_id", "payload", "steps", "marks"), IRREVERSIBLE_CASES)
async def test_partial_approval_is_still_refused(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    connector_id: str,
    payload: dict[str, object],
    steps: tuple[str, ...],
    marks: tuple[str, ...],
) -> None:
    """표시가 하나라도 비면 거부임 — 기본은 거부이고 부분 승인으로 내려 주지 않음."""
    tool = registry.build_tool(connector_id, tool_settings, runtime_settings)
    evidence = {mark: True for mark in marks[:-1]}
    context = context_for(completed_steps=steps, approval_evidence=evidence)
    if len(marks) == 1:
        pytest.skip("표시가 1개인 커넥터는 부분 승인이 성립하지 않음")
    with pytest.raises(ApprovalMissing):
        await tool.call(payload, context)


async def test_c12_refuses_when_reservation_commit_is_missing(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """예약 커밋(`S-C7`) 없이 중지를 부르면 결제 중인 구독을 끊음 — 그래서 막음."""
    tool = registry.build_tool("C-12", tool_settings, runtime_settings)
    context = context_for(
        completed_steps=("S-C5",), approval_evidence={"S-C5": True, "S-C7": True}
    )
    with pytest.raises(PreconditionNotMet) as caught:
        await tool.call(C12_PAYLOAD, context)
    assert caught.value.report.offending_keys == ("S-C7",)
    assert caught.value.report.extra["strict_order"] is True


async def test_approved_call_goes_through_and_is_not_reported_as_success(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """승인 표시가 있으면 호출은 되지만, **대역은 `중지완료`로 꾸미지 않음**."""
    tool = registry.build_tool("C-12", tool_settings, runtime_settings)
    context = context_for(
        completed_steps=("S-C5", "S-C7"),
        approval_evidence={"S-C5": True, "S-C7": True},
    )
    result = await tool.call(C12_PAYLOAD, context)
    assert result.ok is True
    assert result.output["pg_cancel_status"] == "확인 중"
    assert result.output["cancel_schedule_id"] == "cancel-1"
    assert isinstance(result.output["pg_cancel_requested_at"], datetime)
    assert result.audit["mode"] == "mock"
    assert "idempotency_key_fingerprint" in result.audit


def test_irreversible_row_count_matches_refusal_test_count() -> None:
    rows = [
        spec
        for spec in registry.TOOL_SPECS.values()
        if spec.side_effect is SideEffect.WRITE_IRREVERSIBLE
    ]
    assert len(rows) == len(IRREVERSIBLE_CASES) == 2
