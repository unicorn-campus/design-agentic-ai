"""PyMuPDF 텍스트 계층을 Document로 변환하는 어댑터."""

from collections import Counter
from pathlib import Path
import re

from langchain_core.documents import Document
import pymupdf


def _lines(page):
    result = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                result.append((tuple(line["bbox"]), text))
    return result


def _margin(rectangle, height):
    # rectangle은 (x0, y0, x1, y1) 좌표임.
    # 줄의 아래쪽(y1)이 페이지 상단 5.5% 안이거나, 위쪽(y0)이 하단 5% 아래이면 여백으로 판별함.
    return rectangle[3] < height * 0.055 or rectangle[1] > height * 0.95


def _row_text(lines):
    rows = []
    for rectangle, text in sorted(lines, key=lambda item: (round(item[0][1], 1), item[0][0])):
        if rows and abs(rows[-1][0] - rectangle[1]) < 2:
            rows[-1][1].append((rectangle, text))
        else:
            rows.append([rectangle[1], [(rectangle, text)]])
    result = []
    for y, cells in rows:
        cells.sort(key=lambda item: item[0][0])
        text = cells[0][1]
        for previous, current in zip(cells, cells[1:]):
            text += (" | " if current[0][0] - previous[0][2] > 12 else " ") + current[1]
        result.append((y, text))
    return result


def _metadata(text, filename):
    effective = re.search(r"(?:effective_date\s*|시행일[: ]*)(\d{4})[-년 ]+(\d{1,2})[-월 ]+(\d{1,2})", text)
    version = re.search(r"(?:version\s*|버전[: ]*)(\d+(?:\.\d+)+)", text)
    created = re.search(r"(?:created_at|작성일)\s*[:：]?\s*(\d{4}-\d{2}-\d{2})", text)
    # source: 원본 파일 이름.
    # doc_type: 파일명 접두사(D1·D2)로 판별한 문서 종류.
    # effective_date: 본문에서 추출해 YYYY-MM-DD 형식으로 정리한 시행일.
    # version: 본문에서 추출한 문서 버전.
    # created_at: 본문에서 추출한 작성일.
    # supersedes: 이 문서가 대체하는 이전 문서 정보이며, 원문에 없으므로 비워 둠.
    # owner_dept: 문서 담당 부서이며, 원문에 없으므로 비워 둠.
    # access_level: 교육용 공개 등급 문구가 있으면 public으로 설정함.
    # synthetic: 본문에 "합성"이라는 표시가 있는지 나타냄.
    # metadata_origin: 메타데이터의 출처와 누락값 보완 방법을 기록함.
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


class PdfReader:
    def read(self, path: Path, *, remove_margins: bool = True) -> tuple[list[Document], dict]:
        # 호출자가 전달한 경로를 Path로 통일하고, 결과 문서와 처리 보고서를 준비함.
        path = Path(path)
        documents = []
        report = {
            "source": path.name, "pages": 0, "raw_chars": 0, "clean_chars": 0,
            "removed_lines": 0, "warnings": [], "tables": 0, "ruled_tables": 0,
            "removed_line_details": [],
        }
        with pymupdf.open(path) as pdf:
            # 처리 플로우.
            # [1] PDF 접근 가능 여부 확인
            #   ↓
            # [2] 페이지별 텍스트 줄과 좌표 사전 추출
            #   ↓
            # [3] 반복 머리말·꼬리말 수집
            #   ↓
            # [4] 공통 메타데이터 추출 및 누락 경고 기록
            #   ├─ [4-1] 모든 페이지 텍스트 결합
            #   ├─ [4-2] 파일명·본문에서 공통 메타데이터 추출
            #   └─ [4-3] PDF 생성일 보완 및 누락값 경고 기록
            #   ↓
            # [5] 각 페이지를 최종 Document로 변환
            #   ├─ [5-1] 여백·페이지 번호 줄 제거
            #   ├─ [5-2] 선이 있는 표를 Markdown 표로 변환
            #   ├─ [5-3] 일반 텍스트와 표를 본문으로 결합
            #   └─ [5-4] 페이지 메타데이터 보강 및 Document 생성
            #   ↓
            # [6] 전체 페이지 수를 처리 보고서에 기록

            # ===== [1] PDF 접근 가능 여부 확인 =====
            # 암호화된 PDF는 텍스트 계층에 안전하게 접근할 수 없으므로 즉시 중단함.
            if pdf.needs_pass:
                raise ValueError(f"암호화 PDF는 처리할 수 없음: {path.name}")

            # ===== [2] 페이지별 텍스트 줄과 좌표 사전 추출 =====
            # 모든 페이지의 텍스트 줄과 좌표를 먼저 추출하여 이후 처리에서 재사용함.
            page_lines = [_lines(page) for page in pdf]

            # ===== [3] 반복 머리말·꼬리말 수집 =====
            # 여러 페이지의 상·하단에 반복되는 줄을 찾아 머리말·꼬리말 제거 기준으로 사용함.
            repeated = Counter()
            for page, lines in zip(pdf, page_lines):
                # 각 줄의 (좌표, 텍스트) 중 상·하단 여백의 텍스트만 집합으로 추림.
                # 집합을 사용하므로 같은 페이지 안에서 같은 문구는 한 번만 셈.
                # 예: 여백의 "회사명", 본문의 "상품 안내"가 있으면 {"회사명"}만 세어 반복 여부를 확인함.
                # 예: 세 페이지에서 모두 "회사명"을 찾으면 repeated는 Counter({"회사명": 3})이 됨.
                repeated.update({text for rectangle, text in lines if _margin(rectangle, page.rect.height)})
                # 같은 동작을 여러 줄로 풀어 쓰면 다음과 같음.
                # margin_texts = set()
                # for rectangle, text in lines:
                #     if _margin(rectangle, page.rect.height):
                #         margin_texts.add(text)
                # repeated.update(margin_texts)

            # ===== [4] 공통 메타데이터 추출 및 누락 경고 기록 =====
            # ----- [4-1] 모든 페이지 텍스트 결합 -----
            # 문서 전체 텍스트에서 공통 메타데이터를 추출하고, 없으면 PDF 생성일을 보조값으로 사용함.
            # 예: "첫 번째 줄", "두 번째 줄", "세 번째 줄"은 줄바꿈으로 이어 하나의 문자열이 됨.
            # 결과: "첫 번째 줄\n두 번째 줄\n세 번째 줄"
            full_text = "\n".join(text for lines in page_lines for _, text in lines)

            # ----- [4-2] 파일명·본문에서 공통 메타데이터 추출 -----
            common = _metadata(full_text, path.name)

            # ----- [4-3] PDF 생성일 보완 및 누락값 경고 기록 -----
            creation = re.match(r"D:(\d{4})(\d{2})(\d{2})", pdf.metadata.get("creationDate", ""))
            if common["created_at"] is None and creation:
                common["created_at"] = "-".join(creation.groups())
                common["created_at_origin"] = "pdf_creationDate (file creation, not business publication)"
            missing = [key for key, value in common.items() if value is None]
            if missing:
                report["warnings"].append("Missing source metadata (configure explicitly): " + ", ".join(missing))

            # ===== [5] 각 페이지를 최종 Document로 변환 =====
            in_contents = False

            # zip은 PDF 페이지와 각 페이지에서 추출한 줄 목록을 한 쌍으로 묶음.
            # enumerate(start=1)는 이 쌍에 1부터 시작하는 페이지 번호를 붙임.
            # (page, lines)는 zip이 만든 내부 쌍을 페이지 객체와 줄 목록으로 나누어 받음.
            # 예: 첫 반복에서는 page_number=1, page=첫 페이지, lines=첫 페이지의 줄 목록이 됨.
            for page_number, (page, lines) in enumerate(zip(pdf, page_lines), start=1):
                # ----- [5-1] 페이지별 본문 정제(페이지 번호, 반복 텍스트 제거) -----
                report["raw_chars"] += len(page.get_text())
                kept = []

                # 페이지 번호 또는 반복 머리말·꼬리말을 제거하고, 나머지 줄을 보존함.
                for rectangle, text in lines:
                    # 숫자만 있거나 하이픈으로 감싼 숫자 줄을 페이지 번호 후보로 판별함.
                    # 예: "12", "- 12 -"는 True이고, "제12조"는 False임.
                    numbered = bool(re.fullmatch(r"(?:-\s*)?\d+(?:\s*-)?", text))

                    # remove_margins: 호출자가 여백 줄 제거를 허용했는지 확인함.
                    # _margin(...): 현재 줄이 페이지의 상단 또는 하단 여백에 있는지 확인함.
                    # numbered 또는 repeated[text] >= 2: 페이지 번호이거나 여러 페이지에 반복된 문구인지 확인함.
                    # 세 조건이 모두 맞을 때만 현재 줄을 제거함.
                    if remove_margins and _margin(rectangle, page.rect.height) and (numbered or repeated[text] >= 2):
                        report["removed_lines"] += 1
                        report["removed_line_details"].append({"page": page_number, "text": text})
                    else:
                        kept.append((rectangle, text))

                # ----- [5-2] 표를 마크다운 텍스트로 변환 -----
                # 표의 세로 위치와 변환된 Markdown 표를 저장해 본문에 원래 위치대로 합치는 목록임.
                replacements = []

                try:
                    tables = page.find_tables().tables
                except Exception as error:
                    tables = []
                    report["warnings"].append(f"Page {page_number}: table detection failed ({type(error).__name__}); text retained")

                for table in tables:
                    # 표를 행별 셀 목록으로 추출함.
                    # 예: [["상품명", "연회비"], ["카드 A", "10,000원"]]처럼 각 내부 목록이 한 행이 됨.
                    matrix = table.extract()
                    if not matrix or len(matrix[0]) < 2:
                        continue

                    # table.bbox는 감지한 표 영역의 경계 좌표(x0, y0, x1, y1)임.
                    # 예: table.bbox가 (50.0, 100.0, 550.0, 300.0)이면 rectangle은 같은 좌표의 Rect 객체가 됨.
                    rectangle = pymupdf.Rect(table.bbox)

                    # 표 영역 안에 완전히 들어온 원문 줄을 모아 표 변환 결과를 검증하는 데 사용함.
                    contained = [(box, text) for box, text in kept if rectangle.contains(pymupdf.Rect(box).tl) and rectangle.contains(pymupdf.Rect(box).br)]
                    # 같은 동작을 여러 줄로 풀어 쓰면 다음과 같음.
                    # contained = []
                    # for box, text in kept:
                    #     text_rectangle = pymupdf.Rect(box)
                    #     텍스트 줄의 왼쪽 위(tl)와 오른쪽 아래(br)가 모두 표 영역 안에 있는지 확인함.
                    #     if rectangle.contains(text_rectangle.tl) and rectangle.contains(text_rectangle.br):
                    #         contained.append((box, text))


                    # 표 영역 원문의 공백을 제외한 글자별 개수를 세어 표 변환 결과와 비교하는 데 사용함.
                    source_chars = Counter(re.sub(r"\s", "", "".join(text for _, text in contained)))
                    # 같은 동작을 여러 줄로 풀어 쓰면 다음과 같음.
                    # source_text = ""
                    # for _, text in contained:
                    #     source_text += text
                    # re.sub(패턴, 바꿀 문자열, 대상 문자열)은 패턴에 맞는 부분을 바꿔 줌.
                    # r은 역슬래시를 그대로 해석하는 원시 문자열 표기이고, \s는 공백·탭·줄바꿈을 뜻함.
                    # text_without_spaces = re.sub(r"\s", "", source_text)
                    # 예: text_without_spaces가 "AAB"이면 source_chars는 Counter({"A": 2, "B": 1})이 됨.
                    # source_chars = Counter(text_without_spaces)

                    # 추출된 표 셀의 공백을 제외한 글자별 개수를 세어 원문 글자 수와 비교하는 데 사용함.
                    table_chars = Counter(re.sub(r"\s", "", "".join(str(cell or "") for row in matrix for cell in row)))

                    if source_chars != table_chars:
                        report["warnings"].append(f"Page {page_number}: detected table retained as positioned text (glyph mismatch)")
                        continue

                    markdown = []
                    for row_number, row in enumerate(matrix):
                        markdown.append("| " + " | ".join(str(cell or "").replace("\n", " ").replace("|", "\\|") for cell in row) + " |")
                        if row_number == 0:
                            markdown.append("| " + " | ".join("---" for _ in row) + " |")

                    # Markdown 표로 바꾼 원문 줄을 kept에서 제거해 같은 내용이 중복 출력되지 않게 함.
                    kept = [item for item in kept if item not in contained]

                    # 표의 시작 세로 좌표(y0)와 완성된 Markdown 표를 한 쌍으로 저장함.
                    replacements.append((rectangle.y0, "\n".join(markdown)))
                    
                    report["tables"] += 1

                    # 선이 있는 표로 감지되어 검증 후 Markdown으로 변환한 표의 수를 집계함.
                    report["ruled_tables"] += 1

                # ----- [5-3] 텍스트+표 구성 -----
                # 남은 텍스트를 좌표 순서대로 한 줄씩 조합함.
                rows = _row_text(kept)

                # 일반 텍스트 행과 변환된 표를 원래 세로 순서대로 합쳐 페이지의 최종 본문을 만듦.
                # sorted는 여러 항목을 정렬한 새 목록을 반환하고, key는 정렬 기준을 정함.
                # lambda item: item[0]은 (세로 좌표, 텍스트)에서 첫 값인 세로 좌표를 기준으로 선택함.
                # 예: [(300, "본문"), (100, "표")]는 세로 좌표가 작은 표가 먼저 오도록 정렬됨.
                content = "\n".join(text for _, text in sorted(rows + replacements, key=lambda item: item[0]))
                # 같은 동작을 여러 줄로 풀어 쓰면 다음과 같음.
                # ordered_items = sorted(rows + replacements, key=lambda item: item[0])
                # content_lines = []
                # for _, text in ordered_items:
                #     content_lines.append(text)
                # content = "\n".join(content_lines)
                if not content.strip():
                    report["warnings"].append(f"Page {page_number}: no text layer; OCR is not enabled")

                # ----- [5-4] 페이지 메타데이터 보강 및 Document 생성 -----
                # 페이지별 메타데이터를 보강한 LangChain Document를 결과에 추가함.
                metadata = dict(common, page=page_number)
                # common의 모든 항목을 새 딕셔너리에 복사하고, 현재 페이지 번호를 page에 추가함.
                # common 자체는 바꾸지 않으므로 다음 페이지에서도 공통 메타데이터를 그대로 재사용할 수 있음.
                # 같은 동작을 여러 줄로 풀어 쓰면 다음과 같음.
                # metadata = dict(common)
                # metadata["page"] = page_number

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
                metadata["table_count"] = len(replacements)
                documents.append(Document(page_content=content, metadata=metadata))
                report["clean_chars"] += len(content)

            # ===== [6] 전체 처리 보고서 마무리 =====
            # 파일 전체의 최종 페이지 수를 보고서에 기록함.
            report["pages"] = len(pdf)
        return documents, report


def extract_pdf(path: Path, remove_margins: bool = True):
    return PdfReader().read(path, remove_margins=remove_margins)
