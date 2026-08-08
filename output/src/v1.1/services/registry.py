"""도구 목록 — `06-workflow.md`가 여기서 도구를 받아 노드에 배치함(**배치는 06 몫**).

이 파일이 하는 일은 두 가지뿐임.
ⓐ ④ 「사용 도구」에 배정된 커넥터 **7종**의 명세를 한곳에 모음
ⓑ 설정이 정한 대역·실물 판정으로 어댑터를 **갈아 끼움**(실물 코드 안에 분기문이 없음)

**여기 없는 커넥터 5종** — `C-1` · `C-5` · `C-6` · `C-10` · `C-11`은 ④ 「사용 도구」에
**배정 0건**이라 어떤 담당자도 부를 수 없음(⑤ 6절). 만들지 않는 것이 그 판정을 지키는 방법임.
호출 가능한 도구로 만들어 두면 `배정 0건`이 무의미해짐.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from common.config import Settings
from common.guardrail_hooks import HookSet, PassThroughHooks
from toolkit.approval import CallBudget, NoOpCallBudget
from toolkit.errors import ConnectorNotConfigured
from toolkit.idempotency import ResultStore, build_result_store
from toolkit.runner import ConnectorAdapter, ConnectorTool
from toolkit.schema import ToolSpec
from toolkit.settings import ConnectorMode, ToolSettings

from .daily_learning_batch.tools import c3_preference_embedding
from .payment_service.tools import c12_billing_stop, c9_billing_register
from .recommendation_history_service.tools import (
    c2_recommendation_generate,
    c4_nearby_places,
    c7_current_weather,
    c8_business_status,
)

__all__ = [
    "TOOL_MODULES",
    "TOOL_SPECS",
    "UNASSIGNED_CONNECTORS",
    "build_adapter",
    "build_tool",
    "build_all_tools",
]

# ④ 「사용 도구」에 배정된 커넥터만 있음. 이름은 ⑤ 6절 번호를 그대로 씀.
TOOL_MODULES: Mapping[str, Any] = {
    c2_recommendation_generate.CONNECTOR_ID: c2_recommendation_generate,
    c3_preference_embedding.CONNECTOR_ID: c3_preference_embedding,
    c4_nearby_places.CONNECTOR_ID: c4_nearby_places,
    c7_current_weather.CONNECTOR_ID: c7_current_weather,
    c8_business_status.CONNECTOR_ID: c8_business_status,
    c9_billing_register.CONNECTOR_ID: c9_billing_register,
    c12_billing_stop.CONNECTOR_ID: c12_billing_stop,
}

TOOL_SPECS: Mapping[str, ToolSpec] = {
    connector_id: module.SPEC for connector_id, module in TOOL_MODULES.items()
}

# ⑤ 6절 12종 중 ④ 「사용 도구」에 배정이 0건인 5종. 사유를 함께 남김.
UNASSIGNED_CONNECTORS: Mapping[str, str] = {
    "C-1": "배정 0건 — ③ 90단계에 카카오 인증 교환 단계가 없음(⑤ 6절)",
    "C-5": "배정 0건 — 수락·길찾기가 ③ 범위 밖임(⑤ 6절)",
    "C-6": "배정 0건 — 대표 메뉴·가격의 원천이 미확정임(② 소유 · ⑤ 6절)",
    "C-10": "배정 0건 — ③ 90단계에 발송 단계가 없음(⑤ 6절 · ③ 12-2절 6번)",
    "C-11": "배정 0건 — 단말에서 지도 앱을 여는 경로이며 서버가 호출하지 않음(⑤ 6절)",
}


def build_adapter(
    connector_id: str,
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    **extra: Any,
) -> ConnectorAdapter:
    """설정이 정한 대역·실물로 어댑터를 만듦. 판정 값의 주인은 ② 논리아키텍처 4절임."""
    try:
        module = TOOL_MODULES[connector_id]
    except KeyError as exc:
        reason = UNASSIGNED_CONNECTORS.get(connector_id)
        if reason is not None:
            raise ConnectorNotConfigured(
                f"{connector_id}는 호출 가능한 도구가 아님 — {reason}"
            ) from exc
        raise ConnectorNotConfigured(
            f"{connector_id}는 ④ 「사용 도구」에 없는 이름임 — 도구를 새로 만들지 않음"
        ) from exc

    mode = tool_settings.mode_of(connector_id)
    if mode is ConnectorMode.MOCK:
        builder: Callable[..., ConnectorAdapter] | None = getattr(module, "build_mock", None)
        if builder is None:
            raise ConnectorNotConfigured(
                f"{connector_id}: 설정이 대역인데 대역 구현이 없음"
                " — ② 4절은 이 커넥터를 실물로 판정했음"
            )
        return builder(tool_settings, runtime_settings, **extra)
    return module.build(tool_settings, runtime_settings, **extra)


def build_tool(
    connector_id: str,
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    *,
    result_store: ResultStore | None = None,
    hooks: HookSet | None = None,
    call_budget: CallBudget | None = None,
    **extra: Any,
) -> ConnectorTool:
    adapter = build_adapter(connector_id, tool_settings, runtime_settings, **extra)
    store = (
        result_store
        if result_store is not None
        else build_result_store(tool_settings.idempotency_ttl_hours)
    )
    return ConnectorTool(
        adapter=adapter,
        settings=runtime_settings,
        result_store=store,
        hooks=hooks if hooks is not None else PassThroughHooks(),
        call_budget=call_budget if call_budget is not None else NoOpCallBudget(),
        max_calls=tool_settings.max_calls_of(connector_id),
    )


def build_all_tools(
    tool_settings: ToolSettings,
    runtime_settings: Settings,
    *,
    result_store: ResultStore | None = None,
    hooks: HookSet | None = None,
    **extra: Any,
) -> dict[str, ConnectorTool]:
    return {
        connector_id: build_tool(
            connector_id,
            tool_settings,
            runtime_settings,
            result_store=result_store,
            hooks=hooks,
            **extra,
        )
        for connector_id in TOOL_MODULES
    }
