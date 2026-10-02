"""구현체를 만들고 색인 서비스에 주입하는 유일한 조립 지점.

순서: 설정 로딩 → 구현체 생성 → 서비스 조립.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.application.indexing_service import IndexingService
from app.application.state import IndexRequest
from app.infrastructure.chroma_store import create_vector_store
from app.infrastructure.embedder import create_embedder
from app.infrastructure.file_store import FileStore
from app.infrastructure.graph import IndexerResources, LangGraphIndexingPipelineFactory
from app.infrastructure.index_config import JsonIndexConfig
from app.infrastructure.pdf_reader import PdfReader
from app.infrastructure.settings import load_settings


APP_ROOT = Path(__file__).resolve().parents[1]
# 문서 프로필과 메타데이터 규칙 파일이 있는 설정 폴더
CONFIG_DIR = APP_ROOT / "config"
# 중단된 실행을 이어 하기 위한 SQLite 체크포인트 파일
CHECKPOINT_PATH = APP_ROOT / "data" / "checkpoints" / "indexer.sqlite"


def build_resources(
    request: IndexRequest,
    *,
    settings: Any = None,
    pdf_reader: Any = None,
    file_store: Any = None,
    embedder: Any = None,
    vector_store: Any = None,
) -> IndexerResources:
    """기본 구현체를 조립하되 시험에서는 모든 포트를 교체 가능하게 함.

    반환 자원은 Settings(실행 설정), PdfReader(PDF→문서 변환), FileStore(파일 입출력),
    Embedder(텍스트→숫자 벡터 변환), VectorStore(벡터 저장·조회) 묶음임.
    """

    loaded = settings or load_settings()
    actual_embedder = embedder or create_embedder(
        request.embedding_backend,
        loaded.EMBED_MODEL,
        batch_size=int(loaded.EMBED_BATCH_SIZE),
    )
    path = Path(loaded.CHROMA_PATH)
    if request.embedding_backend == "smoke":
        path = Path(request.output_path) / "chroma_smoke"
    actual_store = vector_store or create_vector_store(
        backend=getattr(loaded, "VECTOR_STORE_BACKEND", "chroma"),
        path=path,
        collection=loaded.CHROMA_COLLECTION,
        signature=actual_embedder.signature,
    )
    return IndexerResources(
        settings=loaded,  # Settings: 모델·경로·시간 제한 등 실행 설정
        pdf_reader=pdf_reader or PdfReader(),  # PdfReader: PDF를 Document 목록으로 변환
        file_store=file_store or FileStore(),  # FileStore: 원문·JSON·벡터 파일을 읽고 씀
        embedder=actual_embedder,  # SmokeEmbedder/HuggingFaceEmbedder: 텍스트를 숫자 벡터로 변환
        vector_store=actual_store,  # ChromaVectorStore/MemoryVectorStore: 벡터를 저장하고 조회
    )


def create_indexing_service() -> IndexingService:
    """LangGraph 파이프라인과 JSON 설정 파일 어댑터를 주입한 색인 서비스를 만듦.

    실행 자원(설정·임베더·벡터 저장소)은 요청의 임베딩 방식·출력 경로에 따라 달라지므로
    서비스가 요청을 받은 시점에 build_resources()로 만듦.
    """

    return IndexingService(
        LangGraphIndexingPipelineFactory(build_resources, CHECKPOINT_PATH),
        JsonIndexConfig(CONFIG_DIR),
    )
