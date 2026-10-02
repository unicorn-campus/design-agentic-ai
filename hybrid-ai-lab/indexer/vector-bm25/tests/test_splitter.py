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


def test_table_cut_by_chunk_boundary_repeats_header_row(tmp_path) -> None:
    """표가 청크 경계에서 잘리면 뒤쪽 청크가 표 머리글 행으로 시작하고 상한을 지킴을 보증함."""
    policy_file = tmp_path / "policies.json"
    policy_file.write_text(
        json.dumps({"documents": {"D2": {"separators": ["(?<=\\n)(?=\\| )", "\\n", " ", ""]}}}),
        encoding="utf-8",
    )
    header = "| 항목 | 조건 |\n| --- | --- |\n"
    rows = "".join(f"| 행{index:02d} | 값{index:02d}값 |\n" for index in range(12))
    text = "혜택 조건표\n" + header + rows
    document = LoadedDocument("D2:test", "D2_test.pdf", "D2", text)
    counter = FakeTokenCounter()
    chunks = RecursiveDocumentSplitter(counter, policy_file).split(
        document, SplitPolicy(chunk_size=90, chunk_overlap=0)
    )

    assert len(chunks) > 2
    assert all(counter.count(chunk.text) <= 90 for chunk in chunks)
    continued = [chunk for chunk in chunks[1:] if document.text[chunk.start:chunk.end].startswith("| 행")]
    assert continued
    assert all(chunk.text.startswith(header) for chunk in continued)
    # 머리글을 덧붙인 청크도 본문 구간 자체는 원래 위치를 가리킴
    assert all(chunk.text.endswith(document.text[chunk.start:chunk.end]) for chunk in continued)
    joined_rows = "".join(document.text[chunk.start:chunk.end] for chunk in chunks)
    assert all(f"| 행{index:02d} |" in joined_rows for index in range(12))


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
