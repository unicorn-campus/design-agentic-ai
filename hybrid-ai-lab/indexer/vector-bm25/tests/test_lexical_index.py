"""버전형 corpus와 BM25S 게시 계약 시험."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document
import pytest

from app.domain.korean_tokenizer import KoreanTokenizer, _CONTENT_TAGS, _POLICY_VERSION
from app.infrastructure.file_store import FileStore
from app.infrastructure.lexical_index import publish_search_index
from app.infrastructure.chroma_store import MemoryVectorStore
from app.application.graph import IndexerResources


def _document(chunk_id: str, text: str) -> Document:
    return Document(
        id=chunk_id,
        page_content=text,
        metadata={
            "access_level": "public",
            "source": "D1.pdf",
            "doc_key": "D1",
            "doc_type": "regulation",
        },
    )


def _card_document(chunk_id: str, card_id: str, card_name: str) -> Document:
    return Document(
        id=chunk_id,
        page_content=f"{card_name} 혜택",
        metadata={
            "access_level": "public",
            "source": "D2.pdf",
            "doc_key": "D2",
            "doc_type": "benefit",
            "card_id": card_id,
            "card_name": card_name,
        },
    )


def _publish(root: Path, documents: list[Document], vector_ids: list[str], *, full: bool) -> dict:
    return publish_search_index(
        index_root=root,
        documents=documents,
        vector_ids=vector_ids,
        full_snapshot=full,
        file_store=FileStore(),
        vector_collection="card_docs",
        embedding_signature="test-signature",
    )


def test_publish_writes_generation_then_active_pointer() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "search_indexes"
        pointer = _publish(
            root,
            [_document("D1_0000", "전월 실적 30만원")],
            ["D1_0000"],
            full=True,
        )

        active = json.loads((root / "active_index.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / active["manifest"]).read_text(encoding="utf-8"))
        oov_report = json.loads(
            (root / active["oov_candidates"]).read_text(encoding="utf-8")
        )
        corpus_hash = FileStore().sha256(root / active["corpus"])
        assert active == pointer
        assert active["chunk_count"] == 1
        assert active["corpus_sha256"] == corpus_hash == manifest["corpus_sha256"]
        assert manifest["tokenizer_signature"].startswith("kiwi:")
        assert manifest["oov_candidate_count"] == len(oov_report["candidates"])
        assert oov_report["policy"] == "human-review-required-v1"
        assert oov_report["auto_registered"] is False
        assert (root / active["bm25"] / "params.index.json").is_file()
        assert not (root / active["bm25"] / "corpus.jsonl").exists()


def test_publish_generates_deterministic_card_dictionary() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "search_indexes"
        documents = [
            _card_document("D2_0002", "D2-C002", "한빛 모아생활"),
            _card_document("D2_0001", "D2-C001", " 블루문카드 "),
            _card_document("D2_0003", "D2-C003", "한빛  모아생활"),
        ]

        pointer = _publish(
            root,
            documents,
            [str(document.id) for document in documents],
            full=True,
        )

        dictionary_path = root / pointer["card_dictionary"]
        dictionary_payload = dictionary_path.read_bytes()
        manifest = json.loads((root / pointer["manifest"]).read_text(encoding="utf-8"))
        assert dictionary_payload.decode("utf-8") == (
            "블루문카드\tNNP\t0.0\n"
            "한빛 모아생활\tNNP\t0.0\n"
        )
        assert pointer["card_dictionary_count"] == 2
        assert pointer["card_dictionary_sha256"] == FileStore().sha256(dictionary_path)
        assert manifest["card_dictionary"] == {
            "path": pointer["card_dictionary"],
            "sha256": pointer["card_dictionary_sha256"],
            "count": 2,
            "source": "D2.metadata.card_name",
            "tag": "NNP",
            "score": 0.0,
        }


def test_publish_rejects_conflicting_card_names_for_same_card_id() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "search_indexes"
        documents = [
            _card_document("D2_0001", "D2-C001", "블루문카드"),
            _card_document("D2_0002", "D2-C001", "한빛카드"),
        ]

        with pytest.raises(ValueError, match="같은 card_id에 서로 다른 카드명"):
            _publish(
                root,
                documents,
                [str(document.id) for document in documents],
                full=True,
            )

        assert not (root / "active_index.json").exists()


def test_id_mismatch_keeps_previous_active_generation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "search_indexes"
        first = _publish(
            root,
            [_document("D1_0000", "기존 문서")],
            ["D1_0000"],
            full=True,
        )

        with pytest.raises(ValueError, match="청크 ID"):
            _publish(
                root,
                [_document("D1_0001", "새 문서")],
                ["D1_0000", "D1_0001", "D1_9999"],
                full=False,
            )

        active = json.loads((root / "active_index.json").read_text(encoding="utf-8"))
        assert active["generation"] == first["generation"]


def test_finalize_publishes_only_after_vector_accounting_succeeds() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        document = _document("D1_0000", "전월 실적 30만원")
        vector_store = MemoryVectorStore("test-signature")
        vector_store.upsert(
            ["D1_0000"],
            [document.page_content],
            [[1.0, 0.0]],
            [document.metadata],
        )
        settings = SimpleNamespace(
            CHROMA_COLLECTION="card_docs",
            EMBED_MODEL="test-model",
            SEARCH_INDEX_ROOT=root / "search_indexes",
            KOREAN_USER_DICTIONARY=None,
            BM25_K1=1.5,
            BM25_B=0.75,
        )
        resources = IndexerResources(
            settings,
            None,
            FileStore(),
            SimpleNamespace(signature="test-signature", dimension=2),
            vector_store,
        )
        resources._runs["idx-test"] = {
            "expected_count": 1,
            "chunk_params": {},
            "plan": {"hashes": {"D1_0000": {"text": "hash"}}},
        }

        result = resources._run_finalize_index(
            {
                "thread_id": "idx-test",
                "output_path": str(root),
                "embedding_backend": "smoke",
                "chunks": [document],
                "ok_ids": ["D1_0000"],
                "failed": [],
                "fingerprints": {"D1.pdf": "hash"},
                "full_reindex": True,
            }
        )

        assert result["accounting_ok"] is True
        assert result["search_index"]["chunk_count"] == 1
        assert (root / "index_manifest.json").is_file()
        assert (root / "search_indexes" / "active_index.json").is_file()


def test_korean_tokenizer_preserves_lemmas_and_only_useful_surfaces() -> None:
    tokenizer = KoreanTokenizer(num_workers=1)

    assert "귀엽" in tokenizer.tokenize("귀여워요")
    assert "귀엽" in tokenizer.tokenize("귀엽다")

    inflected = tokenizer.tokenize("연회비가 없어요")
    assert "연회비" in inflected
    assert "없" in inflected
    assert "연회비가" not in inflected
    assert "없어요" not in inflected

    compound = tokenizer.tokenize("해외결제수수료 K-패스 10만원")
    assert {"해외결제수수료", "k-패스", "10만원"} <= set(compound)


def test_korean_tokenizer_batch_matches_single_document_analysis() -> None:
    tokenizer = KoreanTokenizer(num_workers=2)
    texts = ["귀여워요", "해외결제수수료 제외", "K-패스 10만원"]

    assert tokenizer.tokenize_many(texts) == [tokenizer.tokenize(text) for text in texts]
    assert tokenizer.tokenize_many([]) == []


def test_user_dictionary_format_and_hash_are_part_of_signature() -> None:
    with tempfile.TemporaryDirectory() as directory:
        first_path = Path(directory) / "first.dict"
        second_path = Path(directory) / "second.dict"
        first_path.write_text("블루문카드\tNNG\t10.0\n", encoding="utf-8")
        second_path.write_text("블루문카드\tNNP\t5.0\n", encoding="utf-8")

        first = KoreanTokenizer(first_path, num_workers=1)
        second = KoreanTokenizer(second_path, num_workers=1)

        assert "블루문카드" in first.tokenize("블루문카드 혜택")
        assert first.user_dictionary_sha256
        assert first.signature != second.signature


def test_additional_user_words_support_spaces_and_change_signature() -> None:
    with tempfile.TemporaryDirectory() as directory:
        dictionary_path = Path(directory) / "base.dict"
        dictionary_payload = "기본카드\tNNP\t0.0\n"
        dictionary_path.write_text(dictionary_payload, encoding="utf-8")
        baseline = KoreanTokenizer(dictionary_path, num_workers=1)
        first = KoreanTokenizer(
            dictionary_path,
            additional_user_words=[("한빛 모아생활", "NNP", 0.0)],
            num_workers=1,
        )
        second = KoreanTokenizer(
            dictionary_path,
            additional_user_words=[("블루문카드", "NNP", 0.0)],
            num_workers=1,
        )

        assert "기본카드" in first.tokenize("기본카드 혜택")
        assert "한빛모아생활" in first.tokenize("한빛 모아생활 혜택")
        assert dictionary_path.read_text(encoding="utf-8") == dictionary_payload
        assert first.additional_user_words_sha256
        assert baseline.signature != first.signature != second.signature


def test_empty_additional_user_words_keep_legacy_signature() -> None:
    tokenizer = KoreanTokenizer(additional_user_words=[], num_workers=1)
    legacy_payload = {
        "name": "kiwi-content-and-surface",
        "policy_version": _POLICY_VERSION,
        "kiwipiepy": tokenizer._version,
        "normalization": "nfkc-lower-remove-numeric-comma-v1",
        "content_tags": sorted(_CONTENT_TAGS),
        "tag_normalization": "strip-kiwi-regularity-suffix-v1",
        "surface_policy": "number-unit-code-dictionary-clean-compound-v2",
        "stopword_policy": "content-pos-filter-v1",
        "oov_handling": "chr",
        "typo_policy": "basic",
        "typo_cost_threshold": 2.5,
        "user_dictionary_sha256": "",
    }
    encoded = json.dumps(
        legacy_payload,
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")

    assert tokenizer.signature == f"kiwi:{hashlib.sha256(encoded).hexdigest()}"


def test_oov_extraction_returns_candidates_without_registering_them() -> None:
    tokenizer = KoreanTokenizer(num_workers=1)

    class CandidateExtractor:
        def extract_words(self, texts, **kwargs):
            assert list(texts) == ["엑소바이옴 제품"]
            assert kwargs["min_cnt"] == 2
            return [("엑소바이옴", 0.8, 3, 0.7)]

    # add_user_word/extract_add_words가 없는 대역이므로 자동 등록을 시도하면 실패함.
    tokenizer._kiwi = CandidateExtractor()
    candidates = tokenizer.extract_oov_candidates(["엑소바이옴 제품"], min_cnt=2)

    assert [candidate.form for candidate in candidates] == ["엑소바이옴"]
    assert candidates[0].frequency == 3
