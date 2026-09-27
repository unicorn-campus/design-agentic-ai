"""UTF-8 텍스트, YAML 머리말, JSONL 및 CSV 저장 어댑터."""
from pathlib import Path
import csv
import io
import json
import os
import re
import tempfile

import yaml


def markdown(doc: dict) -> str:
    return "---\n" + yaml.safe_dump(doc["metadata"], allow_unicode=True, sort_keys=False) + "---\n\n" + doc["page_content"] + "\n"


def safe_name(value: str) -> str:
    if not value or not re.fullmatch(r"[\w가-힣.\-]+", value) or value in {".", ".."}:
        raise ValueError("결과 파일명으로 사용할 수 없는 식별자")
    return value


class FileStore:
    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8-sig")

    def load_markdown(self, path: Path) -> dict:
        text = self.read_text(path)
        match = re.match(r"\A---\r?\n(.*?)\r?\n---\s*\r?\n(.*)\Z", text, re.S)
        if not match:
            raise ValueError("파일 맨 위 YAML 머리말(---)이 없거나 닫히지 않음")
        try:
            meta = yaml.safe_load(match[1])
        except yaml.YAMLError:
            raise ValueError("YAML 머리말 문법 오류") from None
        if not isinstance(meta, dict):
            raise ValueError("YAML 머리말은 키: 값 구조여야 함")
        # 따옴표 없이 편집한 ISO 날짜도 같은 문자열 계약으로 처리함.
        for key, value in meta.items():
            if hasattr(value, "isoformat"):
                meta[key] = value.isoformat()
        return {"page_content": match[2].strip(), "metadata": meta}

    def save(self, output: Path, documents: list[dict], reports: list[dict],
             validation: dict | None, write_report: bool, manifest: dict) -> None:
        output.mkdir(parents=True, exist_ok=True)
        contents, grouped = {}, {}
        for doc in documents:
            meta = doc["metadata"]
            if meta["doc_type"] == "consult_log":
                relative = f"records/{safe_name(meta['record_id'])}.md"
            else:
                stem = safe_name(Path(meta["source"]).stem)
                relative = f"pages/{stem}_p{meta['page']:04d}.md"
                grouped.setdefault(stem, []).append(doc)
            if relative in contents:
                raise ValueError("중복 출처/상담 ID로 결과 파일이 충돌함")
            contents[relative] = markdown(doc)
        for stem, pages in grouped.items():
            # 다음 주 조항 청킹용 합본. 페이지별 정확한 메타데이터는 JSONL/개별 MD를 사용함.
            contents[f"{stem}.md"] = "\n\n".join(
                f"<!-- source: {d['metadata']['source']} | page: {d['metadata']['page']} -->\n{d['page_content']}"
                for d in pages)
        contents["documents.jsonl"] = "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in documents)
        if write_report:
            columns = ["source", "pages", "records", "expected_records", "raw_chars", "clean_chars",
                       "removed_lines", "min_chars", "max_chars", "tables", "warnings"]
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for report in reports:
                row = dict(report)
                row["warnings"] = " | ".join(str(w) for w in row.get("warnings", []))
                writer.writerow(row)
            contents["report.csv"] = "\ufeff" + buffer.getvalue()
            contents["report.json"] = json.dumps(reports, ensure_ascii=False, indent=2)
        if validation is not None:
            contents["validation.json"] = json.dumps(validation, ensure_ascii=False, indent=2)
        old_files = []
        prior = output / "manifest.json"
        if prior.exists():
            old_files = json.loads(prior.read_text(encoding="utf-8")).get("generated_files", [])
        manifest["generated_files"] = sorted(contents)
        contents["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2)
        # 저장 전 모든 경로를 확인하고 원문 및 외부 경로 덮어쓰기를 차단함.
        for relative in [*contents, *old_files]:
            target = output / relative
            if not target.resolve().is_relative_to(output.resolve()) or target.is_symlink():
                raise ValueError("결과 목록에 허용 범위 밖의 경로가 있어 저장 중단")
        for relative, text in contents.items():
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp = tempfile.mkstemp(prefix=".docprep-", dir=target.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(text)
                os.replace(temp, target)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
        # 이전 실행이 생성한 파일만 정리하고 별도 작성 자료는 보존함.
        for relative in set(old_files) - set(contents):
            target = output / relative
            if target.is_file():
                target.unlink()
