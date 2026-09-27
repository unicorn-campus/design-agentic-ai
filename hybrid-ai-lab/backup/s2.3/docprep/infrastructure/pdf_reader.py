"""PDF text-layer adapter. No OCR, source mutation, or inferred business metadata."""
from collections import Counter
from pathlib import Path
import re

import pymupdf


def _lines(page):
    result = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                result.append((tuple(line["bbox"]), text))
    return result


def _margin(rect, height):
    return rect[3] < height * .055 or rect[1] > height * .95


def _row_text(lines):
    """Keep horizontal cell relationships in borderless source tables."""
    rows = []
    for rect, text in sorted(lines, key=lambda item: (round(item[0][1], 1), item[0][0])):
        if rows and abs(rows[-1][0] - rect[1]) < 2:
            rows[-1][1].append((rect, text))
        else:
            rows.append([rect[1], [(rect, text)]])
    result = []
    for y, cells in rows:
        cells.sort(key=lambda item: item[0][0])
        text = cells[0][1]
        for previous, current in zip(cells, cells[1:]):
            gap = current[0][0] - previous[0][2]
            text += (" | " if gap > 12 else " ") + current[1]
        result.append((y, text))
    return result


def _metadata(text, filename):
    effective = re.search(r"(?:effective_date\s*|시행일[: ]*)(\d{4})[-년 ]+(\d{1,2})[-월 ]+(\d{1,2})", text)
    version = re.search(r"(?:version\s*|버전[: ]*)(\d+(?:\.\d+)+)", text)
    created = re.search(r"(?:created_at|작성일)\s*[:：]?\s*(\d{4}-\d{2}-\d{2})", text)
    return {
        "source": filename,
        "doc_type": "regulation" if filename.startswith("D1") else "benefit_guide" if filename.startswith("D2") else "pdf",
        "effective_date": "-".join((effective[1], effective[2].zfill(2), effective[3].zfill(2))) if effective else None,
        "version": version[1] if version else None,
        "created_at": created[1] if created else None,
        "supersedes": None,
        "owner_dept": None,
        "access_level": "public" if "공개 등급: 교육용 공개" in text else None,
        "synthetic": "합성" in text,
        "metadata_origin": "source_text; missing values require instructor configuration",
    }


def extract_pdf(path: Path, remove_margins: bool = True) -> tuple[list[dict], dict]:
    """Return one document per physical page and a reproducible extraction report.

    Repetition removal is limited to the top 5.5% / bottom 5% of each page.
    Body disclaimers, article numbers, footnotes and contents pages stay intact.
    Detected ruled tables become Markdown; borderless cells retain row separators.
    """
    path = Path(path)
    documents = []
    report = {"source": path.name, "pages": 0, "raw_chars": 0, "clean_chars": 0,
              "removed_lines": 0, "warnings": [], "tables": 0, "ruled_tables": 0, "borderless_table_headers": 0,
              "removed_line_details": []}
    with pymupdf.open(path) as pdf:
        if pdf.needs_pass:
            raise ValueError(f"Encrypted PDF requires decryption before extraction: {path.name}")
        page_lines = [_lines(page) for page in pdf]
        repeated = Counter()
        for page, lines in zip(pdf, page_lines):
            repeated.update({text for rect, text in lines if _margin(rect, page.rect.height)})
        full_text = "\n".join(text for lines in page_lines for _, text in lines)
        common = _metadata(full_text, path.name)
        creation = re.match(r"D:(\d{4})(\d{2})(\d{2})", pdf.metadata.get("creationDate", ""))
        if common["created_at"] is None and creation:
            common["created_at"] = "-".join(creation.groups())
            common["created_at_origin"] = "pdf_creationDate (file creation, not business publication)"
        missing = [key for key, value in common.items() if value is None]
        if missing:
            report["warnings"].append("Missing source metadata (configure explicitly): " + ", ".join(missing))
        in_contents = False
        for index, (page, lines) in enumerate(zip(pdf, page_lines), 1):
            report["raw_chars"] += len(page.get_text())
            kept = []
            for rect, text in lines:
                numbered = bool(re.fullmatch(r"(?:-\s*)?\d+(?:\s*-)?", text))
                if remove_margins and _margin(rect, page.rect.height) and (numbered or repeated[text] >= 2):
                    report["removed_lines"] += 1
                    report["removed_line_details"].append({"page": index, "text": text})
                else:
                    kept.append((rect, text))
            replacements = []
            try:
                tables = page.find_tables().tables
            except Exception as exc:
                tables = []
                report["warnings"].append(f"Page {index}: table detection failed ({type(exc).__name__}); text retained")
            for table in tables:
                matrix = table.extract()
                if not matrix or len(matrix[0]) < 2:
                    continue
                # A table must account for every source glyph before replacing its area.
                rect = pymupdf.Rect(table.bbox)
                contained = [(box, text) for box, text in kept if rect.contains(pymupdf.Rect(box).tl)
                             and rect.contains(pymupdf.Rect(box).br)]
                source_chars = Counter(re.sub(r"\s", "", "".join(text for _, text in contained)))
                table_chars = Counter(re.sub(r"\s", "", "".join(str(cell or "") for row in matrix for cell in row)))
                if source_chars != table_chars:
                    report["warnings"].append(f"Page {index}: detected table retained as positioned text (glyph mismatch)")
                    continue
                md = []
                for row_no, row in enumerate(matrix):
                    md.append("| " + " | ".join(str(cell or "").replace("\n", " ").replace("|", "\\|") for cell in row) + " |")
                    if row_no == 0:
                        md.append("| " + " | ".join("---" for _ in row) + " |")
                kept = [item for item in kept if item not in contained]
                replacements.append((rect.y0, "\n".join(md)))
                report["tables"] += 1
                report["ruled_tables"] += 1
            rows = _row_text(kept)
            borderless = sum(" | " in text and ("총연회비" in text or "합성 조건" in text or "가상 카드명" in text)
                             for _, text in rows)
            report["borderless_table_headers"] += borderless
            report["tables"] += borderless
            content = "\n".join(text for _, text in sorted(rows + replacements, key=lambda item: item[0]))
            if not content.strip():
                report["warnings"].append(f"Page {index}: no text layer; OCR is not enabled")
            metadata = dict(common, page=index)
            if common["doc_type"] == "regulation":
                if "차례" in content:
                    in_contents = True
                elif in_contents and re.search(r"[①②③]|\(1\)|1\.", content):
                    in_contents = False
                metadata["section_kind"] = "contents" if in_contents else "body"
            product_ids = sorted(set(re.findall(r"D2-C\d{3}", content)))
            if len(product_ids) == 1:
                metadata["product_id"] = product_ids[0]
            elif product_ids:
                metadata["product_ids"] = product_ids
            metadata["table_count"] = len(replacements) + borderless
            documents.append({"page_content": content, "metadata": metadata})
            report["clean_chars"] += len(content)
        report["pages"] = len(pdf)
    return documents, report
