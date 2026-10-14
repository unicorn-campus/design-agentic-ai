# GraphRAG 대표 프레임워크 3종 — PPT 스크립트

- 산출물: `temp/graphrag-frameworks/GraphRAG프레임워크.pptx` (1장)
- 작성: 클로니(직접 수행), 2026-10-13
- 입력: cna-bootcamp/aistudy `agentic-ai/textbook/14.GraphRAG.md` 「2.3 Knowledge Graph 구축 프레임워크」  
  (2.4 MS GraphRAG · 2.5 LangChain+Neo4j · 2.6 LightRAG 상세 절 함께 참조)
- 순서(사용자 지정): Neo4j → MS GraphRAG → LightRAG
- 스타일: `references/pptx-guide.md` — `내용_단쪽` 레이아웃, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음
- 앞 장표 「그래프 검색 3가지 방식」과 용어 · 색 · 각주 문구를 맞춤

## 원문 대비 고친 곳(1차 출처로 확인)

| 원문(14.GraphRAG.md) | 판정 | 슬라이드 반영 |
|----------------------|------|---------------|
| Neo4j 계열 Hybrid = "Local + Global 결합" | 부분 | `neo4j-graphrag` HybridRetriever는 벡터 + 전문(키워드) 검색 결합. 원문 2.5.2의 LangChain 예는  
  벡터 + 1홉 그래프 확장. 어느 쪽도 Local + Global 결합 기능은 아님 → "결합 기능 없음, 검색기 조합해 직접 구성" |
| LightRAG Hybrid = "Mix 모드" | 틀림 | README: hybrid = local + global, mix = local + global + naive(원문 조각 벡터). Hybrid 줄은 hybrid로 표기 |
| LightRAG 그래프 저장 = "Neo4j 또는 자체 JSON" | 부분 | 기본 그래프 저장은 NetworkX(.graphml 파일). README: 기본 저장소 4종은 메모리 기반으로  
  테스트용이며 운영 부적합 → "기본은 파일(테스트용)" |
| MS GraphRAG 현재 상태 언급 없음(2026.1 기준 원문) | 보완 | README 공지(2026-08-14): 유지보수 모드 → 각주 |
| Neo4j GDS 사전 요약은 유료 | 틀림 | GDS 문서: Community Edition(무료)에 Leiden 포함 모든 알고리즘. 유료는 4코어 초과 · 클러스터 쓰기 등 운영 기능.  
  커뮤니티 요약은 GDS 기능이 아니라 LLM으로 따로 만듦. 슬라이드에는 넣지 않음 |
| 도입 사례 수치(65% 점유, 63% 단축, 65 ~ 80% 절감 등) | 미반영 | 1차 출처 미확인 |
| "LangChain + Neo4j가 더 많이 사용됨" | 미반영 | PyPI 월 다운로드(2026-10-13): `neo4j-graphrag` 296,514 · `langchain-neo4j` 143,552로 반대.  
  사용 빈도 비교는 슬라이드에 넣지 않음 |

## 재검증(2026-10-13, 지식니 2건 병렬 조사 + 클로니 표본 확인)

### 기술 주장(C1 ~ C11)

| 번호 | 원문 주장 | 판정 | 바른 내용 |
|------|-----------|------|-----------|
| C1 | Neo4j 계열 Hybrid = Local + Global 결합 | 틀림 | `neo4j-graphrag` HybridRetriever · `langchain-neo4j` search_type="hybrid" 모두 벡터 + 전문(키워드) 검색.  
  원문 2.5.2의 '벡터 + 1홉 확장'은 프로젝트가 직접 만든 구성 |
| C2 | LightRAG Hybrid = Mix 모드 | 틀림 | hybrid = local + global, mix = 여기에 원문 청크 벡터(naive)까지. mix가 기본 모드 |
| C3 | LightRAG 그래프 = Neo4j 또는 자체 JSON, 외부 의존성 없음 | 부분 | 기본은 메모리 + 파일(그래프 .graphml, 벡터 · KV JSON). README: 시험용, 운영은 PostgreSQL 등 권장 |
| C4 | MS 증분 업데이트 v0.5.0+, 커뮤니티 재계산 필요 | 부분 | CHANGELOG: v0.4.0 증분 인덱싱, v0.4.1 `update` CLI. update는 새 커뮤니티를 기존 뒤에 이어 붙일 뿐  
  재계산하지 않음 → 품질 위해 전체 재인덱싱이 안전. 신규 판정이 제목 기준이라 내용만 바뀐 문서는 감지 못함 |
| C5 | LightRAG MD5 문서 ID, delete_by_doc_id → ainsert | 맞음 | 사용자 지정 doc_id도 가능 |
| C6 | Neo4j GDS 사전 요약 유료 | 틀림 | 위 표 참조 |
| C7 | Cypher AI 프로시저(2025.12), Enterprise 필요 | 부분 | GenAI 플러그인: 2025.11 `ai.text.completion`, 2025.12 `ai.text.chat`, 2026.02 `ai.text.structuredCompletion`.  
  Cypher 25(Neo4j 2025.06+) 필요, 문서에 Enterprise 조건 없음. 외부 LLM API 키 필요 |
| C8 | LlamaIndex PropertyGraph에 hierarchical_leiden · 요약 내장 | 틀림 | 코어에 없음. 쿡북에서 graspologic `hierarchical_leiden`을 직접 붙임 |
| C9 | LightRAG EMNLP 2025 논문 | 미확인 | arXiv 2410.05779(2024) 페이지 · README 인용에 EMNLP 표기 없음 |
| C10 | MS 벡터 LanceDB 기본 · 그래프 Parquet | 맞음 | Parquet은 기본 출력, Blob · CosmosDB로 변경 가능 |
| C11 | LightRAG 커뮤니티 회피 · Citation · 각종 스토리지 | 맞음 | — |

### 도입 사례 · 수치(N1 ~ N7)

| 번호 | 원문 주장 | 판정 | 실제 |
|------|-----------|------|------|
| N1 | LangChain + Neo4j 65% 점유 · 더 많이 사용 | 출처 없음 | 개인 블로그 1건뿐. PyPI · GitHub 지표는 반대 |
| N2 | Spider-Graph 92% 정확도 | 출처 없음 | 해당 벤치마크 없음 |
| N3 | MS GraphRAG 도입: Fortune 500 · 의료 · LinkedIn, 63% · 18% | 일부 다름 | LinkedIn은 자체 KG-RAG(SIGIR 2024, arXiv 2404.17723),  
  해결 시간 중앙값 28.6% 단축. 나머지 사례 · 수치는 출처 없음 |
| N4 | 글로벌 질문 70 ~ 80% 우위 | 확인 | naive RAG 대비, 포괄성 · 다양성, GPT-4 심판 쌍대 비교(MS 블로그 · arXiv 2404.16130) |
| N5 | LightRAG 65 ~ 80% 비용 절감, ~80ms, 월 1,500+ 문서 | 다름 · 출처 없음 | 논문 Fig.2: 법률 데이터셋 검색 단계 토큰 610×1000 → 100 미만(논문 자체 분석).  
  80ms · 1,500건은 출처 없음 |
| N6 | LazyGraphRAG 인덱싱 99% 절감, 오픈소스 미공개 | 수치 다름 · 공개 여부 맞음 | 인덱싱 비용 = 벡터 RAG 수준 = full GraphRAG의 0.1%(99.9%), 글로벌 질의 700배 이상 저렴 |
| N7 | 기업 지식베이스 분기 ~ 반기 갱신 표 | 출처 없음 | 조사 자료 없음 |

## Neo4j Global 줄 추가(2026-10-13)

- 추가: "(선택) GDS 커뮤니티 + LLM 요약". GDS는 커뮤니티 탐지만 하고 요약문은 LLM이 작성
- 방법 1: Neo4j Labs LLM Graph Builder(Apache 2.0) — `gds.leiden.write` → 커뮤니티별 LLM 요약 → `__Community__.summary`,  
  `gds.version()`으로 GDS 유무 확인 후 커뮤니티 기능 사용, Ollama 지원
- 방법 2: GenAI 플러그인 Cypher AI 함수(`ai.text.completion` 등) — OpenAI · Azure OpenAI · VertexAI · Bedrock만 지원, Cypher 25 필요
- 라이선스: Operations Manual「Configure plugins」— CE · EE 모두 GDS · GenAI를 products 폴더에 포함,  
  "Graph Data Science는 CE · EE 모두 사용 가능, Enterprise 추가 기능만 라이선스 키 필요". GenAI는 라이선스 표기 없음
- 미확인: Aura 무료 티어의 GDS 사용 가능 여부

## 근거(스크립트에만 기록)

- 14.GraphRAG.md 2.3 ~ 2.6: https://github.com/cna-bootcamp/aistudy/blob/main/agentic-ai/textbook/14.GraphRAG.md
- neo4j-graphrag-python User Guide RAG(검색기 분류: Vector · VectorCypher · Hybrid · HybridCypher · Text2Cypher)
- MS GraphRAG: README(유지보수 모드 공지), docs/config/yaml.md(vector_store 기본 lancedb), cli `graphrag update` 명령,  
  docs/query(local · global · drift)
- LightRAG: README(모드 정의, 기본 저장소 · 운영 부적합 안내, 증분 업데이트 · 선택 삭제), `lightrag.py`(`ainsert` · `adelete_by_doc_id`)

## 슬라이드 1 — GraphRAG 대표 프레임워크: Neo4j · MS GraphRAG · LightRAG

- 리드문: 그래프를 어디에 담고, 전체를 묻는 질문을 어떻게 푸는지가 세 프레임워크의 가장 큰 차이
- 도형 구성: 세로 카드 3개(Neo4j 네이비 · MS GraphRAG 블루 · LightRAG 다크 슬레이트)
  - 머리 바: 이름 + 작은 부제
  - 한 줄 정체성(틴트 상자)
  - 인덱싱: 단계 칩 5개(청킹 · 추출 · KG 저장 · 요약 · 임베딩). 요약 칩은 MS만 채움, 나머지는 회색 점선(없음)
  - 저장소: 그래프 · 벡터 상자. Neo4j는 한 상자 안에 둘 다(통합), MS · LightRAG는 따로(분리)
  - 행 4개(왼쪽 필 라벨 + 설명): Local · Global · Hybrid · 문서 갱신
  - 맨 아래 색 띠: 이럴 때 고름
- 각주: ※ 1) MS GraphRAG는 현재 유지보수 모드(사용자 수정 17:13 — 이름 뒤 위첨자 "1)"로 표기)

| 구분 | Neo4j | MS GraphRAG¹⁾ | LightRAG |
|------|-------|--------------|----------|
| 부제 | Neo4j GraphRAG · LangChain + Neo4j | Microsoft Research | HKUDS · 경량 GraphRAG |
| 정체성 | 그래프 DB에 담고 Cypher로 직접 묻기 | 미리 요약해 두어 전체 질문에 강함 | 요약 없이 가볍게, 듀얼레벨 키워드로 찾기 |
| 인덱싱 | 청킹 → 추출 → KG 저장 → 임베딩 | 청킹 → 추출 → KG 저장 → **사전 요약** → 임베딩 | 청킹 → 추출 → KG 저장 → 임베딩 |
| 저장소 | Neo4j 하나(그래프 + 벡터 인덱스) | Parquet 파일(그래프) + LanceDB(벡터) | 그래프(파일 · Neo4j 등) + 벡터(내장 · Milvus 등) |
| 저장소 설명 | 한 DB에 통합 | 그래프 DB 불필요 | 기본은 파일(테스트용) |
| Local | 벡터로 진입점 → Cypher로 주변 탐색 | 엔티티 벡터 → 1홉 관계 · 원문 · 리포트 | Low-level 키워드 → 엔티티 벡터 |
| Global | Cypher 조건 · 집계 + LLM 요약, (선택) GDS 커뮤니티 + LLM 요약 | 커뮤니티 리포트 map-reduce | High-level 키워드 → 관계 벡터 |
| Hybrid | 'Hybrid' = 벡터 + 키워드 검색, Local + Global 결합은 직접 구성 | DRIFT: 요약 → 후속 질문 → Local | hybrid: Low + High 둘 다, 기본 mix는 원문 벡터까지 추가 |
| 문서 갱신 | MERGE로 중복 없이 추가, Cypher로 지우고 재삽입 | update는 새 문서만 이어 붙임, 수정 · 삭제는 전체 재인덱싱이 안전 | 새 문서는 바로 병합, 수정은 문서 삭제 후 재삽입 |
| 이럴 때 | 정형 데이터와 함께 쓰고 조건 · 집계 질문이 많을 때 | 전체 주제 요약 품질이 최우선일 때(인덱싱 비용 감수) | 비용 · 속도가 중요하고 문서가 자주 늘 때 |

### 발표자 노트

- 세 프레임워크 모두 엔티티 · 관계를 LLM으로 뽑아 그래프를 만들고, 벡터로 진입점을 찾는 점은 같음
- 차이 ① 저장: Neo4j는 DB 하나에 다 담고, MS는 파일 + 벡터 DB, LightRAG는 기본 파일(운영은 외부 DB)
- 차이 ② 전체 질문: Neo4j는 Cypher로 조건 · 집계, MS는 미리 만든 커뮤니티 요약, LightRAG는 상위 키워드로 관계 검색
- 차이 ③ 갱신: MS는 커뮤니티를 다시 계산해야 해 전체 재인덱싱이 안전하고, LightRAG는 문서 단위 추가 · 삭제가 쉬움
