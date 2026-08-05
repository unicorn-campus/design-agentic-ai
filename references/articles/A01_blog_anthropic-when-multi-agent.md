# A01 Anthropic 기술 블로그 — 멀티에이전트 시스템: 언제 어떻게 쓸 것인가

## 1. 한눈에 보기

| 항목 | 내용 |
|------|------|
| 원문 URL | `https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them` — 2026-08-05 조회 기준 |
| 발행·갱신일 | 2026-01-23(본문 표기 `Date / January 23, 2026`). 갱신일 표기 없음. 본문 `Reading time 5 min` 병기 |
| 발행 주체 | Anthropic — `claude.com/blog`. 본문 말미에 집필자 `Cara Phillips` 및 기여자 4인 표기 |
| 자료 유형 | 벤더 자사 기술 블로그(실무 원칙 계열). 연작 1편이며 다음 편에서 다른 협업 패턴을 다룬다고 예고 |
| 확인 상태 | FULL |
| 확인 방법·시점 | `curl -sL`로 HTML 저장 후 `style`·`script`·`noscript`·`nav`·`footer` 제거 텍스트 추출로 본문 전문 판독, 2026-08-05 |
| 저장 파일 | `.temp/anthropic-when-multi-agent.html`(578,337바이트), `.temp/A01.txt`(24,614자) |
| 한 줄 요지 | 단일 에이전트로 먼저 시작하고, 컨텍스트 오염 · 병렬화 · 전문화 3가지 상황에서만 멀티로 나누며, 나눌 때는 업무 종류가 아니라 컨텍스트 경계로 쪼갬 |
| 1차 대응 | 4-4절 9단계 ③ 단일·멀티 판정, 산출물 ③④ |

## 2. 핵심 주장

- **C1** (단일 유지 조건) 잘 설계된 단일 에이전트에 알맞은 도구를 붙이면 기대보다 훨씬 많은 일을
  처리함. 멀티 구성은 에이전트마다 실패 지점 · 유지할 프롬프트 · 예상 밖 동작이 하나씩 늘어남.
  판정 문항: "지금 문제가 프롬프트 개선만으로는 해결되지 않는다는 증거가 있는가?"
  [§The case for starting with a single agent]
- **C2** (멀티로 나눌 조건) 멀티가 단일을 꾸준히 앞서는 상황은 3가지뿐임 — 컨텍스트 오염으로 성능이
  떨어질 때 · 과제를 병렬로 돌릴 수 있을 때 · 전문화가 도구 선택이나 과제 집중을 개선할 때.
  이 3가지 밖에서는 조율 비용이 이득을 넘어섬.
  판정 문항: "우리 과제가 이 3가지 중 최소 1개에 해당하는가?" [§What is a multi-agent system?]
- **C3** (멀티로 나눌 조건 · 세부) 컨텍스트 격리는 하위 과제가 많은 컨텍스트(1,000토큰 초과)를 만들지만
  그 정보 대부분이 본 과제와 무관할 때, 하위 과제가 무엇을 뽑아낼지 명확히 정의될 때 가장 효과적임.
  판정 문항: "이 하위 과제의 결과물 중 본 과제에 필요한 부분이 절반 미만인가?" [§Context protection]
- **C4** 나누는 기준은 `문제 중심`이 아니라 `컨텍스트 중심`이어야 함. 업무 종류로 나누면(기획 · 구현 ·
  테스트 · 검토) 핸드오프마다 맥락이 깎이는 전화게임(telephone game)이 발생함. 기능을 맡은 에이전트가
  그 기능의 테스트도 맡는 식으로, 컨텍스트를 진짜로 격리할 수 있을 때만 쪼갬 [§Context-centric decomposition]
- **C5** 여러 영역에서 꾸준히 통하는 패턴은 검증 서브에이전트(verification subagent)임. 검증은 본래
  넘겨야 할 맥락이 적어 전화게임을 비껴가기 때문임. 다만 조율 모델이 더 유능해지면 별도 검증 단계 없이
  직접 평가하는 방향으로 바뀌고 있음 [§The verification subagent pattern]

## 3. 원문 구조

| 원문 장·절(원문 표기) | 1줄 설명 |
|----------------------|----------|
| `What is a multi-agent system?` | 멀티에이전트를 「분리된 대화 컨텍스트를 가진 여러 LLM 인스턴스를 코드로 조율하는 구조」로 정의하고, 이 글의 범위를 `orchestrator-subagent` 패턴으로 한정함 |
| `The case for starting with a single agent` | 단일 에이전트의 여력과 멀티 도입 시 늘어나는 오버헤드(실패 지점 · 프롬프트 유지 · 예상 밖 동작)를 제시함 |
| `A decision framework for multi-agent systems` | 멀티가 값을 하는 경우를 3개 하위 절로 나눠 설명하는 판단 틀의 도입부. Claude Managed Agents 안내 포함 |
| `Context protection`(하위) | 컨텍스트 오염(context pollution) 개념과 고객지원 주문조회 예시. 단일 방식·멀티 방식 코드 비교 |
| `Parallelization`(하위) | 리드 에이전트가 질의를 갈래로 쪼개 서브에이전트를 동시 실행하는 구조. 이득은 속도가 아니라 철저함이라고 못박음 |
| `Specialization`(하위) | 도구 세트 · 시스템 프롬프트 · 도메인 지식 3방향의 전문화를 소개하는 도입부 |
| `Tool set specialization` · `System prompt specialization` · `Domain expertise specialization`(하위 3종) | 도구 과다·도메인 혼동·성능 저하 3신호, 상충하는 페르소나 분리, 도메인 맥락 분리. 다중 플랫폼 연동 예시와 코드 포함 |
| `Outgrowing single-agent architectures` | 단일 구조를 넘어섰다는 구체 신호 3가지(컨텍스트 한계 근접 · 도구 과다 · 병렬 가능 하위 과제)를 열거함 |
| `Context-centric decomposition` | 문제 중심 분해와 컨텍스트 중심 분해를 대비하고, 좋은 분해 경계 3종·나쁜 분해 경계 3종을 목록화함 |
| `The verification subagent pattern` | 검증 전담 서브에이전트 패턴의 정의와 이 패턴이 통하는 이유(맥락 전달량이 원래 적음) |
| `Implementating a multi-agent system`(하위) | 본 에이전트가 작업 완료 후 검증 서브에이전트를 띄우는 절차와 코드 예시 (원문 제목 오타 그대로 옮김) |
| `Multi-agent system applications`(하위) | 검증 서브에이전트가 효과적인 용도 4종 — 품질보증 · 컴플라이언스 점검 · 출력 검증 · 사실 검증 |
| `The early victory problem`(하위) | 검증자가 테스트 한두 개만 돌리고 통과 처리하는 실패 양상과 완화책 4종 |
| `Choosing between single-agent and multi-agent systems` | 도입 전 확인할 3항목과 「가장 단순한 방식으로 시작하라」는 결론. 관련 글 3건 안내 |
| `Acknowledgements` | 집필자·기여자 표기(본문 아님) |

## 4. 인용 가능 문장·수치

| ID | 인용·수치 | 5요소(값 / 표본 n / 시점 / 측정 주체 / 독립 여부) | 앵커 |
|----|----------|--------------------------------------------------|------|
| Q1 | 멀티에이전트 구현은 같은 과제 기준 단일 대비 토큰을 3 ~ 10배 더 씀. 원인은 컨텍스트 중복 · 조율 메시지 · 핸드오프용 요약 3가지 | 3 ~ 10배 / n=원문 미표기 / 2026-01-23 / Anthropic 자체 테스트(`In our testing`) / 벤더 자체 | [§The case for starting with a single agent] |
| Q2 | 컨텍스트 격리가 가장 효과적인 하위 과제의 컨텍스트 규모 기준은 1,000토큰 초과임 | 1,000토큰 / n=원문 미표기 / 2026-01-23 / Anthropic / 벤더 자체 | [§Context protection] |
| Q3 | 주문조회 예시에서 하위 에이전트가 요약해 넘기면 본 에이전트는 실제로 필요한 50 ~ 100토큰만 받음 | 50 ~ 100토큰 / n=예시 시나리오 1건(주문 #12345) / 2026-01-23 / Anthropic 문서 작성자 산정 / 벤더 자체(실측 아님) | [§Context protection] |
| Q4 | 도구가 너무 많으면(흔히 20개 이상) 에이전트가 알맞은 도구를 고르지 못함 | 20개 이상 / n=원문 미표기 / 2026-01-23 / Anthropic / 벤더 자체 | [§Tool set specialization] |
| Q5 | 단일 구조를 넘어섰다는 신호로 제시된 도구 개수는 15 ~ 20개 이상임 | 15 ~ 20개 이상 / n=원문 미표기 / 2026-01-23 / Anthropic / 벤더 자체 | [§Outgrowing single-agent architectures] |
| Q6 | 멀티 전환 전 대안으로 `Tool Search Tool` 사용을 권하며, 토큰 사용을 최대 85%까지 줄이면서 도구 선택 정확도를 개선할 수 있다고 적음 | 최대 85% / n=원문 미표기 / 2026-01-23 / Anthropic / 벤더 자체(자사 제품 전제) | [§Outgrowing single-agent architectures] |
| Q7 | 다중 플랫폼 연동 예시 — 플랫폼마다 관련 API 엔드포인트 10 ~ 15개, 도구 40개 이상을 가진 단일 에이전트는 플랫폼 간 유사 작업을 혼동함 | 10 ~ 15개 · 40개 이상 / n=예시 시나리오 1건(CRM·마케팅·메시징) / 2026-01-23 / Anthropic 문서 작성자 산정 / 벤더 자체(실측 아님) | [§Domain expertise specialization] |
| Q8 | 검증자의 조기 통과를 막는 필수 지시문 — "You MUST run the complete test suite before marking as passed." | 수치 아님 / n=원문 미표기 / 2026-01-23 / Anthropic / 벤더 자체 | [§The early victory problem] |

## 5. 커리큘럼 대응

| 교육 | 위치 | 용도 | 가져올 것 | 집필 메모 |
|------|------|------|-----------|-----------|
| KT | 4-4절 9단계 ③ 단일·멀티 판정, 산출물 ③④ (`recommend-materials.md` 1절 1번 행 지정값) | 판정 단계의 실무 원칙 1차 출처 | C1 · C2 · C3의 예/아니오 판정 문항 3개 | 체크리스트 3문항을 그대로 산출물 ③ 앞단 게이트로 배치함. A02는 호출 수·토큰 정량 계열이라 짝으로 붙임 |
| KT | Day 1 산출물 ④ 오케스트레이션 패턴 + 시퀀스 설계 | 패턴 선택의 기본값 제시 | `orchestrator-subagent` 패턴 정의와 「연작 1편의 범위 한정」 단서 | 원문이 스웜·능력 기반·메시지 버스를 이름만 들고 다루지 않음. 다른 패턴 설명은 A02·O'Reilly에서 가져와야 함 |
| KT | Day 1 산출물 ③ 에이전트 역할 계약서 | 역할을 어떤 축으로 쪼갤지의 판단 근거 | C4 컨텍스트 중심 분해 · 좋은 경계 3종 · 나쁜 경계 3종 | 실습에서 가장 자주 나오는 「기획·구현·검토 3분할」이 원문 기준으로는 나쁜 경계임. 대조 실습 소재로 씀 |
| KT | Day 1 산출물 ④ 시퀀스 · 산출물 ⑥ 가드레일·관측 | 검증 지점 설계 | C5 검증 서브에이전트 · Q8 명시적 지시문 · 조기 통과 완화책 4종 | 조기 통과 문제는 Day 2 품질 개선 시간과 직결됨. Q8은 프롬프트 문구로 바로 전용 가능 |
| KT | Day 1 이론 `MAS 아키텍처 패턴` 도입 | 멀티 도입 비용의 정량 근거 | Q1 토큰 3 ~ 10배 | 벤더 자체 테스트값이며 표본·측정 방법이 원문에 없음을 각주로 병기함 |
| 신한 | M5 `S5.2`(Day 8) — 각주 1행 | 이 과정이 단일 에이전트 구성을 유지하는 근거 | C1 · C2 — 3가지 상황 밖에서는 조율 비용이 이득을 넘어선다는 서술 | 정규 편성 없음. M5는 단일 LLM이 MCP 도구 2개를 고르는 구성이라 멀티 판정 자체가 대상 아님. 각주 1행으로만 씀 |

## 6. 집필 시 주의

- ※ 상충: 역할 분해 방식 — 반대 입장 LLM 기반 MAS 품질속성·패턴 분석(arXiv 2511.08475v2).
  본 자료는 컨텍스트 경계별 분해를 권고하나, 논문 94편 집계에서는 역할 기반 협업이 최다 채택 패턴임
  [§Context-centric decomposition]
- 수치의 성격 — 4절 Q1 ~ Q7은 벤치마크가 아님. 표본 수 · 과제 목록 · 측정 절차 · 재현 자료가 원문에
  전혀 없고, Q3 · Q7은 원문이 만든 예시 시나리오의 산정치임. 벤치마크처럼 인용하면 안 됨
- 자사 제품 전제 — Q6 `Tool Search Tool`과 `Claude Managed Agents`는 Anthropic 제품 사용을 전제한 권고임.
  제품 중립 슬라이드에 올릴 때는 「대안 존재」 각주가 필요함
- 유효기간 — 원문 스스로 "These thresholds will shift as models improve"라고 적음. 도구 20개 · 15 ~ 20개
  같은 임계값은 2026-01 시점의 실무 지침이며 고정 기준으로 쓰면 안 됨 [§Outgrowing single-agent architectures]
- 인접 자료 관계(`recommend-materials.md` 4-2절 기재 요지 범위) — Anthropic 「How we built our multi-agent
  research system」(2025-06)은 `Parallelization` 절이 직접 인용하는 선행 자료로 보완 관계임. Cognition
  「Don't Build Multi-Agents」(2025-06)는 트레이스 전체 공유 입장이라 「요약만 넘김」인 본 자료와 갈림.
  LangChain 「How and when to build multi-agent systems」(2025-06)은 읽기·쓰기 축이라 본 자료 3상황과 다름
- (추론) 판정 문항 3개를 산출물 ③ 이전의 게이트로 두는 편이 안전함. 근거 — 원문이 판정을 역할 설계보다
  앞선 단계로 서술하고, 조율 비용을 사후에 되돌리기 어렵다고 적음

## 7. 이해상충과 주장 강도

- **검증 가능한 주장** — 원문 안에서 조건과 대상이 특정되어 독자가 자기 환경에서 확인해볼 수 있는 서술
  - 멀티 구현이 같은 과제에서 토큰을 3 ~ 10배 쓰며, 원인이 컨텍스트 중복 · 조율 메시지 · 요약 3가지라는 서술
    [§The case for starting with a single agent]
  - 도구 20개 이상에서 선택 정확도가 떨어지고, 15 ~ 20개 이상이면 모델이 선택지 파악에 상당한 컨텍스트를
    쓴다는 서술 [§Tool set specialization] [§Outgrowing single-agent architectures]
  - 병렬화의 주된 이득이 속도가 아니라 철저함이며, 총 실행 시간은 오히려 길어지는 경우가 잦다는 서술
    [§Parallelization]
- **자사 경험 서술** — Anthropic 내부 관찰이며 외부 검증 자료가 원문에 제시되지 않은 서술
  - 여러 팀이 몇 달에 걸쳐 정교한 멀티 구조를 만들었으나 단일 에이전트의 프롬프트 개선으로 동등한 결과를
    얻었다는 관찰 [§What is a multi-agent system?]
  - 기획 · 실행 · 검토 · 반복을 각각 다른 에이전트에 맡긴 팀들이 핸드오프마다 맥락을 잃고 실행보다 조율에
    토큰을 더 썼다는 관찰 [§The case for starting with a single agent]
  - 기획자 · 구현자 · 테스터 · 검토자로 나눈 한 실험에서 서브에이전트들이 실제 작업보다 조율에 더 많은
    토큰을 썼다는 서술. 실험 조건·횟수는 원문 미표기 [§Context-centric decomposition]
- **의견·권고** — 규범적 조언이며 근거 데이터가 병기되지 않은 서술
  - 「가장 단순한 방식으로 시작하고 증거가 뒷받침할 때만 복잡도를 더하라」는 결론
    [§Choosing between single-agent and multi-agent systems]
  - 조율 모델이 더 유능해지면(예: Claude Opus 4.5) 별도 검증 단계 없이 직접 평가할 수 있다는 전망
    [§The verification subagent pattern]
  - 멀티 전환 전에 `Tool Search Tool`을 먼저 검토하라는 권고 [§Outgrowing single-agent architectures]
- **자사 제품 사용 전제 표시** — `Claude Managed Agents`의 멀티에이전트 오케스트레이션 안내
  [§A decision framework for multi-agent systems], `Tool Search Tool` 권고
  [§Outgrowing single-agent architectures], 코드 예시 전부가 `anthropic` SDK와 `claude-sonnet-4-5` 모델을
  사용함 [§Context protection] [§Parallelization]

## 8. 확인 범위와 미확인

- 조회일 2026-08-05. 확보 수단은 `curl -sL` 저장 HTML(578,337바이트) → 태그 제거 텍스트 추출(24,614자).
  Playwright MCP는 사용하지 않음(1차 시도인 `curl`이 본문 전문 확보에 성공함)
- 판독한 것 — 제목 · 요약문 · 발행일 · 읽는 시간 · 본문 7개 대절과 하위 절 9개 전부 · 코드 예시 4건 ·
  결론 · `Acknowledgements`까지 본문 전 범위
- 판독하지 못한 것은 본문이 아닌 요소(사이트 네비게이션 · 로고 · `Related posts` 4건 · 뉴스레터 구독 폼 ·
  쿠키 안내 · `Explore here` 배너)뿐이므로 FULL로 판정함
- 미확인(이미지) — `article` 안의 이미지 8개는 모두 장식용 SVG(`placeholder.svg` · `Object-*.svg` 등)이며
  `alt` 속성이 전부 비어 있음. `<figure>` 요소는 0개임. 즉 원문에 판독할 다이어그램·표·그래프가 없음
- 미확인(연작 후속편) — 원문이 예고한 「다음 글」의 다른 협업 패턴(스웜 · 능력 기반 · 메시지 버스) 내용은
  본 자료에 없으며 발행 여부도 확인하지 않음
- 미확인(코드 검증) — 본문 코드 예시 4건은 문법·동작을 실행 검증하지 않았고 서술 판독에만 사용함

## 9. 열린 질문

- 판정 문항 3개를 산출물 ③ 게이트로 강제할지, 참고 체크리스트로만 둘지 결정 필요. 강제하면 팀 대부분이
  단일 구성으로 수렴해 3일차 MAS 실습 소재가 얇아질 수 있음
- Q1 토큰 3 ~ 10배를 슬라이드에 올릴지 결정 필요. 올린다면 「Anthropic 자체 테스트 · 표본 미공개」 각주를
  같은 장에 둬야 함
- (추론) 「기획·구현·검토 3분할」을 실습에서 일부러 시켜보고 원문 기준으로 되짚는 편이 학습 효과가 큼.
  근거 — `recommend-materials.md` 5절 상충 2번이 「실습 판단 대상으로 드러내는 편」을 권고함
- 원문이 예고한 후속 연작을 교재 집필 전에 다시 조회할지 결정 필요(패턴 어휘가 A02와 어긋날 여지)
