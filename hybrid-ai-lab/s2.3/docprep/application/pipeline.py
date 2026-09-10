"""파일 선택 → 추출 → 정제 → 검증 → 저장을 조립함."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

from docprep.application.ports import DocumentStore, PdfReader
from docprep.domain.consultations import parse_consultations
from docprep.domain.validation import validate_document


PDF_NAMES = {"D1_개인회원표준약관_합성.pdf", "D2_카드혜택안내_합성.pdf"}
TXT_NAME = re.compile(r"D3_S0[1-6]_[^/\\]+_상담이력_합성\.txt$")


@dataclass(frozen=True)
class Options:
    input: Path
    output: Path
    split_by: str = "header"
    pseudonymize: bool = False
    remove_margins: bool = True
    report: bool = False
    validate: bool = False
    segment: int | None = None


def select_sources(location: Path, segment: int | None = None) -> list[Path]:
    if not location.exists():
        raise ValueError(f"입력 경로가 없음: {location}")
    candidates = [location] if location.is_file() else list(location.iterdir())
    sources = []
    for path in sorted(candidates):
        if path.is_symlink() or not path.is_file() or "_instructor" in path.parts:
            continue
        if path.name in PDF_NAMES:
            sources.append(path)
        elif TXT_NAME.fullmatch(path.name) and (segment is None or path.name.startswith(f"D3_S{segment:02d}_")):
            sources.append(path)
    if not sources:
        raise ValueError("입력에 허용된 D1·D2 PDF 또는 D3_S01~S06 상담 TXT가 없음")
    return sources


def check_documents(documents: list[dict], schema: dict) -> dict:
    errors = []
    record_ids = set()
    for index, doc in enumerate(documents):
        issues = validate_document(doc, schema.get("enums"))
        meta = doc.get("metadata", {})
        if not isinstance(meta, dict):
            errors.append({"index": index, "errors": issues})
            continue
        if "allowed_keys" in schema:
            for key in set(meta) - set(schema["allowed_keys"]):
                issues.append(f"정의되지 않은 메타데이터 키: {key}")
        for key in schema.get("required", []):
            if key not in meta or meta[key] is None or meta[key] == "":
                issues.append(f"필수 메타데이터 누락: {key}")
        for key, allowed in schema.get("enums", {}).items():
            if key in meta and meta[key] not in allowed:
                issues.append(f"허용 목록에 없는 값: {key}")
        record_id = meta.get("record_id")
        if record_id:
            if record_id in record_ids:
                issues.append("상담 ID 중복")
            record_ids.add(record_id)
        if issues:
            errors.append({"index": index, "source": meta.get("source"),
                           "record_id": record_id, "page": meta.get("page"),
                           "errors": sorted(set(issues))})
    return {"checked": len(documents), "invalid": len(errors), "errors": errors}


class Pipeline:
    def __init__(self, reader: PdfReader, store: DocumentStore):
        self.reader, self.store = reader, store

    def run(self, options: Options, profiles: dict, schema: dict) -> dict:
        sources = select_sources(options.input, options.segment)
        output = options.output.resolve()
        input_dir = options.input.resolve() if options.input.is_dir() else options.input.resolve().parent
        if output == input_dir or output.is_relative_to(input_dir):
            raise ValueError("원문 폴더 안에는 결과를 저장할 수 없음. 별도 --out 경로를 사용하세요")
        documents, reports, fingerprints = [], [], {}
        for path in sources:
            fingerprints[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            if path.suffix.lower() == ".pdf":
                parsed, report = self.reader(path, remove_margins=options.remove_margins)
            else:
                text = self.store.read_text(path)
                parsed = parse_consultations(text, path.name, options.split_by, options.pseudonymize)
                expected = len(re.findall(r"^\[상담ID\]", text, flags=re.M))
                if options.split_by == "header" and len(parsed) != expected:
                    raise ValueError(f"상담 분리 건수 불일치: {path.name}")
                report = {"source": path.name, "pages": 0, "records": len(parsed),
                          "expected_records": expected, "raw_chars": len(text),
                          "clean_chars": sum(len(d["page_content"]) for d in parsed),
                          "removed_lines": sum(1 for line in text.splitlines() if line and
                                               not line.startswith(("고객:", "상담사:"))),
                          "min_chars": min(len(d["page_content"]) for d in parsed),
                          "max_chars": max(len(d["page_content"]) for d in parsed),
                          "warnings": [] if options.pseudonymize else ["가명화 미실행: 색인 전 정제 필요"]}
            profile = profiles.get(path.name, {})
            forbidden = {"source", "page", "record_id", "member_id", "member_pseudo_id", "pseudonymized"}
            if forbidden.intersection(profile):
                raise ValueError("메타데이터 프로필에서 출처·식별·처리 상태를 덮어쓸 수 없음")
            for doc in parsed:
                doc["metadata"].update(profile)
            # 추출기의 미기재 경고는 프로필 적용 후 미해결 필수 항목으로 갱신함.
            report["warnings"] = [w for w in report.get("warnings", [])
                                  if not str(w).startswith("Missing source metadata")]
            missing = sorted({key for doc in parsed for key in schema.get("required", [])
                              if doc["metadata"].get(key) in (None, "")})
            if missing:
                report["warnings"].append("설정 필요 메타데이터: " + ", ".join(missing))
            documents.extend(parsed)
            reports.append(report)
        validation = check_documents(documents, schema) if options.validate else None
        manifest = {"format_version": 1, "inputs_sha256": fingerprints,
                    "document_count": len(documents), "split_by": options.split_by,
                    "pseudonymized": options.pseudonymize, "remove_margins": options.remove_margins}
        self.store.save(output, documents, reports, validation, options.report, manifest)
        return {"sources": len(sources), "documents": len(documents),
                "consultations": sum(d["metadata"].get("doc_type") == "consult_log" for d in documents),
                "output": str(output), "validation": validation,
                "warnings": [w for r in reports for w in r.get("warnings", [])]}

    def validate_saved(self, location: Path, schema: dict) -> dict:
        if location.is_file():
            paths = [location]
        else:
            # 합본은 열람·청킹용이며, 메타데이터가 있는 페이지·상담 파일을 검사함.
            paths = sorted([*location.glob("pages/*.md"), *location.glob("records/*.md")])
        if not paths:
            raise ValueError("검사 대상 Markdown이 없음: --in에 정제 결과 폴더 또는 파일 지정")
        documents, malformed = [], []
        for path in paths:
            try:
                documents.append(self.store.load_markdown(path))
            except ValueError as exc:
                malformed.append({"file": path.name, "errors": [str(exc)]})
        result = check_documents(documents, schema)
        result["checked"] += len(malformed)
        result["invalid"] += len(malformed)
        result["errors"].extend(malformed)
        return result
