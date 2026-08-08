"""시험용 부품. 바깥을 부르는 것은 전부 대역으로 바꿈(`D-07`).

**시간 제한 · 재시도 · 반복 상한 값은 여기서만 나옴** — 흐름 코드에는 숫자가 0건이고
전부 `common.config.Settings`로 들어감. 아래 값은 ③ 4절 표를 시험용으로 옮긴 것임.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from common.config import load_settings  # noqa: E402
from common.guardrail.rules import load_rulebook  # noqa: E402
from common.observability.exporter import SpanRecord  # noqa: E402
from common.observability.record import StepRecorder  # noqa: E402
from services.flow.context import FlowContext  # noqa: E402
from toolkit.runner import CallContext, ConnectorResult  # noqa: E402
from toolkit.schema import SideEffect  # noqa: E402

# ③ 4절 「타임아웃(상한)」 열 — `[확인필요]`인 단계는 일부러 뺐음(그 자리를 시험이 확인함).
STEP_TIMEOUT_MS: dict[str, int] = {
    "S-R2": 50, "S-R3": 200, "S-R4": 500, "S-R5": 300, "S-R6": 800, "S-R7": 1000,
    "S-R8": 600, "S-R9": 100, "S-R10": 100, "S-R11": 1800, "S-R12": 100, "S-R13": 100,
    "S-R15": 300, "S-R16": 300,
    "S-B1": 1000, "S-B2": 3000, "S-B3": 2000, "S-B4": 300, "S-B5": 3000, "S-B6": 200,
    "S-B7": 300, "S-B8": 1000, "S-B9": 1000, "S-B10": 5000,
    "S-E1": 50, "S-E2": 100, "S-E3": 200, "S-E4": 100, "S-E5": 100, "S-E6": 300,
    "S-E7": 100, "S-E8": 200,
    "S-S2": 50, "S-S3": 120, "S-S4": 80, "S-S5": 50, "S-S6": 50, "S-S8": 100,
    "S-S10": 100, "S-S11": 100, "S-S12": 100, "S-S13": 150,
    "S-C2": 50, "S-C3": 120, "S-C4": 80, "S-C6": 50, "S-C7": 120, "S-C8": 100,
    "S-C9": 100, "S-C11": 150,
    "S-I2": 50, "S-I3": 120, "S-I4": 500, "S-I5": 100, "S-I6": 50, "S-I7": 80,
    "S-I8": 500, "S-I9": 150, "S-I10": 100, "S-I11": 100, "S-I12": 80, "S-I13": 80,
    "S-I14": 150,
    "S-X1": 1000, "S-X2": 2000, "S-X3": 200, "S-X4": 200, "S-X5": 150, "S-X6": 200,
    "S-X7": 150, "S-X8": 1000,
    "S-N1": 50, "S-N2": 300, "S-N3": 100, "S-N4": 100, "S-N5": 100, "S-N6": 100,
    "S-N7": 80, "S-N8": 80, "S-N9": 100, "S-N10": 200,
}
"""`[확인필요]`로 ③이 비워 둔 단계 — `S-R1` `S-R14` `S-S1` `S-S7` `S-S9` `S-C1` `S-C5`
`S-C10` `S-I1`. 9건임."""

# ③ 4절 「재시도」 열.
STEP_RETRY_COUNT: dict[str, int] = {
    **{step: 0 for step in STEP_TIMEOUT_MS},
    "S-R3": 1, "S-R4": 1, "S-R5": 1, "S-R6": 1, "S-R7": 1, "S-R11": 1,
    "S-B2": 1, "S-B5": 1, "S-B7": 1, "S-B9": 1,
    "S-E3": 1, "S-E4": 1, "S-E6": 1, "S-E7": 1,
    "S-S3": 1, "S-S10": 1, "S-S11": 1,
    "S-C3": 1, "S-C7": 1, "S-C8": 1,
    "S-I3": 1, "S-I4": 1, "S-I8": 1,
    "S-X2": 1, "S-X4": 1, "S-X5": 1, "S-X6": 1, "S-X7": 1,
    "S-N2": 1, "S-N3": 1, "S-N5": 1, "S-N6": 1, "S-N7": 1, "S-N8": 1,
    "S-S9": 0, "S-C10": 1,
}

# ③ 9절 대조 2줄 · 8-1절 착지 경로.
BUDGET_TOTAL_MS = {"S-R": 3000, "S-I": 1000, "S-S": 2000, "S-C": 2000,
                   "S-B": 60000, "S-X": 60000, "S-E": 30000, "S-N": 30000}
BUDGET_LANDING_MS = {"S-R": 150, "S-I": 150, "S-S": 150, "S-C": 150,
                     "S-B": 5000, "S-X": 1000, "S-E": 200, "S-N": 200}


@pytest.fixture
def settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUNCHPICK_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LUNCHPICK_LLM_MODEL", "test-model")
    monkeypatch.setenv("LUNCHPICK_LLM_API_KEY", "test-key")


@pytest.fixture
def settings(settings_env: None):
    """③ 값이 담긴 설정. 루프 상한은 ③이 `[확인필요]`로 남겨 **비운 채** 둠."""
    return load_settings(
        step_timeout_ms=STEP_TIMEOUT_MS,
        step_retry_count=STEP_RETRY_COUNT,
        step_retry_conditional=frozenset({"S-R11"}),
        step_backoff_ms={"S-C10": 1000},
        budget_total_ms=BUDGET_TOTAL_MS,
        budget_landing_ms=BUDGET_LANDING_MS,
        loop_max_iter={},
        knowledge_radius_m=500,
    )


@pytest.fixture
def settings_with_loops(settings_env: None):
    """루프 상한이 채워진 설정 — 상한 초과 착지 시험이 씀. 값은 시험용 가정임."""
    return load_settings(
        step_timeout_ms=STEP_TIMEOUT_MS,
        step_retry_count=STEP_RETRY_COUNT,
        step_retry_conditional=frozenset({"S-R11"}),
        budget_total_ms=BUDGET_TOTAL_MS,
        budget_landing_ms=BUDGET_LANDING_MS,
        loop_max_iter={"L-1": 2, "L-2": 3, "L-3": 3},
        knowledge_radius_m=500,
    )


class CollectingSink:
    """관측 기록을 모아 두는 대역. 제품에 실제로 내보내지 않음."""

    def __init__(self) -> None:
        self.records: list[SpanRecord] = []

    def emit(self, record: SpanRecord) -> None:
        self.records.append(record)

    def flush(self) -> None:
        return None


@pytest.fixture
def sink() -> CollectingSink:
    return CollectingSink()


@pytest.fixture
def recorder(sink: CollectingSink) -> StepRecorder:
    return StepRecorder(sink, book=load_rulebook())


class FakeTool:
    """커넥터 대역 — 실제 어댑터를 만들지 않고 `ConnectorResult`만 돌려줌.

    **재시도 루프가 없음.** 커넥터 계층의 재시도를 흉내 내지 않으므로 이 대역으로
    노드에 재시도가 붙어 있는지도 드러남.
    """

    def __init__(
        self,
        connector_id: str,
        step_id: str,
        output: Mapping[str, Any],
        *,
        ok: bool = True,
        side_effect: SideEffect = SideEffect.READ,
    ) -> None:
        self.connector_id = connector_id
        self.step_id = step_id
        self.output = dict(output)
        self.ok = ok
        self.side_effect = side_effect
        self.calls: list[tuple[dict[str, Any], CallContext]] = []

    async def call(self, payload: Mapping[str, Any], context: CallContext) -> ConnectorResult:
        self.calls.append((dict(payload), context))
        return ConnectorResult(
            connector_id=self.connector_id,
            step_id=self.step_id,
            ok=self.ok,
            output=self.output if self.ok else {},
            attempts=1,
            outward_calls=1,
            escalate_to_human=(not self.ok) and self.side_effect is SideEffect.WRITE_IRREVERSIBLE,
        )


@pytest.fixture
def tools() -> dict[str, FakeTool]:
    """④ 「사용 도구」에 배정된 7종만 만듦. 배정 0건 5종은 만들지 않음."""
    return {
        "C-2": FakeTool(
            "C-2",
            "S-R11",
            {
                "recommendations": [
                    {
                        "recommendation_id": f"rec-{i}",
                        "menu_name": f"메뉴{i}",
                        "place_id": f"p{i}",
                        "reason_line": "이유",
                        "reason_detail": "상세",
                        "confidence_score": 0.9,
                    }
                    for i in range(1, 4)
                ],
                "model_call_id": "call-1",
            },
        ),
        "C-3": FakeTool(
            "C-3", "S-B5", {"candidate_vector": [0.1], "vector_model_version": "v1"}
        ),
        "C-4": FakeTool(
            "C-4",
            "S-R7",
            {
                "places": [
                    {
                        "place_id": f"p{i}",
                        "place_name": f"식당{i}",
                        "distance_m": 100 * i,
                        "walk_minutes": i,
                        "ingredient_codes": [],
                    }
                    for i in range(1, 4)
                ]
            },
        ),
        "C-7": FakeTool("C-7", "S-R6", {"weather_temp_c": 21.5, "weather_condition": "맑음"}),
        "C-8": FakeTool("C-8", "S-R8", {"business_status_by_place": {}}),
        "C-9": FakeTool(
            "C-9",
            "S-S9",
            {
                "payment_result": "성공",
                "payment_id": "pay-1",
                "next_billing_date": "2026-09-08",
                "pg_response_at": 1,
            },
            side_effect=SideEffect.WRITE_IRREVERSIBLE,
        ),
        "C-12": FakeTool(
            "C-12",
            "S-C10",
            {
                "pg_cancel_status": "중지완료",
                "pg_cancel_requested_at": 1,
                "cancel_schedule_id": "cs-1",
            },
            side_effect=SideEffect.WRITE_IRREVERSIBLE,
        ),
    }


@pytest.fixture
def make_context(settings, recorder, tools):
    """흐름 부품 묶음을 만드는 공장. 시험마다 입력·조회 결과만 갈아 끼움."""

    def factory(**overrides: Any) -> FlowContext:
        kwargs: dict[str, Any] = {
            "settings": overrides.pop("settings", settings),
            "recorder": overrides.pop("recorder", recorder),
            "tools": overrides.pop("tools", tools),
            "request_id": overrides.pop("request_id", "req-1"),
        }
        kwargs.update(overrides)
        return FlowContext(**kwargs)

    return factory
