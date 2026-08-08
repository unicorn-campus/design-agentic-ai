"""시험 7 — 오류 메시지 · 로그 · 감사 기록에 자격 값이 **0건**(문자열 검색으로 확인).

⑦ 6-2절 3번이 `가장 자주 남는 사고`로 꼽은 자리임 —
실패 경로에서 접속 문자열·클라이언트 시크릿이 통째로 찍히는 것.
정상 경로 시험으로는 안 잡히므로 **실패 경로만** 골라 확인함.
"""

from __future__ import annotations

import json
import logging

import pytest

from common.config import load_settings
from services import registry
from toolkit.settings import load_tool_settings

from .conftest import CONNECTOR_ENDPOINT, SECRET_PLACEHOLDERS, live_mode
from .support import RequestSpy, always, context_for, spy_client_factory

SECRET_VALUES = tuple(SECRET_PLACEHOLDERS.values()) + ("llm-secret-value-for-test",)
ADDRESS_VALUES = ("http://connector.test", "http://pg.test")

C4_PAYLOAD = {"origin_lat": 37.5, "origin_lng": 127.0, "radius_m": 500}
C9_PAYLOAD = {
    "payment_token": "tok-test",
    "amount_krw": 4900,
    "billing_cycle": "monthly",
    "idempotency_key": "C-9:member-1:2026-08-08",
    "user_approval_id": "approval-1",
}


def _live(monkeypatch: pytest.MonkeyPatch, **modes: str):
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_MODE", json.dumps(live_mode(**modes)))
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", json.dumps(CONNECTOR_ENDPOINT))
    return load_tool_settings(), load_settings()


def _assert_no_credential(blob: str, label: str) -> None:
    for secret in SECRET_VALUES:
        assert secret not in blob, f"{label}에 자격 값이 있음"


def _assert_clean(blob: str, label: str) -> None:
    """우리 코드가 만드는 문자열에는 자격도 주소도 없어야 함."""
    _assert_no_credential(blob, label)
    for address in ADDRESS_VALUES:
        assert address not in blob, f"{label}에 주소가 있음"


@pytest.mark.parametrize("status_code", [401, 403, 500, 400])
async def test_error_report_carries_no_credential_or_address(
    env_ready: None, monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    tool_settings, runtime_settings = _live(monkeypatch)
    spy = RequestSpy()
    tool = registry.build_tool(
        "C-4",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(status_code, {"detail": "nope"})),
    )
    result = await tool.call(C4_PAYLOAD, context_for(completed_steps=("S-R3",)))
    assert result.ok is False

    blob = json.dumps(
        {
            "report": result.error_report.as_record(),
            "audit": dict(result.audit),
            "message": str(result.error_report),
        },
        ensure_ascii=False,
        default=str,
    )
    _assert_clean(blob, "오류 보고와 감사 기록")
    # 자격이 실제로 나가기는 했음을 함께 확인 — 안 보내면서 통과하는 것이 아님
    assert any("x-test-key" in {k.lower() for k in headers} for headers in spy.headers)


async def test_raised_exception_text_carries_no_credential(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool_settings, runtime_settings = _live(monkeypatch)
    tool = registry.build_tool("C-4", tool_settings, runtime_settings)
    from toolkit.errors import ConnectorCallFailed

    with pytest.raises(ConnectorCallFailed) as caught:
        await tool.call({"origin_lat": 37.5}, context_for(completed_steps=("S-R3",)))
    _assert_clean(repr(caught.value) + str(caught.value), "예외 문자열")


async def test_log_records_carry_no_credential(
    env_ready: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    tool_settings, runtime_settings = _live(monkeypatch, **{"C-9": "live"})
    spy = RequestSpy()
    tool = registry.build_tool(
        "C-9",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(401)),
    )
    with caplog.at_level(logging.DEBUG):
        result = await tool.call(
            C9_PAYLOAD,
            context_for(
                completed_steps=("S-S7", "S-S8"), approval_evidence={"S-S7": True}
            ),
        )
    assert result.ok is False
    # 자격 값이 로그에 0건 — 이것이 이 시험의 합격 조건임
    _assert_no_credential(caplog.text, "로그")


async def test_http_library_logs_the_address_and_must_be_silenced_by_guardrail(
    env_ready: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """확인된 사실을 숨기지 않고 시험으로 못 박음.

    **우리 코드는 주소를 찍지 않지만 `httpx` 라이브러리가 INFO 단계에서 요청 주소를 찍음.**
    주소에는 자격이 들어 있지 않아(자격은 헤더에 실림) 비밀값 유출은 아니지만,
    로그에 바깥 주소가 남는 것은 사실임. **`05-guardrail.md`가 로그 설정에서 `httpx` 로거를
    `WARNING` 이상으로 내려야 함** — 도구 계층이 전역 로그 설정을 건드리지 않음.
    """
    tool_settings, runtime_settings = _live(monkeypatch)
    spy = RequestSpy()
    tool = registry.build_tool(
        "C-4",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(200, {"places": []})),
    )
    with caplog.at_level(logging.INFO, logger="httpx"):
        await tool.call(C4_PAYLOAD, context_for(completed_steps=("S-R3",)))

    library_lines = [r.getMessage() for r in caplog.records if r.name == "httpx"]
    assert any("connector.test" in line for line in library_lines), (
        "이 시험이 못 박은 사실이 바뀌었으면 README 8절을 함께 고침"
    )
    # 그래도 자격 값은 라이브러리 로그에도 없음
    _assert_no_credential(caplog.text, "라이브러리 로그")

    # 우리 코드가 만든 기록에는 주소가 0건임
    ours = [r.getMessage() for r in caplog.records if r.name != "httpx"]
    _assert_clean("\n".join(ours), "우리 코드의 로그")


async def test_audit_record_keeps_only_the_key_fingerprint(
    tool_settings, runtime_settings
) -> None:
    """중복 방지 키 원문이 감사 기록에 없고 해시만 있음(⑤ `F-17`)."""
    tool = registry.build_tool("C-9", tool_settings, runtime_settings)
    result = await tool.call(
        C9_PAYLOAD,
        context_for(completed_steps=("S-S7", "S-S8"), approval_evidence={"S-S7": True}),
    )
    blob = json.dumps(dict(result.audit), ensure_ascii=False, default=str)
    assert C9_PAYLOAD["idempotency_key"] not in blob
    assert "idempotency_key_fingerprint" in result.audit
    assert "payment_token" not in blob
    assert "tok-test" not in blob


def test_env_example_has_names_only_and_no_values() -> None:
    """비밀값 예시 파일에는 **키 이름만** 있음(`D-10`)."""
    from pathlib import Path

    import toolkit

    example = Path(toolkit.__file__).resolve().parent / ".env.example"
    lines = [
        line.strip()
        for line in example.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert lines, ".env.example이 비어 있음"
    for line in lines:
        name, _, value = line.partition("=")
        assert name.startswith("LUNCHPICK_"), line
        assert value == "", f"예시 파일에 값이 들어 있음: {line}"
