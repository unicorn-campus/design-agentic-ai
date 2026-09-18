"""Indexer가 하위 계층에 요구하는 입출력 계약."""

from pathlib import Path
from typing import Any, Literal, Protocol


class PdfReaderPort(Protocol):
    def read(self, path: Path, *, remove_margins: bool = True) -> tuple[list[Any], dict]: ...


class FileStorePort(Protocol):
    def read_text(self, path: Path) -> str: ...

    def save_jsonl(self, path: Path, rows: list[dict]) -> None: ...

    def save_json(self, path: Path, value: Any) -> None: ...

    def sha256(self, path: Path) -> str: ...


class TokenCounterPort(Protocol):
    limit: int
    prefix: str
    sha256: str

    def count(self, text: str) -> int: ...


class EmbedderPort(Protocol):
    dimension: int

    def embed(
        self,
        texts: list[str],
        *,
        kind: Literal["passage", "query"] = "passage",
    ) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class VectorWritePort(Protocol):
    """인덱싱 과정이 벡터 저장소에 요구하는 쓰기 계약."""

    def reset(self) -> None: ...

    def upsert(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None: ...


class VectorCatalogPort(Protocol):
    """증분 인덱싱과 완료 검증에 필요한 컬렉션 조회 계약."""

    def list_ids(self) -> list[str]: ...

    def describe(self) -> dict[str, Any]: ...

    def count(self) -> int: ...

    def check_signature(self, expected: str) -> bool: ...


class VectorStorePort(VectorWritePort, VectorCatalogPort, Protocol):
    """Indexer 전용 저장소 계약.

    검색은 Retriever의 책임이므로 이 계약에 포함하지 않음.
    """
