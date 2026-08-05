# A03 LangChain 공식 문서 — 에이전트의 컨텍스트 엔지니어링(Context engineering in agents)

## 1. 한눈에 보기

| 항목 | 내용 |
|------|------|
| 원문 URL | `https://docs.langchain.com/oss/python/langchain/context-engineering` — 2026-08-05 조회 기준 |
| 발행·갱신일 | 본문에 발행일·갱신일·버전 표기 없음. `recommend-materials.md` 1절 3번 행 기재 `2026-07`(서지 기준). 실제 조회일 2026-08-05 |
| 발행 주체 | LangChain, Inc. — 사이트 표기 `Docs by LangChain` |
| 자료 유형 | 벤더 공식 제품 가이드 문서. 서술보다 코드 예시 비중이 큼(파이썬 예시 약 20건) |
| 확인 상태 | FULL |
| 확인 방법·시점 | `curl -sL`로 HTML 저장 후 `style`·`script`·`nav`·`footer` 제거 텍스트 추출로 본문 전문 판독, 2026-08-05 |
| 저장 파일 | `.temp/langchain-context-eng.html`(1.5MB), `.temp/langchain-context-eng.txt`(35,322자) |
| 한 줄 요지 | 컨텍스트를 `Model Context` · `Tool Context` · `Life-cycle Context` 3층으로 가르고, 각 층이 `Runtime Context` · `State` · `Store` 3개 출처에서 재료를 끌어오는 구조로 설명함 |
| 1차 대응 | Day 1 이론 `컨텍스트 엔지니어링`, Day 2 멀티 LLM |

## 2. 핵심 주장

- **C1** `Model Context`(모델 컨텍스트) — 모델 호출 한 건에 무엇을 넣을지의 축.
  하위 항목은 `System Prompt` · `Messages` · `Tools` · `Model` · `Response Format` 5개이며 성격은 `Transient`임
  [§What you can control / §Model context, /oss/python/langchain/context-engineering 2026-08-05 조회 기준]
- **C2** `Tool Context`(도구 컨텍스트) — 도구가 무엇을 읽고 무엇을 쓸 수 있는지의 축.
  읽기(`Reads`)와 쓰기(`Writes`)로 갈리며 성격은 `Persistent`임
  [§What you can control / §Tool context, /oss/python/langchain/context-engineering 2026-08-05 조회 기준]
- **C3** `Life-cycle Context`(수명주기 컨텍스트) — 모델 호출과 도구 실행 **사이**에 무엇을 할지의 축.
  요약 · 가드레일 · 로깅이 예로 제시되며 성격은 `Persistent`임
  [§What you can control / §Life-cycle context, /oss/python/langchain/context-engineering 2026-08-05 조회 기준]
- **C4** `Transient context`(일시) 대 `Persistent context`(지속) — 바꾼 내용이 그 호출에서만 유효한지,
  상태에 남아 다음 턴까지 가는지를 가르는 축임
  [§Transient context / §Persistent context, /oss/python/langchain/context-engineering 2026-08-05 조회 기준]
- **C5** 데이터 출처 3종 — `Runtime Context`(정적 설정, 대화 단위) · `State`(단기 기억, 대화 단위) ·
  `Store`(장기 기억, 대화를 넘어 유지). 위 3개 층 모두 이 3개 출처에서 재료를 끌어옴
  [§Data sources, /oss/python/langchain/context-engineering 2026-08-05 조회 기준]

## 3. 원문 구조

| 원문 장·절(원문 표기) | 1줄 설명 |
|----------------------|----------|
| `Overview` | 에이전트가 실패하는 진짜 이유는 모델 성능이 아니라 잘못된 컨텍스트라는 문제 제기 [2026-08-05 조회 기준] |
| `Why do agents fail?` | 실패 원인을 2가지로 좁히고 컨텍스트 엔지니어링을 정의함 [2026-08-05 조회 기준] |
| `The agent loop` | 에이전트 반복 구조를 `Model call`과 `Tool execution` 2단계로 정의 [2026-08-05 조회 기준] |
| `What you can control` | 통제 대상 3층을 `Context Type / What You Control / Transient or Persistent` 3열 표로 제시 [2026-08-05 조회 기준] |
| `Transient context` · `Persistent context` | 일시 변경과 지속 변경의 차이를 각 1문단으로 구분 [2026-08-05 조회 기준] |
| `Data sources` | 출처 3종을 `Also Known As / Scope / Examples` 열로 정리한 표 [2026-08-05 조회 기준] |
| `How it works` | 위 통제를 실제로 가능하게 하는 장치가 미들웨어(middleware)임을 밝힘 [2026-08-05 조회 기준] |
| `Model context` | 모델 호출에 들어가는 5개 항목의 개요와 3개 출처와의 관계 [2026-08-05 조회 기준] |
| `System Prompt` · `Messages` | 지시문과 대화 이력을 출처 3종별 탭 코드로 각각 제시 [2026-08-05 조회 기준] |
| `Tools` (`Defining tools` · `Selecting tools`) | 도구 정의의 4요소와 상황별 도구 선별. 도구 과다 시 오류 증가를 지적 [2026-08-05 조회 기준] |
| `Model` | 대화 길이 · 사용자 선호 · 비용 등급에 따라 호출 모델을 바꾸는 방법 [2026-08-05 조회 기준] |
| `Response format` (`Defining formats` · `Selecting formats`) | 구조화 출력 스키마 정의와 상황별 스키마 교체 [2026-08-05 조회 기준] |
| `Tool context` (`Reads` · `Writes`) | 도구가 3개 출처를 읽고, `Command`로 상태에 쓰는 방법 [2026-08-05 조회 기준] |
| `Life-cycle context` (`Example: Summarization`) | 단계 사이에 끼어드는 처리. 내장 요약 미들웨어 예시 1건 [2026-08-05 조회 기준] |
| `Best practices` · `Related resources` | 권고 6개 항목과 연결 문서 5건(개념 개요 · 미들웨어 · 도구 · 메모리 · 에이전트) [2026-08-05 조회 기준] |

## 4. 인용 가능 문장·수치

| ID | 인용·수치 | 5요소(값 / 표본 n / 시점 / 측정 주체 / 독립 여부) | 앵커 |
|----|----------|--------------------------------------------------|------|
| Q1 | 정의문 — "Context engineering is providing the right information and tools in the right format so the LLM can accomplish a task." | 수치 아님 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [§Why do agents fail?, 2026-08-05 조회 기준] |
| Q2 | "This is the number one job of AI Engineers." — 컨텍스트 구성이 AI 엔지니어의 1순위 업무라는 주장 | 수치 아님 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [§Why do agents fail?, 2026-08-05 조회 기준] |
| Q3 | 실패 원인 2종 — ① 모델 자체의 능력 부족 ② 올바른 컨텍스트가 전달되지 않음. 원문은 후자가 더 잦다고 적음 | 2종 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체(빈도 근거 미제시) | [§Why do agents fail?, 2026-08-05 조회 기준] |
| Q4 | 에이전트 반복 구조 2단계 — `Model call` · `Tool execution`. 모델이 끝났다고 판단할 때까지 반복 | 2단계 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [§The agent loop, 2026-08-05 조회 기준] |
| Q5 | 통제 대상 3층과 지속성 — `Model Context`=`Transient`, `Tool Context`=`Persistent`, `Life-cycle Context`=`Persistent` | 3층 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [표: Context Type, 2026-08-05 조회 기준] |
| Q6 | 출처 3종과 범위 — `Runtime Context`·`State`는 대화 단위(conversation-scoped), `Store`는 대화를 넘어 유지(cross-conversation) | 3종 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [표: Data Source, 2026-08-05 조회 기준] |
| Q7 | 도구 개수 문제 — 도구가 너무 많으면 모델을 압도해 오류가 늘고, 너무 적으면 할 수 있는 일이 줄어듦 | 수치 아님(임계치 미제시) / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [§Selecting tools, 2026-08-05 조회 기준] |
| Q8 | 내장 요약 미들웨어 설정값 예시 — 발동 기준 `trigger={"tokens": 4000}`, 남기는 최근 메시지 `keep=("messages", 20)` | 4,000토큰 · 20건 / n=원문 코드 예시 1건 / 2026-08-05 조회 / LangChain 문서 예시값 / 벤더 자체(권장치·측정값 아님) | [§Example: Summarization, 2026-08-05 조회 기준] |

## 5. 커리큘럼 대응

| 교육 | 위치 | 용도 | 가져올 것 | 집필 메모 |
|------|------|------|-----------|-----------|
| KT | Day 1 이론 `컨텍스트 엔지니어링`, Day 2 멀티 LLM (`recommend-materials.md` 1절 3번 행 지정값) | 한 줄 정의의 1차 출처 | Q1 정의문 · Q3 실패 원인 2종 | 커리큘럼의 「순서·형태·분량」 정의와 원문 축이 1:1로 맞지 않음. 원문 축을 그대로 쓰고 커리큘럼 표현은 부연으로 내림 |
| KT | Day 1 이론 `컨텍스트 엔지니어링` 본론 | 구분 축 어휘 고정 | C1 ~ C5 — 3층 축 · 지속성 축 · 출처 3종 | 슬라이드 1장에 3층 × 3출처 격자로 그리면 이후 실습 지시문과 이름이 맞음 |
| KT | Day 2 실습 `멀티 LLM 적용` | 작업별 모델 교체 근거 | `Model` 절 — 대화 길이 · 사용자 선호 · 비용 등급 3가지 교체 기준 | 원문은 미들웨어로 모델을 바꾸는 방식임. 벤더 비교 실습과 붙이면 그대로 지시문이 됨 |
| KT | Day 2 실습 `RAG 구현과 컨텍스트 구성 조정` | 넣는 내용을 조정하는 지점 | `Messages` 절 — 일시 변경 대 지속 변경의 구분 | 검색 결과를 붙였다 뗐다 하려면 일시 변경 쪽이어야 함을 실습 전 못박음 |
| 신한 | 차시 `2-3` — DB 조회 결과를 LLM Context로 전달 | 조회 결과를 컨텍스트에 넣는 위치 | `Tool Context`의 `Reads` — 도구가 설정·상태를 읽어 조회하는 구조 | 이 차시는 도구 1개 수준이므로 3층 중 도구 층만 씀 |
| 신한 | 차시 `8-3` — 예측 스코어·상담 기록·정형 조회 결과를 하나의 Context로 결합 | 여러 출처를 하나로 합칠 때의 구분 | C5 출처 3종 · `Messages` 절의 결합 방식 | 무엇을 남기고 무엇을 버릴지의 기준을 출처 3종으로 나눠 적게 함 |
| 신한 | 차시 `9-3` — 추론에 필요한 Context 선별 및 구조화 | 선별·구조화의 기준 | `Response format` 절 · `Selecting tools` 절 | 선별은 도구·메시지 쪽, 구조화는 응답 형식 쪽으로 갈라 설명함 |

## 6. 집필 시 주의

- ※ 1차 출처 구분: `Checkpointer`(스레드 내 단기 저장) 대 `Store`(스레드 간 장기 저장) 구분 — **Persistence 문서**.
  이유 — 본 문서는 `Checkpointer` · 스레드 · 재개를 쓰지 않음(원문 전문 검색 `Checkpointer` 0건)
- 겹치는 부분의 경계 — `State`·`Store`의 이름과 용도는 본 문서로 충분하나, 저장소 구현과 재시작 시 소실은 넘김
- 정의문 번역 주의 — Q1은 「올바른 정보·도구를 올바른 형식으로 준다」는 3요소 문장임.
  커리큘럼의 「순서·형태·분량」과 낱말이 다르므로 두 표현을 섞어 쓰면 정의가 흔들림
- 원문에 없는 분류 체계 — `Context Rot`(Chroma, 2025-07)와 `Code execution with MCP`(Anthropic, 2025-11)의
  논의는 본 원문에 없음. 3층 축과 섞어 「원문 분류」로 제시하면 안 되며 출처를 분리 표기해야 함
- `context7` 교차 확인 — `create_agent` · `@dynamic_prompt` · `@wrap_model_call` · `ToolRuntime` ·
  `SummarizationMiddleware` · `request.override(...)` 모두 현행 API임 [context7 2026-08-05 조회]
- `context7` 차이 2건 — ① 도구 선별 예시에서 현행 문서는 `request.runtime`이 `None`일 때 최소 권한으로 막는
  방어 코드를 포함하나 원문 예시에는 없음 ② `SummarizationMiddleware` 인자가 계열별로 다름(본 원문은
  `model`·`trigger`·`keep`, Deep Agents 계열은 `backend`). 교재는 본 원문 표기를 쓰고 차이는 각주로 남김
- 모델 이름 주의 — 원문의 `gpt-5.5` 등은 예시 문자열임. 7절 코드는 **미검증 스케치**이며 실행 확인이 필요함
- ※ 상충 2건 — C4 계층·역할 분해 모두 본 원문이 다루지 않는 주제라 해당 없음
- 유효기간 — 버전·발행일 표기가 없으므로 인용은 2026-08-05 조회 시점으로만 유효함

## 7. API·표기 현행성

- **현재 진입점** — `from langchain.agents import create_agent`이며 본문 코드 예시 전부가 이 진입점을 씀.
  컨텍스트 조작은 `middleware=[...]` 인자로 붙임 [§System Prompt 이하 전 코드 예시, 2026-08-05 조회 기준]
- **폐기 예정 항목** — `AgentExecutor` · `initialize_agent` · deprecated 표기 모두 본문에 없음. `원문 미표기`
  [§전문 검색, /oss/python/langchain/context-engineering 2026-08-05 조회 기준]
- **조회 시점** — 2026-08-05. 버전 번호·갱신일 표기가 없어 조회일 병기가 필수임
  [§전문, /oss/python/langchain/context-engineering 2026-08-05 조회 기준]
- **기존 교재와 어긋나는 표기** — 커리큘럼 4-3절 `LangGraph 단독 사용`과 어긋남. 원문은 컨텍스트 조작을
  `StateGraph` 직접 조립이 아니라 미들웨어로 처리하며 `langgraph`에서 가져오는 것은 `Command`와
  `InMemoryStore`뿐임 [§Writes / §System Prompt 코드 예시, 2026-08-05 조회 기준]
- 데코레이터(decorator, 함수에 기능을 덧붙이는 표기) 3종 — `@dynamic_prompt`(지시문 교체) ·
  `@wrap_model_call`(호출 전후 가로채기) · `@tool`(도구 정의) [§System Prompt / §Messages, 2026-08-05 조회 기준]
- 내장 미들웨어 표기 — 아래는 원문 코드를 줄인 **미검증 스케치**임 [§Example: Summarization, 2026-08-05 조회 기준]

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[SummarizationMiddleware(
        model="gpt-5.4-mini",
        trigger={"tokens": 4000},
        keep=("messages", 20),
    )],
)
```

## 8. 확인 범위와 미확인

- 조회일 2026-08-05. 확보 수단은 `curl -sL` 저장 HTML(1.5MB) → 텍스트 추출(35,322자)
- 판독한 것 — 본문 전 범위. `Overview`부터 `Related resources`까지 모든 절과
  파이썬 코드 예시 약 20건 전문. 출처별 탭(`State` · `Store` · `Runtime Context`) 3종 모두 판독함
- 판독하지 못한 것은 본문이 아닌 요소(사이트 네비게이션 · 로고 · 검색창 · 쿠키 안내 · 피드백 위젯)뿐이므로
  FULL로 판정함
- 미확인(연결 문서, 경로 단위) — 본문이 가리키는 `Context conceptual overview` · `Middleware` · `Tools` ·
  `Memory` · `Agents` · `Dynamic tools` · `Dynamic model` · `State updates` 8건은 열지 않았음
- 미확인(실행) — 코드 예시를 실행하지 않았음. 시그니처는 `context7` 대조까지만 함
- 미확인(발행일) — 본문·HTML 메타 어디에도 발행일·갱신일이 없어 `2026-07`은 서지 기재값으로만 남김

## 9. 열린 질문

- 커리큘럼의 한 줄 정의(「순서·형태·분량」)를 원문 정의문으로 바꿀지 결정 필요.
  원문 3요소는 「올바른 정보 · 올바른 도구 · 올바른 형식」이며 「분량」이 명시 항목에 없음
- (추론) 3층 × 3출처 격자를 Day 1 슬라이드 1장으로 고정하는 편이 좋음.
  근거 — 원문 본문 대부분이 이 격자의 칸을 하나씩 채우는 구성이라 이후 절 이름과 그대로 맞음
- 신한카드 차시 `8-3` · `9-3`에서 `Life-cycle Context`(요약·가드레일)까지 넣을지 판단 필요.
  두 차시는 1시간 분량이라 3층을 모두 넣으면 넘칠 위험이 있음
- (추론) 요약 발동 기준값은 실습에서 직접 바꿔 보게 하는 편이 좋음.
  근거 — 원문의 4,000토큰·20건은 측정값이 아니라 예시값이며 케이스마다 달라짐
