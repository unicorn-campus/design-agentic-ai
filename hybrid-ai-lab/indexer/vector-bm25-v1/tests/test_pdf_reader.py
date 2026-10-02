"""PDF 페이지별 메타데이터 누적 시험."""

import unittest

from app.infrastructure.pdf_reader import (
    _metadata_from_pages,
    _normalize_d2_tables,
    _row_text,
    build_line_joiner,
    join_page_rows,
)


RECTANGLE = (0.0, 0.0, 100.0, 20.0)


class PdfMetadataTests(unittest.TestCase):
    def test_collects_metadata_without_combining_all_pages(self):
        page_lines = [
            [
                (RECTANGLE, "시행일: 2027-01-15"),
                (RECTANGLE, "버전: 2.1"),
            ],
            [
                (RECTANGLE, "작성일: 2026-03-14"),
                (RECTANGLE, "공개 등급: 교육용 공개"),
                (RECTANGLE, "합성 데이터"),
            ],
        ]

        metadata = _metadata_from_pages(page_lines, "D1_sample.pdf")

        self.assertEqual(metadata["source"], "D1_sample.pdf")
        self.assertEqual(metadata["doc_type"], "regulation")
        self.assertEqual(metadata["effective_date"], "2027-01-15")
        self.assertEqual(metadata["version"], "2.1")
        self.assertEqual(metadata["created_at"], "2026-03-14")
        self.assertNotIn("access_level", metadata)
        self.assertTrue(metadata["synthetic"])

    def test_uses_pdf_creation_date_when_source_has_no_created_at(self):
        page_lines = [[
            (RECTANGLE, "시행일: 2027-01-15"),
            (RECTANGLE, "버전: 2.1"),
        ]]

        metadata = _metadata_from_pages(
            page_lines,
            "D2_sample.pdf",
            "D:20260314091500+09'00'",
        )

        self.assertEqual(metadata["created_at"], "2026-03-14")
        self.assertEqual(
            metadata["created_at_origin"],
            "pdf_creationDate (file creation, not business publication)",
        )


class PdfTableTests(unittest.TestCase):
    def test_normalizes_d2_table_but_keeps_benefit_heading(self):
        text = "\n".join((
            "D2-C058-B04 | 반려생활 제휴",
            "항목 | 합성 조건",
            "혜택 | 대상 결제액의 4%를 할인함.",
            "실적 조건 | 전월 이용액 350,000원 이상. 세금은 실적",
            "에서 제외함.",
            "모든 명칭은 교육용 가정임.",
        ))

        normalized, count = _normalize_d2_tables(text)

        self.assertEqual(count, 1)
        self.assertIn("D2-C058-B04 | 반려생활 제휴", normalized)
        self.assertIn("| 항목 | 합성 조건 |\n| --- | --- |", normalized)
        self.assertIn("| 실적 조건 | 전월 이용액 350,000원 이상. 세금은 실적 에서 제외함. |", normalized)

    def test_does_not_duplicate_existing_markdown_separator(self):
        text = "\n".join((
            "| 항목 | 합성 조건 |",
            "| --- | --- |",
            "| 혜택 | 대상 결제액의 4%를 할인함. |",
        ))

        normalized, count = _normalize_d2_tables(text)

        self.assertEqual(count, 0)
        self.assertEqual(normalized.count("| --- | --- |"), 1)


# 접힌 줄 복원 시험에서 쓰는 페이지 폭. 오른쪽 끝을 520으로 두고,
# 520에서 끝나는 행은 "폭이 차서 접힌 줄", 그보다 훨씬 왼쪽에서 끝나는 행은
# "문단·문장이 끝난 줄"로 읽히게 함.
FULL_WIDTH = 520.0
SHORT_WIDTH = 300.0


def row(text, right=FULL_WIDTH):
    """(세로 좌표, 텍스트, 오른쪽 끝 좌표) 한 행을 만듦. 세로 좌표는 순서만 맞으면 됨."""

    return (0.0, text, right)


def joiner_for(*reference_texts):
    """판정 기준을 만듦.

    오른쪽 한계를 FULL_WIDTH로 고정하기 위해 폭이 꽉 찬 줄을 하나 끼워 넣음. 실제 문서에는
    이런 줄이 늘 있지만 시험 자료에는 없어서, 없으면 짧은 줄만으로 한계가 정해져 버림.
    """

    lines = [((0.0, 0.0, FULL_WIDTH, 20.0), "폭 기준 줄")]
    lines += [(RECTANGLE, text) for text in reference_texts]
    return build_line_joiner([lines])


class JoinWrappedLinesTests(unittest.TestCase):
    """폭이 차서 접힌 줄을 원래 문장으로 되돌리는지 확인함."""

    def test_short_line_is_treated_as_paragraph_end(self):
        # 1단계: 오른쪽 끝까지 차지 않은 행 뒤에는 줄바꿈을 유지해야 함.
        joiner = joiner_for()
        rows = [row("제10조(연회비)", SHORT_WIDTH), row("회사는 연회비를 청구합니다.", SHORT_WIDTH)]

        self.assertEqual("제10조(연회비)\n회사는 연회비를 청구합니다.", join_page_rows(rows, joiner))

    def test_word_split_by_wrap_is_glued_using_document_evidence(self):
        # 2단계: 같은 문서 다른 줄에 "반환 기준액"이 붙어 있으므로 붙여야 함.
        # 이것이 인용 검증을 실패하게 만들었던 실제 사례임.
        joiner = joiner_for("반환 기준액은 잔여 일수로 계산합니다.", "반환 기준액 산정")
        rows = [row("남은 일수에 비례하여 반환 기"), row("준액을 계산합니다.", SHORT_WIDTH)]

        self.assertEqual("남은 일수에 비례하여 반환 기준액을 계산합니다.", join_page_rows(rows, joiner))

    def test_phrase_split_by_wrap_keeps_the_space(self):
        # 2단계: 문서가 "한도를 조정할"처럼 띄어 쓰므로 공백을 넣어야 함.
        joiner = joiner_for("회사는 한도를 조정할 수 있습니다.")
        rows = [row("이용 범위나 한도를"), row("조정할 수 있습니다.", SHORT_WIDTH)]

        self.assertEqual("이용 범위나 한도를 조정할 수 있습니다.", join_page_rows(rows, joiner))

    def test_document_evidence_beats_general_korean_rules(self):
        # 2단계의 존재 이유: 일반 한국어 규칙은 "본인 회원"으로 떼지만
        # 이 약관의 용어는 "본인회원"임. 문서에 있는 용례를 따라야 함.
        joiner = joiner_for("본인회원과 가족회원은 구분됩니다.")
        rows = [row("처리 결과를 본인"), row("회원에게 안내합니다.", SHORT_WIDTH)]

        self.assertEqual("처리 결과를 본인회원에게 안내합니다.", join_page_rows(rows, joiner))

    def test_falls_back_to_analyzer_when_document_has_no_evidence(self):
        # 3단계: 문서에 용례가 없으면 형태소 분석기가 이음매만 판정함.
        rows = [row("회원은 연회비를"), row("면제받을 수 있습니다.", SHORT_WIDTH)]

        self.assertEqual("회원은 연회비를 면제받을 수 있습니다.", join_page_rows(rows, joiner_for()))

    def test_non_hangul_boundary_gets_a_space(self):
        # 숫자·영문이 섞인 자리는 애매하지 않으므로 공백을 넣어 안전하게 처리함.
        rows = [row("연회비는 10,000"), row("원입니다.", SHORT_WIDTH)]

        self.assertEqual("연회비는 10,000 원입니다.", join_page_rows(rows, joiner_for()))

    def test_markdown_table_is_never_joined(self):
        # 표는 줄바꿈이 곧 구조라 앞뒤로 반드시 끊어야 함. 오른쪽 좌표 None이 그 표시임.
        rows = [
            row("아래 표를 참고합니다."),
            (1.0, "| 항목 | 금액 |\n| --- | --- |", None),
            row("표 아래 설명입니다."),
        ]

        self.assertEqual(
            "아래 표를 참고합니다.\n| 항목 | 금액 |\n| --- | --- |\n표 아래 설명입니다.",
            join_page_rows(rows, joiner_for()),
        )

    def test_borderless_table_rows_are_never_joined(self):
        # D2의 테두리 없는 표는 선이 없어 표로 감지되지 않고 "셀 | 셀" 행으로 들어옴.
        # 폭이 꽉 찬 행이라 이으면 한 행에 칸이 두 벌 들어가 표가 밀림.
        rows = [
            row("| 리필 조건 | 7,000P 이상 사용하면 700P를 리필함. |"),
            row("| 대상 포인트 | 실제 사용분만 집계함. |", SHORT_WIDTH),
        ]

        self.assertEqual(
            "| 리필 조건 | 7,000P 이상 사용하면 700P를 리필함. |\n| 대상 포인트 | 실제 사용분만 집계함. |",
            join_page_rows(rows, joiner_for()),
        )

    def test_text_flowing_out_of_a_table_cell_is_joined(self):
        # 같은 표 안에서 칸의 글이 폭에 밀려 다음 줄로 흘러내린 모양. 다음 행에 칸 구분자가
        # 없으므로 이어야 하며, 그래야 "실적 에서"처럼 갈라진 낱말이 복원됨.
        joiner = joiner_for("전월 이용액은 실적에서 제외함.")
        rows = [
            row("| 실적 조건 | 전월 국내외 이용액 350,000원 이상. 취소액은 실"),
            row("에서 제외함. |", SHORT_WIDTH),
        ]

        self.assertEqual(
            "| 실적 조건 | 전월 국내외 이용액 350,000원 이상. 취소액은 실에서 제외함. |",
            join_page_rows(rows, joiner),
        )

    def test_row_text_reports_the_right_edge_of_a_row(self):
        # _row_text가 오른쪽 끝 좌표를 함께 돌려줘야 1단계 판정이 가능함.
        lines = [((10.0, 100.0, 200.0, 120.0), "왼쪽"), ((230.0, 100.0, 480.0, 120.0), "오른쪽")]

        self.assertEqual([(100.0, "왼쪽 | 오른쪽", 480.0)], _row_text(lines))


if __name__ == "__main__":
    unittest.main()
