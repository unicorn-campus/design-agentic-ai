"""검증된 청크 스냅샷과 BM25S 색인을 세대 단위로 발행함."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from app.domain.korean_tokenizer import KoreanTokenizer, normalize_korean_text


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def corpus_record(document: Any) -> dict[str, Any]:
    """LangChain Document를 벡터 DB와 독립적인 청크 레코드로 변환함."""

    chunk_id = str(document.id)
    text = str(document.page_content)
    metadata = dict(document.metadata)
    content_hash = hashlib.sha256(
        _json_bytes({"chunk_id": chunk_id, "text": text, "metadata": metadata})
    ).hexdigest()
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": metadata,
        "content_hash": content_hash,
    }


def _active_records(index_root: Path) -> list[dict[str, Any]]:
    pointer_path = index_root / "active_index.json"
    if not pointer_path.exists():
        return []
    pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
    relative = Path(str(pointer.get("corpus", "")))
    corpus_path = (index_root / relative).resolve()
    if not corpus_path.is_relative_to(index_root.resolve()) or not corpus_path.is_file():
        raise ValueError("활성 corpus 경로가 검색 색인 루트 밖이거나 존재하지 않음")
    return [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _merge_records(
    index_root: Path,
    current: list[dict[str, Any]],
    *,
    full_snapshot: bool,
) -> list[dict[str, Any]]:
    if full_snapshot:
        return sorted(current, key=lambda row: row["chunk_id"])
    merged = {row["chunk_id"]: row for row in _active_records(index_root)}
    merged.update({row["chunk_id"]: row for row in current})
    return sorted(merged.values(), key=lambda row: row["chunk_id"])


def _card_dictionary_words(
    records: Iterable[dict[str, Any]],
) -> tuple[tuple[str, str, float], ...]:
    """검증된 D2 메타데이터에서 결정적인 카드명 사전 항목을 만듦."""

    names_by_id: dict[str, str] = {}
    for row in records:
        metadata = dict(row.get("metadata") or {})
        if str(metadata.get("doc_key", "")).strip() != "D2":
            continue
        card_id = str(metadata.get("card_id", "")).strip()
        card_name = " ".join(
            normalize_korean_text(str(metadata.get("card_name", ""))).split()
        )
        if not card_id or not card_name:
            continue
        previous = names_by_id.get(card_id)
        if previous is not None and previous != card_name:
            raise ValueError(
                f"같은 card_id에 서로 다른 카드명이 있음: {card_id} "
                f"({previous!r}, {card_name!r})"
            )
        names_by_id[card_id] = card_name

    return tuple((name, "NNP", 0.0) for name in sorted(set(names_by_id.values())))


def publish_search_index(
    *,
    index_root: Path,
    documents: Iterable[Any],
    vector_ids: Iterable[str],
    full_snapshot: bool,
    file_store: Any,
    user_dictionary: Path | None = None,
    tokenizer_workers: int = 1,
    oov_min_count: int = 10,
    oov_min_score: float = 0.25,
    k1: float = 1.5,
    b: float = 0.75,
    vector_collection: str,
    embedding_signature: str,
) -> dict[str, Any]:
    """완성된 세대를 쓴 뒤 활성 포인터를 마지막에 원자적으로 교체함."""

    try:
        import bm25s
    except ImportError as error:  # pragma: no cover - 설치 오류 안내 경로
        raise RuntimeError("BM25 색인을 만들려면 bm25s가 필요함") from error

    index_root = Path(index_root)
    current = [corpus_record(document) for document in documents]
    records = _merge_records(index_root, current, full_snapshot=full_snapshot)
    corpus_ids = {str(row["chunk_id"]) for row in records}
    actual_vector_ids = {str(chunk_id) for chunk_id in vector_ids}
    if corpus_ids != actual_vector_ids:
        missing = sorted(actual_vector_ids - corpus_ids)[:5]
        extra = sorted(corpus_ids - actual_vector_ids)[:5]
        raise ValueError(
            "corpus와 Vector DB의 청크 ID가 일치하지 않음. "
            f"corpus 누락={missing}, corpus 초과={extra}; --full-reindex 실행 필요"
        )
    if not records:
        raise ValueError("빈 corpus는 활성 검색 색인으로 발행할 수 없음")

    card_dictionary_words = _card_dictionary_words(records)
    card_dictionary_payload = KoreanTokenizer.additional_user_words_payload(
        card_dictionary_words
    )
    card_dictionary_sha256 = hashlib.sha256(card_dictionary_payload).hexdigest()
    tokenizer = KoreanTokenizer(
        user_dictionary,
        additional_user_words=card_dictionary_words,
        num_workers=tokenizer_workers,
    )
    texts = [str(row["text"]) for row in records]
    tokens = tokenizer.tokenize_many(texts)
    oov_candidates = tokenizer.extract_oov_candidates(
        texts,
        min_cnt=oov_min_count,
        min_score=oov_min_score,
    )
    # FileStore.save_jsonl()과 동일한 직렬화로 파일 해시를 미리 계산함.
    corpus_payload = "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in records
    ).encode("utf-8")
    corpus_sha256 = hashlib.sha256(corpus_payload).hexdigest()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    generation = f"gen-{timestamp}-{corpus_sha256[:12]}"
    generation_dir = index_root / "generations" / generation
    bm25_dir = generation_dir / "bm25"
    card_dictionary_path = generation_dir / "card_names.dict"

    file_store.save_jsonl(generation_dir / "corpus.jsonl", records)
    card_dictionary_path.write_bytes(card_dictionary_payload)
    file_store.save_json(
        generation_dir / "oov_candidates.json",
        {
            "policy": "human-review-required-v1",
            "auto_registered": False,
            "min_count": oov_min_count,
            "min_score": oov_min_score,
            "candidates": [
                {
                    **asdict(candidate),
                    "examples": [
                        {
                            "chunk_id": str(row["chunk_id"]),
                            "text": str(row["text"])[:160],
                        }
                        for row in records
                        if candidate.form in normalize_korean_text(str(row["text"]))
                    ][:3],
                }
                for candidate in oov_candidates
            ],
        },
    )
    retriever = bm25s.BM25(k1=k1, b=b, method="lucene")
    retriever.index(tokens, show_progress=False)
    # canonical corpus는 generation/corpus.jsonl 하나만 유지함. BM25S에는
    # 위치 기반 역색인만 저장하고 조회 시 같은 순서의 외부 corpus를 결합함.
    retriever.save(bm25_dir, show_progress=False)

    relative_root = Path("generations") / generation
    relative_card_dictionary = relative_root / "card_names.dict"
    manifest = {
        "format_version": 1,
        "generation": generation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus_sha256,
        "chunk_count": len(records),
        "tokenizer_signature": tokenizer.signature,
        "user_dictionary_sha256": tokenizer.user_dictionary_sha256,
        "card_dictionary": {
            "path": relative_card_dictionary.as_posix(),
            "sha256": card_dictionary_sha256,
            "count": len(card_dictionary_words),
            "source": "D2.metadata.card_name",
            "tag": "NNP",
            "score": 0.0,
        },
        "oov_candidate_count": len(oov_candidates),
        "bm25": {
            "implementation": "bm25s",
            "version": str(getattr(bm25s, "__version__", "unknown")),
            "method": "lucene",
            "k1": k1,
            "b": b,
        },
        "vector": {
            "collection": vector_collection,
            "embedding_signature": embedding_signature,
        },
    }
    file_store.save_json(generation_dir / "manifest.json", manifest)

    pointer = {
        "format_version": 1,
        "generation": generation,
        "manifest": (relative_root / "manifest.json").as_posix(),
        "corpus": (relative_root / "corpus.jsonl").as_posix(),
        "bm25": (relative_root / "bm25").as_posix(),
        "oov_candidates": (relative_root / "oov_candidates.json").as_posix(),
        "card_dictionary": relative_card_dictionary.as_posix(),
        "card_dictionary_sha256": card_dictionary_sha256,
        "card_dictionary_count": len(card_dictionary_words),
        "corpus_sha256": corpus_sha256,
        "chunk_count": len(records),
    }
    file_store.save_json(index_root / "active_index.json", pointer)
    return pointer
