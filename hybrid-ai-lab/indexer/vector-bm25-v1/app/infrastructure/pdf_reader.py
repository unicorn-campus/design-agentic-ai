"""PyMuPDF 텍스트 계층을 Document로 변환하는 어댑터."""

from collections import Counter
from pathlib import Path
import re

from langchain_core.documents import Document
import pymupdf

from app.application.ports import PdfReaderPort


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
    """같은 높이의 조각들을 한 행으로 합쳐 ``(세로 좌표, 텍스트, 오른쪽 끝 좌표)`` 목록을 만듦.

    오른쪽 끝 좌표를 함께 돌려주는 이유는 뒤에서 줄바꿈을 복원하기 위해서임.
    행이 페이지 오른쪽 끝까지 찼는지 여부가 "폭이 차서 접힌 줄"과 "문단이 끝난 줄"을
    가르는 단서인데, 그 판단은 이 함수 밖에서 하므로 좌표를 버리지 않고 넘겨야 함.
    """

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
        # 행에 속한 조각 중 가장 오른쪽 끝(x1)이 이 행이 도달한 오른쪽 한계임.
        result.append((y, text, max(rectangle[2] for rectangle, _ in cells)))
    return result


# ===== 접힌 줄 복원 =====
#
# [왜 필요한가]
# PDF는 "눈에 보이는 줄"만 알려 주고, 그 줄바꿈이 문단이 끝나서 생긴 것인지 폭이 차서
# 자동으로 접힌 것인지는 알려 주지 않음. 접힌 줄을 그대로 줄바꿈으로 남기면 한국어 낱말이
# 가운데서 갈라짐. 실제로 D1 약관에서 "반환 기준액"이 "반환 기 / 준액"으로 접혀 있었고,
# 본문에 "반환 기 준액"처럼 낱말 가운데 공백이 생겨 원문 그대로 인용해도 검증에 실패했음.
#
# [어떻게 판정하는가]
# 세 단계로 내려가며, 앞 단계에서 결론이 나면 뒤 단계는 보지 않음.
#   1단계(기하)  행이 오른쪽 끝까지 차지 않았으면 문단·문장이 끝난 것임. 줄바꿈을 유지함.
#                D1 실측에서 줄 경계 418건 중 314건(75%)이 여기서 끝남.
#   2단계(문서)  같은 문서의 "줄 안쪽" 글자에서 이 낱말이 붙여 쓰이는지 띄어 쓰이는지 세어
#                다수결로 정함. 줄 안쪽 띄어쓰기는 조판이 아니라 원저자가 쓴 것이라 믿을 수 있음.
#                실측에서 애매한 457건 중 364건(80%)을 판정했고 틀린 사례가 없었음. 특히
#                "본인회원"·"이의신청"처럼 이 문서에서만 쓰는 용어를 정확히 붙임.
#   3단계(Kiwi)  문서에 근거가 없을 때만 형태소 분석기에 물음. 문장 전체를 다시 띄어쓰게 하면
#                멀쩡한 낱말까지 바꿔("기준액" → "기준 액") 원문이 훼손되므로, 이음매 한 자리에
#                공백이 생기는지만 보고 나머지 변경은 버림.
#
# [쓰지 않은 신호]
# 줄 끝에 공백이 남았는지도 단서가 될 수 있으나, 양끝맞춤 조판이 줄 끝 공백을 지워
# 실측에서 D2는 388건 중 3건만 남아 있었음. 단독으로는 신뢰할 수 없어 쓰지 않음.

_WRAP_SLACK = 12.0  # 오른쪽 끝에서 이만큼(PDF 포인트) 안쪽에 멈추면 문단 끝으로 봄
_CELL_SEPARATOR = " | "  # _row_text가 같은 행의 떨어진 칸을 이을 때 넣는 표시. 표 행을 가려내는 데 씀
_VOTE_WINDOWS = (4, 3, 2)  # 문서 근거를 찾을 때 볼 이음매 좌우 글자 수. 긴 창부터 봐 우연한 일치를 줄임
_HANGUL = re.compile(r"[가-힣]")


def build_line_joiner(page_lines):
    """문서 전체를 한 번 훑어 접힌 줄 판정에 필요한 기준 두 가지를 준비함.

    기준 말뭉치
        줄 '안쪽'의 띄어쓰기는 원저자가 쓴 그대로지만 줄 '경계'의 띄어쓰기는 조판이
        만들어낸 것이라 믿을 수 없음. 그래서 줄 안쪽 글자만 모으고, 줄과 줄 사이는
        줄바꿈으로 막아 경계를 넘는 우연한 일치를 차단함.

    오른쪽 한계
        본문이 도달하는 가장 오른쪽 좌표이며, 어떤 행이 '폭이 차서 접힌 줄'인지 재는 자임.
        페이지마다 따로 구하면 표지·차례처럼 짧은 줄만 있는 페이지에서 그 페이지의 최댓값
        자체가 짧아져 모든 줄이 접힌 것처럼 보임. 그래서 문서 전체에서 한 번만 구함.
        이 값을 크게 잡으면 줄바꿈이 남을 뿐이지만(안전) 작게 잡으면 낱말을 잘못 붙이므로
        (위험), 최댓값을 쓰는 보수적인 선택을 함.

    문서 전체를 봐야 하므로 페이지 반복에 들어가기 전에 한 번만 호출함.
    """

    return _LineJoiner(
        reference="\n".join(text for lines in page_lines for _, text in lines),
        right_edge=max(
            (rectangle[2] for lines in page_lines for rectangle, _ in lines),
            default=0.0,
        ),
    )


class _LineJoiner:
    """접힌 줄을 이을 때 공백을 넣을지 말지 판정함.

    Kiwi는 만드는 비용이 커서 실제로 3단계까지 내려갈 때만 만들고(문서 근거만으로 끝나면
    아예 만들지 않음), 같은 이음매를 여러 번 묻는 경우가 많아 판정 결과를 캐시함.
    """

    def __init__(self, reference="", right_edge=0.0):
        self._reference = reference
        self.right_edge = right_edge
        self._kiwi = None
        self._cache = {}

    def needs_space(self, left, right):
        """이음매에 공백을 넣어야 하면 True를 반환함."""

        window = max(_VOTE_WINDOWS)
        key = (left[-window:], right[:window])
        if key not in self._cache:
            decided = self._vote_in_document(*key)
            self._cache[key] = self._ask_kiwi(left, right) if decided is None else decided
        return self._cache[key]

    def _vote_in_document(self, left_tail, right_head):
        """2단계. 같은 문서에서 이 이음매를 붙여 쓰는지 띄어 쓰는지 세어 다수결로 정함.

        긴 창부터 시도해 먼저 근거가 나오는 창을 채택함. 창이 길수록 우연히 일치할 확률이
        낮아 더 믿을 만함. 근거가 없거나(둘 다 0) 표가 같으면 다음 창으로 내려가고, 끝까지
        결론이 없으면 None을 돌려 3단계에 넘김.
        """

        for window in _VOTE_WINDOWS:
            before, after = left_tail[-window:], right_head[:window]
            if len(before) < window or len(after) < window:
                continue
            glued = self._reference.count(before + after)
            spaced = self._reference.count(before + " " + after)
            if glued == spaced:
                continue
            return spaced > glued
        return None

    def _ask_kiwi(self, left, right):
        """3단계. 붙인 문장을 Kiwi에 띄어쓰기시킨 뒤 '이음매 그 자리'만 확인함.

        Kiwi가 다른 자리에 넣은 공백은 원문을 바꾸는 것이므로 모두 버리고, 이음매 위치에
        공백이 생겼는지만 본다. 위치는 공백을 뺀 글자 수로 세어, Kiwi가 앞쪽 띄어쓰기를
        바꾸더라도 같은 지점을 가리키게 함.
        """

        left, right = left[-25:], right[:25]  # 판정에 필요한 만큼만 넘겨 분석 비용을 줄임
        try:
            spaced = self._load_kiwi().space(left + right)
        except Exception:
            return False  # 분석기를 못 쓰면 낱말이 갈라지지 않는 쪽(붙임)을 택함
        target = len(left.replace(" ", ""))
        seen, previous_was_space = 0, False
        for char in spaced:
            if char == " ":
                previous_was_space = True
                continue
            if seen == target:
                return previous_was_space
            seen += 1
            previous_was_space = False
        return False

    def _load_kiwi(self):
        if self._kiwi is None:
            from kiwipiepy import Kiwi

            self._kiwi = Kiwi()
        return self._kiwi


def _separator(previous, current, joiner):
    """앞 행과 뒤 행 사이에 넣을 글자를 고름. 줄바꿈이면 접힌 줄이 아니라는 뜻임."""

    _, previous_text, previous_right = previous
    _, current_text, current_right = current
    # Markdown 표는 줄바꿈 자체가 구조라 절대 잇지 않음. 좌표가 없는 항목이 표 덩어리임.
    if previous_right is None or current_right is None:
        return "\n"
    # D2의 테두리 없는 표는 선이 없어 find_tables가 못 잡고, 좌표로만 칸을 나눈
    # "셀 | 셀" 행으로 여기까지 옴. 표 모양은 뒤에서 _normalize_d2_tables가 완성함.
    #
    # 판단 기준은 '다음 행'에만 둠. 다음 행에 칸 구분자가 있으면 그 행은 새 표 행이므로
    # 이으면 한 행에 칸이 두 벌 들어가 표가 밀림. 반대로 칸 구분자가 없으면 앞 칸의 글이
    # 폭에 밀려 흘러내린 이어짐이라 이어야 함. 실제 D2가 아래 두 모양을 모두 만듦.
    #   새 표 행   "실적 조건 | …" + "대상 포인트 | …"   -> 끊음
    #   칸 이어짐  "실적 조건 | …취소액은 실" + "에서 제외함."  -> 이음
    # 앞 행까지 함께 보면 뒤쪽(칸 이어짐)까지 막혀 표 안의 낱말이 갈라진 채 남음.
    if _CELL_SEPARATOR in current_text:
        return "\n"
    # 1단계. 오른쪽 끝까지 차지 않은 행은 문단·문장이 끝나서 바뀐 것임.
    if joiner.right_edge - previous_right >= _WRAP_SLACK:
        return "\n"
    left, right = previous_text.rstrip(), current_text.lstrip()
    if not left or not right:
        return "\n"
    # 한글끼리 만나는 자리만 애매함. 숫자·영문·기호가 섞이면 공백을 넣는 쪽이 안전함.
    if not (_HANGUL.match(left[-1]) and _HANGUL.match(right[0])):
        return " "
    return " " if joiner.needs_space(left, right) else ""


def join_page_rows(items, joiner):
    """한 페이지의 행 목록을 본문 문자열로 조립함.

    items는 ``(세로 좌표, 텍스트, 오른쪽 끝 좌표)`` 목록이며 세로 좌표 순으로 정렬돼 있어야 함.
    오른쪽 끝 좌표가 None인 항목은 Markdown 표처럼 손대면 안 되는 덩어리임.
    판정 기준(기준 말뭉치·오른쪽 한계)은 문서 전체에서 구한 값이라 joiner가 들고 있음.
    """

    if not items:
        return ""
    pieces = [items[0][1]]
    for previous, current in zip(items, items[1:]):
        pieces.append(_separator(previous, current, joiner))
        pieces.append(current[1])
    return "".join(pieces)


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


class PdfReader(PdfReaderPort):
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

            # ===== [3-2] 접힌 줄 판정용 기준 말뭉치 준비 =====
            # 문서 전체의 줄 안쪽 띄어쓰기를 근거로 삼으므로, 페이지 반복에 들어가기 전에
            # 한 번만 만들어 모든 페이지가 같은 기준을 쓰게 함.
            joiner = build_line_joiner(page_lines)

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
                    # 세 번째 값 None은 "손대면 안 되는 덩어리"라는 표시임. 표는 줄바꿈이
                    # 곧 구조라 접힌 줄 복원 대상에서 빼야 하므로 오른쪽 좌표를 두지 않음.
                    replacements.append((rectangle.y0, "\n".join(markdown), None))
                    
                    report["tables"] += 1

                    # 선이 있는 표로 감지되어 검증 후 Markdown으로 변환한 표의 수를 집계함.
                    report["ruled_tables"] += 1

                # ----- [5-3] 텍스트+표 구성 -----
                # 남은 텍스트를 좌표 순서대로 한 줄씩 조합함.
                rows = _row_text(kept)

                # 일반 텍스트 행과 변환된 표를 원래 세로 순서대로 합쳐 페이지의 최종 본문을 만듦.
                # sorted는 여러 항목을 정렬한 새 목록을 반환하고, key는 정렬 기준을 정함.
                # lambda item: item[0]은 (세로 좌표, 텍스트, 오른쪽 좌표)에서 첫 값인 세로 좌표를 기준으로 선택함.
                # 예: [(300, "본문", 520), (100, "표", None)]은 세로 좌표가 작은 표가 먼저 오도록 정렬됨.
                #
                # 예전에는 여기서 모든 행을 "\n"으로 이었으나, 그러면 폭이 차서 접힌 줄까지
                # 문단 바뀜으로 굳어져 한국어 낱말이 가운데서 갈라졌음. join_page_rows가
                # 행마다 줄바꿈·공백·붙임 중 하나를 골라 그 문제를 없앰.
                content = join_page_rows(
                    sorted(rows + replacements, key=lambda item: item[0]),
                    joiner,
                )
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
