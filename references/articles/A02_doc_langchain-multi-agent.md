# A02 LangChain 공식 문서 — 멀티에이전트(Multi-agent)

## 1. 한눈에 보기

| 항목 | 내용 |
|------|------|
| 원문 URL | `https://docs.langchain.com/oss/python/langchain/multi-agent` — 2026-08-05 조회 기준 |
| 발행·갱신일 | 본문에 발행일·갱신일·버전 표기 없음. `recommend-materials.md` 1절 2번 행 기재 `2025-12`(서지 기준). 실제 조회일 2026-08-05 |
| 발행 주체 | LangChain, Inc. — 사이트 표기 `Docs by LangChain` |
| 자료 유형 | 벤더 공식 제품 문서(개요 페이지). 하위에 패턴별 상세 페이지 5건을 둠 |
| 확인 상태 | FULL |
| 확인 방법·시점 | `curl -sL`로 HTML 저장 후 `style`·`script`·`nav`·`footer` 제거 텍스트 추출로 본문 전문 판독, 2026-08-05 |
| 저장 파일 | `.temp/langchain-multi-agent.html`(878KB), `.temp/langchain-multi-agent.txt`(9,139자) |
| 한 줄 요지 | 멀티에이전트 구성 방식을 `Subagents` · `Handoffs` · `Skills` · `Router` · `Custom workflow` 5종으로 제시하고, 모델 호출 수·토큰 수로 3개 시나리오를 비교해 선택 기준을 줌 |
| 1차 대응 | Day 1 이론 `MAS 패턴`, 산출물 ④ 선택 근거표 |

## 2. 핵심 주장

- **C1** 멀티에이전트가 늘 필요한 것은 아님. 원문은 도구와 프롬프트가 적절한 단일 에이전트로도
  비슷한 결과를 낼 수 있다고 먼저 못박음
  [§Multi-agent 도입부, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]
- **C2** 개발자가 「멀티에이전트가 필요하다」고 말할 때 실제로 원하는 것은 3가지로 정리됨 —
  `Context management`(컨텍스트 관리) · `Distributed development`(분산 개발) · `Parallelization`(병렬화)
  [§Why multi-agent?, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]
- **C3** 구성 방식(패턴) 명칭은 5종임 — `Subagents` · `Handoffs` · `Skills` · `Router` · `Custom workflow`.
  이 중 `Custom workflow`만 LangGraph로 직접 흐름을 짜는 방식이며 다른 패턴을 노드로 품을 수 있음
  [§Patterns, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]
- **C4** 패턴 선택 대조표의 축은 4개임 — `Distributed development` · `Parallelization` ·
  `Multi-hop`(여러 서브에이전트를 이어서 호출) · `Direct user interaction`(사용자와 직접 대화)
  [§Choosing a pattern, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]
- **C5** 멀티에이전트 설계의 중심은 컨텍스트 엔지니어링이며, 각 에이전트가 무엇을 보게 할지가 품질을 좌우함.
  내장 멀티에이전트 지원이 필요하면 상위 하네스인 `Deep Agents` 사용을 권함
  [§Why multi-agent? 끝문단 / 도입부, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]

## 3. 원문 구조

| 원문 장·절(원문 표기) | 1줄 설명 |
|----------------------|----------|
| `Multi-agent` (도입부) | 멀티에이전트의 정의와 「단일 에이전트로 충분할 수 있다」는 단서, `Deep Agents` 안내 [2026-08-05 조회 기준] |
| `Why multi-agent?` | 필요 사유 3종과 멀티에이전트가 특히 유효한 상황 3가지(도구 과다·전문 지식·순차 제약) [2026-08-05 조회 기준] |
| `Patterns` | 패턴 5종의 명칭과 동작 방식을 `Pattern / How it works` 2열 표로 제시 [2026-08-05 조회 기준] |
| `Choosing a pattern` | 4개 축에 별점(⭐) 표기로 패턴 4종을 비교. `Custom workflow`는 이 표에 없음 [2026-08-05 조회 기준] |
| `Visual overview` | 패턴 4종의 흐름 그림을 탭으로 전환해 보여줌. `LangSmith` 트레이싱 안내 포함 [2026-08-05 조회 기준] |
| `Performance comparison` | 비교 지표를 `Model calls`(모델 호출 수)와 `Tokens processed`(처리 토큰 수) 2개로 정의 [2026-08-05 조회 기준] |
| `One-shot request` | 단발 요청(`Buy coffee`) 시나리오의 호출 수 비교 [2026-08-05 조회 기준] |
| `Repeat request` | 같은 요청 2회 반복 시 상태 유지 여부가 호출 수에 미치는 차이 [2026-08-05 조회 기준] |
| `Multi-domain` | 3개 도메인 동시 질의 시 호출 수·토큰 수 비교 [2026-08-05 조회 기준] |
| `Summary` | 3개 시나리오를 한 표로 합치고 최적화 목표별 권장 패턴을 표로 정리 [2026-08-05 조회 기준] |
| 하위 `/multi-agent/subagents` | `Subagents` 상세 — 서브에이전트를 도구로 감싸는 구현 [context7 2026-08-05 조회] |
| 하위 `/multi-agent/handoffs` | `Handoffs` 상세 — `Command`로 제어권을 넘기는 구현 [context7 2026-08-05 조회] |
| 하위 `/multi-agent/skills` | `Skills` 상세 — 필요 시점에 프롬프트·지식을 불러오는 구현 [HTML 링크 목록, 2026-08-05 조회 기준] |
| 하위 `/multi-agent/router` | `Router` 상세 — 분류 후 병렬 위임·결과 합성 구현 [HTML 링크 목록, 2026-08-05 조회 기준] |
| 하위 `/multi-agent/custom-workflow` | `Custom workflow` 상세 — LangGraph로 직접 조립 [HTML 링크 목록, 2026-08-05 조회 기준] |

## 4. 인용 가능 문장·수치

| ID | 인용·수치 | 5요소(값 / 표본 n / 시점 / 측정 주체 / 독립 여부) | 앵커 |
|----|----------|--------------------------------------------------|------|
| Q1 | "not every complex task requires this approach" — 복잡한 과제라고 전부 멀티가 답은 아니라는 단서 | 수치 아님 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [§도입부, 2026-08-05 조회 기준] |
| Q2 | 멀티에이전트를 찾는 이유 3종 — `Context management` · `Distributed development` · `Parallelization` | 3종 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [§Why multi-agent?, 2026-08-05 조회 기준] |
| Q3 | 패턴 명칭 5종 — `Subagents` · `Handoffs` · `Skills` · `Router` · `Custom workflow` | 5종 / 원문 미표기 / 2026-08-05 조회 / LangChain / 벤더 자체 | [§Patterns, 2026-08-05 조회 기준] |
| Q4 | 단발 요청 모델 호출 수 — `Subagents` 4회, `Handoffs`·`Skills`·`Router` 각 3회 | 4·3·3·3회 / n=시나리오 예시 1건(`Buy coffee`) / 2026-08-05 조회 / LangChain 문서 작성자 산정 / 벤더 자체(실측 아님) | [§One-shot request, 2026-08-05 조회 기준] |
| Q5 | 반복 요청 2턴 누계 — `Subagents` 8회, `Handoffs`·`Skills` 각 5회, `Router` 6회 | 8·5·5·6회 / n=시나리오 예시 1건(같은 요청 2회) / 2026-08-05 조회 / LangChain 문서 작성자 산정 / 벤더 자체(실측 아님) | [§Repeat request, 2026-08-05 조회 기준] |
| Q6 | "Stateful patterns (Handoffs, Skills) save 40-50% of calls on repeat requests" | 40 ~ 50% / n=시나리오 예시 1건 / 2026-08-05 조회 / LangChain 문서 작성자 산정 / 벤더 자체(실측 아님) | [§Repeat request 요약문, 2026-08-05 조회 기준] |
| Q7 | 다중 도메인 — `Subagents` 5회·약 9K 토큰, `Handoffs` 7회 이상·약 14K 토큰 이상, `Skills` 3회·약 15K 토큰, `Router` 5회·약 9K 토큰 | 위 값 / n=시나리오 예시 1건(3개 언어 비교, 에이전트당 문서 약 2,000토큰) / 2026-08-05 조회 / LangChain 문서 작성자 산정 / 벤더 자체(실측 아님) | [§Multi-domain, 2026-08-05 조회 기준] |
| Q8 | 같은 다중 도메인 조건에서 `Subagents`가 `Skills` 대비 처리 토큰 67% 적음 — 조건은 컨텍스트 격리 | 67% / n=위 Q7과 동일 시나리오 1건 / 2026-08-05 조회 / LangChain 문서 작성자 산정 / 벤더 자체(실측 아님) | [§Multi-domain, 2026-08-05 조회 기준] |

## 5. 커리큘럼 대응

| 교육 | 위치 | 용도 | 가져올 것 | 집필 메모 |
|------|------|------|-----------|-----------|
| KT | Day 1 이론 `MAS 패턴`, 산출물 ④ 선택 근거표 (`recommend-materials.md` 1절 2번 행 지정값) | 패턴 어휘와 선택 기준의 1차 출처 | Q3 패턴 5종 명칭 · C4 선택 축 4개 | 패턴 이름은 원문 영문 표기 그대로 슬라이드에 올리고 괄호로만 우리말을 붙임 |
| KT | Day 1 산출물 ④ 선택 근거표 | 「왜 이 패턴인가」 칸의 정량 근거 | Q4 · Q5 · Q7 호출 수·토큰 수 3시나리오 | 벤더 자체 산정치이며 실측이 아님을 표 각주로 반드시 병기함 |
| KT | Day 1 이론 `MAS 패턴` 도입 | 「멀티로 나눌지」 판단 근거 | Q1 · Q2 — 단일로 충분할 수 있다는 단서와 필요 사유 3종 | 1절 1번 Anthropic 자료와 짝지어 두 관점(실무 원칙 대 정량)으로 배치함 |
| KT | Day 1 산출물 ④ 시퀀스 설계 | 반복 대화에서 상태 유지 여부의 영향 | Q6 — 상태를 유지하는 패턴이 반복 요청에서 호출을 아끼는 구조 | 마이데이터 케이스는 같은 사용자가 여러 번 묻는 흐름이라 이 항목이 직접 걸림 |
| 신한 | 해당 없음 | - | - | 대응 없음 |

## 6. 집필 시 주의

- 수치의 성격 — 4절 Q4 ~ Q8은 측정 실험 결과가 아니라 **원문이 만든 예시 시나리오의 산정치**임.
  표본·측정 방법·재현 절차가 원문에 없으므로 벤치마크처럼 인용하면 안 됨
- 비교 조건 병기 필수 — 다중 도메인 수치는 「에이전트당 문서 약 2,000토큰」·「모든 패턴이 병렬 도구 호출 가능」
  조건에서 나온 값임. 조건을 빼면 우열 단정이 됨
- `Choosing a pattern` 표에 `Custom workflow` 행이 없음. 「다섯 패턴을 비교했다」고 쓰면 원문과 어긋남
- 원문에 없는 패턴 명칭 — `supervisor` · `swarm` · `network` · 블랙보드형 · P2P · 계층형은 본 원문에 없음.
  출처는 `O'Reilly Radar`(2026-02)와 도서 「만들면서 배우는 AI 에이전트 개발 입문+실전」(2026-05)임.
  두 어휘 체계를 섞어 쓰면 산출물 ④ 리뷰가 성립하지 않음
- `context7` 교차 확인 — 하위 페이지가 `create_agent`·`@tool`·`Command`·`StateGraph`를 쓰며 어긋나는 표기 없음.
  본 정리본에 옮긴 코드는 없고, 하위 페이지 코드를 교재로 옮길 때는 **미검증 스케치** 표기가 필요함
- ※ 상충: 역할 분해 방식 — 반대 입장 `LLM 기반 MAS 품질속성·패턴 분석(논문 94편, 2025-11)`.
  해당 논문은 `역할 기반 협업`을 최다 패턴으로 집계하나 본 원문은 컨텍스트 경계로 나눔
- ※ 상충: C4에서 에이전트의 계층 — 본 원문은 C4 표기법을 다루지 않아 해당 없음
- 유효기간 — 인용은 2026-08-05 조회 시점으로만 유효함. 1절의 `2025-12`는 서지 기재값이며 본문 미확인임

## 7. API·표기 현행성

- **현재 진입점** — 개요 페이지 본문에는 코드블록이 없어 `원문 미표기`임. 하위 페이지
  `/multi-agent/subagents`와 `/multi-agent/handoffs`는 `from langchain.agents import create_agent`를
  진입점으로 사용함. 판정: 현행 진입점은 `create_agent`이며 LangChain 1.0(2025-10-22 GA) 이후 표준과 일치함
  [context7 `/websites/langchain_oss_python_langchain` 2026-08-05 조회]
- **폐기 예정 표기** — `AgentExecutor` · `initialize_agent` · deprecated 표기 모두 본문에 등장하지 않음.
  `원문 미표기` [§전문 검색, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]
- **조회 시점** — 2026-08-05. 본문·HTML 어디에도 버전 번호나 갱신일 표기가 없어 조회일 병기가 필수임
  [§전문, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]
- **기존 교재와 어긋나는 표기** — 커리큘럼 4-3절 `LangGraph 단독 사용`은 원문 기준으로
  `Custom workflow` 패턴 1종에 해당함. 원문은 LangGraph 직접 조립을 5종 중 하나로만 두고,
  나머지 4종은 `create_agent` 기반으로 서술함
  [§Patterns, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]
- 구성 방식 명칭은 원문 문자열 그대로임 — `Subagents` · `Handoffs` · `Skills` · `Router` ·
  `Custom workflow`. 번역·의역하지 않음 [§Patterns, 2026-08-05 조회 기준]
- 상위 하네스 표기 — `Deep Agents`는 LangChain 위에 얹는 상위 하네스로 소개되며
  `subagents` · `skills` · 계획 · 가상 파일시스템 · 컨텍스트 관리를 기본 제공한다고 적음
  [§도입부, /oss/python/langchain/multi-agent 2026-08-05 조회 기준]

## 8. 확인 범위와 미확인

- 조회일 2026-08-05. 확보 수단은 `curl -sL` 저장 HTML(878KB) → 텍스트 추출(9,139자)
- 판독한 것 — 개요 페이지 본문 전 범위. 도입부 · `Why multi-agent?` · `Patterns` ·
  `Choosing a pattern` · `Visual overview` 설명문 · `Performance comparison` 4개 하위 절 전부
- 판독하지 못한 것은 본문이 아닌 요소(사이트 네비게이션 · 로고 · 검색창 · 쿠키 안내 · 피드백 위젯)뿐이므로
  FULL로 판정함
- 미확인(하위 페이지, 경로 단위) — `/multi-agent/subagents` · `/multi-agent/handoffs` ·
  `/multi-agent/skills` · `/multi-agent/router` · `/multi-agent/custom-workflow` 5건의 본문 전문.
  경로 존재와 일부 코드 예시만 `context7`·HTML 링크 목록으로 확인했고 페이지를 열어 읽지는 않음
- 미확인(그림) — `Visual overview`와 성능 비교 절의 PNG 다이어그램 12장은 파일 경로만 확인했고
  이미지 내용은 판독하지 않음. 본문 설명문으로 대체 판독함
- 미확인(발행일) — 본문·HTML 메타 어디에도 발행일·갱신일이 없어 `2025-12`는 서지 기재값으로만 남김

## 9. 열린 질문

- 스타터 리포지토리 진입점 결정 — 원문은 LangGraph 직접 조립을 `Custom workflow` 1종으로만 두고 나머지 4종을
  `create_agent` 기반으로 서술함. `recommend-materials.md` 2절 8번 안건과 직결됨
- (추론) 실습에서 다룰 패턴을 2종으로 좁히는 편이 3일 편성에 맞음.
  근거 — 원문 표가 `Subagents`와 `Handoffs`를 서로 반대 성격으로 배치해 대조 실습이 성립함
- 성능 수치를 슬라이드에 올릴지 결정 필요. 올린다면 `실측 아님 · 예시 시나리오 산정` 각주를 같은 장에 둬야 함
- (추론) 산출물 ④ 근거표의 축은 원문 4축을 그대로 쓰는 편이 좋음.
  근거 — 팀마다 축이 다르면 아키니의 교차 검토가 성립하지 않음
