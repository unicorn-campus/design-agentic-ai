"""반드시 넣을 시험 3 · 4 — 쓰기 구문이 실행 전에 막히고, 행 수 상한이 반드시 붙음.

시험 3은 이 프로젝트에서 **질의 생성이 미채택**이므로 두 가지로 나눠 확인함.

- ⓐ 이 묶음의 소스 어디에도 원천을 바꾸는 SQL 문장이 없음(만들어지는 조회문이 0건임)
- ⓑ 밖에서 들어온 조회문에 쓰기 구문이 있으면 **실행 전에** 관문이 막음
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from common.config import Settings
from common.dataset import spec_of
from common.dataset.write_guard import NotReadOnly, ensure_read_only_query
from common.knowledge import lookup

KNOWLEDGE_ROOT = Path(__file__).resolve().parents[2] / "knowledge"

# 원천을 바꾸는 SQL 문장 모양. 낱말을 이어 붙여 적어 이 시험 파일이 스스로 걸리지 않게 함.
WRITE_STATEMENTS: tuple[tuple[str, str, str], ...] = (
    ("행 넣기", r"\bin" + r"sert\s+into\b", "in" + "sert into t values (1)"),
    ("행 바꾸기", r"\bup" + r"date\s+\w+\s+set\b", "up" + "date t set a = 1"),
    ("행 지우기", r"\bde" + r"lete\s+from\b", "de" + "lete from t"),
    ("표 비우기", r"\btr" + r"uncate\s+table\b", "tr" + "uncate table t"),
    ("표 없애기", r"\bdr" + r"op\s+table\b", "dr" + "op table t"),
    ("표 고치기", r"\bal" + r"ter\s+table\b", "al" + "ter table t add x int"),
    ("표 만들기", r"\bcr" + r"eate\s+table\b", "cr" + "eate table t (a int)"),
    ("권한 주기", r"\bgr" + r"ant\s+\w+\s+on\b", "gr" + "ant select on t to u"),
)

WRITE_PATTERN = re.compile("|".join(pattern for _, pattern, _ in WRITE_STATEMENTS), re.IGNORECASE)


def _knowledge_sources() -> list[Path]:
    return sorted(
        path for path in KNOWLEDGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts
    )


def test_knowledge_sources_were_found() -> None:
    assert _knowledge_sources(), "검사할 지식 경로 소스를 못 찾음"


@pytest.mark.parametrize("path", _knowledge_sources(), ids=lambda p: p.name)
def test_no_write_statement_in_knowledge_source(path: Path) -> None:
    """시험 3ⓐ — 소스 어디에도 원천을 바꾸는 SQL 문장이 없음."""
    hits = WRITE_PATTERN.findall(path.read_text(encoding="utf-8"))
    assert not hits, f"{path.name}에 원천을 바꾸는 구문이 있음: {hits}"


@pytest.mark.parametrize("statement", [text for _, _, text in WRITE_STATEMENTS])
def test_guard_blocks_write_query_before_running(statement: str) -> None:
    """시험 3ⓑ — 쓰기 구문은 실행 전에 관문이 막음."""
    with pytest.raises(NotReadOnly):
        ensure_read_only_query(statement, "지식 경로")


def test_guard_blocks_a_read_query_with_a_write_statement_appended() -> None:
    hidden = WRITE_STATEMENTS[0][2]
    with pytest.raises(NotReadOnly):
        ensure_read_only_query(f"SELECT 1 FROM t LIMIT %(row_cap)s; {hidden}", "지식 경로")


def test_knowledge_layer_exposes_no_write_function() -> None:
    """조회 계층에 넣기·바꾸기·지우기 함수가 0건임."""
    import common.knowledge as knowledge

    write_like = [
        name
        for name in knowledge.__all__
        if any(
            word in name.lower()
            for word in ("write", "save", "commit", "erase", "purge", "upsert")
        )
    ]
    assert write_like == []


def test_row_cap_is_attached_to_every_lookup(
    knowledge_settings: Settings, seed_reader
) -> None:
    """시험 4 — 상한을 안 적어도 상한이 붙어서 읽힘."""
    result = lookup("T-5", "R-14", seed_reader, params={"member_id": "M000000"},
                    settings=knowledge_settings)
    cap = knowledge_settings.dataset_row_cap_for("T-5")
    assert result.candidate_count <= cap
    assert any(str(cap) in note for note in result.notes)


def test_requested_limit_over_cap_is_lowered_to_cap(
    knowledge_settings: Settings, seed_reader
) -> None:
    cap = knowledge_settings.dataset_row_cap_for("T-5")
    result = lookup(
        "T-5",
        "R-14",
        seed_reader,
        params={"member_id": "M000000"},
        limit=cap * 2,
        settings=knowledge_settings,
    )
    assert result.candidate_count <= cap


def test_lookup_without_row_cap_setting_refuses(
    knowledge_env: None, monkeypatch: pytest.MonkeyPatch, seed_reader
) -> None:
    """상한이 설정에 없는 경로는 읽지 않음 — 숫자를 짐작하지 않음."""
    from common.config import SettingsMissing, load_settings

    monkeypatch.setenv("LUNCHPICK_DATASET_ROW_CAP", "{}")
    thin = load_settings()
    with pytest.raises(SettingsMissing):
        lookup("T-5", "R-14", seed_reader, settings=thin)


def test_lookup_columns_never_exceed_path_spec(
    knowledge_settings: Settings, seed_reader
) -> None:
    """조회문에 넣는 열이 ⑤ 3절 경로 표 열 목록 안에만 있음."""
    result = lookup("T-9", "R-14", seed_reader, params={"member_id": "M000000"},
                    settings=knowledge_settings)
    spec = spec_of("T-9")
    for payload in result.payloads():
        assert set(payload) <= set(spec.columns)
