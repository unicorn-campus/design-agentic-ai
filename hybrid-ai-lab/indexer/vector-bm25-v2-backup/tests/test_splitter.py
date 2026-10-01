"""공통 재귀 분할기의 원문 좌표와 토큰 상한을 검증함."""

from __future__ import annotations

import json

import pytest

from app.domain.models import LoadedDocument, SplitPolicy
from app.infrastructure.splitter import RecursiveDocumentSplitter
from conftest import FakeTokenCounter


pytest.importorskip("langchain_text_splitters")


def test_common_splitter_preserves_source_offsets_and_hard_token_limit(tmp_path) -> None:
    """모든 청크가 원문 좌표를 유지하고 실제 토큰 상한 안에서 원문 전체를 덮음을 보증함."""
    policy_file = tmp_path / "policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "documents": {
                    "D1": {
                        "separators": [
                            "(?=제\\s*\\d+조\\s*\\([^\\n]+\\))",
                            "\\n",
                            " ",
                            "",
                        ]
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    text = "제1조(목적)\n" + "가" * 35 + "\n제2조(조건)\n" + "나" * 35
    document = LoadedDocument(
        document_id="D1:test",
        source="D1_test.pdf",
        doc_key="D1",
        text=text,
        metadata={"doc_type": "regulation", "access_level": "public"},
    )
    counter = FakeTokenCounter()
    chunks = RecursiveDocumentSplitter(counter, policy_file).split(
        document, SplitPolicy(chunk_size=24, chunk_overlap=6)
    )

    assert len(chunks) > 2
    assert all(counter.count(chunk.text) <= 24 for chunk in chunks)
    assert all(document.text[chunk.start:chunk.end] == chunk.text for chunk in chunks)
    assert [chunk.start for chunk in chunks] == sorted(chunk.start for chunk in chunks)
    covered = [False] * len(text)
    for chunk in chunks:
        for index in range(chunk.start, chunk.end):
            covered[index] = True
    assert all(covered)


def test_capture_group_separator_is_rejected(tmp_path) -> None:
    """좌표 계산을 흐리는 캡처 그룹 정규식을 설정 단계에서 거부함을 보증함."""
    policy_file = tmp_path / "policies.json"
    policy_file.write_text(
        json.dumps({"documents": {"D1": {"separators": ["(제\\d+조)", ""]}}}),
        encoding="utf-8",
    )
    document = LoadedDocument("D1:test", "test.pdf", "D1", "제1조 본문")
    with pytest.raises(ValueError, match="캡처 그룹"):
        RecursiveDocumentSplitter(FakeTokenCounter(), policy_file).split(
            document, SplitPolicy(chunk_size=20, chunk_overlap=5)
        )
