"""외부 파서와 무관하게 텍스트 정제·가명화·검색 메타데이터 규칙을 적용함."""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Iterable

from app.domain.models import LoadedDocument, RawChunk, TextSpan


_SPACE_BEFORE_NEWLINE = re.compile(r"[ \t]+\n")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")
# 알려진 형식의 잔존 검사로 로더의 위치 기반 치환을 보완함. 모든 종류의 개인정보를 탐지하는 규칙은 아님.
_RESIDUAL_PRIVATE = (
    re.compile(r"(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\d[ -]?){15}\d(?!\d)"),
    re.compile(r"\bM-\d{4,}\b", re.IGNORECASE),
)


def sha256_text(value: str) -> str:
    """문자열을 UTF-8로 고정하여 실행 환경과 무관한 본문 지문을 반환함."""
    return sha256(value.encode("utf-8")).hexdigest()


def stable_json_hash(value: dict[str, Any]) -> str:
    """키 삽입 순서와 공백 차이가 변경으로 잡히지 않도록 정렬한 JSON의 지문을 반환함."""
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(serialized)


def pseudonym(prefix: str, raw_value: str) -> str:
    """기존 인덱스와 고객 필터가 일치하도록 SHA-256 앞 16자리로 가명 ID를 만듦.

    인자: prefix는 회원·상담사 등의 구분값이며 원문 값은 그대로 해시하므로 호출자가 공백을 정리해야 함.
    반환값: 구분값과 지문을 밑줄로 연결한 값임. 비밀키를 사용하는 암호화나 익명성 보증은 아님.
    부수효과: 없음. 입력 원문을 저장하거나 로그에 남기지 않음.
    """

    return f"{prefix}_{sha256_text(raw_value)[:16]}"


def normalize_spans(spans: Iterable[TextSpan], text_length: int) -> tuple[TextSpan, ...]:
    """범위를 문서 안으로 제한하고 겹치거나 맞닿은 동일 처리 범위를 합침.

    인자: text_length는 원문의 문자 수이며 끝 위치는 포함하지 않음.
    반환값: 시작 순서로 정렬한 유효 구간임. 빈 구간은 제외하고 서로 다른 대체 값은 합치지 않음.
    """

    result: list[TextSpan] = []
    for span in sorted(spans, key=lambda item: (item.start, item.end)):
        start, end = max(0, span.start), min(text_length, span.end)
        if start >= end:
            continue
        current = TextSpan(start, end, span.value)
        if result and start <= result[-1].end and span.value == result[-1].value:
            previous = result[-1]
            result[-1] = TextSpan(previous.start, max(previous.end, end), previous.value)
        else:
            result.append(current)
    return tuple(result)


def clean_chunk_text(chunk: RawChunk) -> str:
    """원문 좌표를 기준으로 제외 구간을 지운 뒤 남은 개인정보 구간을 치환함.

    목적: 먼저 문자열을 삭제하여 좌표가 바뀌거나 개인정보가 청크 경계에서 나뉘어 남는 일을 방지함.
    방법: 원문에서 남길 구간을 정하고 각 구간과 겹치는 개인정보를 치환한 뒤 공백을 정리함.
    반환값: 저장 후보 문자열임. 내용이 모두 제거되면 빈 문자열이며 잔존 검사와 토큰 검사는 별도로 필요함.
    부수효과: 없음. 원문 객체와 구간 목록을 변경하지 않음.
    """

    pieces: list[str] = []
    for keep_start, keep_end in _kept_ranges(
        chunk.start, chunk.end, chunk.document.removal_spans
    ):
        pieces.append(
            _replace_private(
                chunk.document.text,
                keep_start,
                keep_end,
                chunk.document.privacy_spans,
            )
        )
    cleaned = "".join(pieces)
    cleaned = _SPACE_BEFORE_NEWLINE.sub("\n", cleaned)
    return _EXCESS_NEWLINES.sub("\n\n", cleaned).strip()


def _kept_ranges(start: int, end: int, removals: Iterable[TextSpan]) -> list[tuple[int, int]]:
    """원문 좌표를 바꾸지 않고 제거 대상 밖에 남은 반열린 문자 구간을 구함."""
    cursor = start
    kept: list[tuple[int, int]] = []
    for span in normalize_spans(removals, end):
        if span.end <= cursor or span.start >= end:
            continue
        cut_start, cut_end = max(start, span.start), min(end, span.end)
        if cursor < cut_start:
            kept.append((cursor, cut_start))
        cursor = max(cursor, cut_end)
    if cursor < end:
        kept.append((cursor, end))
    return kept


def _replace_private(
    source: str,
    start: int,
    end: int,
    privacy_spans: Iterable[TextSpan],
) -> str:
    """청크 안에 들어온 개인정보의 일부만 있더라도 겹치는 부분 전체를 대체함."""
    cursor = start
    output: list[str] = []
    for span in normalize_spans(privacy_spans, len(source)):
        if span.end <= cursor or span.start >= end:
            continue
        private_start, private_end = max(start, span.start), min(end, span.end)
        if cursor < private_start:
            output.append(source[cursor:private_start])
        output.append(str(span.value or "[삭제]"))
        cursor = max(cursor, private_end)
    output.append(source[cursor:end])
    return "".join(output)


def chunk_metadata(document: LoadedDocument, start: int, end: int) -> dict[str, Any]:
    """원문 구간과 겹치는 페이지·업무 문맥을 검색 메타데이터로 변환함.

    방법: 겹치는 페이지와 문맥을 모으고, 문맥이 없으면 시작 위치 이전의 마지막 문맥을 사용함.
    반환값: 문서 메타데이터를 복사해 보강한 값임. 여러 문맥이 있으면 대표값과 전체값을 함께 보관함.
    부수효과: 없음. 전달받은 문서의 메타데이터는 변경하지 않음.
    """

    metadata = dict(document.metadata)
    metadata.update({"source": document.source, "doc_key": document.doc_key})

    pages = [span.value for span in document.page_spans if _intersects(span, start, end)]
    if pages:
        metadata["page"] = min(pages)
        metadata["page_end"] = max(pages)

    contexts = [span.value for span in document.context_spans if _intersects(span, start, end)]
    if not contexts:
        preceding = [span.value for span in document.context_spans if span.start <= start]
        contexts = preceding[-1:] if preceding else []
    mappings = [value for value in contexts if isinstance(value, dict)]
    _merge_contexts(metadata, mappings)
    return metadata


def _merge_contexts(metadata: dict[str, Any], contexts: list[dict[str, Any]]) -> None:
    """입력 메타데이터를 갱신하되 여러 조항·상품에 걸친 청크임을 전체값과 모호성 표시로 남김."""
    if not contexts:
        return
    keys = {key for context in contexts for key in context}
    for key in keys:
        values = list(dict.fromkeys(context[key] for context in contexts if context.get(key)))
        if not values:
            continue
        metadata[key] = values[0]
        if len(values) > 1:
            metadata[f"{key}_all"] = json.dumps(values, ensure_ascii=False)
            metadata["context_ambiguous"] = True


def assert_no_residual_private(text: str) -> None:
    """알려진 개인정보 형식이 남아 있으면 저장을 막기 위해 ValueError를 발생시킴.

    인자: 정제된 본문이나 검사할 메타데이터 문자열임.
    반환값: 검사 통과 시 반환값 없음. 이름 등 정규식에 없는 개인정보의 부재까지 보증하지는 않음.
    예외: 전화번호·이메일·카드번호·원회원 ID 패턴이 발견되면 ValueError가 발생함.
    부수효과: 없음. 오류 메시지에도 발견된 원문 값을 포함하지 않음.
    """
    if any(pattern.search(text) for pattern in _RESIDUAL_PRIVATE):
        raise ValueError("정제된 청크에 개인정보 형식이 남아 있습니다.")


def _intersects(span: TextSpan, start: int, end: int) -> bool:
    """끝 위치는 제외하므로 경계만 맞닿은 구간은 겹치지 않은 것으로 판단함."""
    return span.start < end and start < span.end
