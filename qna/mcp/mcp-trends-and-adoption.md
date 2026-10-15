# MCP 최신 트렌드 및 활용 추이

- 작성일: 2026-10-15  
- 작성: 클로니(Agentic AI 아키텍트)  
- 성격: 공개 출처 조사 기반 답변. 사실(Fact)과 의견(Opinion)을 구분해 기술함  
- 출처 우선순위: MCP 공식 사양과 공식 블로그, Linux Foundation 보도자료, Anthropic 공식 글,  
  미국 NSA와 OWASP와 CSA 같은 보안 기관 문서, 패키지 저장소 실측 API 순으로 신뢰함.  
  벤더 블로그와 집계 사이트 수치는 "미검증"으로 표시함

---

## 1. 한 줄 요약

MCP(Model Context Protocol)는 2024년 11월 Anthropic이 공개한 "AI 모델과 외부 도구를 잇는 공통 규격"임.  
2년이 안 되는 사이에 OpenAI, Google, Microsoft, AWS가 모두 채택했고,  
2025년 12월 Linux Foundation 산하 Agentic AI Foundation(AAIF)으로 소유권이 넘어가 중립 표준이 됨.  
2026년 10월 현재 공식 SDK 다운로드는 월 5억 건 수준이며, 2026년 7월 28일 사양 개정으로  
"세션을 기억하는 프로토콜"에서 "보통의 HTTP API처럼 상태 없는 프로토콜"로 바뀌는 큰 전환이 일어남.  
활용 추이는 "개인 개발 도구에서 쓰는 단계"를 지나 "기업이 관리형 원격 서버로 운영하는 단계"로 옮겨가는 중이나,  
설문 기준 거버넌스가 갖춰진 전사 운영은 아직 5% 수준이고, 보안이 가장 큰 병목임.

---

## 2. Fact: MCP가 어디까지 왔나

### 2.1 연혁 한눈에 보기

| 시점 | 사건 | 출처 |
|------|------|------|
| 2024-11-25 | Anthropic이 MCP를 오픈소스로 공개. 초기 채택사 Block, Apollo, Zed, Replit, Sourcegraph | [Anthropic 발표](https://www.anthropic.com/news/model-context-protocol) |
| 2025-03-26 | 사양 개정(OAuth 2.1 인증, Streamable HTTP 전송). 같은 날 OpenAI가 Agents SDK에 MCP 채택 | [버전 연표](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html) |
| 2025-04-09 | Google이 Gemini 모델과 SDK에 MCP 지원 약속 | [버전 연표](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html) |
| 2025-06-18 | 사양 개정(구조화된 도구 출력, 엘리시테이션, 보안 모범사례 페이지 신설) | [버전 연표](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html) |
| 2025-11-21 | MCP Apps 확장 제안(SEP-1865). Anthropic, OpenAI, MCP-UI 공동 | [MCP 공식 블로그](https://blog.modelcontextprotocol.io/tags/apps/) |
| 2025-11-25 | 사양 개정(OpenID Connect 탐색, URL 모드 엘리시테이션, 실험적 Tasks, 거버넌스 공식화) | [2025-11-25 변경 내역](https://modelcontextprotocol.io/specification/2025-11-25/changelog) |
| 2025-12-09 | Linux Foundation이 AAIF 설립. Anthropic이 MCP, OpenAI가 AGENTS.md, Block이 goose를 기부 | [Linux Foundation 보도자료](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) |
| 2026-01-26 | MCP Apps가 첫 공식 확장으로 정식 출시 | [MCP 공식 블로그](https://blog.modelcontextprotocol.io/tags/apps/) |
| 2026-04 | MCP Dev Summit 북미(뉴욕) 개최, 약 1,200명 참석 | [Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol) |
| 2026-05-20 | 미국 NSA가 MCP 보안 설계 지침(CSI) 발표 | [NSA 문서 PDF](https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf), [Executive Gov](https://executivegov.com/articles/nsa-model-context-protocol-deployment) |
| 2026-07-28 | 사양 대개정(상태 없는 코어, 확장 프레임워크, 인증 강화, 폐기 정책) | [2026-07-28 변경 내역](https://modelcontextprotocol.io/specification/2026-07-28/changelog) |
| 2026-08-13 | MCP Dev Summit 서울 개최. AAIF 회원 247개 조직 도달 | [Linux Foundation 보도자료](https://www.linuxfoundation.org/press/agentic-ai-foundation-welcomes-57-new-members-gaining-major-financial-services-players-and-apac-leaders) |
| 2026-08-22 | 새 MCP 로드맵 공개(5개 우선 영역) | [MCP 공식 블로그](https://blog.modelcontextprotocol.io/posts/mcp-roadmap/) |

### 2.2 사양(스펙)은 어떻게 바뀌어 왔나

MCP는 버전 이름을 날짜로 씀. 지금까지 5개 버전이 나왔고, 흐름은 "로컬 도구 연결"에서 "분산 서비스 프로토콜"로 향함.

| 버전 | 핵심 변화 | 쉽게 말하면 |
|------|-----------|-------------|
| 2024-11-05 | JSON-RPC 기반 클라이언트-서버 구조, tools/resources/prompts, stdio와 HTTP+SSE 전송 | 내 PC 안에서 AI와 도구를 잇는 첫 규격 |
| 2025-03-26 | OAuth 2.1 인증 틀, Streamable HTTP 전송(세션 ID 헤더), 도구 주석 | 원격 서버에 로그인해서 쓸 수 있게 됨 |
| 2025-06-18 | 구조화된 도구 출력, 엘리시테이션(서버가 사용자에게 추가 입력 요청), 보안 모범사례 | 도구 결과를 표 형태로 받고, 중간에 사용자에게 물어볼 수 있음 |
| 2025-11-25 | OpenID Connect 탐색, 점진적 권한 동의, URL 모드 엘리시테이션, 실험적 Tasks(긴 작업 추적), 아이콘 메타데이터, SDK 등급제 | 기업 로그인 체계와 맞물리고, 오래 걸리는 작업을 나중에 받아올 수 있음 |
| 2026-07-28 | 프로토콜 세션과 initialize 핸드셰이크 제거, 매 요청이 자기 설명적, `server/discover` 추가, Multi Round-Trip Requests, 캐시 가능한 목록 결과, 공식 확장 프레임워크, Roots와 Sampling과 Logging 폐기 예고, DCR 대신 Client ID Metadata Documents | 보통의 HTTP API처럼 아무 서버 인스턴스가 아무 요청이나 받을 수 있음. 로드밸런서 뒤에 그냥 놓으면 됨 |

출처: [2025-11-25 변경 내역](https://modelcontextprotocol.io/specification/2025-11-25/changelog),  
[2026-07-28 변경 내역](https://modelcontextprotocol.io/specification/2026-07-28/changelog),  
[2026-07-28 공식 발표 글](https://blog.modelcontextprotocol.io/posts/2026-07-28/)

2026-07-28 개정의 의미를 공식 블로그는 이렇게 설명함.  
"MCP가 양방향 상태 유지 프로토콜에서 요청-응답 방식의 상태 없는 프로토콜로 바뀌는 중"이며,  
"개발자들이 서버의 안정성과 확장성을 위해 가장 많이 요청한 기능"이었다고 밝힘.  
이 개정은 호환성이 깨지는 변경(breaking change)을 포함하며, 폐기 기능은 최소 12개월 유예 기간을 둠.

### 2.3 누가 소유하고 운영하나: Anthropic에서 중립 재단으로

- 2025-12-09 Linux Foundation이 Agentic AI Foundation(AAIF)을 세우고 MCP를 넘겨받음  
- 플래티넘 회원: AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI  
- 골드 회원(설립 당시): Adyen, Cisco, Datadog, Docker, IBM, JetBrains, Okta, Oracle, Salesforce, SAP, Shopify, Snowflake 등  
- 설립 발표문 기준 공개된 MCP 서버는 1만 개 이상이며, Claude, Cursor, Microsoft Copilot, Gemini, VS Code, ChatGPT가 채택  
- 2026-08-13 기준 회원 247개 조직. 직전 분기에 57개가 새로 가입했고 Alibaba, Visa, Wells Fargo가 골드로 합류  
- 같은 발표에서 한국 ETRI(한국전자통신연구원)가 신규 회원으로 언급됨  

출처: [AAIF 설립 보도자료](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation),  
[AAIF 57개 회원 추가 보도자료](https://www.linuxfoundation.org/press/agentic-ai-foundation-welcomes-57-new-members-gaining-major-financial-services-players-and-apac-leaders)

### 2.4 생태계 규모: 숫자로 보기

아래 표의 "실측" 항목은 이 문서를 쓰면서 패키지 저장소 공개 API를 직접 호출해 확인한 값임.

| 지표 | 값 | 기준 시점 | 근거 |
|------|-----|-----------|------|
| TypeScript SDK 주간 다운로드(npm) | 64,994,424건 | 2026-10-06 ~ 2026-10-12 | 실측, [npm API](https://api.npmjs.org/downloads/point/last-week/@modelcontextprotocol/sdk) |
| TypeScript SDK 월간 다운로드(npm) | 273,345,683건 | 2026-09-13 ~ 2026-10-12 | 실측, [npm API](https://api.npmjs.org/downloads/point/last-month/@modelcontextprotocol/sdk) |
| Python SDK 주간 다운로드(PyPI) | 62,097,089건 | 최근 7일 | 실측, [pypistats API](https://pypistats.org/api/packages/mcp/recent) |
| Python SDK 월간 다운로드(PyPI) | 235,193,557건 | 최근 30일 | 실측, [pypistats API](https://pypistats.org/api/packages/mcp/recent) |
| Tier 1 SDK 합산 월간 다운로드 | "5억 건에 근접", TS와 Python 각각 누적 10억 건 돌파 | 2026-07-28 | [MCP 공식 블로그](https://blog.modelcontextprotocol.io/posts/2026-07-28/) |
| 공개 MCP 서버 수 | 1만 개 이상 | 2025-12-09 | [Linux Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) |
| 공식 레지스트리 등록 서버 수 | 4만 3천여 개(미검증) | 2026-10-14 | 집계 사이트 주장. 공식 API는 총계를 돌려주지 않아 직접 확인 못 함 |

읽는 법:  
- 두 SDK의 월간 실측 합계는 약 5억 8백만 건으로, 공식 블로그의 "5억 건에 근접"과 맞아떨어짐  
- 서버 수는 세는 방법(공식 레지스트리, GitHub 토픽, 집계 사이트)에 따라 1만에서 4만까지 벌어짐.  
  공신력 있는 숫자는 Linux Foundation이 밝힌 "1만 개 이상"까지임  

### 2.5 어느 플랫폼이 어떻게 쓰나

| 주체 | 활용 방식 | 출처 |
|------|-----------|------|
| OpenAI | 2025-03 Agents SDK부터 채택, 이후 ChatGPT 데스크톱과 Responses API. 2025-09 ChatGPT 앱에 MCP 지원 | [Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol) |
| Google Cloud | 2025-12 Google 서비스용 원격 MCP 서버 미리보기. 2026-03-17부터 지원 제품을 켜면 원격 MCP 엔드포인트가 기본 제공. 2026-04-10 Cloud Trace로 MCP 호출 추적 지원. 권한은 IAM 거부 정책으로 통제 | [Google Cloud MCP 릴리스 노트](https://docs.cloud.google.com/mcp/release-notes) |
| AWS | Amazon Bedrock AgentCore가 2026-07-28 사양의 상태 없는 코어를 지원. 세션이나 영구 연결 없이 MCP 서버 배포 가능 | [MCP 공식 블로그](https://blog.modelcontextprotocol.io/posts/2026-07-28/) |
| Microsoft | Copilot Studio가 초기 채택 플랫폼 중 하나. Semantic Kernel과 Azure OpenAI 연동. MCP Apps 지원 호스트에 VS Code Copilot과 Microsoft 365 Copilot 포함 | [버전 연표](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html), [Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol) |
| Salesforce | 2026-04 Headless 360 플랫폼이 고객과 에이전트 상호작용을 MCP로 라우팅. 2026-05 말 기준 누적 450만 건 MCP 호출 처리 보고 | [Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol) (The Register 2026-05-28 인용) |
| MCP Apps 출시 파트너 | Amplitude, Asana, Box, Canva, Figma, monday.com, Salesforce, Slack 등. 호스트는 Claude, ChatGPT, VS Code, Cursor, Goose, Postman 등 | [MCP 공식 블로그](https://blog.modelcontextprotocol.io/tags/apps/) |

### 2.6 기업 현장에서는 얼마나 쓰나

Stacklok이 AAIF와 함께 2026년 7월 미국과 영국 기업의 시니어 엔지니어 100명을 조사한 결과임.

| 항목 | 값 |
|------|-----|
| MCP를 "어떤 형태로든 운영 중"이라고 답한 비율 | 41% |
| 실제 사용 중 실험이나 로컬 개발 단계인 비율 | 86% |
| 거버넌스가 갖춰진 전사 운영 환경 비율 | 5% |
| 운영 중이지만 통제 없이 돌리는 비율 | 9% |

해석: "운영 중"이라는 답과 "통제된 운영"은 전혀 다른 뜻임.  
조사 결과를 분석한 Forkast는 보안이 도입을 막는 가장 큰 제약이라고 짚음.  
표본이 100명이라 산업 전체로 일반화하기에는 작다는 점을 유의해야 함.

출처: [Forkast 분석 기사](https://forkast.news/mcp-locked-in-its-architecture-today-now-the-hard-part-enterprise-adoption-at-scale/),  
[Stacklok 금융권 보고서 PDF](https://stacklok.com/wp-content/uploads/2026/01/State-of-MCP-in-Financial-Services-2026_FINAL.pdf)

### 2.7 보안: 가장 많이 다뤄지는 주제

**공신력 있는 기관의 문서**

| 기관 | 문서 | 핵심 내용 |
|------|------|-----------|
| 미국 NSA(국가안보국) | Cybersecurity Information Sheet "MCP: Security Design Considerations for AI-Driven Automation", 2026년 5월 Ver 1.0 | "MCP의 빠른 확산이 보안 모델의 발전을 앞질렀다"고 평가. 약한 접근 통제, 승인 절차 미흡, 토큰 수명 관리 공백, 감사 로그 부족을 지적하고 제로 트러스트와 최소 권한 적용을 권고 |
| OWASP | MCP Top 10(베타) | MCP01 토큰 관리 부실과 비밀값 노출, MCP02 권한 범위 확대, MCP03 도구 오염(Tool Poisoning), MCP04 공급망 공격, MCP05 명령 주입, MCP06 프롬프트 주입, MCP07 인증과 인가 부족, MCP08 감사와 원격 측정 부재, MCP09 섀도 MCP 서버, MCP10 컨텍스트 주입과 과다 공유 |
| Cloud Security Alliance(CSA) | 연구 노트 "MCP Attack Surface: Tool Poisoning and IDE Auto-Execution", 2026-07-01 | 도구 설명 필드가 검증 없는 공격 표면임. MCPTox 벤치마크에서 20개 LLM 대상 도구 오염 공격 평균 성공률 36.5%, 최고 72.8%. Cursor, Claude Code, Gemini CLI, GitHub Copilot, Amazon Q가 프로젝트에 정의된 MCP 서버를 개발자 권한으로 자동 실행한 취약점(예: Amazon Q의 CVE-2026-12957, CVE-2026-12958) |
| MCP 공식 사양 | Security Best Practices | 프록시 서버의 "혼동된 대리인(confused deputy)" 위험을 설명하고, 토큰 통과 전달(token passthrough)을 금지 |

출처: [NSA 문서 PDF](https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf),  
[Executive Gov 보도](https://executivegov.com/articles/nsa-model-context-protocol-deployment),  
[OWASP MCP Top 10](https://owasp.org/www-project-mcp-top-10/),  
[CSA 연구 노트](https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-tool-poisoning-auto-execution-20260701/),  
[Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol)

**사양 쪽의 대응**  
- 2025-06-18: 보안 모범사례 페이지 신설, MCP 서버를 OAuth 리소스 서버로 분류  
- 2025-11-25: 점진적 권한 동의, OpenID Connect 탐색, Client ID Metadata Documents 권장  
- 2026-07-28: 발급자(issuer) 검증 의무화, 자격 증명을 발급자별로 분리 보관, 동적 클라이언트 등록(DCR) 폐기 예고  
- 2026-08 로드맵: 에이전트 신원(Workload Identity Federation, DPoP, 토큰 교환)을 우선 영역으로 지정  

### 2.8 한국의 움직임

| 시점 | 사건 | 출처 |
|------|------|------|
| 2025-08-13 | 카카오가 국내 첫 개방형 MCP 플랫폼 PlayMCP 베타 공개. 카카오 계정만 있으면 MCP 서버 등록과 테스트 가능 | [카카오 보도자료](https://www.kakaocorp.com/page/detail/11674?lang=KOR) |
| 2026-05-01 | PlayMCP에 외부 MCP 서버 약 200개 등록. 오픈소스 에이전트 OpenClaw 연동 지원, 10분 유효 원타임 토큰 적용 | [카카오 보도자료](https://www.kakaocorp.com/page/detail/12012?lang=KOR) |
| 2026-08-13 | AAIF가 MCP Dev Summit 서울을 열고 아시아태평양 확산을 강조. ETRI 가입 | [Linux Foundation 보도자료](https://www.linuxfoundation.org/press/agentic-ai-foundation-welcomes-57-new-members-gaining-major-financial-services-players-and-apac-leaders) |

네이버, 삼성SDS, LG CNS의 MCP 서버 공개 사례는 이번 조사에서 공식 출처로 확인하지 못함.

---

## 3. Fact 기반 트렌드 7가지

### 3.1 "세션 있는 프로토콜"에서 "보통의 HTTP 워크로드"로

2026-07-28 개정으로 세션 ID와 초기화 핸드셰이크가 사라지고 매 요청이 버전과 능력을 스스로 실어 나름.  
공식 로드맵은 "원격 MCP 서버가 이제 다른 HTTP 워크로드와 다를 바 없다"고 표현함.  
결과적으로 기존 API 게이트웨이, 로드밸런서, 서버리스 인프라에 그대로 올릴 수 있게 됨.  
출처: [2026-07-28 변경 내역](https://modelcontextprotocol.io/specification/2026-07-28/changelog), [로드맵](https://blog.modelcontextprotocol.io/posts/mcp-roadmap/)

### 3.2 코어는 작게, 기능은 "확장(extension)"으로

Tasks(긴 작업 추적)는 코어에서 빠져 공식 확장이 됐고, MCP Apps(대화 안 인터랙티브 UI)와  
Enterprise Managed Authorization(기업 관리형 인가)이 같은 확장 틀 안에 들어감.  
Roots, Sampling, Logging은 폐기 예고됨. "모두가 쓰는 것만 코어에 남긴다"는 방향임.  
출처: [2026-07-28 공식 발표 글](https://blog.modelcontextprotocol.io/posts/2026-07-28/)

### 3.3 인증의 초점이 "사람 로그인"에서 "에이전트 신원"으로

지금 MCP 인가는 사람이 브라우저에서 승인하는 흐름이 기본임.  
로드맵은 "호출자가 점점 더 사용자 없이 도는 클라우드 워크로드나 하위 에이전트"라며,  
붙여넣은 API 키와 장기 토큰 대신 표준 기반 에이전트 신원과 위임을 우선 과제로 둠.  
출처: [로드맵](https://blog.modelcontextprotocol.io/posts/mcp-roadmap/)

### 3.4 컨텍스트 비용 절감이 설계 이슈로 부상

도구가 많아지면 모델이 질문을 받기도 전에 도구 설명으로 컨텍스트를 다 써버림.  
Anthropic은 MCP 도구를 코드 파일로 노출하고 필요한 것만 읽게 하는 "코드 실행" 방식으로  
한 예시에서 150,000 토큰을 2,000 토큰으로 줄였다고 밝힘(98.7% 절감).  
공식 로드맵도 "작은 진입점을 두고 대화가 좁혀질수록 카탈로그를 더 드러내는 점진적 탐색"을 시작한다고 밝힘.  
출처: [Anthropic 엔지니어링 글](https://www.anthropic.com/engineering/code-execution-with-mcp), [로드맵](https://blog.modelcontextprotocol.io/posts/mcp-roadmap/)

### 3.5 보안이 도입 속도를 결정하는 병목

NSA, OWASP, CSA가 2026년 상반기에 잇따라 문서를 냈고,  
설문에서도 운영 중이라는 41% 가운데 통제된 전사 운영은 5%에 그침.  
도구 오염과 IDE 자동 실행이 실제 CVE로 이어져 "규격이 아니라 구현과 운영이 문제"라는 인식이 자리 잡음.  
출처: 2.6절과 2.7절 참조

### 3.6 소유권 중립화 이후 기업 회원이 빠르게 늘어남

AAIF는 설립 8개월 만에 247개 조직으로 늘었고, 금융권(Visa, Wells Fargo)과 아시아(Alibaba, ETRI)가 합류함.  
AAIF가 추적하는 오픈소스 에이전트 프로젝트는 116개에 이름.  
출처: [Linux Foundation 보도자료](https://www.linuxfoundation.org/press/agentic-ai-foundation-welcomes-57-new-members-gaining-major-financial-services-players-and-apac-leaders)

### 3.7 "내 PC에서 돌리는 서버"에서 "클라우드가 관리하는 원격 서버"로

Google Cloud는 지원 제품을 켜면 원격 MCP 엔드포인트를 기본 제공하고 IAM으로 통제함.  
AWS Bedrock AgentCore는 상태 없는 코어를 바로 지원함. Salesforce는 고객 상호작용을 MCP로 라우팅함.  
개발자가 stdio로 띄우던 서버가 벤더 관리형 엔드포인트로 옮겨가는 흐름임.  
출처: 2.5절 참조

---

## 4. Opinion: 우리 팀 아키텍처 설계에 주는 시사점

아래는 조사 결과를 바탕으로 한 클로니의 의견임.

- **새로 만드는 MCP 서버는 2026-07-28 사양을 기준으로 설계함.**  
  세션 ID와 initialize에 기대는 코드는 12개월 안에 폐기 대상이 됨.  
  상태가 필요하면 서버가 발급하는 핸들을 도구 인자로 넘기는 방식으로 바꿔야 함  
- **도구 수를 늘리기보다 "진입 도구 소수 + 점진적 공개"로 설계함.**  
  Anthropic 사례와 공식 로드맵이 같은 방향을 가리킴. 커넥니의 도구 명세 단계에서 적용할 사항임  
- **"운영 중"의 기준을 거버넌스로 정의함.**  
  설문의 41%와 5%의 차이가 보여주듯, 인증과 감사 로그와 권한 범위가 없으면 운영이 아니라 실험임.  
  옵스니의 배포 체크리스트에 OWASP MCP Top 10 항목을 넣는 것을 권함  
- **IDE 자동 실행 경로를 위협 모델에 포함함.**  
  저장소에 커밋된 MCP 설정 파일 하나로 팀 전체가 감염될 수 있음.  
  프로젝트 설정의 MCP 서버는 리뷰 대상에 포함하고, 도구 설명 변경(rug pull)을 감지하는 절차를 둠  
- **A2A와 MCP는 경쟁이 아니라 층이 다름.**  
  MCP는 에이전트와 도구, A2A는 에이전트와 에이전트 사이 규격임.  
  단일 에이전트로 될 일에 A2A를 끌어들이지 않는 절제가 필요함(단일/멀티 판정 원칙과 같음)  
- **한국 서비스 연동은 카카오 PlayMCP가 가장 현실적인 출발점임.**  
  카카오톡, 캘린더, 지도, 멜론이 MCP 서버로 열려 있어 실습과 데모에 바로 쓸 수 있음

---

## 5. 출처 목록

**공식 사양과 재단**  
- [MCP 2026-07-28 사양 변경 내역](https://modelcontextprotocol.io/specification/2026-07-28/changelog)  
- [MCP 2025-11-25 사양 변경 내역](https://modelcontextprotocol.io/specification/2025-11-25/changelog)  
- [MCP 공식 블로그: The 2026-07-28 Specification](https://blog.modelcontextprotocol.io/posts/2026-07-28/)  
- [MCP 공식 블로그: The New MCP Roadmap (2026-08-22)](https://blog.modelcontextprotocol.io/posts/mcp-roadmap/)  
- [MCP 공식 블로그: MCP Apps 태그](https://blog.modelcontextprotocol.io/tags/apps/)  
- [Linux Foundation: AAIF 설립 (2025-12-09)](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)  
- [Linux Foundation: AAIF 57개 회원 추가 (2026-08-13)](https://www.linuxfoundation.org/press/agentic-ai-foundation-welcomes-57-new-members-gaining-major-financial-services-players-and-apac-leaders)

**벤더 공식 자료**  
- [Anthropic: Introducing the Model Context Protocol (2024-11-25)](https://www.anthropic.com/news/model-context-protocol)  
- [Anthropic: Code execution with MCP (2025-11-04)](https://www.anthropic.com/engineering/code-execution-with-mcp)  
- [Google Cloud: MCP servers release notes](https://docs.cloud.google.com/mcp/release-notes)  
- [카카오: PlayMCP 베타 오픈 (2025-08-13)](https://www.kakaocorp.com/page/detail/11674?lang=KOR)  
- [카카오: PlayMCP OpenClaw 연동 (2026-05-01)](https://www.kakaocorp.com/page/detail/12012?lang=KOR)

**보안 기관**  
- [NSA: MCP Security Design Considerations (PDF, 2026-05)](https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf)  
- [Executive Gov: NSA MCP 지침 보도](https://executivegov.com/articles/nsa-model-context-protocol-deployment)  
- [OWASP MCP Top 10](https://owasp.org/www-project-mcp-top-10/)  
- [CSA: MCP Attack Surface 연구 노트 (2026-07-01)](https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-tool-poisoning-auto-execution-20260701/)

**조사와 실측**  
- [Forkast: Stacklok과 AAIF 설문 분석 (2026-07-28)](https://forkast.news/mcp-locked-in-its-architecture-today-now-the-hard-part-enterprise-adoption-at-scale/)  
- [npm 다운로드 API: @modelcontextprotocol/sdk](https://api.npmjs.org/downloads/point/last-month/@modelcontextprotocol/sdk)  
- [pypistats API: mcp](https://pypistats.org/api/packages/mcp/recent)  
- [Wikipedia: Model Context Protocol](https://en.wikipedia.org/wiki/Model_Context_Protocol)  
- [MCP 사양 버전 연표 (Hidekazu Konishi)](https://hidekazu-konishi.com/entry/mcp_specification_version_timeline.html)

---

## 6. 검증 메모

- 직접 원문을 내려받아 확인한 출처: MCP 사양 변경 내역 2종, MCP 공식 블로그 3종, Linux Foundation 보도자료 2종,  
  Anthropic 글 2종, Google Cloud 릴리스 노트, 카카오 보도자료 2종, OWASP, CSA, Forkast, Wikipedia  
- 패키지 저장소 수치는 2026-10-15에 npm과 pypistats 공개 API를 직접 호출한 값임  
- NSA 문서는 nsa.gov가 이 환경에서 접속 차단되어 원문을 열지 못함.  
  Wikipedia 각주와 Executive Gov 보도로 발행 사실과 핵심 문구를 교차 확인함  
- 공식 레지스트리 서버 총계는 API가 총계를 제공하지 않아 확인하지 못함. 집계 사이트 수치는 미검증으로 표기함  
- Gartner의 "API 게이트웨이 75%가 MCP 통합" 같은 수치는 벤더 블로그 인용만 있고 Gartner 원문을 찾지 못해 본문에서 제외함
