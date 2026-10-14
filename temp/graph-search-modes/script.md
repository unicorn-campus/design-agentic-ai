# 그래프 검색 3가지 방식 — PPT 스크립트

- 산출물: `temp/graph-search-modes/그래프검색방식.pptx` (1장)
- 작성: 클로니(직접 수행) — 사실 검증은 지식니(2026-10-13), 클로니가 MS GraphRAG 원문으로 교차 확인
- 입력: 사용자가 준 「검색 단계」 슬라이드(Local · Global · Hybrid 3카드 + Global 3방식)
- 스타일: `references/pptx-guide.md` — `내용_단쪽` 레이아웃, Pretendard, 14pt 이상, 출처 줄 없음, 편집 가능 도형

## 검증 결과(원본 대비 고친 곳)

| 원본 문장 | 판정 | 고친 내용 |
|-----------|------|-----------|
| Local 1 "핵심 엔티티·키워드 식별" | 부분 | MS GraphRAG는 질문 임베딩 ↔ 엔티티 설명 임베딩 매칭. 키워드 추출은 LightRAG 방식 → 각주로 분리 |
| Local 3 "관련 관계 확장" | 부분 | 관계 외에 이웃 엔티티 · 커뮤니티 리포트 · 원문 조각까지 확장 |
| Local 4 "컨텍스트 수집 → 답변" | 부분 | 순위를 매겨 컨텍스트 창 하나에 맞추는 단계 추가 |
| Global 1 "광범위 주제·테마 식별" | 틀림 | MS 기본 Global에 주제 식별 단계 없음. 한 계층의 커뮤니티 리포트를 그대로 씀 |
| Global 3 "컨텍스트 통합(커뮤니티, 엔티티/관계)" | 틀림 | Global 컨텍스트는 커뮤니티 리포트만 씀. map(나눠 답하기) → reduce(요점 추려 합치기)로 수정 |
| Hybrid "Local + Global 병행" | 부분 | Hybrid는 LightRAG 모드명(local · global · hybrid · naive · mix). MS GraphRAG에는 Hybrid가 없고  
  비슷한 역할의 DRIFT(리포트로 큰 답 → 후속 질문 → Local 반복)가 있음 → 각주 |
| ① 커뮤니티 요약 "질문 관련 리포트 탐색" | 틀림 | 기본은 리포트 전체를 묶음으로 나눠 map-reduce. 관련 리포트만 고르는 동적 선택은 옵션 |
| ② High-level 키워드(LightRAG) | 맞음(보완) | 상위 키워드는 관계(relationship) 벡터와, 세부 키워드는 엔티티 벡터와 매칭 |
| ③ Cypher 쿼리 집계(Neo4j) | 부분 | Neo4j는 'Global Search' 범주가 없고 Text2Cypher는 검색기 종류 중 하나. 개수 · 순위 같은  
  집계형 거시 질문에 쓰는 다른 길로 표현 |

## 근거(스크립트에만 기록, 슬라이드에는 넣지 않음)

- MS GraphRAG Query 문서: overview · local_search · global_search · drift_search  
  https://microsoft.github.io/graphrag/query/overview/
- MS GraphRAG 설정 문서 `dynamic_search_*`(동적 커뮤니티 선택 옵션)  
  https://github.com/microsoft/graphrag/blob/main/docs/config/yaml.md
- LightRAG 소스 `lightrag/base.py`(모드 정의), `lightrag/operate.py`(hl_keywords → 관계 VDB, ll_keywords → 엔티티 VDB)  
  https://github.com/HKUDS/LightRAG
- LlamaIndex GraphRAG cookbook v1 · v2(커뮤니티 요약 구현)  
  https://github.com/run-llama/llama_index/tree/main/docs/examples/cookbooks
- neo4j-graphrag-python User Guide RAG(검색기 분류, Text2Cypher)  
  https://github.com/neo4j/neo4j-graphrag-python/blob/main/docs/source/user_guide_rag.rst

## 사용자 직접 수정 반영(2026-10-13 15:53 판)

- 사용자가 pptx에서 문구 6곳을 직접 고침(위치 · 크기 변경 없음). 원본 백업: `그래프검색방식.user-1553.pptx`
- 클로니 검토: 6곳 모두 원 출처(MS GraphRAG `local_context.py` · `global_search/search.py` · DRIFT 문서,  
  LightRAG `prompt.py` · `operate.py`)와 일치. build.js에 그대로 옮겨 다시 빌드 후 도형 137개 문구 · 위치 일치 확인

## 아래 띠 셋째 줄 변경(2026-10-13): '잘 맞는 질문' → '방식의 특징'

- 이유: 세 프레임워크 모두 주제 · 경향 질문을 다룰 수 있어 질문 유형으로 구분되지 않음(사용자 지적)
  - MS Global 문서: "top 5 themes" 같은 데이터 전체 집계 질문 / LightRAG README global: 큰 주제 · 요약 · 추세 분석
  - Neo4j: Text2Cypher 결과를 LLM이 받아 답함. LLM Graph Builder(neo4j-labs)는 GDS Leiden 커뮤니티 + 요약 +  
    `global_vector` 모드(커뮤니티 요약 top-k 검색) 제공 — `neo4j-graphrag-python` 기본 검색기에는 없음
- 차이는 읽는 범위: MS = 한 계층 리포트 전부(map-reduce), LightRAG = 상위 키워드와 맞는 관계 top-k,  
  Neo4j = Cypher 조건으로 대상을 좁혀 집계 후 LLM 요약
- 「그래프 검색이 필요한 이유」 장표 ③ 질문(해지 문의 회원들의 공통 원인 · 거절 제안)은 조건으로 좁힌 집단의 경향이라  
  Neo4j(Cypher 필터 · 집계 + LLM 요약)가 적합. 단, 불만 원인이 노드로 추출돼 있어야 집계가 정확함(스키마 미확인)

## 슬라이드 1 — 그래프 검색 3가지 방식: Local · Global · Hybrid

- 리드문: 질문이 묻는 범위(한 대상 / 전체 / 둘 다)에 따라 그래프에서 꺼내는 재료와 순서가 달라짐
- 도형 구성
  - 위: 세로 카드 3개(Local 네이비 · Global 블루 · Hybrid 다크 슬레이트)
    - 머리 바: 방식 이름 + 질문 유형
    - 예시 질문 상자(틴트)
    - 미니 그래프: 검색 범위를 점·선으로 그림
      - Local: Q(파란 원) + 엔티티 4개를 Q와 다른 거리로 배치(점선 = 뜻 거리). 가까운 2개(채움)가 진입점,  
        진입점끼리 관계 1개 + 진입점마다 1홉 이웃 2개(실선). 진입점마다 원문 조각 아이콘을 회색 선으로 붙임.  
        오른쪽 범례(진입점 · 뜻 거리 · 관계 (1홉) · 원문 조각)
      - Global: 리포트 3묶음 → map(묶음마다 중간 답) → reduce(최종 답). 열 머리에 「리포트 묶음 · map · reduce」
      - Hybrid: Local(세부 근거) + Global(전체 맥락) → 결합. 결합 방법은 프레임워크별 행으로 따로 보여 줌
    - Local · Global: 4단계(번호 배지 + 한 줄 설명) + 각주(회색) 한 줄
    - Hybrid: 단계 대신 「결합 방법은 프레임워크마다 다름」 + 프레임워크 3행(Neo4j · MS GraphRAG · LightRAG)
  - 아래: 「대표 프레임워크의 Global 질문 처리」 띠 — 상자 3개(프레임워크 이름 + 방법, 설명 한 줄, 잘 맞는 질문 한 줄)  
    + 띠 아래 MS GraphRAG 유지보수 모드 각주 한 줄

### 카드 내용

| 구분 | Local Search | Global Search |
|------|--------------|---------------|
| 질문 유형 | 한 대상을 깊게 묻는 질문 | 문서 전체를 조망하는 질문 |
| 예시 | 예) A카드의 해외 결제 혜택은? | 예) 고객 불만의 주요 주제는? |
| 1 | Q와 뜻이 가까운 엔티티 몇 개를 진입점으로 찾기 | 한 계층의 커뮤니티 리포트를 묶음으로 나누기 |
| 2 | 진입점에서 뻗은 관계(1홉)와 관계 설명을 근거 후보에 넣기 | map: 묶음마다 따로 중간 답 쓰기 |
| 3 | 진입점의 원문 조각 · 리포트도 근거 후보에 넣기 | reduce: 중간 답 안의 요점별 중요도 점수로 골라 합치기 |
| 4 | 토큰 한도에 맞게 추려 LLM이 답변 | 전체 조망 답변 생성 |
| 각주 | LightRAG는 1단계를 세부(Low-level) 키워드로 수행 | 관련 리포트만 골라 사용하는 동적 선택은 옵션 |

- Local 보충(2026-10-13 사용자 질문 반영): 원문 조각은 이웃이 아니라 **진입점 엔티티가 나온 조각**만 가져옴.  
  MS GraphRAG `mixed_context.py` `_build_text_unit_context` — 선택 엔티티의 text_unit_ids만 모아 엔티티 순서 · 관계 수로 정렬.  
  리포트도 진입점이 속한 커뮤니티 것. 이웃은 진입점에 직접 연결된 엔티티 · 관계(1홉)만.  
  LightRAG `operate.py` `_merge_all_chunks` — 진입점 엔티티의 조각 + 그 1홉 관계를 뽑은 조각.  
  진입점은 1개가 아니라 top-k 여러 개. Neo4j는 `VectorCypherRetriever`의 Cypher 질의로 홉 · 조각 범위를 직접 정함
- Local 보충 2(2026-10-13): '근거 후보'는 답변 후보가 아니라 LLM 프롬프트에 넣을 재료 후보임.  
  MS 기본 토큰 몫(코드 기본값): 전체 8,000 중 원문 조각 50% · 커뮤니티 리포트 25% · 엔티티 · 관계 표 25%.  
  엔티티 표에는 진입점만 들어가고, 1홉 이웃은 관계 표의 한 줄(진입점 → 이웃 + 관계 설명)로만 들어감  
  (`local_context.py` `_filter_relationships`: in-network + out-network, 진입점 여러 개와 이어진 이웃 우선).  
  이웃의 조각 · 리포트를 안 넣는 이유는 문서에 명시 없음 — 토큰 예산 · 관계 설명이 이미 요약 · 질문과의 거리(클로니 의견)
- Global 보충(2026-10-13 사용자 지적 반영): map은 '점수 매기기'가 아니라 '묶음마다 따로 답하기'임.  
  map이 쓴 중간 답의 요점마다 LLM이 0 ~ 100 중요도 점수를 함께 붙이고, reduce가 그 점수로 요점을 골라 합침

**Hybrid Search** — 한 대상 + 전체 흐름을 함께 묻는 질문 / 예) A카드 혜택은 업계 흐름과 어떻게 다른가?

| 프레임워크 | 결합 방법 |
|------------|-----------|
| Neo4j | 'Hybrid' = 벡터 + 키워드 검색(뜻이 다름). Local + Global 결합은 직접 설계 |
| MS GraphRAG | DRIFT: 요약으로 큰 답 → 후속 질문마다 Local 검색 (순서대로) |
| LightRAG | 듀얼 레벨(hybrid 모드): 세부(Low-level) 키워드 → 엔티티 + 상위(High-level) 키워드 → 관계, 둘 다 사용. 코드상 두 검색을 차례로 돌린 뒤 결과를 번갈아 섞어(라운드 로빈) 중복 제거 |

- 근거: Neo4j `HybridRetriever`(벡터 + 전문 검색) · `HybridCypherRetriever`(+ Cypher 확장), MS GraphRAG DRIFT 문서,  
  LightRAG README 모드 정의. 이전 판은 LightRAG 방식만 그려 다른 두 프레임워크에 맞지 않았음(사용자 지적)

### 대표 프레임워크의 Global 질문 처리 (2026-10-13 개정)

- 순서: Neo4j → MS GraphRAG → LightRAG (사용자 지정)
- LlamaIndex 제외: 커뮤니티 요약은 쿡북(예제) 수준이고 코어 PropertyGraphIndex에 Global 검색이 없음
- 대표 선정 근거(지식니 조사, 2026-10-13 수집, 클로니가 수치 6개 재확인)

| 프레임워크 | GitHub 별 | PyPI 월 다운로드 | 비고 |
|------------|-----------|------------------|------|
| Neo4j GraphRAG (`neo4j-graphrag`) | 1,308 | 296,514 | Global 검색 범주 없음. 집계형 질문은 Text2Cypher로 처리 |
| MS GraphRAG (`graphrag`) | 36,312 | 50,897 | v3.3.0(2026-10-08). README 공지(2026-08-14 추가): 유지보수 모드 |
| LightRAG (`lightrag-hku`) | 40,098 | 122,085 | local · global · hybrid · naive · mix 모드 |

| 프레임워크 | 방법 | 설명 | 방식의 특징 |
|------------|------|------|-------------|
| ① Neo4j GraphRAG | Text2Cypher | 질문을 Cypher로 바꿔 그래프 전체를 집계 | 조건으로 대상을 좁혀 정확히 집계 · 요약은 LLM |
| ② MS GraphRAG※ | 커뮤니티 요약 | 미리 만든 커뮤니티 요약을 나눠 답하고 합침 | 전체 리포트를 다 훑음 · 빠짐없지만 비용 큼 |
| ③ LightRAG | High-level 키워드 | 질문의 상위(High-level) 키워드로 관계 벡터 검색 | 맞는 관계만 골라 봄 · 가볍지만 놓칠 수 있음 |

- 각주(슬라이드 표시, 2026-10-13 15:59 사용자 수정): ※ MS GraphRAG는 현재 유지보수 모드: 새 기능 추가 없이 버그 · 보안 수정만 이어 가는 상태 (2026-08 공지).  
  Local · Global · DRIFT 개념의 원형으로 참고
- 근거: https://github.com/microsoft/graphrag README "largely in maintenance mode … won't be accepting new PRs or  
  implementing new features" (커밋 "Add notice. (#2486)", 2026-08-14)
- 참고(슬라이드 미반영): LazyGraphRAG(2024-11 MS Research 블로그)는 사전 요약 없이 질문 시점에 탐색하는 별도 방식.  
  오픈소스 저장소에 구현 없음, Microsoft Discovery · Azure Local 공개 미리보기로만 제공(블로그 편집자 주 2025-06-06)

### 발표자 노트

- Local은 '한 점에서 출발해 이웃으로 넓히기', Global은 '미리 만든 요약들을 나눠 읽고 합치기'임
- Hybrid라는 이름은 LightRAG의 모드 이름이고, MS GraphRAG에서 같은 역할은 DRIFT가 맡음.  
  DRIFT는 동시에 돌리지 않고 '요약으로 큰 답 → 후속 질문 → Local 반복' 순서로 진행함
- Global의 기본 동작은 관련 리포트를 골라 읽는 것이 아니라 한 계층의 리포트를 전부 나눠 읽는 것이라 비용이 큼.  
  관련 리포트만 고르는 동적 선택은 비용을 줄이는 옵션임
- Cypher 집계는 '몇 개' · '가장 많은' 같은 숫자형 거시 질문에 강하고, 주제 요약형 질문에는 커뮤니티 요약이 맞음
- MS GraphRAG는 2026-08부터 유지보수 모드(새 기능 없음, 버그 · 보안 수정만)이지만 검색 방식 개념의 원형이라 소개함
