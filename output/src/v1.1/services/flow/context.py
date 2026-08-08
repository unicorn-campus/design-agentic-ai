"""노드가 부를 부품을 한 그릇에 담아 넘김. **부품을 여기서 만들지 않고 받아 씀.**

- 설정 · 마감선 · 중간 저장 장치 → `01-runtime`
- 검사 · 가리기 · 기록 · 승인 문 → `05-guardrail`
- 커넥터 7종 → `04-connector`(`services.registry`)
- 조회 · 검색 → `03-knowledge`

이 그릇에는 시간 제한 · 재시도 · 반복 상한 **숫자가 없음.** 전부 `settings`를 통해 읽음.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from common.checkpointer import IdempotencyStore, InMemoryIdempotencyStore
from common.config import Settings
from common.guardrail.tool_guard import ToolGuard
from common.guardrail_hooks import HookSet, PassThroughHooks
from common.observability.record import StepRecorder
from toolkit.runner import ConnectorTool

__all__ = ["FlowContext"]


@dataclass(slots=True)
class FlowContext:
    """흐름 1개가 도는 동안 쓰는 부품 묶음."""

    settings: Settings
    recorder: StepRecorder
    hooks: HookSet = field(default_factory=PassThroughHooks)
    tool_guard: ToolGuard = field(default_factory=ToolGuard)
    tools: Mapping[str, ConnectorTool] = field(default_factory=dict)
    idempotency: IdempotencyStore = field(default_factory=InMemoryIdempotencyStore)
    request_id: str = ""
    """③ 5절 `K-1`의 `request_id`. 기록·호출 상한이 이 값으로 묶임."""
    inputs: Mapping[str, Any] = field(default_factory=dict)
    """진입 값 — ③에 집합 식별자가 없는 6개 진입 구간의 값도 여기로 들어옴."""
    sources: Mapping[str, Any] = field(default_factory=dict)
    """`03-knowledge` 조회 결과를 노드에 넣어 주는 자리. 조회 구현체를 여기서 만들지 않음."""

    def tool(self, connector_id: str) -> ConnectorTool:
        """④ 「사용 도구」에 배정된 커넥터만 나옴. 없으면 지어내지 않고 실패함."""
        try:
            return self.tools[connector_id]
        except KeyError as exc:
            raise KeyError(
                f"{connector_id} 도구가 이 흐름에 주입되지 않았음"
                " — `services.registry.build_tool`로 만들어 넘겨야 함"
            ) from exc

    def has_tool(self, connector_id: str) -> bool:
        return connector_id in self.tools

    def input_of(self, key: str, default: Any = None) -> Any:
        return self.inputs.get(key, default)

    def source_of(self, key: str, default: Any = None) -> Any:
        return self.sources.get(key, default)
