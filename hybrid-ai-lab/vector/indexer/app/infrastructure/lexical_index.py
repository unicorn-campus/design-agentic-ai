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

    # 목적: D2 카드명을 검색할 때 하나의 고유명사로 인식하도록 버전별 자동 사용자 사전을 준비함.
    # 처리:
    # 1. 최종 원문 목록의 D2 메타데이터에서 card_id와 card_name을 수집하고 이름을 정규화함.
    # 2. 중복을 제거하고 정렬한 카드명을 NNP·점수 0.0 항목으로 만들어, 같은 입력은 항상 같은 순서로 구성함.
    # 3. 카드명 항목을 고정된 형식의 바이트로 직렬화함. 이 값은 아래에서 card_names.dict로 저장됨.
    # 4. 바이트의 SHA-256을 계산함. 이 해시는 manifest와 active_index.json에 기록되어 파일 무결성 검증에 쓰임.
    # 5. 운영자가 관리하는 외부 사전은 수정하지 않고, 자동 카드명 항목을 추가 입력으로 함께 적용해 토크나이저를 만듦.
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

    # 목적: 최종 원문 목록을 BM25S가 사용할 토큰 목록으로 바꾸고, 검토할 미등록어 후보를 찾음.
    # 처리:
    # 1. records의 현재 순서를 바꾸지 않고 각 청크의 본문을 문자열로 꺼내 texts를 만듦.
    # 2. 기본 사용자 사전과 자동 카드명 사전이 적용된 tokenizer로 전체 본문을 한 번에 분석함.
    # 3. 생성된 tokens는 BM25S 색인 입력으로 사용되며, records와 같은 순서를 유지함.
    #    이후 같은 records를 corpus.jsonl로 저장하므로 BM25의 위치 번호와 원문 목록의 위치가 일치함.
    # 4. 같은 본문에서 최소 출현 횟수와 최소 품질 점수를 모두 만족하는 미등록어(OOV) 후보를 추출함.
    # 5. OOV 후보는 이후 검토용 JSON에만 저장하며, 현재 tokenizer나 BM25 색인에는 자동으로 반영하지 않음.
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

    # 목적: 토큰화된 전체 문서로 BM25S 역색인을 만들고 Retriever 서비스가 읽을 검색 파일로 저장함.
    # 역할: retriever는 BM25 설정을 가진 색인 생성·검색 객체이며, 이 위치에서는 색인 생성기로 사용함.
    # 처리:
    # 1. k1은 단어 반복 출현의 점수 포화 정도, b는 문서 길이 보정 정도를 정함.
    #    method="lucene"은 이 두 값을 Lucene 방식의 BM25 점수 계산에 사용하도록 지정함.
    # 2. index(tokens)는 문서별 토큰에서 단어가 나온 문서 위치를 찾는 역색인과 점수 계산용 통계를 만듦.
    # 3. save()는 완성된 BM25S 검색 파일을 bm25_dir에 저장하며 원문 본문은 그 안에 중복 저장하지 않음.
    # 4. 원문은 같은 순서의 generation/corpus.jsonl 하나로 별도 저장함.
    #    Retriever 서비스는 BM25S를 load_corpus=False로 읽고 검색 결과 위치를 외부 원문 목록과 결합함.
    retriever = bm25s.BM25(k1=k1, b=b, method="lucene")
    retriever.index(tokens, show_progress=False)
    retriever.save(bm25_dir, show_progress=False)

    # 목적: 새 검색 버전의 원문·토크나이저·사전·BM25·Vector 연결 정보를 manifest 파일 하나에 기록함.
    # 처리:
    # 1. 사전 경로는 SEARCH_INDEX_ROOT 기준의 상대 경로로 기록해, 루트 폴더를 옮겨도 같은 구조로 찾게 함.
    # 2. format_version·generation·created_at에는 manifest 형식, 검색 버전 이름, 생성 시각을 기록함.
    # 3. corpus_sha256·chunk_count에는 원문 목록의 해시와 청크 수를 기록함.
    # 4. tokenizer_signature에는 토큰화 정책과 사전 구성을 합친 식별값을 기록함.
    #    user_dictionary_sha256은 운영자가 제공한 외부 사용자 사전의 해시임.
    # 5. card_dictionary에는 D2에서 자동 생성한 카드명 사전의 경로·해시·항목 수·생성 정책을 기록함.
    # 6. oov_candidate_count에는 검토용 미등록어 후보 수를 기록함.
    # 7. bm25에는 BM25S 구현 버전, Lucene 계산 방식, k1·b 점수 설정을 기록함.
    # 8. vector에는 함께 검색할 Vector DB 컬렉션 이름과 임베딩 설정 식별값을 기록함.
    # 9. Retriever는 실제 원문·카드명 사전·토크나이저·BM25 문서 수를 일부 manifest 값과 대조함.
    #    BM25 세부 설정과 Vector 정보 등 나머지 값은 버전 구성을 추적하고 문제를 확인하는 근거로 남김.
    # 10. manifest.json을 버전 폴더에 먼저 저장한 뒤 아래에서 active_index.json을 마지막에 교체함.
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

    # 목적: Retriever가 사용할 현재 검색 버전을 한 번에 선택하도록 active_index.json 포인터를 만듦.
    #       포인터는 검색 자료 자체가 아니라 활성 버전의 위치와 검증값만 담는 작은 JSON 파일임.
    # 처리:
    # 1. format_version은 포인터 형식, generation은 현재 활성화할 검색 버전 이름을 나타냄.
    # 2. manifest·corpus·bm25·oov_candidates·card_dictionary에는 해당 버전 산출물의 경로를 기록함.
    # 3. card_dictionary_sha256·card_dictionary_count는 자동 카드명 사전의 내용과 항목 수 검증값임.
    # 4. corpus_sha256·chunk_count는 원문 목록의 내용과 청크 수 검증값임.
    # 5. 모든 경로는 SEARCH_INDEX_ROOT 기준 상대 경로이며, Retriever는 루트 밖을 가리키는 경로를 거부함.
    # 6. Retriever는 이 파일에서 시작해 같은 버전의 manifest·원문·BM25·카드명 사전을 읽음.
    #    원문과 카드명 사전의 해시·개수, 토크나이저 설정, BM25 문서 수를 확인한 뒤 검색에 사용함.
    # 7. 모든 버전 파일을 먼저 저장한 뒤 이 포인터를 마지막에 교체해 작성 중인 버전이 노출되지 않게 함.
    #    FileStore는 임시 파일을 디스크에 기록한 후 os.replace()로 포인터를 원자적으로 교체함.
    # 8. 기존 버전 폴더는 삭제하지 않고 그대로 두며, 포인터만 새 버전을 가리키도록 바꿈.
    pointer = {
        "format_version": 1,
        "generation": generation,
        "manifest": (relative_root / "manifest.json").as_posix(),  # Windows에서도 / 구분자의 경로 문자열로 저장함
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
