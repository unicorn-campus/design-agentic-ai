"""대상 경계 하드 분할과 색인용 머리말이 메타데이터·토큰 예산 계약을 지키는지 검증함."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from app.application.indexing_service import IndexingWorkflow
from app.domain.models import LoadedDocument, SplitPolicy, TextSpan
from app.domain.segments import (
    HeaderPolicy,
    SegmentPolicy,
    plan_segments,
    segment_document,
)
from app.infrastructure.processor import ValidatingChunkProcessor
from app.infrastructure.settings import _segment_policy
from app.infrastructure.splitter import RecursiveDocumentSplitter
from conftest import FakeTokenCounter


HEADER = HeaderPolicy(
    template="[카드: {card_name} ({card_id})]",
    field_templates=(("card_name", "[카드: {card_name}]"), ("card_id", "[카드: {card_id}]")),
)
POLICY = SegmentPolicy(
    boundary_regex=r"(?m)^(D2-C\d{3})[ \t]*$",
    tail_regex=r"(?m)^D2-C\d{3}(?!-B)[ \t]*[|·]",
    key_field="card_id",
    value_fields=("card_name",),
    metadata_fields=(("card_id", "card_id"), ("product_id", "card_id"), ("card_name", "card_name")),
    clear_keys=("card_id", "product_id", "card_name", "card_id_all", "card_name_all"),
    ambiguity_keys=("benefit_id_all", "section_label_all"),
    header=HEADER,
)

COVER = "혜택 안내서\n목차\nD2-C001 가가\nD2-C002 나나\n\n"
CARD1 = "D2-C001\n한빛 가가\n적립률은 1퍼센트입니다.\n\n"
CARD2 = "D2-C002\n한빛 나나\n할인율은 2퍼센트입니다.\n\n"
TAIL = "참고 목록\nD2-C001 | 참고 카드: 가가\n"
TEXT = COVER + CARD1 + CARD2 + TAIL


def _document(text: str = TEXT) -> LoadedDocument:
    """카드 문맥 구간을 갖춘 시험용 D2 문서를 만듦."""
    first = text.find("D2-C001\n한빛")
    second = text.find("D2-C002\n한빛")
    contexts = (
        (
            TextSpan(first, second, {"card_id": "D2-C001", "card_name": "한빛 가가"}),
            TextSpan(second, len(text), {"card_id": "D2-C002", "card_name": "한빛 나나"}),
        )
        if first >= 0 and second > first
        else ()
    )
    return LoadedDocument(
        document_id="D2_test",
        source="D2.pdf",
        doc_key="D2",
        text=text,
        metadata={
            "source": "D2.pdf",
            "doc_key": "D2",
            "doc_type": "benefit_guide",
            "access_level": "public",
            "created_at": "2026-01-01",
            "version": "v1",
            "owner_dept": "benefit_ops",
        },
        page_spans=(TextSpan(0, len(text), 1),),
        context_spans=contexts,
    )


def test_segments_split_at_boundaries_and_mark_untargeted_parts():
    """표지·목차와 문서 끝 참고 목록은 대상 없음으로, 카드 구간은 각자의 카드로 나뉨을 보증함."""
    segments = plan_segments(_document(), POLICY)
    assert [item.targeted for item in segments] == [False, True, True, False]
    assert "".join(TEXT[item.start : item.end] for item in segments) == TEXT
    assert segments[1].binding.value_map() == {"card_id": "D2-C001", "card_name": "한빛 가가"}
    assert segments[2].binding.value_map()["card_id"] == "D2-C002"
    # 참고 목록은 마지막 카드 구간에 딸려 들어가지 않음
    assert TEXT[segments[3].start :].startswith("참고 목록")


def test_segments_fall_back_to_one_part_without_policy_or_boundary():
    """정책이 없거나 경계를 찾지 못하면 문서 전체를 대상 없는 구간 하나로 둠을 보증함."""
    assert len(plan_segments(_document(), SegmentPolicy())) == 1
    plain = _document("카드 코드가 없는 본문입니다.")
    assert plan_segments(plain, POLICY) == plan_segments(plain, SegmentPolicy())


def test_segment_document_moves_spans_into_segment_coordinates():
    """구간 문서의 페이지·문맥 위치가 구간 기준 좌표로 옮겨짐을 보증함."""
    document = _document()
    segment = plan_segments(document, POLICY)[1]
    sub = segment_document(document, segment)
    assert sub.text == TEXT[segment.start : segment.end]
    assert sub.page_spans[0].start == 0
    assert sub.context_spans[0].value["card_id"] == "D2-C001"
    assert sub.document_id == document.document_id and sub.doc_key == "D2"


def test_binding_replaces_card_metadata_and_clears_mixed_markers():
    """구간의 카드로 메타데이터가 확정되고 여러 카드 표시가 사라짐을 보증함."""
    binding = plan_segments(_document(), POLICY)[2].binding
    result = binding.apply(
        {
            "source": "D2.pdf",
            "card_id": "D2-C001",
            "card_name": "한빛 가가",
            "card_id_all": '["D2-C001", "D2-C002"]',
            "context_ambiguous": True,
        }
    )
    assert result["card_id"] == "D2-C002" and result["product_id"] == "D2-C002"
    assert result["card_name"] == "한빛 나나"
    assert "card_id_all" not in result and "context_ambiguous" not in result


def test_untargeted_segment_has_no_card_metadata():
    """목차 구간에 첫 코드 카드가 붙던 오류가 사라짐을 보증함."""
    binding = plan_segments(_document(), POLICY)[0].binding
    result = binding.apply({"source": "D2.pdf", "card_id": "D2-C001", "card_name": "한빛 가가"})
    assert "card_id" not in result and "card_name" not in result and "product_id" not in result


def test_binding_keeps_ambiguity_marker_when_other_groups_remain():
    """혜택·조항이 여러 개 걸친 청크는 카드가 확정돼도 모호성 표시를 남김을 보증함."""
    binding = plan_segments(_document(), POLICY)[1].binding
    result = binding.apply({"benefit_id_all": '["D2-C001-B01"]', "context_ambiguous": True})
    assert result["context_ambiguous"] is True


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("적립률 안내", "[카드: 한빛 가가 (D2-C001)]"),
        ("한빛 가가 적립률", "[카드: D2-C001]"),
        ("D2-C001 적립률", "[카드: 한빛 가가]"),
        ("D2-C001 한빛 가가 적립률", ""),
        ("d2-c001  한빛가가 적립률", ""),  # 공백·대소문자만 다른 경우도 중복으로 봄
    ],
)
def test_header_omits_values_already_present_in_body(body: str, expected: str):
    """본문에 이미 있는 값은 머리말에서 빠지고, 둘 다 있으면 머리말이 없음을 보증함."""
    values = {"card_id": "D2-C001", "card_name": "한빛 가가"}
    assert HEADER.compose(values, body) == expected
    # 예산 계산용 머리말은 본문과 무관하게 가장 긴 형태임
    assert HEADER.full(values) == "[카드: 한빛 가가 (D2-C001)]"


def _pipeline() -> tuple[RecursiveDocumentSplitter, ValidatingChunkProcessor, FakeTokenCounter]:
    """실제 분할기·처리기와 문자 수 기반 가짜 토큰 계산기를 묶음."""
    counter = FakeTokenCounter()
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "metadata_schema.json").read_text(
            encoding="utf-8-sig"
        )
    )
    policies = {
        "documents": {"D2": {"separators": [r"(?=D2-C\d{3}(?:-B\d+)?)", "\\n\\n", "\\n", " ", ""]}}
    }
    return RecursiveDocumentSplitter(counter, policies), ValidatingChunkProcessor(counter, schema), counter


def _workflow(splitter, processor, counter) -> IndexingWorkflow:
    """경계 분할만 검증하기 위해 나머지 포트를 쓰지 않는 워크플로를 만듦."""
    return IndexingWorkflow(
        sources=None,
        loader=None,
        splitter=splitter,
        token_counter=counter,
        processor=processor,
        embedder=None,
        repository=None,
        artifacts=None,
        policies={"D2": SplitPolicy()},
        default_policy=SplitPolicy(),
        segment_policies={"D2": POLICY},
        policy_signature="p",
        profile_signature="f",
    )


def test_chunks_never_merge_across_a_target_boundary():
    """한 청크가 두 카드의 설명을 함께 담지 않음을 보증함."""
    splitter, processor, counter = _pipeline()
    workflow = _workflow(splitter, processor, counter)
    document = _document()
    chunks = []
    for segment in plan_segments(document, POLICY):
        chunks.extend(workflow._split_segment(document, segment, SplitPolicy(), POLICY))
    assert chunks, "청크가 하나도 만들어지지 않음"
    for chunk in chunks:
        if not chunk.metadata.get("card_id"):
            continue  # 목차는 여러 코드를 나열하는 '대상 없음' 구간이라 검사 대상이 아님
        codes = {"D2-C001", "D2-C002"} & set(chunk.text.replace("\n", " ").split())
        assert len(codes) <= 1, (chunk.chunk_id, chunk.text)
        assert codes <= {chunk.metadata["card_id"]}
    cards = [chunk.metadata.get("card_id") for chunk in chunks]
    assert "D2-C001" in cards and "D2-C002" in cards
    assert None in cards  # 표지·목차와 참고 목록 구간


def test_header_goes_into_index_text_only_and_fits_the_token_budget():
    """머리말은 색인용 텍스트에만 들어가고 저장 본문은 원문 그대로임을 보증함."""
    splitter, processor, counter = _pipeline()
    workflow = _workflow(splitter, processor, counter)
    document = _document()
    segment = plan_segments(document, POLICY)[1]
    chunks = workflow._split_segment(document, segment, SplitPolicy(), POLICY)
    assert chunks
    for chunk in chunks:
        assert not chunk.text.startswith("[카드:")
        if chunk.index_text:
            assert chunk.index_text == f"[카드: 한빛 가가]\n{chunk.text}"
            assert chunk.embedding_text == chunk.index_text
        else:
            assert chunk.embedding_text == chunk.text
        assert chunk.token_count == counter.count(chunk.embedding_text)
        assert chunk.token_count <= counter.max_tokens


def test_header_budget_is_reserved_before_splitting():
    """머리말 몫을 먼저 빼기 때문에 머리말을 붙여도 상한을 넘지 않음을 보증함."""
    splitter, processor, counter = _pipeline()
    workflow = _workflow(splitter, processor, counter)
    long_body = "적립 조건 안내 문장입니다. " * 120
    document = _document(COVER + f"D2-C001\n한빛 가가\n{long_body}\n\n" + CARD2 + TAIL)
    segment = plan_segments(document, POLICY)[1]
    narrow = SplitPolicy(chunk_size=200, chunk_overlap=20)
    chunks = workflow._split_segment(document, segment, narrow, POLICY)
    assert len(chunks) > 1, "예산이 줄어 여러 청크로 나뉘어야 함"
    for chunk in chunks:
        assert counter.count(chunk.embedding_text) <= narrow.chunk_size


def test_segment_policy_is_read_from_document_policies_config():
    """운영 설정 파일의 D2 정책에서 경계·머리말 규칙이 그대로 읽힘을 보증함."""
    config = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "document_policies.json").read_text(
            encoding="utf-8-sig"
        )
    )
    d2 = _segment_policy(config["documents"]["D2"])
    assert d2.enabled and d2.key_field == "card_id"
    assert d2.header.template == "[카드: {card_name} ({card_id})]"
    # 경계 설정이 없는 문서는 하드 분할을 쓰지 않음
    assert not _segment_policy(config["documents"]["D1"]).enabled
    assert not _segment_policy(config["documents"]["D3"]).header.enabled


def test_index_text_is_published_and_readable_by_existing_retriever(tmp_path: Path):
    """머리말이 붙은 세대를 기존 Retriever가 그대로 읽고 원문을 인용함을 보증함."""
    pytest.importorskip("chromadb")
    pytest.importorskip("bm25s")
    pytest.importorskip("kiwipiepy")
    from app.domain.models import PreparedChunk
    from app.infrastructure.index_repository import GenerationIndexRepository
    from app.domain.text_rules import sha256_text, stable_json_hash

    body = "적립률은 1퍼센트입니다."
    index_text = "[카드: 한빛 가가 (D2-C001)]\n" + body
    metadata = {
        "chunk_id": "D2-C001-0000",
        "source": "D2.pdf",
        "doc_key": "D2",
        "doc_type": "benefit_guide",
        "access_level": "public",
        "card_id": "D2-C001",
        "card_name": "한빛 가가",
    }
    chunk = PreparedChunk(
        chunk_id="D2-C001-0000",
        text=body,
        metadata=metadata,
        token_count=20,
        text_hash=sha256_text(index_text),
        metadata_hash=stable_json_hash(metadata),
        index_text=index_text,
    )
    signature = "sentence-transformers:nlpai-lab/KURE-v2:prompt-policy-v2"
    repository = GenerationIndexRepository(tmp_path / "data")
    repository.begin("gen-header", signature)
    repository.upsert("gen-header", [chunk], [[1.0, *([0.0] * 767)]])
    stage = repository.build_text_index("gen-header", [chunk], {})
    publication = repository.publish("gen-header", [chunk], {}, stage)

    retriever_root = Path(__file__).resolve().parents[3] / "retriever" / "vector-retriever"
    retriever_python = retriever_root / ".venv" / "Scripts" / "python.exe"
    if not retriever_python.is_file():
        pytest.skip("기존 Retriever 가상환경이 없습니다.")
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        "from app.infrastructure.bm25_index import BM25Index\n"
        "from app.infrastructure.corpus_store import VersionedCorpusStore\n"
        "from app.infrastructure.korean_tokenizer import KoreanTokenizer\n"
        "corpus = VersionedCorpusStore(Path(sys.argv[1]))\n"
        "snapshot = corpus.load_active()\n"
        "assert snapshot is not None and len(snapshot.records) == 1\n"
        "row = snapshot.records[0]\n"
        "assert row['index_text'].startswith('[')\n"
        "assert not row['text'].startswith('[')\n"
        "bm25 = BM25Index(corpus, KoreanTokenizer())\n"
        "bm25.warm()\n"
        "scores = bm25.keyword_search('한빛 가가 적립률',"
        " allowed_access_levels=frozenset({'public'}), k=5)\n"
        "assert 'D2-C001-0000' in scores\n"
        "hit = bm25.chunks()['D2-C001-0000']\n"
        "assert not hit.text.startswith('[')\n"
        "print('header-compatible')\n"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(retriever_root)
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(retriever_python), "-c", script, publication.search_index_root],
        cwd=retriever_root,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "header-compatible" in result.stdout
