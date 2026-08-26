from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from help_desk_runtime.settings import RuntimeSettings


class KnowledgeConfigurationError(ValueError):
    pass


def required(settings: RuntimeSettings, name: str) -> Any:
    value = getattr(settings, name, None)
    if value is None or value == "":
        raise KnowledgeConfigurationError(f"필수 설정이 비어 있음: HELP_DESK_{name.upper()}")
    if hasattr(value, "get_secret_value"):
        return value.get_secret_value()
    return value


def safe_identifier(value: str) -> str:
    if not value.replace("_", "").isalnum() or value[0].isdigit():
        raise KnowledgeConfigurationError(f"안전하지 않은 식별자: {value}")
    return value


@dataclass(frozen=True)
class RagSpec:
    dsn: str
    table: str
    index_name: str
    product: str
    source_documents: str
    source_count: int | None
    baseline_date: str | None
    extraction: str
    cleaning: str
    chunk_tokens: int
    overlap_tokens: int
    separator: str
    embedding_model: str
    embedding_dimensions: int
    hnsw_min_chunks: int
    hnsw_m: int
    hnsw_ef_construction: int
    hnsw_ef_search: int
    search_method: str
    fusion_method: str
    rrf_k: int
    diversity: str
    top_k: int
    filter_score: float

    @classmethod
    def from_settings(cls, settings: RuntimeSettings) -> "RagSpec":
        return cls(
            dsn=str(required(settings, "knowledge_rag_dsn")),
            table=safe_identifier(str(required(settings, "knowledge_rag_table"))),
            index_name=str(required(settings, "knowledge_rag_index_name")),
            product=str(required(settings, "knowledge_rag_product")),
            source_documents=str(required(settings, "knowledge_rag_source_documents")),
            source_count=getattr(settings, "knowledge_rag_source_count", None),
            baseline_date=getattr(settings, "knowledge_rag_baseline_date", None),
            extraction=str(required(settings, "knowledge_rag_extraction")),
            cleaning=str(required(settings, "knowledge_rag_cleaning")),
            chunk_tokens=int(required(settings, "knowledge_rag_chunk_tokens")),
            overlap_tokens=int(required(settings, "knowledge_rag_overlap_tokens")),
            separator=str(required(settings, "knowledge_rag_separator")),
            embedding_model=str(required(settings, "knowledge_rag_embedding_model")),
            embedding_dimensions=int(required(settings, "knowledge_rag_embedding_dimensions")),
            hnsw_min_chunks=int(required(settings, "knowledge_rag_hnsw_min_chunks")),
            hnsw_m=int(required(settings, "knowledge_rag_hnsw_m")),
            hnsw_ef_construction=int(required(settings, "knowledge_rag_hnsw_ef_construction")),
            hnsw_ef_search=int(required(settings, "knowledge_rag_hnsw_ef_search")),
            search_method=str(required(settings, "knowledge_rag_search_method")),
            fusion_method=str(required(settings, "knowledge_rag_fusion_method")),
            rrf_k=int(required(settings, "knowledge_rag_rrf_k")),
            diversity=str(required(settings, "knowledge_rag_diversity")),
            top_k=int(required(settings, "knowledge_rag_top_k")),
            filter_score=float(required(settings, "knowledge_rag_filter_score")),
        )

    def unresolved(self) -> tuple[str, ...]:
        missing = []
        if self.source_count is None:
            missing.append("승인 문서 원천 건수")
        if not self.baseline_date:
            missing.append("승인 문서 기준일")
        return tuple(missing)


@dataclass(frozen=True)
class GraphSpec:
    uri: str
    user: str
    password: str
    database: str
    product: str
    version: str
    max_hops: int
    result_limit: int
    role_map_path: Path
    human_sample_size: int
    human_accuracy: float

    @classmethod
    def from_settings(cls, settings: RuntimeSettings) -> "GraphSpec":
        return cls(
            uri=str(required(settings, "knowledge_graph_uri")),
            user=str(required(settings, "knowledge_graph_user")),
            password=str(required(settings, "knowledge_graph_password")),
            database=str(required(settings, "knowledge_graph_database")),
            product=str(required(settings, "knowledge_graph_product")),
            version=str(required(settings, "knowledge_graph_version")),
            max_hops=int(required(settings, "knowledge_graph_max_hops")),
            result_limit=int(required(settings, "knowledge_graph_result_limit")),
            role_map_path=Path(str(required(settings, "knowledge_graph_role_map_path"))),
            human_sample_size=int(required(settings, "knowledge_graph_human_sample_size")),
            human_accuracy=float(required(settings, "knowledge_graph_human_accuracy")),
        )
