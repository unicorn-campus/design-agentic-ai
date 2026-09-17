"""PDF 페이지별 메타데이터 누적 시험."""

import unittest

from app.infrastructure.pdf_reader import _metadata_from_pages, _normalize_d2_tables


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


if __name__ == "__main__":
    unittest.main()
