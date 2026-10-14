# 벡터검색을 Native Neo4j 벡터 인덱스로 — PPT 스크립트

- 산출물: `temp/neo4j-vector-search/Neo4j벡터검색.pptx` (2장)
- 작성: 클로니(직접 수행), 2026-10-13
- 요청: 벡터검색을 Native Neo4j(neo4j-graphrag) 벡터 인덱스로 하는 방법. 하이브리드 검색의 키워드 쪽은 기존 BM25 인덱스를 쓴다는 점과  
  검색 세대 구성을 포함
- 2장으로 나눈 이유: 인덱싱 · 검색 · 세대를 한 장에 넣으면 14pt 하한을 지킬 수 없음
- 스타일: `references/pptx-guide.md` — `내용_단쪽` 레이아웃, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음
- 처음엔 제안 설계였고, v2에서 **검증 완료**(아래 v2 변경)

## v2 변경(2026-10-13, 검증 결과 반영 · 사용자 결정)

- 검증: `hybrid-ai-lab/verify/neo4j-vector-search`(Neo4j 2026.09.0 CE · neo4j-graphrag 1.22.0), `pytest` 24 passed,  
  `pytest -m ollama` 1 passed. 기존 Chroma 대비 벡터 상위 10 순서 60/60, 하이브리드 60/60 일치(README 결과 표)
- 시험으로 드러나 고친 설계

| # | 처음 설계 | 실측 | 바꾼 설계 |
|---|-----------|------|-----------|
| 1 | filterable_properties로 세대 필터를 인덱스 안에서 | 기본 VectorRetriever가 인덱스의 거를 속성을 못 읽어 늘 전수 비교 | 하위 클래스로 `properties` 목록도 읽음 |
| 2 | 회원 필터는 $or라 앱에서 · 후보를 넉넉히 | 후보 4배 + 앱 거르기는 E07 · E09 · E10 누락. $ne는 서버가 거부 | `member_scope`("all" 또는 회원 가명) + $eq 검색 2번 합치기 |
| 3 | (언급 없음) | 2026.09 벡터 인덱스 기본 압축 BINARY, 후보 배수 1이면 40/60 | 후보 배수(effective_search_ratio) 4 → 60/60 |
| 4 | 하이브리드 = RRF(fusion.py) | 기존 검색기 벡터 + BM25 합치기는 `weighted_hybrid`(0.6 : 0.4), RRF는 다중 질의용(steps.py 595 · 669행) | 가중합으로 표기 |

- 슬라이드 1: 코드에 access_level · member_scope 추가, 메모 2줄 교체, Chunk 속성 줄 교체, 검색 3가지 → 4가지(회원 필터 줄 추가),  
  오른쪽 위 '실측 검증 60/60 일치' 표시
- 슬라이드 2: '제안 설계' → '검증 완료 · 시험 24건 통과', 게시 순서 2에 member_scope, 주의 카드 4개 교체
- 아래 슬라이드 본문 표는 v2 내용으로 고침

## 근거(스크립트에만 기록)

| 내용 | 근거 |
|------|------|
| 청크 노드 = text · index + metadata 전부, `metadata["embedding"]`은 벡터 속성으로 | `neo4j_graphrag/components/lexical_graph.py` 126 ~ 150행(`.temp/n4j_lex.py`) |
| `TextChunk.uid`는 저장 뒤 지워지는 임시 ID | `neo4j_queries.py` 103행 `__tmp_internal_id`, 144 ~ 156행 정리 쿼리(`.temp/n4j_queries.py`) |
| 저장기는 `CREATE` | 같은 파일 103행 |
| 관계 이름 기본값 FROM_DOCUMENT · NEXT_CHUNK · FROM_CHUNK, 청크 ID 속성 `id` | `types.py` 236 ~ 244행(`.temp/n4j_types2.py`) |
| `create_vector_index(driver, name, label, embedding_property, dimensions, similarity_fn, filterable_properties)` | `indexes.py` 37 ~ 46행(`.temp/n4j_indexes.py`) |
| `VectorRetriever(driver, index_name, embedder)`, `search(query_text, top_k, effective_search_ratio, filters)` | `retrievers/vector.py` 101 ~ 165행(`.temp/n4j_vector_v2.py`) |
| 필터 인덱스 내 처리 = Neo4j 2026.01+ · `filterable_properties` 필요, 이전 버전은 전수 비교 | User Guide RAG 760 ~ 815행(`.temp/n4j_ug_rag_v2.rst`) |
| `$eq` · `$gte` 등은 인덱스 안 처리, `$or` · `$in` · `$like`는 전수 비교 | 같은 문서 801 ~ 812행 |
| `HybridRetriever`는 Neo4j 전문 색인(`db.index.fulltext.queryNodes`)만 연결 | `retrievers/hybrid.py` 94행, `neo4j_queries.py` 65행 |
| 병합기 기본 범위 = 모든 `__Entity__`, `filter_query`로 좁힘 | `components/resolver.py` 58 · 78행(`.temp/neo4j-graphrag-resolver.py`) |
| 지금 세대 방식: `data/generations/<세대>/` 생성 → `active_generation.json` 원자적 교체, 검색기는 포인터를 한 번 읽어 같은 세대 두 경로 사용, 되돌릴 때 두 경로를 함께 | `hybrid-ai-lab/indexer/vector-bm25-v2/README.md` 201 ~ 207행 |
| 현재 세대 값: KURE-v2 · 768차원 · 청크 218개(검색기 사용 중 세대 `gen-ch2-20261003-001-17151790`) | `hybrid-ai-lab/indexer/vector-bm25/data/active_generation.json`(검색기 DATA_ROOT 기본값). v2 인덱서 data는 192개로 다른 세대 |
| BM25 = bm25s 0.3.11 + kiwipiepy 0.23.2, 결과 합치기 = RRF · 가중합 | `requirements.txt` 10 ~ 11행, `retriever/vector-retriever/app/domain/fusion.py` |
| 회원 필터 규칙: 회원 가명 없는 조각은 통과, 있으면 같은 회원만 | `retriever/vector-retriever/app/domain/member.py` `member_allows` |

## 슬라이드 1 — 벡터검색을 Native Neo4j 벡터 인덱스로

- 리드문: 청크 · 벡터 · 그래프를 Neo4j 한 곳에 담고, 하이브리드 검색의 키워드 쪽은 기존 BM25 인덱스를 그대로 씀
- 도형 구성
  - 왼쪽 위 「① 인덱싱」: 칩 흐름 4칸 + 코드 상자 + 메모 2줄
  - 오른쪽 위 「Neo4j에 담긴 모습」: Document · Chunk 2개 · 엔티티 2개 노드와 관계 화살표, 벡터 인덱스 표시
  - 아래 「② 검색 4가지」: 벡터 · 회원 필터 · 하이브리드 · 그래프 확장 4줄(라벨 + 칩 흐름 + 설명)
  - 오른쪽 위 표시: "실측 검증 60/60 일치"

### ① 인덱싱

- 흐름: 청킹(기존 코드) → TextChunk 만들기 → Neo4jWriter 저장 → 벡터 인덱스 생성
- 코드:  
  `TextChunk(text=c.text, index=i, uid=c.chunk_id, metadata={`  
  `    "chunk_id": c.chunk_id, "generation": gen, "access_level": c.level,`  
  `    "member_scope": c.member or "all", "embedding": c.vector})`  
  `create_vector_index(driver, "chunk_vec", label="Chunk",`  
  `    embedding_property="embedding", dimensions=768, similarity_fn="cosine",`  
  `    filterable_properties=["generation", "access_level", "member_scope"])`
- 메모: uid는 임시 ID라 chunk_id는 metadata에 · 기존 벡터(768차원)를 넣어 재사용 /  
  member_scope: 상담이 아니면 "all", 상담이면 회원 가명 → 회원 필터를 $eq로

### Neo4j에 담긴 모습

- (Chunk) ─FROM_DOCUMENT→ (Document), (Chunk) ─NEXT_CHUNK→ (Chunk), (A사) ─FROM_CHUNK→ (Chunk), (A사) ─LAUNCHED→ (B카드)
- Chunk 속성: chunk_id · text · embedding · generation · 등급(access_level) · member_scope
- 벡터 인덱스 chunk_vec = Chunk.embedding

### ② 검색 4가지

| 검색 | 흐름 | 설명 |
|------|------|------|
| 벡터 | 질문 → VectorRetriever(속성 인식 보완) → chunk_id 목록 | 세대 · 등급을 $eq로 인덱스 안에서 거름, 후보 배수 4(압축 보정) |
| 회원 필터 | member_scope = "all" + member_scope = 회원 → 점수순 합침 | $or · $ne는 전수 비교 · 서버 거부 → $eq 검색 2번 |
| 하이브리드 | Neo4j 벡터 + 기존 BM25(bm25s · Kiwi) → 가중합 0.6 : 0.4(weighted_hybrid) | HybridRetriever 대신 기존 BM25 유지, 점수는 정규화돼 순위 그대로 |
| 그래프 확장 | chunk_id → FROM_CHUNK로 엔티티 → 관계 따라감 | VectorCypherRetriever 또는 Cypher 직접 |

### 발표자 노트(슬라이드 1)

- 기존 인덱서가 만든 청크를 그대로 TextChunk로 바꿔 Neo4j에 넣음. 정제 · 가명처리 · 청킹은 기존 코드가 함
- uid는 저장할 때만 쓰고 지워지므로, 검색 결과를 BM25와 맞추려면 chunk_id를 metadata에 넣어 속성으로 남겨야 함
- metadata에 embedding을 넣으면 벡터 속성으로 저장돼 다시 임베딩하지 않아도 됨. 질문 임베딩도 같은 KURE-v2를 써야 함
- member_scope: Neo4j 2026.09 벡터 필터는 같음(=)과 범위만 받아 '상담이 아니거나 그 회원'이라는 OR 조건을 넘길 수 없음.  
  member_scope = "all" 검색과 = 회원 검색을 따로 해 점수순으로 합침. 후보를 넉넉히 받아 앱에서 거르는 방식은 3/20 문항이 틀렸음
- 기본 VectorRetriever는 이 버전 조합에서 거를 속성을 못 읽어 필터가 늘 전수 비교가 되므로 하위 클래스로 보완함
- 인덱스 기본 압축(BINARY) 때문에 후보 배수 4를 둬야 기존 Chroma와 60/60 같았음(배수 1은 40/60)
- 하이브리드: HybridRetriever는 Neo4j 전문 색인만 연결할 수 있어 쓰지 않고, 기존 BM25와 기존 가중합(0.6 : 0.4)으로 합침.  
  Neo4j 점수는 (1+cos)/2라 값은 다르지만 최소-최대 정규화 뒤 같아져 순위가 그대로임
- 그래프 확장은 찾은 chunk_id에서 FROM_CHUNK를 거꾸로 따라가 엔티티와 관계를 모음

## 슬라이드 2 — 검색 세대 구성: Neo4j와 BM25를 한 세대로

- 리드문: 새 세대를 다 만든 뒤 포인터 하나만 바꿔, 검색기가 늘 같은 세대의 벡터 · 그래프 · BM25를 보게 함
- 도형 구성
  - 왼쪽: 포인터 상자(active_generation.json, 바뀌는 값 강조) → 세대 2개(gen-A 보관 · gen-B 활성) 각각 Neo4j 칸 + BM25 칸
  - 오른쪽: 게시 순서 6단계 + 되돌리기 띠
  - 아래: 주의 카드 4개
- 표시: "검증 완료 · 시험 24건 통과"

### 포인터

```
{ "generation": "gen-B",
  "neo4j": { "vector_index": "chunk_vec", "generation": "gen-B" },
  "search_index_root": "generations/gen-B/search_indexes",
  "embedding_dimension": 768 }
```

- 바뀌는 점: chroma_path(폴더) 대신 neo4j.generation(값) — 세대를 폴더가 아니라 노드 속성으로 구분

### 세대 그림

| 세대 | Neo4j | BM25 |
|------|-------|------|
| gen-A(이전 · 보관) | generation=gen-A 청크 · 엔티티 | generations/gen-A/search_indexes |
| gen-B(활성) | generation=gen-B 청크 · 엔티티 | generations/gen-B/search_indexes |

### 게시 순서

1. 새 세대 ID 정함(gen-B)
2. Neo4j에 저장 — 청크는 metadata(member_scope 포함)로, 엔티티는 저장 뒤 Cypher로 generation 표시
3. 같은 세대 안에서만 병합(병합기 filter_query)
4. BM25 색인 생성(generations/gen-B)
5. 검증 — Neo4j 청크 수 = BM25 청크 수, chunk_id 집합 같음, 768차원, 인덱스 ONLINE
6. 포인터 교체(active_generation.json 원자적 교체)

- 되돌리기: 포인터만 gen-A로(두 값을 함께). 이전 세대는 정한 개수만큼 보관 후 삭제

### 주의

| # | 제목 | 내용 |
|---|------|------|
| 1 | 라이브러리 불일치 | 기본 VectorRetriever가 거를 속성을 못 읽어 필터가 늘 전수 비교 → 하위 클래스로 보완 |
| 2 | 회원 필터는 $eq 2번 | $or · $ne는 전수 비교 · 서버 거부, 앱에서 거르면 3/20 문항 누락 → member_scope로 2번 검색 |
| 3 | 압축(BINARY) 보정 | 기본 압축 + 후보 배수 1은 순서 일치 40/60 → 후보 배수 4로 60/60 |
| 4 | CREATE · 병합 범위 | 같은 세대 재저장 시 청크 중복 → 실패 세대는 지우고 처음부터, 병합기는 filter_query로 새 세대만 |

### 발표자 노트(슬라이드 2)

- 지금 인덱서는 Chroma와 BM25를 같은 세대 폴더에 만들고 active_generation.json을 한 번에 바꿈. 검색기는 포인터를 한 번 읽고  
  같은 세대의 두 경로를 씀. Neo4j로 바꿔도 이 원칙은 그대로 둠
- 차이는 Neo4j 쪽 세대를 폴더가 아니라 노드의 generation 속성으로 구분한다는 점. 한 DB에 여러 세대가 같이 있음
- 엔티티는 추출기가 만들 때 generation이 붙지 않으므로, 저장 뒤 해당 세대 청크와 FROM_CHUNK로 이어진 엔티티에 표시함
- 병합기를 그냥 돌리면 이전 세대 엔티티와도 합쳐 세대가 섞이므로 filter_query로 새 세대만 대상으로 함
- 검증을 통과해야 포인터를 바꿈. 되돌릴 때는 포인터를 이전 세대로 바꾸면 Neo4j 값과 BM25 경로가 함께 돌아감
- 검증(2026-10-13): 게시 · 전환 · 되돌리기, 검증 실패 시 게시 거부, 세대 범위 병합이 시험을 통과함.  
  같은 세대 재저장 시 청크 2배, 병합 범위를 안 좁히면 두 세대 엔티티가 한 노드로 합쳐지는 현상도 재현함
- 주의 1 · 2 · 3은 시험 중 드러나 설계를 고친 부분임
- 한계: BM25 세대는 하나뿐이라 BM25 쪽 전환은 포인터 값 대조까지만 확인함
