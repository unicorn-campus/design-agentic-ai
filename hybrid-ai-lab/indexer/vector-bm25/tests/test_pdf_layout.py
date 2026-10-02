"""PDF 레이아웃 정제(접힌 줄 복원·표 Markdown 변환)의 판정 규칙을 검증함."""

from __future__ import annotations

from app.infrastructure.pdf_layout import LineJoiner, join_page_rows, normalize_d2_tables, row_text


class _FakeSpacer:
    """Kiwi 대신 정해 둔 띄어쓰기 결과를 돌려주는 가짜 분석기임."""

    def __init__(self, spaced: str) -> None:
        self.spaced = spaced
        self.calls = 0

    def space(self, text: str) -> str:
        self.calls += 1
        return self.spaced


def test_short_line_keeps_newline_and_full_line_is_joined_by_document_vote() -> None:
    """오른쪽 끝에 못 미친 줄은 줄바꿈을 유지하고, 끝까지 찬 줄은 문서 다수결로 붙임을 보증함."""
    joiner = LineJoiner(reference="반환 기준액을 계산함\n기준액은 남은 일수로 정함", right_edge=500.0)
    rows = [
        (10.0, "제1조(목적)", 120.0),  # 짧은 제목 줄 → 문단 끝
        (20.0, "연회비 반환 기", 500.0),  # 오른쪽 끝까지 찬 줄 → 접힌 줄
        (30.0, "준액을 계산함", 300.0),
    ]
    assert join_page_rows(rows, joiner) == "제1조(목적)\n연회비 반환 기준액을 계산함"


def test_kiwi_is_asked_only_when_document_has_no_evidence() -> None:
    """문서 근거가 없을 때만 띄어쓰기 분석기에 묻고 이음매 자리의 공백만 반영함을 보증함."""
    spacer = _FakeSpacer("가나다 라마바")
    joiner = LineJoiner(reference="", right_edge=500.0, spacer_factory=lambda: spacer)
    rows = [(10.0, "가나다", 500.0), (20.0, "라마바", 200.0)]
    assert join_page_rows(rows, joiner) == "가나다 라마바"
    assert spacer.calls == 1


def test_markdown_table_block_is_never_joined() -> None:
    """오른쪽 좌표가 없는 Markdown 표 덩어리는 앞뒤 줄과 줄바꿈으로만 이어짐을 보증함."""
    joiner = LineJoiner(right_edge=500.0)
    rows = [(10.0, "요금표", 500.0), (20.0, "| 구분 | 금액 |\n| --- | --- |", None), (30.0, "끝", 100.0)]
    assert join_page_rows(rows, joiner) == "요금표\n| 구분 | 금액 |\n| --- | --- |\n끝"


def test_row_text_marks_distant_cells_with_separator() -> None:
    """같은 높이에서 멀리 떨어진 조각은 칸 구분자로 이어 표 행으로 표시됨을 보증함."""
    lines = [((10.0, 100.0, 60.0, 110.0), "기본"), ((200.0, 100.0, 260.0, 110.0), "6,000")]
    assert row_text(lines) == [(100.0, "기본 | 6,000", 260.0)]


def test_d2_card_index_rows_and_wrapped_header_become_one_table() -> None:
    """카드 목록표의 행은 카드 머리글로 오인하지 않고, 접힌 머리글 칸은 머리글에 붙음을 보증함."""
    text = "\n".join(
        [
            "카드 찾아보기 (1-16)",
            "자료 ID | 가상 카드명 | 안내 항목",
            "수",
            "D2-C001 | 한빛 모아생활 | 3",
            "D2-C002 | 한빛 모아생활 플러스 | 4",
            "PDF 검색에서 자료 ID 또는 카드명으로 해당 안내를 찾을 수 있음.",
        ]
    )
    converted, count = normalize_d2_tables(text)
    assert count == 1
    assert converted.splitlines()[1:5] == [
        "| 자료 ID | 가상 카드명 | 안내 항목 수 |",
        "| --- | --- | --- |",
        "| D2-C001 | 한빛 모아생활 | 3 |",
        "| D2-C002 | 한빛 모아생활 플러스 | 4 |",
    ]
    assert converted.splitlines()[-1].startswith("PDF 검색")


def test_d2_benefit_heading_outside_table_is_kept_as_heading() -> None:
    """표 밖의 혜택 머리글(칸 구분자 1개)은 표로 바꾸지 않고 다음 표만 변환함을 보증함."""
    text = "D2-C001-B01 | 생활 포인트 적립\n항목 | 합성 조건\n혜택 | 1.2% 적립"
    converted, count = normalize_d2_tables(text)
    assert count == 1
    assert converted.splitlines() == [
        "D2-C001-B01 | 생활 포인트 적립",
        "| 항목 | 합성 조건 |",
        "| --- | --- |",
        "| 혜택 | 1.2% 적립 |",
    ]
