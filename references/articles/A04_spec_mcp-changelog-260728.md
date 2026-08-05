# A04 MCP 명세 2026-07-28 변경 요약(MCP Specification Changelog 2026-07-28)

## 1. 한눈에 보기

| 항목 | 내용 |
|------|------|
| 원문 URL | https://modelcontextprotocol.io/specification/2026-07-28/changelog |
| 발행·갱신일 | 2026-07-28 개정판(본문 표기 — 직전 개정판을 `2025-11-25`로 명시). 페이지 상단에 `latest` 배지가 있어 `2026-08-05 조회 기준`으로 병기함 |
| 발행 주체 | Model Context Protocol(MCP) 명세 관리 주체 — `modelcontextprotocol.io` 공식 문서 |
| 자료 유형 | 표준 명세 변경 이력(changelog). 조사·벤치마크 자료가 아니므로 표본·측정 주체 축이 성립하지 않음 |
| 확인 상태 | FULL |
| 확인 방법·시점 | curl 저장 후 본문 판독 / 2026-08-05 |
| 저장 파일 | `.temp/mcp-changelog-20260728.html`(285KB) · 텍스트 추출본 `.temp/mcp-changelog.txt`(9,818자) |
| 한 줄 요지 | 세션과 핸드셰이크(handshake)를 없애 MCP를 무상태(stateless) 프로토콜로 바꾸고, Roots · Sampling · Logging을 폐기 예정으로 지정함 |
| 1차 대응 | KT Day 2 멀티 MCP 실습과 산출물 ⑤ 커넥터 규격, 신한 Day 8 MCP 서버 구축의 판본 고정 근거 |

## 2. 핵심 주장

- **C1** 프로토콜 수준 세션과 `Mcp-Session-Id` 헤더가 Streamable HTTP 전송에서 제거됨. `tools/list` · `resources/list` ·  
  `prompts/list` 결과가 연결마다 달라지지 않으며, 호출 사이에 상태가 필요하면 서버가 발급한 핸들(handle)을  
  평범한 도구 인자로 주고받음 [§Major changes]
- **C2** `initialize` · `notifications/initialized` 핸드셰이크가 제거되어 모든 요청이 자기 프로토콜 버전과 클라이언트  
  능력(capabilities)을 `_meta`에 실어 보냄. 버전이 맞지 않으면 `UnsupportedProtocolVersionError`가 반환됨 [§Major changes]
- **C3** 서버가 먼저 거는 요청(`roots/list` · `sampling/createMessage` · `elicitation/create`)이 MRTR(Multi Round-Trip  
  Requests) 방식으로 대체됨. 서버가 `InputRequiredResult`를 돌려주면 클라이언트가 원래 요청을 재시도하며 답을 실어 보냄.  
  모든 결과에 `resultType` 필드가 필수가 됨 [§Major changes]
- **C4** Roots · Sampling · Logging 3기능이 폐기 예정(Deprecated)으로 지정됨. 폐기 기간 동안은 그대로 동작하나 신규  
  구현은 채택하지 않도록 권고되며, 기능 수명주기 정책이 최소 12개월의 폐기 창을 규정함 [§Deprecated]
- **C5** 서버→클라이언트 알림 경로가 `subscriptions/listen` 단일 스트림으로 통합되고 SSE 재개(resumability)가 삭제됨.  
  인증·캐시 쪽에서는 `iss` 검증 의무, `CacheableResult`(`ttlMs` · `cacheScope`) 필수화가 추가됨 [§Major changes]

## 3. 원문 구조

| 원문 소제목 | 1줄 설명 | 앵커 |
|------------|---------|------|
| (도입 문장) | 직전 개정판 `2025-11-25` 이후의 변경만 다룬다고 밝힘 | `[§(도입 문장)]` |
| Major changes | 전송·세션·요청 흐름을 바꾸는 큰 변경 9건. 커넥터 구현에 직접 영향 | `[§Major changes]` |
| Minor changes | 필드·헤더·오류 코드·인증 세부 규칙 변경 11건 | `[§Minor changes]` |
| Deprecated | 남아 있으나 제거 예정인 기능 4건과 각각의 대체 경로 | `[§Deprecated]` |
| Other schema changes | `schema.json` 생성 오류 정정 1건(minimum·maximum·default의 타입) | `[§Other schema changes]` |
| Governance and process updates | 기능 수명주기·폐기 정책 채택과 폐기 기능 레지스트리 신설 | `[§Governance and process updates]` |
| Process changes | SEP(명세 제안) 작업 방식을 PR 기반으로 공식화 | `[§Process changes]` |
| Full changelog | 전체 변경 목록은 GitHub을 보라고 안내하는 링크 1줄 | `[§Full changelog]` |

## 4. 인용 가능 문장·수치

| ID | 인용·수치 | 5요소(값·단위 / 표본n / 시점 / 측정 주체 / 독립 여부) | 앵커 |
|----|----------|--------------------------------------------|------|
| Q1 | 직전 개정판이 `2025-11-25`임 | 2025-11-25(판본일) / 해당 없음(명세 문서) / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서(조사 아님) · 2026-08-05 조회 | `[§(도입 문장)]` |
| Q2 | 리소스 없음 오류 코드가 `-32002` → `-32602`(Invalid Params)로 변경됨 | -32002→-32602(코드) / 해당 없음 / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서 · 2026-08-05 조회 | `[§Minor changes]` |
| Q3 | 오류 코드 구획: `-32000` ~ `-32019` 구현 정의, `-32020` ~ `-32099` 명세 예약 | 20개·80개(코드 구간) / 해당 없음 / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서 · 2026-08-05 조회 | `[§Minor changes]` |
| Q4 | 재번호 3건 — `HeaderMismatch` -32001→-32020, `MissingRequiredClientCapability` -32003→-32021, `UnsupportedProtocolVersion` -32004→-32022 | 3건(코드) / 해당 없음 / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서 · 2026-08-05 조회 | `[§Minor changes]` |
| Q5 | 최소 12개월의 폐기 창(deprecation window)을 규정함 | 12개월(기간) / 해당 없음 / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서 · 2026-08-05 조회 | `[§Governance and process updates]` |
| Q6 | `ttlMs`는 밀리초 단위 신선도 힌트이고 `cacheScope`는 `"public"` 또는 `"private"` 2값임 | ms·2값 / 해당 없음 / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서 · 2026-08-05 조회 | `[§Minor changes]` |
| Q7 | "Make MCP stateless: remove the `initialize`/`notifications/initialized` handshake."(직접 인용) | 해당 없음 / 해당 없음 / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서 · 2026-08-05 조회 | `[§Major changes]` |
| Q8 | "Deprecate the Roots, Sampling, and Logging features"(직접 인용) | 3기능 / 해당 없음 / 2026-07-28 개정 / MCP 명세 제정 주체 자체 규정 / 표준 문서 · 2026-08-05 조회 | `[§Deprecated]` |

- 표기 규칙 — 5요소 중 ④측정 주체 · ⑤독립 여부는 조사 자료에만 성립하는 축임. 본 자료는 표준 명세이므로  
  `명세 제정 주체 자체 규정` · `표준 문서(조사 아님)`로 성격을 밝혀 채웠고 추정으로 메우지 않음

## 5. 커리큘럼 대응

| 교육 | 위치 | 용도 | 가져올 것 | 집필 메모 |
|------|------|------|----------|----------|
| KT | Day 2 멀티 MCP, 산출물 ⑤ 커넥터 규격(`recommend-materials.md` 1절 4번 값 그대로) | 실습지시문 | C1 · C2 · Q1 · Q7 | 여러 서버를 붙이는 전제 규격이 무상태로 바뀐 점을 실습 도입 1문단으로 씀 |
| KT | 산출물 ⑤ MCP 커넥터 목록·입출력 규격 칸 | 템플릿 | C1 · C3 · Q1 | 규격 칸 상단에 `기준 판본 2026-07-28`을 고정 표기하는 방식으로 반영함 |
| KT | 8-1절 스타터 리포지토리 MCP 클라이언트 | 점검 | C4 · Q8 | 폐기 예정 3기능 의존 여부 점검 항목을 9절에 올림(코드 미확인) |
| 신한 | M5 S5.1 · S5.2(Day 8-1 ~ 8-3) | 슬라이드 | C1 · C2 · C3 | 도구 정의 4요소 설명은 유지되나 요청 처리 흐름 그림에서 핸드셰이크 단계를 뺌 |
| 신한 | M2 S2.1(Day 2-1) 폐쇄망 MCP 운영 | 각주 | C1 · C5 · Q5 | 무상태화로 서버 배치·재기동이 쉬워지는 대신 호출 로그 보존은 요청 단위 설계가 필요하다는 각주 1줄로 붙임 |
| 신한 | 7.2절 SDK 버전 고정 스타터 서버 | 준비물 | C1 · C4 | 판본 선택이 갈리는 축은 무상태 전송 지원 여부와 폐기 예정 3기능 사용 여부 2개임. 판본 확정은 9절로 올림 |

## 6. 집필 시 주의

- 유효기간 — URL에 판본이 박혀 있어 내용은 고정이나 페이지에 `latest` 배지가 있으므로 인용 시 `2026-08-05 조회 기준`을 병기함
- 한계 — 본 문서는 변경 목록만 담고 각 조항의 상세 규격은 담지 않음. 필드 세부 규격은 명세 본문 해당 절을 별도 확인해야 함
- 한계 — SDK 구현이 본 개정을 어디까지 따라왔는지는 changelog에 없음. SDK 판본 판단은 본 문서로 확정 불가함
- ※ 기록 정정: `server/discover` RPC 필수화 → 원문은 서버에 대해 MUST 구현이고 클라이언트는 MAY 호출임(호출 의무 아님)
- 보조 자료 취급 — 릴리스 후보 해설 블로그(`blog.modelcontextprotocol.io`)는 본 작업에서 열지 않았고 근거로 쓰지 않음
- `recommend-materials.md` 5절 상충 2건(C4에서 에이전트의 계층 · 역할 분해 방식)은 본 자료의 내용과 겹치지 않아 해당 없음
- (추론) 무상태화는 로드밸런서 뒤 다중 인스턴스 배치를 쉽게 만들 여지가 있음 — 근거: 세션 헤더 제거로 요청이 특정  
  서버 인스턴스에 묶이지 않음. 다만 원문이 배치 이점을 명시하지 않았으므로 사실 문장으로 쓰지 않음
- (추론) 신한 7.2절 스타터 서버는 폐기 예정 3기능을 처음부터 쓰지 않는 편이 안전함 — 근거: 최소 12개월 폐기 창 이후  
  제거가 예정되어 있어 교육 후 재작업 비용이 발생함
- 구현 서술 표기 — 본 문서의 커넥터·클라이언트 관련 서술은 서버·클라이언트를 실제 기동해 확인하지 않은 `미검증 설계`임

## 7. 명세 변경 이력

직전 개정판: 2025-11-25 [§(도입 문장)]

| 구분 | 항목(규격 이름·필드·RPC) | 직전 개정판 대비 내용 | 앵커 |
|------|------------------------|---------------------|------|
| 파괴적 변경 | 프로토콜 세션 · `Mcp-Session-Id` 헤더 | Streamable HTTP에서 제거됨. 목록 엔드포인트가 연결별로 달라지지 않고, 상태는 서버 발급 핸들을 도구 인자로 전달함 | `[§Major changes]` |
| 파괴적 변경 | `initialize` · `notifications/initialized` | 핸드셰이크 제거. 요청마다 `_meta`에 `io.modelcontextprotocol/protocolVersion`·`clientCapabilities`를 실음 | `[§Major changes]` |
| 추가 | `server/discover` | 서버가 MUST 구현하여 지원 버전·능력·신원을 알림. 클라이언트는 MAY 호출(사전 버전 선택 또는 STDIO 하위호환 탐침) | `[§Major changes]` |
| 파괴적 변경 | HTTP GET 엔드포인트 · `resources/subscribe` · `resources/unsubscribe` | `subscriptions/listen` 단일 롱리브드 POST 스트림으로 대체. 클라이언트가 알림 종류 4종을 옵트인함 | `[§Major changes]` |
| 파괴적 변경 | `ping` · `logging/setLevel` · `notifications/roots/list_changed` | 제거됨. 로그 레벨은 요청별 `_meta`의 `io.modelcontextprotocol/logLevel`로 지정함 | `[§Major changes]` |
| 파괴적 변경 | `roots/list` · `sampling/createMessage` · `elicitation/create` | 서버 개시 요청이 MRTR로 대체. 서버가 `InputRequiredResult`·`inputRequests`를 주고 클라이언트가 재시도에 `inputResponses`를 실음 | `[§Major changes]` |
| 파괴적 변경 | `resultType` | 모든 결과에 필수 필드로 추가. `"complete"` 또는 `"input_required"` 2값임 | `[§Major changes]` |
| 파괴적 변경 | `Last-Event-ID` · SSE 이벤트 ID | 스트림 재개·메시지 재전송이 제거됨. 스트림이 끊기면 새 요청 ID로 다시 보내야 함 | `[§Major changes]` |
| 변경 | 실험적 tasks | 코어에서 공식 확장 `io.modelcontextprotocol/tasks`로 이전. `tasks/result` → `tasks/get` 폴링 + `tasks/update`, `tasks/list` 제거 | `[§Major changes]` |
| 추가 | `Mcp-Method` · `Mcp-Name` · `x-mcp-header` | Streamable HTTP POST에 표준 헤더를 요구하고, 도구 파라미터에서 온 커스텀 헤더를 지원함 | `[§Minor changes]` |
| 추가 | `CacheableResult`(`ttlMs` · `cacheScope`) | 목록·읽기 계열 결과 5종에 캐시 힌트 필드를 요구함 | `[§Minor changes]` |
| 변경 | JSON-RPC 오류 코드 | 리소스 없음이 `-32002`→`-32602`. 서버 오류 구간을 구현 정의/명세 예약으로 분할하고 3건을 재번호함 | `[§Minor changes]` |
| 폐기 예정 | Roots · Sampling · Logging | 폐기 창 동안 완전 동작. 대체는 도구 파라미터·리소스 URI·서버 설정 / LLM 제공자 API 직접 연동 / `stderr` 또는 OpenTelemetry | `[§Deprecated]` |
| 폐기 예정 | HTTP+SSE 전송 · `includeContext`의 `"thisServer"`·`"allServers"` | 수명주기 정책상 Deprecated로 재분류. 전송은 Streamable HTTP로 이관, 값은 생략하거나 `"none"` 사용 | `[§Deprecated]` |
| 폐기 예정 | OAuth 2.0 동적 클라이언트 등록(RFC7591) | Client ID Metadata Documents를 선호 방식으로 바꿈. 미지원 인가 서버 대상 하위호환용으로만 유지 | `[§Deprecated]` |

하위호환 조건 — 구판 서버가 `resultType`을 생략하면 클라이언트가 `"complete"`로 취급해야 함 [§Major changes].  
폐기 예정 기능은 폐기 창 동안 그대로 동작하고, 오류 코드 `-32000` ~ `-32019`의 기존 SDK 사용은 유예됨 [§Deprecated][§Minor changes].  
`server/discover`는 STDIO에서 하위호환 탐침으로 쓸 수 있고, RFC7591 등록은 미지원 인가 서버용으로 남음 [§Major changes][§Deprecated].

## 8. 확인 범위와 미확인

판독한 것 — changelog 본문 6개 절(Major · Minor · Deprecated · Other schema · Governance · Process)과 도입 문장 전체임  
못 본 것 — 명세 본문(`/specification/2026-07-28/`) 각 조항, 각 SEP 문서 원문, GitHub 전체 변경 목록, 해설 블로그임  
7절 표 15행 상한으로 제외한 나머지 변경은 11건임(Minor 8 · Other schema 1 · Governance 1 · Process 1) [§Minor changes]

| 기록 내용(`recommend-materials.md` 2절 1번) | 원문 확인 결과 | 판정 |
|----------|--------------|------|
| ① 핸드셰이크 제거 | `initialize`·`notifications/initialized` 핸드셰이크를 제거하고 MCP를 무상태로 만든다고 명시됨 | 일치 |
| ② `Mcp-Session-Id` 제거로 인한 무상태화 | 프로토콜 세션과 `Mcp-Session-Id` 헤더를 Streamable HTTP에서 제거한다고 명시됨 | 일치 |
| ③ `Roots`·`Sampling`·`Logging` 3기능 폐기 예정 | Deprecated 절 첫 항목으로 3기능 폐기와 대체 경로가 명시됨 | 일치 |
| ④ `server/discover` RPC 필수화 | 서버는 MUST 구현이나 클라이언트는 MAY 호출임 — 필수 범위가 서버 측에 한정됨 | 일치(범위 정정) |

## 9. 열린 질문

- 스타터 리포지토리 MCP 클라이언트가 폐기 예정 3기능(Roots · Sampling · Logging)에 의존하는지 점검 필요 —  
  어느 기능: Roots · Sampling · Logging / 확인할 대상: KT 8-1절 스타터 리포지토리 MCP 클라이언트 코드 / 대체 경로 후보:  
  도구 파라미터·리소스 URI·서버 설정, LLM 제공자 API 직접 연동, `stderr` 또는 OpenTelemetry. `코드 미확인 상태의 점검 제안`임
- `recommend-materials.md` 2절 1번 정정 필요 — `server/discover` 필수화(서버 MUST 구현 / 클라이언트 MAY 호출로 범위 한정)
- 신한 7.2절 스타터 MCP 서버의 SDK 판본 확정 — 판단 축은 무상태 전송 지원 여부와 폐기 3기능 사용 여부. 담당자 결정 사항임
- KT Day 2 실습 서버를 2026-07-28 판과 2025-11-25 판 중 어느 쪽으로 맞출지 결정 필요

