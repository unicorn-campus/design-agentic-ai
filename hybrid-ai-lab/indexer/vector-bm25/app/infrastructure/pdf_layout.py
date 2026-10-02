"""PDF 페이지 좌표로 여백 제거·접힌 줄 복원·표 Markdown 변환을 마친 페이지 본문을 만듦."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Callable, Iterable

import pymupdf

# 표 탐지(find_tables)를 처음 부를 때 PyMuPDF가 표준 출력에 권장 문구를 찍음. 표준 출력은 결과 JSON 전용이므로 끔.
pymupdf.no_recommend_layout()

# 줄 상자 좌표 (x0, y0, x1, y1)
BBox = tuple[float, ...]
# 페이지 본문을 이룰 한 항목. 오른쪽 끝 좌표가 None이면 Markdown 표처럼 손대면 안 되는 덩어리임
RowItem = tuple[float, str, float | None]

_WRAP_SLACK = 12.0  # 오른쪽 끝에서 이만큼(PDF 포인트) 안쪽에 멈추면 문단 끝으로 봄
_CELL_GAP = 12.0  # 같은 높이의 조각이 이만큼 떨어져 있으면 표의 다른 칸으로 봄
_CELL_SEPARATOR = " | "  # 같은 행의 떨어진 칸을 이을 때 넣는 표시. 표 행을 가려내는 데 씀
_VOTE_WINDOWS = (4, 3, 2)  # 문서 근거를 찾을 때 볼 이음매 좌우 글자 수. 긴 창부터 봐 우연한 일치를 줄임
_HANGUL = re.compile(r"[가-힣]")

_D2_HEADING = re.compile(r"^D2-C\d{3}(?:-B\d+)?(?:\s*\||$)")
# 테두리 없는 D2 표가 끝나는 줄. 표 아래 안내 문구가 표 칸으로 빨려 들어가지 않게 함
_D2_TABLE_END = re.compile(
    r"^(?:D2-C\d{3}(?:-B\d+)?(?:\s*\||$)|가상 시행일|연회비$|모든 명칭|일반 혜택|"
    r"가족카드:|카드별 명칭|PDF 검색)"
)
_MARKDOWN_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$")


def page_lines(page_dict: dict[str, Any]) -> list[tuple[BBox, str]]:
    """PyMuPDF 텍스트 계층에서 읽기 순서로 정렬된 줄과 좌표를 추출함."""

    lines: list[tuple[BBox, str]] = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            value = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if value:
                lines.append((tuple(line["bbox"]), value))
    return sorted(lines, key=lambda item: (round(item[0][1], 1), item[0][0]))


def margin_key(line: str) -> str:
    """페이지 번호가 달라도 같은 여백 문구로 셀 수 있도록 숫자를 일반화함."""

    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line)).strip()


def is_margin(bbox: BBox, height: float) -> bool:
    """줄이 페이지 위쪽 7% 또는 아래쪽 7%에 속하는지 판정함."""

    return bbox[3] < height * 0.07 or bbox[1] > height * 0.93


def repeated_margin_keys(pages: Iterable[tuple[float, list[tuple[BBox, str]]]], minimum: int) -> set[str]:
    """설정된 최소 페이지 수 이상 반복되는 여백 문구를 찾음.

    인자: pages는 (페이지 높이, 줄 목록) 묶음이며, minimum은 반복으로 볼 최소 페이지 수임.
    반환값: 숫자를 일반화한 여백 문구 집합임. 같은 페이지 안의 중복은 한 번만 셈.
    """

    counter: Counter[str] = Counter()
    for height, lines in pages:
        counter.update({margin_key(text) for bbox, text in lines if is_margin(bbox, height)})
    return {key for key, count in counter.items() if key and count >= minimum}


def row_text(lines: list[tuple[BBox, str]]) -> list[RowItem]:
    """같은 높이의 조각들을 한 행으로 합쳐 (세로 좌표, 텍스트, 오른쪽 끝 좌표) 목록을 만듦.

    오른쪽 끝 좌표를 함께 넘기는 이유: 행이 페이지 오른쪽 끝까지 찼는지가 "폭이 차서 접힌 줄"과
    "문단이 끝난 줄"을 가르는 단서이며, 그 판단은 이 함수 밖의 줄 잇기 단계에서 함.
    """

    rows: list[list[Any]] = []
    for rectangle, text in sorted(lines, key=lambda item: (round(item[0][1], 1), item[0][0])):
        if rows and abs(rows[-1][0] - rectangle[1]) < 2:
            rows[-1][1].append((rectangle, text))
        else:
            rows.append([rectangle[1], [(rectangle, text)]])
    result: list[RowItem] = []
    for y, cells in rows:
        cells.sort(key=lambda item: item[0][0])
        text = cells[0][1]
        for previous, current in zip(cells, cells[1:]):
            text += (_CELL_SEPARATOR if current[0][0] - previous[0][2] > _CELL_GAP else " ") + current[1]
        result.append((y, text, max(rectangle[2] for rectangle, _ in cells)))
    return result


class LineJoiner:
    """접힌 줄을 이을 때 공백을 넣을지 말지 판정함.

    왜 필요한가: PDF는 눈에 보이는 줄만 알려 주고 그 줄바꿈이 문단 끝인지 폭이 차서 접힌 것인지는
    알려 주지 않음. 접힌 줄을 그대로 두면 "반환 기 / 준액"처럼 한국어 낱말이 가운데서 갈라짐.
    판정 순서: ① 기하(행이 오른쪽 끝까지 찼는가) → ② 같은 문서의 줄 안쪽 띄어쓰기 다수결 → ③ Kiwi.
    앞 단계에서 결론이 나면 뒤 단계는 보지 않음. Kiwi는 만드는 비용이 커서 ③까지 갈 때만 만듦.
    """

    def __init__(
        self,
        reference: str = "",
        right_edge: float = 0.0,
        spacer_factory: Callable[[], Any] | None = None,
    ) -> None:
        """문서 전체의 줄 안쪽 글자와 본문 오른쪽 한계를 기준으로 설정함.

        인자: reference는 줄 경계를 줄바꿈으로 막은 문서 전체 글자이며, right_edge는 본문 최대 오른쪽 좌표임.
        인자: spacer_factory는 시험에서 Kiwi를 대체할 생성 함수이며 None이면 Kiwi를 사용함.
        부수효과: 없음. Kiwi는 실제로 필요할 때 처음 만듦.
        """

        self._reference = reference
        self.right_edge = right_edge
        self._spacer_factory = spacer_factory
        self._spacer: Any = None
        self._cache: dict[tuple[str, str], bool] = {}

    @classmethod
    def for_document(
        cls,
        pages: Iterable[list[tuple[BBox, str]]],
        spacer_factory: Callable[[], Any] | None = None,
    ) -> LineJoiner:
        """문서 전체를 한 번 훑어 판정 기준 두 가지를 준비함.

        오른쪽 한계를 페이지마다 구하지 않는 이유: 표지·차례처럼 짧은 줄만 있는 페이지에서는 그 페이지의
        최댓값 자체가 짧아져 모든 줄이 접힌 것처럼 보임. 크게 잡으면 줄바꿈이 남을 뿐(안전)이지만
        작게 잡으면 낱말을 잘못 붙이므로(위험) 문서 전체 최댓값을 씀.
        """

        all_lines = [item for lines in pages for item in lines]
        return cls(
            reference="\n".join(text for _, text in all_lines),
            right_edge=max((rectangle[2] for rectangle, _ in all_lines), default=0.0),
            spacer_factory=spacer_factory,
        )

    def needs_space(self, left: str, right: str) -> bool:
        """이음매에 공백을 넣어야 하면 True를 반환함."""

        window = max(_VOTE_WINDOWS)
        key = (left[-window:], right[:window])
        if key not in self._cache:
            decided = self._vote_in_document(*key)
            self._cache[key] = self._ask_spacer(left, right) if decided is None else decided
        return self._cache[key]

    def _vote_in_document(self, left_tail: str, right_head: str) -> bool | None:
        """같은 문서에서 이 이음매를 붙여 쓰는지 띄어 쓰는지 세어 다수결로 정함.

        줄 안쪽 띄어쓰기는 조판이 아니라 원저자가 쓴 것이라 믿을 수 있음. 근거가 없거나 표가 같으면
        더 짧은 창으로 내려가고, 끝까지 결론이 없으면 None을 돌려 Kiwi 판정으로 넘김.
        """

        for window in _VOTE_WINDOWS:
            before, after = left_tail[-window:], right_head[:window]
            if len(before) < window or len(after) < window:
                continue
            glued = self._reference.count(before + after)
            spaced = self._reference.count(before + " " + after)
            if glued != spaced:
                return spaced > glued
        return None

    def _ask_spacer(self, left: str, right: str) -> bool:
        """붙인 문장을 Kiwi로 띄어쓰기한 뒤 이음매 그 자리에 공백이 생겼는지만 확인함.

        Kiwi가 다른 자리에 넣은 공백은 원문을 바꾸는 것이므로 모두 버림. 위치는 공백을 뺀 글자 수로 세어
        Kiwi가 앞쪽 띄어쓰기를 바꾸더라도 같은 지점을 가리키게 함.
        """

        left, right = left[-25:], right[:25]  # 판정에 필요한 만큼만 넘겨 분석 비용을 줄임
        try:
            spaced = self._load_spacer().space(left + right)
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

    def _load_spacer(self) -> Any:
        """Kiwi 또는 주입된 띄어쓰기 도구를 한 번만 만듦."""

        if self._spacer is None:
            if self._spacer_factory is not None:
                self._spacer = self._spacer_factory()
            else:
                from kiwipiepy import Kiwi

                self._spacer = Kiwi()
        return self._spacer


def _separator(previous: RowItem, current: RowItem, joiner: LineJoiner) -> str:
    """앞 행과 뒤 행 사이에 넣을 글자를 고름. 줄바꿈이면 접힌 줄이 아니라는 뜻임."""

    _, previous_text, previous_right = previous
    _, current_text, _current_right = current
    # Markdown 표는 줄바꿈 자체가 구조라 절대 잇지 않음
    if previous_right is None or _current_right is None:
        return "\n"
    # 다음 행에 칸 구분자가 있으면 새 표 행이므로 끊음. 없으면 앞 칸 글이 폭에 밀려 흘러내린 것이라 이음
    if _CELL_SEPARATOR in current_text:
        return "\n"
    # ① 기하: 오른쪽 끝까지 차지 않은 행은 문단·문장이 끝나서 바뀐 것임
    if joiner.right_edge - previous_right >= _WRAP_SLACK:
        return "\n"
    left, right = previous_text.rstrip(), current_text.lstrip()
    if not left or not right:
        return "\n"
    # 한글끼리 만나는 자리만 애매함. 숫자·영문·기호가 섞이면 공백을 넣는 쪽이 안전함
    if not (_HANGUL.match(left[-1]) and _HANGUL.match(right[0])):
        return " "
    return " " if joiner.needs_space(left, right) else ""


def join_page_rows(items: list[RowItem], joiner: LineJoiner) -> str:
    """세로 순서로 정렬된 한 페이지의 행을 줄바꿈·공백·붙임 중 하나로 이어 본문을 만듦."""

    if not items:
        return ""
    pieces = [items[0][1]]
    for previous, current in zip(items, items[1:]):
        pieces.append(_separator(previous, current, joiner))
        pieces.append(current[1])
    return "".join(pieces)


def ruled_tables(
    page: Any,
    lines: list[tuple[BBox, str]],
) -> tuple[list[RowItem], list[tuple[BBox, str]], list[str]]:
    """선이 있는 표를 Markdown 덩어리로 바꾸고 표에 들어간 줄을 본문 줄에서 뺌.

    방법: PyMuPDF 표 탐지 결과의 셀 글자와 표 영역 원문 줄의 글자 수가 같을 때만 변환함.
    반환값: (표 덩어리 목록, 남은 줄 목록, 경고 목록)임. 탐지가 실패하면 원래 줄을 그대로 돌려줌.
    부수효과: 없음. 페이지 객체를 읽기만 함.
    """

    tables: list[RowItem] = []
    warnings: list[str] = []
    try:
        found = page.find_tables().tables
    except Exception as error:  # 표 탐지 실패가 문서 전체 처리를 막지 않게 하고 원문 줄을 유지함
        return [], lines, [f"table detection failed ({type(error).__name__}); text retained"]
    kept = list(lines)
    for table in found:
        matrix = table.extract()
        if not matrix or len(matrix[0]) < 2:
            continue
        rectangle = pymupdf.Rect(table.bbox)
        contained = [
            (box, text) for box, text in kept
            if rectangle.contains(pymupdf.Rect(box).tl) and rectangle.contains(pymupdf.Rect(box).br)
        ]
        # 셀 추출이 글자를 빠뜨리거나 덧붙이면 원문 줄을 그대로 둠. 표 모양보다 내용 보존이 우선임
        source_chars = Counter(re.sub(r"\s", "", "".join(text for _, text in contained)))
        table_chars = Counter(re.sub(r"\s", "", "".join(str(cell or "") for row in matrix for cell in row)))
        if source_chars != table_chars:
            warnings.append("detected table retained as positioned text (glyph mismatch)")
            continue
        markdown: list[str] = []
        for row_number, row in enumerate(matrix):
            cells = (str(cell or "").replace("\n", " ").replace("|", "\\|") for cell in row)
            markdown.append("| " + " | ".join(cells) + " |")
            if row_number == 0:
                markdown.append("| " + " | ".join("---" for _ in row) + " |")
        kept = [item for item in kept if item not in contained]
        tables.append((rectangle.y0, "\n".join(markdown), None))
    return tables, kept, warnings


def normalize_d2_tables(text: str) -> tuple[str, int]:
    """D2의 테두리 없는 표(좌표로 만든 "셀 | 셀" 행)를 Markdown 표로 바꾸고 변환한 표 수를 반환함.

    테두리 선이 없어 PyMuPDF 표 탐지가 잡지 못하는 표를 대상으로 함. 칸 구분자가 없는 다음 줄은
    앞 칸 글이 폭에 밀려 흘러내린 것으로 보고 마지막 칸에 이어 붙임.
    """

    lines = text.splitlines()
    output: list[str] = []
    in_table, converted = False, 0
    for index, line in enumerate(lines):
        # 표 안에서 "D2-C001 | 카드명 | 3"처럼 칸이 둘 이상인 줄은 카드 목록표의 행이지 카드 머리글이 아님.
        is_heading = bool(_D2_HEADING.match(line)) and not (in_table and line.count("|") >= 2)
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
            # 흘러내린 글은 직전 표 행에 붙임. 직전 줄이 구분선이면 머리글 칸이 접힌 것이므로 머리글에 붙임.
            target = -2 if _MARKDOWN_SEPARATOR.match(output[-1]) and len(output) >= 2 else -1
            output[target] = output[target].rstrip("| ") + " " + line.strip() + " |"
        else:
            output.append(line)
            in_table = False
    return "\n".join(output), converted


def page_body(
    page: Any,
    lines: list[tuple[BBox, str]],
    joiner: LineJoiner,
    *,
    borderless_tables: bool,
) -> tuple[str, list[str]]:
    """여백을 뺀 한 페이지의 줄로 표 변환과 줄 잇기를 마친 본문을 만듦.

    인자: lines는 여백 제거를 마친 줄 목록이며, borderless_tables가 참이면 D2 테두리 없는 표도 변환함.
    반환값: (페이지 본문, 경고 목록)임.
    부수효과: 없음.
    """

    tables, kept, warnings = ruled_tables(page, lines)
    content = join_page_rows(sorted(row_text(kept) + tables, key=lambda item: item[0]), joiner)
    if borderless_tables:
        content, _ = normalize_d2_tables(content)
    return content, warnings
