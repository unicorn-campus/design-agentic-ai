# Graph RAG 최신 트렌드 및 활용 추이

> 작성: 지식니(지식 데이터 엔지니어) | 작성일: 2026-10-15  
> 독자: Agentic AI 아키텍처 교육 수강생(GraphRAG 초심자), 설계 검토자

## 질문 원문

<question>
Graph RAG 최신 트렌드 및 활용 추이 (지식그래프의 이론과 역사, Graph RAG 검색 방식의 장단점, 최신 트렌드)
</question>

## 한 눈에 보는 답

- 지식그래프는 1980 ~ 1990년대 손으로 만든 지식베이스에서 출발해, 2000년대 시맨틱 웹 표준과 자동 지식 추출을 거쳐
  2012년 구글 Knowledge Graph로 대중화됨 [16][17][18]
- Graph RAG는 문서에서 개체와 관계를 뽑아 그래프로 만든 뒤, 그 연결을 따라가며 답을 찾는 검색 방식임 [1][7]
- 전체 문서를 아우르는 질문과 여러 사실을 이어 붙여야 하는 질문에서 강하고, 단순 사실 조회에서는 일반 벡터 RAG와
  차이가 거의 없거나 오히려 뒤처짐 [13][14]
- 2024 ~ 2026년 흐름은 "비용 줄이기(LazyGraphRAG, LightRAG), 벡터와 그래프 섞기, 프레임워크와 클라우드 내장,
  에이전트가 그래프를 도구로 쓰기, 제대로 된 평가 기준 만들기"로 요약됨 [4][11][15][22]
- 결론: GraphRAG는 "무조건 좋은 상위 기술"이 아니라 질문 유형에 따라 선택하는 지식 경로 중 하나임 [13]

---

## 1장. 지식그래프의 이론과 역사

### 1-1. 먼저 알아야 할 용어

| 용어 | 쉬운 설명 |
|------|-----------|
| 노드(Node) | 그래프에서 "점" 하나. 사람, 부품, 회사처럼 이야기의 주인공이 되는 대상임 |
| 엣지(Edge) | 점과 점을 잇는 "선". "A가 B를 만든다" 같은 관계를 나타냄 |
| 트리플(Triple) | "주어 ~ 서술어 ~ 목적어" 세 칸짜리 문장 한 줄. 예: (아이폰, 만든곳, 애플) |
| 온톨로지(Ontology) | 그 분야에서 쓰는 말과 분류를 미리 정해 둔 사전이자 규칙집 |
| 지식그래프 | 노드와 엣지로 사실을 쌓아 둔 큰 지도. 지도를 따라가며 답을 찾을 수 있음 |
| 커뮤니티(Community) | 서로 빽빽하게 연결된 노드 묶음. 그래프에서 "동네" 하나에 해당함 |

비유를 하나만 쓰자면, 벡터 검색은 **비슷한 책을 서가에서 집어 오는 일**이고,  
그래프 검색은 **책 속 인물들의 관계도를 펼쳐 놓고 선을 따라가는 일**임.

### 1-2. 연표

| 시기 | 사건 | 출처 |
|------|------|------|
| 1980 ~ 1990년대 | Cyc, WordNet처럼 사람이 직접 만든 대형 지식베이스 등장. 손으로 만들어 규모에 한계가 있었음 | [16] |
| 2001년 5월 | Berners-Lee, Hendler, Lassila의 "The Semantic Web"이 Scientific American 표지 기사로 실림 | [18] |
| 2000년대 초 | 시맨틱 웹 비전에 따라 도메인 온톨로지와 웹 데이터 표기 표준이 만들어짐. 이때도 대부분 수작업이었음 | [16] |
| 2000년대 | 웹과 문서에서 지식을 자동으로 긁어모으는 연구가 본격화됨. DBpedia, Freebase, YAGO 등이 시작됨 | [16] |
| 2009 ~ 2014년 | W3C가 OWL 2(2012-12-11), SPARQL 1.1(2013-03-21), RDF 1.1(2014-02-25)을 권고안으로 확정함 | [19][20][21] |
| 2012년 5월 16일 | 구글이 Knowledge Graph를 공개함. 공개 당시 객체 5억 개 이상, 사실과 관계 35억 개 이상 | [17] |
| 2010년대 | Wikidata, BabelNet, DBpedia, YAGO가 공개 대형 지식베이스로 자리잡음. 수백만 개체와 수억 ~ 수십억 건의 관계 문장을 담음 | [16] |
| 2024년 ~ | LLM이 문서에서 직접 지식그래프를 뽑아내면서, 지식그래프가 검색 보조 장치(Graph RAG)로 다시 주목받음 | [1][7][8] |

표에서 가장 많이 인용되는 2012년 구글 발표를 조금 더 풀면, 구글은 Knowledge Graph의 재료로 Freebase,
Wikipedia, CIA World Factbook 같은 공개 자료를 썼다고 밝혔음. 발표 취지는 검색어를 "글자 뭉치"가 아니라
"실제 대상"으로 다루겠다는 것이었음 [17].

> **참고**: 1960년대 의미망(Semantic Network) 연구는 지식그래프의 먼 뿌리로 자주 언급되지만, 이 문서는
> 원문 또는 그에 준하는 1차 자료에 접근하지 못해 연표에서 뺌. 확인 가능한 가장 이른 시점은 [16]이 적은
> 1980 ~ 1990년대 Cyc와 WordNet임.

### 1-3. RDF 그래프와 속성 그래프의 차이

지식그래프를 담는 방식은 크게 둘로 나뉨.

- **RDF 그래프**: 모든 사실을 트리플 한 줄로 적음. W3C가 데이터 모델(RDF)[19], 의미 규칙(OWL)[20],
  질의 언어(SPARQL)[21]를 표준으로 정해 두어, 기관 사이에 데이터를 주고받기에 유리함
- **속성 그래프(Labeled Property Graph)**: 노드와 엣지에 이름표와 속성을 직접 매달 수 있음.
  Neo4j의 GraphRAG 파이썬 패키지[23]와 LlamaIndex의 Property Graph Index[24]가 이 방식을 씀

> **의견**: 교육 실습과 사내 프로젝트라면 속성 그래프가 시작하기 쉬움. 노드에 속성을 바로 붙일 수 있어
> 스키마를 빨리 바꿔 볼 수 있기 때문임. 반대로 여러 기관이 데이터를 공유해야 하거나 규제 대응 문서를
> 다룬다면 RDF 표준 쪽이 설명하기 좋음.

---

## 2장. Graph RAG 검색 방식과 장단점

### 2-1. 왜 그래프를 쓰나

Microsoft Research는 일반 RAG가 "이 자료의 핵심 주제는 무엇인가" 같은 **문서 전체를 묻는 질문**에
약하다고 지적함. 이런 질문은 특정 구절을 찾는 일이 아니라 자료 전체를 요약하는 일이기 때문임 [1].  
LightRAG 저자들은 같은 문제를 "자료를 평평한 조각으로만 다뤄 맥락을 놓친다"고 표현함 [11].

Graph RAG는 그래서 **미리 그래프를 만들어 두고 그 연결을 따라가는 방식**을 씀. 그래프 기반 색인,
그래프를 따라가는 검색, 그래프로 보강한 생성의 세 단계로 정리됨 [7].

### 2-2. 대표 검색 방식 6종

#### (1) Local Search ~ 개체 중심 탐색

- **어떻게 찾나**: 질문에 나온 개체를 그래프에서 찾고, 그 개체에 붙은 관계와 원문 조각을 함께 모아 답함 [6]
- **잘 맞는 질문**: "캐모마일의 치유 효능은?"처럼 특정 대상 하나를 깊게 묻는 질문 [6]
- **약점**: 출발점이 질문에 적힌 개체로 한정되어, 시야가 좁음 [3]

#### (2) Global Search ~ 커뮤니티 요약 기반

- **어떻게 찾나**: 인덱싱 때 그래프를 커뮤니티로 나눠 요약문을 미리 만들어 두고, 질문이 오면 모든 요약문에서
  부분 답을 만든 뒤 합침(map-reduce) [1][6]
- **잘 맞는 질문**: "이 자료 전체를 관통하는 주제는?"처럼 전체를 묻는 질문 [1]
- **약점**: 자원을 많이 먹는 방식임. 공식 문서도 "resource-intensive"라고 적음 [6]

#### (3) DRIFT Search ~ 넓게 시작해 좁혀 들어가기

- **어떻게 찾나**: 먼저 커뮤니티 보고서로 넓은 밑그림(primer)을 잡고, 거기서 후속 질문을 만들어
  Local Search로 파고들며 답을 다듬음. 결과는 질문과 답의 계층 구조로 나옴 [3][6]
- **잘 맞는 질문**: 넓이와 깊이가 모두 필요한 탐색형 질문 [6]
- **약점**: 단계가 많아 비용과 지연이 Local Search보다 큼 [3]
- 2024년 10월 31일 Microsoft Research 블로그로 공개됨 [3]

#### (4) Personalized PageRank 계열 ~ HippoRAG

- **어떻게 찾나**: LLM이 문서를 스키마 없는 지식그래프로 바꿔 두고, 질문에서 핵심 개념을 뽑아
  그 개념을 출발점으로 Personalized PageRank를 돌려 관련 구절을 한 번에 끌어모음 [9]
- **잘 맞는 질문**: 여러 문서에 흩어진 사실을 이어 붙여야 하는 멀티홉 질문 [9]
- **보고된 수치**: 멀티홉 QA에서 기존 최고 방법 대비 최대 20% 향상. 단일 단계 검색이 반복 검색(IRCoT)과
  비슷하거나 더 좋으면서 10 ~ 30배 저렴하고 6 ~ 13배 빠름 [9]
- **약점과 후속**: 그래프를 붙인 RAG는 기본 사실 암기 과제에서 일반 RAG보다 성능이 크게 떨어지는 문제가
  있었고, HippoRAG 2가 이를 고쳐 사실, 의미 파악, 연상 세 과제 모두에서 일반 RAG를 앞섰다고 보고함.
  연상 기억 과제에서 최고 임베딩 모델 대비 7% 향상 [10]

#### (5) 경량화 ~ LightRAG

- **어떻게 찾나**: 그래프 구조와 벡터 표현을 함께 써서, 낮은 수준(개별 개체)과 높은 수준(주제)의
  두 층위로 검색함(dual-level retrieval) [11]
- **잘 맞는 질문**: 자료가 자주 바뀌는 환경. 새 자료만 덧붙이는 증분 갱신 알고리즘을 제공함 [11]
- **약점**: 인덱싱 시간이 짧지 않음. 한 벤치마크에서 약 56,000 토큰짜리 책 한 권을 색인하는 데
  710초 이상이 걸렸다고 보고됨 [13]

#### (6) 지연 처리 ~ LazyGraphRAG

- **어떻게 찾나**: 원본을 미리 요약하지 않음. 가벼운 색인만 만들어 두고 LLM 사용을 질문 시점으로 미룸 [4]
- **보고된 수치** [4]
  - 인덱싱 비용이 벡터 RAG와 같고, 풀 GraphRAG의 **0.1%** 수준임
  - 글로벌 질문에서 GraphRAG Global Search와 비슷한 답 품질을 내면서 질의 비용은 **700배 이상** 낮음
  - GraphRAG Global Search 질의 비용의 **4%**만 써도 비교 대상 전부를 뚜렷이 앞섬
- **약점**: 질문 시점에 계산이 몰리므로, 질의가 많을수록 누적 비용 관리가 필요함
- 2024년 11월 25일 Microsoft Research 블로그로 공개됨 [4]

#### (참고) Basic Search ~ 비교용 벡터 RAG

GraphRAG 공식 문서는 비교 목적의 기본 벡터 RAG 구현도 함께 제공함 [6].

### 2-3. 장단점 비교표

| 방식 | 인덱싱 비용 | 질의 비용 | 강한 질문 | 약한 지점 | 출처 |
|------|------------|-----------|-----------|-----------|------|
| 벡터 RAG | 낮음 | 낮음 | 한두 구절에 답이 있는 사실 조회 | 문서 전체를 묻는 질문 | [1][13] |
| Local Search | 높음(그래프 구축 필요) | 중간 | 특정 개체를 깊게 묻는 질문 | 출발점이 좁음 | [3][6] |
| Global Search | 높음(커뮤니티 요약까지) | 높음 | 자료 전체 주제, 경향 질문 | 자원 소모가 큼 | [1][6] |
| DRIFT Search | 높음 | 중간 ~ 높음 | 넓이와 깊이가 함께 필요한 탐색 | 단계가 많아 지연 증가 | [3][6] |
| HippoRAG 계열 | 중간 | 낮음 | 멀티홉 추론 | 기본 사실 암기 과제에서 약했음(2에서 개선) | [9][10] |
| LightRAG | 중간 ~ 높음 | 낮음 | 자주 바뀌는 자료 | 색인 시간이 길 수 있음 | [11][13] |
| LazyGraphRAG | 매우 낮음(벡터 RAG 수준) | 조절 가능 | 로컬과 글로벌 모두 | 질의 시점 계산 부담 | [4] |

### 2-4. 비용을 숫자로 보기

같은 책 한 권(약 56,000 토큰)을 색인할 때 측정된 값 [13]

| 방법 | 색인 시간 | 토큰 사용량 |
|------|-----------|-------------|
| KGP | 32.01초 | 89,215 토큰(최저) |
| HippoRAG, HippoRAG 2 | 낮은 편 | 낮은 편 |
| LightRAG | 710초 이상 | ~ |
| MS-GraphRAG | ~ | 약 655,000 토큰 |

논문은 "시간이나 예산이 빠듯한 곳에서는 경량 프레임워크가 훨씬 비용 대비 효과가 좋다"고 정리함 [13].

### 2-5. 품질을 숫자로 보기

GraphRAG-Bench(arXiv 2506.05690)가 GPT-4o-mini로 측정한 정확도(ACC) 일부 [13]

| 데이터셋 | 방법 | 사실 조회 | 복합 추론 | 맥락 요약 |
|----------|------|-----------|-----------|-----------|
| 소설 | RAG(리랭킹 적용) | 60.92 | 42.93 | 51.30 |
| 소설 | MS-GraphRAG | 49.29 | 50.93 | 64.40 |
| 소설 | HippoRAG 2 | 60.14 | 53.38 | 64.10 |
| 의료 | RAG(리랭킹 적용) | 64.73 | 58.64 | 65.75 |
| 의료 | MS-GraphRAG | 38.63 | 47.04 | 41.87 |
| 의료 | HippoRAG 2 | 66.28 | 61.98 | 63.08 |

논문이 직접 적은 두 가지 관찰 [13]

- **관찰 1**: 단순 사실 조회에서는 기본 RAG가 GraphRAG와 비슷하거나 더 나음. 쉬운 질문에서는 그래프 처리가
  오히려 불필요하거나 잡음 섞인 정보를 끌어와 답 품질을 떨어뜨릴 수 있음
- **관찰 2**: 복합 추론, 맥락 요약, 창의적 생성에서는 GraphRAG가 뚜렷하게 유리함. 여러 개념 사이의 복잡한
  관계를 이어야 하는 과제이고, 이는 그래프 구조에 자연스럽게 맞기 때문임

표에서 읽히듯 **의료 데이터셋의 MS-GraphRAG는 세 과제 모두에서 기본 RAG보다 낮음**. 그래프를 붙이기만 하면
좋아진다는 생각이 사실과 다르다는 점을 보여 줌 [13].

---

## 3장. 최신 트렌드와 활용 추이 (2024 ~ 2026)

### 3-1. 시작점 ~ 2024년

- 2024년 4월, Microsoft Research가 "From Local to Global" 논문에서 GraphRAG를 제안함. LLM으로 개체
  지식그래프를 만들고 커뮤니티 요약을 미리 생성해 두는 2단계 색인이 핵심임 [1]
- 2024년 7월, GraphRAG가 GitHub에 공개됨 [2]
- 2024년 8월, 첫 종합 서베이가 나와 GraphRAG를 "그래프 기반 색인 → 그래프 유도 검색 → 그래프 강화 생성"의
  세 단계로 정리함 [7]
- 2024년 12월 16일, GraphRAG 1.0이 공개됨. Microsoft는 2024년 7월 사전 공개 이후 GitHub 별 2만 개 이상,
  포크 2천 개 이상을 모았다고 밝힘 [5]

### 3-2. 흐름 1: 비용 줄이기(경량화)

초기 GraphRAG의 가장 큰 벽은 인덱싱 비용이었음. 그래서 "미리 다 요약하지 않는" 방향이 빠르게 등장함.

- LazyGraphRAG: 사전 요약을 생략해 인덱싱 비용을 벡터 RAG 수준으로 낮춤. 풀 GraphRAG의 0.1% [4]
- LightRAG: 그래프와 벡터를 함께 쓰고 증분 갱신을 지원해, 자료가 바뀔 때마다 전체를 다시 만들지 않아도 됨 [11]
- 벤치마크 측정에서도 경량 프레임워크가 시간과 토큰 면에서 유리하다고 확인됨 [13]

### 3-3. 흐름 2: 벡터와 그래프를 섞는 하이브리드

- LightRAG는 그래프 구조와 벡터 표현을 함께 써서 관련 개체와 관계를 효율적으로 찾음 [11]
- AWS의 Bedrock Knowledge Bases GraphRAG는 질문 시점에 **벡터 유사도 검색과 그래프 탐색을 결합**해,
  서로 떨어져 있지만 연결된 자료에서 정확도를 높인다고 설명함 [22]
- HippoRAG 2는 임베딩 기반 검색의 강점과 그래프의 강점을 함께 가져가는 방향을 택함 [10]

### 3-4. 흐름 3: 프레임워크와 데이터베이스 벤더 내장

| 제공처 | 형태 | 출처 |
|--------|------|------|
| Microsoft | GraphRAG 오픈소스 라이브러리와 공식 문서 | [2][5][6] |
| Neo4j | `neo4j-graphrag` 파이썬 패키지와 공식 문서 | [23] |
| LlamaIndex | `PropertyGraphIndex`로 문서에서 속성 그래프를 만들고 질의 | [24] |
| LangChain | `LLMGraphTransformer`로 문서를 그래프 문서로 변환(허용 노드와 관계 제한 가능) | [25] |
| AWS | Bedrock Knowledge Bases GraphRAG. 2024년 12월 4일 미리보기, 2025년 3월 7일 정식 출시. Neptune Analytics 기반 | [22] |

> 직접 만들지 않아도 되는 선택지가 늘었다는 점이 2025 ~ 2026년의 실질적 변화임 [22][23][24][25].

### 3-5. 흐름 4: 에이전트와 결합

- Agentic RAG 서베이는 RAG가 단순 구조에서 모듈형, 그래프 기반을 거쳐 에이전트형으로 옮겨 가는 흐름을
  정리하고, Graph RAG를 "관계와 계층을 활용해 멀티홉 추론을 돕는 확장"으로 설명함 [15]
- 설계 관점에서는 그래프 조회가 "검색 단계"가 아니라 **에이전트가 골라 쓰는 도구 중 하나**로 들어감.
  즉 벡터 검색, 그래프 탐색, SQL 조회를 질문에 따라 나눠 쓰는 구조임 [15]

### 3-6. 흐름 5: 평가 기준이 만들어짐

| 벤치마크 | 내용 | 출처 |
|----------|------|------|
| GraphRAG-Bench (2506.02404) | 대학 수준 문제 1,018개, 20권 교재에서 뽑은 16개 학문 분야 | [12] |
| GraphRAG-Bench (2506.05690) | 난이도별 4단계 과제. "언제 그래프가 실제로 도움이 되는가"를 물음 | [13] |
| RAG vs. GraphRAG (2502.11371) | 평가 규약을 통일해 둘을 공정하게 비교하고 섞는 전략도 탐색 | [14] |

각 벤치마크를 조금 더 풀면 다음과 같음.

- **GraphRAG-Bench (2506.02404)**: 객관식, 복수 선택, 참과 거짓, 빈칸 채우기, 서술형의 5가지 문항 유형을 씀.
  그래프 구축부터 검색, 답 생성까지 전 과정을 평가하고, 최종 정답뿐 아니라 추론 과정의 논리적 일관성까지 봄.
  최신 GraphRAG 방법 9종을 실제로 적용해 비교함 [12]
- **GraphRAG-Bench (2506.05690)**: 사실 조회, 복합 추론, 맥락 요약, 창의적 생성의 네 가지 과제를 난이도
  순으로 배치함. ICLR 2026에 채택됨 [13]
- **RAG vs. GraphRAG (2502.11371)**: 데이터 전처리, 검색 설정, 생성 설정을 똑같이 맞춘 평가 규약을 제시해
  재현 가능한 비교를 가능하게 하고, 두 방식을 고르거나 합치는 전략까지 탐색함 [14]

### 3-7. 한계와 비판

정직하게 적어야 할 부분임.

- **효과가 늘 있지는 않음**: "GraphRAG가 많은 NLP 과제에서 일반 RAG를 못 넘는 경우가 잦다"는 보고가
  연구 동기로 명시됨 [13]. 실제 측정에서도 의료 데이터셋의 MS-GraphRAG는 세 과제 모두 기본 RAG보다 낮았음 [13]
- **단순 질문에는 잡음이 됨**: 쉬운 사실 조회에서 그래프 처리가 불필요하거나 잡음 섞인 정보를 끌어와
  답 품질을 떨어뜨릴 수 있음 [13]
- **그래프는 크기가 아니라 품질**: 관계를 많이 뽑는다고 성능이 좋아지지 않음. 촘촘히 연결된 커뮤니티가
  있어야 멀티홉 지식이 살아남 [13]
- **맥락이 폭발함**: GraphRAG는 개체, 관계, 원문 조각을 함께 끌어오므로 맥락이 갑자기 커지고 추론 비용이
  치솟을 수 있음. 검색 경계를 정해 맥락 증가를 막아야 함 [13]
- **정밀한 검색이 먼저**: 필요한 핵심 사실만 집어 오고 불필요한 내용은 걸러야 함 [13]
- **평가 자체가 어려움**: 기존 QA 데이터셋은 질문 범위와 지표가 좁아 GraphRAG의 추론 향상을 제대로 재지
  못한다는 지적이 벤치마크 논문들의 출발점임 [12][13]

### 3-8. 산업별 활용

1차 출처로 확인한 범위만 적음.

- **의료**: GraphRAG-Bench(2506.05690)의 의료 데이터셋은 NCCN(미국 종합 암 네트워크) 임상 지침을
  재료로 구성됨. 표준 치료 절차, 약물 상호작용 계층, 진단 기준을 담음 [13]
- **긴 서사 문서**: 같은 벤치마크의 소설 데이터셋은 Project Gutenberg의 20세기 이전 소설을 씀.
  비선형적이고 추론이 필요한 실제 문서를 흉내 내기 위함임 [13]
- **산업 사례 일반**: GraphRAG 서베이가 downstream 과제, 응용 분야, 산업 사례를 함께 다룸 [7]

> 개별 기업의 도입 성과 수치(예: "A사 정확도 몇 % 상승")는 1차 출처에서 확인하지 못해 적지 않음.

---

## 4장. 도입 판단 가이드

> **이 장 전체는 「의견」임.** 위 출처들의 사실을 바탕으로 지식니가 정리한 판단 기준이며,
> 특정 논문이 제시한 판정표가 아님.

### 4-1. 질문 유형별 1차 판정표 (의견)

| 질문 유형 | 대표 질문 | 1차 권장 경로 | 근거가 된 사실 |
|-----------|-----------|---------------|----------------|
| 단순 사실 조회 | "휴가 이월 규정은?" | 벡터 RAG | 단순 조회에서 기본 RAG가 GraphRAG와 대등하거나 더 나음 [13] |
| 관계와 경로 탐색 | "이 부품 불량이 영향 준 제품군은?" | GraphRAG(Local 또는 PageRank 계열) | 복합 추론에서 그래프가 뚜렷하게 유리함 [13] |
| 문서 전체 요약 | "이 자료 전체의 핵심 주제는?" | GraphRAG(Global 또는 LazyGraphRAG) | 전체를 묻는 질문은 일반 RAG가 약한 영역임 [1] |
| 넓고 깊은 탐색 | "이 사건의 배경과 주요 인물 관계는?" | DRIFT Search | 넓이와 깊이를 함께 요구하는 질문에 맞음 [6] |
| 정형 집계 | "지난달 부서별 지출 합계" | NL2SQL | 그래프가 아니라 테이블 집계가 정답인 영역임 |

### 4-2. 도입 전 확인할 5가지 (의견)

1. **질문 목록을 먼저 만들었나**: 실제 사용자 질문 30개 이상을 모아 4-1 표로 분류해 봄.
   그래프가 필요한 질문이 20% 미만이면 벡터 RAG로 시작하는 편이 나음
2. **인덱싱 예산을 계산했나**: 56,000 토큰 책 한 권에 MS-GraphRAG가 약 655,000 토큰을 쓴 측정이 있음 [13].
   문서 수를 곱해 보면 금액이 바로 나옴
3. **자료가 얼마나 자주 바뀌나**: 매일 바뀐다면 증분 갱신을 지원하는 쪽(LightRAG)을 먼저 봄 [11]
4. **맥락 상한을 정했나**: 그래프 검색은 맥락이 폭발하기 쉬우므로 검색 경계를 미리 정해 둠 [13]
5. **비교 측정을 준비했나**: 같은 질문 세트로 벡터 RAG와 GraphRAG를 나란히 재지 않으면 효과를 말할 수 없음.
   공정 비교 규약을 제시한 연구가 있으니 참고함 [14]

### 4-3. 단계적 도입 순서 (의견)

1. 벡터 RAG로 기준선을 만들고 질문 세트로 점수를 기록함
2. 그래프가 필요한 질문만 추려 LazyGraphRAG나 LightRAG 같은 경량 방식으로 먼저 붙여 봄 [4][11]
3. 효과가 확인되면 전체 그래프 구축과 커뮤니티 요약으로 확장함 [1]
4. 마지막에 에이전트가 벡터, 그래프, SQL을 골라 쓰도록 도구로 감쌈 [15]

---

## 5장. 참고 출처

1. From Local to Global: A Graph RAG Approach to Query-Focused Summarization, Darren Edge 외 9인
   (Microsoft Research), arXiv:2404.16130, 2024년 4월 24일 제출(2025년 2월 19일 v2),
   https://arxiv.org/abs/2404.16130
2. GraphRAG: New tool for complex data discovery now on GitHub, Microsoft Research Blog, 2024,
   https://www.microsoft.com/en-us/research/blog/graphrag-new-tool-for-complex-data-discovery-now-on-github/
3. Introducing DRIFT Search: Combining global and local search methods to improve quality and efficiency,
   Microsoft Research Blog, 2024년 10월 31일,
   https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/
4. LazyGraphRAG: Setting a new standard for quality and cost, Microsoft Research Blog, 2024년 11월 25일,
   https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/
5. Moving to GraphRAG 1.0 ~ Streamlining ergonomics for developers and users, Microsoft Research Blog,
   2024년 12월 16일,
   https://www.microsoft.com/en-us/research/blog/moving-to-graphrag-1-0-streamlining-ergonomics-for-developers-and-users/
6. GraphRAG 공식 문서 Query Engine(Local, Global, DRIFT, Basic Search), Microsoft, 2024 ~ ,
   https://microsoft.github.io/graphrag/query/overview/ (소스 저장소: https://github.com/microsoft/graphrag )
7. Graph Retrieval-Augmented Generation: A Survey, Boci Peng 외 7인, arXiv:2408.08921,
   2024년 8월 15일 제출(2024년 9월 10일 v2), https://arxiv.org/abs/2408.08921
8. Retrieval-Augmented Generation with Graphs (GraphRAG), Haoyu Han 외 17인, arXiv:2501.00309,
   2024년 12월 31일 제출(2025년 1월 8일 v2), https://arxiv.org/abs/2501.00309
9. HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models,
   Bernal Jiménez Gutiérrez 외 4인, NeurIPS 2024, arXiv:2405.14831, 2024년 5월 23일 제출,
   https://arxiv.org/abs/2405.14831
10. From RAG to Memory: Non-Parametric Continual Learning for Large Language Models (HippoRAG 2),
    Bernal Jiménez Gutiérrez 외 4인, ICML 2025, arXiv:2502.14802, 2025년 2월 20일 제출,
    https://arxiv.org/abs/2502.14802
11. LightRAG: Simple and Fast Retrieval-Augmented Generation, Zirui Guo 외 4인, arXiv:2410.05779,
    2024년 10월 8일 제출(2025년 4월 28일 v3), https://arxiv.org/abs/2410.05779
12. GraphRAG-Bench: Challenging Domain-Specific Reasoning for Evaluating Graph Retrieval-Augmented
    Generation, Yilin Xiao 외 7인, arXiv:2506.02404, 2025년 6월 3일 제출, https://arxiv.org/abs/2506.02404
13. When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation,
    Zhishang Xiang 외 6인, ICLR 2026, arXiv:2506.05690, 2025년 6월 6일 제출(2026년 2월 22일 v3),
    https://arxiv.org/abs/2506.05690
14. RAG vs. GraphRAG: A Systematic Evaluation and Key Insights, Haoyu Han 외 11인, arXiv:2502.11371,
    2025년 2월 17일 제출(2026년 3월 4일 v3), https://arxiv.org/abs/2502.11371
15. Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG, Aditi Singh 외 4인,
    arXiv:2501.09136, 2025년 1월 15일 제출(2026년 4월 1일 v4), https://arxiv.org/abs/2501.09136
16. Machine Knowledge: Creation and Curation of Comprehensive Knowledge Bases, Gerhard Weikum,
    Luna Dong, Simon Razniewski, Fabian Suchanek, arXiv:2009.11564, 2020년 9월 24일 제출(2021년 v2),
    https://arxiv.org/abs/2009.11564
17. Introducing the Knowledge Graph: things, not strings, Amit Singhal, Google, 2012년 5월 16일,
    https://blog.google/products/search/introducing-knowledge-graph-things-not/
18. Semantic Web Featured in Scientific American(Tim Berners-Lee, James Hendler, Ora Lassila의
    "The Semantic Web" 2001년 5월호 표지 기사 안내), W3C, 2001,
    https://www.w3.org/news/2001/semantic-web-featured-in-scientific-american/
19. RDF 1.1 Concepts and Abstract Syntax, W3C Recommendation, 2014년 2월 25일,
    https://www.w3.org/TR/rdf11-concepts/
20. OWL 2 Web Ontology Language Document Overview (Second Edition), W3C Recommendation,
    2012년 12월 11일, https://www.w3.org/TR/owl2-overview/
21. SPARQL 1.1 Overview, W3C Recommendation, 2013년 3월 21일, https://www.w3.org/TR/sparql11-overview/
22. Amazon Bedrock Knowledge Bases supports GraphRAG now generally available, AWS What's New,
    2025년 3월 7일(미리보기 2024년 12월 4일),
    https://aws.amazon.com/about-aws/whats-new/2025/03/amazon-bedrock-knowledge-bases-graphrag-generally-available/
23. GraphRAG for Python (neo4j-graphrag-python documentation), Neo4j, 2024 ~ ,
    https://neo4j.com/docs/neo4j-graphrag-python/current/
24. Using a Property Graph Index, LlamaIndex 공식 문서, 2024 ~ ,
    https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/
25. LLMGraphTransformer (langchain-neo4j) API 레퍼런스, LangChain, 2025 ~ ,
    https://reference.langchain.com/python/langchain-neo4j/graph_transformers/llm/LLMGraphTransformer

---

## Fact와 Opinion 구분 안내

- **Fact**: 문장 끝에 `[번호]`가 붙은 내용임. 위 5장 목록의 1차 출처(논문 원문, 공식 문서, 공식 블로그,
  표준 문서)에서 직접 확인한 사실과 수치만 적음
- **Opinion**: 「의견」이라고 표시한 단락과 4장 전체임. 지식니의 판단이며, 특정 출처가 보증하지 않음
- **적지 않은 것**: 확인하지 못한 URL, 수치, 기업 사례는 넣지 않음. 추정치도 쓰지 않음

### 이 문서에서 Opinion으로 표시한 부분

1. 1장 1-3절 끝 「의견」 단락 ~ RDF 그래프와 속성 그래프 중 무엇으로 시작할지에 대한 판단
2. 3장 3-4절 끝 인용 문단 ~ 벤더 내장이 2025 ~ 2026년의 실질적 변화라는 해석
3. 4장 전체(4-1 판정표, 4-2 확인 5가지, 4-3 단계적 도입 순서)
