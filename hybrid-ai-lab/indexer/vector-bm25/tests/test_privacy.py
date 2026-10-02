"""청크 정제 과정의 개인정보 제거와 식별자 안정성을 검증함."""

from __future__ import annotations

import pytest

from app.domain.models import LoadedDocument, RawChunk, TextSpan
from app.domain.text_rules import apply_text_edits
from app.infrastructure.processor import ValidatingChunkProcessor
from conftest import FakeTokenCounter


def _document(text: str, *, pseudonymized: bool = True) -> LoadedDocument:
    """개인정보 처리 시험에 필요한 제한 등급 상담 문서를 생성함."""
    return LoadedDocument(
        document_id="D3:C-1",
        source="D3_test.txt",
        doc_key="D3",
        text=text,
        metadata={
            "doc_type": "consult_log",
            "access_level": "restricted",
            "created_at": "2026-03-02",
            "version": "v2",
            "owner_dept": "customer_service",
            "record_id": "C-1",
            "member_pseudo_id": "m_test",
        },
        pseudonymized=pseudonymized,
    )


def test_document_edits_replace_private_value_before_chunking() -> None:
    """문서 단위 치환은 청크 경계와 무관하게 개인정보를 한 번에 대체함을 보증함."""
    text = "[접수정보] 전화: 010-1234-5678\n고객: 회신은 010-1234-5678로 주세요."
    header_end = text.index("\n") + 1
    first = text.index("010")
    second = text.index("010", header_end)
    cleaned = apply_text_edits(
        text,
        (TextSpan(0, header_end, "record_header"),),
        (TextSpan(first, first + 13, "[삭제]"), TextSpan(second, second + 13, "[삭제]")),
    )
    assert cleaned == "고객: 회신은 [삭제]로 주세요."


def test_processor_blocks_residual_private_value() -> None:
    """로더 치환을 빠져나간 개인정보 형식이 청크에 남으면 저장을 막음을 보증함."""
    text = "고객: 연락처는 010-1234-5678입니다."
    processor = ValidatingChunkProcessor(FakeTokenCounter())
    with pytest.raises(ValueError, match="개인정보"):
        processor.process(RawChunk(_document(text), text, 0, len(text), 0))


def test_processor_sets_stable_hash_id_and_retriever_metadata() -> None:
    """동일 입력의 청크 ID와 해시가 안정적이며 검색 필수 메타데이터를 포함함을 보증함."""
    text = "고객: 연회비를 문의했습니다."
    document = _document(text, pseudonymized=False)
    processor = ValidatingChunkProcessor(FakeTokenCounter())
    first = processor.process(RawChunk(document, text, 0, len(text), 0))
    second = processor.process(RawChunk(document, text, 0, len(text), 0))

    assert first == second
    assert first is not None
    assert first.metadata["source"] == "D3_test.txt"
    assert first.metadata["record_id"] == "C-1"
    assert first.metadata["chunk_id"] == first.chunk_id
    # 글자 위치는 검색 이후 쓰는 곳이 없어 메타데이터에 남기지 않음.
    assert not {"char_start", "char_end", "char_len"} & set(first.metadata)
    assert first.metadata["pseudonymized"] is False
