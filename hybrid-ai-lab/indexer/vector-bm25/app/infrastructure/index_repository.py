"""Chroma와 BM25를 같은 세대로 준비한 뒤 단일 포인터로 활성화하는 저장소 어댑터임."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable

from app.application.ports import IndexRepositoryPort
from app.domain.models import IndexSnapshot, PreparedChunk, Publication
from app.infrastructure.file_lock import CrossPlatformFileLock
from app.infrastructure.lexical_index import LexicalIndexBuilder


_GENERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PRIMITIVES = (str, int, float, bool)


def _canonical_hash(value: Any) -> str:
    """키 순서와 JSON 공백에 영향을 받지 않는 SHA-256 해시를 계산함."""

    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _text_hash(text: str) -> str:
    """UTF-8 본문의 SHA-256 해시를 계산함."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_metadata(metadata: dict[str, Any], chunk_id: str) -> dict[str, str | int | float | bool]:
    """Chroma가 저장할 수 있도록 메타데이터를 원시값 또는 안정적인 JSON 문자열로 바꿈."""

    clean: dict[str, str | int | float | bool] = {}
    for key, value in {**metadata, "chunk_id": chunk_id}.items():
        if value is None:
            continue
        if isinstance(value, _PRIMITIVES):
            clean[str(key)] = value
        else:
            clean[str(key)] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return clean


def _replace_json(path: Path, value: Any) -> None:
    """같은 디렉터리의 임시 파일을 fsync한 뒤 JSON 파일을 원자적으로 교체함."""

    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".generation-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class GenerationIndexRepository(IndexRepositoryPort):
    """새 세대만 수정하고 활성 세대는 publish 마지막 순간에 교체함.

    데이터 루트·BM25 빌더·Chroma 생성자를 주입받으며, 문서 로딩·청킹·임베딩은 수행하지 않음.
    """

    def __init__(
        self,
        data_root: Path,
        *,
        collection: str = "card_docs",
        lexical_builder: LexicalIndexBuilder | None = None,
        chroma_client_factory: Callable[..., Any] | None = None,
        lock_path: Path | None = None,
    ) -> None:
        """세대 저장 경로와 벡터·BM25 어댑터 구성을 설정함.

        인자: lock_path는 활성 세대 포인터 교체만 보호하는 프로세스 간 잠금 파일 경로임.
        부수효과: data_root 디렉터리가 없으면 생성함.
        """

        self.data_root = Path(data_root).resolve()
        self.collection = str(collection)
        self.lexical_builder = lexical_builder or LexicalIndexBuilder()
        self._client_factory = chroma_client_factory
        # LangGraph가 publish 노드를 호출 스레드와 다른 스레드에서 실행할 수 있어 별도 잠금이 필요함.
        # 전체 실행용 .writer.lock과 분리하여 포인터 교체 구간만 짧게 직렬화함.
        self.lock_path = Path(lock_path or self.data_root / ".publish.lock").resolve()
        self._clients: dict[str, Any] = {}
        self._collections: dict[str, Any] = {}
        self._signatures: dict[str, str] = {}
        self.data_root.mkdir(parents=True, exist_ok=True)

    @property
    def active_pointer_path(self) -> Path:
        """현재 활성 벡터·BM25 세대를 가리키는 포인터 파일 경로를 반환함."""

        return self.data_root / "active_generation.json"

    def _generation_dir(self, generation: str) -> Path:
        """경로 이탈을 막도록 세대 이름과 data_root 내부 경로를 검증함."""

        if not _GENERATION.fullmatch(str(generation)) or generation in {".", ".."}:
            raise ValueError("generation 형식이 올바르지 않습니다.")
        path = (self.data_root / "generations" / generation).resolve()
        if not path.is_relative_to(self.data_root):
            raise ValueError("generation 경로가 data 루트 밖을 가리킵니다.")
        return path

    def _new_client(self, path: Path) -> Any:
        """주입된 생성자 또는 지정 경로의 영속 Chroma 클라이언트를 만듦."""

        if self._client_factory is not None:
            return self._client_factory(path=path)
        import chromadb

        return chromadb.PersistentClient(path=str(path))

    def _open(self, generation: str, signature: str | None = None) -> Any:
        """준비된 세대의 cosine 컬렉션을 열고 실행 중 캐시에 보관함."""

        if generation in self._collections:
            return self._collections[generation]
        generation_dir = self._generation_dir(generation)
        state_path = generation_dir / "generation_state.json"
        if not state_path.is_file():
            raise ValueError(f"시작되지 않은 generation입니다: {generation}")
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        stored_signature = str(state["embedding_signature"])
        if signature is not None and stored_signature != signature:
            raise ValueError("generation 임베딩 서명이 기존 준비 상태와 다릅니다.")
        client = self._new_client(generation_dir / "chroma")
        collection = client.get_or_create_collection(
            name=self.collection,
            metadata={
                "embedding_model_signature": stored_signature,
                "hnsw:space": "cosine",
            },
            configuration={"hnsw": {"space": "cosine"}},
        )
        self._clients[generation] = client
        self._collections[generation] = collection
        self._signatures[generation] = stored_signature
        return collection

    def begin(self, generation: str, embedding_signature: str) -> None:
        """활성 세대를 건드리지 않고 새 세대의 Chroma 준비 상태를 만듦.

        인자: generation은 영문·숫자로 시작하는 128자 이하 안전 이름이어야 함.
        예외: 같은 세대를 다른 임베딩 서명으로 재사용하면 ValueError를 발생시킴.
        부수효과: 새 세대 디렉터리·상태 파일·Chroma 컬렉션을 생성함.
        """

        generation_dir = self._generation_dir(generation)
        state_path = generation_dir / "generation_state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8-sig"))
            if str(state.get("embedding_signature")) != embedding_signature:
                raise ValueError("같은 generation을 다른 임베딩 서명으로 재사용할 수 없습니다.")
        else:
            # 디렉터리 생성 직후 프로세스가 종료되어도 같은 세대 재시도가 상태 파일을 복구할 수 있어야 함.
            generation_dir.mkdir(parents=True, exist_ok=True)
            _replace_json(
                state_path,
                {
                    "generation": generation,
                    "embedding_signature": embedding_signature,
                    "collection": self.collection,
                    "base_generation": (self._active_pointer() or {}).get("generation"),
                    "status": "building",
                },
            )
        self._open(generation, embedding_signature)

    def upsert(
        self,
        generation: str,
        chunks: list[PreparedChunk],
        vectors: list[list[float]],
    ) -> None:
        """검증한 청크·벡터 배치를 아직 활성화되지 않은 세대에 저장함.

        인자: 청크와 벡터 행 수가 같고 ID가 중복되지 않으며 벡터 차원이 일정해야 함.
        예외: 입력 계약 위반 시 ValueError를, Chroma 저장 실패 시 어댑터 예외를 발생시킴.
        부수효과: 해당 세대의 Chroma 컬렉션을 변경함. 활성 포인터는 변경하지 않음.
        """

        if len(chunks) != len(vectors):
            raise ValueError("청크 수와 벡터 수가 일치하지 않습니다.")
        if not chunks:
            return
        ids = [chunk.chunk_id for chunk in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("한 배치에 중복 chunk_id가 있습니다.")
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ValueError("벡터 차원이 일정하지 않습니다.")
        if any(not math.isfinite(float(value)) for vector in vectors for value in vector):
            raise ValueError("벡터에 유한하지 않은 값이 있습니다.")
        collection = self._open(generation)
        collection.upsert(
            ids=ids,
            documents=[chunk.text for chunk in chunks],
            embeddings=vectors,
            metadatas=[_clean_metadata(chunk.metadata, chunk.chunk_id) for chunk in chunks],
        )

    def _active_pointer(self) -> dict[str, Any] | None:
        """활성 세대 포인터를 읽으며 파일이 없으면 None을 반환함."""

        if not self.active_pointer_path.is_file():
            return None
        return json.loads(self.active_pointer_path.read_text(encoding="utf-8-sig"))

    def _resolve_pointer_path(self, relative: str, *, directory: bool) -> Path:
        """활성 포인터 경로가 data_root 안에 존재하는 파일 또는 디렉터리인지 확인함."""

        path = (self.data_root / relative).resolve()
        if not path.is_relative_to(self.data_root):
            raise ValueError("활성 세대 경로가 data 루트 밖을 가리킵니다.")
        exists = path.is_dir() if directory else path.is_file()
        if not exists:
            raise FileNotFoundError(f"활성 세대 경로가 없습니다: {relative}")
        return path

    def load_active(self) -> IndexSnapshot | None:
        """활성 BM25 corpus를 증분 판정에 사용할 청크 스냅샷으로 읽음.

        반환값: 활성 포인터가 없으면 None, 있으면 청크와 manifest를 담은 스냅샷임.
        예외: 포인터 경로 이탈·파일 누락·청크 수 불일치가 있으면 예외를 발생시킴.
        부수효과: 활성 포인터·corpus·manifest 파일을 읽지만 변경하지 않음.
        """

        pointer = self._active_pointer()
        if pointer is None:
            return None
        search_root = self._resolve_pointer_path(str(pointer["search_index_root"]), directory=True)
        search_pointer = json.loads((search_root / "active_index.json").read_text(encoding="utf-8-sig"))
        corpus_path = (search_root / str(search_pointer["corpus"])).resolve()
        manifest_path = (search_root / str(search_pointer["manifest"])).resolve()
        for path in (corpus_path, manifest_path):
            if not path.is_relative_to(search_root) or not path.is_file():
                raise ValueError("활성 검색 파일이 search_index_root 밖을 가리킵니다.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        chunks: list[PreparedChunk] = []
        for line in corpus_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            chunk_id = str(row["chunk_id"])
            # chunk_id는 메타데이터 해시를 만들 때 포함된 값이므로 여기서 빼면 재사용 청크의 해시 검증이 깨짐.
            metadata = {**dict(row.get("metadata") or {}), "chunk_id": chunk_id}
            text = str(row["text"])
            index_text = str(row.get("index_text") or "")
            chunks.append(
                PreparedChunk(
                    chunk_id=chunk_id,
                    text=text,
                    metadata=metadata,
                    token_count=int(row.get("token_count", 0)),
                    text_hash=str(row.get("text_hash") or _text_hash(index_text or text)),
                    metadata_hash=str(row.get("metadata_hash") or _canonical_hash(metadata)),
                    index_text=index_text,
                )
            )
        if len(chunks) != int(search_pointer["chunk_count"]):
            raise ValueError("활성 corpus 청크 수가 포인터와 일치하지 않습니다.")
        return IndexSnapshot(tuple(chunks), manifest)

    def get_vectors(self, chunk_ids: list[str]) -> dict[str, list[float]]:
        """활성 세대에서 요청한 청크 ID의 기존 벡터를 읽음.

        반환값: 활성 세대가 없으면 빈 dict, 있으면 발견된 청크 ID별 float 벡터임.
        부수효과: 활성 Chroma 컬렉션을 열 수 있으나 저장 내용은 변경하지 않음.
        """

        if not chunk_ids:
            return {}
        pointer = self._active_pointer()
        if pointer is None:
            return {}
        generation = str(pointer["generation"])
        collection = self._open(generation)
        result = collection.get(ids=list(dict.fromkeys(chunk_ids)), include=["embeddings"])
        embeddings = result.get("embeddings")
        if embeddings is None:
            return {}
        return {
            str(chunk_id): [float(value) for value in vector]
            for chunk_id, vector in zip(result.get("ids", []), embeddings, strict=True)
        }

    def _verify_collection(self, generation: str, chunks: list[PreparedChunk]) -> int:
        """발행 대상과 Chroma의 ID·본문·메타데이터·벡터 차원이 모두 일치하는지 검증함."""

        collection = self._open(generation)
        result = collection.get(include=["documents", "metadatas", "embeddings"])
        ids = [str(value) for value in result.get("ids", [])]
        expected = {chunk.chunk_id: chunk for chunk in chunks}
        if len(ids) != len(expected) or set(ids) != set(expected):
            raise ValueError("Chroma와 발행 대상의 chunk_id 집합이 일치하지 않습니다.")
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        embeddings = result.get("embeddings")
        if embeddings is None or not (len(documents) == len(metadatas) == len(embeddings) == len(ids)):
            raise ValueError("Chroma 검증 결과의 행 수가 일치하지 않습니다.")
        dimensions: set[int] = set()
        for chunk_id, text, metadata, vector in zip(ids, documents, metadatas, embeddings, strict=True):
            chunk = expected[chunk_id]
            # Chroma에는 표시·인용에 쓰는 원래 본문만 저장함. 지문은 머리말까지 포함한 색인용 텍스트 기준임.
            if str(text) != chunk.text:
                raise ValueError(f"Chroma 본문이 발행 대상과 다릅니다: {chunk_id}")
            if _text_hash(chunk.embedding_text) != chunk.text_hash:
                raise ValueError(f"발행 대상 본문 해시가 다릅니다: {chunk_id}")
            expected_metadata = _clean_metadata(chunk.metadata, chunk_id)
            if dict(metadata or {}) != expected_metadata:
                raise ValueError(f"Chroma 메타데이터가 다릅니다: {chunk_id}")
            if _canonical_hash(chunk.metadata) != chunk.metadata_hash:
                raise ValueError(f"발행 대상 메타데이터 해시가 다릅니다: {chunk_id}")
            dimensions.add(len(vector))
        if len(dimensions) != 1 or next(iter(dimensions), 0) <= 0:
            raise ValueError("Chroma 벡터 차원이 일정하지 않습니다.")
        return next(iter(dimensions))

    def _publication_value(self, generation: str, chunk_count: int) -> dict[str, Any]:
        """텍스트 manifest와 최종 Publication이 공유할 게시 위치를 만듦."""

        generation_dir = self._generation_dir(generation)
        return {
            "generation": generation,
            "chroma_path": str((generation_dir / "chroma").resolve()),
            "search_index_root": str((generation_dir / "search_indexes").resolve()),
            "collection": self.collection,
            "chunk_count": chunk_count,
        }

    def _lexical_manifest(
        self,
        generation: str,
        chunks: list[PreparedChunk],
        manifest: dict[str, Any],
        dimension: int,
    ) -> dict[str, Any]:
        """벡터 검증 결과와 게시 위치를 텍스트 색인 manifest 입력에 합침."""

        return {
            **dict(manifest),
            "embedding_dimension": dimension,
            "publication": self._publication_value(generation, len(chunks)),
        }

    def build_text_index(
        self,
        generation: str,
        chunks: list[PreparedChunk],
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        """벡터 적재를 검증하고 같은 세대의 텍스트 검색 색인을 완성함.

        목적: 오래 걸리는 BM25 생성을 최종 포인터 교체와 분리하여 안전하게 재개할 수 있게 함.
        방법: Chroma 전체를 검증한 뒤 비공개 임시 루트에서 텍스트 색인을 만들고 내용 해시를 기록함.
        인자: chunks는 비어 있지 않고 ID가 서로 달라야 하며 모두 Chroma에 저장되어 있어야 함.
        반환값: generation·청크 수와 manifest·corpus·BM25·검색 포인터 해시를 담은 dict임.
        예외: 벡터·텍스트 색인 무결성 검증이나 파일 승격 실패 예외를 호출자에게 전달함.
        부수효과: 대상 세대의 텍스트 색인과 세대 상태를 쓰며 전역 활성 포인터는 변경하지 않음.
        """

        if not chunks:
            raise ValueError("빈 세대의 텍스트 색인은 만들 수 없습니다.")
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("텍스트 색인 대상에 중복 chunk_id가 있습니다.")
        dimension = self._verify_collection(generation, chunks)
        generation_dir = self._generation_dir(generation)
        state_path = generation_dir / "generation_state.json"
        generation_state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        signature = str(generation_state["embedding_signature"])
        search_root = generation_dir / "search_indexes"
        lexical_manifest = self._lexical_manifest(
            generation,
            chunks,
            manifest,
            dimension,
        )

        active = self._active_pointer()
        if active is not None and str(active.get("generation")) == generation:
            _pointer, final_manifest, stage = self.lexical_builder.verify(
                search_root=search_root,
                generation=generation,
            )
            expected_manifest_hash = _canonical_hash(lexical_manifest)
            if final_manifest.get("source_manifest_sha256") != expected_manifest_hash:
                raise ValueError("활성 세대는 다른 manifest로 텍스트 색인을 다시 만들 수 없습니다.")
            if int(stage["chunk_count"]) != len(chunks):
                raise ValueError("활성 세대의 텍스트 색인 청크 수가 대상과 다릅니다.")
        else:
            self.lexical_builder.build(
                search_root=search_root,
                generation=generation,
                chunks=chunks,
                collection=self.collection,
                embedding_signature=signature,
                manifest=lexical_manifest,
            )
            _pointer, final_manifest, stage = self.lexical_builder.verify(
                search_root=search_root,
                generation=generation,
            )
        if int(final_manifest["chunk_count"]) != len(chunks):
            raise ValueError("BM25 manifest 청크 수가 텍스트 색인 대상과 다릅니다.")

        _replace_json(
            state_path,
            {
                **generation_state,
                "status": "text_index_ready",
                "chunk_count": len(chunks),
                "embedding_dimension": dimension,
                "text_index_stage": stage,
            },
        )
        return stage

    def publish(
        self,
        generation: str,
        chunks: list[PreparedChunk],
        manifest: dict[str, Any],
        text_index_stage: dict[str, Any],
    ) -> Publication:
        """미리 완성한 Chroma와 텍스트 색인을 하나의 활성 검색 세대로 발행함.

        목적: Retriever가 서로 다른 시점의 벡터와 BM25를 함께 읽는 상태를 방지함.
        방법: Chroma와 텍스트 색인 stage를 재검증하고 잠금 안에서 활성 포인터를 마지막에 교체함.
        인자: chunks는 비어 있지 않고 ID가 서로 달라야 하며 모두 Chroma에 저장되어 있어야 함.
        반환값: 활성화한 세대와 두 검색 저장소 경로를 담은 Publication임.
        예외: 무결성 검증 실패 시 ValueError, 기준 활성 세대가 바뀌면 RuntimeError를 발생시킴.
        부수효과: 세대 상태를 쓰고, 성공한 경우에만 전역 활성 세대 포인터를 교체함.
        """

        if not chunks:
            raise ValueError("빈 세대는 발행할 수 없습니다.")
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("발행 대상에 중복 chunk_id가 있습니다.")
        dimension = self._verify_collection(generation, chunks)
        generation_dir = self._generation_dir(generation)
        search_root = generation_dir / "search_indexes"
        state_path = generation_dir / "generation_state.json"
        generation_state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        signature = str(generation_state["embedding_signature"])
        _search_pointer, final_manifest, actual_stage = self.lexical_builder.verify(
            search_root=search_root,
            generation=generation,
        )
        if actual_stage != dict(text_index_stage):
            raise ValueError("체크포인트의 텍스트 색인 stage가 실제 파일과 다릅니다.")
        if generation_state.get("text_index_stage") != actual_stage:
            raise ValueError("세대 상태의 텍스트 색인 stage가 실제 파일과 다릅니다.")
        if int(actual_stage["chunk_count"]) != len(chunks):
            raise ValueError("텍스트 색인 stage 청크 수가 발행 대상과 다릅니다.")
        lexical_manifest = self._lexical_manifest(generation, chunks, manifest, dimension)
        if final_manifest.get("source_manifest_sha256") != _canonical_hash(lexical_manifest):
            raise ValueError("텍스트 색인을 만들 때 사용한 manifest가 발행 입력과 다릅니다.")

        publication_value = self._publication_value(generation, len(chunks))
        relative_generation = Path("generations") / generation
        pointer = {
            "format_version": 1,
            "generation": generation,
            "chroma_path": (relative_generation / "chroma").as_posix(),
            "search_index_root": (relative_generation / "search_indexes").as_posix(),
            "collection": self.collection,
            "chunk_count": len(chunks),
            "embedding_dimension": dimension,
            "embedding_signature": signature,
        }
        with CrossPlatformFileLock(self.lock_path):
            current = self._active_pointer()
            current_generation = None if current is None else str(current.get("generation"))
            base_generation = generation_state.get("base_generation")
            if current_generation not in {base_generation, generation}:
                raise RuntimeError(
                    "게시 준비 중 활성 세대가 바뀌었습니다. 오래된 실행 결과는 활성화하지 않습니다."
                )
            # 세대 상태를 ready로 기록한 뒤 단일 활성 포인터를 교체해야 Retriever가 완성된 두 색인만 읽음.
            _replace_json(
                state_path,
                {
                    **generation_state,
                    "status": "ready",
                    "chunk_count": len(chunks),
                    "embedding_dimension": dimension,
                },
            )
            _replace_json(self.active_pointer_path, pointer)
        return Publication(
            generation=generation,
            chroma_path=str(publication_value["chroma_path"]),
            search_index_root=str(publication_value["search_index_root"]),
            collection=self.collection,
            chunk_count=len(chunks),
        )


__all__ = ["GenerationIndexRepository"]
