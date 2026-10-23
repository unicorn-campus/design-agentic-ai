# Neo4j 벡터검색 설계 검증

장표 「벡터검색을 Native Neo4j 벡터 인덱스로」·「검색 세대 구성」(`temp/neo4j-vector-search/`)의 설계 방안이  
실제로 동작하는지 확인하는 검증 코드임. 기존 indexer·retriever 코드는 고치지 않고 읽기만 함.

## 구성

| 파일 | 하는 일 |
|------|---------|
| `tools/export_fixture.py` | 기존 검색기 가상환경으로 사용 중 세대를 읽어 청크·벡터·평가 질문 벡터·기존 벡터/BM25 결과를 JSON으로 뽑음 |
| `neo4j_store.py` | 설계 방안 구현(저장·병합·벡터 인덱스·검색·가중합·그래프 확장·세대 검증·포인터 교체) |
| `llms.py` | 가짜 LLM(카드명 추출, 결과 고정) · Ollama HTTP LLM |
| `tests/` | 시험 25건(Ollama 1건은 `-m ollama`로 따로) |
| `tools/measure_recall.py` | 설정별 Chroma 결과 일치율 측정 |

## 실행

Neo4j는 실습 공용 컨테이너 `neo4j`(`hybrid-ai-lab/neo4j/compose.yml`, bolt 7687)를 씀. 처음이면 `neo4j/README.md`대로 `.env`를 만든 뒤 띄움.  
비밀번호는 `neo4j/.env`의 값을 환경변수 `NEO4J_PASSWORD`로 넘김(이 폴더 `.env.example`에는 비밀번호를 두지 않음).

```bash
docker compose -f ../../neo4j/compose.yml up -d
```

```bash
export NEO4J_PASSWORD=$(grep '^NEO4J_PASSWORD=' ../../neo4j/.env | cut -d= -f2-)
```

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
```

```bash
cd ../../retriever/vector-retriever && .venv/Scripts/python ../../verify/neo4j-vector-search/tools/export_fixture.py
```

```bash
.venv/Scripts/python -m pytest -q
```

```bash
.venv/Scripts/python -m pytest -q -s -m ollama
```

- 접속값은 `.env.example`(시험 전용 값). 시험은 시작할 때 Neo4j DB를 비우므로 시험 전용 컨테이너에만 씀
- APOC는 이미지 안 `labs/apoc-2026.09.0-core.jar`에서 설치됨(추가 다운로드 없음). 저장기·병합기가 APOC를 씀

## 결과(2026-10-13, Neo4j 2026.09.0 Community · neo4j-graphrag 1.22.0)

- `pytest -q`: 24 passed / `pytest -m ollama`: 1 passed(청크 2개 153.1초)
- 시험 자료: 검색기 사용 중 세대 `gen-ch2-20261003-001-17151790`(청크 218 · KURE-v2 768차원), 평가 질문 20 × 역할 3

| 확인 항목 | 결과 |
|-----------|------|
| 청크 218개 저장, chunk_id 속성 유지, 임시 ID 제거, 기존 벡터 그대로(오차 < 1e-6) | 통과 |
| Document · FROM_DOCUMENT · NEXT_CHUNK 생성, 벡터 인덱스 ONLINE | 통과 |
| 벡터 상위 10 순서 = 기존 Chroma(60/60) | 통과(아래 설계 수정 반영 후) |
| 하이브리드(기존 BM25 + 기존 가중합 0.6 : 0.4) 순위 = 기존 | 통과(60/60) |
| 그래프 확장(FROM_CHUNK → 엔티티 → 관계), 다른 세대 섞임 없음 | 통과 |
| 포인터 게시 → 전환 → 되돌리기, 검증 실패 시 게시 거부 | 통과 |
| 세대 범위 병합(filter_query): 다른 세대를 건드리지 않음 | 통과 |
| 저장기 CREATE: 같은 세대 재실행 시 청크 2배 → 검증 실패 | 재현 |
| 병합 범위를 안 좁히면 두 세대 엔티티가 한 노드로 합쳐짐 | 재현 |
| 실제 LLM(gemma-4 12B) 추출 JSON → 노드 · FROM_CHUNK | 통과(스키마 없이 라벨이 제각각) |

## 시험으로 드러난 설계 수정 사항

1. **기본 VectorRetriever는 필터를 늘 전수 비교로 처리함** — 인덱스는 `WITH [n.prop]`로 만들고 Neo4j 2026.09는 그 속성을
   `properties`에 보여 주는데, 검색기는 `options.indexConfig.vector.filterable_properties`만 읽음.
   `FilterAwareVectorRetriever`(하위 클래스)로 우회함
2. **서버가 `$ne`를 거부함** — 라이브러리는 인덱스 안 처리로 분류하지만 SEARCH 필터는 =·범위의 AND만 받음.
   `$or`·`$in`도 전수 비교
3. **회원 필터를 '후보 4배 받아 앱에서 거르기'로 하면 틀림** — E07 · E09 · E10에서 그 회원 상담 조각이 빠짐.
   `member_scope`(상담 아님 = "all", 상담 = 회원 가명)를 두고 `$eq "all"` · `$eq 회원` 검색 2번을 합쳐 정확히 맞춤
4. **Neo4j 2026.09 벡터 인덱스 기본 압축은 BINARY** — 후보 배수(effective_search_ratio) 1이면 순서 일치 40/60,
   2이면 56/60, 4 이상이면 60/60. 기본값 4로 둠
5. **기존 하이브리드는 RRF가 아니라 가중합**(`weighted_hybrid`, 최소-최대 정규화). Neo4j 점수 (1+cos)/2와
   Chroma 점수 cos는 값이 달라도 정규화 뒤 같아 순위가 같음

## 한계

- BM25는 기존 세대 1개만 있어, BM25 쪽 세대 전환은 포인터 값(`search_index_root`) 대조까지만 확인함
- 엔티티 추출 품질은 보지 않음(가짜 LLM). 실제 LLM은 형식 · 연결만 확인
- 데이터 218건 규모의 결과임 — 대규모에서 압축 · 후보 배수 영향은 다시 재야 함
