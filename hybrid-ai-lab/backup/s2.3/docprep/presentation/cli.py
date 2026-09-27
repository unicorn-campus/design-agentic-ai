"""명령 입력을 처리 옵션으로 변환하는 얇은 경계."""
import argparse
import json
from pathlib import Path
import sys

from docprep.application.pipeline import Options, Pipeline
from docprep.infrastructure.file_store import FileStore
from docprep.infrastructure.pdf_reader import extract_pdf

BASE = Path(__file__).resolve().parents[2]


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("설정 JSON은 객체 형태여야 함")
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="S2.3 PDF·상담 TXT 추출/정제·메타데이터 검사")
    parser.add_argument("--in", dest="input", type=Path, help="원문 폴더/파일; 기본값은 w2-4 옆 docs")
    parser.add_argument("--out", dest="output", type=Path, default=BASE / "data/parsed")
    parser.add_argument("--split-by", choices=["header", "rule", "date"], default="header")
    parser.add_argument("--pseudonymize", action="store_true", help="상담 PII 제거·ID 가명화·나이 모호화")
    parser.add_argument("--keep-margins", action="store_true", help="PDF 머리말·꼬리말을 제거하지 않고 비교")
    parser.add_argument("--report", action="store_true", help="문서별 추출·정제 보고서 저장")
    parser.add_argument("--validate", action="store_true", help="추출 결과의 메타데이터·정제 결과 검사")
    parser.add_argument("--validate-only", action="store_true", help="저장된 Markdown만 검사; 재추출/덮어쓰기 없음")
    parser.add_argument("--segment", type=int, choices=range(1, 7), help="PDF 2개와 선택 세그먼트 상담 파일만 처리")
    parser.add_argument("--metadata", type=Path, default=BASE / "config/document_profiles.json")
    parser.add_argument("--schema", type=Path, default=BASE / "config/metadata_schema.json")
    args = parser.parse_args(argv)
    try:
        pipeline = Pipeline(extract_pdf, FileStore())
        schema = read_object(args.schema)
        if args.validate_only:
            result = pipeline.validate_saved(args.input or args.output, schema)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2 if result["invalid"] else 0
        options = Options(input=args.input or BASE.parent / "docs", output=args.output,
                          split_by=args.split_by, pseudonymize=args.pseudonymize,
                          remove_margins=not args.keep_margins, report=args.report,
                          validate=args.validate, segment=args.segment)
        result = pipeline.run(options, read_object(args.metadata), schema)
        print(f"입력 {result['sources']}파일 → {result['documents']}개 문서(상담 {result['consultations']}건)")
        print(f"저장: {result['output']}")
        if result["warnings"]:
            print(f"확인 사항 {len(result['warnings'])}건: --report의 report.json 확인")
        validation = result["validation"]
        if validation:
            print(f"검사 {validation['checked']}건 / 오류 {validation['invalid']}건")
            return 2 if validation["invalid"] else 0
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"처리 중단: {exc}", file=sys.stderr)
        return 1
