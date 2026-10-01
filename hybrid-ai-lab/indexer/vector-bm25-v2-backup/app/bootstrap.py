"""설정에 따라 구현체를 만들고 응용 서비스의 포트에 주입하는 조립 지점임."""

from __future__ import annotations

from typing import Any

from app.application.indexing_service import IndexingService, IndexingWorkflow
from app.domain.models import SplitPolicy
from app.infrastructure.artifact_store import JsonArtifactStore
from app.infrastructure.embedder import HuggingFaceEmbedder
from app.infrastructure.graph import LangGraphPipeline
from app.infrastructure.index_repository import GenerationIndexRepository
from app.infrastructure.lexical_index import LexicalIndexBuilder
from app.infrastructure.loaders import ConfiguredDocumentLoader, FileSystemSourceCatalog
from app.infrastructure.locked_runner import LockedPipelineRunner
from app.infrastructure.processor import ValidatingChunkProcessor
from app.infrastructure.progress_reporter import ConsoleProgressReporter
from app.infrastructure.settings import Settings, load_settings
from app.infrastructure.splitter import RecursiveDocumentSplitter
from app.infrastructure.token_counter import ModelTokenCounter


def create_service(settings: Settings | None = None, **ports: Any) -> IndexingService:
    """인덱싱 서비스를 구성하되 시험에서는 포트 구현체를 교체할 수 있게 함.

    방법: 전달된 포트를 우선 사용하고 나머지는 파일·모델·Chroma·BM25·LangGraph 구현체로 구성함.
    인자: settings가 없으면 설정 파일과 환경변수를 읽음. ports는 시험에서 대체할 계약 이름별 구현체임.
    반환값: 실행 준비가 된 서비스임. 실제 원천 처리와 임베딩은 서비스를 실행할 때 수행함.
    예외: 잘못된 설정은 ValueError 등으로 전달되며 경로 접근 실패는 OSError 계열 예외로 전달됨.
    부수효과: 기본 저장소 구현체 생성 시 결과·산출물 디렉터리를 만들 수 있음.
    """
    config = settings or load_settings()
    
    # 임베딩 모델의 토크나이저(문장을 토큰으로 자르고 각 조각을 번호로 바꿈. 모델이 이 번호별 조각을 임베딩함)
    # 분할과 임베딩이 같은 모델 revision을 사용해야 토큰 상한의 기준이 어긋나지 않음.
    counter = ports.get("token_counter") or ModelTokenCounter(
        config.model_name, config.model_revision, config.max_tokens, local_files_only=config.local_files_only)
    
    # 임베딩 처리 객체 
    embedder = ports.get("embedder") or HuggingFaceEmbedder(
        config.model_name, revision=config.model_revision, max_seq_length=config.max_tokens,
        batch_size=config.batch_size, device=config.device, local_files_only=config.local_files_only,
        expected_dimension=config.embedding_dimension)
    
    # 벡터와 BM25 인덱스 저장 처리 객체   
    repository = ports.get("repository") or GenerationIndexRepository(
        config.output_path, collection=config.collection, lexical_builder=LexicalIndexBuilder(),
        lock_path=config.output_path / ".publish.lock")
    
    # 워크플로우 처리 객체  
    workflow = IndexingWorkflow(
        sources=ports.get("sources") or FileSystemSourceCatalog(config.policies),
        loader=ports.get("loader") or ConfiguredDocumentLoader(config.policies, config.profiles),
        splitter=ports.get("splitter") or RecursiveDocumentSplitter(counter, config.policies),
        token_counter=counter, 
        processor=ports.get("processor") or ValidatingChunkProcessor(counter, config.metadata_schema),
        embedder=embedder, repository=repository,
        artifacts=ports.get("artifacts") or JsonArtifactStore(config.output_path / "artifacts"),
        policies=config.split_policies, default_policy=SplitPolicy(),
        policy_signature=config.policy_signature, 
        profile_signature=config.profile_signature,
        embedding_contract=config.embedding_contract,
        embed_batch_size=config.batch_size, 
        upsert_batch_size=64,  # 적재는 최대 64개씩 저장해 재개 단위를 제한함
    )
    
    # 실행 전체 잠금과 게시 잠금을 분리함. 그래프의 게시 노드는 호출자와 다른 스레드에서 실행될 수 있음.
    runner = ports.get("runner") or LockedPipelineRunner(
        LangGraphPipeline(workflow, config.output_path / "checkpoints" / "indexing.sqlite",
                          progress=ports.get("progress") or ConsoleProgressReporter()),
        config.output_path / ".writer.lock",
    )
    
    # 무변경 실행에서 모델을 불필요하게 읽지 않도록 설정 차원을 전달하고 실제 로딩 시 별도로 검증함.
    return IndexingService(runner, policy_signature=config.policy_signature,
                           profile_signature=config.profile_signature, embedding_signature=embedder.signature,
                           embedding_dimension=config.embedding_dimension)


def create_cli_service(overrides: dict[str, Any]) -> tuple[IndexingService, Any, Any]:
    """CLI 입력을 우선 적용한 서비스와 입출력 경로를 함께 반환함.

    목적: CLI가 인프라 설정 로더나 개별 구현체를 직접 선택하지 않도록 조립을 이 지점에 모음.
    반환값: 서비스·원천 경로·결과 경로 순서임.
    예외: 설정 해석·검증·경로 접근에서 발생한 오류를 호출자에게 그대로 전달함.
    부수효과: 설정 파일을 읽고 서비스 조립에 필요한 결과 디렉터리를 만들 수 있음.
    """
    settings = load_settings(overrides)
    return create_service(settings), settings.input_path, settings.output_path
