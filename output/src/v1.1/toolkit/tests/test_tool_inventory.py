"""도구 목록 대조 — ④ 「사용 도구」 행과 만든 도구 수를 숫자로 맞춰 봄.

여기 적은 기대값은 전부 ④ 역할계약서 3절 「사용 도구」 칸에서 옮긴 것임.
"""

from __future__ import annotations

import pytest

from common.config import Settings
from services import registry
from toolkit.errors import ConnectorNotConfigured
from toolkit.schema import SideEffect
from toolkit.settings import ToolSettings

# ④ 3절 「사용 도구」에 실제로 적힌 커넥터(=바깥 시스템에 붙는 도구)와 그 3값 표시
ASSIGNED_CONNECTORS: dict[str, tuple[str, SideEffect]] = {
    "C-2": ("R-1", SideEffect.READ),
    "C-3": ("R-3", SideEffect.READ),
    "C-4": ("R-2", SideEffect.READ),
    "C-7": ("R-2", SideEffect.READ),
    "C-8": ("R-2", SideEffect.READ),
    "C-9": ("R-8", SideEffect.WRITE_IRREVERSIBLE),
    "C-12": ("R-10", SideEffect.WRITE_IRREVERSIBLE),
}

# ④ 「사용 도구」에 `커넥터 아님`으로 적힌 항목 — 이 프롬프트 범위 밖(`03-knowledge.md` 몫)
OUT_OF_SCOPE_ROWS: tuple[str, ...] = (
    "T-1 member_profile 조회",
    "T-2 diet_restriction 조회",
    "T-3 consent_log 조회",
    "T-4 meal_history 조회",
    "T-5 meal_history 30일 달력 뷰 조회",
    "T-6 feedback 조회",
    "T-8 accept_reject_log 조회",
    "T-9 insight_agg 집계 뷰 조회",
    "T-10 preference_vector 조회",
    "T-11 recommendation_cache 조회",
    "T-12 subscription 조회",
    "⑤ 5절 K-3ⓑ 알레르겐 라벨 → 제외 식재료 코드 사전 조회",
    "S-1 회원 저장소 쓰기(서비스 쓰기 API)",
    "S-3 이력 저장소 쓰기(서비스 쓰기 API)",
    "S-4 취향 벡터 인덱스 쓰기(서비스 쓰기 API)",
    "S-5 추천 캐시 적재(서비스 쓰기 API)",
    "S-6 감사 로그 적재(서비스 쓰기 API)",
    "S-7 결제 저장소 쓰기(서비스 쓰기 API)",
)

# ④가 이름을 짓지 않고 `[확인필요]`로 둔 수단 2건 — 도구를 지어내지 않음
UNNAMED_ROWS: tuple[str, ...] = (
    "[확인필요: 온보딩 스와이프 결과 조회 경로와 초기 취향 벡터 생성 수단](R-6)",
    "[확인필요: 구독 플랜 가격 캐시의 보관 위치](R-12)",
)


def test_made_connector_count_matches_assigned_rows() -> None:
    assert set(registry.TOOL_SPECS) == set(ASSIGNED_CONNECTORS)
    assert len(registry.TOOL_SPECS) == 7


def test_row_arithmetic_adds_up() -> None:
    """④ 행 수 = 만든 도구 + 범위 밖 + 이름 없음. 제외 건수를 숫자로 적음."""
    made = len(registry.TOOL_SPECS)
    out_of_scope = len(OUT_OF_SCOPE_ROWS)
    unnamed = len(UNNAMED_ROWS)
    assert (made, out_of_scope, unnamed) == (7, 18, 2)
    assert made + out_of_scope + unnamed == 27


def test_every_tool_has_a_side_effect_value() -> None:
    """읽기·쓰기 구분에 공란 0건. 3값 중 하나임."""
    for connector_id, spec in registry.TOOL_SPECS.items():
        expected_role, expected_effect = ASSIGNED_CONNECTORS[connector_id]
        assert spec.side_effect is expected_effect
        assert spec.side_effect.value in {
            "읽기",
            "쓰기(되돌림 가능)",
            "쓰기(되돌림 불가)",
        }
        assert spec.owner_role == expected_role


def test_irreversible_writes_carry_approval_and_idempotency() -> None:
    irreversible = [
        spec
        for spec in registry.TOOL_SPECS.values()
        if spec.side_effect is SideEffect.WRITE_IRREVERSIBLE
    ]
    assert len(irreversible) == 2
    for spec in irreversible:
        assert spec.approval_marks, f"{spec.connector_id}: 승인 표시 요구가 비어 있음"
        assert spec.idempotency_key_field
        assert spec.unresolved_marker is not None


def test_read_tools_have_no_idempotency_key() -> None:
    for spec in registry.TOOL_SPECS.values():
        if spec.side_effect is SideEffect.READ:
            assert spec.idempotency_key_field is None


def test_unassigned_connectors_are_not_callable(
    tool_settings: ToolSettings, runtime_settings: Settings
) -> None:
    """⑤ 6절 12종 중 배정 0건 5종은 도구로 만들지 않았음 — 부르려 하면 막힘."""
    assert set(registry.UNASSIGNED_CONNECTORS) == {"C-1", "C-5", "C-6", "C-10", "C-11"}
    for connector_id in registry.UNASSIGNED_CONNECTORS:
        with pytest.raises(ConnectorNotConfigured, match="호출 가능한 도구가 아님"):
            registry.build_adapter(connector_id, tool_settings, runtime_settings)


def test_connector_total_matches_design_five_section() -> None:
    """⑤ 6절 커넥터 단위 수 12 = 만든 7 + 배정 0건 5."""
    assert len(registry.TOOL_SPECS) + len(registry.UNASSIGNED_CONNECTORS) == 12


def test_every_tool_has_usage_condition_and_source() -> None:
    for spec in registry.TOOL_SPECS.values():
        assert spec.usage_condition.strip()
        assert spec.design_source.strip()
        assert spec.requested_scopes, f"{spec.connector_id}: 요청 범위가 비어 있음"
