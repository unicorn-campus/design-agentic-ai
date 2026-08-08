"""시험 1 — ② 판정 2-2 「경계 미통과 항목」의 이름이 도구 스키마에 **0건**.

가리기(마스킹)로 대신한 행도 0건임을 함께 확인함 — 칸 자체가 없어야 통과함.
"""

from __future__ import annotations

import pytest

from services import registry
from toolkit.boundary import forbidden_keys_for
from toolkit.schema import CredentialKind, SideEffect, ToolPayload, ToolSpec

# ② 판정 2-2 7행을 코드에서 찾을 수 있는 이름 후보로 펼친 것
BOUNDARY_ROWS: dict[str, tuple[str, ...]] = {
    "알레르겐 원문 라벨": ("allergyItems", "allergy_items"),
    "이메일 · 카카오 ID": ("email", "kakao_id"),
    "정확 위치 좌표(TB-2 한정)": ("origin_lat", "origin_lng", "dest_lat", "dest_lng"),
    "카드번호 · 유효기간 · CVC": ("card_number", "cardNumber", "card_expiry", "cvc"),
    "식이 유형": ("diet_type", "dietType"),
    "인증 토큰(JWT · 카카오 토큰)": ("jwt", "access_token", "kakao_access_token"),
    "닉네임": ("nickname",),
}

# ②가 좌표를 넘기기로 판정한 경로 — 여기만 좌표 칸을 가짐(TB-3)
COORDINATE_ALLOWED = {"C-4", "C-7"}


def test_seven_boundary_rows_are_zero_in_every_tool_schema() -> None:
    hits: list[str] = []
    for connector_id, spec in registry.TOOL_SPECS.items():
        blocked = forbidden_keys_for(spec.trust_boundary)
        names = set(spec.input_key_names) | set(spec.output_key_names)
        for row, candidates in BOUNDARY_ROWS.items():
            for candidate in candidates:
                if candidate not in names:
                    continue
                if candidate not in blocked and connector_id in COORDINATE_ALLOWED:
                    continue  # ②가 넘기기로 판정한 경로임
                hits.append(f"{connector_id}/{row}/{candidate}")
    assert hits == [], f"경계 미통과 항목이 스키마에 있음: {hits}"


def test_card_fields_are_zero_everywhere_including_payment_tools() -> None:
    """카드번호 · 유효기간 · CVC는 결제 커넥터에도 칸이 없고 `payment_token`만 있음."""
    payment = registry.TOOL_SPECS["C-9"]
    assert "payment_token" in payment.input_key_names
    for name in ("card_number", "cardNumber", "card_expiry", "cvc"):
        assert name not in payment.input_key_names
    stop = registry.TOOL_SPECS["C-12"]
    assert not (set(stop.input_key_names) & {"payment_token", "card_number", "cvc"})


def test_model_vendor_tools_have_no_coordinates_or_labels() -> None:
    """TB-2(모델 벤더)로 나가는 `C-2`는 좌표·알레르겐 원문·닉네임 칸이 없고 대체 키만 가짐."""
    spec = registry.TOOL_SPECS["C-2"]
    names = set(spec.input_key_names)
    assert not (names & {"origin_lat", "origin_lng", "allergyItems", "nickname", "email"})
    assert "region_label" in names
    assert "excluded_ingredient_codes" in names


def test_registering_a_forbidden_key_fails_loudly() -> None:
    """표가 살아 있는지 확인 — 금지된 칸을 만든 도구는 등록 시점에 실패함."""

    class Bad(ToolPayload):
        allergyItems: list[str]  # noqa: N815 - 일부러 금지된 이름을 씀

    with pytest.raises(ValueError, match="경계 미통과 항목"):
        ToolSpec(
            connector_id="C-시험",
            display_name="시험용",
            external_service="(E)시험",
            trust_boundary="TB-2",
            side_effect=SideEffect.READ,
            usage_condition="시험용",
            step_id="S-R11",
            owner_role="R-0",
            owning_service="시험",
            input_model=Bad,
            output_model=None,
            credential_kind=CredentialKind.API_KEY,
            requested_scopes=("test.read",),
            preconditions=(),
            strict_order=False,
        )
