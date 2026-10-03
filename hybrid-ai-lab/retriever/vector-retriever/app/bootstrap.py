"""구현체를 고르고 만들어 서비스에 끼우는 유일한 조립 지점임."""

from __future__ import annotations

import logging

from app.application.services import RetrieverService
from app.application.steps import RetrieverSteps, StepConfig
from app.infrastructure.audit_log import JsonlAuditLog
from app.infrastructure.clock import SystemClock
from app.infrastructure.embedder import SentenceTransformerEmbedder
from app.infrastructure.graph import LangGraphWorkflow
from app.infrastructure.groq_gateway import GroqLanguageModel
from app.infrastructure.index_store import LocalIndexProvider
from app.infrastructure.reranker import CrossEncoderReranker
from app.infrastructure.settings import Settings, load_settings

logger = logging.getLogger(__name__)

# 모델을 미리 올릴 때 쓰는 짧은 문장. 검색 결과에는 쓰이지 않음
_WARMUP_TEXT = "연회비"


def create_language_model(settings: Settings) -> GroqLanguageModel:
    """LLM 커넥터 C-01 ~ C-04 구현체를 만듦. 커넥터를 바꿀 때는 이 함수만 고침."""

    return GroqLanguageModel(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        timeouts={"C-01": settings.timeout_c01, "C-02": settings.timeout_c02,
                  "C-03": settings.timeout_c03, "C-04": settings.timeout_c04},
        reasoning_effort=settings.groq_reasoning_effort,
    )


def create_service(settings: Settings | None = None, *, warm_up: bool = True) -> RetrieverService:
    """설정을 읽어 검색 서비스 전체를 조립함.

    방법: 설정 로딩 → 임베더·색인 공급자·리랭커·LLM·감사 로그·시계 생성 → 단계 로직 → LangGraph 실행기 → 서비스 순서.
    인자: warm_up이 참이면 임베딩·리랭커 모델을 서버 시작 때 한 번 올림(설계 S-R1 비고 '모델은 시작 때 1회 적재').
    첫 요청에서 모델을 올리면 10초 넘게 걸려 30초 시간 예산의 대부분을 써 버리기 때문임(지식니 실측 11.9초).
    반환값: RetrieverService. 색인 적재에 실패해도 예외 없이 돌려주며 상태 확인(health)이 ready=false를 알림.
    부수효과: 색인 세대 적재(약 4초)·모델 적재.
    """

    settings = settings or load_settings()
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY가 비어 있어 LLM 단계(C-01 ~ C-04)는 모두 대체 경로로 동작함")
    embedder = SentenceTransformerEmbedder(
        settings.embed_model,
        revision=settings.embed_revision,
        device=settings.embed_device,
        max_seq_length=settings.embed_max_tokens,
        dimension=settings.embed_dimension,
        local_files_only=settings.hf_local_files_only,
    )
    index_provider = LocalIndexProvider(
        settings.data_root,
        embedder=embedder,
        expected_embedding_contract={
            "model": settings.embed_model,
            "revision": settings.embed_revision,
            "dimension": settings.embed_dimension,
            "normalize_embeddings": True,
        },
    )
    index_provider.load_initial()
    reranker = CrossEncoderReranker(
        settings.rerank_model,
        revision=settings.rerank_revision,
        max_length=settings.rerank_max_length,
        device=settings.embed_device,
        local_files_only=settings.hf_local_files_only,
    )
    if warm_up:
        _warm_up(embedder, reranker)
    audit_log = JsonlAuditLog(settings.audit_log_path)
    clock = SystemClock()
    steps = RetrieverSteps(
        index_provider=index_provider,
        reranker=reranker,
        llm=create_language_model(settings),
        audit_log=audit_log,
        clock=clock,
        config=StepConfig(
            budget=settings.budget_policy(),
            thresholds=settings.grade_thresholds(),
            vector_weight=settings.hybrid_vector_weight,
            keyword_weight=settings.hybrid_bm25_weight,
            keyword_max_df_ratio=settings.keyword_max_df_ratio,
        ),
    )
    return RetrieverService(
        workflow=LangGraphWorkflow(steps),
        index_provider=index_provider,
        clock=clock,
        audit_log=audit_log,
    )


def _warm_up(embedder: SentenceTransformerEmbedder, reranker: CrossEncoderReranker) -> None:
    """임베딩·리랭커 모델을 미리 한 번 돌려 메모리에 올림. 실패해도 서버 시작은 막지 않음(검색 단계가 경고로 처리)."""

    try:
        embedder.embed(_WARMUP_TEXT)
        reranker.score(_WARMUP_TEXT, [_WARMUP_TEXT])
    except Exception as error:
        logger.warning("모델 미리 올리기 실패: %s", type(error).__name__)
