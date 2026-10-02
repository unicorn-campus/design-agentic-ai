"""구현체를 생성·주입하는 유일한 조립 지점.

순서: 설정 로딩 → 구현체(어댑터) 생성 → 그래프 실행 어댑터 → 응용 서비스 조립.
시험·평가에서는 필요한 포트만 인자로 바꿔 끼울 수 있음.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.application.keyword_service import KeywordCoverageService
from app.application.ports import (
    BM25Port,
    CorpusPort,
    EmbedderPort,
    LLMPort,
    RerankerPort,
    TransformCachePort,
    VectorStorePort,
)
from app.application.retriever_service import RetrieverService, ServiceLimits
from app.infrastructure.bm25_index import BM25Index
from app.infrastructure.keyword_analyzer import BM25KeywordAnalyzer
from app.infrastructure.chroma_store import create_vector_store
from app.infrastructure.corpus_store import VersionedCorpusStore
from app.infrastructure.embedder import LazyHuggingFaceEmbedder
from app.infrastructure.graph import LangGraphRetrieverRunner, RetrieverResources
from app.infrastructure.korean_tokenizer import KoreanTokenizer
from app.infrastructure.llm_client import LangChainLLMClient
from app.infrastructure.reranker import CrossEncoderReranker
from app.infrastructure.settings import Settings, load_settings
from app.infrastructure.transform_cache import TransformCache


def create_resources(
    *,
    settings: Any = None,
    embedder: EmbedderPort | None = None,
    vector_store: VectorStorePort | None = None,
    bm25: BM25Port | None = None,
    reranker: RerankerPort | None = None,
    llm: LLMPort | None = None,
    transform_cache: TransformCachePort | None = None,
) -> RetrieverResources:
    """기본 구현체를 조립하되 시험에서는 모든 포트를 교체 가능하게 함."""

    loaded = settings or load_settings()
    actual_embedder = embedder or LazyHuggingFaceEmbedder(loaded.EMBED_MODEL)
    actual_store = vector_store or create_vector_store(
        backend=getattr(loaded, "VECTOR_STORE_BACKEND", "chroma"),
        path=Path(loaded.CHROMA_PATH),
        collection=loaded.CHROMA_COLLECTION,
        signature=actual_embedder.signature,
    )
    actual_bm25 = bm25 or BM25Index(
        VersionedCorpusStore(Path(loaded.SEARCH_INDEX_ROOT)),
        KoreanTokenizer(
            getattr(loaded, "KOREAN_USER_DICTIONARY", None),
            num_workers=int(getattr(loaded, "KOREAN_TOKENIZER_WORKERS", 1)),
        ),
    )
    if bm25 is None:
        actual_bm25.warm()
    return RetrieverResources(
        settings=loaded,
        embedder=actual_embedder,
        vector_store=actual_store,
        bm25=actual_bm25,
        reranker=reranker
        or CrossEncoderReranker(
            loaded.RERANK_MODEL,
            max_length=int(loaded.RERANK_MAX_LENGTH),
        ),
        llm=llm or LangChainLLMClient(loaded),
        transform_cache=transform_cache or TransformCache(loaded.TRANSFORM_CACHE_PATH),
    )


def create_keyword_coverage_service(
    *,
    settings: Any = None,
    bm25: BM25Index | None = None,
    corpus: CorpusPort | None = None,
) -> KeywordCoverageService:
    """질문 핵심어가 검색 결과에 있는지 판정하는 서비스를 조립함.

    목적: 근거 충분성 판정에서 쓸 부품을 검색 그래프와 분리해 따로 만들고 시험할 수 있게 함.
    방법: BM25 색인이 이미 쓰고 있는 질의 토크나이저와 corpus 통계를 그대로 재사용함.
    인자: bm25·corpus를 넘기면 그 구현체를 쓰고, 없으면 설정으로 새 색인 어댑터를 만듦.
    반환값: 아직 검색 그래프·API 응답에 연결되지 않은 독립 서비스임.
    부수효과: bm25를 새로 만들면 첫 사용 시 활성 세대의 색인 파일을 읽음.
    """

    loaded = settings or load_settings()
    actual_corpus = corpus or VersionedCorpusStore(Path(loaded.SEARCH_INDEX_ROOT))
    actual_bm25 = bm25 or BM25Index(
        actual_corpus,
        KoreanTokenizer(
            getattr(loaded, "KOREAN_USER_DICTIONARY", None),
            num_workers=int(getattr(loaded, "KOREAN_TOKENIZER_WORKERS", 1)),
        ),
    )
    return KeywordCoverageService(
        BM25KeywordAnalyzer(actual_bm25, actual_corpus),
        max_document_ratio=float(loaded.KEYWORD_MAX_DOC_RATIO),
        top_keywords=int(loaded.KEYWORD_TOP_N),
    )


def service_limits(settings: Any) -> ServiceLimits:
    """설정값에서 API 호출 예산·제한 시간을 꺼내 서비스에 넘길 값으로 만듦."""

    return ServiceLimits(
        max_llm_calls_total=int(settings.get("MAX_LLM_CALLS_TOTAL", 200)),
        max_llm_calls_per_request=int(settings.get("MAX_LLM_CALLS_PER_REQUEST", 2)),
        request_timeout_seconds=float(settings.get("REQUEST_TIMEOUT_SECONDS", 120)),
    )


def create_service(**overrides: Any) -> RetrieverService:
    """구현체를 조립해 응용 서비스(RetrieverService)를 만듦.

    overrides는 create_resources()와 같은 키워드(settings·llm 등)를 받음.
    """

    resources = create_resources(**overrides)
    return RetrieverService(
        LangGraphRetrieverRunner(resources),
        service_limits(resources.settings),
    )


__all__ = [
    "Settings",
    "create_keyword_coverage_service",
    "create_resources",
    "create_service",
    "load_settings",
    "service_limits",
]
