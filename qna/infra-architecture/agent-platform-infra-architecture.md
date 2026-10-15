# Agent 개발 플랫폼의 인프라 아키텍처 및 고도화 전략

작성일: 2026-10-15  
작성: 클로니(Agentic AI 아키텍트 겸 오케스트레이터)  
구분 표기: **[Fact]**는 공식 문서와 1차 출처에서 직접 확인한 내용, **[Opinion]**은 그 위에 세운 팀의 판단임

---

## 1. 질문

> Agent 개발 플랫폼의 인프라 아키텍처는 어떻게 구성해야 하고, 어떤 순서로 고도화해야 하는가?

---

## 2. 한눈에 보는 답

- **[Fact]** 2025 ~ 2026년에 나온 주요 벤더의 에이전트 플랫폼(AWS Bedrock AgentCore, Google Agent Platform,  
  Anthropic Claude Managed Agents, LangChain LangSmith Deployment)은 이름만 다를 뿐 같은 구성 요소로 수렴함.  
  **실행 런타임(Harness), 세션과 메모리, 도구 게이트웨이, 신원(Identity), 샌드박스, 관측, 평가, 정책, 레지스트리**임
- **[Fact]** 공통된 핵심 설계 원칙은 세 가지임.  
  ① "뇌(모델과 루프)"와 "손(샌드박스와 도구)"과 "세션 기록"을 분리함.  
  ② 세션마다 격리된 실행 환경을 주고, 비밀값은 에이전트 코드가 닿을 수 없는 곳에 둠.  
  ③ 모든 단계를 표준 형식(OpenTelemetry)으로 기록하고, 그 기록으로 평가와 개선을 돌림
- **[Opinion]** 고도화는 "플랫폼을 먼저 다 짓는" 방식이 아니라 **4단계로 키움**.  
  단일 호출과 검색 → 고정 워크플로우 → 단일 에이전트와 관측 → 멀티 에이전트와 공용 플랫폼.  
  각 단계는 앞 단계의 측정값(비용, 품질, 실패율)이 근거가 될 때만 올라감

---

## 3. 용어 풀이 (먼저 읽기)

| 용어 | 쉬운 설명 |
|------|-----------|
| 하네스(Harness) | 모델을 반복 호출하고, 모델이 고른 도구를 실제로 실행해 주는 "운전석" 코드 |
| 런타임(Runtime) | 하네스와 에이전트 코드가 실제로 돌아가는 서버 환경 |
| 샌드박스(Sandbox) | 에이전트가 만든 코드나 명령을 안전하게 실행하는 격리된 방 |
| microVM | 컨테이너보다 더 강하게 격리된 아주 작은 가상 머신. 세션 하나에 하나씩 줌 |
| 세션(Session) | 한 작업 동안 오간 모든 이벤트(사용자 입력, 도구 호출, 결과)의 기록 |
| 체크포인트 | 작업 중간 상태를 저장해 두어, 장애가 나도 처음부터가 아니라 그 지점부터 다시 시작하는 장치 |
| 컨트롤 플레인 / 데이터 플레인 | 배포와 설정을 관리하는 쪽 / 실제 에이전트가 돌아가는 쪽. 둘을 나누면 데이터가 고객 망 밖으로 안 나감 |
| MCP(Model Context Protocol) | 에이전트가 외부 도구를 같은 방식으로 부르게 해 주는 표준 규약 |
| A2A(Agent2Agent) | 에이전트끼리 서로 작업을 주고받는 표준 규약 |
| 게이트웨이(Gateway) | 도구 호출이나 모델 호출이 모두 거쳐 가는 관문. 인증, 정책, 사용량 집계를 한곳에서 함 |
| OpenTelemetry(OTel) | 추적(trace), 지표(metric), 로그를 어느 모니터링 도구로든 보낼 수 있는 표준 형식 |
| TTFT | 요청을 받고 첫 글자가 나오기까지 걸리는 시간. 사용자가 가장 민감하게 느끼는 지연 |
| 레인보우 배포 | 새 버전과 옛 버전을 함께 띄워 두고, 진행 중인 작업을 끊지 않으면서 서서히 옮기는 배포 방식 |

---

## 4. [Fact] 주요 플랫폼이 공통으로 가진 구성 요소

### 4.1 벤더별 구성 요소 비교

| 구성 요소 | AWS Bedrock AgentCore | Google Agent Platform | Anthropic Managed Agents | LangChain LangSmith Deployment |
|-----------|----------------------|----------------------|-------------------------|-------------------------------|
| 실행 루프 | Harness(관리형 루프) | Agent Runtime + ADK | Harness(관리형, 교체 가능) | LangGraph Server |
| 런타임 격리 | Runtime, 세션별 microVM | Agent Runtime, 리비전과 트래픽 관리 | Environment(클라우드 또는 자체 호스팅 샌드박스) | 데이터 플레인(고객 VPC 가능) |
| 세션과 메모리 | Memory(단기, 장기, 공유) | Sessions, Memory Bank | Session(서버 측 이벤트 로그) | 체크포인터(Postgres, Redis) |
| 도구 연결 | Gateway(API와 Lambda를 MCP 도구화) | Agent Gateway, Skill Registry | MCP 서버, MCP 터널(연구 미리보기) | 도구 노드, MCP 연동 |
| 신원과 권한 | Identity(Cognito, Okta, Entra 연동) | Agent Identity, IAM 정책 | 세션 토큰과 OAuth 금고(vault) | 워크스페이스 권한 |
| 코드 실행 샌드박스 | Code Interpreter, Browser | Sandbox(코드 실행, 컴퓨터 사용) | 클라우드 샌드박스, 자체 호스팅 샌드박스 | (외부 연동) |
| 관측 | Observability(OTel 호환, CloudWatch) | 추적, 로깅, 모니터링, 토폴로지 그래프 | 이벤트 스트림(SSE) | LangSmith 추적 |
| 평가와 최적화 | Evaluations, Optimization(A/B) | 에이전트 평가 | (외부) | LangSmith 평가 |
| 정책과 거버넌스 | Policy(Cedar 호환 언어), Registry | Semantic Governance 정책, Agent Registry | 도메인 허용 목록 | (외부) |

출처: AWS AgentCore 개발자 가이드, Google Agent Platform 문서, Claude Managed Agents 문서, LangSmith 호스팅 문서  
(링크는 9절)

### 4.2 세 벤더가 같은 결론에 이른 지점

- **세션마다 격리된 실행 환경**  
  AWS: "각 세션은 파일시스템과 셸을 가진 격리된 microVM에서 실행"(Harness 설명)  
  Anthropic: 환경(Environment)은 "Anthropic 관리 클라우드 샌드박스 또는 자체 인프라의 자체 호스팅 샌드박스"
- **상태는 서버 측에 내구성 있게 보관**  
  Anthropic: "세션은 장시간 실행되고, 일시정지 후 깨끗하게 재개되며, 대화 기록과 샌드박스 상태와 출력물을 서버 측에 저장"  
  (이 때문에 Zero Data Retention 대상이 아님. 데이터 거버넌스 요건이 있으면 이 점을 먼저 확인해야 함)
- **도구는 게이트웨이를 거쳐 MCP로 표준화**  
  AWS Gateway: "API, Lambda 함수, 기존 서비스를 MCP 호환 도구로 변환"하고, Policy가 "실행 전 모든 도구 호출을 가로챔"
- **관측은 OpenTelemetry 형식**  
  AWS Observability: "표준 OpenTelemetry(OTEL) 호환 형식으로 내보낸 텔레메트리와 연동하는 모든 모니터링 스택"과 통합
- **프레임워크와 모델에 중립**  
  AWS Runtime: CrewAI, LangGraph, LlamaIndex, Google ADK, OpenAI Agents SDK, Strands와 MCP, A2A 지원  
  Google Agent Runtime: ADK, A2A, LangChain, LangGraph, AG2, LlamaIndex, 커스텀 지원

---

## 5. [Fact + Opinion] 참조 인프라 아키텍처

### 5.1 계층 구조 (Opinion: 4절의 공통 요소를 계층으로 정리한 것)

```
┌──────────────────────────────────────────────────────────────────────┐
│ L7 거버넌스     정책 엔진(도구 호출 사전 차단), 레지스트리(에이전트/도구/스킬 목록), 감사  │
├──────────────────────────────────────────────────────────────────────┤
│ L6 관측과 평가   OTel 추적(invoke_agent, execute_tool) → 평가셋 → 최적화(A/B)     │
├──────────────────────────────────────────────────────────────────────┤
│ L1 진입 계층     API 게이트웨이, 인증, SSE 스트리밍, 속도 제한, 세션 라우팅          │
├──────────────────────────────────────────────────────────────────────┤
│ L2 오케스트레이션 하네스(에이전트 루프), 워크플로우 그래프, 재시도/타임아웃/휴먼인루프  │
│      ("뇌")      상태 없는(stateless) 프로세스로 띄우고, 죽으면 세션 로그에서 재개     │
├───────────────────────┬──────────────────────────────────────────────┤
│ L3 세션과 메모리        │ L4 도구와 실행 ("손")                            │
│  세션 이벤트 로그(추가 전용)│  도구 게이트웨이(MCP) ─ 신원/OAuth 금고 ─ 정책 검사     │
│  체크포인트(Postgres 등) │  세션별 샌드박스(microVM/컨테이너), 브라우저, 코드 실행    │
│  단기/장기 메모리        │  A2A로 다른 에이전트 호출                           │
├───────────────────────┴──────────────────────────────────────────────┤
│ L5 모델과 지식 서빙  LLM 게이트웨이(모델 라우팅, 토큰 집계) ─ 추론 게이트웨이(GPU 풀)   │
│                   벡터/그래프/SQL 지식 저장소(RAG, GraphRAG, NL2SQL)           │
├──────────────────────────────────────────────────────────────────────┤
│ L0 플랫폼 기반     Kubernetes 또는 서버리스, 비밀값 저장소, 네트워크 격리(VPC), IaC   │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 계층별 설계 원칙과 근거

#### L2 오케스트레이션: "뇌"와 "손"과 "세션"을 분리함

- **[Fact]** Anthropic은 처음에 세션, 하네스, 샌드박스를 컨테이너 하나에 넣었음.  
  그 결과 "컨테이너가 죽으면 세션을 잃는" 애완동물(pet) 문제가 생겼고, 고객 VPC 연결도 망 피어링 외엔 길이 없었음
- **[Fact]** 해결책은 하네스를 컨테이너 밖으로 꺼내 샌드박스를 `execute(name, input) → string` 도구처럼 부르는 것.  
  하네스가 죽으면 `wake(sessionId)`로 새로 띄우고 세션 로그에서 마지막 이벤트부터 재개함
- **[Fact]** 이 분리로 샌드박스는 필요할 때만 만들어지게 되어, **TTFT p50이 약 60%, p95가 90% 이상 줄었음**
- **[Opinion]** 우리 설계에서도 LangGraph 노드(플로니)는 상태를 자기 프로세스에 두지 않고 체크포인터에 두며,  
  샌드박스와 도구 서버는 노드가 호출하는 별도 서비스로 둠. 노드 프로세스는 언제든 죽여도 되는 "가축(cattle)"이어야 함

#### L3 세션과 메모리: 세션 로그는 컨텍스트 창이 아님

- **[Fact]** Anthropic: 컨텍스트 압축(compaction)은 "무엇을 버릴지 되돌릴 수 없는 결정"이라 실패를 부를 수 있음.  
  그래서 세션 로그를 컨텍스트 창 밖에 내구성 있게 두고, `getEvents()`로 필요한 구간만 다시 읽게 함
- **[Fact]** Anthropic 리서치 시스템: "에이전트는 상태가 있고 오류가 누적됨 … 처음부터 다시 시작할 수 없어  
  오류가 난 지점에서 재개하는 시스템을 만들었음". 재시도 로직과 주기적 체크포인트를 함께 씀
- **[Fact]** LangGraph: 체크포인터가 상태 스냅샷을 저장함. 운영 환경은 Postgres 체크포인터가 권장됨.  
  Redis는 전체 기록 보관형(RedisSaver)과 최신만 보관형(ShallowRedisSaver)이 있음
- **[Opinion]** 세션 로그(추가 전용 이벤트)와 체크포인트(상태 스냅샷)는 다른 것임. 둘 다 두어야  
  "무슨 일이 있었나"와 "어디서 재개하나"를 각각 답할 수 있음

#### L4 도구와 실행: 비밀값은 샌드박스에서 닿을 수 없어야 함

- **[Fact]** Anthropic: 결합형 설계에서는 "Claude가 생성한 신뢰할 수 없는 코드가 자격증명과 같은 컨테이너에서 실행"되어  
  프롬프트 인젝션 한 번으로 토큰이 새었음. 구조적 해결은 **토큰이 샌드박스에서 절대 닿지 않게** 하는 것.  
  Git은 초기화 때 토큰을 로컬 리모트에 심고, MCP는 전용 프록시가 금고(vault)에서 자격증명을 꺼내 대신 호출함
- **[Fact]** MCP 보안 모범 사례(2025-06-18 사양)는 세 가지 공격을 명시함.  
  혼동된 대리인(confused deputy), 토큰 통과(token passthrough) 안티패턴, 세션 탈취(session hijacking).  
  MCP 프록시 서버는 클라이언트별 동의(consent)를 반드시 구현해야 함(MUST)
- **[Fact]** AWS AgentCore Policy는 Cedar 호환 언어로 규칙을 쓰고, Gateway와 연동해 "실행 전 모든 도구 호출을 가로챔"
- **[Opinion]** 커넥니의 원칙 "권한은 기본 거부, 되돌릴 수 없는 작업은 사람 승인"을 L4에서 코드로 강제함.  
  승인은 프롬프트가 아니라 게이트웨이 정책에 둠. 모델이 아무리 똑똑해져도 정책은 우회할 수 없어야 함

#### L5 모델 서빙: 모델 게이트웨이와 추론 게이트웨이를 나눔

- **[Fact]** Kubernetes Gateway API Inference Extension(2025-06 발표)은 `InferencePool`(GPU 풀 관리)과  
  `InferenceModel`(어떤 모델과 LoRA를 서빙할지)을 나눔. Envoy ext-proc로 "엔드포인트 선택기"를 끼워  
  KV 캐시와 요청 비용을 보고 파드를 고름
- **[Fact]** 같은 발표의 벤치마크(H100, Llama2 복제본 10개)에서 처리량은 기본 Service와 비슷했고,  
  **QPS 500 이상에서 p90 지연이 유의미하게 낮았음**
- **[Fact]** 이 확장은 LiteLLM, Solo AI Gateway, Apigee 같은 상위 AI 게이트웨이와 "함께 쓰는" 위치임.  
  Azure AI Landing Zone도 API Management를 "AI Gateway"로 두어 모델을 중앙에서 관리함
- **[Fact]** Anthropic 라우팅 패턴: "쉽고 흔한 질문은 작은 모델(Haiku)로, 어렵고 드문 질문은 큰 모델(Sonnet)로" 보냄
- **[Opinion]** 자체 GPU가 없으면 L5는 LLM 게이트웨이(모델 라우팅, 토큰 집계, 키 관리)만 두면 됨.  
  추론 게이트웨이는 자체 서빙(vLLM, KServe)을 시작할 때 추가함

#### L6 관측과 평가: 표준 스팬으로 기록해야 평가가 돌아감

- **[Fact]** OpenTelemetry GenAI 의미 규약은 에이전트 호출을 `invoke_agent` 스팬, 도구 호출을 `execute_tool` 스팬으로 정의함.  
  2026-05 기준 규약 상태는 아직 "Development"라 속성 이름이 바뀔 수 있음
- **[Fact]** Anthropic 리서치 시스템: "전체 운영 추적(tracing)을 넣고 나서야 에이전트가 왜 실패했는지 진단"할 수 있었음.  
  개별 대화 내용이 아니라 **결정 패턴과 상호작용 구조**를 모니터링해 프라이버시를 지킴
- **[Fact]** AWS Evaluations는 OTel 또는 OpenInference로 계측된 세션, 추적, 스팬을 평가하고,  
  Optimization은 그 추적을 바탕으로 프롬프트와 도구 설명을 고쳐 A/B 테스트로 검증함
- **[Fact]** Anthropic 평가 지침: 상태를 바꾸는 에이전트는 "턴별 과정"이 아니라 **최종 상태(end-state)**로 평가함.  
  긴 워크플로우는 상태 변화가 일어나야 할 체크포인트 단위로 쪼개 평가함
- **[Opinion]** 관측 없는 플랫폼은 고도화가 불가능함. L6은 2단계(아래 7절)부터 필수임

#### L1과 L0 배포: 진행 중인 에이전트를 끊지 않는 배포

- **[Fact]** Anthropic: "에이전트 시스템은 거의 쉬지 않고 도는 상태 있는 망"이라 배포 때 "어느 지점에 있을지 모름".  
  그래서 **레인보우 배포**로 옛 버전과 새 버전을 같이 띄우고 트래픽을 서서히 옮김
- **[Fact]** LangChain: Cloud(전부 LangChain), BYOC(컨트롤 플레인은 LangChain, 데이터 플레인은 고객 VPC),  
  Self-hosted(전부 고객)의 세 가지 호스팅. 데이터 플레인은 LangGraph 서버와 Postgres, Redis를 포함함.  
  독립 컨테이너 모드는 서버리스 환경을 권장하지 않음(0으로 축소 시 작업 손실 가능)
- **[Fact]** Anthropic 자체 호스팅 샌드박스: "오케스트레이션은 Anthropic 쪽에 두고 도구 실행만 고객 인프라로" 옮김.  
  워커는 Linux 호스트와 아웃바운드 HTTPS만 필요함. Cloudflare, Daytona, Modal이 플랫폼 가이드를 제공함
- **[Fact]** Azure AI Landing Zones: Bicep, Terraform, 포털로 제공되는 참조 구현.  
  AI Foundry 랜딩 존과 AI Gateway 랜딩 존을 따로 또는 함께 배포함
- **[Opinion]** 옵스니의 원칙 "되돌리는 방법이 없는 배포는 배포가 아님"을 에이전트에 맞게 바꾸면  
  "진행 중인 세션을 죽이는 배포는 배포가 아님"임. 세션 로그와 체크포인트가 L3에 있어야 이 배포가 가능함

### 5.3 [Fact] 보안 위험 목록: OWASP Top 10 for Agentic Applications 2026

2025-12-09에 OWASP GenAI Security Project가 100명 넘는 전문가와 함께 발표함. 계층별로 대응 위치를 붙임(Opinion).

| 코드 | 위험 | 주로 막는 계층 |
|------|------|----------------|
| ASI01 | 에이전트 목표 탈취(Goal Hijack) | L2 하네스 가드레일, L6 관측 |
| ASI02 | 도구 오용과 악용 | L4 게이트웨이 정책 |
| ASI03 | 신원과 권한 남용 | L4 신원(Identity), OAuth 금고 |
| ASI04 | 에이전트 공급망 취약점 | L7 레지스트리(승인된 도구만) |
| ASI05 | 예상치 못한 코드 실행(RCE) | L4 샌드박스 격리 |
| ASI06 | 메모리와 컨텍스트 오염 | L3 메모리 쓰기 권한 분리 |
| ASI07 | 안전하지 않은 에이전트 간 통신 | L4 A2A 인증, 서명 |
| ASI08 | 연쇄 실패(Cascading Failures) | L2 타임아웃, 루프 상한, 회로 차단 |
| ASI09 | 사람과 에이전트 간 신뢰 악용 | L1 UI 명시, 휴먼인루프 |
| ASI10 | 불량 에이전트(Rogue Agents) | L7 정책, L6 이상 탐지 |

정확한 명칭은 OWASP 공식 문서(9절 링크)를 기준으로 함. 위 표의 명칭은 2차 요약본과 교차 확인한 것임

### 5.4 [Fact] 검토 기준: AWS Well-Architected Generative AI Lens (2025-11-19 개정)

여섯 기둥별로 플랫폼을 점검하는 질문 목록임. 에이전트 관련 항목만 추림.

| 기둥 | 렌즈가 요구하는 것 |
|------|-------------------|
| 운영 우수성 | 일관된 출력 품질, 추적 가능성, 수명 주기 자동화 |
| 보안 | 엔드포인트 보호, 유해 출력과 **과도한 자율성(excessive agency)** 완화, 프롬프트 보호 |
| 신뢰성 | 처리량 대응, 구성 요소 간 통신 신뢰성, 우아한 실패 처리, 분산 작업 완료 검증 |
| 성능 효율 | 모델 성능 측정과 개선, 검색 성능 최적화 |
| 비용 최적화 | 비용 최적 모델 선택, 비용을 고려한 프롬프트, **벡터 저장소와 에이전트 워크플로우 최적화** |
| 지속 가능성 | 서버리스와 모델 효율 기법으로 자원 최소화 |

수명 주기는 범위 설정 → 모델 선택 → 맞춤화 → 개발 → 배포 → 지속 개선의 여섯 단계임

---

## 6. [Fact] 고도화 전략의 근거가 되는 숫자

| 근거 | 수치 | 출처 |
|------|------|------|
| 에이전트가 쓰는 토큰 | 채팅의 약 4배 | Anthropic 멀티 에이전트 리서치 |
| 멀티 에이전트가 쓰는 토큰 | 채팅의 약 15배 | Anthropic 멀티 에이전트 리서치 |
| 성능 분산 설명력 | 토큰 사용량 하나가 80% | Anthropic 멀티 에이전트 리서치 |
| 병렬화 효과 | 복잡한 조사 시간 최대 90% 단축 | Anthropic 멀티 에이전트 리서치 |
| 뇌와 손 분리 효과 | TTFT p50 약 60% 감소, p95 90% 이상 감소 | Anthropic Managed Agents 엔지니어링 |
| 취소 예측 | 2027년 말까지 에이전틱 AI 프로젝트 40% 이상 취소 | Gartner 2025-06 (언론 보도) |
| 취소 원인 | 비용 상승, 불명확한 가치, 부족한 위험 통제 | Gartner 2025-06 (언론 보도) |

**[Fact]** Anthropic "Building effective agents"의 첫 원칙: "가능한 가장 단순한 해법을 찾고 필요할 때만 복잡도를 높임.  
많은 응용에서는 검색과 예시를 붙인 단일 LLM 호출을 최적화하는 것으로 충분함"

---

## 7. [Opinion] 고도화 전략: 4단계 로드맵

**원칙: 단계를 올리는 근거는 앞 단계의 측정값임.** 측정 없이 다음 단계로 가면 Gartner가 말한 취소 원인 세 가지를 그대로 밟음

| 단계 | 목표 | 들어가는 인프라 | 올라가는 조건(측정값) |
|------|------|----------------|---------------------|
| 0단계 증강 LLM | 검색과 도구를 붙인 단일 호출 | L1 진입 API, L5 LLM 게이트웨이, 지식 저장소 1종 | 평가셋 정확도가 목표 미달이고 원인이 "한 번 호출로 못 푸는 과제"일 때 |
| 1단계 워크플로우 | 코드가 정한 경로(체이닝, 라우팅, 병렬) | L2 그래프 런타임, L3 체크포인터(Postgres), L6 OTel 추적 | 입력 유형이 다양해 경로를 미리 못 정할 때 |
| 2단계 단일 에이전트 | 모델이 도구와 순서를 고름 | L4 도구 게이트웨이(MCP)와 정책, 세션별 샌드박스, 휴먼인루프 | 한 컨텍스트 창을 넘는 과제, 병렬화 여지가 큰 과제가 확인될 때 |
| 3단계 멀티 에이전트와 플랫폼 | 오케스트레이터와 워커, 여러 팀 공용 | L7 레지스트리와 정책, A2A, 평가와 최적화 루프, 레인보우 배포 | 토큰 15배를 감당할 만큼 과제 가치가 높을 때만 |

### 7.1 단계별 핵심 작업

**0단계 증강 LLM**
- 진입 API와 LLM 게이트웨이부터 둠. 모델 키와 토큰 집계를 한곳에서 하는 것이 이후 모든 비용 통제의 시작임
- 평가셋을 먼저 만듦. 지식니의 원칙 "검색이 안 되면 모델을 바꿔도 소용없다"가 여기서 적용됨

**1단계 워크플로우**
- LangGraph 같은 그래프 런타임에 체크포인터(Postgres)를 붙임. 메모리 저장(MemorySaver)은 개발용으로만 씀
- 모든 노드에 타임아웃과 루프 상한을 둠(플로니 원칙). ASI08 연쇄 실패의 첫 방어선임
- OTel 추적을 이때부터 넣음. `invoke_agent`, `execute_tool` 스팬 이름을 처음부터 표준으로 맞추면  
  나중에 모니터링 도구를 바꿔도 계측 코드를 다시 쓰지 않음

**2단계 단일 에이전트**
- 도구는 전부 MCP 게이트웨이를 거치게 하고, 정책(기본 거부, 되돌릴 수 없는 작업은 승인)을 게이트웨이에 둠
- 샌드박스를 세션별로 격리하고, 비밀값은 샌드박스 밖 금고에 둠. 하네스는 샌드박스를 도구처럼 부름
- 긴 작업은 Anthropic 하네스 지침을 따름. 첫 세션이 진행 기록 파일과 기능 목록을 만들고,  
  이후 세션은 "한 번에 기능 하나"만 하고 깨끗한 상태로 끝냄. 완료 판정은 실제 끝단(E2E) 테스트로만 함
- 평가는 턴별이 아니라 최종 상태로 함

**3단계 멀티 에이전트와 플랫폼**
- 오케스트레이터와 워커 패턴. 워커 산출물은 오케스트레이터를 거치지 않고 파일 시스템이나 산출물 저장소에  
  직접 쓰고 참조만 돌려줌("전화 게임" 방지)
- 레지스트리로 승인된 에이전트, 도구, 스킬만 쓰게 함. 공급망(ASI04)과 불량 에이전트(ASI10) 대응임
- 배포는 레인보우 방식. 실행 중인 세션이 옛 버전에서 끝나도록 둘을 함께 띄움
- 관측 데이터로 평가 → 프롬프트와 도구 설명 최적화 → A/B 검증의 루프를 자동화함

### 7.2 호스팅 선택 기준

| 상황 | 권장 | 근거 |
|------|------|------|
| 빠른 시작, 데이터 민감도 낮음 | 관리형(AgentCore, Agent Platform, Managed Agents, LangSmith Cloud) | 인프라 관리 없이 격리와 관측이 포함됨 |
| 데이터는 내 망에, 운영은 벤더에 | BYOC 또는 하이브리드(컨트롤 플레인만 벤더) | LangSmith BYOC, Claude 자체 호스팅 샌드박스가 이 모델 |
| 규제로 전부 내 망에 | 셀프 호스팅(Kubernetes + Postgres + Redis + OTel) | 업그레이드와 확장을 직접 책임짐 |
| 자체 GPU 서빙 | 위 선택 + 추론 게이트웨이(Gateway API Inference Extension) | QPS 500 이상에서 p90 지연 개선 확인됨 |

**주의**: 관리형 세션 저장(예: Claude Managed Agents)은 Zero Data Retention 대상이 아닐 수 있음.  
데이터 보존 요건이 있으면 호스팅 선택 전에 이 항목을 먼저 확인함

### 7.3 우리 팀 역할 매핑

| 계층 | 담당 | 통과 기준(담당자의 성향에서 가져옴) |
|------|------|-----------------------------------|
| L2 오케스트레이션, L3 체크포인트 | 플로니 | 루프 상한과 타임아웃 없는 그래프는 통과 불가 |
| L4 도구 게이트웨이, 신원, 정책 | 커넥니 | 기본 거부, 되돌릴 수 없는 작업은 사람 승인 |
| L5 지식 저장소, 검색 품질 | 지식니 | 평가셋 없는 검색 경로는 통과 불가 |
| L5 멀티모달 파이프라인 | 모달니 | 지연 예산과 단가 산식 없는 설계는 통과 불가 |
| L1 진입 API, SSE, 화면 | 스택니 | 경로 함수 안에 흐름 판단이 들어가면 통과 불가 |
| L0 플랫폼, 배포, 비밀값 주입 | 옵스니 | 롤백 절차와 상태 확인 없는 매니페스트는 통과 불가 |
| 설명 문서, 용어사전 | 에듀니 | 설명이 코드보다 어려우면 실패 |
| 단계 판정, L6 평가 기준, L7 거버넌스 | 클로니 | 실행 증거 없는 완료 보고 불가 |

---

## 8. [Opinion] 흔한 실패와 피하는 법

| 실패 | 왜 생기나 | 피하는 법 |
|------|-----------|-----------|
| 플랫폼을 먼저 다 짓고 쓸 데가 없음 | 과제 가치보다 기술이 앞섬 | 0단계부터 측정값으로 올라감 |
| 컨테이너 하나에 전부 넣음 | 처음엔 단순해 보임 | 뇌, 손, 세션을 처음부터 다른 프로세스로 둠 |
| 비밀값이 샌드박스 환경변수에 있음 | 편의 | 금고와 프록시. 샌드박스에서 토큰이 안 보이게 함 |
| 배포하면 진행 중 세션이 죽음 | 상태가 프로세스 안에 있음 | 세션 로그와 체크포인트를 외부 저장소에, 레인보우 배포 |
| 왜 실패했는지 모름 | 추적이 없음 | 1단계부터 OTel 표준 스팬 |
| 멀티 에이전트가 토큰을 태움 | 15배 비용을 계산 안 함 | 과제 가치가 비용을 넘을 때만 3단계로 |
| 턴별 과정을 평가하다 지침 | 경로가 매번 다름 | 최종 상태와 체크포인트 단위 평가 |

---

## 9. 출처

### 1차 출처 (공식 문서, 직접 확인)
- Anthropic, Building effective agents (2024-12, 2026년 주석 포함):  
  https://www.anthropic.com/research/building-effective-agents
- Anthropic, How we built our multi-agent research system:  
  https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, Effective harnesses for long-running agents:  
  https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, Managed Agents 엔지니어링(뇌와 손과 세션 분리, TTFT 수치):  
  https://www.anthropic.com/engineering/managed-agents
- Anthropic, Demystifying evals for AI agents:  
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Claude Managed Agents 개요(베타, 핵심 개념 4가지, 데이터 보존 안내):  
  https://platform.claude.com/docs/en/managed-agents/overview
- Claude Managed Agents 자체 호스팅 샌드박스:  
  https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes
- AWS, Amazon Bedrock AgentCore 개요(서비스 13종):  
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html
- AWS, Well-Architected Generative AI Lens (2025-11-19):  
  https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html
- Google Cloud, Agent Platform 확장(Agent Runtime, Sessions, Memory Bank, Sandbox, Governance):  
  https://docs.cloud.google.com/agent-builder/agent-engine/overview
- LangChain, LangSmith 호스팅 비교(Cloud, BYOC, Self-hosted):  
  https://docs.langchain.com/langgraph-platform/deployment-options
- LangChain, 독립 컨테이너 배포(서버리스 비권장):  
  https://docs.langchain.com/langgraph-platform/standalone-container
- Kubernetes 블로그, Introducing Gateway API Inference Extension (2025-06-05):  
  https://kubernetes.io/blog/2025/06/05/introducing-gateway-api-inference-extension/
- Model Context Protocol, Security Best Practices (2025-06-18):  
  https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices
- OWASP GenAI Security Project, Top 10 for Agentic Applications 2026 (2025-12-09):  
  https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- OpenTelemetry, GenAI agent and framework spans 의미 규약:  
  https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
- Microsoft, Azure AI Landing Zones (참조 구현):  
  https://github.com/Azure/AI-Landing-Zones
- A2A Protocol 사양: https://a2a-protocol.org/latest/

### 2차 출처 (언론 보도, 요약본. 원문 확인이 어려워 교차 검증으로만 사용)
- Gartner 2025-06 예측 보도(40% 이상 취소, 원인 3가지, 에이전트 워싱):  
  https://www.newelectronics.co.uk/content/news/over-40-of-agentic-ai-projects-could-be-cancelled-by-2027
- OWASP ASI01 ~ ASI10 명칭 요약: https://www.giskard.ai/knowledge/owasp-top-10-for-agentic-application-2026
- OTel GenAI 규약 상태(Development) 요약:  
  https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions
- McKinsey QuantumBlack, Agentic AI mesh 5원칙(구성 가능성, 분산 지능, 계층 분리, 벤더 중립, 통제된 자율):  
  https://medium.com/quantumblack/how-we-enabled-agents-at-scale-in-the-enterprise-with-the-agentic-ai-mesh-baf4290daf48
- NIST CAISI AI Agent Standards Initiative(2026-02 출범), SP 800-53 통제 오버레이, 에이전트 신원 개념 문서 요약:  
  https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-initiative-governa/

### 확인하지 못한 것
- Gartner 보도자료 원문(봇 차단으로 접근 불가). 수치는 복수 언론 보도로 교차 확인함
- McKinsey 백서 원문(접근 불가). 5원칙은 QuantumBlack 공식 블로그와 요약본으로 확인함
- OWASP 공식 PDF 본문. 명칭은 2차 요약본 간 일치 여부로 확인함
