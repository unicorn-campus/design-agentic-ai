"""반드시 넣을 시험 1 — 읽기 계층에 원천을 바꾸는 구문이 0건임.

파이썬 메서드 이름(`dict.update` 같은 것)과 헷갈리지 않게 **SQL 문장 모양**으로 찾음.
낱말은 이어 붙여 적음 — 이 시험 파일 자체가 검사에 걸리지 않게 함.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from common.dataset.write_guard import NotReadOnly, ensure_read_only_query

DATASET_ROOT = Path(__file__).resolve().parents[2] / "dataset"

# 원천을 바꾸는 SQL 문장 모양. `이름 / 찾을 무늬 / 관문 시험에 넣을 문장` 3개씩임.
WRITE_STATEMENTS: tuple[tuple[str, str, str], ...] = (
    ("행 넣기", r"\bin" + r"sert\s+into\b", "in" + "sert into t values (1)"),
    ("행 바꾸기", r"\bup" + r"date\s+\w+\s+set\b", "up" + "date t set a = 1"),
    ("행 지우기", r"\bde" + r"lete\s+from\b", "de" + "lete from t"),
    ("표 비우기", r"\btr" + r"uncate\s+table\b", "tr" + "uncate table t"),
    ("표 없애기", r"\bdr" + r"op\s+table\b", "dr" + "op table t"),
    ("표 고치기", r"\bal" + r"ter\s+table\b", "al" + "ter table t add x int"),
    ("표 만들기", r"\bcr" + r"eate\s+table\b", "cr" + "eate table t (a int)"),
    ("권한 주기", r"\bgr" + r"ant\s+\w+\s+on\b", "gr" + "ant select on t to u"),
    ("합쳐 쓰기", r"\bme" + r"rge\s+into\b", "me" + "rge into t using s on (1=1)"),
    ("있으면 바꾸기", r"\bup" + r"sert\b", "up" + "sert t values (1)"),
)

WRITE_PATTERN = re.compile(
    "|".join(pattern for _, pattern, _ in WRITE_STATEMENTS), re.IGNORECASE
)


def _dataset_sources() -> list[Path]:
    return sorted(
        path for path in DATASET_ROOT.rglob("*.py") if "__pycache__" not in path.parts
    )


def test_dataset_sources_were_found() -> None:
    assert _dataset_sources(), "검사할 데이터 준비 소스를 못 찾음"


@pytest.mark.parametrize("path", _dataset_sources(), ids=lambda p: p.name)
def test_no_write_statement_in_source(path: Path) -> None:
    """시험 1 — 소스 어디에도 원천을 바꾸는 SQL 문장이 없음."""
    hits = WRITE_PATTERN.findall(path.read_text(encoding="utf-8"))
    assert not hits, f"{path.name}에 원천을 바꾸는 구문이 있음: {hits}"


@pytest.mark.parametrize(
    "statement", [statement for _, _, statement in WRITE_STATEMENTS]
)
def test_guard_rejects_write_query(statement: str) -> None:
    """관문이 바꾸는 문장을 실제로 막는지 확인함."""
    with pytest.raises(NotReadOnly):
        ensure_read_only_query(statement, "시험")


def test_guard_rejects_select_hiding_a_write_statement() -> None:
    hidden = WRITE_STATEMENTS[0][2]
    with pytest.raises(NotReadOnly):
        ensure_read_only_query(
            f"SELECT 1 FROM t WHERE x = 1 LIMIT %(row_cap)s; {hidden}", "시험"
        )


def test_guard_rejects_write_word_hidden_in_a_comment_free_tail() -> None:
    hidden = WRITE_STATEMENTS[1][2]
    with pytest.raises(NotReadOnly):
        ensure_read_only_query(f"SELECT 1 LIMIT %(row_cap)s /* x */ {hidden}", "시험")


def test_guard_rejects_query_without_row_cap_placeholder() -> None:
    with pytest.raises(NotReadOnly):
        ensure_read_only_query("SELECT a FROM t", "시험")


def test_guard_rejects_empty_query() -> None:
    with pytest.raises(NotReadOnly):
        ensure_read_only_query("   -- 주석만 있음", "시험")


def test_guard_accepts_capped_select() -> None:
    query = "SELECT a, b FROM t WHERE member_id = %(member_id)s LIMIT %(row_cap)s"
    assert ensure_read_only_query(query, "시험") == query


def test_guard_accepts_capped_with_clause() -> None:
    query = "WITH x AS (SELECT 1) SELECT * FROM x LIMIT %(row_cap)s"
    assert ensure_read_only_query(query, "시험") == query


def test_live_reader_opens_the_connection_read_only() -> None:
    """접속 자체를 읽기 전용으로 여는 줄이 실제로 있는지 확인함."""
    text = (DATASET_ROOT / "live_reader.py").read_text(encoding="utf-8")
    assert "conn.read_only = True" in text
