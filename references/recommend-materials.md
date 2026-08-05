# 에이전틱 AI 설계 학습자료 추천 (2025년 이후 발행분 한정)

작성: 2026-08-05 · 용도: KT Tech Build 교재·설계 템플릿·스타터 리포지토리 제작 근거  
대상 커리큘럼: `output/kt-techbuild/curricurum_kt-techbuild_v2.md`(3일 구성)  
대체 문서: `output/kt-techbuild/참고자료_v1.md` — v1의 오래된 자료·오류를 본 문서가 정정함

> 취급: KT·패스트캠퍼스 자료 기반 문서임. 대외 공개·외부 전송 금지.

**작성 원칙**
- **2025-01-01 이후 발행 또는 최종 갱신된 자료만 추천함.** 그 이전 발행분은 부록 B에 인용 출처로만 남김
- 수록 자료는 팀원 5명이 `curl` 저장 후 본문 판독 또는 출판사 공식 목차로 **내용을 확인한 것만** 올림.
  검색 결과 요약만으로 판단한 자료는 수록하지 않음
- 접근이 막힌 자료는 확인 완료로 보고하지 않고 6절에 분리함
- 점수는 `최신성 / 발행주체 신뢰도 / 커리큘럼 적합도 / 교육 활용도` 각 5점, 합계 20점 만점임
- 상세 근거는 팀원별 원본 보고서에 있음(7절 분담표)

---

## 1. 최우선 10건 — 전부 무료

교재 집필 착수 전 이 10건을 읽으면 커리큘럼 전 구간의 1차 출처가 확보됨.

| # | 자료 | 발행 | 커리큘럼 대응 | 점수 |
|---|------|------|--------------|------|
| 1 | [Anthropic — Building multi-agent systems: When and how to use them](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them) | 2026-01 | 4-4절 9단계 ③ 단일·멀티 판정, 산출물 ③④ | 20 |
| 2 | [LangChain Docs — Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent) | 2025-12 | Day 1 이론 `MAS 패턴`, 산출물 ④ 선택 근거표 | 20 |
| 3 | [LangChain Docs — Context engineering in agents](https://docs.langchain.com/oss/python/langchain/context-engineering) | 2026-07 | Day 1 이론 `컨텍스트 엔지니어링`, Day 2 멀티 LLM | 20 |
| 4 | [MCP 명세 2026-07-28 변경 요약](https://modelcontextprotocol.io/specification/2026-07-28/changelog) | 2026-07 | Day 2 멀티 MCP, 산출물 ⑤ 커넥터 규격 | 19 |
| 5 | [AgentArcEval (CSIRO Data61 · Kazman 공저)](https://arxiv.org/html/2510.21031v1) | 2025-10 | 산출물 ① 목표·품질속성 카드 양식 | 19 |
| 6 | [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | 2025-12 | 산출물 ⑥ 가드레일 항목 도출표 | 20 |
| 7 | [OpenTelemetry GenAI 시맨틱 컨벤션 (전용 저장소)](https://github.com/open-telemetry/semantic-conventions-genai) | 2026-08 | 산출물 ⑥ 기록 지점 표준 이름 | 19 |
| 8 | [Ragas — 에이전트·도구 사용 지표](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/) | 2025-12 | **7-2절 (2) MAS 흐름 정확성 정량화** | 20 |
| 9 | [Ragas — Text-to-SQL 에이전트 평가](https://docs.ragas.io/en/stable/howtos/applications/text2sql/) | 2025-12 | 7-2절 (2) NL2SQL 정확성, 품질 측정 러너 | 20 |
| 10 | [금융위 — 금융분야 인공지능 가이드라인 개정안](https://www.fsc.go.kr/no010101/87142) | 2026-06 | **7-3절 전체**, 산출물 ①⑥, 10절 11번 | 20 |

**왜 이 10건인가** — 1·2번이 `언제 멀티로 나눌지`를 서로 다른 근거(실무 원칙 대 호출 수·토큰 정량)로 답하고,
5번이 품질속성 양식을, 6·7번이 가드레일·관측의 표준 어휘를, 8·9번이 측정 공백을, 10번이 국내 규제 근거를
채움. 3·4번은 도서 전부가 아직 담지 못한 최신 변경을 담음(2절 참조).

---

## 2. 교재에 즉시 반영할 8건 — 확인 과정에서 드러난 변경·공백

v1 작성 시점과 달라진 사실 또는 새로 확인한 공백임. 교재 집필 전에 처리해야 함.

| # | 항목 | 내용 | 조치 |
|---|------|------|------|
| 1 | **MCP 최신 개정판** | 2026-08 기준 최신은 **2026-07-28**임. 핸드셰이크·`Mcp-Session-Id` 제거로 **무상태화**되고 `Roots`·`Sampling`·`Logging` 3기능이 폐기 예정임. `server/discover` RPC가 필수가 됨 | MCP 절은 공식 명세로만 작성함. **조사한 도서 전부가 미반영**임. 스타터 리포지토리 MCP 클라이언트가 폐기 3기능에 의존하지 않는지 점검함 |
| 2 | **A2A 버전** | v0.3 → **v1.0(2026-03-12)**. `kind` 판별자 제거 등 파괴적 변경이 있음 | 4-4절 인용에 `v1.0` 병기함. 실습 대상 아님을 함께 표기함(팀 1개 MAS에는 개입하지 않음) |
| 3 | **관측 표준 표기** | `experimental`이 아니라 현행 어휘는 **`Development`**임. `gen_ai.*` 중 Stable 항목은 없고 `error.type`·`server.address`만 Stable임. 본체 semconv가 v1.43.0(2026-07)에서 `gen_ai.*`를 완전 제거해 1차 출처가 전용 저장소로 이전됨 | 각주를 전용 저장소로 교체함. 버전 대신 **조회 시점 병기**(`main 브랜치 2026-08-05 기준`). `표준 후보` 표현 유지 |
| 4 | **7-2절 측정 공백** | 시스템 품질(MAS 흐름·NL2SQL)이 육안 확인에 머물러 2절 차별성과 어긋남. 이를 메울 지표가 **Ragas 안에 이미 존재**함 | `RAGAS 4지표 + ToolCallAccuracy·ToolCallF1 + Execution based Datacompy Score`로 확장함. 신규 도구 도입 없음. 지표 교체는 불필요 |
| 5 | **국내 규제 근거** | v1이 인용한 금융위 85908은 **개정방향 단계** 문서임. 최종 개정안은 2026-06-18 발표·**2026-06-22 시행**이며 7대 원칙 중 **`보조수단성`**이 7-3절 `사람의 최종 판단`의 직접 근거임 | 본문 근거를 87142로 교체하고 85908은 계보 설명용으로 내림 |
| 6 | **v1 수치 오류 3건** | ① `Spider 2.0 10.1%`는 2024-11 GPT-4o 기준이며 해당 설정이 2025-05-22 제거됨(2026-08-05 조회 시 Spider 2.0-Snow 1위 96.70%) ② `Essential GraphRAG`는 2025-08이 아니라 **2025-07** ③ `AI-Powered Search`는 **2024-12** 발행으로 기준 미달 | ①은 인용 중단 또는 조건 병기, ②는 연월 수정, ③은 목록에서 제외하고 하이브리드 검색 근거를 Azure RRF 문서(2026-06)로 대체 |
| 7 | **RAGAS 코드 표기** | 구 `ragas.metrics` API는 v1.0에서 **제거 예정**이며 `ragas.metrics.collections`로 이관해야 함. `Relevance`의 정식 명칭은 **`Response Relevancy`**임 | 스타터 리포지토리 측정 러너를 신 API로 작성하고 교재 표기를 정정함 |
| 8 | **협의 안건 추가 권고** | 커리큘럼 4-3절 `LangGraph 단독 사용`이 LangChain 1.0(2025-10-22 GA) 이후 표준 진입점이 된 `create_agent`+미들웨어와 어긋날 수 있음. 특히 **`PII redaction` 미들웨어가 7-3절 마스킹 지점을 대체**할 수 있어 산출물 ⑥ 작성 분량까지 바뀜 | 10절 협의 확인 사항에 `스타터 리포지토리 진입점 결정` 1행 추가를 권고함 |

---

## 3. 도서 추천 (2025년 이후 출간분)

### 3-1. 1순위 — 즉시 확보 권고 6권

| 도서 | 저자·출판 | 출간 | 왜 이 책인가 | 점수 |
|------|----------|------|------------|------|
| **만들면서 배우는 AI 에이전트 개발 입문+실전** | 박나연 / 한빛미디어, 652쪽 | 2026-05 | 부제에 **`LangGraph v1 기반`** 명시 — 조사 대상 중 **API 노후화 위험이 가장 낮음**. 멀티에이전트 3패턴(네트워크·슈퍼바이저·계층형)·메모리·MCP·A2A가 한 권에. 한국어라 6절 선수학습 지정 가능 | 19 |
| **AI Agents and Applications** | Roberto Infante / Manning, 448쪽 | 2026-02 | 목차가 Day 2 실습 순서와 거의 겹침. 11장이 도구 등록 → 상태 추적 → 그래프 조립 → 디버깅 순이라 **스타터 리포지토리의 "배관만 제공" 경계 설계에 직접 참고**. 독자 저장소 실측 `langchain==1.0.3` | 19 |
| **Essential GraphRAG** | Bratanič·Hane / Manning, 176쪽 | 2025-07 | Day 2 검색 방식 비교와 범위 일치. 벡터·하이브리드·Text2Cypher를 한 권에서 비교. **[Neo4j 전권 무료 제공](https://neo4j.com/essential-graphrag/)** | 19 |
| **Knowledge Graphs and LLMs in Action** | Negro 외 4인 / Manning, 472쪽 | 2025-10 | GraphRAG 에이전트를 **도구 3종 구성**(KG Retriever·KG-Enhanced Doc Retriever·벡터)으로 제시. 14장 스키마 기반 질의, **15장이 LangGraph QA 에이전트**. 8-1절 Neo4j dump 스키마 설계에 직결 | 19 |
| **Agentic Architectural Patterns for Building Multi-Agent Systems** | Arsanjani(Google Cloud)·Bustos / Packt, 16장 | 2026-01 | **13~15장이 여신 심사(loan processing)를 단일 → 멀티 → 프레임워크로 3연속** 다룸. KT 케이스(금융상품 추천)와 도메인이 겹쳐 실습 시나리오 각색에 그대로 사용 가능 | 18 |
| **Building Applications with AI Agents** | Michael Albada / O'Reilly, 352쪽 | 2025 | 8장 `From One Agent to Many`가 단일→멀티 판정에 독립 배정. [예제 저장소](https://github.com/michaelalbada/BuildingApplicationsWithAIAgents)가 **동일 시나리오를 LangGraph·AutoGen 병렬 구현 + 공용 평가 하네스 + OTel 관측** 구조라 8-1절 설계 참고 | 18 |

### 3-2. 2순위 — 목적이 맞을 때만

| 도서 | 출간 | 쓸 곳 | 주의 |
|------|------|------|------|
| **Securing AI Agents** (Huang·Hughes / Springer, 373쪽) | 2025-09 | 산출물 ⑥⑦, **11장이 금융을 첫 사례**로 다뤄 7-3절 대응. 2장이 위협모델링 독립 장 | 유료(Springer), O'Reilly 구독으로 대체 불가 |
| **Observability Engineering, 2nd Edition** (O'Reilly) | 2026-06 | Day 1 이론 `관측 가능성 설계`. 1판 대비 **신규 27개 장**이며 `AI 에이전트 계측`·비결정적 워크로드가 신규 주제 | 목차 원문 미확인(O'Reilly 403). 에이전트 분량 비중 미확정 |
| **개발자를 위한 쉬운 쿠버네티스** (위키북스, 384쪽) | 2025-05 | **6절 선수학습(플랫폼 엔지니어) 지정 후보**. 2장 컨테이너화 순서가 Day 2~3과 거의 일치 | 예제가 GKE 기준이라 EKS와 일부 명령이 다름 |
| **The Kubernetes Book (2026 Edition)** (Poulton, 336쪽) | 2026-06 | Day 3 외부 접근 경로(Service·신설 Gateway API 장) | 자가출판·매년 개정 → 각주에 판본 병기 필수. AI 관련 장 없음 |
| **A Simple Guide to Retrieval Augmented Generation** (Manning, 256쪽) | 2025-06 | 개선 1회차 선택지 목록(의미·에이전틱 청킹, 하이브리드·반복 검색) | 입문서로 설계 근거로는 얕음. RAGAS 실행 절차 없음 |
| **AI 에이전트 개발 완벽 입문** (위키북스, 732쪽) | 2026-04 | 선수학습 보조. 랭그래프 4장·MCP 9장 | CrewAI·smolagents·n8n은 4-5절 제외 범위 → **읽을 장을 1~4·9장으로 한정** 지정 |
| **Agentic AI: Theories and Practices** (Ken Huang 편 / Springer, 407쪽) | 2025-06 | 3장 멀티에이전트 조정(47쪽), **8장 AI Agents in Banking(40쪽)** | 담당 영역 해당 장이 2개뿐. 2장이 AutoGen·CrewAI 병렬로 4-3절 방침과 어긋남 |
| **AI 에이전트 마스터 클래스** (한빛, 340쪽) | 2026-01 | 선수학습 보조. CheckPointer 장 | 배포가 Streamlit 수준이라 Day 3과 어긋남. 평가 장 없음 |
| **Context Engineering** (García / Manning) · **RAG, The Foundational Ideas** (Auffarth / Manning) | 2026-08 MEAP · 2026-10 출간 예정 | 컨텍스트 스택·RAG 논문 계보 | **둘 다 MEAP(미완성)** — 목차·페이지가 바뀔 수 있어 각주 인용 부적합. 개념 참조만 |

### 3-3. 비추천 — 2025년 출간이지만 코드가 낡음

LangChain 1.0·LangGraph 1.0이 **2025-10-22 GA**되었고 현행 진입점은 `create_agent`+미들웨어임.
아래 3권은 그 이전 세대로, 지면 코드를 그대로 옮기면 동작하지 않음.

| 도서 | 출간 | 지면 기준 | 위험 | 실측 근거 |
|------|------|----------|------|----------|
| 랭체인과 랭그래프로 구현하는 RAG·AI 에이전트 실전 입문 (위키북스) | 2025-06 | `langgraph==0.2.22` / `langchain==0.3.0` | **매우 높음** | 저장소 `requirements.txt` 실측. httpx 의존성 붕괴(`proxies` 오류)가 README에 이미 문서화됨. LCEL 중심 구성 |
| 랭체인 & 랭그래프로 AI 에이전트 개발하기 (길벗) | 2025-03 | 미표기(0.2~0.3 추정) | **매우 높음** | v1 대응 표기 없음. 4부가 M365 코파일럿으로 범위 외 |
| Generative AI with LangChain, 2nd ed. (Packt) | 2025-05 | **LangChain v0.3** | **높음** | 저장소가 `v1`/`2nd edition`/`softupdate`/`main` **4브랜치 유지** — 계열 도서의 노후화 속도를 보여주는 증거 |

- 예외 활용: 위키북스판 **7.4절(Ragas 합성 테스트 데이터 생성)** 만 발췌 참조 가능함
- **교재 집필 규칙** — 도서 참조 표에 `지면 버전`·`저장소 브랜치` 2열을 필수로 두고, 스타터 리포지토리
  코드는 도서에서 인용하지 않고 공식 문서 + `context7` 대조로 작성함

---

## 4. 웹문서 추천 — 영역별

1절 최우선 10건에 든 항목은 여기서 생략함.

### 4-1. 설계 방법론·아키텍처 문서화

| 자료 | 발행 | 핵심 | 커리큘럼 대응 |
|------|------|------|--------------|
| [Describing Agentic AI Systems with C4](https://arxiv.org/html/2603.15021v1) | 2026-03 | 에이전트를 **C3 컴포넌트 계층의 활동**으로 두고 `<<agent>>`·`<<task>>` 스테레오타입 부여. **입출력은 에이전트가 아니라 태스크가 소유** | 산출물 ② 계층 확정, ④ 표기 규칙 |
| [Designing Effective Multi-Agent Architectures (O'Reilly Radar)](https://www.oreilly.com/radar/designing-effective-multi-agent-architectures/) | 2026-02 | 감독자형·블랙보드형·P2P·스웜의 적합 상황과 실패 양상. 실패 원인을 프롬프트가 아닌 협업 구조로 지목(`프롬프팅 오류`) | Day 1 이론 읽기자료, ④ 후보 대조표 |
| [RAD-AI: Rethinking Architecture Documentation](https://arxiv.org/html/2603.28735v1) | 2026-03 | arc42에 7절 확장+1절 신설, C4에 3다이어그램 확장. **AI 경계마다 `출력 유형·신뢰도 규격·갱신 주기·폴백` 4부 계약** | 산출물 ② 신뢰 경계, ⑦ 운영 뷰 |
| [Agent Contracts (COINE 2026)](https://arxiv.org/html/2601.08815v3) | 2026-01 | 계약에 입출력·자원 상한·시간 경계·성공 기준을 묶고 위임 예산에 **보존 법칙** 적용. 도입 사례로 재귀 루프 11일 방치·API 4.7만 달러 사고 | 산출물 ③ 중단 조건, ⑥ 비용 상한 |
| [Architectures for Building Agentic AI (Springer 3장 프리프린트)](https://arxiv.org/html/2512.09458v1) | 2025-12 | 실행 게이트웨이에 스키마 검증·`시뮬레이트 후 작동`·멱등성 토큰. 에이전트 간 전달을 원문이 아닌 **요약·타입 있는 사실**로 제한 | 산출물 ③ 입출력, ④ 전달 형식 |
| [LLM 기반 MAS 품질속성·패턴 분석 (논문 94편)](https://arxiv.org/html/2511.08475v2) | 2025-11 | **ISO/IEC 25010:2023 분류로 집계** — 기능적합성 94.7%, 보안·상호작용성은 10% 내외. 현장이 기능 정확성에 편중됨을 수치로 보여줌 | 산출물 ① 품질속성 어휘 고정 |
| [MAS 역할 개념 비판 (EMAS 2025)](https://emas.in.tu-clausthal.de/2025/assets/pdfs/emas2025-14.pdf) | 2025-05 | **GAIA의 역할이 `책임·프로토콜·권한`을 포함**함을 명시 — 4-4절 `역할에 권한 포함` 규칙의 2025년 인용 출처 | 산출물 ③ 권한 칸 정당화 |
| [A practical guide to building agents (OpenAI, 34쪽)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) | 2025-04 | **AI 적용 적합성 3기준**(복잡한 판단·유지 어려운 규칙·비정형 의존)과 배제 기준. 도구 문제는 개수가 아니라 **중복**이라고 정정 | **Day 1 이론 `AI 적용 적합성 판별` 1차 기준표** |

### 4-2. 구현·프로토콜

| 자료 | 발행 | 핵심 |
|------|------|------|
| [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | 2026-06 | `Checkpointer`(스레드 단기) 대 `Store`(스레드 간 장기) 구분. 함정 4종 — **`MemorySaver` 재시작 시 소실**은 Day 3 배포에서 실제로 부딪히는 지점 |
| [MCP 2026-07-28 릴리스 후보 해설](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) | 2026-05 | 무상태화로 라운드로빈 LB 뒤 운영 가능. 변경 전·후 HTTP 예시가 나란히 있어 슬라이드 1장으로 전용 가능 |
| [LangChain·LangGraph v1.0 마일스톤](https://www.langchain.com/blog/langchain-langgraph-1dot0) | 2025-10 | `create_agent` 새 진입점, 기본 미들웨어에 HITL·요약·**PII redaction**. 2.0까지 파괴적 변경 없음 약속 |
| [Cognition — Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) | 2025-06 | 컨텍스트를 메시지가 아닌 **트레이스 전체**로 공유. 결정 충돌이 없게 분할. Flappy Bird 실패 경로 구체화 |
| [LangChain — How and when to build multi-agent systems](https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems) | 2025-06 | **읽기 중심 MAS는 쓰기 중심보다 쉽다** — 마이데이터 과제의 병렬·단일 구간을 가르는 기준으로 그대로 적용 가능 |
| [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | 2025-06 | 서브에이전트마다 `목표·출력 형식·도구·출처 지침·과제 경계` 4요소 명시 필수 — **산출물 ③ 칸 구성과 거의 일치** |
| [Anthropic — Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) | 2025-11 | 도구 정의가 컨텍스트를 선점하고 중간 결과가 반복 소모됨. 2시간 회의록 예시에서 약 5만 토큰 추가 소모 계산 |
| [Chroma — Context Rot](https://research.trychroma.com/context-rot) | 2025-07 | 18개 모델 실험으로 "컨텍스트를 균일하게 처리한다"는 가정 반박 | 
| [A2A 명세 v1.0](https://a2a-protocol.org/latest/specification/) | 2026-03 | `Major.Minor`만 협상, `kind` 판별자 제거, 서명된 Agent Card. **실습 대상 아님 — 이론 인용 한정** |

### 4-3. 검색·데이터·평가

| 자료 | 발행 | 핵심 |
|------|------|------|
| [Neo4j GraphRAG for Python 공식 문서](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html) | 패키지 1.18.0 / 2026-06 | **검색기 9종을 동일 `search()` 인터페이스로 제공** → 벡터·하이브리드·GraphRAG를 코드 한 줄 교체로 비교 가능. 단 **하이브리드 계열은 필터 미지원**(금융 실습 제약) |
| [Ragas — 지표 전체 목록](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/) | 2025-12 | 7개 군 분류. 커리큘럼 4지표는 그대로 존재하며 폐기 없음. **에이전트·도구 4종과 SQL 2종이 추가**됨 |
| [Ragas — 테스트셋 생성(지식그래프 기반)](https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/) | 2025-12 | 문항을 `단일홉/멀티홉 × 구체/추상` 2×2로 분류. **금융 문서 예시**(재무제표 절 단위 커스텀 분할기) 포함 |
| [독립 연구 — GraphRAG 진실성 비교 (NICD)](https://neo4j.com/blog/agentic-ai/study-graphrag-ai-agents-80-percent-more-truthful/) | 2026-07 | MoNaCo 510문항: 진실성 63 대 35, 복잡 질문 응답 시도율 65.3% 대 28.9%. **정교한 온톨로지 없는 경량 그래프**에서 나온 결과 — **단, Neo4j 후원 연구임을 병기** |
| [GraphRAG-Bench (ICLR 2026 채택)](https://github.com/GraphRAG-Bench/GraphRAG-Benchmark) | 2026-01 | 문제 제기가 4-2절 학습 목표와 동일 — "GraphRAG가 일반 RAG보다 못한 경우가 잦다. 이득이 나는 시나리오는 어디인가". 과업을 난이도 4단계로 계층화 |
| [Agentic GraphRAG — 상업등기부 감사가능 분석](https://arxiv.org/abs/2605.18770) | 2026-07(v2) | 정형은 **결정적 적재**, 비정형만 LLM 추출, 신원해소는 결정적 계층 — **어디까지 규칙이고 어디부터 LLM인지의 경계 설계 사례**. 답변마다 근거 그래프·실행 트레이스 노출 |
| [Azure AI Search — RRF 관련성 스코어링](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) | 2026-06 | `1/(rank+k)`, k=60. **이 k는 kNN의 k와 완전히 별개**(교재 최대 혼동 지점). 점수 범위 표로 순위 융합의 이유 설명 |
| [Text-to-SQL Benchmarks are Broken (CIDR 2026)](https://www.vldb.org/cidrdb/papers/2026/p5-jin.pdf) | 2026-01 | BIRD Mini-Dev 문항 **52.8%**가 주석 오류. 오류 4패턴(E1~E4) → **8-2절 D-7 도메인 전문가 검증 체크리스트로 그대로 전환 가능** |
| [LangSmith — Evaluate a complex agent](https://docs.langchain.com/langsmith/evaluate-complex-agent) | 2026-08 | 평가를 최종 응답·**경로(trajectory)**·단일 스텝 3층으로 분리. `trajectory_subsequence`로 기대 단계 순서 부분일치 비율 산출 — **SaaS 도입 없이 로직만 차용** |
| [ORAN Vector·Graph·Hybrid RAG 벤치마크](https://arxiv.org/abs/2507.03608) | 2025-08(v2) | 같은 문서로 3종을 동일 지표 비교 — Day 2 실습과 구조가 같은 실험 설계. Hybrid GraphRAG 사실 정확성 +8%, GraphRAG 맥락 관련성 +11%(상대 개선폭) |
| [RAG vs. GraphRAG 체계적 평가](https://arxiv.org/abs/2502.11371) | 2026-03(v3) | 평가 프로토콜 통일. 결론이 **한쪽 승리가 아니라 선택·통합 전략** — Day 2 비교 실습의 결론 유도 근거 |

### 4-4. 가드레일·보안·관측·배포

| 자료 | 발행 | 핵심 |
|------|------|------|
| [Google's Approach for Secure AI Agents (18쪽 PDF)](https://storage.googleapis.com/gweb-research2023-media/pubtools/1018686.pdf) | 2025-05 | 위험을 `rogue actions`·`sensitive data disclosure` 2개로 좁힘. 결정형 단독은 효용을 깎고 모델 판단 단독은 인젝션에 뚫림 → **하이브리드 다층 방어**. 13쪽 Figure 3이 산출물 ⑥ 템플릿 구획의 원형 |
| [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) | 2026-03 | **도구 스키마 전체를 인젝션 표면으로 취급**(`description`만 검사하면 불충분). 도구 정의 해시 고정으로 rug pull 차단 |
| [MCP 공식 Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices) | 2026-07 | confused deputy 성립 조건 4개를 명시 — **하나만 끊어도 차단됨**. 토큰 패스스루 금지·SSRF·스코프 최소화를 공격·완화 쌍으로 정리 |
| [AWS Well-Architected Agentic AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentic-ai-lens.html) | 2026-06 | 실제 구조가 `질문 + Capability intent + **5단계 성숙도 표**`임 → **산출물 ① 품질속성 문장을 성숙도 레벨 2 서술로 채울 수 있음**. AGENTCOST02는 모델 계층화·캐시 적중률 추적 규정 |
| [OTel GenAI 컨벤션 현황 (2026-07)](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/) | 2026-07 | Stable 항목이 하나도 없음을 정리. 개명 이력 3건 — `gen_ai.system`→`gen_ai.provider.name`(2025-08), `invoke_agent` client/internal 분리(2026-04). **개인 블로그이므로 표준 원문과 교차 확인 필요** |
| [Amazon EKS Best Practices Guide (공식 이관본)](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html) | 2026-07 | `aws.github.io` 판이 AWS 공식 문서로 **이관 완료**되고 [한국어 경로](https://docs.aws.amazon.com/ko_kr/eks/latest/best-practices/security.html)도 존재 → v1의 링크 병기 이슈 해소 |
| [EKS Workshop — External Secrets Operator](https://www.eksworkshop.com/docs/security/secrets-management/secrets-manager/external-secrets) | 2026-04 | 비밀값 주입이 `ClusterSecretStore` + `ExternalSecret` 2리소스로 끝남. IRSA로 정적 키 제거. **3일 편성에서는 산출물 ⑦ 선택지 비교용**으로 쓰고 실습은 Secret 직접 생성 권고 |
| [Kubernetes — Secrets 좋은 실천법](https://kubernetes.io/docs/concepts/security/secrets-good-practices/) | 2025-06 | Secret은 base64일 뿐 **기본적으로 etcd에 암호화되지 않음**. `list` 권한은 사실상 조회 권한이며 Pod 생성 권한자는 값을 볼 수 있음 |
| [The best Docker base image for Python](https://pythonspeed.com/articles/base-image-python-docker-images/) | 2026-02 | Alpine은 musl libc로 빌드 실패·성능 문제 → 회피 권고. `slim-trixie` 41MB 대 `alpine` 17MB. **Day 2 빌드 게이트 통과율에 직결** |
| [NIST CAISI — AI Agent Hijacking 평가](https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations) | 2025-01 | 원인을 **신뢰된 지시와 외부 데이터를 한 입력으로 합치는 분리 부재**로 지목. 집계 성공률만 보면 위험을 놓침 |

### 4-5. 트렌드·국내 자료 (도입부·규제 근거)

| 자료 | 발행 | 표본·시점 | 핵심 |
|------|------|----------|------|
| [Deloitte — Agentic AI is scaling faster than guardrails](https://www.deloitte.com/us/en/insights/topics/emerging-technologies/ai-agents-scaling-faster.html) | 2026-04 | IT·비즈니스 리더 3,235명 / 24개국 / **독립 조사** | 2027년까지 74%가 도입 예상, **성숙한 거버넌스는 21%뿐**. 나머지 약 80%는 결정 경계·실시간 모니터링·감사 추적이 모두 없음 |
| [Anthropic — The 2026 State of AI Agents Report (48쪽)](https://resources.anthropic.com/hubfs/The%202026%20State%20of%20AI%20Agents%20Report.pdf) | 2025-12 | 미국 기술 리더 500명 이상 / **벤더 자체 조사** | 최대 장벽이 모델 성능·비용이 아니라 **데이터 접근성과 조직 준비도**. 금융 3사례 — NBIM 주당 20% 절감, N26 프로세스 70% 자동화, Parcha CDD 3개월→5분 |
| [Why Do Multi-Agent LLM Systems Fail? (MAST)](https://arxiv.org/abs/2503.13657) | 2025-03(v3 2025-10) | 트레이스 1,600건 / UC Berkeley 계열 / κ=0.88 | 실패 모드 **14종·3군집** — 시스템 설계 결함 / 에이전트 간 정렬 실패 / 과업 검증 실패. **실패의 축이 모델이 아니라 설계와 검증**임 |
| [금융위 — 금융권 AI 협의회](https://www.fsc.go.kr/no010101/85908) | 2025-12 | 금융위 금융데이터정책과 | **합성데이터를 정식 활용 대상**으로 다루고 가명·익명처리 체크리스트 제시 → 4-5절 합성 데이터 대체 결정의 제도적 근거 |
| [개인정보위 — 전 분야 마이데이터 전송요구권 안내서](https://www.korea.kr/archive/expDocView.do?docId=41320) | 2025-04 | 개인정보보호위원회 | 전송요구권 요건·절차·안전조치. **금융 마이데이터(신용정보법)와 법령이 다르므로 `동의·전송의 일반 구조` 설명에만 사용** |
| [신한은행 AI 점검 에이전트](https://www.youthdaily.co.kr/news/article.html?no=224379) | 2026-08 | 은행 내부 측정치 / 언론 보도 | 건당 점검 시간 약 70% 감소·일 처리량 약 3배. **AI 결과를 본부 직원이 검토해 최종 판단하는 이중 확인 구조 유지** |
| FDE 개념 — [MarkTechPost](https://www.marktechpost.com/2026/05/20/what-is-a-forward-deployed-engineer-the-ai-role-openai-anthropic-and-google-are-hiring-in-2026/) | 2026-05 | 기술 미디어 집계 | FDE는 **산출물이 보고서가 아니라 고객 시스템에서 돌아가는 코드**인 고객 대면 엔지니어. 요구 역량 목록이 커리큘럼과 거의 일치 → 1절 지향점 정의 근거 |

**Day 1 오전 도입부 인용 3건** — `문제 제기 → 국내 현실 → 이 교육의 답` 순서로 배치함.

| # | 소재 | 슬라이드 맥락 |
|---|------|--------------|
| 1 | Deloitte 74% 도입 의향 대 **거버넌스 성숙 21%** | 오프닝 WHY — "만드는 법은 퍼졌고 없는 것은 통제와 근거임. 그래서 3일이 코드가 아니라 **설계 산출물 7종과 측정**부터 시작함" |
| 2 | 신한은행 70%↓·3배↑ + **사람 최종 판단 유지** | 케이스 브리핑 직전 — "가정이 아니라 지난달 국내 은행에서 실제로 돌아간 일임. 그리고 사람이 최종 판단함 → 우리 산출물도 `제안서`임" |
| 3 | MAST **실패 모드 14종**이 설계·정렬·검증 군집 | 이론 `MAS 패턴` 진입 — "패턴을 감각으로 고르면 이 중 하나에 빠짐. 그래서 9단계 절차와 역할 계약서를 씀" |

**수치 인용 규칙(집필 시 준수)** — 벤더 자체·의뢰 조사와 독립 조사를 슬라이드에서 시각적으로 구분하고,
모든 조사 수치에 `표본 n / 조사 시점 / 조사 주체`를 각주로 병기함.

---

## 5. 자료 간 상충 2건 — 교재에서 한쪽을 고정해야 함

추천 자료끼리 결론이 다른 지점임. 어느 쪽이 맞다고 단정할 근거가 없으므로 처리 방침을 정해 둠.

| 상충 | A 입장 | B 입장 | 권고 |
|------|--------|--------|------|
| **C4에서 에이전트의 계층** | C4 논문(2026-03): 에이전트는 **C3 컴포넌트 계층의 활동**이며 C2는 노드·프로토콜만 | RAD-AI(2026-03): AI 구성요소에 스테레오타입을 붙인 **컨테이너**로 다룸 | 산출물 ② 템플릿에 **한쪽을 고정**하고 다른 쪽은 각주로 대안 표기함. 팀별로 다르게 그리면 리뷰가 성립하지 않음 |
| **역할 분해 방식** | 논문 94편 집계: 최다 채택 패턴은 **역할 기반 협업**(기획·구현·검토 분업) | Anthropic(2026-01): 그 형태가 **핸드오프마다 맥락이 소실되는 전화게임**을 유발 → **컨텍스트 경계별** 분해 권고 | **실습 판단 대상으로 드러내는 편**을 권고함. 같은 과제를 두 분해로 놓고 비교하면 커리큘럼의 `수강생 주도 결정` 의도와 맞음 |

---

## 6. 접근 실패·미확인 — 추천하지 않음

확인하지 못한 것을 확인한 것처럼 쓰지 않기 위해 분리함. 교재 인용 전 후속 확인 대상임.

| 자료 | 상태 | 필요 조치 |
|------|------|----------|
| ~~OWASP Top 10 for Agentic Applications 2026 — **PDF 본문**~~ **→ 2026-08-05 확보 완료** | 조사 시점에는 이메일 등록 게이트로 미확인이었음. **이후 원문 PDF 57쪽을 `references/books/OWASP-Top-10-for-Agentic-Applications-2026-12.6-1.pdf`로 확보하여 전량 판독함**(`Version 2026 / December 2025`) | **조치 완료.** 10종 `ASI01` ~ `ASI10`과 항목별 완화책을 [A06 정리본](articles/A06_std_owasp-agentic-top10.md)에 정리함. 조항 인용 제한 해제됨 |
| OWASP Multi-Agentic System Threat Modeling Guide v1.0 | 발행일·목적만 확인. 본문·방법론 명칭 미확인 | 위와 동일 |
| Gartner — 에이전틱 AI 40% 취소 예측(2025-06) | **원문 403.** 2차 출처로만 확인. 표본이 웨비나 참석자 3,412명 폴로 **확률표본 아님** | `실패율`이 아니라 `취소 예측치`로 표기. 원문 확보 후 각주 |
| MIT NANDA — GenAI Divide 95%(2025-07) | **원문 PDF 403.** 2차 출처 2건으로만 확인. 표본 설문 153건으로 일반화 부족하며 방법론 비판 다수 | 단정 인용 금지. 쓰려면 `표본 153건 기준` 병기 |
| McKinsey — State of AI trust in 2026 | WebFetch 3회 ECONNRESET·curl 타임아웃으로 **본문 미판독** | 재시도 또는 PDF 직접 확보 |
| O'Reilly 플랫폼 도서 4종(Learning LangChain, Context Engineering with DSPy 외, Observability Engineering 2nd 목차, The C4 Model) | HTTP 403으로 목차 확인 실패 | O'Reilly 구독 계정으로 접근 |
| Building Knowledge Graphs 무료 PDF (v1 수록분) | Neo4j 무료 배포 프로모션 **종료 안내** 확인 | 링크 접근 가능 여부 재확인 |
| GraphRAG 자가출판 도서 2종 · graphrag.com | 발행일·본문 미확인(JS 셸·차단) | 신뢰도 확인 전 인용 금지 |
| 금융보안원 「금융분야 AI 보안 안내서」·금감원 「AI 위험관리프레임워크」(2026-06-22 배포) | 배포 사실만 확인 | 자료실에서 원문 확보 — 산출물 ①⑥을 국내 기준으로 보강 가능 |

---

## 7. 조사 분담과 검증 범위

**분담** — 클로니가 5개 영역으로 나눠 병렬 위임하고, 반환된 5건을 교차검증·중복 제거해 본 문서로 통합함.

| 담당 | 영역 | 원본 보고서 | 확인 건수 |
|------|------|-----------|----------|
| 아키텍트 | 설계 방법론·아키텍처 문서화·품질속성 | [A-설계방법론.md](.research/A-설계방법론.md) | 도서 3 · 웹 11 |
| AI 엔지니어 | 구현 프레임워크·오케스트레이션·컨텍스트·프로토콜 | [B-구현프레임워크.md](.research/B-구현프레임워크.md) | 도서 7 · 웹 16 |
| AI 엔지니어 | RAG·하이브리드 검색·GraphRAG·NL2SQL·평가 | [C-검색평가.md](.research/C-검색평가.md) | 도서 4 · 웹 14 |
| DevOps 엔지니어 | 가드레일·보안·관측·컨테이너·EKS | [D-가드레일관측배포.md](.research/D-가드레일관측배포.md) | 도서 4 · 웹 13 |
| AI 교육 콘텐츠 전문가 | 도입 동향·기업 사례·한국어 자료·금융 규제·FDE | [E-트렌드국내자료.md](.research/E-트렌드국내자료.md) | 한국어 8 · 영문 6 |

**확인한 것**
- 웹문서는 `curl -sL` 저장 후 본문 판독을 원칙으로 하고, 403·JS 셸인 경우 WebFetch로 재시도함
- 발행일은 본문 표기·arXiv 제출일·GitHub 커밋 이력·패키지 릴리스일·출판사 서지 중 하나로 개별 확인함.
  날짜 표기가 없는 공식 문서는 원본 저장소의 해당 파일 최종 커밋일을 갱신일로 사용함
- LangGraph 현행 API는 `context7` MCP로 교차 확인함(`StateGraph`·`Annotated` 리듀서·`Command`·`Overwrite`)
- 도서 2건은 예제 저장소 `requirements.txt`를 실측해 고정 버전을 확인함(3-3절 근거)

**확인하지 못한 것**
- **유료 도서의 본문 전량.** 목차·chapter briefs·소개문 수준까지만 확인했으며 지면 코드를 실행 검증하지
  않았음. 조항·코드를 교재에 옮길 때는 확보 후 대조가 필요함
- 6절에 열거한 접근 실패 자료 전부

---

## 부록 A. v1 대비 변경 요약

| v1 | 본 문서 |
|----|--------|
| 1순위에 Wooldridge(2009)·Bass 외(2021)를 올림 | **추천 목록에서 제외**하고 부록 B로 이동. 2025년 이후 대체 자료로 1순위를 재구성함 |
| ATAM(2000) 원문을 품질속성 양식의 출처로 사용 | **AgentArcEval(2025-10)** 로 교체 — ATAM 6칸 양식을 이어받아 에이전트용 시나리오 11종을 카탈로그화함. Kazman 본인 공저 |
| MCP 최신 개정일 미확인 | **2026-07-28** 확인 |
| OTel을 블로그·정리본으로 인용, `experimental` 표기 | 1차 출처를 전용 저장소로 교체, **`Development`** 로 표기 갱신 |
| AI-Powered Search(Manning) 추천 | **2024-12 발행**으로 기준 미달 → Azure RRF 문서(2026-06)로 대체 |
| Spider 2.0 10.1% 수치로 실습 난이도 설명 | 설정이 제거된 2024-11 수치 → 인용 중단 권고 |
| 금융위 85908을 AI 가이드라인 근거로 사용 | **87142(2026-06 최종 개정안, 2026-06-22 시행)** 로 교체 |

## 부록 B. 2025년 이전 자료 — 추천 아님, 각주 출처로만

조사 대상에서 제외했으나, 아래 5건은 **양식·정의의 원전**이어서 각주 표기에만 필요함.
강의 본문 서술과 예시는 1~4절 자료로 구성함.

| 자료 | 발행 | 각주로만 필요한 이유 |
|------|------|-------------------|
| [ATAM: Method for Architecture Evaluation (CMU/SEI-2000-TR-004)](https://www.sei.cmu.edu/documents/629/2000_005_001_13706.pdf) | 2000 | 품질속성 시나리오 6요소(`source·stimulus·artifact·environment·response·response measure`)의 원전. AgentArcEval이 이 양식을 그대로 이어받음 |
| ISO/IEC 25010:2023 | 2023 | 품질속성 분류 어휘의 현행 표준. 2025년 이후 대체 표준 없음 |
| [Developing multiagent systems: The Gaia methodology (ACM TOSEM)](https://dl.acm.org/doi/10.1145/958961.958963) | 2003 | `역할 = 책임·프로토콜·권한` 정의의 원전. 4-4절 `역할에 권한 포함` 규칙의 출처 |
| An Introduction to MultiAgent Systems, 2nd ed. (Wooldridge) | 2009 | 역할·조직구조 개념의 교과서적 정본이며 Gaia 공동 저자 서술. **LLM 내용 없음** |
| ISO/IEC/IEEE 42010 | 2011 또는 2022 | 관심사–뷰포인트–뷰 대응의 표준 근거. **판본 확정 필요**(iso.org 403으로 미확인) |

- 커리큘럼 4-4절의 `20년 축적된 계보` 서술은 위 정본으로, **현행성은 AgentArcEval·EMAS 2025 논문으로**
  이중 인용하는 구성을 권고함
