"""PreparedChunk 목록을 기존 Retriever가 읽는 corpus·BM25 형식으로 만드는 어댑터임."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Iterable
from uuid import uuid4

from app.domain.models import PreparedChunk
from app.infrastructure.korean_tokenizer import KoreanTokenizer, normalize_korean_text


def _json_bytes(value: Any) -> bytes:
    """키 순서와 공백에 영향을 받지 않는 해시용 JSON 바이트를 만듦."""

    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _replace_bytes(path: Path, payload: bytes) -> None:
    """같은 디렉터리의 임시 파일을 fsync한 뒤 대상 파일을 원자적으로 교체함."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("심볼릭 링크에는 색인 파일을 저장할 수 없습니다.")
    descriptor, temporary = tempfile.mkstemp(prefix=".index-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _replace_json(path: Path, value: Any) -> None:
    """사람이 읽을 수 있는 UTF-8 JSON을 원자적으로 저장함."""

    _replace_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _file_sha256(path: Path) -> str:
    """파일 내용을 순서대로 읽어 SHA-256 해시를 계산함."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _directory_sha256(path: Path) -> str:
    """디렉터리의 상대 경로와 파일 내용을 묶은 안정적인 SHA-256 해시를 계산함."""

    files = sorted(candidate for candidate in path.rglob("*") if candidate.is_file())
    if not files:
        raise ValueError("BM25 색인 디렉터리가 비어 있습니다.")
    digest = hashlib.sha256()
    for candidate in files:
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with candidate.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def _resolve_descendant(root: Path, relative: str, *, directory: bool) -> Path:
    """검색 포인터의 상대 경로가 루트 안의 실제 파일 또는 디렉터리인지 확인함."""

    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("텍스트 색인 포인터가 검색 루트 밖을 가리킵니다.")
    exists = path.is_dir() if directory else path.is_file()
    if not exists:
        raise FileNotFoundError(f"텍스트 색인 산출물이 없습니다: {relative}")
    return path


def corpus_record(chunk: PreparedChunk) -> dict[str, Any]:
    """Retriever corpus 형식에 청크와 무결성 해시를 담아 반환함.

    반환값: 본문·메타데이터·토큰 수와 본문·메타데이터·전체 내용 해시를 가진 레코드임.
    부수효과: 없음.
    """

    metadata = {**dict(chunk.metadata), "chunk_id": chunk.chunk_id}
    value = {"chunk_id": chunk.chunk_id, "text": chunk.text, "metadata": metadata}
    return {
        **value,
        "token_count": int(chunk.token_count),
        "text_hash": chunk.text_hash,
        "metadata_hash": chunk.metadata_hash,
        "content_hash": hashlib.sha256(_json_bytes(value)).hexdigest(),
    }


def _metadata_values(metadata: dict[str, Any], plural_key: str, single_key: str) -> list[str]:
    """복수 키를 우선해 문자열·JSON 문자열·목록 값을 문자열 목록으로 통일함."""

    value = metadata.get(plural_key)
    if value in (None, ""):
        value = metadata.get(single_key)
    if value in (None, ""):
        return []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError as error:
                raise ValueError(f"{plural_key} JSON 형식이 올바르지 않습니다.") from error
            value = decoded
        else:
            value = [text]
    elif not isinstance(value, (list, tuple)):
        value = [value]
    return [str(item).strip() for item in value if str(item).strip()]


def _card_dictionary_words(records: Iterable[dict[str, Any]]) -> tuple[tuple[str, str, float], ...]:
    """D2 메타데이터에서 카드명 사용자 사전 항목을 안정적인 순서로 만듦.

    카드 ID와 이름의 대응이 모호하면 잘못된 검색어가 등록되지 않도록 ValueError를 발생시킴.
    """

    names_by_id: dict[str, str] = {}
    for row in records:
        metadata = dict(row.get("metadata") or {})
        if (
            str(metadata.get("doc_key", "")).strip() != "D2"
            and str(metadata.get("doc_type", "")).strip() != "benefit_guide"
        ):
            continue
        card_ids = _metadata_values(metadata, "card_id_all", "card_id")
        card_names = _metadata_values(metadata, "card_name_all", "card_name")
        if not card_ids and not card_names:
            continue
        if len(card_ids) != len(card_names):
            raise ValueError("D2 card_id와 card_name 목록 길이가 일치하지 않습니다.")
        for card_id, raw_name in zip(card_ids, card_names, strict=True):
            card_name = " ".join(normalize_korean_text(raw_name).split())
            previous = names_by_id.get(card_id)
            if previous is not None and previous != card_name:
                raise ValueError(f"같은 card_id에 서로 다른 카드명이 있습니다: {card_id}")
            names_by_id[card_id] = card_name
    return tuple((name, "NNP", 0.0) for name in sorted(set(names_by_id.values())))


class LexicalIndexBuilder:
    """Kiwi 토큰과 BM25S 파일을 한 검색 세대로 생성함.

    토크나이저와 BM25 생성자를 주입받으며, Chroma 저장이나 전역 활성 세대 전환은 수행하지 않음.
    """

    def __init__(
        self,
        *,
        user_dictionary: Path | None = None,
        tokenizer_workers: int = 1,
        k1: float = 1.5,
        b: float = 0.75,
        oov_candidates: bool = False,
        tokenizer_factory: Callable[..., KoreanTokenizer] = KoreanTokenizer,
        bm25_factory: Callable[..., Any] | None = None,
    ) -> None:
        """사용자 사전, 토큰화 작업자 수와 BM25 매개변수를 설정함.

        인자: k1은 양수, b는 0보다 크고 1 이하여야 함.
        예외: 작업자 수 또는 BM25 매개변수 범위가 잘못되면 ValueError를 발생시킴.
        부수효과: 없음.
        """

        if tokenizer_workers <= 0 or k1 <= 0 or not 0 < b <= 1:
            raise ValueError("BM25 토크나이저 작업자 수와 k1·b 설정이 올바르지 않습니다.")
        self.user_dictionary = user_dictionary
        self.tokenizer_workers = int(tokenizer_workers)
        self.k1 = float(k1)
        self.b = float(b)
        self.oov_candidates = bool(oov_candidates)
        self.tokenizer_factory = tokenizer_factory
        self.bm25_factory = bm25_factory

    def _new_bm25(self) -> Any:
        """주입된 생성자 또는 Lucene 방식 bm25s 인스턴스를 만듦."""

        if self.bm25_factory is not None:
            return self.bm25_factory(k1=self.k1, b=self.b, method="lucene")
        try:
            import bm25s
        except ImportError as error:
            raise RuntimeError("BM25 색인을 만들려면 bm25s가 필요합니다.") from error
        return bm25s.BM25(k1=self.k1, b=self.b, method="lucene")

    def build(
        self,
        *,
        search_root: Path,
        generation: str,
        chunks: list[PreparedChunk],
        collection: str,
        embedding_signature: str,
        manifest: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """corpus·카드 사전·BM25·manifest를 임시 루트에서 완성한 뒤 승격함.

        목적: 저장 중 중단된 BM25 파일이 재시도 결과와 섞이거나 게시 대상으로 오인되지 않도록 함.
        방법: 형제 임시 디렉터리에서 전체 산출물을 검증하고, 완성된 검색 루트만 최종 위치로 승격함.
        인자: chunks는 비어 있지 않고 chunk_id가 서로 달라야 함.
        반환값: 활성 검색 포인터와 실제 토큰화·BM25 계약이 합쳐진 manifest임.
        예외: 청크·메타데이터·토큰 수 계약이 어긋나거나 색인 저장에 실패하면 예외를 발생시킴.
        부수효과: search_root를 완성된 텍스트 색인 파일 묶음으로 만들거나 같은 입력의 기존 묶음을 재사용함.
        """

        if not chunks:
            raise ValueError("빈 청크 목록은 검색 세대로 발행할 수 없습니다.")
        records = sorted((corpus_record(chunk) for chunk in chunks), key=lambda row: row["chunk_id"])
        if len({row["chunk_id"] for row in records}) != len(records):
            raise ValueError("중복 chunk_id가 있습니다.")

        source_manifest_sha256 = hashlib.sha256(_json_bytes(manifest)).hexdigest()
        corpus_payload = "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in records
        ).encode("utf-8")
        corpus_hash = hashlib.sha256(corpus_payload).hexdigest()
        search_root = Path(search_root).resolve()
        if search_root.exists():
            try:
                pointer, existing_manifest, stage = self.verify(
                    search_root=search_root,
                    generation=generation,
                )
            except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
            else:
                if (
                    stage["chunk_count"] == len(records)
                    and stage["corpus_sha256"] == corpus_hash
                    and existing_manifest.get("source_manifest_sha256") == source_manifest_sha256
                    and existing_manifest.get("vector", {}).get("collection") == collection
                    and existing_manifest.get("vector", {}).get("embedding_signature")
                    == embedding_signature
                ):
                    return pointer, existing_manifest

        search_root.parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(prefix=f".{search_root.name}-stage-", dir=search_root.parent)
        )
        previous_root: Path | None = None
        try:
            pointer, final_manifest = self._build_into(
                search_root=temporary_root,
                generation=generation,
                records=records,
                corpus_payload=corpus_payload,
                corpus_hash=corpus_hash,
                collection=collection,
                embedding_signature=embedding_signature,
                manifest=manifest,
                source_manifest_sha256=source_manifest_sha256,
            )
            self.verify(search_root=temporary_root, generation=generation)
            if search_root.exists():
                # Windows는 비어 있지 않은 디렉터리를 os.replace로 덮을 수 없어 기존 루트를 먼저 치움.
                # 최종 루트는 게시 전 비공개이므로 중단되어도 기존 활성 세대에는 영향이 없음.
                previous_root = search_root.with_name(
                    f".{search_root.name}-previous-{uuid4().hex}"
                )
                os.replace(search_root, previous_root)
            os.replace(temporary_root, search_root)
            if previous_root is not None:
                shutil.rmtree(previous_root, ignore_errors=True)
            return pointer, final_manifest
        finally:
            if temporary_root.exists():
                shutil.rmtree(temporary_root, ignore_errors=True)

    def _build_into(
        self,
        *,
        search_root: Path,
        generation: str,
        records: list[dict[str, Any]],
        corpus_payload: bytes,
        corpus_hash: str,
        collection: str,
        embedding_signature: str,
        manifest: dict[str, Any],
        source_manifest_sha256: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """한 임시 검색 루트 안에 텍스트 색인 산출물 전체를 생성함."""

        words = _card_dictionary_words(records)
        card_payload = KoreanTokenizer.additional_user_words_payload(words)
        card_hash = hashlib.sha256(card_payload).hexdigest()
        tokenizer = self.tokenizer_factory(
            self.user_dictionary,
            additional_user_words=words,
            num_workers=self.tokenizer_workers,
        )
        texts = [str(row["text"]) for row in records]
        tokens = tokenizer.tokenize_many(texts)
        if len(tokens) != len(records):
            raise ValueError("BM25 토큰 목록과 corpus 행 수가 일치하지 않습니다.")
        oov_values = tokenizer.extract_oov_candidates(texts) if self.oov_candidates else []

        relative_root = Path("generations") / generation
        generation_dir = search_root / relative_root
        bm25_dir = generation_dir / "bm25"
        _replace_bytes(generation_dir / "corpus.jsonl", corpus_payload)
        _replace_bytes(generation_dir / "card_names.dict", card_payload)
        _replace_json(
            generation_dir / "oov_candidates.json",
            {
                "policy": "human-review-required-v1" if self.oov_candidates else "disabled-by-default-v1",
                "auto_registered": False,
                "candidates": [asdict(value) for value in oov_values],
            },
        )

        bm25 = self._new_bm25()
        bm25.index(tokens, show_progress=False)
        scores = getattr(bm25, "scores", None)
        indexed_count = scores.get("num_docs") if isinstance(scores, dict) else None
        if indexed_count is not None and int(indexed_count) != len(records):
            raise ValueError("BM25 색인 문서 수가 corpus 행 수와 일치하지 않습니다.")
        bm25.save(bm25_dir, show_progress=False)
        try:
            bm25_version = importlib.metadata.version("bm25s")
        except importlib.metadata.PackageNotFoundError:
            bm25_version = "injected"

        relative_card = relative_root / "card_names.dict"
        final_manifest = {
            **dict(manifest),
            "format_version": 2,
            "generation": generation,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_manifest_sha256": source_manifest_sha256,
            "corpus_sha256": corpus_hash,
            "chunk_count": len(records),
            "tokenizer_signature": tokenizer.signature,
            "user_dictionary_sha256": tokenizer.user_dictionary_sha256,
            "card_dictionary": {
                "path": relative_card.as_posix(),
                "sha256": card_hash,
                "count": len(words),
                "source": "D2.metadata.card_name",
                "tag": "NNP",
                "score": 0.0,
            },
            "oov_candidate_count": len(oov_values),
            "bm25": {
                "implementation": "bm25s",
                "version": bm25_version,
                "method": "lucene",
                "k1": self.k1,
                "b": self.b,
            },
            "vector": {
                **dict(manifest.get("vector") or {}),
                "collection": collection,
                "embedding_signature": embedding_signature,
            },
        }
        _replace_json(generation_dir / "manifest.json", final_manifest)
        pointer = {
            "format_version": 1,
            "generation": generation,
            "manifest": (relative_root / "manifest.json").as_posix(),
            "corpus": (relative_root / "corpus.jsonl").as_posix(),
            "bm25": (relative_root / "bm25").as_posix(),
            "oov_candidates": (relative_root / "oov_candidates.json").as_posix(),
            "card_dictionary": relative_card.as_posix(),
            "card_dictionary_sha256": card_hash,
            "card_dictionary_count": len(words),
            "corpus_sha256": corpus_hash,
            "chunk_count": len(records),
        }
        # 검색 포인터는 모든 세대 산출물과 manifest가 저장된 뒤 교체해야 부분 색인이 노출되지 않음.
        _replace_json(search_root / "active_index.json", pointer)
        return pointer, final_manifest

    def verify(
        self,
        *,
        search_root: Path,
        generation: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """완성된 텍스트 색인의 경로·건수·해시가 서로 일치하는지 검증함.

        인자: search_root는 해당 Chroma 세대 안의 비공개 텍스트 색인 루트여야 함.
        반환값: 검색 포인터, manifest, 체크포인트에 저장할 내용 해시 묶음임.
        예외: 경로 이탈·파일 누락·세대·건수·해시 불일치가 있으면 예외를 발생시킴.
        부수효과: 색인 파일을 읽지만 변경하지 않음.
        """

        search_root = Path(search_root).resolve()
        pointer_path = search_root / "active_index.json"
        if not pointer_path.is_file():
            raise FileNotFoundError("텍스트 색인 포인터가 없습니다.")
        pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
        if str(pointer.get("generation")) != generation:
            raise ValueError("텍스트 색인 포인터의 generation이 대상 세대와 다릅니다.")

        manifest_path = _resolve_descendant(search_root, str(pointer["manifest"]), directory=False)
        corpus_path = _resolve_descendant(search_root, str(pointer["corpus"]), directory=False)
        bm25_path = _resolve_descendant(search_root, str(pointer["bm25"]), directory=True)
        oov_path = _resolve_descendant(search_root, str(pointer["oov_candidates"]), directory=False)
        card_path = _resolve_descendant(search_root, str(pointer["card_dictionary"]), directory=False)
        del oov_path  # 파일 존재와 경로 범위 확인만 필요함.

        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
        corpus_hash = _file_sha256(corpus_path)
        card_hash = _file_sha256(card_path)
        chunk_count = sum(1 for line in corpus_path.read_bytes().splitlines() if line.strip())
        expected_count = int(pointer["chunk_count"])
        if str(manifest.get("generation")) != generation:
            raise ValueError("텍스트 색인 manifest의 generation이 대상 세대와 다릅니다.")
        if int(manifest.get("chunk_count", -1)) != expected_count or chunk_count != expected_count:
            raise ValueError("텍스트 색인의 청크 수가 포인터·manifest·corpus에서 일치하지 않습니다.")
        if pointer.get("corpus_sha256") != corpus_hash or manifest.get("corpus_sha256") != corpus_hash:
            raise ValueError("텍스트 색인의 corpus 해시가 일치하지 않습니다.")
        if pointer.get("card_dictionary_sha256") != card_hash:
            raise ValueError("텍스트 색인의 카드 사전 해시가 일치하지 않습니다.")
        if manifest.get("card_dictionary", {}).get("sha256") != card_hash:
            raise ValueError("텍스트 색인 manifest의 카드 사전 해시가 일치하지 않습니다.")

        stage = {
            "generation": generation,
            "chunk_count": expected_count,
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "corpus_sha256": corpus_hash,
            "bm25_sha256": _directory_sha256(bm25_path),
            "search_pointer_sha256": _file_sha256(pointer_path),
        }
        return pointer, manifest, stage


__all__ = ["LexicalIndexBuilder", "corpus_record"]
