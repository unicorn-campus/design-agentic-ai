"""장표 「벡터검색을 Native Neo4j 벡터 인덱스로」·「검색 세대 구성」의 설계 방안을 그대로 옮긴 검증용 구현임.

검증 전용 모듈이라 계층 구조(domain·application·infrastructure)로 나누지 않음 — 시험이 이 함수들을 직접 부름.
기존 검색기 코드는 결과 합치기 규칙(app/domain/fusion.py, 표준 라이브러리만 씀)만 파일 경로로 읽어 씀.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from neo4j import Driver, GraphDatabase
from neo4j_graphrag.components.entity_relation_extractor import LLMEntityRelationExtractor, OnError
from neo4j_graphrag.components.kg_writer import Neo4jWriter
from neo4j_graphrag.components.resolver import SinglePropertyExactMatchResolver
from neo4j_graphrag.components.types import DocumentInfo, TextChunk, TextChunks
from neo4j_graphrag.indexes import create_vector_index
from neo4j_graphrag.retrievers import VectorRetriever

HERE = Path(__file__).resolve().parent
FUSION_PATH = HERE.parent.parent / "retriever" / "vector-retriever" / "app" / "domain" / "fusion.py"
INDEX_NAME = "chunk_vec"
DIMENSION = 768
CONSULT_DOC_TYPE = "consult_log"
# 인덱스 안에서 거를 속성 — 세대·열람 등급·문서 종류·회원 범위.
# member_scope: 상담 이력이 아니면 "all", 상담 이력이면 회원 가명. 회원 규칙($or)을 $eq 검색 2번으로 바꾸려고 둠 —
# Neo4j 2026.09 SEARCH 필터는 =·범위를 AND로 묶은 것만 받고 <>($ne)·OR은 거부함(2026-10-13 실측)
FILTERABLE = ["generation", "access_level", "doc_type", "member_scope"]
ALL_MEMBERS = "all"
VECTOR_WEIGHT, KEYWORD_WEIGHT = 0.6, 0.4  # 기존 검색기 설정 기본값(settings.py hybrid_*_weight)


def load_fusion() -> Any:
    """기존 검색기의 결과 합치기 규칙 모듈을 고치지 않고 파일 경로로 읽어 돌려줌."""

    spec = importlib.util.spec_from_file_location("existing_fusion", FUSION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def connect() -> Driver:
    """환경변수(NEO4J_URI·NEO4J_USER·NEO4J_PASSWORD)로 시험용 Neo4j에 연결함."""

    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),  # 실습 공용 컨테이너 neo4j(hybrid-ai-lab/neo4j/compose.yml)
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )


def reset_db(driver: Driver) -> None:
    """시험 DB의 노드·관계·인덱스를 모두 지움(시험 전용 컨테이너에만 씀)."""

    # CALL ... IN TRANSACTIONS는 자동 커밋 세션에서만 돌아 execute_query(명시적 트랜잭션) 대신 session.run을 씀
    with driver.session() as session:
        session.run("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS").consume()
    records, _, _ = driver.execute_query("SHOW INDEXES YIELD name, type WHERE type <> 'LOOKUP' RETURN name")
    for record in records:
        driver.execute_query(f"DROP INDEX `{record['name']}` IF EXISTS")


# ---------------------------------------------------------------- 인덱싱(장표 1 ①)

def to_text_chunks(chunks: Sequence[dict[str, Any]], generation: str) -> dict[str, list[TextChunk]]:
    """기존 청크를 문서(source)별 TextChunk 목록으로 바꿈.

    uid는 저장 뒤 지워지는 임시 ID라서 chunk_id·generation은 metadata에 넣어 속성으로 남김(장표 1 메모).
    기존 벡터를 metadata["embedding"]에 넣어 다시 임베딩하지 않음. 값이 없는 회원 가명은 넣지 않음(Neo4j는 null 속성 없음).
    """

    groups: dict[str, list[TextChunk]] = defaultdict(list)
    for chunk in chunks:
        metadata = {
            "chunk_id": chunk["chunk_id"], "generation": generation, "access_level": chunk["access_level"],
            "doc_type": chunk["doc_type"], "source": chunk["source"], "embedding": list(chunk["embedding"]),
            "member_scope": chunk["member_pseudo_id"] if chunk["doc_type"] == CONSULT_DOC_TYPE else ALL_MEMBERS,
        }
        if chunk.get("member_pseudo_id"):
            metadata["member_pseudo_id"] = chunk["member_pseudo_id"]
        group = groups[chunk["source"]]
        group.append(TextChunk(text=chunk["text"], index=len(group), uid=f"{generation}:{chunk['chunk_id']}",
                               metadata=metadata))
    return dict(groups)


def write_generation(driver: Driver, llm: Any, chunks: Sequence[dict[str, Any]], generation: str) -> None:
    """한 세대를 Neo4j에 저장함: 문서별 추출 → 저장기 → 엔티티에 세대 표시(게시 순서 2)."""

    extractor = LLMEntityRelationExtractor(llm=llm, create_lexical_graph=True, on_error=OnError.IGNORE)
    writer = Neo4jWriter(driver)

    async def run() -> None:
        for source, group in to_text_chunks(chunks, generation).items():
            graph = await extractor.run(chunks=TextChunks(chunks=group),
                                        document_info=DocumentInfo(path=source, metadata={"generation": generation}))
            await writer.run(graph)

    asyncio.run(run())
    # 추출기가 만든 엔티티에는 세대가 없어, 저장 뒤 그 세대 청크와 FROM_CHUNK로 이어진 엔티티에 표시함
    driver.execute_query(
        "MATCH (c:Chunk {generation: $g})<-[:FROM_CHUNK]-(e:__Entity__) SET e.generation = $g", g=generation)


def resolve(driver: Driver, generation: str | None) -> None:
    """같은 라벨·같은 이름 엔티티를 합침. generation을 주면 그 세대 안에서만 합침(게시 순서 3)."""

    scope = f"WHERE entity.generation = '{generation}'" if generation else None
    asyncio.run(SinglePropertyExactMatchResolver(driver, filter_query=scope).run())


def ensure_vector_index(driver: Driver) -> None:
    """Chunk.embedding 벡터 인덱스를 만들고 ONLINE이 될 때까지 기다림."""

    create_vector_index(driver, INDEX_NAME, label="Chunk", embedding_property="embedding", dimensions=DIMENSION,
                        similarity_fn="cosine", filterable_properties=FILTERABLE)
    driver.execute_query("CALL db.awaitIndexes(120)")


def index_state(driver: Driver) -> str:
    """벡터 인덱스 상태(ONLINE 등)를 돌려줌."""

    records, _, _ = driver.execute_query("SHOW VECTOR INDEXES YIELD name, state WHERE name = $n RETURN state",
                                         n=INDEX_NAME)
    return records[0]["state"] if records else "MISSING"


# ---------------------------------------------------------------- 검색(장표 1 ②)

class FilterAwareVectorRetriever(VectorRetriever):
    """인덱스의 걸러 낼 속성을 SHOW VECTOR INDEXES의 properties에서도 읽는 VectorRetriever.

    왜 필요한가(2026-10-13 실측): neo4j-graphrag 1.22.0은 인덱스를 `WITH [n.prop]`로 만들고, Neo4j 2026.09는 그 속성을
    properties 목록(첫 칸은 벡터 속성)에 보여 줌. 그런데 기본 VectorRetriever는 options.indexConfig의
    `vector.filterable_properties`만 읽어 빈 목록이 되고, 필터가 있으면 늘 전수 비교로 바뀜.
    """

    def _fetch_index_infos(self, vector_index_name: str) -> None:
        super()._fetch_index_infos(vector_index_name)
        if self._filterable_properties:
            return
        records, _, _ = self.driver.execute_query(
            "SHOW VECTOR INDEXES YIELD name, properties WHERE name = $n RETURN properties", n=vector_index_name)
        if records:
            self._filterable_properties = list(records[0]["properties"][1:])


def access_filter(access_levels: Sequence[str]) -> dict[str, Any]:
    """열람 등급 조건. 등급이 하나면 $eq(인덱스 안 처리), 전부면 조건 없음, 그 밖은 $in(전수 비교)."""

    levels = sorted(set(access_levels))
    if levels == ["public", "restricted"]:
        return {}
    if len(levels) == 1:
        return {"access_level": {"$eq": levels[0]}}
    return {"access_level": {"$in": levels}}


def member_allows(doc_type: str | None, chunk_member: str | None, requested: str | None) -> bool:
    """기존 검색기 Chroma 조건과 같은 회원 규칙: 상담 이력이 아니거나 그 회원 것이면 통과."""

    return not requested or doc_type != CONSULT_DOC_TYPE or chunk_member == requested


def vector_search(driver: Driver, query_vector: Sequence[float], *, generation: str, access_levels: Sequence[str],
                  k: int, member: str | None = None, member_strategy: str = "split", oversample: int = 4,
                  search_ratio: int = 4, stock_retriever: bool = False,
                  extra: dict[str, Any] | None = None) -> list[tuple[str, float]]:
    """활성 세대 안에서 벡터검색함.

    회원 규칙('상담 이력이 아님 OR 그 회원 것')을 푸는 방법(member_strategy):
      split(기본) — member_scope $eq "all" 검색과 $eq 회원 검색을 인덱스 안에서 따로 해 점수순으로 합침(정확한 상위 k)
      oversample — 후보를 k×oversample개 받아 앱에서 거름(그 회원 조각이 후보 밖이면 빠짐, 시험으로 재현)
      or — $or 필터를 Neo4j에 넘김(전수 비교로 바뀜)
    search_ratio: 인덱스 안 검색의 후보 배수(effective_search_ratio). Neo4j 2026.09 기본 BINARY 압축 인덱스에서
      1이면 기존 Chroma와 순서 일치 43/60, 4 이상이면 압축 없는 결과와 같았음(tools/measure_recall.py 실측).
    stock_retriever=True면 라이브러리 기본 VectorRetriever를 씀(속성 인식 불일치 재현용).
    반환값: (chunk_id, 점수) 점수 내림차순. 점수는 Neo4j 코사인 유사도((1+cos)/2).
    """

    filters: dict[str, Any] = {"generation": {"$eq": generation}, **access_filter(access_levels), **(extra or {})}
    if member and member_strategy == "split":
        common = dict(generation=generation, access_levels=access_levels, k=k, search_ratio=search_ratio,
                      stock_retriever=stock_retriever)
        public = vector_search(driver, query_vector, extra={"member_scope": {"$eq": ALL_MEMBERS}}, **common)
        own = vector_search(driver, query_vector, extra={"member_scope": {"$eq": member}}, **common)
        return sorted(dict(public + own).items(), key=lambda item: (-item[1], item[0]))[:k]
    top_k = k
    if member and member_strategy == "or":
        filters["$or"] = [{"doc_type": {"$ne": CONSULT_DOC_TYPE}}, {"member_pseudo_id": {"$eq": member}}]
    elif member:
        top_k = k * oversample
    retriever = (VectorRetriever if stock_retriever else FilterAwareVectorRetriever)(driver, INDEX_NAME)
    raw = retriever.get_search_results(query_vector=list(query_vector), top_k=top_k, filters=filters,
                                       effective_search_ratio=search_ratio)
    found = []
    for record in raw.records:
        node = record["node"]
        if member and member_strategy == "oversample" and not member_allows(
                node.get("doc_type"), node.get("member_pseudo_id"), member):
            continue
        found.append((str(node["chunk_id"]), float(record["score"])))
    found.sort(key=lambda item: (-item[1], item[0]))
    return found[:k]


def hybrid(vector_hits: Iterable[Sequence[Any]], keyword_hits: Iterable[Sequence[Any]], k: int) -> list[str]:
    """기존 검색기와 같은 방식(최소-최대 정규화 가중합 0.6 : 0.4 → rank_keys)으로 합친 조각ID 순위."""

    fusion = load_fusion()
    vector_scores = {str(cid): float(score) for cid, score in vector_hits}
    keyword_scores = {str(cid): float(score) for cid, score in keyword_hits}
    fused = fusion.weighted_hybrid(vector_scores, keyword_scores, vector_weight=VECTOR_WEIGHT,
                                   keyword_weight=KEYWORD_WEIGHT)
    return fusion.rank_keys(fused, (vector_scores, keyword_scores))[:k]


def graph_expand(driver: Driver, chunk_ids: Sequence[str], generation: str) -> list[dict[str, Any]]:
    """찾은 chunk_id에서 FROM_CHUNK를 거꾸로 따라가 엔티티와 그 관계를 모음(그래프 확장)."""

    records, _, _ = driver.execute_query(
        "MATCH (c:Chunk {generation: $g}) WHERE c.chunk_id IN $ids "
        "MATCH (e:__Entity__)-[:FROM_CHUNK]->(c) "
        "OPTIONAL MATCH (e)-[r]->(o:__Entity__) "
        "RETURN c.chunk_id AS chunk_id, e.name AS entity, labels(e) AS labels, type(r) AS rel, o.name AS other",
        g=generation, ids=list(chunk_ids))
    return [dict(record) for record in records]


# ---------------------------------------------------------------- 세대(장표 2)

def verify_generation(driver: Driver, generation: str, expected_ids: set[str]) -> dict[str, Any]:
    """게시 전 검증(게시 순서 5): 청크 수·chunk_id 집합·벡터 차원·인덱스 상태."""

    records, _, _ = driver.execute_query(
        "MATCH (c:Chunk {generation: $g}) RETURN collect(c.chunk_id) AS ids, "
        "min(size(c.embedding)) AS min_dim, max(size(c.embedding)) AS max_dim", g=generation)
    row = records[0]
    ids = [str(value) for value in row["ids"]]
    report = {
        "count": len(ids), "unique": len(set(ids)), "ids_match": set(ids) == expected_ids,
        "min_dim": row["min_dim"], "max_dim": row["max_dim"], "index": index_state(driver),
    }
    report["ok"] = (report["count"] == len(expected_ids) == report["unique"] and report["ids_match"]
                    and report["min_dim"] == report["max_dim"] == DIMENSION and report["index"] == "ONLINE")
    return report


def publish(pointer_path: Path, generation: str, search_index_root: str, report: dict[str, Any]) -> None:
    """검증을 통과한 세대만 포인터를 원자적으로 바꿈(게시 순서 6). 통과 못 하면 ValueError."""

    if not report.get("ok"):
        raise ValueError(f"검증을 통과하지 못한 세대는 게시하지 않음: {report}")
    pointer = {"generation": generation, "neo4j": {"vector_index": INDEX_NAME, "generation": generation},
               "search_index_root": search_index_root, "embedding_dimension": DIMENSION}
    temporary = pointer_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, pointer_path)


def read_pointer(pointer_path: Path) -> dict[str, Any]:
    """검색기가 요청 처음에 한 번 읽는 포인터."""

    return json.loads(pointer_path.read_text(encoding="utf-8"))
