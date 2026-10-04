"""조립 지점 — 설정을 읽고 어댑터를 만들어 서비스에 끼움. 구현체 생성은 이 파일에서만 함."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from app.application.compare_service import CompareService
from app.application.eval_set_service import EvalSetService
from app.application.models import RunnerPaths
from app.application.ragas_service import RagasService
from app.application.review_service import ReviewService
from app.application.runner_service import RunnerService
from app.infrastructure.files import ActiveCorpusReader, ActivePointer, LocalArtifactStore, RunnerLock
from app.infrastructure.processes import HttpServerProbe, IndexerProcess, LocalEnvironment, RetrieverEvalProcess
from app.infrastructure.ragas_judge import RagasJudge, build_embeddings, build_llm
from app.infrastructure.settings import Settings, load_settings


@dataclass
class Services:
    """명령행이 쓰는 서비스 묶음."""

    settings: Settings
    eval_set: EvalSetService
    ragas: RagasService
    review: ReviewService
    compare: CompareService
    runner: RunnerService


def create_judge_factory(settings: Settings):
    """평가자 이름(local · anthropic · groq)으로 RagasJudge를 만드는 함수를 돌려줌.

    임베딩 생성 함수는 평가자끼리 같은 것(KURE-v2)을 씀 — AnswerRelevancy 점수가 평가자에 따라 달라지지 않게 함.
    """

    embeddings = build_embeddings(settings)

    def factory(provider: str) -> RagasJudge:
        llm, model = build_llm(provider, settings=settings)
        return RagasJudge(provider, llm, embeddings, model, settings.embed_model)

    return factory


def create_services(settings: Settings | None = None) -> Services:
    """설정 로딩 → 어댑터 생성 → 서비스 조립 순으로 만듦. 모델 · 평가자는 처음 채점할 때 올림."""

    settings = settings or load_settings()
    store = LocalArtifactStore()
    ragas = RagasService(store, create_judge_factory(settings), concurrency=settings.ragas_concurrency)
    review = ReviewService(store)
    compare = CompareService(store)
    environment = LocalEnvironment(
        settings.app_root,
        {"ragas": Path(sys.executable), "indexer": settings.indexer_python,
         "retriever": settings.retriever_python},
        settings.embed_device,
        {"GROQ_API_KEY": bool(settings.groq_api_key), "ANTHROPIC_API_KEY": bool(settings.anthropic_api_key)},
    )
    runner = RunnerService(
        store=store,
        pointer=ActivePointer(settings.data_root),
        lock=RunnerLock(settings.experiments_root / ".runner.lock"),
        indexer=IndexerProcess(settings.indexer_python, settings.indexer_dir, settings.process_timeout_seconds),
        retriever=RetrieverEvalProcess(settings.retriever_python, settings.retriever_dir, settings.process_timeout_seconds),
        probe=HttpServerProbe(settings.retriever_api_urls),
        environment=environment,
        ragas=ragas, review=review, compare=compare,
        paths=RunnerPaths(ragas_root=settings.app_root, experiments_root=settings.experiments_root,
                          indexer_dir=settings.indexer_dir, data_root=settings.data_root),
    )
    return Services(settings, EvalSetService(store, ActiveCorpusReader(settings.data_root)), ragas, review, compare,
                    runner)
