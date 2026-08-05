# A08 Ragas — 에이전트·도구 사용 지표(Agents or Tool Use Cases)

## 1. 한눈에 보기

| 항목 | 내용 |
|------|------|
| 원문 URL | `https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/` — 2026-08-05 조회 기준 |
| 발행·갱신일 | 2025-12-09 (본문 하단 표기 — 생성일·갱신일이 같은 날짜로 표기됨). 라이브러리 버전 표기는 없음 |
| 발행 주체 | Ragas 프로젝트(공식 문서 사이트 `docs.ragas.io`) — 지표 제작 주체 자체의 문서임 |
| 자료 유형 | 공식 문서의 개념·지표 설명 페이지(concepts / available_metrics). 논문·벤치마크가 아님 |
| 확인 상태 | FULL |
| 확인 방법·시점 | `curl -sL`로 저장한 원문 HTML에서 본문·목차·코드블록 26개를 추출해 판독, 2026-08-05 |
| 저장 파일 | `.temp/ragas-agent-metrics.html`, `.temp/a08.txt` |
| 한 줄 요지 | 에이전트가 **맞는 도구를 맞는 인자로 맞는 순서에 불렀는지**를 0 ~ 1 점수로 재는 지표 4종을 규정함 |
| 1차 대응 | 7-2절 (2) MAS 흐름 정확성 정량화 |

## 2. 핵심 주장

- **C1** 에이전트·도구 사용 품질은 한 개 점수가 아니라 여러 축으로 나누어 잰다고 밝힘.
  본 페이지에 등재된 지표는 `TopicAdherence` · `ToolCallAccuracy` · `ToolCallF1` ·
  `AgentGoalAccuracy`(참조 있음 / 없음) 4종임 [§Agentic or Tool use, /stable/ 2026-08-05 조회 기준]
- **C2** `ToolCallAccuracy`는 **도구 호출 순서와 인자 정확도를 함께** 보며, 최종 점수는
  인자 정확도에 순서 정렬 여부(1 또는 0)를 곱해 만듦. 순서가 어긋나면 인자가 다 맞아도 0점임
  [§Tool call Accuracy > Key Features, /stable/ 2026-08-05 조회 기준]
- **C3** `ToolCallF1`은 **순서를 보지 않는 무순서 매칭**이며 이름과 인자가 모두 맞는 호출만 정답으로 셈.
  누락(FN)과 초과 호출(FP)을 함께 잡아 부분 점수를 주므로 도입 초기 반복 개선에 쓴다고 밝힘
  [§Tool Call F1 > Formula, /stable/ 2026-08-05 조회 기준]
- **C4** `AgentGoalAccuracy`는 경로가 아니라 **결과**를 봄. 0 또는 1의 이진 지표이며,
  참조 있음(`WithReference`)은 기대 결과 문장과 비교하고 참조 없음은 대화에서 목표와 결과를 각각
  추론해 비교함 [§Agent Goal Accuracy, /stable/ 2026-08-05 조회 기준]
- **C5** 구 `ragas.metrics` 경로는 **v1.0에서 제거 예정**이라고 4개 지표 절 모두에 같은 문구로 고지되며,
  `ragas.metrics.collections`로 옮기라고 안내함. 구 경로는 `MultiTurnSample` 객체를 요구함
  [§Legacy API (Deprecated) × 4, /stable/ 2026-08-05 조회 기준]

## 3. 원문 구조

| 원문 장·절 | 1줄 설명 |
|-----------|----------|
| `Agentic or Tool use` (H1) | 에이전트 작업은 여러 축으로 평가된다는 도입 1문단 [/stable/ 2026-08-05 조회 기준] |
| `Topic Adherence` | 정해 둔 주제 범위를 벗어나지 않았는지 재는 지표. Precision · Recall · F1 수식 제시 [/stable/ 2026-08-05 조회 기준] |
| `Topic Adherence > Example` | `mode="precision"` 실행 예제와 출력 `0.6666666666444444` [/stable/ 2026-08-05 조회 기준] |
| `Tool call Accuracy` | 실제 호출과 기대 호출을 비교하는 지표 정의. 필요한 입력 2종을 명시 [/stable/ 2026-08-05 조회 기준] |
| `Tool call Accuracy > Key Features` | 엄격 순서(기본) · 유연 순서 2개 모드와 최종 점수 산식 [/stable/ 2026-08-05 조회 기준] |
| `Tool call Accuracy > Example: Basic Usage` | 신 경로 임포트 실행 예제와 출력 `1.0` [/stable/ 2026-08-05 조회 기준] |
| `Tool call Accuracy > Example: Flexible Order Mode` | `strict_order=False` 병렬 호출 예제 [/stable/ 2026-08-05 조회 기준] |
| `Tool call Accuracy > Scoring Examples` | 완전 일치 · 인자 부분 일치 · 순서 오류 3개 채점 사례 [/stable/ 2026-08-05 조회 기준] |
| `Tool call Accuracy > Use Cases` | 에이전트 검증 · 회귀 테스트 · 다단계 흐름 · 도구 선택 4개 용도 [/stable/ 2026-08-05 조회 기준] |
| `Tool call Accuracy > When to Use Different Metrics` | 3개 지표를 언제 쓰는지 비교한 2열 표 [/stable/ 2026-08-05 조회 기준] |
| `Tool Call F1 > Formula` | Precision · Recall · F1 수식과 무순서 매칭 명시 [/stable/ 2026-08-05 조회 기준] |
| `Tool Call F1 > How is it different from Topic Adherence?` | 두 지표가 재는 대상이 다름을 밝힌 비교 표 [/stable/ 2026-08-05 조회 기준] |
| `Tool Call F1 > Example: Extra Tool Called` | 초과 호출 1건 시 TP · FP · FN 분해와 F1 `0.67` [/stable/ 2026-08-05 조회 기준] |
| `Agent Goal Accuracy > With / Without Reference` | 결과 달성 여부를 0 · 1로 재는 두 변형의 실행 예제 [/stable/ 2026-08-05 조회 기준] |
| `Legacy API (Deprecated)` (4개 절 반복) | 구 `ragas.metrics` 경로의 v1.0 제거 예고와 `MultiTurnSample` 사용법 [/stable/ 2026-08-05 조회 기준] |

## 4. 인용 가능 문장·수치

| ID | 원문 인용·수치 | 5요소(값·n·시점·주체·독립여부) | 앵커 | 교재 사용처 |
|----|---------------|------------------------------|------|------------|
| Q1 | `ToolCallAccuracy`가 재는 것 — 기대 호출 대비 실제 호출의 **순서와 인자**를 함께 본다는 정의문(의역) | 값 해당없음 / n 원문 미표기 / 2026-08-05 조회 / Ragas / 벤더 자체 | [§Tool call Accuracy, /stable/ 2026-08-05 조회 기준] | KT 7-2절 (2) 슬라이드 정의 |
| Q2 | 최종 점수 산식 — "Final score = (argument accuracy) × (sequence aligned ? 1 : 0)" | 값 산식 / n 해당없음 / 2026-08-05 조회 / Ragas / 벤더 자체 | [§Key Features, /stable/ 2026-08-05 조회 기준] | KT 7-2절 (2) 채점 규칙 설명 |
| Q3 | 모드 2종 — 엄격 순서가 기본값이고 `strict_order=False`로 유연 순서 전환(의역) | 값 해당없음 / n 원문 미표기 / 2026-08-05 조회 / Ragas / 벤더 자체 | [§Key Features / §Flexible Order Mode, /stable/ 2026-08-05 조회 기준] | KT 실습지시문 모드 선택 |
| Q4 | 인자 부분 일치 채점 예 — 인자 3개 중 2개 일치 시 점수 `0.66` | 값 0.66(무단위) / n 인자 3개 1문항 / 2026-08-05 조회 / Ragas 문서 예시 / 벤더 자체 | [§Scoring Examples, /stable/ 2026-08-05 조회 기준] | KT 실습지시문 채점 예시 |
| Q5 | 순서 오류 채점 예 — 도구는 맞고 순서만 뒤바뀌면 점수 `0.0` | 값 0.0(무단위) / n 도구 2개 1문항 / 2026-08-05 조회 / Ragas 문서 예시 / 벤더 자체 | [§Scoring Examples, /stable/ 2026-08-05 조회 기준] | KT 7-2절 (2) 경로 오류 설명 |
| Q6 | 초과 호출 1건 시 분해 — TP=2, FP=1, FN=0, Precision `0.67`, Recall `1.0`, F1 `0.67` | 값 F1 0.67(무단위) / n 기대 호출 2건·실제 3건 1문항 / 2026-08-05 조회 / Ragas 문서 예시 / 벤더 자체 | [§Example: Extra Tool Called, /stable/ 2026-08-05 조회 기준] | KT 개선 1회차 진단 예시 |
| Q7 | 인자 불일치 시 — 도구 이름이 같아도 인자가 다르면 F1 `0.0`, "arguments must be exact" | 값 0.0(무단위) / n 호출 1건 / 2026-08-05 조회 / Ragas 문서 예시 / 벤더 자체 | [§Tool Call F1 > Scoring Examples, /stable/ 2026-08-05 조회 기준] | 신한 8-3 도구 선택 검증 |
| Q8 | `AgentGoalAccuracy`는 이진 지표이며 1은 목표 달성, 0은 미달성(의역) | 값 0 또는 1 / n 해당없음 / 2026-08-05 조회 / Ragas / 벤더 자체 | [§Agent Goal Accuracy, /stable/ 2026-08-05 조회 기준] | KT 7-2절 (2) 결과 축 보조 지표 |

## 5. 커리큘럼 대응

| 교육 | 위치 | 용도 | 가져올 것 | 집필 메모 |
|------|------|------|-----------|-----------|
| KT | Day 3 7-2절 (2) `MAS 흐름 정확성` 정량화 | 육안 확인을 점수로 대체 | Q1 · Q2 — `ToolCallAccuracy` 정의와 최종 점수 산식 | **신규 지표 행**. 기존 4지표는 `검색·응답 품질` 층, 본 지표는 `시스템 품질` 층으로 층이 다름 |
| KT | 7-2절 (1) 검색·응답 품질 RAGAS 4지표 | 층 구분 유지 | 가져올 것 없음(기존 유지) | **기존 지표 행**. Precision · Recall · Faithfulness · Relevance는 그대로 두고 교체하지 않음 |
| KT | Day 2 ~ 3 품질 측정 러너(9절 스타터 리포지토리) | 기준선 → 개선 → 최종 3회 측정 | Q4 · Q5 · Q6 — 채점 사례 3종을 러너 회귀 테스트 케이스로 씀 | **신규 지표 행**. 신규 도구 도입 없이 기존 러너에 지표 2개를 추가하는 방식임 |
| KT | Day 1 4-1절 이론 `RAGAS` 소개 | 지표 층 구조 설명 | C1 — 에이전트 품질을 여러 축으로 나눈다는 도입 문단 | 4지표만 소개하던 슬라이드에 `시스템 품질` 층 1장을 덧붙임 |
| 신한 | M5 S5.2 차시 8-3(Day 8) | 도구 선택 흐름 검증 | Q7 — 이름이 같아도 인자가 다르면 0점이라는 규칙 | **신규 지표 행**. 도구 2개(예측·문서검색)뿐이라 `ToolCallF1`의 무순서 매칭으로 충분함 |
| 신한 | M5 S5.2 기획자 과업 | 문항 3건 설계 근거 | Q3 — 순서 모드 선택 기준. 도구 2개 병렬이면 유연 순서 | 기획자가 만드는 "도구 선택이 갈리는 질문 3건"이 곧 기대 호출 시퀀스 3건이 됨 |
| 신한 | 6.6절 최종 심사 기준 `도구(MCP) 활용` | 심사 근거를 점수로 | Q1 — 맞는 도구를 골랐는지의 판정 기준 | 심사 배점에 쓸지는 미정. 배점 연동은 9절 열린 질문으로 올림 |

## 6. 집필 시 주의

- ※ 정정 필요: `ragas.metrics.ToolCallAccuracy` → `ragas.metrics.collections.ToolCallAccuracy`
- ※ 정정 필요: `ragas.metrics.ToolCallF1` → `ragas.metrics.collections.ToolCallF1`
- ※ 정정 필요: `ragas.metrics.TopicAdherenceScore` → `collections.TopicAdherence` (`Score`가 빠짐)
- ※ 정정 필요: `ragas.metrics.AgentGoalAccuracyWith(out)Reference` → `collections` 하위 동명 클래스
- 위 4건은 원문이 `Legacy API (Deprecated)` 절에 이관 안내용으로 남긴 예제이며 원문 오류가 아님.
  교재는 신 경로만 싣고 구 경로는 각주로만 언급함
- 측정 대상이 다름 — 도구 호출 지표는 KT 4지표의 **대체재가 아님**. 4지표는 찾아온 자료와 쓴 답을,
  본 지표는 경로(어떤 도구를 어떤 인자로 어떤 순서에)를 봄. 두 층을 함께 측정해야 함
- 벤더 자체 문서임 — 4절 수치는 전부 문서 저자가 만든 설명용 예시이며 실측 성능 수치가 아님.
  따라서 지표 도입의 효과를 주장하는 근거로는 쓸 수 없음
- ※ 상충: 해당 없음 — `recommend-materials.md` 5절 상충 2건은 본 자료의 측정 범위와 겹치지 않음
- (추론) `ToolCallAccuracy`는 순서가 틀리면 0점이라 점수가 계단식으로 튐. 근거 — 원문 산식이 순서
  정렬 여부를 0 또는 1의 곱셈 항으로 둠. 개선 추이는 `ToolCallF1`을 함께 기록해야 부드럽게 보임
- 유효기간 — `/stable/`은 버전 표기가 없어 내용이 예고 없이 바뀌고 구 API의 v1.0 제거도 예고 상태임.
  교재 집필 시점에 임포트 경로를 재확인해야 함

## 7. 지표·실행 규격

원문에 등재된 지표만 올림. 다른 Ragas 페이지의 지표는 포함하지 않음
[§Agentic or Tool use, /stable/ 2026-08-05 조회 기준].

| 지표명 | 입력 데이터 | 출력 범위 | 계산 근거 | API 경로 |
|--------|------------|----------|----------|---------|
| TopicAdherence | `user_input`(대화 메시지 목록) + `reference_topics`(허용 주제 목록) + 판정용 LLM | 0 ~ 1(높을수록 좋음). 상·하한 명시 문구는 원문 미표기 — Precision · Recall · F1 수식에서 도출됨 | 답변한 질의가 허용 주제에 부합하는지 세어 Precision · Recall · F1 산출 [§Topic Adherence 수식 3개] | `ragas.metrics.collections.TopicAdherence` (`mode="precision"` 또는 `"recall"`) |
| ToolCallAccuracy | `user_input`(대화 메시지 목록) + `reference_tool_calls`(기대 호출 목록). 판정용 LLM 불필요 | 0 ~ 1(높을수록 좋음). 원문이 0 ~ 1 범위를 명시함 | 인자 정확도 × 순서 정렬 여부(1 또는 0) [§Tool call Accuracy > Key Features] | `ragas.metrics.collections.ToolCallAccuracy` (`strict_order` 인자) |
| ToolCallF1 | `user_input`(대화 메시지 목록) + `reference_tool_calls`(기대 호출 목록). 판정용 LLM 불필요 | 0 ~ 1(높을수록 좋음). 상·하한 명시 문구는 원문 미표기 — F1 수식에서 도출됨 | 이름·인자가 모두 맞는 호출을 TP로 두고 무순서 매칭으로 Precision · Recall · F1 산출 [§Tool Call F1 > Formula] | `ragas.metrics.collections.ToolCallF1` |
| AgentGoalAccuracyWithReference | `user_input`(대화 메시지 목록) + `reference`(기대 결과 문장) + 판정용 LLM | 0 또는 1의 이진값(1이 목표 달성) | 워크플로 종료 상태를 기대 결과 문장과 대조 [§Agent Goal Accuracy > With Reference] | `ragas.metrics.collections.AgentGoalAccuracyWithReference` |
| AgentGoalAccuracyWithoutReference | `user_input`(대화 메시지 목록) + 판정용 LLM. 정답 문장 불필요 | 0 또는 1의 이진값(1이 목표 달성) | 대화에서 사용자 목표와 달성 결과를 각각 추론해 서로 비교 [§Agent Goal Accuracy > Without Reference] | `ragas.metrics.collections.AgentGoalAccuracyWithoutReference` |

기대 도구 호출 시퀀스(정답 경로)의 입력 형태 — 3항목 모두 원문에서 확인됨
[§Tool call Accuracy · §Tool Call F1, /stable/ 2026-08-05 조회 기준].

- 자료구조 — `ragas.messages.ToolCall(name=..., args={...})` 객체의 **파이썬 리스트**를
  `reference_tool_calls`로 넘기고, 실제 호출은 `AIMessage.tool_calls`에서 읽음 [§Example: Basic Usage]
- 인자 비교 여부 — 비교함. `ToolCallAccuracy`는 인자 단위 부분 점수를 주고(3개 중 2개 일치 시 0.66),
  `ToolCallF1`은 인자가 하나라도 다르면 매치로 인정하지 않음 [§Scoring Examples × 2]
- 순서 일치 여부 — `ToolCallAccuracy`는 기본이 순서 일치 요구이며 `strict_order=False`로 해제함.
  `ToolCallF1`은 순서를 보지 않음 [§Key Features / §Tool Call F1 > Formula]

구/신 API 이관 여부 — 원문 대조 결과

- ① `ragas.metrics` → `ragas.metrics.collections` 이관 — **원문에서 확인됨**. 4개 지표 절 모두에
  구 경로가 v1.0에서 제거된다는 고지와 신 경로 이전 안내가 있음 [§Legacy API (Deprecated) × 4,
  /stable/ 2026-08-05 조회 기준]
- ② `Relevance` → `Response Relevancy` 개명 — **본 원문에서는 확인 불가**.
  본 페이지의 지표 범위에 `Relevance` 계열이 등재되어 있지 않아 대조 대상 자체가 없음
  [§Agentic or Tool use 지표 목록, /stable/ 2026-08-05 조회 기준]

## 8. 확인 범위와 미확인

- 조회일 2026-08-05. 확보 수단은 `curl -sL` 1회 성공이며 재시도 불필요
- 판독한 것 — H1 1개 · H2 4개 · H3 19개 전부, 본문 텍스트 8,188자 전문, 코드블록 26개 전부,
  수식 6개(TopicAdherence 3 · ToolCallF1 3), 비교 표 2개
- 못 본 것 — 본문 요소 중 판독하지 못한 것은 없음. 제외한 것은 좌측 네비게이션 · 상단 검색 ·
  하단 GitHub 링크 등 **본문이 아닌 요소**뿐이므로 FULL로 판정함
- 원문에 이미지·다이어그램은 0건임(추출 결과 `=== IMAGES ===` 항목이 비어 있음)
- `context7` MCP 대조 수행함(`/websites/ragas_io_en_stable`, 2026-08-05).
  두 지표의 신 경로 임포트와 `strict_order=False` 예제가 원문과 일치하고,
  v0.3 → v0.4 이관 문서에서 collections 이동도 재확인됨 — **불일치 0건**
- 미확인 — 본 페이지는 각 지표의 내부 구현 코드·판정 프롬프트를 싣지 않음.
  `AgentGoalAccuracy`가 LLM에게 무엇을 묻는지는 소스 코드를 별도로 봐야 확인 가능함

## 9. 열린 질문

- 기대 도구 호출 시퀀스(정답 경로)를 **누가 언제 만드는가** — KT는 강사 제작·도메인 전문가 검증(7-2절),
  신한은 조별 기획자 설계(6.5절 · S5.2)로 주체가 다름. 실습지시문을 두 벌로 나눌지 판단 필요
- (추론) KT 문항 수·난이도 배분이 미정임. 근거 — 7-2절은 테스트 데이터셋 존재만 규정하고 문항 수를
  적지 않으며, 본 원문도 권장 문항 수를 제시하지 않음
- 교재용 목표치 설정 여부 — 원문에 임계값이 없고 KT 7-2절도 지표와 수료 기준선을 연동하지 않음.
  목표치를 두지 않는 편이 맞는지 확인 필요. 신한 6.6절 `도구(MCP) 활용` 배점 연동 여부도 함께 판단
- `AgentGoalAccuracy`를 KT 7-2절에 넣을지 판단 필요. 결과 축 지표라 `MAS 흐름 정확성`(경로 축)과
  측정 대상이 다르며, 판정용 LLM 호출 비용이 추가로 발생함
