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


class VectorStorePort(Protocol):
    def reset(self) -> None: ...

    def search(self, query_embedding: list[float], k: int, where: dict) -> list[Any]: ...

    def upsert(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None: ...

    def get_all(self) -> dict: ...

    def count(self) -> int: ...

    def check_signature(self, expected: str) -> bool: ...
