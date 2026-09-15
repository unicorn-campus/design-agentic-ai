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
HEADING_RE = re.compile(r"^##[ \t]+.+$", re.M)


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


def _sections(text: str) -> list[tuple[str, str, str]]:
    matches = list(CLAUSE_RE.finditer(text)) or list(HEADING_RE.finditer(text))
    if not matches:
        return [("", text.strip(), "본문")]
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title, _, body = text[match.start():end].strip().partition("\n")
        clause = CLAUSE_RE.match(title)
        label = clause.group("no") if clause else title.removeprefix("## ").strip()
        sections.append((title, body.strip(), label))
    return sections


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
    for title, body, label in _sections(text):
        whole = "\n".join(part for part in (title, body) if part)
        extras: dict[str, dict] = {}
        if len(whole) <= max_chars:
            pieces = [(whole, "")]
        elif any(line.lstrip().startswith("|") for line in body.splitlines()):
            table_parts = _table_parts(title, body, max_chars)
            pieces = [(part, "") for part, _ in table_parts]
            extras = dict(table_parts)
        else:
            pieces = _split_prose(title, body, max_chars, overlap)
        active_item = ""
        for part, fresh in pieces:
            markers = sorted(
                [(m.start(), m.group("no")) for m in ITEM_RE.finditer(fresh)]
                + [(m.start(), str(ord(m.group("symbol")) - ord("①") + 1)) for m in CIRCLED_RE.finditer(fresh)]
            )
            item = f" 제{markers[0][1]}항" if markers and markers[0][0] == 0 else active_item
            chunks.append(_make(part, metadata, doc_key, len(chunks), clause_no=label + (item if len(pieces) > 1 else ""), **extras.get(part, {})))
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
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        speaker, words = match.group(1), text[match.end():end].strip()
        if utterances and utterances[-1][0] == speaker:
            utterances[-1][1] += "\n" + words
        else:
            utterances.append([speaker, words])
    turns = ["\n".join(f"{speaker}: {words}" for speaker, words in utterances[i:i + 2]) for i in range(0, len(utterances), 2)]
    chunks, start = [], 0
    while start < len(turns):
        end = min(start + turns_per_chunk, len(turns))
        if 0 < len(turns) - end <= 2:
            end = len(turns)
        chunks.append(_make("\n".join(turns[start:end]), metadata, "D3", len(chunks), turn_range=f"{start + 1}-{end}"))
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


CLAUSE_UNIT_RE = re.compile(r"^제\s*\d+조(?:의\d+)?\s*\([^\n]+", re.M)
BENEFIT_RE = re.compile(r"^D2-C\d{3}-B\d+\s*\|", re.M)


def normalize_table(text: str) -> str:
    """D2 테두리 없는 표와 셀 줄바꿈을 Markdown 표로 정규화함."""

    output, in_table = [], False
    for line in text.splitlines():
        if "|" in line and not line.startswith("##"):
            cells = line.strip().strip("|").strip()
            output.append(f"| {cells} |")
            if not in_table:
                output.append("| " + " | ".join(["---"] * len(cells.split("|"))) + " |")
            in_table = True
        elif in_table and line and not re.match(r"^(모든 명칭|일반 혜택|가족카드:|카드별 명칭)", line):
            output[-1] = output[-1].rstrip("| ") + " " + line.strip() + " |"
        else:
            output.append(line)
            in_table = False
    return "\n".join(output)


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
            for document in source_documents:
                if document.page_content.startswith("각주와 출처"):
                    for line in document.page_content.splitlines():
                        if match := re.match(r"^(\*+)\s+(.+)", line):
                            footnotes.append((match.group(1), line, document.metadata["page"]))
            for document in source_documents:
                metadata, body = dict(document.metadata), document.page_content
                if metadata.get("section_kind") == "contents" or body.startswith(("한빛카드\n", "문서 메타데이터", "각주와 출처")):
                    skipped.append({"source": source, "page": metadata["page"], "reason": "표지·메타정보·목차·출처 페이지"})
                    continue
                body = re.sub(r"^제\d+장[^\n]*\n?", "", body, flags=re.M)
                matches = list(CLAUSE_UNIT_RE.finditer(body))
                prefix = body[:matches[0].start()] if matches else body
                if prefix.strip():
                    if active is None:
                        raise ValueError(f"{source} p{metadata['page']}: 연결할 조항 없는 본문")
                    active["text"] += "\n" + prefix.strip()
                    active["meta"]["page_end"] = metadata["page"]
                for index, match in enumerate(matches):
                    end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
                    active = {
                        "text": body[match.start():end].strip(),
                        "meta": {**metadata, "doc_key": "D1", "page_end": metadata["page"]},
                        "key": "D1",
                    }
                    units.append(active)
            for unit in [item for item in units if item["meta"].get("source") == source]:
                for marker, note, page in footnotes:
                    if re.search(r"(?<!\*)" + re.escape(marker) + r"(?!\*)", unit["text"]):
                        unit["text"] += "\n" + note
                        unit["meta"]["footnote_page"] = page
            continue
        card_names = {}
        for document in source_documents:
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
                        "text": title + "\n" + first.replace(" | ", " · ") + "\n" + normalize_table(content),
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
                    "text": f"## {card_names[card_id]} · {heading.replace(' | ', ' · ')}\n{normalize_table(content)}",
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
) -> tuple[list[Document], list[dict], list[dict]]:
    """준비 단위를 청킹하며 자동 분할 불가 항목만 reviews로 격리함."""

    chunks, reviews, exceptions = [], [], []
    for unit in units:
        if doc != "all" and unit["key"] != doc:
            continue
        try:
            if unit["key"] == "D3":
                created = chunk_by_turn(unit["text"], unit["meta"], turns_per_chunk=turns_per_chunk, overlap_turns=overlap_turns)
            else:
                created = chunk_by_clause(unit["text"], unit["meta"], max_chars=max_chars, overlap=d2_overlap if unit["key"] == "D2" else overlap)
            for chunk in created:
                checked = enforce_token_limit(chunk, token_counter, max_tokens) if token_counter else [chunk]
                for item in checked:
                    if item.metadata.get("size_exception"):
                        exceptions.append({"chunk_id": item.chunk_id, "reason": item.metadata.get("exception_reason")})
                    chunks.append(item)
        except ValueError as error:
            reviews.append({"source": unit["meta"].get("source"), "reason": str(error)})
    # 개별 입력 단위 안에서 임시로 만든 순번을 저장 직전에 문서별 전역 순번으로 재부여함.
    # D3는 서로 다른 상담 레코드의 0000이 충돌하지 않도록 record_id를 정본 ID에 유지함.
    counters = {"D1": 0, "D2": 0}
    reassigned = []
    for item in chunks:
        key = _doc_key(item.metadata)
        if key in counters:
            chunk_id = f"{key}_{counters[key]:04d}"
            counters[key] += 1
        else:
            chunk_id = f"D3_{item.metadata['record_id']}_{item.metadata['chunk_index']:04d}"
        reassigned.append(Chunk(item.text, chunk_id, item.metadata))
    exceptions = [
        {"chunk_id": item.chunk_id, "reason": item.metadata.get("exception_reason")}
        for item in reassigned
        if item.metadata.get("size_exception")
    ]
    return assign_storage_ids(reassigned), reviews, exceptions
