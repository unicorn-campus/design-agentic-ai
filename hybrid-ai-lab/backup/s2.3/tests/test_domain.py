"""실제 합성 원문 48건 및 변형 입력에 대한 도메인 회귀 검사."""
import copy
import json
from pathlib import Path
import re
import unittest

from docprep.domain.consultations import parse_consultations, to_pseudo
from docprep.domain.validation import validate_document

DOCS = Path(__file__).resolve().parents[2] / "docs"


class ConsultationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = sorted(DOCS.glob("D3_S*.txt"))
        cls.expected = json.loads((DOCS / "_instructor/D3/정제검증_기대값.json").read_text(encoding="utf-8"))
        cls.documents = [doc for p in cls.paths for doc in parse_consultations(p.read_text(encoding="utf-8"), p.name, pseudonymize=True)]

    def test_corpus_counts_and_identity_link(self):
        self.assertEqual(len(self.paths), 6)
        self.assertEqual(len(self.documents), 48)
        self.assertEqual(len({d["metadata"]["member_pseudo_id"] for d in self.documents}), 12)
        by_id = {d["metadata"]["record_id"]: d for d in self.documents}
        for expected in self.expected:
            doc = by_id[expected["record_id"]]
            self.assertEqual(doc["metadata"]["member_pseudo_id"], to_pseudo(expected["member_id"]))
            self.assertEqual(doc["metadata"]["age_band"], expected["expected_age_band"])
            self.assertEqual(len(doc["page_content"].splitlines()), expected["utterance_count"])
            self.assertEqual(validate_document(doc), [], expected["record_id"])

    def test_no_known_pii_in_any_metadata_or_dialogue(self):
        by_id = {d["metadata"]["record_id"]: d for d in self.documents}
        for expected in self.expected:
            value = json.dumps(by_id[expected["record_id"]], ensure_ascii=False)
            for key, pii in expected["synthetic_pii"].items():
                if key == "age":
                    self.assertNotRegex(value, rf"(?:만\s*)?{pii}\s*세")
                elif key == "last4":
                    self.assertNotRegex(value, r"(?<![\d,./-])" + re.escape(str(pii)) + r"(?![\d,./-]|\s*원)")
                else:
                    self.assertNotIn(str(pii), value, (expected["record_id"], key))

    def test_business_amounts_dates_and_topics_preserved(self):
        for path in self.paths:
            raw = parse_consultations(path.read_text(encoding="utf-8"), path.name)
            clean = parse_consultations(path.read_text(encoding="utf-8"), path.name, pseudonymize=True)
            for before, after in zip(raw, clean):
                for amount in re.findall(r"\d[\d,]*원", before["page_content"]):
                    self.assertIn(amount, after["page_content"])
                self.assertEqual(before["metadata"]["topic"], after["metadata"]["topic"])

    def test_boundary_errors_are_visible(self):
        text = self.paths[0].read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "날짜 경계 오류"):
            parse_consultations(text, "sample", "date")
        with self.assertRaisesRegex(ValueError, "구분선 경계 오류"):
            parse_consultations(text.rstrip() + "\n=====\n", "sample", "rule")
        with self.assertRaises(ValueError):
            parse_consultations(text.replace("[상담ID] C-", "[상담ID] X-", 1), "sample")

    def test_raw_mode_has_no_claim_of_pseudonymization(self):
        raw = parse_consultations(self.paths[0].read_text(encoding="utf-8"), "sample")[0]
        self.assertFalse(raw["metadata"]["pseudonymized"])
        self.assertIn("member_id", raw["metadata"])
        self.assertNotIn("member_pseudo_id", raw["metadata"])
        self.assertEqual(validate_document(raw), [])

    def test_validation_detects_mutated_fields_and_privacy(self):
        for field, value in (("access_level", "public"), ("channel", "unknown"),
                             ("created_at", "2026-02-30"), ("member_pseudo_id", "M-1001")):
            doc = copy.deepcopy(self.documents[0])
            doc["metadata"][field] = value
            self.assertTrue(validate_document(doc), field)
        doc = copy.deepcopy(self.documents[0])
        doc["page_content"] += "\n고객: 전화 010 1234 5678"
        self.assertTrue(any("privacy" in e for e in validate_document(doc)))


if __name__ == "__main__":
    unittest.main()
