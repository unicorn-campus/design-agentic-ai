"""실제 상담 입력과 가짜 PDF 어댑터를 조립하는 파일 기반 통합 검사."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from docprep.application.pipeline import Options, Pipeline, select_sources
from docprep.infrastructure.file_store import FileStore, markdown

BASE = Path(__file__).resolve().parents[1]
DOCS = BASE.parent / "docs"
SCHEMA = json.loads((BASE / "config/metadata_schema.json").read_text(encoding="utf-8"))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / "docs"
        self.input.mkdir()
        self.output = self.root / "parsed"
        self.source = next(DOCS.glob("D3_S01_*.txt"))
        (self.input / self.source.name).write_bytes(self.source.read_bytes())
        self.calls = []
        self.store = FileStore()
        self.pipeline = Pipeline(self.fake_pdf, self.store)

    def fake_pdf(self, path, *, remove_margins):
        self.calls.append((path.name, remove_margins))
        document = {"page_content": "제1조 적용 범위\n합성 규정 내용", "metadata": {
            "source": path.name, "doc_type": "regulation", "created_at": "2027-01-15",
            "version": "v1", "effective_date": "2027-01-15", "supersedes": "",
            "owner_dept": "product_planning", "access_level": "public", "page": 1}}
        return [document], {"source": path.name, "pages": 1, "records": 0, "warnings": []}

    def run_pipeline(self, **kwargs):
        values = {"input": self.input, "output": self.output, "pseudonymize": True,
                  "validate": True, "report": True}
        values.update(kwargs)
        return self.pipeline.run(Options(**values), {}, SCHEMA)

    def test_allowlist_excludes_instructor_and_other_files(self):
        (self.input / "README.md").write_text("설명", encoding="utf-8")
        private = self.input / "_instructor"
        private.mkdir()
        (private / self.source.name).write_bytes(self.source.read_bytes())
        pdf = self.input / "D1_개인회원표준약관_합성.pdf"
        pdf.write_bytes(b"fake-pdf")
        self.assertEqual(len(select_sources(self.input)), 2)
        with self.assertRaises(ValueError):
            select_sources(private)
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.input.rglob("*") if p.is_file()}
        result = self.run_pipeline(remove_margins=False)
        self.assertEqual(result["documents"], 9)
        self.assertEqual(result["validation"]["invalid"], 0)
        self.assertEqual(self.calls, [(pdf.name, False)])
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["inputs_sha256"]), {self.source.name, pdf.name})

    def test_metadata_override_persists_and_invalid_override_is_reported(self):
        options = Options(self.input, self.output, pseudonymize=True, validate=True)
        result = self.pipeline.run(options, {self.source.name: {"version": "v3"}}, SCHEMA)
        self.assertEqual(result["validation"]["invalid"], 0)
        record = next((self.output / "records").glob("*.md"))
        self.assertEqual(self.store.load_markdown(record)["metadata"]["version"], "v3")
        result = self.pipeline.run(options, {self.source.name: {"access_level": "unknown"}}, SCHEMA)
        self.assertEqual(result["validation"]["invalid"], 8)
        with self.assertRaises(ValueError):
            self.pipeline.run(options, {self.source.name: {"member_pseudo_id": "forged"}}, SCHEMA)

    def test_validate_saved_uses_learner_edits_instead_of_jsonl(self):
        self.run_pipeline()
        paths = sorted((self.output / "records").glob("*.md"))
        first = self.store.load_markdown(paths[0])
        first["metadata"]["acess_level"] = first["metadata"].pop("access_level")
        paths[0].write_text(markdown(first), encoding="utf-8")
        second = self.store.load_markdown(paths[1])
        second["metadata"]["owner_dept"] = "invalid_dept"
        second["page_content"] += "\n고객: 전화 010-1234-5678로 부탁합니다."
        paths[1].write_text(markdown(second), encoding="utf-8")
        result = self.pipeline.validate_saved(self.output, SCHEMA)
        self.assertEqual(result["checked"], 8)
        self.assertEqual(result["invalid"], 2)
        self.assertTrue(any("privacy" in issue for item in result["errors"] for issue in item["errors"]))
        self.assertEqual(self.pipeline.validate_saved(paths[0], SCHEMA)["invalid"], 1)

    def test_rerun_removes_stale_generated_files_but_preserves_extra_work(self):
        self.run_pipeline()
        extra = self.output / "records" / "우리조_메모.md"
        extra.write_text("교육생 별도 기록", encoding="utf-8")
        self.assertTrue((self.output / "report.csv").exists())
        self.run_pipeline(report=False, validate=False)
        self.assertFalse((self.output / "report.csv").exists())
        self.assertFalse((self.output / "validation.json").exists())
        self.assertEqual(extra.read_text(encoding="utf-8"), "교육생 별도 기록")
        self.assertEqual(len(list((self.output / "records").glob("C-*.md"))), 8)

    def test_invalid_boundary_and_output_inside_input_are_rejected(self):
        with self.assertRaises(ValueError):
            self.run_pipeline(split_by="unknown")
        with self.assertRaises(ValueError):
            self.run_pipeline(split_by="date")
        with self.assertRaises(ValueError):
            self.run_pipeline(output=self.input / "parsed")
        with self.assertRaises(ValueError):
            self.run_pipeline(output=self.input)
        self.assertFalse(self.output.exists())

    def test_malformed_frontmatter_is_counted_without_crash(self):
        self.run_pipeline()
        record = next((self.output / "records").glob("*.md"))
        record.write_text("---\naccess_level: [\n---\n본문", encoding="utf-8")
        result = self.pipeline.validate_saved(self.output, SCHEMA)
        self.assertEqual(result["checked"], 8)
        self.assertEqual(result["invalid"], 1)


if __name__ == "__main__":
    unittest.main()
