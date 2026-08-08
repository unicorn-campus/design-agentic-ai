"""시험 6 — 일시 장애는 ③이 정한 횟수만큼만 재시도하고 **계층이 하나뿐**임."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from common.config import Settings, load_settings
from services import registry
from toolkit import runner
from toolkit.errors import ErrorClass
from toolkit.settings import load_tool_settings

from .conftest import CONNECTOR_ENDPOINT, live_mode
from .support import RequestSpy, always, context_for, spy_client_factory

C4_PAYLOAD = {"origin_lat": 37.5, "origin_lng": 127.0, "radius_m": 500}
C7_PAYLOAD = {"origin_lat": 37.5, "origin_lng": 127.0}


def _live(monkeypatch: pytest.MonkeyPatch) -> tuple[object, Settings]:
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_MODE", json.dumps(live_mode()))
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", json.dumps(CONNECTOR_ENDPOINT))
    return load_tool_settings(), load_settings()


@pytest.mark.parametrize(
    ("connector_id", "payload", "steps", "step_id"),
    [
        ("C-4", C4_PAYLOAD, ("S-R3",), "S-R7"),
        ("C-7", C7_PAYLOAD, ("S-R3",), "S-R6"),
    ],
)
async def test_transient_retries_exactly_the_design_count(
    env_ready: None,
    monkeypatch: pytest.MonkeyPatch,
    connector_id: str,
    payload: dict[str, object],
    steps: tuple[str, ...],
    step_id: str,
) -> None:
    tool_settings, runtime_settings = _live(monkeypatch)
    design_retries = runtime_settings.retry_count(step_id)
    spy = RequestSpy()
    tool = registry.build_tool(
        connector_id,
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(503)),
    )
    result = await tool.call(payload, context_for(completed_steps=steps))

    assert result.ok is False
    assert result.error_class is ErrorClass.TRANSIENT
    # 첫 호출 1회 + ③이 정한 재시도 횟수. 곱해지지 않음.
    assert spy.count == 1 + design_retries
    assert result.attempts == 1 + design_retries


async def test_zero_retry_step_is_called_once(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """③이 `S-R8`에 재시도 0회를 줬으므로 일시 장애에도 한 번만 부름."""
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_MODE", json.dumps(live_mode(**{"C-8": "live"})))
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", json.dumps(CONNECTOR_ENDPOINT))
    tool_settings, runtime_settings = load_tool_settings(), load_settings()
    assert runtime_settings.retry_count("S-R8") == 0

    spy = RequestSpy()
    tool = registry.build_tool(
        "C-8",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(503)),
    )
    result = await tool.call({"place_ids": ["p1"]}, context_for(completed_steps=("S-R7",)))
    assert spy.count == 1
    assert result.ok is False


async def test_payment_register_never_auto_retries(
    env_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """③ 8-3절 `PG 자동 재시도` = 0회. 응답을 못 받은 상태에서 다시 부르면 이중 결제가 남음."""
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_MODE", json.dumps(live_mode(**{"C-9": "live"})))
    monkeypatch.setenv("LUNCHPICK_CONNECTOR_ENDPOINT", json.dumps(CONNECTOR_ENDPOINT))
    tool_settings, runtime_settings = load_tool_settings(), load_settings()
    assert runtime_settings.retry_count("S-S9") == 0

    spy = RequestSpy()
    tool = registry.build_tool(
        "C-9",
        tool_settings,
        runtime_settings,
        client_factory=spy_client_factory(spy, always(503)),
    )
    result = await tool.call(
        {
            "payment_token": "tok-test",
            "amount_krw": 4900,
            "billing_cycle": "monthly",
            "idempotency_key": "C-9:member-1:2026-08-08",
            "user_approval_id": "approval-1",
        },
        context_for(
            completed_steps=("S-S7", "S-S8"), approval_evidence={"S-S7": True}
        ),
    )
    assert spy.count == 1
    assert result.ok is False
    assert result.escalate_to_human is True


def test_only_one_place_in_the_tool_layer_calls_the_retry_wrapper() -> None:
    """재시도 루프를 부르는 자리가 코드 전체에 **1곳**뿐임을 문자열로 확인함."""
    layer_root = Path(runner.__file__).resolve().parent.parent
    hits: list[str] = []
    for path in layer_root.rglob("*.py"):
        if ".venv" in path.parts or "tests" in path.parts or path.parts[-2] == "common":
            continue
        text = path.read_text(encoding="utf-8")
        if "call_with_limits(" in text:
            hits.append(str(path.relative_to(layer_root)))
    # `common/external_call.py`는 감싸개 자체이므로 제외하고, 도구 계층에서는 runner 1곳만 부름
    hits = [h for h in hits if "external_call" not in h]
    assert hits == [str(Path("toolkit") / "runner.py")], hits


def test_no_extra_retry_loop_inside_connector_adapters() -> None:
    """어댑터 파일에 재시도 낱말(`for attempt` · `while` · `retry`)이 없음."""
    import services

    root = Path(services.__file__).resolve().parent
    offenders: list[str] = []
    for path in root.rglob("tools/*.py"):
        # `uv` 가상환경에도 의존성 패키지의 `tools/` 디렉터리가 있을 수 있음.
        # 프로젝트 어댑터만 검사하며 제3자 패키지는 검사 범위에서 제외함.
        if ".venv" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        body = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith("#")
        )
        for token in ("while True", "for attempt", "retry_count(", "asyncio.sleep"):
            if token in body:
                offenders.append(f"{path.name}: {token}")
    assert offenders == [], offenders


def test_wrapper_is_the_runtime_one_not_a_copy() -> None:
    """감싸개를 새로 만들지 않고 `common`의 것을 가져다 씀."""
    source = inspect.getsource(runner)
    assert "from common.external_call import" in source
    assert source.count("await call_with_limits(") == 1
