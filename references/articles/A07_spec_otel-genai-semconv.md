# A07 OpenTelemetry GenAI 시맨틱 컨벤션(전용 저장소)

## 1. 한눈에 보기

| 항목 | 내용 |
|------|------|
| 원문 URL | `https://github.com/open-telemetry/semantic-conventions-genai` — `main` 브랜치 2026-08-05 조회 기준 |
| 발행·갱신일 | 저장소 생성 2026-05-05, 최종 커밋 2026-08-05(최종 커밋일 기준). 릴리스·태그 0건이라 버전 표기 없음 |
| 발행 주체 | OpenTelemetry 프로젝트(CNCF 산하) — GitHub 조직 `open-telemetry` |
| 자료 유형 | 명세(specification) 문서 저장소. 문서 상태는 `Development`이며 확정 표준이 아닌 **표준 후보**임 |
| 확인 상태 | PARTIAL |
| 확인 방법·시점 | `curl -sL` + GitHub REST API로 원문 판독, 2026-08-05 |
| 저장 파일 | `.temp/otel-genai-semconv-repo.html`, `.temp/otel-genai-*.md` 11건 |
| 한 줄 요지 | GenAI·MCP 관측 기록의 속성·스팬·지표 이름을 정의한 표준 후보이며 `gen_ai.*`는 전부 `Development` 단계임 |
| 1차 대응 | 산출물 ⑥ 기록 지점 표준 이름 |

## 2. 핵심 주장

- **C1** 문서 상태 어휘는 `experimental`이 아니라 `Development`임. GenAI 규약 묶음 문서 첫머리에
  `**Status**: [Development]`로 표기됨 [docs/gen-ai/README.md §Status, main 2026-08-05 기준]
- **C2** `gen_ai.*` 네임스페이스(namespace, 이름 묶음) 속성 중 `Stable` 단계는 하나도 없음.
  속성 등록부 표의 모든 행이 `Development` 배지임 [표: Gen AI Attributes, main 2026-08-05 기준]
- **C3** 기록 대상은 4개 신호(signal)로 나뉨 — 스팬(span, 구간 기록) · 지표(metric) · 이벤트(event) ·
  예외(exception). 여기에 MCP(Model Context Protocol) 규약이 별도 문서로 붙음
  [docs/gen-ai/README.md §Signals, main 2026-08-05 기준]
- **C4** 스팬 이름은 값을 조합한 형식으로 정해짐. 모델 호출은 `{gen_ai.operation.name} {gen_ai.request.model}`,
  도구 호출은 `execute_tool {gen_ai.tool.name}`, 에이전트 실행은 `invoke_agent {gen_ai.agent.name}`임
  [docs/gen-ai/gen-ai-spans.md §Inference / §Execute tool span, main 2026-08-05 기준]
- **C5** 이 저장소는 아직 릴리스·태그가 0건이며 공통 규약은 상위 저장소에 핀(pin, 버전 고정)으로 참조함.
  현행 핀은 `v1.44.0`임 [model/manifest.yaml, main 2026-08-05 기준 / commit 2026-08-04]

## 3. 원문 구조

| 원문 경로 | 1줄 설명 |
|-----------|----------|
| `README.md` | 저장소 목적과 Weaver 기반 의존성 관리 안내. 문서는 `docs/`, 정의는 `model/`에 있음 [main 2026-08-05 기준] |
| `docs/README.md` | 상위 semantic-conventions 저장소에서 갈라져 나온 범위와 경계 설명 [main 2026-08-05 기준] |
| `docs/gen-ai/README.md` | GenAI 규약 묶음의 상태(`Development`)와 신호별 문서 목차 [main 2026-08-05 기준] |
| `docs/gen-ai/gen-ai-spans.md` | 모델 호출 스팬 — 추론 · 임베딩 · 검색 · 응답조회 · 메모리 · 도구 실행 [main 2026-08-05 기준] |
| `docs/gen-ai/gen-ai-agent-spans.md` | 에이전트 스팬 — 에이전트 생성 · 호출(client/internal) · 워크플로 · 계획 [main 2026-08-05 기준] |
| `docs/gen-ai/gen-ai-metrics.md` | 지표 — 클라이언트 · 모델 서버 · 워크플로 · 에이전트 · 도구 5개 묶음 [main 2026-08-05 기준] |
| `docs/gen-ai/gen-ai-events.md` | 이벤트 — 추론 상세(`gen_ai.client.inference.operation.details`)와 평가 결과 [main 2026-08-05 기준] |
| `docs/gen-ai/gen-ai-exceptions.md` | 클라이언트 작업 중 발생한 예외 기록 규칙 [main 2026-08-05 기준] |
| `docs/gen-ai/mcp.md` | MCP 스팬·지표·전송 기록과 stdio · Streamable HTTP 예시 [main 2026-08-05 기준] |
| `docs/gen-ai/{anthropic,openai,aws-bedrock,azure-ai-inference}.md` | 공급자별 추가 규약 4종(본 정리에서 미판독) [main 2026-08-05 기준] |
| `docs/registry/attributes/gen-ai.md` | `gen_ai.*` 속성 등록부. 이름 · 안정성 · 타입 · 설명 · 예시 5열 표 [main 2026-08-05 기준] |
| `docs/registry/attributes/{mcp,openai,aws}.md` | `mcp.*` · `openai.*` · `aws.*` 등록부(본 정리에서 미판독) [main 2026-08-05 기준] |
| `model/` | 문서를 생성하는 YAML 원본 정의. `manifest.yaml`이 상위 저장소 핀을 지정함 [main 2026-08-05 기준] |
| `changelog.d/` | Towncrier 방식 변경 조각 파일. `CHANGELOG.md` 본문은 아직 비어 있음 [main 2026-08-05 기준] |
| `reference/` | 파이썬 참조 구현과 신호별 준수 매트릭스(본 정리에서 미판독) [main 2026-08-05 기준] |

## 4. 인용 가능 문장·수치

| ID | 인용 가능 문장·수치 | 출처 앵커 |
|----|---------------------|-----------|
| Q1 | 문서 상태 표기 `**Status**: [Development]` — 안정성 단계 어휘가 `Development`임을 보이는 1차 근거 | [docs/gen-ai/README.md §Status, main 2026-08-05 기준] |
| Q2 | 갈라져 나온 경위 문장 — "split out from the main open-telemetry/semantic-conventions repository" | [docs/README.md §Contents 앞 문단, main 2026-08-05 기준] |
| Q3 | 저장소 성격 문장 — "This repository extends the OpenTelemetry Semantic Conventions with GenAI-specific conventions" | [README.md 도입부, main 2026-08-05 기준] |
| Q4 | ① `gen_ai.*` 속성 109개 전부 `Development`, `Stable` 0개 ② n=속성 등록부 표 전체 행 ③ 2026-08-05 조회 ④ 정리자가 원문 표 배지를 집계 ⑤ 원문 표 직접 집계(제3자 조사 아님) | [표: Gen AI Attributes, main 2026-08-05 기준] |
| Q5 | ① `gen_ai.operation.name` 허용값 18개 전부 `development` ② n=해당 속성 열거값 전체 ③ 2026-08-05 조회 ④ 정리자가 원문 정의 파일에서 집계 ⑤ 원문 직접 집계 | [model/gen-ai/registry.yaml `gen_ai.operation.name`, main 2026-08-05 기준] |
| Q6 | 모델 호출 스팬 이름 규칙 `{gen_ai.operation.name} {gen_ai.request.model}` (SHOULD 수준) | [docs/gen-ai/gen-ai-spans.md §Inference, main 2026-08-05 기준] |
| Q7 | 도구·에이전트 스팬 이름 규칙 `execute_tool {gen_ai.tool.name}` · `invoke_agent {gen_ai.agent.name}` (SHOULD 수준) | [docs/gen-ai/gen-ai-spans.md §Execute tool span / gen-ai-agent-spans.md §Invoke agent client span, main 2026-08-05 기준] |
| Q8 | ① 토큰 사용량 지표 `gen_ai.client.token.usage`, 히스토그램, 단위 `{token}`, 권장 버킷 경계 14개(1 ~ 67108864) ② n=원문 명시 버킷 목록 ③ 2026-08-05 조회 ④ OpenTelemetry 명세 본문 표기 ⑤ 명세 제정 주체 자체 규정(독립 조사 아님) | [docs/gen-ai/gen-ai-metrics.md §Metric: gen_ai.client.token.usage, main 2026-08-05 기준] |

## 5. 커리큘럼 대응

| 교육 | 위치 | 용도 | 가져올 것 | 집필 메모 |
|------|------|------|-----------|-----------|
| KT | Day 1 산출물 ⑥ 가드레일·관측 설계 | 기록 지점 표준 이름 | Q6 · Q7 — 모델 호출 · 도구 호출 · 에이전트 실행 3개 지점의 스팬 이름 규칙 | 템플릿 ⑥의 기록 지점 태그를 이 3개 이름 규칙으로 고정함 |
| KT | Day 1 산출물 ⑥ 오류·비용 태그 | 오류 · 토큰/비용 기록 지점 | Q8 — 토큰 지표 이름과 단위. 오류는 `error.type`(Stable 공통 속성) | 오류·비용 2개 지점만 가져옴. 속성 전체 목록은 옮기지 않음 |
| KT | Day 1 이론 `관측 가능성 설계` | 어휘 출처 | Q1 · Q4 — `Development` 단계와 `Stable` 0건 사실 | 확정 표준이 아니라 `표준 후보`로 소개함 |
| KT | Day 3 7-2절 (2) 시스템 품질 | 관측 기록 기반 검증 근거 | Q6 · Q7 — Day 1에 심은 스팬 이름을 Day 2 ~ 3 재측정 키로 씀 | 이름이 어긋나면 재측정이 불가하므로 Day 1에서 이름을 잠금 |
| 신한 | 해당 없음 | - | - | 대응 없음 |

## 6. 집필 시 주의

- 안정성 한계 — `gen_ai.*`에 `Stable` 항목이 0건이므로 속성 이름이 예고 없이 바뀔 수 있음.
  교재는 `표준 후보` 표기를 유지해야 하며 이 방침은 원문의 `Development` 단계와 **일치함**
  (고유-7 판정 결과) [docs/gen-ai/README.md §Status, main 2026-08-05 기준]
- 버전 없음 — 릴리스·태그가 0건이라 인용 시 버전 대신 조회일 병기가 필수임
- 정정 1 — `recommend-materials.md` 2절 3번은 `Stable`인 공통 속성을 `error.type` · `server.address` 2개로
  적었으나 원문에는 `server.port`도 `Stable`임. 원문 기준으로 3개로 정정함
- 정정 2 — 같은 항목의 `experimental` → `Development` 기재는 원문과 일치함을 재확인함(수정 불필요)
- 2차 출처 주장, 원문 미확인 — `recommend-materials.md` 4-4절 개인 블로그(`john-hodge.com`)의
  `gen_ai.system` → `gen_ai.provider.name` 개명 시점 `2025-08`은 저장소 이력과 어긋남.
  저장소에서 확인된 개명 반영 커밋은 2025-07-08임 [commit 06e681a, 2025-07-08]
- 2차 출처 주장, 원문 미확인 — 같은 블로그의 `본체 semconv v1.43.0에서 gen_ai.* 완전 제거` 서술은
  본 저장소 어디에서도 확인되지 않음. 8절 미확인으로 분리함
- (추론) 개명 이력을 교재에 실으려면 상위 저장소를 별도 1차 출처로 확인해야 함.
  근거 — 본 저장소는 상위 이력을 물려받았을 뿐 제거 사유를 스스로 서술하지 않음
- 유효기간 — `main` 브랜치가 매일 갱신되므로 인용은 2026-08-05 시점으로만 유효함

## 7. 명세 변경 이력

- 안정성 단계 어휘 판정 — 현행 어휘는 `Development`이며 `experimental`이 아님. 원문 문서 머리말에
  `**Status**: [Development]`로 명시됨 [docs/gen-ai/README.md §Status, main 2026-08-05 기준]

| 속성 이름 | 안정성 단계 | 적용 대상 |
|-----------|-------------|-----------|
| `gen_ai.operation.name` | Development | 모든 GenAI 스팬 공통 — 작업 종류 구분 [표: Gen AI Attributes, main 2026-08-05 기준] |
| `gen_ai.request.model` | Development | 모델 호출 스팬 — 스팬 이름 구성값 [docs/gen-ai/gen-ai-spans.md §Inference, main 2026-08-05 기준] |
| `gen_ai.tool.name` | Development | 도구 호출 스팬 — 스팬 이름 구성값 [docs/gen-ai/gen-ai-spans.md §Execute tool span, main 2026-08-05 기준] |
| `gen_ai.agent.name` | Development | 에이전트 스팬 — 스팬 이름 구성값 [docs/gen-ai/gen-ai-agent-spans.md §Invoke agent client span, main 2026-08-05 기준] |
| `gen_ai.usage.input_tokens` | Development | 토큰·비용 기록 [표: Gen AI Attributes, main 2026-08-05 기준] |
| `error.type` | Stable | 모든 스팬 공통 오류 기록. 상위 저장소 `v1.44.0` 핀 참조 [docs/gen-ai/gen-ai-spans.md 속성표, main 2026-08-05 기준] |
| `server.address` · `server.port` | Stable | 클라이언트·MCP 스팬 공통. 상위 저장소 `v1.44.0` 핀 참조 [docs/gen-ai/mcp.md 속성표, main 2026-08-05 기준] |

- 안정성 단계는 3종이 관찰됨 — `Development` · `Stable` 외에 `Release Candidate`가 4건 있으나
  모두 상위 저장소의 `rpc.*` 속성이며 `gen_ai.*`에는 없음 [docs/gen-ai/mcp.md 속성표, main 2026-08-05 기준]
- 저장소 이전 경위 — 원문이 밝히는 것은 GenAI·MCP 규약이 상위 저장소에서
  "split out from the main open-telemetry/semantic-conventions repository" 되었다는 사실까지임
  [docs/README.md, main 2026-08-05 기준]. 상위 저장소가 특정 버전에서 `gen_ai.*`를 제거했다는 서술은
  원문에 없으므로 8절 미확인에 남김
- 확인된 개명·분리 이력 2건 — `invoke_agent` 스팬이 client용과 internal용으로 분리됨
  [commit 451ca93, 2026-04-03]. `gen_ai.system`은 폐기 등록부에 `renamed_to: gen_ai.provider.name`으로
  기록된 뒤 해당 파일이 삭제됨 [commit 06e681a, 2025-07-08 / commit 0bcb478, 2026-05-18]
- 릴리스 이력 없음 — `/releases` · `/tags` 모두 0건이며 `CHANGELOG.md`는 Towncrier 머리말만 있음
  [CHANGELOG.md, main 2026-08-05 기준]

## 8. 확인 범위와 미확인

- 조회일 2026-08-05, 최신 커밋 해시 앞 7자리 `7e6e188`(2026-08-05T05:11:06Z)
- 판독한 것 — `README.md` · `CHANGELOG.md` · `docs/README.md` · `docs/gen-ai/README.md` ·
  `gen-ai-spans.md` · `gen-ai-agent-spans.md` · `gen-ai-metrics.md` · `gen-ai-events.md` ·
  `gen-ai-exceptions.md` · `mcp.md` · `docs/registry/attributes/gen-ai.md` · `versions.env` ·
  `changelog.d/` 파일 목록과 breaking 조각 5건
- 못 본 것 — 공급자별 규약 4종(`anthropic` · `openai` · `aws-bedrock` · `azure-ai-inference`),
  `docs/gen-ai/non-normative/` 전체, `docs/registry/attributes/{mcp,openai,aws}.md`,
  `model/` YAML 전체(일부만 확인), `reference/` 구현. 본문에 해당하므로 PARTIAL로 판정함
- 미확인 — 상위 semantic-conventions 저장소가 `v1.43.0`(2026-07)에서 `gen_ai.*`를 제거하여
  1차 출처가 전용 저장소로 옮겨졌다는 경위는 본 저장소의 README · CHANGELOG · 기여 문서 어디에서도
  확인되지 않음. 저장소 안의 `v1.43.0` 표기는 모두 상위 문서를 가리키는 링크 핀이며 서술문이 아님
- 미확인 — 저장소 GitHub 설명(description)은 비어 있어 서지 정보로 쓸 수 없음

## 9. 열린 질문

- 상위 저장소의 `gen_ai.*` 제거 경위를 별도 1차 출처로 확인할지 결정 필요.
  확인하지 않으면 교재에서 이전 경위를 서술하지 않고 "전용 저장소가 현행 1차 출처"까지만 적어야 함
- 신한카드 M2 S2.1(2-1 차시 폐쇄망 MCP 호출 로그 보존)과 M5 S5.2(8-2 차시 호출·응답 로그 확인)에
  `mcp.*` 속성 이름을 최소한으로 얹을지 판단 필요. 현재 두 차시는 이름 체계를 다루지 않음
- (추론) 릴리스가 0건인 동안에는 교재 각주를 조회일 기준으로 유지하는 편이 안전함.
  근거 — 태그가 없어 인용 시점을 고정할 다른 수단이 없음
