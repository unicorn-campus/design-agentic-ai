"""K-1 취향 벡터 유사도 검색 — 색인 만들기와 검색기를 **짝으로** 둠.

색인을 만든 설정과 검색할 때 쓰는 설정이 **같은 곳**(`common.config`)에서 나옴.
색인 이름 · 임베딩 모델 이름 · 버전 · 제품 이름 · 후보 수는 **코드에 없고 전부 설정**임.

⑤ K-1이 정한 검색 방식을 그대로 지킴 — **속성 필터를 먼저 적용한 뒤 유사도로 줄 세움.**
필터를 나중에 걸면 반경 밖 항목이 상위에 섞임.

색인 1건에는 **어느 항목의 어느 자리에서 왔는지**(`locator`)를 함께 넣음.
근거를 되짚을 수 없는 결과를 만들지 않음.

**청킹(쪼개는 단위)은 해당 없음** — ⑤ K-1이 「항목 1건 = 벡터 1건」으로 정했음.
쪼갤 대상이 없으므로 크기 · 겹침 설정도 만들지 않았음(설정은 값이 「해당 없음」임을 적는 칸뿐임).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from common.config import Settings, SettingsMissing, get_settings

from .model_input import REMOVED_INPUT_FIELDS
from .result import (
    Candidate,
    Provenance,
    RetrievalKind,
    RetrievalResult,
    RetrievalTrace,
    ScoreKind,
    now_utc,
)

__all__ = [
    "EmbeddingClient",
    "EmbeddingUnavailable",
    "IndexSwapPlan",
    "IndexedItem",
    "UnknownFilterKey",
    "VectorIndex",
    "build_index",
    "cosine_similarity",
    "index_name_for",
    "plan_index_swap",
    "search_similar",
]

_ROUTE_ID = "K-1"


class EmbeddingUnavailable(RuntimeError):
    """임베딩 모델 이름·버전이 설정에 없음. 무엇이 없는지 알리고 멈춤 — 지어내지 않음."""


class UnknownFilterKey(ValueError):
    """④가 소유하지 않은 거르기 키임. 새 이름을 짓지 않음."""


@runtime_checkable
class EmbeddingClient(Protocol):
    """항목 글을 벡터로 바꿔 주는 사람. 제품·모델 이름은 이 바깥에서 옴."""

    model_name: str
    model_version: str

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True, slots=True)
class IndexedItem:
    """색인 1건. `locator`가 「어느 항목의 어느 자리」를 가리킴."""

    item_key: str
    locator: str
    vector: tuple[float, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorIndex:
    """색인 1벌. 만든 설정을 함께 들고 있어 검색이 같은 값을 씀."""

    index_name: str
    embedding_model: str
    embedding_model_version: str
    product: str | None
    corpus_scope: str | None
    corpus_as_of: str | None
    chunking: str | None
    built_at: datetime
    items: tuple[IndexedItem, ...]
    notes: tuple[str, ...] = ()

    @property
    def item_count(self) -> int:
        return len(self.items)


@dataclass(frozen=True, slots=True)
class IndexSwapPlan:
    """색인을 다시 만드는 절차. 되묻기 1의 기본값을 그대로 적은 것임.

    실제 갈아 끼우기는 색인 제품이 정해진 뒤에만 할 수 있음 — 여기서는 순서만 들고 있음.
    """

    serving_name: str
    staging_name: str
    steps: tuple[str, ...]


def _require(value: str | None, what: str) -> str:
    if not value:
        raise EmbeddingUnavailable(
            f"{what}이 설정에 없음 — [확인필요: 벡터 인덱스 제품·임베딩 모델명·버전]"
        )
    return value


def index_name_for(role: str, settings: Settings | None = None, staging: bool = False) -> str:
    """색인 이름을 설정에서만 읽음. 다시 만들 때는 접미가 붙은 **새 이름**을 씀."""
    conf = settings if settings is not None else get_settings()
    base = conf.knowledge_index_name_for(role)
    if not staging:
        return base
    suffix = conf.knowledge_index_build_suffix
    if not suffix:
        raise SettingsMissing(
            "색인을 다시 만들 때 붙일 접미가 설정에 없음 — 쓰는 색인을 지우고 덮지 않음"
        )
    return f"{base}{suffix}"


def plan_index_swap(role: str, settings: Settings | None = None) -> IndexSwapPlan:
    """되묻기 1 — 새 이름으로 만들고 다 되면 갈아 끼움. 쓰는 색인을 먼저 지우지 않음."""
    serving = index_name_for(role, settings, staging=False)
    staging = index_name_for(role, settings, staging=True)
    return IndexSwapPlan(
        serving_name=serving,
        staging_name=staging,
        steps=(
            f"1. {staging} 이름으로 새로 만듦(쓰는 색인 {serving}은 그대로 둠)",
            "2. 새 색인의 건수와 임베딩 모델 이름·버전을 확인함",
            f"3. 읽는 곳이 가리키는 이름을 {staging}으로 갈아 끼움",
            f"4. 되돌릴 일이 없다고 확인한 뒤에 옛 {serving}을 치움",
        ),
    )


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """두 벡터가 얼마나 같은 방향인가. 값이 클수록 가까움."""
    if len(left) != len(right):
        raise ValueError(f"벡터 길이가 다름 — {len(left)} vs {len(right)}")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0.0 or norm_right == 0.0:
        raise ValueError("길이가 0인 벡터끼리는 가까운지 견줄 수 없음")
    return dot / (norm_left * norm_right)


def _check_metadata_keys(keys: Iterable[str], conf: Settings, where: str) -> None:
    allowed = set(conf.knowledge_metadata_filter_keys)
    if not allowed:
        raise SettingsMissing(
            "메타데이터 거르기 키가 설정에 없음 — 이름의 주인은 ④ 「입출력 형식」임"
        )
    outside = sorted(set(keys) - allowed)
    if outside:
        raise UnknownFilterKey(f"{where}: ④가 소유하지 않은 거르기 키임 — {outside}")


def _check_payload(payload: Mapping[str, Any], where: str) -> None:
    removed = sorted(name for name in payload if name in REMOVED_INPUT_FIELDS)
    if removed:
        raise ValueError(f"{where}: 규격에서 지운 필드를 색인에 넣으려 했음 — {removed}")


def build_index(
    role: str,
    items: Sequence[Mapping[str, Any]],
    embedder: EmbeddingClient,
    settings: Settings | None = None,
) -> VectorIndex:
    """색인을 만듦. 항목 1건 = 벡터 1건임(쪼개지 않음).

    항목 1건은 `item_key` · `locator` · `text` · `metadata` · `payload`를 가짐.
    임베딩 모델 이름·버전이 설정에 없으면 **만들지 않고 무엇이 없는지 알리고 멈춤**.
    """
    conf = settings if settings is not None else get_settings()
    model_name = _require(conf.embedding_model, "임베딩 모델 이름")
    model_version = _require(conf.knowledge_embedding_model_version, "임베딩 모델 버전")
    if embedder.model_name != model_name or embedder.model_version != model_version:
        raise EmbeddingUnavailable(
            "색인을 만드는 모델이 설정값과 다름 —"
            f" 설정 {model_name}/{model_version} · 부른 것 {embedder.model_name}/{embedder.model_version}"
        )

    index_name = index_name_for(role, conf, staging=True)
    notes: list[str] = []
    if conf.knowledge_chunking:
        notes.append(f"쪼개는 단위 — {conf.knowledge_chunking}")

    if not items:
        return VectorIndex(
            index_name=index_name,
            embedding_model=model_name,
            embedding_model_version=model_version,
            product=conf.knowledge_vector_index_product,
            corpus_scope=conf.knowledge_corpus_scope,
            corpus_as_of=conf.knowledge_corpus_as_of,
            chunking=conf.knowledge_chunking,
            built_at=now_utc(),
            items=(),
            notes=(*notes, "색인할 항목이 0건임 — 없는 항목을 만들어 채우지 않음"),
        )

    for index, item in enumerate(items):
        _check_metadata_keys(dict(item.get("metadata") or {}), conf, f"{role} {index}번째 항목")
        _check_payload(dict(item.get("payload") or {}), f"{role} {index}번째 항목")

    vectors = embedder.embed([str(item["text"]) for item in items])
    if len(vectors) != len(items):
        raise EmbeddingUnavailable(
            f"항목 수와 벡터 수가 다름 — 항목 {len(items)} · 벡터 {len(vectors)}"
        )

    built = tuple(
        IndexedItem(
            item_key=str(item["item_key"]),
            locator=str(item["locator"]),
            vector=tuple(float(value) for value in vector),
            metadata=dict(item.get("metadata") or {}),
            payload=dict(item.get("payload") or {}),
        )
        for item, vector in zip(items, vectors, strict=True)
    )
    return VectorIndex(
        index_name=index_name,
        embedding_model=model_name,
        embedding_model_version=model_version,
        product=conf.knowledge_vector_index_product,
        corpus_scope=conf.knowledge_corpus_scope,
        corpus_as_of=conf.knowledge_corpus_as_of,
        chunking=conf.knowledge_chunking,
        built_at=now_utc(),
        items=built,
        notes=tuple(notes),
    )


def _matches(item: IndexedItem, criteria: Mapping[str, Any]) -> bool:
    for key, wanted in criteria.items():
        if key not in item.metadata:
            return False
        if item.metadata[key] != wanted:
            return False
    return True


def search_similar(
    index: VectorIndex,
    query_vector: Sequence[float],
    metadata_filter: Mapping[str, Any] | None = None,
    settings: Settings | None = None,
) -> RetrievalResult:
    """속성 필터를 **먼저** 걸고 남은 것만 유사도로 줄 세움.

    못 볼 항목은 이 단계에서 걸러 냄 — 뽑아 놓고 나중에 지우지 않음.
    후보가 0건이면 빈 결과 + 사유를 돌려줌.
    """
    conf = settings if settings is not None else get_settings()
    criteria = dict(metadata_filter or {})
    _check_metadata_keys(criteria, conf, "유사도 검색 거르기 조건")
    top_k = conf.knowledge_top_k_value()

    if not index.items:
        return RetrievalResult.empty(
            _ROUTE_ID,
            RetrievalKind.VECTOR_SIMILARITY,
            f"색인 {index.index_name}에 항목이 0건임 — 지어낸 근거를 채우지 않음",
        )

    kept = [item for item in index.items if _matches(item, criteria)]
    if not kept:
        return RetrievalResult.empty(
            _ROUTE_ID,
            RetrievalKind.VECTOR_SIMILARITY,
            f"거르기 조건 {sorted(criteria)}을 지난 항목이 0건임",
            notes=(f"색인 {index.index_name} 전체 {index.item_count}건",),
        )

    scored = sorted(
        ((cosine_similarity(query_vector, item.vector), item) for item in kept),
        key=lambda pair: pair[0],
        reverse=True,
    )[:top_k]

    candidates = tuple(
        Candidate(
            payload=dict(item.payload) or {"item_key": item.item_key},
            source=Provenance(
                route_id=_ROUTE_ID,
                locator=item.locator,
                design_row="⑤ 5절 K-1",
                origin=f"색인 {index.index_name} · {index.embedding_model}/{index.embedding_model_version}",
                read_at=index.built_at,
            ),
            score=score,
            score_kind=ScoreKind.COSINE_SIMILARITY,
        )
        for score, item in scored
    )
    trace = RetrievalTrace(
        stage="유사도 검색",
        before=tuple(item.item_key for item in index.items),
        after=tuple(item.item_key for _, item in scored),
        detail={"metadata_filter": criteria, "top_k": top_k},
    )
    return RetrievalResult.of(
        _ROUTE_ID,
        RetrievalKind.VECTOR_SIMILARITY,
        candidates,
        reason_when_empty="유사도 검색 후보가 0건임",
        notes=(f"거르기를 먼저 걸어 {index.item_count}건 → {len(kept)}건이 남았음",),
        traces=(trace,),
    )
