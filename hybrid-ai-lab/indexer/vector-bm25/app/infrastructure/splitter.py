"""임베딩 모델의 토큰 계산기를 공유하는 공통 문서 분할기임."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from app.application.ports import TextSplitterPort, TokenCounterPort
from app.domain.models import LoadedDocument, RawChunk, SplitPolicy


class RecursiveDocumentSplitter(TextSplitterPort):
    """문서별 정규식 경계를 공통 RecursiveCharacterTextSplitter에 주입함.

    토큰 계산기와 문서 정책을 주입받으며, 정제·개인정보 치환(로더 담당)과 임베딩은 수행하지 않음.
    """

    def __init__(
        self,
        token_counter: TokenCounterPort,
        policies: str | Path | dict[str, Any],
    ) -> None:
        """토큰 단위 길이 계산기와 문서별 구분자 정책을 설정함.

        부수효과: 정책 경로를 받으면 생성 시점에 JSON 파일을 읽음.
        """

        self._counter = token_counter
        if isinstance(policies, dict):
            self._policies = policies["documents"]
        else:
            self._policies = json.loads(Path(policies).read_text(encoding="utf-8"))["documents"]

    def split(self, document: LoadedDocument, policy: SplitPolicy) -> list[RawChunk]:
        """문서별 경계를 우선해 원문을 토큰 상한 안의 청크로 분할함.

        방법: 정규식 구분자로 재귀 분할한 뒤 원문 좌표를 복원하고, 상한 초과 조각을 실제 토큰 수로 재분할함.
        인자: policy 크기와 중첩은 토큰 단위임. 구분자 끝에 빈 문자열을 보충해 문자 단위 분할을 허용함.
        반환값: 정제 본문 좌표와 순번을 보존한 청크 목록임. 표 중간에서 시작하는 청크는 머리글 행을 앞에 붙임.
        예외: 캡처 그룹이 있거나 원문 좌표를 복원할 수 없거나 토큰 상한을 지킬 수 없으면 ValueError를 발생시킴.
        부수효과: 최초 호출 시 LangChain 분할 모듈과 TokenCounterPort의 토크나이저를 불러와 캐시할 수 있음.
        """

        try:
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError as error:  # pragma: no cover - 선택 의존성 누락을 명확히 알리는 경로임
            raise RuntimeError("langchain-text-splitters 패키지가 필요합니다.") from error

        separators = tuple(self._policies.get(document.doc_key, {}).get("separators", policy.separators))
        if not separators or separators[-1] != "":
            separators = (*separators, "")
        for separator in separators[:-1]:
            if re.compile(separator).groups:
                raise ValueError("분할 정규식에는 캡처 그룹을 사용할 수 없습니다.")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=policy.chunk_size,
            chunk_overlap=policy.chunk_overlap,
            length_function=self._counter.count,
            separators=list(separators),
            is_separator_regex=True,
            keep_separator="start",
            add_start_index=True,
            strip_whitespace=False,
        )
        pieces = splitter.split_documents([Document(page_content=document.text)])
        ranges: list[tuple[int, int]] = []
        aligned = self._align_pieces(document.text, [piece.page_content for piece in pieces])
        for piece, (start, end) in zip(pieces, aligned, strict=True):
            if self._counter.count(piece.page_content) <= policy.chunk_size:
                ranges.append((start, end))
            else:
                ranges.extend(self._strict_ranges(document.text, start, end, policy))

        pieces_with_text: list[tuple[int, int, str]] = []
        for start, end in ranges:
            if start >= end:
                continue
            header = _table_header(document.text, start)
            if header is None:
                pieces_with_text.append((start, end, document.text[start:end]))
                continue
            # 표 중간에서 시작하는 청크는 열 이름을 잃으므로 그 표의 머리글 행을 앞에 다시 붙임.
            for row_start, row_end in self._fit_rows(document.text, start, end, header, policy.chunk_size):
                pieces_with_text.append((row_start, row_end, header + document.text[row_start:row_end]))

        chunks = [
            RawChunk(document, text, start, end, ordinal)
            for ordinal, (start, end, text) in enumerate(pieces_with_text)
        ]
        if any(self._counter.count(chunk.text) > policy.chunk_size for chunk in chunks):
            raise ValueError("청크가 토큰 상한을 초과했습니다.")
        return chunks

    def _fit_rows(self, text: str, start: int, end: int, header: str, limit: int) -> list[tuple[int, int]]:
        """머리글 행을 붙여도 토큰 상한을 넘지 않도록 표 행 경계에서 구간을 다시 나눔.

        반환값: 시작 순서의 (시작, 끝) 목록임. 각 구간에 머리글을 붙인 글이 상한 안에 들어감.
        예외: 머리글과 한 글자도 함께 넣을 수 없으면 ValueError를 발생시킴.
        """

        result: list[tuple[int, int]] = []
        cursor = start
        while cursor < end:
            if self._counter.count(header + text[cursor:end]) <= limit:
                result.append((cursor, end))
                break
            low, high, cut = cursor + 1, end, cursor
            while low <= high:
                middle = (low + high) // 2
                if self._counter.count(header + text[cursor:middle]) <= limit:
                    cut, low = middle, middle + 1
                else:
                    high = middle - 1
            if cut <= cursor:
                raise ValueError("표 머리글과 함께 넣을 수 있는 행이 없습니다. 청크 크기를 늘려야 합니다.")
            # 행 가운데서 자르지 않도록 상한 안의 마지막 행 경계로 물러남. 경계가 없으면 상한 지점에서 자름.
            boundary = text.rfind("\n| ", cursor, cut)
            if boundary > cursor:
                cut = boundary + 1
            result.append((cursor, cut))
            cursor = cut
        return result

    @staticmethod
    def _align_pieces(source: str, pieces: list[str]) -> list[tuple[int, int]]:
        """반복 문자열에서도 모든 원문을 덮는 단조 증가 좌표를 찾음.

        LangChain의 ``start_index``는 토큰 중첩값을 문자 오프셋처럼 빼기 때문에 반복 문자열에서
        앞선 위치를 다시 가리킬 수 있음. 본 함수는 분할 결과의 순서를 유지하면서 구간 사이에
        빠진 글자가 없고 마지막 글자까지 덮는 경로만 허용함.
        """

        if not pieces:
            return []
        if not source.startswith(pieces[0]):
            raise ValueError("첫 분할 결과가 원문 시작과 일치하지 않습니다.")
        first = (0, len(pieces[0]))

        states: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {first: (first,)}
        for piece in pieces[1:]:
            next_states: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {}
            for (previous_start, covered_end), path in states.items():
                cursor = source.find(piece, previous_start + 1, covered_end + len(piece) + 1)
                while cursor >= 0 and cursor <= covered_end:
                    end = cursor + len(piece)
                    if end > covered_end:
                        next_states.setdefault((cursor, end), (*path, (cursor, end)))
                    cursor = source.find(piece, cursor + 1, covered_end + len(piece) + 1)
            if not next_states:
                raise ValueError("분할 결과를 원문 좌표에 누락 없이 정렬할 수 없습니다.")
            states = next_states

        completed = [path for (_, end), path in states.items() if end == len(source)]
        if not completed:
            raise ValueError("분할 결과를 원문 좌표에 누락 없이 정렬할 수 없습니다.")
        return list(completed[0])

    def _strict_ranges(
        self,
        source: str,
        start: int,
        end: int,
        policy: SplitPolicy,
    ) -> list[tuple[int, int]]:
        """토크나이저 비가산성으로 남은 초과 청크를 실제 계산값으로 다시 자름."""

        result: list[tuple[int, int]] = []
        cursor = start
        while cursor < end:
            cut = self._largest_fitting_end(source, cursor, end, policy.chunk_size)
            if cut <= cursor:
                raise ValueError("한 글자도 토큰 상한 안에 넣을 수 없습니다.")
            result.append((cursor, cut))
            if cut >= end:
                break
            overlap_start = self._largest_fitting_start(source, cursor, cut, policy.chunk_overlap)
            cursor = max(cursor + 1, overlap_start)
        return result

    def _largest_fitting_end(self, text: str, start: int, end: int, limit: int) -> int:
        """이진 탐색으로 시작점부터 토큰 상한을 만족하는 끝 좌표를 선택함."""

        low, high, best = start + 1, end, start
        while low <= high:
            middle = (low + high) // 2
            if self._counter.count(text[start:middle]) <= limit:
                best, low = middle, middle + 1
            else:
                high = middle - 1
        return best

    def _largest_fitting_start(self, text: str, start: int, end: int, limit: int) -> int:
        """이진 탐색으로 끝점을 유지하며 중첩 토큰 상한을 만족하는 시작 좌표를 선택함."""

        if limit <= 0:
            return end
        low, high, best = start, end, end
        while low <= high:
            middle = (low + high) // 2
            if self._counter.count(text[middle:end]) <= limit:
                best, high = middle, middle - 1
            else:
                low = middle + 1
        return best


_TABLE_SEPARATOR_LINE = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$")


def _table_header(text: str, start: int) -> str | None:
    """start가 Markdown 표의 머리글이 아닌 행에서 시작하면 그 표의 머리글·구분선 두 줄을 반환함.

    방법: start가 속한 표 덩어리(연속한 "| " 줄)를 거슬러 올라가 첫 줄과 구분선을 찾음.
    반환값: "머리글 행\n구분선\n" 문자열 또는 None(표 행으로 시작하지 않거나 이미 머리글에서 시작함).
    """

    if not text.startswith("| ", start) or (start and text[start - 1] != "\n"):
        return None
    lines_before = text[:start].split("\n")[:-1]
    block: list[str] = []
    for line in reversed(lines_before):
        if not line.startswith("|"):
            break
        block.append(line)
    block.reverse()
    if len(block) < 2 or not _TABLE_SEPARATOR_LINE.match(block[1]):
        return None
    return f"{block[0]}\n{block[1]}\n"

