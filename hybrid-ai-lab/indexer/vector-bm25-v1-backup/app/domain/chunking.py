"""조·항·표·상담 턴 경계를 보존하는 결정적 청킹 규칙."""

from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Callable

from langchain_core.documents import Document


CLAUSE_RE = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+)?(?P<no>제\d+조(?:의\d+)?)(?!\d)", re.M)
ITEM_RE = re.compile(r"^[ \t]*\((?P<no>[1-9]\d*)\)", re.M)
CIRCLED_RE = re.compile(r"^[ \t]*(?P<symbol>[①-⑳])", re.M)
TURN_RE = re.compile(r"^[ \t]*(상담사|고객)[ \t]*[:：][ \t]*", re.M)


class ChunkIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class Chunk:
    text: str
    chunk_id: str
    metadata: dict

    def to_document(self) -> Document:
        metadata = {**self.metadata, "chunk_id": self.chunk_id}
        return Document(id=self.chunk_id, page_content=self.text, metadata=metadata)


def _check_int(name: str, value: int, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name}은 {minimum} 이상의 정수여야 함")


def _make(text: str, metadata: dict, doc_key: str, index: int, **extra) -> Chunk:
    chunk_id = (
        f"D3_{metadata['record_id']}_{index:04d}"
        if doc_key == "D3" else f"{doc_key}_{index:04d}"
    )
    merged = {**deepcopy(metadata), **extra, "chunk_index": index, "char_len": len(text)}
    return Chunk(text=text, chunk_id=chunk_id, metadata=merged)


def _doc_key(metadata: dict) -> str:
    value = metadata.get("doc_key")
    if value in {"D1", "D2", "D3"}:
        return value
    source = str(metadata.get("source", "")).replace("\\", "/").rsplit("/", 1)[-1]
    match = re.match(r"(D[123])(?:_|\.|$)", source)
    if match:
        return match.group(1)
    if metadata.get("record_id"):
        return "D3"
    raise ValueError("doc_key 또는 D1/D2/D3 source가 필요함")


def _section(text: str) -> tuple[str, str, str]:
    """이미 나뉜 입력 단위의 첫 줄에서 제목·본문·구분 이름만 꺼냄."""

    stripped = text.strip()
    title, _, body = stripped.partition("\n")

    # D1 입력은 첫 줄의 조 번호를 구분 이름으로 사용함. 예: "제1조(목적)" -> "제1조"
    clause = CLAUSE_RE.match(title)
    if clause:
        return title, body.strip(), clause.group("no")

    # D2 입력은 prepare_units가 붙인 "## " 제목을 구분 이름으로 사용함.
    # 예: "## D2-C058-B04 | 반려생활 제휴" -> "D2-C058-B04 | 반려생활 제휴"
    if title.startswith("## "):
        return title, body.strip(), title.removeprefix("## ").strip()

    # 제목 형식이 없으면 첫 줄도 본문이므로 원문 전체를 돌려줌.
    return "", stripped, "본문"


def _units(body: str) -> list[str]:
    starts = sorted({0, len(body), *(m.start() for m in ITEM_RE.finditer(body)), *(m.start() for m in CIRCLED_RE.finditer(body))})
    return [body[start:end].strip() for start, end in zip(starts, starts[1:]) if body[start:end].strip()]


def _cut(text: str, capacity: int) -> tuple[str, str]:
    boundaries = [m.end() for m in re.finditer(r"[.!?。](?:\s+|$)|\n+", text[:capacity])]
    stop = boundaries[-1] if boundaries else capacity
    return text[:stop].rstrip(), text[stop:].lstrip()


def _split_prose(title: str, body: str, max_chars: int, overlap: int) -> list[tuple[str, str]]:
    prefix = f"{title}\n" if title else ""
    if len(prefix) + overlap + 1 >= max_chars:
        raise ValueError("제목과 overlap이 최대 길이에 비해 너무 큼")
    pending = _units(body)
    if not pending:
        raise ValueError("제목만 있는 긴 구간은 자동 분할 불가")
    pieces, previous = [], ""
    while pending:
        repeated = previous[-overlap:] if previous and overlap else ""
        head = prefix + (f"{repeated}\n" if repeated else "")
        room, packed = max_chars - len(head), ""
        while pending:
            separator = "\n" if packed else ""
            if len(packed) + len(separator) + len(pending[0]) <= room:
                packed += separator + pending.pop(0)
            elif packed:
                break
            else:
                packed, remainder = _cut(pending.pop(0), room)
                if remainder:
                    pending.insert(0, remainder)
                break
        pieces.append((head + packed, packed))
        previous = repeated + ("\n" if repeated else "") + packed
    return pieces


def _table_parts(title: str, body: str, max_chars: int) -> list[tuple[str, dict]]:
    lines = body.splitlines()
    context = [line for line in lines if not line.lstrip().startswith("|")]
    prefix = "\n".join(item for item in [title, *context] if item.strip())
    results: list[tuple[str, dict]] = []
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        block = []
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            block.append(lines[index])
            index += 1
        if len(block) < 2 or not re.fullmatch(r"[\s|:\-]+", block[1]):
            raise ValueError("표 열 머리글과 구분선 확인 필요")
        attribute_table = bool(re.match(r"^\s*\|\s*항목\s*\|\s*(?:합성\s+)?조건\s*\|", block[0]))
        if attribute_table:
            text = "\n".join([prefix, *block]).strip()
            extra = _exception(text, max_chars)
            if extra:
                extra["exception_reason"] += "; 속성표 조건행 전체 보존"
            results.append((text, extra))
            continue
        current: list[str] = []
        for row in block[2:]:
            candidate = "\n".join([prefix, *block[:2], *current, row]).strip()
            if current and len(candidate) > max_chars:
                results.append(("\n".join([prefix, *block[:2], *current]).strip(), {}))
                current = []
            single = "\n".join([prefix, *block[:2], row]).strip()
            if len(single) > max_chars:
                results.append((single, _exception(single, max_chars)))
            else:
                current.append(row)
        if current:
            results.append(("\n".join([prefix, *block[:2], *current]).strip(), {}))
    return list(dict((text, (text, extra)) for text, extra in results).values())


def _exception(text: str, max_chars: int) -> dict:
    if len(text) <= max_chars:
        return {}
    return {
        "size_exception": True,
        "max_chars": max_chars,
        "token_check": "required",
        "exception_reason": f"단일 행과 필수 문맥 {len(text)}자가 max_chars={max_chars} 초과",
    }


def chunk_by_clause(text: str, metadata: dict, *, max_chars: int = 600, overlap: int = 80) -> list[Chunk]:
    _check_int("max_chars", max_chars, 1)
    _check_int("overlap", overlap, 0)
    if overlap >= max_chars:
        raise ValueError("overlap은 max_chars보다 작아야 함")
    if not text.strip():
        return []
    doc_key, chunks = _doc_key(metadata), []

    # prepare_units에서 조항(D1)이나 혜택(D2) 하나로 나눈 입력이므로 첫 줄만 제목으로 확인함.
    # 반환값은 (제목, 본문, 청크 구분 이름) 순서임.
    # D1 예: ("제1조(목적)", "① 이 약관은 ...", "제1조")
    # D2 예: ("## D2-C058-B04 | 반려생활 제휴", "| 항목 | 합성 조건 | ...", "D2-C058-B04 | 반려생활 제휴")
    title, body, label = _section(text)

    # (title, body)를 제목부터 차례대로 확인하고, if part로 빈 문자열을 제외한 뒤 "\n"으로 연결함.
    # 예: title="제1조(목적)", body="① 이 약관은 ..."이면 whole="제1조(목적)\n① 이 약관은 ..."가 됨.
    # 제목이 없는 일반 본문은 title이 빈 문자열이므로 body만 whole에 들어감.
    whole = "\n".join(
        part
        for part in (title, body)
        if part
    )
    extras: dict[str, dict] = {}
    if len(whole) <= max_chars:
        pieces = [(whole, "")]

    # 길이를 초과한 본문에 "|"로 시작하는 줄이 하나라도 있으면 마크다운 표가 포함된 것으로 판단함.
    # _table_parts는 표의 머리글을 유지하며 행을 나누고, 각 결과를 (분할한 글, 추가 메타데이터)로 반환함.
    # pieces에는 분할한 글을, extras에는 글별 크기 예외 등의 추가 메타데이터를 저장함.
    elif any(line.lstrip().startswith("|") for line in body.splitlines()):
        table_parts = _table_parts(title, body, max_chars)
        pieces = [(part, "") for part, _ in table_parts]
        extras = dict(table_parts)

    # 최대 길이를 초과했지만 표는 없는 일반 글이면 문장·항목 경계를 기준으로 여러 조각으로 나눔.
    # 각 조각에 title을 다시 붙이고, 다음 조각에는 앞 조각의 끝부분을 overlap 글자만큼 겹쳐 넣음.
    else:
        pieces = _split_prose(title, body, max_chars, overlap)

    active_item = ""

    for part, fresh in pieces:
        # 긴 조항이 여러 청크로 나뉘면 모두 같은 조 번호만 갖게 되므로, 각 청크가 어느 항인지 구분할 필요가 있음.
        # 아래에서 항목 표식을 찾아 section_label에 "제1항", "제2항"처럼 붙일 수 있도록 위치와 항 번호를 준비함.
        # 현재 조각에서 "(1)"과 "①" 같은 항목 표식을 찾아 (글 안의 위치, 항 번호)로 저장함.
        # 동그라미 숫자는 ①의 유니코드 번호를 기준으로 빼서 "①" -> "1", "②" -> "2"로 바꿈.
        numbered_markers = [
            (match.start(), match.group("no"))
            for match in ITEM_RE.finditer(fresh)
        ]
        circled_markers = [
            (
                match.start(),
                str(ord(match.group("symbol")) - ord("①") + 1),
            )
            for match in CIRCLED_RE.finditer(fresh)
        ]

        # 두 종류의 항목 표식을 합친 뒤 본문에 나타난 위치가 빠른 순서로 정렬함.
        markers = sorted(numbered_markers + circled_markers)
        item = f" 제{markers[0][1]}항" if markers and markers[0][0] == 0 else active_item
        section_label = label + (item if len(pieces) > 1 else "")
        location_metadata = {
            **extras.get(part, {}),
            "section_label": section_label,
        }
        # clause_no는 약관의 조·항 위치라는 의미로만 유지함.
        # 혜택 문서는 공통 표시 위치인 section_label만 저장함.
        if doc_key == "D1":
            location_metadata["clause_no"] = section_label
        output_metadata = (
            metadata
            if doc_key == "D1"
            else {key: value for key, value in metadata.items() if key != "clause_no"}
        )
        chunks.append(_make(part, output_metadata, doc_key, len(chunks), **location_metadata))
        if markers:
            active_item = f" 제{markers[-1][1]}항"

    return chunks


def chunk_by_turn(text: str, metadata: dict, *, turns_per_chunk: int = 4, overlap_turns: int = 1) -> list[Chunk]:
    _check_int("turns_per_chunk", turns_per_chunk, 1)
    _check_int("overlap_turns", overlap_turns, 0)
    if overlap_turns >= turns_per_chunk:
        raise ValueError("overlap_turns는 turns_per_chunk보다 작아야 함")
    if not text.strip():
        return []
    if not metadata.get("record_id"):
        raise ValueError("D3 metadata에 record_id가 필요함")
    matches = list(TURN_RE.finditer(text))
    if not matches or text[:matches[0].start()].strip():
        raise ValueError("상담 본문은 상담사: 또는 고객:으로 시작해야 함")
    utterances: list[list[str]] = []

    # 찾은 화자 표시를 순서대로 돌면서 각 발화를 [화자, 내용] 형태로 만들고 utterances에 저장함.
    # 같은 화자가 연속해서 말한 부분은 하나의 발화로 합치고, 화자가 바뀌면 새 발화를 추가함.
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        # 현재 "고객:" 또는 "상담사:"에서 화자 이름을 얻고, 다음 화자 표시 전까지의 발화 내용을 잘라냄.
        speaker, words = match.group(1), text[match.end():end].strip()  # match.end(): 현재 화자 표시가 끝난 위치

        if utterances and utterances[-1][0] == speaker:  # 기존 발화가 있고, 직전 화자와 현재 화자가 같은 경우
            utterances[-1][1] += "\n" + words
        else:
            utterances.append([speaker, words])

    # 정리한 발화를 앞에서부터 2개씩 묶어 하나의 대화 턴으로 만듦.
    # 예: [고객 발화, 상담사 발화, 고객 발화, 상담사 발화]는 대화 턴 2개가 됨.
    turns = []
    for index in range(0, len(utterances), 2):  # 0부터 발화 개수 전까지 2씩 증가함. 예: 0, 2, 4, ...
        utterance_pair = utterances[index:index + 2]
        turn_lines = []
        for speaker, words in utterance_pair:
            turn_lines.append(f"{speaker}: {words}")
        turns.append("\n".join(turn_lines))

    # 만든 대화 턴을 turns_per_chunk개씩 잘라 D3 청크로 저장함.
    # 마지막에 1~2턴만 남으면 너무 작은 청크를 만들지 않고 현재 청크에 포함함.
    # 다음 청크는 overlap_turns만큼 앞쪽 턴을 다시 포함하는 위치에서 시작함.
    chunks, start = [], 0
    while start < len(turns):
        end = min(start + turns_per_chunk, len(turns))
        if 0 < len(turns) - end <= 2:
            end = len(turns)
        chunks.append(
            _make(
                "\n".join(turns[start:end]),
                metadata,
                "D3",
                len(chunks),
                turn_range=f"{start + 1}-{end}",
            )
        )
        if end == len(turns):
            break
        start = end - overlap_turns
    return chunks


def enforce_token_limit(chunk: Chunk, counter: Callable[[str], int], max_tokens: int) -> list[Chunk]:
    _check_int("max_tokens", max_tokens, 1)
    token_count = counter(chunk.text)
    _check_int("counter 반환값", token_count, 0)
    if token_count > max_tokens:
        raise ValueError("검토 필요: 실제 토큰 한도 초과")
    metadata = {**chunk.metadata, "token_check": "passed", "token_count": token_count, "token_limit": max_tokens}
    return [Chunk(chunk.text, chunk.chunk_id, metadata)]


def assign_storage_ids(chunks: list[Chunk]) -> list[Document]:
    """한 지점에서 정본 ID를 검증하여 Document.id와 metadata에 함께 기록함."""

    seen: set[str] = set()
    documents: list[Document] = []
    for chunk in chunks:
        if chunk.chunk_id in seen:
            raise ChunkIntegrityError(f"중복 chunk_id: {chunk.chunk_id}")
        if chunk.metadata.get("char_len") != len(chunk.text):
            raise ChunkIntegrityError(f"char_len 불일치: {chunk.chunk_id}")
        seen.add(chunk.chunk_id)
        documents.append(chunk.to_document())
    return documents


# 정규식 풀이: ^는 각 줄의 시작(re.M), 제\s*\d+조는 "제 10조" 같은 조 번호를 찾음.
# (?:의\d+)?는 선택 사항이라 "용어의 정리"나 '목적' 모두 찾음.
# \s*\(는 제목 앞의 여는 괄호를 찾음.
# [^\n]+는 줄 끝까지 제목을 읽음. 예: "제 10조의2 (우대 조건)" 전체가 하나의 조항 시작으로 일치함.
CLAUSE_UNIT_RE = re.compile(r"^제\s*\d+조(?:의\d+)?\s*\([^\n]+", re.M)
BENEFIT_RE = re.compile(r"^D2-C\d{3}-B\d+\s*\|", re.M)


def prepare_units(documents: list[Document]) -> tuple[list[dict], list[dict]]:
    """페이지 문서를 D1 조항·D2 혜택·D3 상담 단위로 연결함."""

    units, skipped = [], []
    groups: dict[str, list[Document]] = defaultdict(list)
    for document in documents:
        groups[str(document.metadata.get("source", ""))].append(document)
    for source, source_documents in sorted(groups.items()):
        kind = source_documents[0].metadata.get("doc_type")
        if kind == "consult_log":
            units.extend({"text": item.page_content, "meta": {**item.metadata, "doc_key": "D3"}, "key": "D3"} for item in source_documents)
            continue
        source_documents.sort(key=lambda item: item.metadata["page"])

        if kind == "regulation":
            active = None
            footnotes = []

            # "각주와 출처" 페이지에서 *, ** 같은 각주 표시와 출처 문장·페이지 번호를 모음.
            # 나중에 조항 청크의 footnote_page 메타데이터에도 각주와 출처값을 붙이는 데 사용함
            for document in source_documents:
                if document.page_content.startswith("각주와 출처"):
                    for line in document.page_content.splitlines():
                        if match := re.match(r"^(\*+)\s+(.+)", line):
                            # match.group(1): 각주 표시. 예: "**"
                            # line: 출처 문장이 담긴 줄 전체. 예: "** 금융소비자보호법 제19조"
                            # document.metadata["page"]: 출처가 나온 PDF 쪽수. 예: 12
                            # 따라서 footnotes에는 ("**", "** 금융소비자보호법 제19조", 12)처럼 저장됨.
                            footnotes.append((match.group(1), line, document.metadata["page"]))


            for document in source_documents:
                metadata, body = dict(document.metadata), document.page_content
                # 타이틀 페이지, 문서 기본 정보, 각주와 출처 페이지는 청킹에서 제외함.
                if metadata.get("section_kind") == "contents" or body.startswith(("한빛카드\n", "문서 메타데이터", "각주와 출처")):
                    skipped.append({"source": source, "page": metadata["page"], "reason": "표지·메타정보·목차·출처 페이지"})
                    continue

                # '장' 찾기
                body = re.sub(r"^제\d+장[^\n]*\n?", "", body, flags=re.M)

                # 예시에서 "제1조(목적)", "제2조(용어의 정의)"가 시작하는 위치를 모두 찾음.
                matches = list(CLAUSE_UNIT_RE.finditer(body))
                # 첫 조항 앞의 글을 분리함. 예시의 "제1장 총칙"은 위에서 지워져 보통 빈 문자열이 됨.
                prefix = body[:matches[0].start()] if matches else body
                # 앞 페이지에서 이어진 조항 본문이 prefix에 남아 있으면 이전 조항에 이어 붙임.
                if prefix.strip():
                    # 이어 붙일 이전 조항이 없으면 조항 제목 없는 본문이라 처리할 수 없어 중단함.
                    if active is None:
                        raise ValueError(f"{source} p{metadata['page']}: 연결할 조항 없는 본문")
                    # 예: 제1조의 ②항이 다음 페이지에서 시작하면 이전 제1조 청크 뒤에 추가함.
                    active["text"] += "\n" + prefix.strip()
                    # 조항이 이어진 마지막 페이지 번호로 page_end를 갱신함.
                    active["meta"]["page_end"] = metadata["page"]

                # 찾은 조항을 순서대로 처리함. 예시에서는 index=0이 제1조, index=1이 제2조임.
                for index, match in enumerate(matches):
                    # 다음 조항 시작 전까지 자름. 마지막 조항은 문서 끝(len(body))까지 자름.
                    end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
                    # 예: 제1조 청크에는 제1조 제목·①항·②항만 담고, 제2조부터는 다음 반복에서 처리함.
                    active = {
                        "text": body[match.start():end].strip(),
                        # 원래 페이지 정보에 D1 문서 표시와 조항이 끝나는 페이지 번호를 더함.
                        "meta": {**metadata, "doc_key": "D1", "page_end": metadata["page"]},
                        # "key": "D1"은 이후 청킹 규칙에서 약관 문서 방식으로 처리할 분류 표시임.
                        "key": "D1",
                    }
                    # 완성한 제1조·제2조 청크를 검색용 단위 목록에 추가함.
                    units.append(active)

            # "각주와 출처"을 해당 문서조각에 추가하고 각주와 출처 페이지 번호도 추가함
            for unit in [item for item in units if item["meta"].get("source") == source]:
                for marker, note, page in footnotes:
                    if re.search(r"(?<!\*)" + re.escape(marker) + r"(?!\*)", unit["text"]):
                        unit["text"] += "\n" + note
                        unit["meta"]["footnote_page"] = page
            continue

        ###### ======== 카드 혜택 문서 ===========
        card_names = {}
        for document in source_documents:
            # re.match는 document.page_content의 맨 처음부터 이 형식과 맞는지 확인함.
            # 정규식 풀이: (D2-C\d{3})은 카드 ID를, \n은 바로 다음 줄을, ([^\n]+)는 카드 이름을 찾음.
            # D2-C: 글자 "D2-C"와 정확히 일치함. \d{3}: 숫자 3자리와 일치함. 예: 058.
            # [^\n]+: 줄바꿈(\n)이 아닌 글자가 1개 이상이라는 뜻으로, 한 줄 전체 이름을 가져옴.
            # 예: 첫 줄이 "D2-C058", 다음 줄이 "반려생활 카드"라면 group(1)은 "D2-C058", group(2)는 "반려생활 카드"가 됨.
            # 이미지의 "D2-C058-B04 | 반려생활 제휴"는 058 뒤에 "-B04"가 있어 이 정규식에는 맞지 않음.
            # 그 줄은 아래의 BENEFIT_RE가 혜택 단위로 따로 찾음.
            match = re.match(r"(D2-C\d{3})\n([^\n]+)", document.page_content)
            if match:
                card_names[match.group(1)] = match.group(2)

        for document in source_documents:
            metadata, body = dict(document.metadata), document.page_content
            if body.startswith(("SYNTHETIC DATA", "카드 찾아보기", "원문 참고", "참고 자료")):
                skipped.append({"source": source, "page": metadata["page"], "reason": "표지·목차·참고 목록"})
                continue
            if body.startswith("문서 적용 기준"):
                units.append({"text": "## " + body, "meta": {**metadata, "doc_key": "D2"}, "key": "D2"})
                continue
            matches = list(BENEFIT_RE.finditer(body))
            prefix = body[:matches[0].start()] if matches else body
            if prefix.strip():
                card = re.match(r"(D2-C\d{3})\n([^\n]+)\n(.*)", prefix, re.S)
                if card:
                    title = f"## {card.group(1)} {card.group(2)} · 연회비"
                    content = card.group(3).replace("연회비\n", "", 1)
                    first, _, content = content.partition("\n")
                    units.append({
                        "text": title + "\n" + first.replace(" | ", " · ") + "\n" + content,
                        "meta": {**metadata, "doc_key": "D2", "card_id": card.group(1), "card_name": card.group(2)},
                        "key": "D2",
                    })
                elif "참고 카드:" in prefix:
                    skipped.append({"source": source, "page": metadata["page"], "reason": "카드/혜택 경계 없는 참고 본문"})
                elif units and units[-1]["meta"].get("source") == source:
                    units[-1]["text"] += "\n" + prefix.strip()
                    units[-1]["meta"]["page_end"] = metadata["page"]
                else:
                    raise ValueError(f"{source} p{metadata['page']}: 연결할 카드/혜택 없는 본문")

            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
                heading, _, content = body[match.start():end].strip().partition("\n")
                card_id = heading.split("-B", 1)[0]
                if card_id not in card_names:
                    raise ValueError(f"카드명 연결 실패: {heading}")
                units.append({
                    "text": f"## {card_names[card_id]} · {heading.replace(' | ', ' · ')}\n{content}",
                    "meta": {**metadata, "doc_key": "D2", "card_id": card_id, "card_name": card_names[card_id]},
                    "key": "D2",
                })

    return units, skipped


def chunk_units(
    units: list[dict],
    *,
    doc: str = "all",
    max_chars: int = 600,
    overlap: int = 80,
    d2_overlap: int = 0,
    turns_per_chunk: int = 4,
    overlap_turns: int = 1,
    token_counter: Callable[[str], int] | None = None,
    max_tokens: int = 8192,
) -> tuple[list[Chunk], list[dict]]:
    """준비 단위를 청킹하고 최종 ID 부여 전의 Chunk 객체와 검토 목록을 반환함."""

    chunks, reviews = [], []
    for unit in units:
        if doc != "all" and unit["key"] != doc:
            continue
        try:
            if unit["key"] == "D3":
                created = chunk_by_turn(unit["text"], unit["meta"], turns_per_chunk=turns_per_chunk, overlap_turns=overlap_turns)
            else:
                created = chunk_by_clause(unit["text"], unit["meta"], max_chars=max_chars, overlap=d2_overlap if unit["key"] == "D2" else overlap)

            # 방금 만든 청크를 하나씩 확인하여 토큰 검사와 결과 저장을 차례대로 수행함.
            # token_counter가 있으면 토큰 수를 검사하고, 없으면 검사 없이 원래 청크를 그대로 사용함.
            # size_exception은 메타데이터에 유지하며, 최종 ID가 정해진 뒤 _run_chunk에서 예외 목록으로 만듦.
            for chunk in created:
                checked = enforce_token_limit(chunk, token_counter, max_tokens) if token_counter else [chunk]
                for item in checked:
                    chunks.append(item)
        except ValueError as error:
            reviews.append({"source": unit["meta"].get("source"), "reason": str(error)})

    # ID는 아직 입력 단위 안에서 만든 초기값이며, 전체 청크가 모이는 _run_chunk에서 고유 ID로 다시 부여함.
    return chunks, reviews
