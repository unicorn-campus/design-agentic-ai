"""Indexer 유스케이스의 요청·응답·오류 계약을 정의함."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IndexingError(RuntimeError):
    """Indexer가 복구하지 못해 호출자에게 전달하는 공통 오류임."""


class ThreadReuseError(IndexingError):
    """같은 thread_id를 서로 다른 요청이나 설정에 사용한 경우의 오류임."""


class TransientOperationError(IndexingError):
    """앞선 시도의 종료가 확인되어 안전하게 다시 실행할 수 있는 일시 오류임."""


class IndexRequest(BaseModel):
    """CLI 입력을 응용 계층에 전달하는 불변 요청임."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_path: Path = Field(description="색인할 원천 문서가 있는 입력 경로")
    output_path: Path = Field(description="세대별 색인과 체크포인트를 저장할 출력 경로")
    doc: Literal["D1", "D2", "D3", "all"] = Field(
        default="all", description="처리할 문서 유형, all은 모든 유형을 뜻함"
    )
    segment: int | None = Field(
        default=None,
        ge=1,
        le=6,
        description="D3에서 선택할 상담 세그먼트 번호, None은 전체를 뜻함",
    )
    thread_id: str = Field(
        min_length=1,
        description="체크포인트 재개와 요청 일치 검증에 사용하는 실행 식별자",
    )
    full_reindex: bool = Field(
        default=False, description="기존 벡터 재사용 없이 전체를 다시 임베딩할지 여부"
    )
    dry_run: bool = Field(
        default=False, description="정제 결과까지만 만들고 색인 세대를 게시하지 않을지 여부"
    )


class ExtractSummary(BaseModel):
    """원천 발견과 개인정보 처리 완료 건수를 요약함."""

    source_count: int = Field(default=0, description="선택 조건에 맞아 발견한 원천 문서 수")
    prepared_count: int = Field(default=0, description="정제와 개인정보 처리를 끝낸 청크 수")


class ChunkSummary(BaseModel):
    """최종 청크와 벡터 재사용·생성 건수를 요약함."""

    chunk_count: int = Field(default=0, description="새 세대에 포함될 최종 청크 수")
    reused_count: int = Field(default=0, description="본문 해시가 같아 기존 벡터를 재사용한 청크 수")
    embedded_count: int = Field(default=0, description="새로 임베딩한 청크 수")


class IndexSummary(BaseModel):
    """게시된 색인 세대의 결과와 실패 항목을 요약함."""

    collection_count: int = Field(default=0, description="게시된 컬렉션의 청크 수")
    newly_embedded: int = Field(default=0, description="이번 실행에서 새로 만든 벡터 수")
    skipped_by_hash: int = Field(default=0, description="본문 해시 일치로 임베딩을 생략한 벡터 수")
    failed: list[dict[str, Any]] = Field(
        default_factory=list, description="처리하지 못한 항목과 오류 정보 목록"
    )
    embedding_dimension: int = Field(default=0, description="임베딩 벡터의 차원 수")
    generation: str | None = Field(default=None, description="게시된 색인 세대 식별자")


class IndexResult(BaseModel):
    """CLI와 테스트가 공유하는 최종 실행 결과임."""

    sources: int = Field(default=0, description="선택 조건에 맞아 발견한 원천 문서 수")
    extract: ExtractSummary = Field(
        default_factory=ExtractSummary, description="원천 발견과 정제 단계 요약"
    )
    chunk: ChunkSummary = Field(default_factory=ChunkSummary, description="청킹과 임베딩 단계 요약")
    index: IndexSummary = Field(default_factory=IndexSummary, description="색인 게시 단계 요약")
    timings: dict[str, int] = Field(
        default_factory=dict, description="단계별 누적 실행 시간(밀리초)"
    )
    status: Literal["ok", "dry_run", "error"] = Field(description="최종 실행 상태")
    exit_code: int = Field(description="CLI 프로세스 종료 코드")
    thread_id: str = Field(description="실행과 체크포인트를 식별하는 값")
    no_op: bool = Field(default=False, description="변경이 없어 처리를 생략했는지 여부")

