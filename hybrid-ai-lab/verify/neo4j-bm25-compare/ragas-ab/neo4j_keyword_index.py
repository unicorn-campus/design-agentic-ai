"""기존 검색기의 BM25(Kiwi + bm25s, 앱 안 색인)를 Neo4j 전문 검색("A 방식")으로 갈아 끼우는 어댑터임.

왜 이렇게 하나: `indexer/`와 `retriever/`의 기존 코드를 한 줄도 고치지 않고 BM25만 바꿔 끼우려는 것임.
기존 검색기는 세대 색인을 `SearchIndexPort`로 쓰므로, 그 포트를 그대로 감싸 `keyword_search`만 Neo4j로 보내고
나머지 11개 메서드(벡터 검색, 말뭉치 조회, 낱말 분석 등)는 원래 구현에 그대로 넘김.

A 방식 = 색인할 때 Kiwi로 미리 나눈 낱말을 공백으로 이어 붙여 속성에 넣고, Neo4j 전문 검색 인덱스를
`whitespace` 분석기로 만듦. 질문도 같은 Kiwi로 나눠 보냄(직전 시험 `../run_compare.py`의 후보 A와 같음).

접속은 Neo4j HTTP Query API를 씀 — 검색기 가상환경에 `neo4j` 드라이버가 없고 새 패키지를 깔지 않기 때문임.
접속값은 `../../neo4j-vector-search/.env.example`(시험 전용 값)에서 읽고 어디에도 출력하지 않음.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import requests

from app.application.ports import SearchIndexPort
from app.domain.member import member_allows
from app.domain.models import Chunk, ScoredChunk

ROOT = Path(__file__).resolve().parent
ENV_SOURCE = ROOT.parent.parent / "neo4j-vector-search" / ".env.example"
BASELINE = ROOT.parent / "fixtures" / "baseline.json"

LABEL = "RagasAbChunk"  # 이 시험 전용 라벨. 기존 Chunk, Card, Document 노드와 섞이지 않게 분리함
INDEX_NAME = "ragasab_tokens_ws"  # 이 시험 전용 인덱스 이름(끝나면 지움)
HTTP_PORT = 17474  # 시험 전용 컨테이너 verify-neo4j의 HTTP 포트
POOL = 300  # 전문 검색에서 한 번에 받아 올 후보 수. 세대 조각이 218건이라 전부 덮음

_LUCENE_SPECIAL = re.compile(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)')


def escape_lucene(value: str) -> str:
    """Lucene 질의 문법 글자에 역슬래시를 붙여 글자 그대로 찾게 함.

    왜 필요한가: 낱말에 섞인 '-'는 질의에서 NOT으로, '/'는 정규식 구분자로 읽혀 질문이 통째로 깨짐.
    반환값: 이스케이프한 문자열임.
    예외: 없음.
    부수효과: 없음.
    """

    return _LUCENE_SPECIAL.sub(r"\\\1", value)


def read_connection() -> tuple[str, tuple[str, str]]:
    """시험 전용 접속값을 읽어 (HTTP 질의 주소, (사용자, 비밀번호))를 반환함.

    방법: 환경변수가 있으면 그것을 먼저 쓰고, 없으면 시험 전용 `.env.example`에서 읽음.
    반환값: 주소 문자열과 인증 짝. 값은 호출한 쪽에서도 출력하지 않음.
    예외: 설정 파일이 없거나 키가 비면 SystemExit을 발생시킴.
    부수효과: 없음(환경변수를 바꾸지 않음).
    """

    values: dict[str, str] = {}
    if ENV_SOURCE.exists():
        for line in ENV_SOURCE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    uri = os.environ.get("NEO4J_URI") or values.get("NEO4J_URI", "")
    user = os.environ.get("NEO4J_USER") or values.get("NEO4J_USER", "")
    password = os.environ.get("NEO4J_PASSWORD") or values.get("NEO4J_PASSWORD", "")
    if not (uri and user and password):
        raise SystemExit(f"Neo4j 접속 설정을 찾지 못함: {ENV_SOURCE}")
    host = uri.split("//", 1)[-1].split(":")[0] or "localhost"
    return f"http://{host}:{HTTP_PORT}/db/neo4j/query/v2", (user, password)


class Neo4jQuerySession:
    """Neo4j HTTP Query API로 Cypher 한 문장을 보내고 행 목록을 받는 최소 클라이언트임."""

    def __init__(self, url: str, auth: tuple[str, str], *, timeout: float = 60.0) -> None:
        """접속 주소와 인증 짝을 들고 연결을 재사용하는 세션을 만듦."""

        self._url = url
        self._timeout = float(timeout)
        self._session = requests.Session()
        self._session.auth = auth

    def run(self, statement: str, **parameters: Any) -> list[list[Any]]:
        """Cypher 한 문장을 실행하고 값 행 목록을 반환함.

        인자: parameters는 Cypher의 `$이름`에 들어갈 값임.
        반환값: 행마다 RETURN 칸 순서대로 담은 목록임. RETURN이 없으면 빈 목록임.
        예외: HTTP 오류나 Neo4j 오류면 RuntimeError를 발생시킴(메시지에 접속값은 넣지 않음).
        부수효과: 문장에 따라 Neo4j 자료를 바꿈.
        """

        response = self._session.post(self._url, json={"statement": statement, "parameters": parameters},
                                      timeout=self._timeout)
        # Query API는 알림(notification)이 붙으면 200 대신 202를 돌려줌 — 둘 다 정상 응답임
        if response.status_code not in (200, 202):
            raise RuntimeError(f"Neo4j 질의 실패(HTTP {response.status_code}): {response.text[:300]}")
        body = response.json()
        if body.get("errors"):
            raise RuntimeError(f"Neo4j 질의 오류: {body['errors'][0].get('message', '')[:300]}")
        return list(body.get("data", {}).get("values", []))

    def close(self) -> None:
        """연결을 닫음. 두 번 불러도 괜찮음."""

        self._session.close()


def setup_index(session: Neo4jQuerySession, chunks: Sequence[dict[str, Any]]) -> None:
    """조각을 전용 라벨로 넣고 whitespace 분석기 전문 검색 인덱스를 만듦(기존 노드는 건드리지 않음).

    인자: chunks는 `fixtures/baseline.json`의 조각 목록(조각ID와 Kiwi 낱말 tokens를 가짐)임.
    반환값: 없음.
    예외: 적재 건수가 다르거나 인덱스가 120초 안에 ONLINE이 되지 않으면 RuntimeError를 발생시킴.
    부수효과: Neo4j에 전용 라벨 노드와 전용 인덱스를 만듦(teardown_index로 지움).
    """

    teardown_index(session)
    rows = [{"chunk_id": row["chunk_id"], "tokens_text": " ".join(row["tokens"])} for row in chunks]
    session.run(f"UNWIND $rows AS row CREATE (n:{LABEL}) SET n = row", rows=rows)
    stored = session.run(f"MATCH (n:{LABEL}) RETURN count(n) AS n")
    if int(stored[0][0]) != len(rows):
        raise RuntimeError(f"적재 건수가 다름: {stored[0][0]} != {len(rows)}")
    session.run(
        f"CREATE FULLTEXT INDEX {INDEX_NAME} FOR (n:{LABEL}) ON EACH [n.tokens_text] "
        "OPTIONS {indexConfig: {`fulltext.analyzer`: 'whitespace'}}"
    )
    deadline = time.time() + 120
    while time.time() < deadline:
        states = session.run("SHOW INDEXES YIELD name, state WHERE name = $name RETURN state", name=INDEX_NAME)
        if states and states[0][0] == "ONLINE":
            return
        time.sleep(1.0)
    raise RuntimeError("전문 검색 인덱스가 ONLINE이 되지 않음")


def teardown_index(session: Neo4jQuerySession) -> None:
    """이 시험이 만든 전용 인덱스와 전용 라벨 노드만 지움(다른 노드와 인덱스는 그대로 둠)."""

    session.run(f"DROP INDEX {INDEX_NAME} IF EXISTS")
    session.run(f"MATCH (n:{LABEL}) DETACH DELETE n")


class Neo4jKeywordIndex(SearchIndexPort):
    """기존 세대 색인을 감싸 `keyword_search`만 Neo4j 전문 검색으로 보내는 어댑터임.

    나머지 메서드는 감싼 색인(기존 `GenerationIndex`)에 그대로 넘김 — 벡터 검색과 말뭉치와 낱말 분석은 바꾸지 않음.
    """

    def __init__(self, delegate: SearchIndexPort, session: Neo4jQuerySession, *, pool: int = POOL) -> None:
        """감쌀 색인과 Neo4j 세션을 들고 있음.

        인자: pool은 전문 검색에서 한 번에 받아 올 후보 수임(조각 수보다 크면 기존 BM25와 같은 범위를 봄).
        """

        self._delegate = delegate
        self._session = session
        self._pool = int(pool)
        self.neo4j_calls = 0  # 실행 뒤 확인용 — 정말 Neo4j로 갔는지 세어 둠

    # ------------------------------------------------------------ 바꿔 끼우는 단 하나의 메서드

    def keyword_search(self, query: str, *, access_levels: Sequence[str], k: int,
                       member_pseudo_id: str | None = None) -> list[ScoredChunk]:
        """색인과 같은 Kiwi 분석기로 질의를 낱말로 나눠 Neo4j 전문 검색 점수가 높은 조각 k개를 찾음.

        기존 구현과 같게 맞춘 것: 같은 분석기로 자른 낱말을 질의로 씀, 점수가 0 이하면 버림,
        열람 등급과 회원 필터는 점수를 낸 뒤 순위 매기기 전에 적용함, 같은 점수면 조각ID 오름차순임.
        다른 것: 점수 값이 bm25s(k1 = 1.5)가 아니라 Lucene(k1 = 1.2)이라 크기와 순서가 조금 달라질 수 있음.
        반환값: 점수 내림차순 ScoredChunk 목록. 낱말이 하나도 없으면 빈 목록임.
        예외: Neo4j 질의 실패는 RuntimeError를 그대로 올림(호출한 단계가 '한쪽 실패'로 처리함).
        부수효과: Neo4j에 읽기 질의 1회.
        """

        levels = tuple(dict.fromkeys(str(value) for value in access_levels if str(value)))
        if not levels or int(k) <= 0:
            return []
        tokens = [token for token in self._delegate.tokens(query) if token.strip()]
        if not tokens:
            return []
        lucene_query = " ".join(escape_lucene(token) for token in tokens)
        self.neo4j_calls += 1
        rows = self._session.run(
            "CALL db.index.fulltext.queryNodes($name, $q, {limit: $limit}) "
            "YIELD node, score RETURN node.chunk_id AS chunk_id, score",
            name=INDEX_NAME, q=lucene_query, limit=self._pool,
        )
        scores = {str(chunk_id): float(score) for chunk_id, score in rows}
        chunks = self._delegate.get_chunks(scores.keys())
        found: list[ScoredChunk] = []
        for chunk_id, score in scores.items():
            if score <= 0.0:
                continue
            chunk = chunks.get(chunk_id)
            if chunk is None or chunk.access_level not in levels:
                continue
            if not member_allows(chunk.member_pseudo_id, member_pseudo_id):
                continue
            found.append(ScoredChunk(chunk_id, score))
        found.sort(key=lambda value: (-value.score, value.chunk_id))
        return found[: int(k)]

    # ------------------------------------------------------------ 나머지는 그대로 넘김

    def generation_id(self) -> str:
        """감싼 색인의 세대ID를 그대로 돌려줌."""

        return self._delegate.generation_id()

    def num_docs(self) -> int:
        """감싼 색인의 조각 수를 그대로 돌려줌."""

        return self._delegate.num_docs()

    def vector_search(self, query: str, *, access_levels: Sequence[str], k: int,
                      member_pseudo_id: str | None = None) -> list[ScoredChunk]:
        """벡터 검색은 바꾸지 않음 — 기존 Chroma 검색을 그대로 부름."""

        return self._delegate.vector_search(query, access_levels=access_levels, k=k,
                                            member_pseudo_id=member_pseudo_id)

    def get_chunks(self, chunk_ids: Iterable[str]) -> dict[str, Chunk]:
        """말뭉치 조회는 바꾸지 않음."""

        return self._delegate.get_chunks(chunk_ids)

    def consult_history(self, member_pseudo_id: str, *, access_levels: Sequence[str]) -> list[Chunk]:
        """상담 이력 조회는 바꾸지 않음."""

        return self._delegate.consult_history(member_pseudo_id, access_levels=access_levels)

    def tokens(self, text: str) -> list[str]:
        """낱말 나누기는 바꾸지 않음(질의 쪽도 이 분석기를 씀)."""

        return self._delegate.tokens(text)

    def keyword_candidates(self, text: str) -> list[str]:
        """채점 핵심어 후보 뽑기는 바꾸지 않음."""

        return self._delegate.keyword_candidates(text)

    def document_frequency(self, terms: Iterable[str]) -> dict[str, int]:
        """낱말 문서 빈도는 바꾸지 않음(기존 색인이 세대 적재 때 센 값)."""

        return self._delegate.document_frequency(terms)

    def chunk_terms(self, chunk_ids: Iterable[str]) -> frozenset[str]:
        """조각 낱말 집합은 바꾸지 않음."""

        return self._delegate.chunk_terms(chunk_ids)

    def target_terms(self, text: str) -> frozenset[str]:
        """카드 대상명 뽑기는 바꾸지 않음."""

        return self._delegate.target_terms(text)

    def condition_terms(self, text: str) -> frozenset[str]:
        """조건 낱말 뽑기는 바꾸지 않음."""

        return self._delegate.condition_terms(text)
