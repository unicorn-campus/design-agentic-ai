"""PyMuPDF 텍스트 계층을 Document로 변환하는 어댑터."""

from collections import Counter
from pathlib import Path
import re

from langchain_core.documents import Document
import pymupdf


def _lines(page):
    """PDF 한 페이지의 글자를 위치와 함께 읽어 ``(bbox, text)`` 목록으로 반환함.

    첨부 예시에는 제목, 두 문단, 표가 다음과 같이 들어 있음::

        제5조(통지 방법)
        ① 카드사는 앱 알림, 문자, 전자우편 또는 우편 중 회원이 선택한 수단으로 중요한 내용을 알립니다.
        ② 연락처가 바뀐 회원은 지체 없이 정보를 수정합니다. ...

        통지 종류       기본 수단    보조 수단    확인 기록
        약관 변경       앱 알림      전자우편     발송일·열람일
        이상거래 정지   문자         앱 알림      발송일·정지 사유
        연회비 반환 지연 전자우편    문자         예정일·지연 사유

    각 코드 줄은 이 페이지를 다음 순서로 처리함.

    1. ``result = []``
       제목·본문·표에서 읽은 줄을 담을 빈 목록을 준비함.

    2. ``for block in page.get_text("dict")["blocks"]``
       페이지를 사전으로 바꾼 뒤 제목, 본문, 표의 글자가 들어 있는 블록을 하나씩 꺼냄.
       예를 들어 제목 블록, ① 문단 블록, 표 셀 블록 등이 차례로 처리 대상이 됨.
       제목 ``제5조(통지 방법)``이 들어 있는 block의 간단한 예시는 다음과 같음::

           block = {
               "type": 0,
               "bbox": (28, 15, 230, 48),
               "lines": [
                   {
                       "bbox": (28, 15, 230, 48),
                       "spans": [
                           {"text": "제5조"},
                           {"text": "(통지 방법)"},
                       ],
                   }
               ],
           }

       ``type: 0``은 글자 블록이라는 뜻이고, ``bbox``는 블록 전체의 위치임.
       ``lines``에는 이 블록의 글자 줄들이 들어 있으며, 3번 반복문이 이 목록을 하나씩 꺼냄.

    3. ``for line in block.get("lines", [])``
       현재 블록 안에서 글자 줄을 하나씩 꺼냄.
       이미지 블록처럼 ``lines``가 없으면 빈 목록을 사용하므로 반복하지 않고 건너뜀.

    4. ``text = "".join(span["text"] for span in line["spans"]).strip()``
       글꼴이나 서식 때문에 여러 span으로 나뉜 글자 조각을 한 줄로 이어 붙임.
       예를 들어 ``"제5조"``와 ``"(통지 방법)"``을 ``"제5조(통지 방법)"``으로 만듦.

    5. ``if text``
       합친 결과에 실제 글자가 있는지 확인하여 빈 줄을 제외함.

    6. ``result.append((tuple(line["bbox"]), text))``
       줄의 위치와 완성한 글자를 한 쌍으로 저장함.
       bbox는 ``(왼쪽 x, 위쪽 y, 오른쪽 x, 아래쪽 y)`` 좌표임.

    7. ``return result``
       페이지에서 추출한 모든 ``(줄 위치, 줄 내용)``을 목록으로 반환함.

    반환값 일부는 다음과 같음. 좌표는 설명을 위한 예시임::

        [
            ((28, 15, 230, 48), "제5조(통지 방법)"),
            ((28, 67, 1000, 96), "① 카드사는 앱 알림, 문자, 전자우편 또는 우편 중 ..."),
            ((78, 201, 265, 250), "통지 종류"),
            ((285, 201, 465, 250), "기본 수단"),
            ((78, 251, 265, 299), "약관 변경"),
            ((285, 251, 465, 299), "앱 알림"),
            ((467, 251, 649, 299), "전자우편"),
            ((650, 251, 972, 299), "발송일·열람일"),
        ]

    이 함수는 표를 행·열 구조로 완성하지 않음. 같은 y 위치의 표 셀도 별도 줄로 저장될 수 있음.
    이후 ``_row_text``가 가까운 y 좌표의 셀을 같은 행으로 묶고 x 좌표 순서로 정렬하여
    ``약관 변경 | 앱 알림 | 전자우편 | 발송일·열람일``처럼 합침.
    """
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


_D2_HEADING = re.compile(r"^D2-C\d{3}(?:-B\d+)?(?:\s*\||$)")
_D2_TABLE_END = re.compile(
    r"^(?:D2-C\d{3}(?:-B\d+)?(?:\s*\||$)|가상 시행일|연회비$|모든 명칭|일반 혜택|"
    r"가족카드:|카드별 명칭|PDF 검색)"
)
_MARKDOWN_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$")


def _normalize_d2_tables(text: str) -> tuple[str, int]:
    """D2의 좌표 기반 표를 Markdown으로 바꾸고 새로 변환한 표 수를 반환함."""

    lines = text.splitlines()
    output, in_table, converted = [], False, 0
    for index, line in enumerate(lines):
        is_heading = bool(_D2_HEADING.match(line))
        is_metadata = line.startswith("가상 시행일")
        is_separator = bool(_MARKDOWN_SEPARATOR.match(line))
        if is_separator and in_table:
            output.append(line)
            continue
        if "|" in line and not is_heading and not is_metadata:
            cells = line.strip().strip("|").strip()
            output.append(f"| {cells} |")
            if not in_table:
                next_is_separator = index + 1 < len(lines) and bool(_MARKDOWN_SEPARATOR.match(lines[index + 1]))
                if not next_is_separator:
                    output.append("| " + " | ".join(["---"] * len(cells.split("|"))) + " |")
                    converted += 1
            in_table = True
        elif in_table and line and not _D2_TABLE_END.match(line):
            output[-1] = output[-1].rstrip("| ") + " " + line.strip() + " |"
        else:
            output.append(line)
            in_table = False
    return "\n".join(output), converted


def _metadata_from_pages(page_lines, filename, pdf_creation_date=""):
    """전체 문서 문자열을 만들지 않고 페이지별 메타데이터를 누적함."""

    common = {"effective_date": None, "version": None, "created_at": None}
    for lines in page_lines:
        page_text = "\n".join(text for _, text in lines)
        if common["effective_date"] is None:
            effective = re.search(
                r"(?:effective_date\s*|시행일[: ]*)(\d{4})[-년 ]+(\d{1,2})[-월 ]+(\d{1,2})",
                page_text,
            )
            if effective:
                common["effective_date"] = "-".join(
                    (effective[1], effective[2].zfill(2), effective[3].zfill(2))
                )
        if common["version"] is None:
            version = re.search(r"(?:version\s*|버전[: ]*)(\d+(?:\.\d+)+)", page_text)
            if version:
                common["version"] = version[1]
        if common["created_at"] is None:
            created = re.search(r"(?:created_at|작성일)\s*[:：]?\s*(\d{4}-\d{2}-\d{2})", page_text)
            if created:
                common["created_at"] = created[1]

        if all(common[key] is not None for key in ("effective_date", "version", "created_at")):
            break

    # 파일명이나 문서 전체에서 한 번만 판단하면 되는 값은 페이지 루프 밖에서 설정함.
    common.update({
        "source": filename,
        "doc_type": "regulation" if filename.startswith("D1") else "benefit_guide" if filename.startswith("D2") else "pdf",
        "supersedes": None,
        "owner_dept": None,
        "synthetic": any("합성" in text for lines in page_lines for _, text in lines),
        "metadata_origin": "source_text; missing values require instructor configuration",
    })

    # 본문에 작성일이 없으면 PDF 파일의 생성일을 보조값으로 사용함.
    creation = re.match(r"D:(\d{4})(\d{2})(\d{2})", pdf_creation_date)
    if common["created_at"] is None and creation:
        common["created_at"] = "-".join(creation.groups())
        common["created_at_origin"] = "pdf_creationDate (file creation, not business publication)"
    return common


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
            #   ├─ [4-1] 페이지별 시행일·버전·작성일 추출
            #   ├─ [4-2] 파일명·본문 메타데이터 통합 및 PDF 생성일 보완
            #   └─ [4-3] 누락값 경고 기록
            #   ↓
            # [5] 각 페이지를 최종 Document로 변환
            #   ├─ [5-1] 여백·페이지 번호 줄 제거
            #   ├─ [5-2] 선이 있는 표를 Markdown 표로 변환
            #   ├─ [5-3] 일반 텍스트와 표를 결합하고 D2 테두리 없는 표를 Markdown으로 변환
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
            for page, lines in zip(pdf, page_lines):  # zip: 1쪽 page와 1쪽 lines처럼 같은 순서끼리 한 쌍으로 묶음.
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
            # ----- [4-1·2] 페이지별 값 추출, 공통값 설정, PDF 생성일 보완 -----
            common = _metadata_from_pages(
                page_lines,
                path.name,
                pdf.metadata.get("creationDate", ""),
            )

            # ----- [4-3] 누락값 경고 기록 -----
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
                # D2의 테두리 없는 표는 좌표 정렬로 만든 "셀 | 셀" 행을 추출 단계에서 Markdown 표로 완성함.
                borderless_tables = 0
                if common["doc_type"] == "benefit_guide":
                    content, borderless_tables = _normalize_d2_tables(content)
                    report["tables"] += borderless_tables
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
                metadata["table_count"] = len(replacements) + borderless_tables
                documents.append(Document(page_content=content, metadata=metadata))
                report["clean_chars"] += len(content)

            # ===== [6] 전체 처리 보고서 마무리 =====
            # 파일 전체의 최종 페이지 수를 보고서에 기록함.
            report["pages"] = len(pdf)
        return documents, report


def extract_pdf(path: Path, remove_margins: bool = True):
    return PdfReader().read(path, remove_margins=remove_margins)
