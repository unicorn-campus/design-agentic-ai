"""Extraction guarantees using small generated PDFs and the supplied corpus."""
from collections import Counter
from pathlib import Path
import re
import tempfile
import unittest
import pymupdf

from docprep.infrastructure.pdf_reader import extract_pdf


class PDFReaderTests(unittest.TestCase):
    def test_margin_removal_keeps_body_and_option(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "example.pdf"
            pdf = pymupdf.open()
            for number in range(1, 4):
                page = pdf.new_page()
                page.insert_text((40, 25), "Repeated header")
                page.insert_text((40, 120), "Repeated body must remain")
                page.insert_text((40, 820), str(number))
            pdf.save(path)
            pdf.close()
            cleaned, report = extract_pdf(path)
            raw, raw_report = extract_pdf(path, False)
            self.assertEqual(report["removed_lines"], 6)
            self.assertEqual(raw_report["removed_lines"], 0)
            self.assertNotIn("Repeated header", cleaned[0]["page_content"])
            self.assertIn("Repeated body must remain", cleaned[0]["page_content"])
            self.assertIn("Repeated header", raw[0]["page_content"])
            self.assertEqual([item["metadata"]["page"] for item in cleaned], [1, 2, 3])

    def test_no_text_reports_no_ocr(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "blank.pdf"
            with pymupdf.open() as pdf:
                pdf.new_page()
                pdf.save(path)
            documents, report = extract_pdf(path)
            self.assertEqual(documents[0]["page_content"], "")
            self.assertTrue(any("OCR" in warning for warning in report["warnings"]))

    def test_supplied_corpus_glyphs_fees_and_conditions(self):
        folder = Path(__file__).resolve().parents[2] / "docs"
        paths = sorted(folder.glob("D[12]*.pdf"))
        if len(paths) != 2:
            self.skipTest("Supplied D1/D2 corpus not installed")
        for path, expected_pages in zip(paths, (15, 196)):
            documents, report = extract_pdf(path)
            self.assertEqual(len(documents), expected_pages)
            removed = {}
            for item in report["removed_line_details"]:
                removed.setdefault(item["page"], []).append(item["text"])
            with pymupdf.open(path) as pdf:
                for page_number, (page, document) in enumerate(zip(pdf, documents), 1):
                    # All non-layout source characters survive exactly once;
                    # pipes/backslashes/hyphens are Markdown formatting characters.
                    normalize = lambda text: Counter(re.sub(r"[\s|\\-]", "", text))
                    source = normalize(page.get_text())
                    source.subtract(normalize("".join(removed.get(page_number, []))))
                    self.assertEqual(+source, normalize(document["page_content"]), (path.name, page_number))
            self.assertEqual(documents[0]["metadata"]["effective_date"], "2027-01-15")
            expected_created = "2026-09-10" if path.name.startswith("D1") else "2026-09-09"
            self.assertEqual(documents[0]["metadata"]["created_at"], expected_created)
            if path.name.startswith("D1"):
                self.assertEqual(documents[0]["metadata"]["version"], "1.2")
                full_text = "\n".join(document["page_content"] for document in documents)
                self.assertIn("제10조(연회비 면제 및 계약 해지에 따른 반환)", full_text)
                self.assertIn("직전 12개월 이용금액이 3,000,000원 이상", full_text)
            if path.name.startswith("D2"):
                page = documents[6]["page_content"]
                self.assertIn("국내전용 | 6,000 | 16,000 | 22,000", page)
                self.assertIn("해외 A | 6,000 | 19,000 | 25,000", page)
                self.assertIn("혜택 제외 |", page)
                self.assertEqual(documents[6]["metadata"]["product_id"], "D2-C001")


if __name__ == "__main__":
    unittest.main()
