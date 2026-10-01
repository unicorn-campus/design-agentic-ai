"""청크 정제 과정의 개인정보 제거와 식별자 안정성을 검증함."""

from __future__ import annotations

from app.domain.models import LoadedDocument, RawChunk, TextSpan
from app.infrastructure.processor import ValidatingChunkProcessor
from conftest import FakeTokenCounter


def _document(text: str, privacy_spans: tuple[TextSpan, ...]) -> LoadedDocument:
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
        privacy_spans=privacy_spans,
    )


def test_private_value_split_by_chunk_boundary_is_fully_masked() -> None:
    """개인정보가 청크 경계에서 잘려도 양쪽 조각에 원문이 남지 않음을 보증함."""
    text = "앞 010-1234-5678 뒤"
    start = text.index("010")
    end = start + len("010-1234-5678")
    document = _document(text, (TextSpan(start, end, "[삭제]"),))
    processor = ValidatingChunkProcessor(FakeTokenCounter())

    left = processor.process(RawChunk(document, text[: start + 6], 0, start + 6, 0))
    right = processor.process(RawChunk(document, text[start + 6 :], start + 6, len(text), 1))

    assert left is not None and right is not None
    assert "010" not in left.text
    assert "5678" not in right.text
    assert "[삭제]" in left.text and "[삭제]" in right.text


def test_processor_sets_stable_hash_id_and_retriever_metadata() -> None:
    """동일 입력의 청크 ID와 해시가 안정적이며 검색 필수 메타데이터를 포함함을 보증함."""
    text = "고객: 연회비를 문의했습니다."
    document = _document(text, ())
    processor = ValidatingChunkProcessor(FakeTokenCounter())
    first = processor.process(RawChunk(document, text, 0, len(text), 0))
    second = processor.process(RawChunk(document, text, 0, len(text), 0))

    assert first == second
    assert first is not None
    assert first.metadata["source"] == "D3_test.txt"
    assert first.metadata["record_id"] == "C-1"
    assert first.metadata["chunk_id"] == first.chunk_id
