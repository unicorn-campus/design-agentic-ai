"""README와 코드가 어긋나지 않게 못 박음.

`[확인필요]` 건수 · 되묻기 값 건수 · 도구 명세 표 행 수 · 요청 범위 전건 기재를 세어 봄.
"""

from __future__ import annotations

import re
from pathlib import Path

import toolkit
from services import registry
from toolkit.schema import SideEffect

README = Path(toolkit.__file__).resolve().parent / "README.md"


def _section(title_prefix: str) -> str:
    text = README.read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.MULTILINE)
    for part in parts:
        if part.startswith(title_prefix):
            return part
    raise AssertionError(f"README에 '{title_prefix}' 절이 없음")


def _table_rows(section: str) -> list[str]:
    rows: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if set(stripped) <= set("|-: "):
            continue  # 표 구분선
        rows.append(stripped)
    return rows


def test_unconfirmed_count_matches_the_stated_number() -> None:
    section = _section("8. `[확인필요]` 목록")
    stated = re.search(r"\*\*(\d+)건\*\*", section)
    assert stated is not None, "README 8절에 건수가 숫자로 적혀 있지 않음"
    rows = _table_rows(section)[1:]  # 머리 행 제외
    assert len(rows) == int(stated.group(1)) == 7


def test_asked_back_values_are_four_rows() -> None:
    section = _section("7. 되묻기로 정한 값")
    rows = _table_rows(section)[1:]
    assert len(rows) == 4


def test_tool_spec_table_lists_every_made_tool() -> None:
    section = _section("3. 도구 명세 표")
    for connector_id in registry.TOOL_SPECS:
        assert f"`{connector_id}` " in section, f"{connector_id}가 도구 명세 표에 없음"


def test_every_requested_scope_is_written_in_the_readme() -> None:
    """최소 권한 — 요청한 범위가 README 표에 **전건** 적혀 있음."""
    text = README.read_text(encoding="utf-8")
    missing: list[str] = []
    for spec in registry.TOOL_SPECS.values():
        for scope in spec.requested_scopes:
            if scope not in text:
                missing.append(f"{spec.connector_id}:{scope}")
    assert missing == [], f"README에 안 적힌 요청 범위: {missing}"


def test_unassigned_connectors_are_named_in_the_readme() -> None:
    text = README.read_text(encoding="utf-8")
    for connector_id in registry.UNASSIGNED_CONNECTORS:
        assert f"`{connector_id}`" in text


def test_readme_declares_unverified_design() -> None:
    """실물 호출 시험을 하지 않았으므로 머리에 `미검증 설계`가 적혀 있어야 함."""
    head = README.read_text(encoding="utf-8").splitlines()[0]
    assert "미검증 설계" in head


def test_readme_states_the_single_retry_layer() -> None:
    section = _section("4. 오류 분류표")
    assert "1개뿐임" in section
    assert "call_with_limits" in section


def test_side_effect_labels_in_readme_match_the_specs() -> None:
    section = _section("1. 개요")
    for spec in registry.TOOL_SPECS.values():
        row = next(
            line for line in _table_rows(section) if f"`{spec.connector_id}` " in line
        )
        if spec.side_effect is SideEffect.WRITE_IRREVERSIBLE:
            assert "쓰기(되돌림 불가)" in row, spec.connector_id
        else:
            assert "읽기" in row, spec.connector_id


def test_live_call_marker_count_is_reported_honestly() -> None:
    """`live_call` 표식이 붙은 시험이 실제로 0건이며 README가 그렇게 적었음."""
    tests_dir = Path(toolkit.__file__).resolve().parent / "tests"
    marker = "@pytest.mark." + "live_call"
    marked = [
        path.name
        for path in tests_dir.glob("test_*.py")
        if marker in path.read_text(encoding="utf-8")
    ]
    assert marked == []
    assert "`live_call` 표식이 붙은 시험이 0건임" in README.read_text(encoding="utf-8")
