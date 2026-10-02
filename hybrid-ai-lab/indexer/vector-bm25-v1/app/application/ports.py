"""Indexer가 하위 계층에 요구하는 입출력 계약."""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Literal, Protocol

from .state import IndexerState, IndexRequest


class PdfReaderPort(Protocol):
    @abstractmethod
    def read(self, path: Path, *, remove_margins: bool = True) -> tuple[list[Any], dict]: ...


class FileStorePort(Protocol):
    @abstractmethod
    def read_text(self, path: Path) -> str: ...

    @abstractmethod
    def save_jsonl(self, path: Path, rows: list[dict]) -> None: ...

    @abstractmethod
    def save_json(self, path: Path, value: Any) -> None: ...

    @abstractmethod
    def sha256(self, path: Path) -> str: ...


class TokenCounterPort(Protocol):
    limit: int
    prefix: str
    sha256: str

    @abstractmethod
    def count(self, text: str) -> int: ...


class EmbedderPort(Protocol):
    dimension: int

    @abstractmethod
    def embed(
        self,
        texts: list[str],
        *,
        kind: Literal["passage", "query"] = "passage",
    ) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class VectorWritePort(Protocol):
    """인덱싱 과정이 벡터 저장소에 요구하는 쓰기 계약."""

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def upsert(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None: ...


class VectorCatalogPort(Protocol):
    """증분 인덱싱과 완료 검증에 필요한 컬렉션 조회 계약."""

    @abstractmethod
    def list_ids(self) -> list[str]: ...

    @abstractmethod
    def describe(self) -> dict[str, Any]: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def check_signature(self, expected: str) -> bool: ...


class VectorStorePort(VectorWritePort, VectorCatalogPort, Protocol):
    """Indexer 전용 저장소 계약.

    검색은 Retriever의 책임이므로 이 계약에 포함하지 않음.
    """


class IndexConfigPort(Protocol):
    """색인 실행마다 읽는 문서 프로필·메타데이터 규칙 계약."""

    @abstractmethod
    def load_profiles(self) -> dict[str, Any]:
        """원문 파일별 담당 부서·공개 등급 등의 프로필을 돌려줌."""

    @abstractmethod
    def load_schema(self) -> dict[str, Any]:
        """메타데이터 허용값과 필수 항목 규칙을 돌려줌."""


class IndexingPipelinePort(Protocol):
    """8개 노드 색인 파이프라인 한 번의 실행 계약."""

    @abstractmethod
    def run(self, initial_state: IndexerState, thread_id: str) -> IndexerState:
        """첫 상태로 실행(같은 thread_id의 체크포인트가 있으면 이어서 실행)하고 최종 상태를 돌려줌."""


class IndexingPipelineFactoryPort(Protocol):
    """요청 조건(임베딩 방식·출력 경로)에 맞는 실행 자원과 파이프라인을 준비하는 계약."""

    @abstractmethod
    def create(self, request: IndexRequest) -> IndexingPipelinePort:
        """요청 한 건을 실행할 파이프라인을 만듦."""
