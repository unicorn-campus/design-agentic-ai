"""BM25S 로딩, 한글 토큰화, ACL 사전 필터 시험."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import bm25s
import pytest

from app.domain.korean_tokenizer import KoreanTokenizer
from app.infrastructure.bm25_index import BM25Index
from app.infrastructure.corpus_store import VersionedCorpusStore


def _write_generation(
    root: Path,
    records: list[dict],
    *,
    generation: str = "gen-test",
    card_words: tuple[tuple[str, str, float], ...] | None = None,
    user_dictionary: Path | None = None,
) -> dict:
    tokenizer = KoreanTokenizer(
        user_dictionary,
        additional_user_words=card_words,
    )
    generation_dir = root / "generations" / generation
    bm25_path = generation_dir / "bm25"
    generation_dir.mkdir(parents=True)
    corpus_payload = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    ).encode("utf-8")
    (generation_dir / "corpus.jsonl").write_bytes(corpus_payload)
    corpus_hash = hashlib.sha256(corpus_payload).hexdigest()
    retriever = bm25s.BM25()
    retriever.index(
        tokenizer.tokenize_many(row["text"] for row in records),
        show_progress=False,
    )
    retriever.save(bm25_path, show_progress=False)
    manifest = {
        "generation": generation,
        "corpus_sha256": corpus_hash,
        "tokenizer_signature": tokenizer.signature,
    }
    pointer = {
        "generation": generation,
        "manifest": f"generations/{generation}/manifest.json",
        "corpus": f"generations/{generation}/corpus.jsonl",
        "bm25": f"generations/{generation}/bm25",
        "corpus_sha256": corpus_hash,
        "chunk_count": len(records),
    }
    if card_words is not None:
        dictionary_payload = KoreanTokenizer.additional_user_words_payload(card_words)
        dictionary_hash = hashlib.sha256(dictionary_payload).hexdigest()
        dictionary_relative = f"generations/{generation}/card_names.dict"
        (generation_dir / "card_names.dict").write_bytes(dictionary_payload)
        dictionary_info = {
            "path": dictionary_relative,
            "sha256": dictionary_hash,
            "count": len(card_words),
            "source": "D2.metadata.card_name",
            "tag": "NNP",
            "score": 0.0,
        }
        manifest["card_dictionary"] = dictionary_info
        pointer.update(
            {
                "card_dictionary": dictionary_relative,
                "card_dictionary_sha256": dictionary_hash,
                "card_dictionary_count": len(card_words),
            }
        )
    (generation_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "active_index.json").write_text(
        json.dumps(pointer, ensure_ascii=False),
        encoding="utf-8",
    )
    return pointer


@pytest.mark.parametrize(
    ("query", "expected_chunk_id", "expected_terms"),
    [
        ("배달 음식점 할인 혜택", "dining-benefit", ("음식점", "배달앱", "할인")),
        ("공항 라운지 항공권 혜택", "travel-benefit", ("공항", "라운지", "항공권")),
        ("버스 지하철 교통비 할인", "transit-benefit", ("버스", "지하철", "교통비")),
    ],
)
def test_keyword_search_returns_expected_top_chunk(
    tmp_path: Path,
    query: str,
    expected_chunk_id: str,
    expected_terms: tuple[str, ...],
) -> None:
    records = [
        {
            "chunk_id": "dining-benefit",
            "text": "음식점 외식 배달앱 점심 저녁 할인 혜택 안내",
            "metadata": {"access_level": "public"},
        },
        {
            "chunk_id": "travel-benefit",
            "text": "공항 라운지 항공권 해외여행 호텔 할인 혜택 안내",
            "metadata": {"access_level": "public"},
        },
        {
            "chunk_id": "transit-benefit",
            "text": "대중교통 버스 지하철 택시 교통비 할인 혜택 안내",
            "metadata": {"access_level": "public"},
        },
    ]
    _write_generation(tmp_path, records)
    index = BM25Index(VersionedCorpusStore(tmp_path), KoreanTokenizer())

    keyword_search_scores_by_chunk_id = index.keyword_search(query, k=2)

    assert keyword_search_scores_by_chunk_id
    top_chunk_id = next(iter(keyword_search_scores_by_chunk_id))
    assert top_chunk_id == expected_chunk_id
    top_hit = index.chunks()[top_chunk_id]
    missing_terms = [term for term in expected_terms if term not in top_hit.text]
    assert not missing_terms, f"1위 청크 본문에 핵심어가 없음: {missing_terms}"
    assert len(keyword_search_scores_by_chunk_id) <= 2
    assert all(score > 0 for score in keyword_search_scores_by_chunk_id.values())


def test_korean_query_and_acl_are_applied_before_score_fusion() -> None:
    records = [
        {
            "chunk_id": "public",
            "text": "전월 실적 30만원 이상에서 연회비 면제 제외 조건",
            "metadata": {"access_level": "public", "source": "terms.pdf"},
        },
        {
            "chunk_id": "restricted",
            "text": "전월실적 30만원 연회비 면제 제외 비밀 조건",
            "metadata": {"access_level": "restricted", "source": "audit.pdf"},
        },
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_generation(root, records)
        index = BM25Index(VersionedCorpusStore(root), KoreanTokenizer())

        agent_scores = index.keyword_search(
            "전월실적 30만원 제외",
            allowed_access_levels=frozenset({"public", "internal"}),
            k=10,
        )
        auditor_scores = index.keyword_search(
            "전월실적 30만원 제외",
            allowed_access_levels=frozenset({"public", "internal", "restricted"}),
            k=10,
        )

        assert agent_scores["public"] > 0
        assert "restricted" not in agent_scores
        assert auditor_scores["restricted"] > 0
        assert not (root / "generations" / "gen-test" / "bm25" / "corpus.jsonl").exists()


def test_top_k_zero_score_filter_and_query_only_typo_fallback() -> None:
    records = [
        {
            "chunk_id": "benefit",
            "text": "카드 혜택 안내",
            "metadata": {"access_level": "public"},
        },
        {
            "chunk_id": "fee",
            "text": "카드 연회비 안내",
            "metadata": {"access_level": "public"},
        },
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_generation(root, records)
        index = BM25Index(VersionedCorpusStore(root), KoreanTokenizer())

        assert index.keyword_search("완전미등록질의", k=2) == {}

        corrected = index.keyword_search("혜텍", k=1)
        assert list(corrected) == ["benefit"]
        assert corrected["benefit"] > 0

        limited = index.keyword_search("카드 안내", k=1)
        assert len(limited) == 1


def test_corpus_hash_mismatch_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_generation(
            root,
            [{"chunk_id": "one", "text": "본문", "metadata": {"access_level": "public"}}],
        )
        corpus_path = root / "generations" / "gen-test" / "corpus.jsonl"
        corpus_path.write_text("변조", encoding="utf-8")

        with pytest.raises(ValueError, match="SHA-256"):
            VersionedCorpusStore(root).load_active()


def test_active_card_dictionary_is_loaded_for_query_tokenization() -> None:
    records = [
        {
            "chunk_id": "card",
            "text": "한빛 모아생활 카드의 생활비 적립 혜택",
            "metadata": {"access_level": "public"},
        }
    ]
    card_words = (("한빛 모아생활", "NNP", 0.0),)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        user_dictionary = root / "base.dict"
        user_dictionary.write_text("기본카드\tNNP\t0.0\n", encoding="utf-8")
        pointer = _write_generation(
            root,
            records,
            card_words=card_words,
            user_dictionary=user_dictionary,
        )
        snapshot = VersionedCorpusStore(root).load_active()

        assert snapshot is not None
        assert snapshot.card_dictionary_words == card_words
        assert snapshot.card_dictionary_sha256 == pointer["card_dictionary_sha256"]

        index = BM25Index(
            VersionedCorpusStore(root),
            KoreanTokenizer(user_dictionary),
        )
        assert index.keyword_search("한빛 모아생활", k=1)["card"] > 0
        assert "한빛모아생활" in index.tokenizer.tokenize("한빛 모아생활")
        assert "기본카드" in index.tokenizer.tokenize("기본카드")


@pytest.mark.parametrize(
    (
        "query",
        "expected_card_token",
        "other_card_token",
        "expected_chunk_id",
        "expected_text_terms",
    ),
    [
        (
            "한빛 모아생활 카드의 마트 적립 혜택은?",
            "한빛모아생활",
            "블루문트래블",
            "hanbit-benefit",
            ("한빛 모아생활", "마트", "적립"),
        ),
        (
            "블루문 트래블 카드 공항 라운지 혜택 알려줘",
            "블루문트래블",
            "한빛모아생활",
            "bluemoon-benefit",
            ("블루문 트래블", "공항", "라운지"),
        ),
    ],
)
def test_card_dictionary_preserves_card_name_and_finds_expected_chunk(
    tmp_path: Path,
    query: str,
    expected_card_token: str,
    other_card_token: str,
    expected_chunk_id: str,
    expected_text_terms: tuple[str, ...],
) -> None:
    records = [
        {
            "chunk_id": "hanbit-benefit",
            "text": "한빛 모아생활 카드의 생활비 적립과 마트 할인 혜택",
            "metadata": {"access_level": "public"},
        },
        {
            "chunk_id": "bluemoon-benefit",
            "text": "블루문 트래블 카드의 공항 라운지와 해외 결제 혜택",
            "metadata": {"access_level": "public"},
        },
    ]
    card_words = (
        ("한빛 모아생활", "NNP", 0.0),
        ("블루문 트래블", "NNP", 0.0),
    )
    _write_generation(tmp_path, records, card_words=card_words)
    index = BM25Index(VersionedCorpusStore(tmp_path), KoreanTokenizer())

    index.warm()
    query_tokens = index.tokenizer.tokenize(query)
    keyword_search_scores_by_chunk_id = index.keyword_search(query, k=2)

    assert expected_card_token in query_tokens
    assert other_card_token not in query_tokens
    assert keyword_search_scores_by_chunk_id
    top_chunk_id = next(iter(keyword_search_scores_by_chunk_id))
    assert top_chunk_id == expected_chunk_id
    top_hit = index.chunks()[top_chunk_id]
    missing_terms = [term for term in expected_text_terms if term not in top_hit.text]
    assert not missing_terms, f"1위 청크 본문에 핵심어가 없음: {missing_terms}"


def test_card_dictionary_tampering_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        pointer = _write_generation(
            root,
            [{"chunk_id": "one", "text": "본문", "metadata": {}}],
            card_words=(("블루문카드", "NNP", 0.0),),
        )
        (root / pointer["card_dictionary"]).write_text(
            "변조카드\tNNP\t0.0\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="카드명 사전 SHA-256"):
            VersionedCorpusStore(root).load_active()


def test_card_dictionary_count_mismatch_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_generation(
            root,
            [{"chunk_id": "one", "text": "본문", "metadata": {}}],
            card_words=(("블루문카드", "NNP", 0.0),),
        )
        pointer_path = root / "active_index.json"
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        pointer["card_dictionary_count"] = 2
        pointer_path.write_text(json.dumps(pointer, ensure_ascii=False), encoding="utf-8")
        manifest_path = root / pointer["manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["card_dictionary"]["count"] = 2
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        with pytest.raises(ValueError, match="카드명 사전 항목 수"):
            VersionedCorpusStore(root).load_active()


def test_card_dictionary_manifest_mismatch_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        pointer = _write_generation(
            root,
            [{"chunk_id": "one", "text": "본문", "metadata": {}}],
            card_words=(("블루문카드", "NNP", 0.0),),
        )
        manifest_path = root / pointer["manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["card_dictionary"]["source"] = "untrusted"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        with pytest.raises(ValueError, match="manifest의 카드명 사전 정보"):
            VersionedCorpusStore(root).load_active()


def test_card_dictionary_path_cannot_escape_index_root() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "indexes"
        outside = Path(directory) / "outside.dict"
        outside.write_text("외부카드\tNNP\t0.0\n", encoding="utf-8")
        _write_generation(
            root,
            [{"chunk_id": "one", "text": "본문", "metadata": {}}],
            card_words=(("블루문카드", "NNP", 0.0),),
        )
        pointer_path = root / "active_index.json"
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        pointer["card_dictionary"] = "../outside.dict"
        pointer_path.write_text(json.dumps(pointer, ensure_ascii=False), encoding="utf-8")

        with pytest.raises(ValueError, match="루트 밖"):
            VersionedCorpusStore(root).load_active()


def test_tokenizer_signature_mismatch_keeps_previous_active_bundle() -> None:
    first_records = [
        {"chunk_id": "first", "text": "블루문카드 혜택", "metadata": {}}
    ]
    second_records = [
        {"chunk_id": "second", "text": "한빛 모아생활 혜택", "metadata": {}}
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_generation(
            root,
            first_records,
            generation="gen-first",
            card_words=(("블루문카드", "NNP", 0.0),),
        )
        index = BM25Index(VersionedCorpusStore(root), KoreanTokenizer())
        assert index.keyword_search("블루문카드", k=1)["first"] > 0
        first_signature = index.tokenizer.signature

        pointer = _write_generation(
            root,
            second_records,
            generation="gen-second",
            card_words=(("한빛 모아생활", "NNP", 0.0),),
        )
        manifest_path = root / pointer["manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tokenizer_signature"] = "kiwi:invalid"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        with pytest.raises(ValueError, match="토크나이저 서명"):
            index.warm()
        assert index._generation == "gen-first"
        assert index.tokenizer.signature == first_signature


def test_active_generation_switches_bm25_corpus_and_tokenizer_together() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _write_generation(
            root,
            [{"chunk_id": "first", "text": "블루문카드 혜택", "metadata": {}}],
            generation="gen-first",
            card_words=(("블루문카드", "NNP", 0.0),),
        )
        index = BM25Index(VersionedCorpusStore(root), KoreanTokenizer())
        assert set(index.chunks()) == {"first"}
        first_signature = index.tokenizer.signature

        _write_generation(
            root,
            [
                {
                    "chunk_id": "second",
                    "text": "한빛 모아생활 혜택",
                    "metadata": {},
                }
            ],
            generation="gen-second",
            card_words=(("한빛 모아생활", "NNP", 0.0),),
        )

        # 다른 요청이 새 버전을 준비하는 동안에는 완성된 기존 묶음으로 검색함.
        index._warm_lock.acquire()
        try:
            assert index.keyword_search("블루문카드", k=1)["first"] > 0
            assert index._generation == "gen-first"
            assert index.tokenizer.signature == first_signature
        finally:
            index._warm_lock.release()

        assert set(index.chunks()) == {"second"}
        assert index._generation == "gen-second"
        assert index.tokenizer.signature != first_signature
        assert "한빛모아생활" in index.tokenizer.tokenize("한빛 모아생활")


def test_original_and_typo_corrected_query_tokens_are_distinct() -> None:
    tokenizer = KoreanTokenizer(num_workers=1)

    result = tokenizer.tokenize_with_typo_fallback("혜텍이 뭐예요")

    assert "혜텍" in result.original
    assert "혜택" in result.corrected
    assert result.changed is True


def test_indexer_and_retriever_tokenizer_contracts_match() -> None:
    module_name = "indexer_korean_tokenizer_contract"
    module_path = (
        Path(__file__).resolve().parents[2]
        / "indexer"
        / "app"
        / "domain"
        / "korean_tokenizer.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    retriever_tokenizer = KoreanTokenizer(num_workers=1)
    indexer_tokenizer = module.KoreanTokenizer(num_workers=1)
    samples = [
        "귀여워요",
        "귀엽다",
        "연회비가 없어요",
        "해외결제수수료 K-패스 10만원",
    ]

    assert retriever_tokenizer.signature == indexer_tokenizer.signature
    assert retriever_tokenizer.tokenize_many(samples) == indexer_tokenizer.tokenize_many(samples)
