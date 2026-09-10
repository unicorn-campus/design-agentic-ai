"""교재 슬라이드 17~26의 4단계 청킹 구현. 외부 라이브러리 불필요.

글자 수는 Python len() 기준이며 모델 토큰 수와 다름.
단일 표 행+필수 문맥의 글자 상한 예외는 후보로 반환하고 실제 토큰 검사를 별도로 요구함.
"""

from copy import deepcopy
from dataclasses import dataclass
import re


CLAUSE_RE = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+)?(?P<no>제\d+조(?:의\d+)?)(?!\d)", re.M)
# 교재의 ^[(1)-(20)]는 문자 집합이므로 (10) 같은 항 번호를 인식하지 못함.
ITEM_RE = re.compile(r"^[ \t]*\((?P<no>[1-9]\d*)\)", re.M)
CIRCLED_ITEM_RE = re.compile(r"^[ \t]*(?P<symbol>[①-⑳])", re.M)
TURN_RE = re.compile(r"^[ \t]*(상담사|고객)[ \t]*[:：][ \t]*", re.M)
HEADING_RE = re.compile(r"^##[ \t]+.+$", re.M)


@dataclass
class Chunk:
    text: str
    chunk_id: str
    metadata: dict


def make_chunk(text, meta, doc_key, idx, **extra) -> Chunk:
    """원본 꼬리표를 복사하고, 계산한 길이와 문서 전체 인덱스를 부착."""
    md = {**deepcopy(meta), **extra, "chunk_index": idx, "char_len": len(text)}
    return Chunk(text, f"{doc_key}_{idx:04d}", md)


def _check_int(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name}은 {minimum} 이상의 정수여야 합니다.")


def _doc_key(meta):
    if meta.get("doc_key"):
        return str(meta["doc_key"])
    source = str(meta.get("source", "")).replace("\\", "/").rsplit("/", 1)[-1]
    match = re.match(r"(D[12])(?:_|\.|$)", source)
    if match:
        return match.group(1)
    raise ValueError("meta에 doc_key 또는 D1_/D2_로 시작하는 source가 필요합니다.")


def _sections(text):
    """조 경계 우선, 조가 없는 혜택 안내는 ## 제목 경계 사용."""
    matches = list(CLAUSE_RE.finditer(text))
    if not matches:
        matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [("", text.strip(), "본문")]
    result = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[match.start():end].strip()
        title, _, body = section.partition("\n")
        no_match = CLAUSE_RE.match(title)
        label = no_match.group("no") if no_match else title.removeprefix("## ").strip()
        result.append((title, body.strip(), label))
    # 첫 경계 앞 표지·목차는 제외. 본문형 조 제목을 가진 목차는 입력 정제가 필요함.
    return result


def _units(body):
    starts = [m.start() for pattern in (ITEM_RE, CIRCLED_ITEM_RE) for m in pattern.finditer(body)]
    starts = sorted(set([0, *starts, len(body)]))
    return [body[a:b].strip() for a, b in zip(starts, starts[1:]) if body[a:b].strip()]


def _cut(text, capacity):
    """항을 우선 유지하고, 긴 항은 문장/줄 경계, 마지막으로 글자 경계에서 분할."""
    if len(text) <= capacity:
        return text, ""
    candidates = [m.end() for m in re.finditer(r"[.!?。](?:\s+|$)|\n+", text[:capacity])]
    stop = candidates[-1] if candidates else capacity
    return text[:stop].rstrip(), text[stop:].lstrip()


def _split_prose(title, body, max_chars, overlap):
    prefix = title + "\n" if title else ""
    if len(prefix) + overlap + 1 >= max_chars:
        raise ValueError("제목과 overlap이 너무 깁니다. max_chars를 늘리거나 overlap을 줄이세요.")
    pending = _units(body)
    if not pending:
        raise ValueError("제목만으로 max_chars를 초과합니다. 제목 또는 최대 길이를 검토하세요.")
    pieces = []
    previous = ""
    while pending:
        # (3) 중첩: 같은 조 내부에만 직전 본문 끝을 반복. 제목도 길이 예산에 포함.
        repeated = previous[-overlap:] if previous and overlap else ""
        head = prefix + (repeated + "\n" if repeated else "")
        room = max_chars - len(head)
        packed = ""
        while pending:
            separator = "\n" if packed else ""
            if len(packed) + len(separator) + len(pending[0]) <= room:
                packed += separator + pending.pop(0)
                continue
            if packed:
                break
            packed, remainder = _cut(pending.pop(0), room)
            if remainder:
                pending.insert(0, remainder)
            break
        pieces.append((head + packed, packed))
        previous = repeated + ("\n" if repeated else "") + packed
    return pieces


def _table_parts(title, body):
    """비표 문장은 관련 조건·각주로 반복하며 각 표의 머리글과 행을 구분함."""
    lines = body.splitlines()
    context = [line for line in lines if not line.lstrip().startswith("|")]
    tables = []
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        block = []
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            block.append(lines[i])
            i += 1
        if len(block) < 2 or not re.fullmatch(r"[\s|:\-]+", block[1]):
            raise ValueError("검토 필요: 표 열 머리글/구분선을 확인하세요.")
        tables.append(block)
    prefix = "\n".join([x for x in [title, *context] if x.strip()])
    return prefix, tables


def _attribute_table(block):
    """D2 한 혜택의 속성행은 서로 독립적인 상품 행이 아님."""
    return bool(re.match(r"^\s*\|\s*항목\s*\|\s*(?:합성\s+)?조건\s*\|", block[0]))


def _table_text(prefix, block, rows):
    return "\n".join(x for x in [prefix, *block[:2], *rows] if x)


def _exception_metadata(text, max_chars):
    if len(text) <= max_chars:
        return {}
    return {"size_exception": True, "max_chars": max_chars, "token_check": "required",
            "exception_reason": f"단일 행과 필수 문맥 {len(text)}자가 max_chars={max_chars} 초과"}


def _split_table(title, body, max_chars):
    """행 묶음 분할. 단일 행+필수 문맥 초과만 토큰 검사 전 예외 후보로 반환함."""
    prefix, tables = _table_parts(title, body)
    output = []
    for block in tables:
        if _attribute_table(block):
            # 각 주행의 나머지 속성행 전부가 필수 조건임. 따라서 재조립 결과는 동일함.
            # 동일 후보를 행 수만큼 만들지 않고 1개로 합침(조건행 누락 방지).
            text = _table_text(prefix, block, block[2:])
            extra = _exception_metadata(text, max_chars)
            if extra:
                extra["exception_reason"] += "; 속성표의 다른 모든 행을 관련 조건으로 반복"
            output.append((text, extra))
            continue
        current = []
        for row in block[2:]:
            combined = _table_text(prefix, block, [*current, row])
            if current and len(combined) > max_chars:
                output.append((_table_text(prefix, block, current), {}))
                current = []
            single = _table_text(prefix, block, [row])
            if len(single) > max_chars:
                output.append((single, _exception_metadata(single, max_chars)))
            else:
                current.append(row)
        if current:
            output.append((_table_text(prefix, block, current), {}))
        elif len(block) == 2:
            text = _table_text(prefix, block, [])
            if len(text) > max_chars:
                raise ValueError("검토 필요: 데이터 행 없는 표의 문맥이 max_chars를 초과합니다.")
            output.append((text, {}))
    # 완전히 같은 표 후보만 제거함. 문서의 다른 조각/다른 출처는 건드리지 않음.
    seen = set()
    unique = []
    for text, extra in output:
        if text not in seen:
            unique.append((text, extra))
            seen.add(text)
    return unique


def _cell_parts(row):
    # 이스케이프한 \|는 셀 구분자로 취급하지 않음.
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", row.strip().strip("|"))]


def enforce_token_limit(chunk: Chunk, counter, max_tokens: int) -> list[Chunk]:
    """실제 모델 counter(text)로 검사. 긴 셀은 문장 단위로 재분할 후 다시 검사함.

    counter는 인코딩·모델 입력 접두어·특수 토큰을 포함하는 실제 토큰 계산 함수여야 함.
    모델은 이 함수가 선택하지 않음. 뜻을 보존할 수 없는 조건행/긴 문장은 ValueError로 보류함.
    """
    _check_int("max_tokens", max_tokens, 1)
    if not callable(counter):
        raise ValueError("counter는 실제 모델 토큰 수를 반환하는 함수여야 합니다.")

    def count(text):
        tokens = counter(text)
        _check_int("counter 반환값", tokens, 0)
        return tokens

    def checked(text, index=None):
        md = deepcopy(chunk.metadata)
        md.update(token_check="passed", token_count=count(text), token_limit=max_tokens, char_len=len(text))
        if md["token_count"] > max_tokens:
            raise ValueError("검토 필요: 분할 뒤에도 실제 토큰 한도를 초과합니다.")
        if index is not None:
            md.update(parent_chunk_id=chunk.chunk_id, token_part_index=index)
            if "max_chars" in md:
                md["size_exception"] = len(text) > md["max_chars"]
                if not md["size_exception"]:
                    md.pop("exception_reason", None)
                else:
                    md["exception_reason"] = (
                        f"문장 분할 후 단일 행과 필수 문맥 {len(text)}자가 max_chars={md['max_chars']} 초과"
                    )
        return Chunk(text, chunk.chunk_id if index is None else f"{chunk.chunk_id}_part{index:04d}", md)

    if count(chunk.text) <= max_tokens:
        return [checked(chunk.text)]
    prefix, tables = _table_parts("", chunk.text)
    if not tables:
        raise ValueError("검토 필요: 토큰 한도를 넘는 일반 본문은 경계·크기를 다시 설계하세요.")

    def split_cell(block, row, other_rows):
        cells = _cell_parts(row)
        if len(cells) < 2:
            raise ValueError("검토 필요: 표의 항목명과 셀 구분을 확인하세요.")
        if _attribute_table(block) and re.search(r"조건|실적|한도|제외|대상|횟수|취소", cells[0]):
            raise ValueError("검토 필요: 필수 조건행은 의미를 확인하지 않고 문장별로 분리할 수 없습니다.")
        column = max(range(1, len(cells)), key=lambda j: len(cells[j]))
        sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+", cells[column]) if s.strip()]
        if len(sentences) < 2:
            raise ValueError("검토 필요: 긴 셀에 안전한 문장 경계가 없습니다.")

        def render(fragment):
            partial = cells.copy()
            partial[column] = fragment
            new_row = "| " + " | ".join(partial) + " |"
            # 같은 행의 항목명·다른 셀과 모든 관련 조건행을 반복함.
            return _table_text(prefix, block, [new_row, *other_rows])

        result, pending = [], ""
        for sentence in sentences:
            if count(render(sentence)) > max_tokens:
                raise ValueError("검토 필요: 단일 문장·항목명·관련 조건도 실제 토큰 한도를 초과합니다.")
            trial = (pending + " " + sentence).strip()
            if pending and count(render(trial)) > max_tokens:
                result.append(render(pending))
                pending = sentence
            else:
                pending = trial
        if pending:
            result.append(render(pending))
        return result

    output = []
    for block in tables:
        rows = block[2:]
        whole = _table_text(prefix, block, rows)
        if count(whole) <= max_tokens:
            output.append(whole)
        elif _attribute_table(block):
            # 모든 속성 조건을 유지한 채 가장 긴 설명 셀만 분할 시도함.
            candidates = [(i, row) for i, row in enumerate(rows)
                          if not re.search(r"조건|실적|한도|제외|대상|횟수|취소", _cell_parts(row)[0])]
            if not candidates:
                raise ValueError("검토 필요: 속성표 전체가 필수 조건이어서 토큰 한도 내 분리가 불가능합니다.")
            index, row = max(candidates, key=lambda pair: len(pair[1]))
            output.extend(split_cell(block, row, rows[:index] + rows[index + 1:]))
        else:
            for row in rows:
                single = _table_text(prefix, block, [row])
                output.extend([single] if count(single) <= max_tokens else split_cell(block, row, []))
    if not output:
        raise ValueError("검토 필요: 토큰 한도를 넘는 표에 분할할 데이터 행이 없습니다.")
    return [checked(text, i) for i, text in enumerate(dict.fromkeys(output))]


def chunk_by_clause(doc_text: str, meta: dict, max_chars: int = 600,
                    overlap: int = 80) -> list[Chunk]:
    """D1 조·항 또는 D2 ## 제목/표 단위로 분할. 빈 문서는 빈 목록 반환."""
    _check_int("max_chars", max_chars, 1)
    _check_int("overlap", overlap, 0)
    if overlap >= max_chars:
        raise ValueError("overlap은 max_chars보다 작아야 합니다.")
    if not doc_text.strip():
        return []
    doc_key = _doc_key(meta)
    chunks = []
    # (1) 경계 탐지: 조 하나를 후보 하나로 만들고 제목을 기억함.
    for title, body, label in _sections(doc_text):
        whole = "\n".join(x for x in (title, body) if x)
        table_metadata = {}
        # (2) 크기 제한·분할: 짧은 조는 보존, 긴 표는 행, 긴 조는 항부터 분할함.
        if len(whole) <= max_chars:
            parts = [(whole, "")]
        elif any(line.lstrip().startswith("|") for line in body.splitlines()):
            table_parts = _split_table(title, body, max_chars)
            parts = [(part, "") for part, extra in table_parts]
            table_metadata = dict(table_parts)
        else:
            parts = _split_prose(title, body, max_chars, overlap)
        # (4) 꼬리표·ID: 문서 전체에서 순번 증가. overlap의 항 번호는 출처에 섞지 않음.
        active_item = ""
        for text, fresh in parts:
            markers = sorted([(m.start(), m.group("no")) for m in ITEM_RE.finditer(fresh)] +
                             [(m.start(), str(ord(m.group("symbol")) - ord("①") + 1))
                              for m in CIRCLED_ITEM_RE.finditer(fresh)])
            first_item = f" 제{markers[0][1]}항" if markers and markers[0][0] == 0 else active_item
            clause_no = label + first_item if len(parts) > 1 else label
            chunks.append(make_chunk(text, meta, doc_key, len(chunks), clause_no=clause_no,
                                     **table_metadata.get(text, {})))
            if markers:
                active_item = f" 제{markers[-1][1]}항"
    return chunks


def chunk_by_turn(record_text: str, meta: dict, turns_per_chunk: int = 4,
                  overlap_turns: int = 1) -> list[Chunk]:
    """레코드 1건의 연속 같은 화자를 합친 뒤 두 마디를 한 턴으로 묶음."""
    _check_int("turns_per_chunk", turns_per_chunk, 1)
    _check_int("overlap_turns", overlap_turns, 0)
    if overlap_turns >= turns_per_chunk:
        raise ValueError("overlap_turns는 turns_per_chunk보다 작아야 합니다.")
    if not record_text.strip():
        return []
    if not meta.get("record_id"):
        raise ValueError("D3 꼬리표에 record_id가 필요합니다.")
    # (1) 경계 탐지: 화자 표시를 찾고 연속 같은 화자의 발화를 한 마디로 병합함.
    matches = list(TURN_RE.finditer(record_text))
    if not matches or record_text[:matches[0].start()].strip():
        raise ValueError("상담 본문은 '상담사:' 또는 '고객:'으로 시작해야 합니다.")
    utterances = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(record_text)
        speaker = match.group(1)
        content = record_text[match.end():end].strip()
        if utterances and utterances[-1][0] == speaker:
            utterances[-1][1] += "\n" + content
        else:
            utterances.append([speaker, content])
    turns = ["\n".join(f"{who}: {words}" for who, words in utterances[i:i + 2])
             for i in range(0, len(utterances), 2)]
    # (2) 묶기: 남은 새 턴이 1~2개면 지금 조각에 흡수. 홀수 마지막 마디도 보존함.
    chunks = []
    start = 0
    while start < len(turns):
        end = min(start + turns_per_chunk, len(turns))
        if 0 < len(turns) - end <= 2:
            end = len(turns)
        # (4) 꼬리표·ID: 레코드 키와 1부터 시작하는 턴 범위를 부착함.
        chunks.append(make_chunk("\n".join(turns[start:end]), meta, f"D3_{meta['record_id']}",
                                 len(chunks), turn_range=f"{start + 1}-{end}"))
        if end == len(turns):
            break
        # (3) 중첩: 다음 시작을 겹칠 턴 수만큼 뒤로 옮김. 레코드 경계는 넘지 않음.
        start = end - overlap_turns
    return chunks
