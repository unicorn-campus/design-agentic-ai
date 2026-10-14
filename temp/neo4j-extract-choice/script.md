# 엔티티·관계 추출 도구 선택: LangChain + Neo4j vs Native Neo4j — PPT 스크립트

- 산출물: `temp/neo4j-extract-choice/Neo4j추출도구선택.pptx` (1장)
- 작성: 클로니(장표) · 지식니(조사), 2026-10-13
- 위치: 「그래프DB 인덱싱 과정」 장표의 ④ 엔티티·관계 추출 상세 앞 — 도구 결정용
- 스타일: `references/pptx-guide.md` — `내용_단쪽` 레이아웃, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음
- 색: A(LangChain) = 블루 `#2E74C6`, B(Native) = 네이비 `#1E2A5C`

## 조사 중 바로잡은 전제(1차 출처로 확인)

| 전제 | 판정 | 실제 |
|------|------|------|
| `langchain_experimental.graph_transformers.LLMGraphTransformer` 사용 | 틀림 | `langchain-experimental` 저장소 보관 처리(archived: true, 마지막 푸시 2026-05-22).  
  현재 경로는 `from langchain_neo4j import LLMGraphTransformer` |
| A와 B는 서로 다른 별개 도구 | 부분 | `langchain-neo4j` 0.11.0 의존성에 `neo4j-graphrag>=1.12.0` 포함. 추출기는 각자 구현,  
  스키마 · 벡터 배관은 A가 B를 가져다 씀 |
| Neo4j 공식 LLM Knowledge Graph Builder = Native 사용 | 틀림 | 백엔드 `src/llm.py` 7행 `from langchain_neo4j import LLMGraphTransformer` |
| A는 병합 기능 없음(지식니 보고) | 부분 | `add_graph_documents`가 `MERGE (n {id})`로 저장 → **이름이 완전히 같은 노드는 자동 합침**.  
  이름이 조금 다른 노드(유사 이름) 병합은 없음 — 클로니 확인(`.temp/lcn-graph.py` 30행) |
| 삼중쌍(출발-관계-도착) 제약은 B만 지원(지식니 보고) | 틀림 | A의 `allowed_relationships`도 3개 묶음 목록을 받음(`.temp/lcn-llm.py` 696행) → 장점 목록에서 뺌 |
| B 병합 | 확인 | `SimpleKGPipeline` 기본으로 같은 라벨 · 같은 이름 병합(`perform_entity_resolution=True`),  
  유사 이름은 `FuzzyMatchResolver` · `SpaCySemanticMatchResolver`를 따로 붙임 |

## 실무 사용도 수치(2026-10-13 조회)

| 지표 | A `langchain-neo4j` | B `neo4j-graphrag` | 출처 |
|------|--------------------|--------------------|------|
| PyPI 최근 1개월 다운로드 | 143,552 | 296,514 | https://pypistats.org/api/packages/langchain-neo4j/recent · …/neo4j-graphrag/recent |
| GitHub 최근 90일 커밋 | 15 | 89 | GitHub API `/commits?since=2026-07-13` (지식니 조회) |
| GitHub 별 | 41 | 1,308 | 슬라이드 미반영 — A는 LangChain 본체의 위성 저장소라 별이 모이지 않아 비교 왜곡 |
| 최신 버전 | 0.11.0 (2026-10-09) | 1.22.0 (2026-10-01) | PyPI JSON |

- 다운로드는 사람 수가 아니라 설치 횟수(CI · 도커 반복 설치 포함)
- A를 설치하면 B가 함께 깔리므로 B 수치에 A 몫이 일부 섞임. 그래도 B 단독분(약 15만)이 A 이상(계산값, 추정)
- 두 방식 추출 품질을 비교한 벤치마크는 찾지 못함 → 품질 우열은 슬라이드에 넣지 않음
- 기업 이름 단위 도입 사례 · 설문 자료 없음

## 근거(스크립트에만 기록)

- langchain-neo4j: https://github.com/langchain-ai/langchain-neo4j , PyPI JSON(의존성)
- langchain-experimental 종료: https://github.com/langchain-ai/langchain-experimental , 이슈 #87
- neo4j-graphrag: https://github.com/neo4j/neo4j-graphrag-python , User Guide KG Builder(SimpleKGPipeline · 병합 기본값 · 스키마 patterns)
- resolver 클래스: `neo4j_graphrag.components.resolver`(SinglePropertyExactMatchResolver · SpaCySemanticMatchResolver · FuzzyMatchResolver)
- LLM Graph Builder: https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/src/llm.py

## v2 변경(2026-10-13, 사용자 결정)

- 사용자 지적: Native에는 정제 · 가명처리 단계가 없음 → 로드 · 정제 · 청킹은 벡터DB 인덱싱과 함께 하고 추출부터 Native로 잇는 구성이 맞음.  
  LangChain 방식은 병합 · 임베딩을 따로 처리해야 해 실무에서 쓰기 어려움
- 확인(원본 코드, `.temp/`에 저장)
  - `simple_kg_builder.py` 106 ~ 112행: 구성요소 = (PDF 로드) · 분할 · 청크 임베딩 · (스키마) · 추출 · 가지치기 · 저장 · 병합 — 정제 · 가명처리 없음
  - `entity_relation_extractor.py` 133행: `run(chunks: TextChunks, document_info=...)` → 미리 만든 청크를 바로 넣을 수 있음
  - `types.py`: `TextChunk(text, index)`, `TextChunks(chunks=[...])` / `kg_writer.py`: `Neo4jWriter(driver).run(graph)` /  
    `resolver.py`: `SinglePropertyExactMatchResolver(driver=...)`
  - 노드 설명 임베딩 · 사전요약(커뮤니티 요약)은 Native 파이프라인에도 없음 → 직접 구성
- 반영: 범위 칩에 '가명처리' 칸 추가(둘 다 없음), B 임베딩 = 청크만(일부), B 코드를 부품 조립형으로, B 단점에 가명처리 없음 추가,  
  사실 카드(공식 KG Builder)는 발표자 노트로 옮기고 판정 카드를 권장 구성 흐름으로 바꿈
- 4번 상세 장표(LangChain 기준)는 사용자 결정으로 그대로 둠

## 슬라이드 1 — 엔티티·관계 추출 도구 선택: LangChain + Neo4j vs Native Neo4j

- 리드문: 둘 다 정제·가명처리는 없음 → 앞단은 벡터DB와 함께 쓰고, 추출부터 Native 부품으로 잇는 구성이 실무에 맞음
- 도형 구성: 좌우 카드 2개(A 블루 · B 네이비) + 아래 실무 사용도 띠
  - 머리 바: 이름 + 패키지 · 핵심 클래스
  - 범위: 단계 칩 7개(로드 · 가명처리 · 청킹 · ④ 추출 · 병합 · KG 저장 · 임베딩). 채움 = 이 도구가 맡음,  
    점선 = 없음(다른 부품 · 직접 코드), 옅은 채움 = 일부만
  - 코드 3줄(핵심 호출)
  - 장점 3 · 단점 3(위아래 상자, 왼쪽 세로 배지)
  - 아래 띠: 막대 2개(월 다운로드 · 90일 커밋) + 판정 카드(권장 구성 칩 흐름)

| 구분 | A. LangChain + Neo4j | B. Native Neo4j |
|------|---------------------|-----------------|
| 부제 | langchain-neo4j · LLMGraphTransformer | neo4j-graphrag · 추출기 · 저장기 · 병합기 부품 |
| 범위 | ④ 추출 · KG 저장(맡음), 병합(같은 이름만), 로드 · 가명처리 · 청킹 · 임베딩(없음) | 로드 · 청킹 · 추출 · 병합 · KG 저장(맡음),  
  임베딩(청크만), 가명처리(없음) |
| 범위 설명 | 병합은 같은 이름만 · 임베딩 연결 · 유사 이름 병합은 직접 조립 | 정제 · 가명처리 없음 · 임베딩은 청크만(노드 설명은 직접) |
| 코드 | `t = LLMGraphTransformer(llm=llm, allowed_nodes=[...])`  
  `docs = t.convert_to_graph_documents(chunks)`  
  `graph.add_graph_documents(docs, include_source=True)` | `ext = LLMEntityRelationExtractor(llm=llm)`  
  `graph = await ext.run(chunks=TextChunks(chunks=my_chunks))`  
  `await Neo4jWriter(driver).run(graph)   # 이어서 병합기 실행` |
| 장점 1 | 코드 3줄로 첫 그래프 — 배우기 · 시연이 빠름 | 벡터DB와 같은 청크를 추출기에 바로 넣음(부품 조립) |
| 장점 2 | LLM 교체 쉬움 — ChatOpenAI · ChatOllama 객체만 바꿈 | 같은 이름 병합 기본, 유사 이름 병합기 선택 |
| 장점 3 | LangChain · LangGraph 흐름에 그대로 끼움 | 문서 – 청크 – 엔티티 연결을 자동으로 만듦 |
| 단점 1 | 추출만 맡음 — 임베딩 연결(Neo4jVector)은 따로 조립 | 개념(컴포넌트 · 파이프라인)이 많아 첫 장벽 높음 |
| 단점 2 | 유사 이름('A사' · 'A사(주)') 병합은 직접 작성 | Neo4j 전용 — 다른 그래프DB로 옮기기 어려움 |
| 단점 3 | 옛 예제의 langchain_experimental 경로는 종료 | 정제 · 가명처리 없음 — 원문 그대로면 실명이 LLM · 그래프로 |

- 실무 사용도(2026-10-13 기준)
  - 월 다운로드(PyPI): A 약 14.4만 · B 약 29.7만
  - 최근 90일 커밋: A 15 · B 89
  - 판정: 운영은 Native(B) — 앞단은 벡터DB 인덱싱과 함께  
    [로드 → 가명처리 → 청킹](벡터DB와 같은 코드 · 같은 청크) → [④ 추출 → KG 저장 → 병합](Native 부품으로 조립)  
    ※ 노드 설명 임베딩 · 사전요약은 어느 쪽이든 직접 · 다운로드는 설치 횟수(B에 A 몫 포함)

### 발표자 노트

- A는 ④ 한 단계 부품, B는 추출기 · 저장기 · 병합기 같은 부품을 이어 붙이는 파이프라인임
- B의 SimpleKGPipeline에는 정제 · 가명처리 단계가 없어, 원문을 넣으면 실명이 LLM에 전달되고 그래프에 저장됨
- 그래서 로드 · 정제 · 가명처리 · 청킹은 벡터DB 인덱싱과 같은 코드로 한 번만 하고, 그 청크를 TextChunks로 바꿔 B 추출기에 넣음
- 둘 다 허용 노드 · 관계 목록과 (출발, 관계, 도착) 묶음으로 스키마를 제한할 수 있음 — 스키마 통제는 차이가 아님
- 병합 차이: A도 저장 시 MERGE로 이름이 완전히 같은 노드는 합침. 'A사' · 'A사(주)' 같은 유사 이름은 A는 직접, B는 Fuzzy · spaCy 병합기
- 노드 설명 임베딩과 사전요약은 어느 쪽에도 없어 직접 만들어야 함
- 사용도: 다운로드 · 개발 활동 모두 B가 큼. 단 Neo4j 공식 데모 도구(LLM KG Builder)는 A로 추출하고, A를 깔면 B도 같이 깔림.  
  학습용 예제는 A가 많음
- 추출 품질 우열을 비교한 공개 벤치마크는 없음
