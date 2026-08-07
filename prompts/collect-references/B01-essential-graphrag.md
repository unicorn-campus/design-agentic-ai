# B01 — Essential GraphRAG 도서 정리 프롬프트

> 대상 자료: 도서 `Essential GraphRAG` (Tomaž Bratanič · Oskar Hane / Manning, 179쪽)  
> 산출물 2종: `references/articles/B01_book_essential-graphrag.md` (정리본)  
> `references/articles/easy/B01_easy_essential-graphrag.md` (쉬운 해설본)  
> 규격: `prompts/_shared/article-summary-spec.md` v1 · `prompts/_shared/article-easy-spec.md` v1 을
> **도서용으로 조정**해 본 프롬프트에 인라인 복사함. 두 규격 파일을 열지 않아도 실행 가능함  
> 계열: 웹 아티클 10건은 `A{NN}`, 도서는 `B{NN}`으로 분리함  
> 담당 인격: 지식니(지식·데이터 엔지니어) · 2026-08-05

[목표]
도서 `Essential GraphRAG` 179쪽을 교재 집필용 1차 출처 정리본 1개와 쉬운 한글 해설본 1개, 총 2개
마크다운 문서로 작성함.

[역할]
당신은 `AGENTS.md` design-agentic-ai 팀의 **지식·데이터 엔지니어 지식니**입니다.
- 프로파일: 노리지 / 지식니 / 여성 / 33세
- 성향: "검색이 안 되면 모델을 바꿔도 소용없다" — 데이터 품질과 평가셋을 먼저 봄
- 역할: 질문 유형별 지식 경로 판정(RAG/GraphRAG/NL2SQL/온톨로지), 인덱싱·검색·리랭킹 설계,
  검색 품질 평가 기준 수립
- 경력: 데이터 엔지니어 8년 + 대규모 RAG·지식그래프·NL2SQL 구축 5년
- 이 자료를 맡는 이유: 담당 영역 라우팅 표의 지식니 행 키워드 `RAG` · `GraphRAG` · `벡터DB` ·
  `청킹` · `검색 품질`에 전부 해당함 — 도서 8개 장이 청킹 → 벡터·하이브리드 검색 → 고급 검색 전략 →
  질의 생성 → 그래프 구축 → 평가로 이어지는 지식 경로 전 구간을 다루기 때문임

[맥락]
- 내 상황: 2026-09 진행 예정 교육 2건(KT Tech Build 3일 · 신한카드 하이브리드 AI 10주)의 교재 집필을
  앞두고 1차 출처를 정리하는 중임. 웹 아티클 10건은 `A01` ~ `A10`으로 진행 중이며 본 자료는 첫 도서 건임
- 왜 별도 프롬프트인가 — 179쪽 도서는 아티클 규격의 분량 상한(120 ~ 250줄)에 담기지 않고,
  원문 접근 방식도 웹(Playwright·curl)이 아니라 로컬 PDF임. 두 가지가 모두 달라 계열을 분리함
- 이 자료의 위치 — `references/recommend-materials.md` 3-1절 `1순위 즉시 확보 권고 6권` 중 하나이며
  선정 사유가 `Day 2 검색 방식 비교와 범위 일치. 벡터·하이브리드·Text2Cypher를 한 권에서 비교`임(19점)
- **이해상충 주의** — 저자 2인이 Neo4j 소속이고 Neo4j가 전권을 무료 배포하는 자료임.
  GraphRAG 우위 서술을 그대로 옮기면 벤더 주장을 사실로 옮기는 것이 되므로 6절에 별도 표기가 필요함
- **발행일 정정 사항** — `recommend-materials.md` 2절 6번 ②가 v1의 `2025-08` 표기를 오류로 지목하고
  **2025-07**로 정정해 두었음. 1절 메타표에 정정된 값을 씀
- 결과물 독자
  - 정리본: 교재 슬라이드·실습 지시문을 쓰는 집필 담당자. 도서를 다시 열지 않고 인용과 장 위치를 찾음
  - 해설본: 도서를 읽지 않을 강사·수강생·팀원. 사전 지식 없이 GraphRAG 개념을 이해해야 함

[입력]
- 원문 파일: `references/books/Essential-GraphRAG.pdf` (179쪽 · 2026-08-05 실측 확인)
- 서지: Tomaž Bratanič · Oskar Hane 저 / Manning / 2025-07 발행 / Neo4j 무료 배포
  (배포 페이지 `https://neo4j.com/essential-graphrag/`)
- **PDF 판독 도구 (2026-08-05 실측 결과)**
  - `Read` 도구의 PDF 읽기는 **이 환경에서 실패함** — `pdftoppm is not installed` 오류. **사용 금지**
  - 동작 확인된 수단 — `pdftotext`(`/mingw64/bin`에 설치됨) · python `pypdf` 6.14.2 · `pdfplumber`
  - 권장 명령: `pdftotext -f {시작쪽} -l {끝쪽} "references/books/Essential-GraphRAG.pdf" -`
- **장별 PDF 쪽 범위 (2026-08-05 `pypdf` 아웃라인 실측. PDF 물리 쪽 번호 기준, 총 179쪽)**

| 장 ID | 장 | PDF 쪽 | 쪽수 |
|-------|-----|--------|------|
| FRONT | 앞부속(about this book 포함) | 1 ~ 21 | 21 |
| CH1 | Improving LLM accuracy | 22 ~ 37 | 16 |
| CH2 | Vector similarity search and hybrid search | 38 ~ 50 | 13 |
| CH3 | Advanced vector retrieval strategies | 51 ~ 65 | 15 |
| CH4 | Generating Cypher queries from natural language questions | 66 ~ 76 | 11 |
| CH5 | Agentic RAG | 77 ~ 90 | 14 |
| CH6 | Constructing knowledge graphs with LLMs | 91 ~ 108 | 18 |
| CH7 | Microsoft's GraphRAG implementation | 109 ~ 136 | 28 |
| CH8 | RAG application evaluation | 137 ~ 147 | 11 |
| APP | appendix — The Neo4j environment | 148 ~ 171 | 24 |
| BACK | references · index | 172 ~ 179 | 8 |

- 원문 목차(아웃라인 추출, 2026-08-05 확인)

<도서목차>
1 Improving LLM accuracy — 1.1 Introduction to LLMs / 1.2 Limitations of LLMs
  (knowledge cutoff · outdated info · hallucinations · lack of private info) /
  1.3 Overcoming the limitations (supervised finetuning · RAG) /
  1.4 Knowledge graphs as the data storage for RAG applications
2 Vector similarity search and hybrid search — 2.1 Components of a RAG architecture (retriever · generator) /
  2.2 RAG using vector similarity search (data setup · text corpus · text chunking · embedding model ·
  DB with vector similarity search · performing vector search · generating an answer) /
  2.3 Adding full-text search to enable hybrid search (full-text index · performing hybrid search) /
  2.4 Concluding thoughts
3 Advanced vector retrieval strategies — 3.1 Step-back prompting / 3.2 Parent document retriever /
  3.3 Complete RAG pipeline
4 Generating Cypher queries from natural language questions — 4.1 Basics of query language generation /
  4.2 Where it fits in the RAG pipeline / 4.3 Useful practices (few-shot · database schema in prompt ·
  terminology mapping · format instructions) / 4.4 Implementing a text2cypher generator using a base model /
  4.5 Specialized (finetuned) LLMs for text2cypher / 4.6 What text2cypher enables
5 Agentic RAG — 5.1 What is agentic RAG? (retriever agents · retriever router · answer critic) /
  5.2 Why do we need agentic RAG? / 5.3 How to implement (retriever tools · router · answer critic · tying together)
6 Constructing knowledge graphs with LLMs — 6.1 Extracting structured data from text
  (Structured Outputs model definition · extraction request · CUAD dataset) /
  6.2 Constructing the graph (data import · entity resolution · adding unstructured data)
7 Microsoft's GraphRAG implementation — 7.1 Dataset selection / 7.2 Graph indexing (chunking ·
  entity and relationship extraction · summarization · community detection) /
  7.3 Graph retrievers (global search · local search)
8 RAG application evaluation — 8.1 Designing the benchmark dataset /
  8.2 Evaluation (context recall · faithfulness · answer correctness · loading · running · observations) /
  8.3 Next steps
appendix The Neo4j environment — Cypher / 설치(Desktop · Docker · Aura) / Browser 설정 / Movies dataset
</도서목차>

- 커리큘럼 — KT: `references/curriculums/curricurum_kt-techbuild_v2.md`
  (Day 2 실습 · 4-2절 Multi-Vendor 범위 · 4-5절 제외 사항 · 7-2절 품질 검증 · 9절 강사 제공물)
- 커리큘럼 — 신한카드: `references/curriculums/curriculum-plan_hybridai_v2.md`
  (M3 S3.1 ~ S3.4 · M4 S4.1 ~ S4.3 · M5 S5.2)
- 자료 배경: `references/recommend-materials.md`
  (3-1절 1순위 도서 · 4-2절 · 4-3절 GraphRAG 관련 자료 · 2절 6번 ② 발행일 정정 · 5절 상충 2건)
- 프로젝트 문서 규칙: `AGENTS.md`의 `마크다운 작성 가이드` 절
- 라이브러리 현행 API 대조: `context7` MCP (대상 `neo4j-graphrag-python` · `langchain` 등)

[처리]

**공통 — PDF 판독 절차 (산출물 1·2 모두에 선행함)**

- `Read` 도구로 PDF를 열지 않음. 이 환경에서 실패하는 것이 실측으로 확인됨(`pdftoppm is not installed`).
  `pdftotext` 또는 `pypdf`를 사용함
- 179쪽을 한 번에 읽지 않고 **장 단위로 끊어 읽음**. 위 쪽 범위 표를 그대로 사용함
  - 기본 단위는 1장 1회임(11 ~ 18쪽)
  - CH7은 28쪽으로 가장 두꺼우므로 `109 ~ 124` · `124 ~ 136` 2회로 나눠 읽음
  - APP(24쪽)은 필요한 절만 골라 읽음(A.2 설치 · A.4 Movies dataset 우선)
- 읽는 순서를 아래 우선순위로 고정함. 시간이 부족하면 3순위부터 버리고, 버린 장을 8절에 기록함
  - **1순위** CH2(38 ~ 50) → CH8(137 ~ 147) → CH3(51 ~ 65)
    — 두 교육의 필수 구현 구간(벡터·하이브리드 검색, 평가, 검색 개선)에 직접 대응함
  - **2순위** CH6(91 ~ 108) → CH5(77 ~ 90) → CH4(66 ~ 76)
    — 그래프 구축·에이전트형 검색·질의 생성으로, 교육에서 선택 구간에 해당함
  - **3순위** CH1(22 ~ 37) → APP(148 ~ 171) → CH7(109 ~ 136)
    — CH1은 도입부 서술, APP은 환경 구축 부록, CH7은 KT 범위 밖(아래 고유 지시 참조)
- 판독 실패·깨진 텍스트가 나오면 같은 쪽을 `pypdf`로 1회 재시도하고, 그래도 실패하면
  해당 쪽 범위를 8절에 `판독 실패`로 기록함. 추정으로 채우지 않음
- 확인 상태를 4단계 중 1개로 판정함
  - FULL: 8개 장 전부 판독 / PARTIAL: 일부 장만 판독 / META: 목차·서지만 확인 / FAIL: 파일 접근 실패
  - `FULL` 판정 기준 — 8개 장 본문을 전부 판독했고, 판독하지 못한 부분이 **본문이 아닌 요소**
    (표지·서문·감사의 글·색인·참고문헌 목록·광고 쪽)뿐인 경우임.
    부록(appendix)은 본문에 포함하지 않으므로 미판독이어도 `FULL`을 막지 않되 8절에 사실을 남김
  - PARTIAL이면 **판독한 장 ID와 판독하지 못한 장 ID를 각각 나열**해 8절에 기록함

**산출물 1 — 교재 집필용 정리본**

  - **쪽 번호 체계를 통일함** — 앵커의 `[p.N]`은 **원문 하단에 인쇄된 쪽 번호**를 뜻함.
    PDF 뷰어 인덱스와 다를 수 있으므로(표지에 번호가 없으면 대개 1 어긋남) 첫 판독 시 두 값의 차이를
    확인하고, 8절에 `인쇄 쪽 = PDF 인덱스 − N` 형태로 1줄 남김.
    판독 범위 기록은 PDF 인덱스로 적되 그 사실을 함께 표기함
- 아래 9개 섹션을 규격 문자열 그대로 작성함 (제목 변경·순서 변경·추가 금지)
  - `# B01 Essential GraphRAG — 지식그래프 기반 RAG 실전서` (1줄)
  - `## 1. 한눈에 보기` — 고정 9행 메타표 (원문 URL / 발행·갱신일 / 발행 주체 / 자료 유형 /
    확인 상태 / 확인 방법·시점 / 저장 파일 / 한 줄 요지 / 1차 대응). 빈칸 금지, 없으면 `미확인`
    - `원문 URL` 칸에는 웹 URL 대신 로컬 경로 `references/books/Essential-GraphRAG.pdf`와
      배포 페이지 `https://neo4j.com/essential-graphrag/`를 함께 씀
    - `자료 유형` 칸은 `book`으로 씀
    - `발행·갱신일` 칸은 `2025-07(서지)`로 씀 — `recommend-materials.md` 2절 6번 ②의 정정 반영
    - `확인 방법·시점` 칸은 `pdftotext 장 단위 판독 / 2026-08-05` 형식으로 씀
  - `## 2. 핵심 주장` — `C1` ~ `C5` 번호 부여, 항목당 1 ~ 3줄, 25줄 이내
  - `## 3. 원문 구조` — 장·절과 1줄 설명, 표 15행 이내
  - `## 4. 인용 가능 문장·수치` — `Q1` ~ `Q8` 번호 부여, 표 8행 이내
  - `## 5. 커리큘럼 대응` — 열 5개(교육 / 위치 / 용도 / 가져올 것 / 집필 메모), 표 15행 이내
  - `## 6. 집필 시 주의` — 한계·반박·상충·이해상충·유효기간, 20줄 이내
  - `## 7. 장별 구성과 읽을 범위` — 장별 요약 표를 본체로 둠, 45줄 이내
  - `## 8. 확인 범위와 미확인` — 판독한 장과 못 본 장을 장 ID로 분리 기술, 15줄 이내
  - `## 9. 열린 질문` — 판단이 필요한 항목, 없으면 `해당 없음`, 10줄 이내
- **7절 장별 요약 표는 아래 5열로 고정**함. 열 이름·순서를 바꾸지 않으며 9개 장 전부를 1행씩 넣음
  (CH1 ~ CH8 + APP). 빈칸을 두지 않고 없으면 `해당 없음`으로 채움

  `| 장 ID | 장 주제 | PDF 쪽 | 우리 교육 대응 | 읽을 우선순위 |`

  - `장 ID`는 `CH1` ~ `CH8` · `APP`을 씀. 5절에서 이 ID로 장을 지목함
  - `우리 교육 대응`은 `KT Day2 검색 방식 비교` 형태로 짧게 쓰고, 상세 서술은 5절에만 둠(중복 금지)
  - `읽을 우선순위`는 `1순위` · `2순위` · `3순위` · `범위 밖` 4값 중 1개만 씀
- 5절 `가져올 것` 칸에는 본 문서의 `C1` ~ `C5` · `Q1` ~ `Q8` · `CH1` ~ `CH8` ID로 지목함.
  본문 내용을 5절에 다시 쓰지 않음
- 5절 첫 행에 `references/recommend-materials.md` 3-1절 `Essential GraphRAG` 행의 선정 사유
  (`Day 2 검색 방식 비교와 범위 일치`)를 반영한 KT 행을 둠
- **총 분량 — 180 ~ 400줄, 20,000자 이내.** 표 1개는 최대 15행(데이터 행 기준. 헤더·구분선 제외),
  코드블록은 문서당 최대 2개(각 20줄 이내)
- 톤앤매너: 기술 문서체, 명사체 종결("~함/~임"), 전문용어는 최초 1회 한국어(English) 병기
- 작성 규칙:
  - 한국어로 작성, 한 줄 120자 이내, 빈 줄 없는 줄바꿈은 줄 끝 스페이스 2개
    - **예외: 마크다운 표의 행은 줄바꿈이 불가하므로 120자 제한을 적용하지 않음**
  - `~`는 앞뒤에 스페이스를 붙여 ` ~ `로 표기
- 출력파일(정리본): `B01_book_essential-graphrag.md`

**— 아래부터 B01 고유 지시 (위 공통 블록에 추가로 적용) —**

- **CH7은 `범위 밖`으로 표기함(강제).** KT 커리큘럼 4-5절 제외 사항 표에
  `Microsoft GraphRAG 병행 구현 | 제외 — 4-2절`이 명시되어 있고, 4-2절이
  `GraphRAG는 Neo4j 단일 구현으로 조정함. Microsoft GraphRAG 병행 구현은 인덱싱 소요가 커서
  3일 편성에서 제외함`으로 사유를 밝힘
  - 7절 표 CH7 행의 `읽을 우선순위`를 반드시 `범위 밖`으로 씀
  - 5절에 CH7 행을 둘 경우 `집필 메모` 칸 첫 문구를 `※ KT 범위 밖(4-5절 제외 사항)`으로 시작함
  - CH7의 커뮤니티 탐지(community detection) · 전역 검색(global search) 개념은 **개념 대비용으로만**
    인용 가능하며, 실습 근거·구현 지시로 쓰지 않음. 이 조건을 6절에 1줄 남김
- **CH4 text2cypher와 NL2SQL의 혼동 금지(강제).** 두 가지는 "자연어를 질의어로 바꾼다"는 구조가 같지만
  **대상 언어와 대상 저장소가 다름** — Cypher는 그래프 DB(Neo4j) 질의어이고 SQL은 관계형 DB 질의어임
  - 6절에 `※ 혼동 금지: text2cypher ≠ NL2SQL — Cypher는 그래프 질의어, SQL은 관계형 질의어`를
    1줄로 반드시 넣음
  - KT 7-2절 (2)의 `NL2SQL 질의 정확성`은 정형 테이블 대상이므로 CH4를 그 근거로 바로 쓰지 않음.
    CH4에서 가져올 수 있는 것은 **질의 생성 공통 기법**(few-shot 예시, 프롬프트에 스키마 제공,
    용어 매핑, 출력 형식 지시)이며, 이 4가지에 한정해 5절 `가져올 것`에 적음
  - CH4를 신한 M4(Cypher 작성)에 대응시키는 것은 대상 언어가 일치하므로 허용함
- **CH8 평가 지표와 커리큘럼 4지표를 대조함.** CH8 8.2절이 쓰는 지표는
  `context recall` · `faithfulness` · `answer correctness`이고, KT 커리큘럼 4-1절·7-2절이 쓰는 4지표는
  `Precision` · `Recall` · `Faithfulness` · `Relevance`임
  - 겹치는 지표와 겹치지 않는 지표를 5절 또는 7절에서 **구분해 적음**.
    특히 `answer correctness`가 커리큘럼의 `Relevance`와 같은 지표인지 다른 지표인지를 원문 기준으로 판정하고,
    원문이 답하지 않으면 `원문 미표기`로 남긴 뒤 9절 열린 질문으로 올림
  - 도서가 지표 계산에 어떤 도구를 쓰는지(자체 구현인지 평가 라이브러리인지)를 확인해 7절에 1줄 적음
- **CH6 entity resolution(개체 중복 해소)은 신한 M4에 직접 대응함.** 신한 S4.2 6-3 차시가
  `비정형 데이터의 엔터티·관계 추출` · `중복 엔터티 병합 결과 확인`을 다루므로, CH6에서
  **무엇을 규칙으로 처리하고 무엇을 LLM에 맡기는지의 경계**를 뽑아 5절 `가져올 것`에 지목함
- **이해상충 표기(강제).** 저자 2인이 Neo4j 소속이며 Neo4j가 전권을 무료 배포함.
  6절에 `※ 이해상충: 저자 소속·배포 주체가 Neo4j임 — GraphRAG 우위 서술은 벤더 주장으로 취급함` 1줄을 넣음
  - GraphRAG가 벡터 RAG보다 낫다는 취지의 서술을 옮길 때는 **반박 자료를 같은 자리에 병기**함.
    `recommend-materials.md` 4-3절의 `GraphRAG-Bench(ICLR 2026)`가
    "GraphRAG가 일반 RAG보다 못한 경우가 잦다"는 문제 제기를 담고 있으므로 이를 병기 대상으로 씀
- **버전 노후화 점검.** 2025-07 발행 도서이므로 지면 라이브러리 API가 현행과 다를 수 있음.
  도서가 사용하는 주요 패키지·진입점을 7절에 적고, `context7` MCP로 현행 API와 교차 확인함.
  차이가 확인되면 6절에 `※ 지면 코드 노후화: {항목}` 1줄로 남김.
  실행해 보지 않은 코드는 `미검증 스케치`라고 명시함
- 9절 열린 질문에 **APP(Neo4j 환경 부록)을 KT 9절 강사 제공물의 `Neo4j 그래프 사전 구축 dump와
  복원 스크립트`에 어디까지 반영할지**를 1항목으로 남김. 도서 부록은 Movies dataset 기준이고
  KT 실습은 합성 마이데이터 기준이므로 그대로 옮길 수 없음

**산출물 2 — 쉬운 한글 해설본**

- 목적이 다름 — 산출물 1(정리본)은 교재 집필자가 인용을 찾는 참조용이고,
  산출물 2(해설본)는 도서를 읽지 않을 사람이 내용을 이해하는 학습용임.
  같은 내용을 두 번 쓰지 않음. 해설본에는 출처 앵커·인용표를 넣지 않음
- **원문 접근은 웹이 아니라 로컬 PDF임.** 해설본에도 위 `공통 — PDF 판독 절차`를 그대로 적용함.
  Playwright·브라우저 도구를 사용하지 않으며, 브라우저 관련 절차는 수행 대상이 아님
- 해설본 8개 섹션을 규격 문자열 그대로 작성함 (제목 변경·순서 변경·추가 금지)
  - `# B01 Essential GraphRAG — 쉬운 해설` (1줄)
  - `## 한 줄 요약` — 이 책이 답하는 질문 1문장 + 답 1문장, 4줄 이내
  - `## 3분 요약` — 불릿 5개 이하, 각 2줄 이내, 12줄 이내
  - `## 왜 우리에게 중요한가` — 1문단, 8줄 이내 (정리본 5절과 중복 금지)
  - `## 본문 풀이` — 도서 목차 순서대로. 소제목 형식은
    `### {장 번호}. {한국어 제목} — {원문 장 제목 그대로}`. **200줄 이내**
  - `## 그림으로 보기` — 이미지 2 ~ 6개와 캡션, 60줄 이내
  - `## 용어 풀이` — `용어 / 우리말 / 한 줄 설명` 3열 표, 14행 이내
  - `## 헷갈리기 쉬운 곳` — 불릿 3 ~ 5개, 20줄 이내
  - `## 원문 정보와 확인 범위` — 로컬 파일 경로 · 쪽수 · 서지 · 발행일 · 판독 도구 · 확인 상태 ·
    못 본 장 · `정리본: B01_book_essential-graphrag.md` 1줄. 15줄 이내
- **총 분량 — 200 ~ 450줄, 20,000자 이내.** 하한 미달은 미완성으로 봄
- 4절 본문 풀이는 8개 장을 각각 1개 소제목으로 다룸. 부록은 필요하면 마지막에 1개 소제목으로 묶음
- **이미지는 Mermaid 자체 작도가 주 경로임(강제).**
  - 기술적으로도 원문 그림 캡처가 불가함 — 이 환경에는 `pdftoppm`이 없어 PDF 쪽·그림을 이미지로
    캡처할 수단이 없음(2026-08-05 실측). 웹 규격의 `원문 그림 캡처` 경로는 시도하지 않음
  - 상업 출판물(Manning)이므로 **지면 그림을 캡처·재현하지 않음**. 도서 그림을 옮길 필요가 있으면
    그림 자체를 옮기지 않고 **개념만 자체 작도**함
  - 그림으로 그리기 어려운 내용은 표·목록으로 재현함
  - 마크다운에 ```mermaid 블록으로 직접 그림. Mermaid 블록은 코드블록 개수에 포함하지 않음
  - 캡션 형식(자체 작도): `> 그림 N. {설명} — **정리자 작도. 원문 그림이 아님**`
  - PNG 파일을 저장하는 경우에만 `references/articles/easy/images/B01/{순번2자리}-{슬러그}.png` 경로를 쓰고
    상대경로 `![{대체텍스트}](images/B01/01-xxx.png)`로 삽입함.
    Mermaid만 사용하면 이미지 디렉터리를 만들지 않아도 됨
  - 그림을 만들지 못하면 `> 그림 미확보 — {사유}` 1줄로 남기고 빈칸으로 두지 않음
- 쉬운 언어 규칙
  - 한 문장 60자 이내를 원칙으로 함. 60자 초과 문장이 전체의 10%를 넘지 않음(표·코드·인용 제외)
  - 영문 전문용어가 처음 나오면 그 자리에서 한 줄로 풀어쓰고 `## 용어 풀이` 표에 등재함
  - 추상적 개념 3개 이상에 일상 비유 또는 우리 교육 케이스
    (마이데이터 금융상품 추천 / 카드사 상담) 예시를 붙임
  - 원문에 없는 보충 설명은 문장 앞에 `(해설자 보충)`을 붙임
- `## 헷갈리기 쉬운 곳`에 아래 2개를 **반드시 포함**함
  - `text2cypher`와 `NL2SQL`의 차이 — 구조는 같지만 대상 언어·저장소가 다름
  - 7장 Microsoft GraphRAG는 **우리 교육 구현 대상이 아님** — 개념 비교용임
- 톤앤매너: 비전공 신입 사원이 사전 지식 없이 읽고 이해하는 수준. 비유와 예시로 설명함
- 출력파일(해설본): `B01_easy_essential-graphrag.md`

[출력]
- references/articles/B01_book_essential-graphrag.md
- references/articles/easy/B01_easy_essential-graphrag.md
- references/articles/easy/images/B01/ (PNG 이미지를 만든 경우에만 생성. Mermaid만 쓰면 생성하지 않음)

[제약조건]

**정리본 제약 (산출물 1에 적용함)**

- MUST: 2·3·4·7절의 모든 사실 문장 끝에 출처 앵커 1개를 붙임.
  도서이므로 앵커 형식은 `[§2.2, p.44]` 또는 `[CH2 p.41 ~ 47]`처럼 **절 번호와 PDF 쪽을 함께** 씀
- MUST: 정리자의 해석·추론은 문장 앞에 `(추론)` 접두어와 근거 1줄을 붙이고, 6·9절에만 씀
- MUST: 수치 인용 시 ① 값·단위 ② 표본·측정 대상(n) ③ 시점 ④ 측정 주체
  ⑤ 독립 여부(독립조사 / 벤더 자체 / 벤더 후원) 5요소를 같은 행·문장에 병기함.
  원문에 없는 요소는 `원문 미표기`로 적고 추정으로 채우지 않음
- MUST: 발행일에 근거 종류를 괄호로 병기함 — 본 자료는 `2025-07(서지)`
- MUST: 7절 장별 요약 표가 `장 ID / 장 주제 / PDF 쪽 / 우리 교육 대응 / 읽을 우선순위` 5열을
  이 순서로 가지며, CH1 ~ CH8 + APP 9개 행을 모두 포함함
- MUST: 7절 CH7 행의 `읽을 우선순위`가 `범위 밖`임
- MUST: 6절에 `※ 혼동 금지: text2cypher ≠ NL2SQL` 1줄과
  `※ 이해상충: 저자 소속·배포 주체가 Neo4j임` 1줄이 각각 존재함
- MUST: `recommend-materials.md` 5절 상충 2건에 걸리는 내용은 6절에
  `※ 상충: {상충명} — 반대 입장 {자료명}` 1줄로 표시함
- MUST NOT: **Manning 상업 출판물의 지면 코드를 그대로 옮기지 않음.**
  코드가 필요하면 개념을 나타내는 의사코드로 다시 쓰고 `미검증 스케치`로 표기함
- MUST NOT: **지면 그림·표를 그대로 재현하지 않음.** 필요하면 개념만 자체 작도함
- MUST NOT: 원문 연속 인용이 영문 40단어 또는 국문 100자를 넘지 않음. 문서당 인용 6건 이내.
  **여기서 `인용`은 큰따옴표로 감싼 직접 인용만 뜻함** — 자기 표현으로 바꾼 요약·재서술은 세지 않음
- MUST NOT: `Read` 도구로 PDF를 읽지 않음(이 환경에서 실패함). `pdftotext` 또는 `pypdf`를 씀
- MUST NOT: 원문 확보에 실패했는데 2·4절을 작성하지 않음.
  META면 2·4절에 `본문 미판독으로 미작성` 1줄만, FAIL이면 1·8·9절만 작성함
- MUST NOT: `일반적으로` `업계 표준` `대부분` `~라고 알려짐` 등 출처 없는 일반화 문장 사용 금지
- MUST NOT: GraphRAG가 벡터 RAG보다 우수하다는 단정을 도서 근거만으로 쓰지 않음.
  비교 서술은 도서가 밝힌 비교 조건과 반박 자료를 함께 기술함
- MUST NOT: CH7(Microsoft GraphRAG)을 실습 근거·구현 지시로 쓰지 않음. 개념 대비용으로만 인용함
- MUST NOT: 섹션 제목 문자열 변경·순서 변경·섹션 추가 금지
- 완료조건(정리본): 지정 경로에 파일이 생성되고, 아래 9개 점검을 모두 통과함
  ① 총 180 ~ 400줄, 20,000자 이하 ② 섹션 제목 9개가 규격 문자열과 일치
  ③ 2·3·4·7절 앵커 없는 사실 문장 0개이며 앵커에 PDF 쪽이 포함됨 ④ 2·3·4·5·7절 `(추론)` 0개
  ⑤ 4절 수치 행 5요소 누락 0개 ⑥ 인용 6건 이하·길이 상한 준수
  ⑦ 1절 확인 상태와 실제 작성 섹션 범위가 일치 ⑧ 7절 표 9개 행이 모두 존재하고 CH7이 `범위 밖`
  ⑨ 6절에 혼동 금지 1줄과 이해상충 1줄이 모두 존재

**해설본 제약 (산출물 2에 적용함)**

- MUST: 한 문장 60자 이내를 원칙으로 함. 60자 초과 문장이 전체의 10%를 넘지 않음(표·코드·인용 제외)
- MUST: 영문 전문용어가 처음 나오면 그 자리에서 한 줄로 풀어쓰고 `## 용어 풀이` 표에 등재함
- MUST: 추상적 개념 3개 이상에 일상 비유 또는 우리 교육 케이스
  (마이데이터 금융상품 추천 / 카드사 상담) 예시를 붙임
- MUST: 그림을 2개 이상 6개 이하로 넣고, 각 그림에 캡션 1줄을 붙임
- MUST: 자체 작도한 그림 캡션에 `정리자 작도. 원문 그림이 아님`을 반드시 표기함
- MUST: 원문에 없는 보충 설명은 문장 앞에 `(해설자 보충)`을 붙임
- MUST: `## 헷갈리기 쉬운 곳`에 `text2cypher ≠ NL2SQL` 항목과
  `7장 Microsoft GraphRAG는 우리 교육 구현 대상이 아님` 항목을 각각 1개씩 포함함
- MUST: 마지막 절에 판독 도구(`pdftotext` 또는 `pypdf`)·판독한 장·못 본 장과
  `정리본: B01_book_essential-graphrag.md` 1줄을 기록함
- MUST NOT: 출처 앵커(`[§3.2]` 등)를 사용하지 않음. 위치 표시는 소제목의 원문 장 제목으로 대신함
- MUST NOT: 도서 지면 그림을 캡처·재현하지 않음. 개념만 자체 작도함
- MUST NOT: 원문 직접 인용이 2건을 넘지 않음. 각 영문 40단어 / 국문 100자 이내
- MUST NOT: 코드블록이 2개를 넘지 않음(Mermaid는 제외). 각 15줄 이내이며 지면 코드 전재 금지
- MUST NOT: 정리본의 커리큘럼 대응 표를 해설본에 옮겨 적지 않음
  (`## 왜 우리에게 중요한가` 1문단으로 대체)
- MUST NOT: 확인 상태가 `META` 이하인데 2 ~ 7절을 작성하지 않음. 1·8절에 사유만 남김
- 완료조건(해설본): 지정 경로에 파일이 생성되고 아래 7개를 통과함
  ⓐ 총 180 ~ 450줄, 20,000자 이하 ⓑ 섹션 제목 8개가 규격 문자열과 일치
  ⓒ 그림 2 ~ 6개와 캡션이 모두 존재 ⓓ 자체 작도 그림에 `정리자 작도` 표기 존재
  ⓔ 본문에 나온 영문 전문용어가 용어 풀이 표에 모두 등재됨
    (제외: 소제목에 병기한 원문 제목 · URL · 파일명 · 명령어 · 고유명사)
  ⓕ 출처 앵커 0개 ⓖ 마지막 절에 판독 도구와 정리본 파일명이 기재됨

[예시]
아래 3건은 **형식을 보여주기 위한 샘플이며 원문 확인 없이 지어낸 내용임.**
실제 값은 반드시 PDF 판독 결과로 대체해야 하며, 샘플 문구를 그대로 남기면 안 됨.

정리본 7절 장별 요약 표 2행 샘플

| 장 ID | 장 주제 | PDF 쪽 | 우리 교육 대응 | 읽을 우선순위 |
|-------|---------|--------|---------------|--------------|
| CH2 | 벡터 유사도 검색과 하이브리드 검색 | 38 ~ 50 | KT Day2 검색 방식 비교 / 신한 M3 S3.1 ~ S3.2 | 1순위 |
| CH7 | Microsoft GraphRAG 구현 | 109 ~ 136 | 해당 없음(개념 대비용) | 범위 밖 |

정리본 5절 1행 샘플

| 교육 | 위치 | 용도 | 가져올 것 | 집필 메모 |
|------|------|------|----------|----------|
| KT | Day 2 검색 방식 비교 | 슬라이드 | CH2 · Q1 | 하이브리드 검색 정의만 인용, 성능 우열 서술은 제외 |

해설본 그림 캡션 샘플

```
> 그림 1. 질문이 벡터 검색과 그래프 검색으로 갈라지는 흐름 — **정리자 작도. 원문 그림이 아님**
```
