"""문서 유형별 원본 문서와 사람이 찾을 수 있는 원문 위치를 만듦."""

import re

DOC_NAMES = {
    "D1_개인회원표준약관_합성.pdf": "개인회원표준약관",
    "D2_카드혜택안내_합성.pdf": "카드혜택안내",
}

PARAGRAPH_MARKS = {
    mark: index for index, mark in enumerate("①②③④⑤⑥⑦⑧⑨⑩", start=1)
}
PARAGRAPH_PATTERN = re.compile(f"([{' '.join(PARAGRAPH_MARKS).replace(' ', '')}])")
ARTICLE_PATTERN = re.compile(r"제\d+조(?:의\d+)?")
BENEFIT_CODE_PATTERN = re.compile(r"^D2-C\d+\s*")


def source_record(metadata: dict) -> dict:
    """출처 칸에 넣을 원본 파일과 개정 정보를 구조화함."""
    source = metadata.get("source")
    if not source:
        raise ValueError("출처 메타데이터에 source가 필요함")
    record = {"file": source}
    if metadata.get("version"):
        record["version"] = str(metadata["version"])
    if metadata.get("effective_date"):
        record["effective_date"] = str(metadata["effective_date"])
    if metadata.get("doc_type") == "consult_log" and metadata.get("consult_date"):
        record["consult_date"] = str(metadata["consult_date"])
    return record


def format_source(metadata: dict) -> str:
    """원본 파일명과 검증에 필요한 개정 정보를 한 줄로 표시함."""
    record = source_record(metadata)
    parts = [record["file"]]
    if record.get("version"):
        version = record["version"]
        parts.append(version if version.lower().startswith("v") else f"v{version}")
    if record.get("effective_date"):
        parts.append(f"시행일 {record['effective_date']}")
    if record.get("consult_date"):
        parts.append(f"상담일 {record['consult_date']}")
    return " · ".join(parts)


def _compact(text: str) -> str:
    """PDF 줄바꿈과 화면 줄바꿈 차이를 제거해 발췌문을 대조함."""
    return re.sub(r"\s+", "", text or "")


def quote_is_in_text(quote: str, text: str) -> bool:
    """발췌문이 청크의 연속 원문인지 공백 차이를 무시하고 확인함."""
    compact_quote = _compact(quote.strip().strip('“”"'))
    return bool(compact_quote) and compact_quote in _compact(text)


def _regulation_location(metadata: dict, text: str, quote: str) -> tuple[str, bool]:
    source = metadata.get("source", "")
    name = DOC_NAMES.get(source, source or "문서명 미표기")
    article_match = ARTICLE_PATTERN.search(text)
    article = article_match.group(0) if article_match else ""
    matches = list(PARAGRAPH_PATTERN.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        paragraph_text = text[match.start():end]
        if quote_is_in_text(quote, paragraph_text):
            number = PARAGRAPH_MARKS[match.group(1)]
            return f"{name} {article} 제{number}항".strip(), True
    fallback = article or str(metadata.get("clause_no") or "위치 미표기")
    return f"{name} {fallback}".strip(), False


def _consult_location(metadata: dict, text: str, quote: str) -> tuple[str, bool]:
    """상담 청크의 대화쌍을 세어 발췌문이 속한 정확한 턴을 찾음."""
    record_id = metadata.get("record_id") or "기록번호 미표기"
    turn_range = str(metadata.get("turn_range") or "범위 미표기")
    quote_ok = quote_is_in_text(quote, text)
    start_match = re.match(r"(\d+)", turn_range)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if quote_ok and start_match and any(line.startswith(("고객:", "상담사:")) for line in lines):
        start_turn = int(start_match.group(1))
        turns = ["\n".join(lines[index:index + 2]) for index in range(0, len(lines), 2)]
        compact_quote = _compact(quote.strip().strip('“”"'))
        for span in range(1, len(turns) + 1):
            for first in range(0, len(turns) - span + 1):
                last = first + span - 1
                combined = "".join(_compact(turn) for turn in turns[first:last + 1])
                if compact_quote in combined:
                    first_turn, last_turn = start_turn + first, start_turn + last
                    turn = str(first_turn) if first_turn == last_turn else f"{first_turn}-{last_turn}"
                    return f"상담 {record_id} > 턴 {turn}", True
    return f"상담 {record_id} > 턴 {turn_range}", quote_ok


def format_location(metadata: dict, text: str, quote: str) -> tuple[str, bool]:
    """약관 조항·혜택 항목·상담 구간 중 알맞은 원문 위치를 반환함."""
    doc_type = metadata.get("doc_type")
    if doc_type == "regulation":
        return _regulation_location(metadata, text, quote)
    if doc_type == "benefit_guide":
        clause = str(metadata.get("clause_no") or "").strip()
        clause = BENEFIT_CODE_PATTERN.sub("", clause).replace(" · ", " > ")
        if not clause:
            clause = str(metadata.get("card_name") or "항목 미표기")
        return clause, quote_is_in_text(quote, text)
    if doc_type == "consult_log":
        return _consult_location(metadata, text, quote)
    return str(metadata.get("clause_no") or "위치 미표기"), quote_is_in_text(quote, text)
