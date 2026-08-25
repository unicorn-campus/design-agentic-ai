# 미검증 설계: Help Desk 도구·커넥터

실물 연결·호출 시험 없이 HTTP Mock과 메모리 대역으로만 검증한 설계임.  
외부 응답 문자열은 신뢰하지 않는 데이터로 취급함.  
`response_guard` 훅을 통과한 뒤에만 반환함.

## 개요

바깥 시스템 5종과 연결하는 REST 커넥터 5개 제공 모듈임.  
설계서 ② 「신뢰경계표」와 ⑤ 「Mock·실물 구분」에 따라 전건 Mock을 기본값으로 둠.

| 커넥터 | 대상 | 기본 구현 | 부작용 |
|---|---|---|---|
| `C-A1` | 상용 LLM API | Mock | 읽기 |
| `C-A2` | 상담·거래 분석 뷰 | Mock | 읽기 |
| `C-A3` | 공식 웹·영상 | Mock | 읽기 |
| `C-A4` | CRM | Mock | 쓰기(되돌림 가능) |
| `C-A5` | 설문 시스템 | Mock | 쓰기(되돌림 불가) |

## 적용 결정

| 항목 | 정한 값 | 되돌려 알릴 곳 |
|---|---|---|
| 재시도 계층 | 커넥터 1계층만 | `06-workflow.md` 담당자 |
| 비가역 호출 시간 초과 | 승인 뒤 요청을 취소하지 않고 결과 대기 | `06-workflow.md` 담당자 |
| 중복 방지 저장 | D-08 SQLite 저장소, 24시간 | 배포 설정과 운영자 |
| 인증 갱신 | 만료 전 갱신, 갱신 실패는 인증 오류 | 커넥터 운영자 |

## 가상환경 만들기와 시험 실행

### Windows GitBash

```bash
cd src/tools
uv sync --group dev
uv run pytest
```

### Windows PowerShell

```powershell
Set-Location src/tools
uv sync --group dev
uv run pytest
```

### Linux 또는 Mac

```bash
cd src/tools
uv sync --group dev
uv run pytest
```

실호출 시험은 `uv run pytest -m live_call`로만 실행하는 규칙임.  
현재 `live_call` 시험은 0건이며 실제 주소나 자격을 사용한 적 없음.

## 도구 명세

| 도구명 | 입력 | 출력 | 부작용 | 인증 방식 | 요청 범위 | 승인 필요 | 출처 |
|---|---|---|---|---|---|:---:|---|
| 상용 LLM API | `model`, `input`, `max_output_tokens` | `id`, `output_text`, `usage.total_tokens` | 읽기 | Mock 무자격 | 0건 | 아니오 | ④ 표B·⑤ REST `C-A1` |
| 상담·거래 분석 뷰 | `statement`, `parameters`, `max_rows` | `query_id`, `rows`, `row_count` | 읽기 | Mock 무자격 | 0건 | 아니오 | ④ 표B·⑤ REST `C-A2` |
| 공식 웹·영상 | `query`, `source_type`, `period_days`, `sort`, `max_results`, 선택 2키 | `results` 5키 | 읽기 | Mock 무자격 | 0건 | 아니오 | ④ 표B·⑤ REST `C-A3` |
| CRM | `consultation_ref`, `approval_id`, `summary`, `idempotency_key` | `record_id`, `status` | 쓰기(되돌림 가능) | Mock 무자격 | 0건 | 예, `R-H3` | ④ 표B·⑤ REST `C-A4`·⑥ 승인 지점 |
| 설문 시스템 | `customer_ref`, `consultation_ref`, `consent_ref`, `idempotency_key` | `send_id`, `status` | 쓰기(되돌림 불가) | Mock 무자격 | 0건 | 예, `R-H4` | ④ 표B·⑤ REST `C-A5`·⑥ 승인 지점 |

Mock이므로 요청한 외부 권한 범위는 전건 0개임.  
실물 전환 전 커넥터별 인증 방식과 제공자 고유 scope 확정 필요함.

최소 권한은 실제 필요한 엔드포인트 1개만 허용하는 원칙임.  
최소 권한은 열쇠를 업무에 필요한 문 하나에만 맞추는 보안 방식임.

## 외부 키와 우리쪽 이름 매핑

`해당 없음(상태 미적재)`은 외부 응답을 검증·관측한 뒤 State에 보존하지 않는다는 뜻임.  
새 State 필드 생성이 아니라 단계 안에서만 쓰고 버리는 처리임.

### `C-A1` 상용 LLM API

| 외부 키 | 방향 | 우리쪽 이름 | 변환 |
|---|---|---|---|
| `model` | 요청 | `RuntimeSettings.llm_model` | 설정에서 주입 |
| `input` | 요청 | `safe_inquiry_text`·`sql_candidate`·`evidence_refs`·`masked_consultation_refs`·`topic_evidence`·`masked_transcript` | 호출 단계별 배열 조립 |
| `max_output_tokens` | 요청 | `RuntimeSettings.llm_max_tokens` | 설정에서 주입 |
| `id` | 응답 | 해당 없음(상태 미적재) | 관측 훅에만 전달 |
| `output_text` | 응답 | `route_decision`·`sql_candidate`·`evidence_refs`·`answer_draft`·`topic_evidence`·`faq_candidates`·`summary_draft` | 호출 단계의 State 타입으로 파싱 |
| `usage.total_tokens` | 응답 | 해당 없음(상태 미적재) | 관측 훅에만 전달 |

### `C-A2` 상담·거래 분석 뷰

| 외부 키 | 방향 | 우리쪽 이름 | 변환 |
|---|---|---|---|
| `statement` | 요청 | `sql_candidate` | 없음 |
| `parameters` | 요청 | 해당 없음(상태 미적재) | `S-R4`·`S-B2`·`S-B4` 호출 인자 조립 |
| `max_rows` | 요청 | 해당 없음(상태 미적재) | 단계별 조회 상한 전달 |
| `query_id` | 응답 | 해당 없음(상태 미적재) | 관측 훅에만 전달 |
| `rows` | 응답 | `evidence_refs`·`masked_consultation_refs` | 단계에 따라 참조값 배열로 변환 |
| `row_count` | 응답 | 해당 없음(상태 미적재) | 관측 훅에만 전달 |

### `C-A3` 공식 웹·영상

| 외부 키 | 방향 | 우리쪽 이름 | 변환 |
|---|---|---|---|
| `query` | 요청 | `safe_inquiry_text`·`topic_evidence` | 비식별 검색어만 조립 |
| `source_type` | 요청 | 해당 없음(상태 미적재) | 웹·영상 값으로 조립 |
| `period_days` | 요청 | 해당 없음(상태 미적재) | ⑤ 외부검색 기준 전달 |
| `sort` | 요청 | 해당 없음(상태 미적재) | ⑤ 외부검색 기준 전달 |
| `max_results` | 요청 | 해당 없음(상태 미적재) | ⑤ 외부검색 기준 전달 |
| `include_content` | 요청 | 해당 없음(상태 미적재) | 웹 호출 때 선택 전달 |
| `include_transcript` | 요청 | 해당 없음(상태 미적재) | 영상 호출 때 선택 전달 |
| `results.title` | 응답 | `evidence_refs`·`topic_evidence` | 근거 객체의 제목으로 변환 |
| `results.url` | 응답 | `evidence_refs`·`topic_evidence` | 근거 객체의 URL로 변환 |
| `results.retrieved_at` | 응답 | `evidence_refs`·`topic_evidence` | 근거 객체의 조회 시각으로 변환 |
| `results.content_excerpt` | 응답 | `evidence_refs`·`topic_evidence` | 입력측 검사 후 근거 발췌로 변환 |
| `results.transcript_range` | 응답 | `evidence_refs`·`topic_evidence` | 입력측 검사 후 자막 구간으로 변환 |

### `C-A4` CRM

| 외부 키 | 방향 | 우리쪽 이름 | 변환 |
|---|---|---|---|
| `consultation_ref` | 요청 | `consultation_ref` | 없음 |
| `approval_id` | 요청 | `review_decision` | 객체에서 승인 ID 추출 |
| `summary` | 요청 | `summary_draft`·`review_decision` | 승인된 수정 요약 우선 |
| `idempotency_key` | 요청 | `event_id` | W-3 + event ID + 작업 종류 해시 |
| `record_id` | 응답 | `crm_result` | 객체 필드로 저장 |
| `status` | 응답 | `crm_result` | 객체 필드로 저장 |

### `C-A5` 설문 시스템

| 외부 키 | 방향 | 우리쪽 이름 | 변환 |
|---|---|---|---|
| `customer_ref` | 요청 | `consultation_ref` | 설계된 고객·상담 참조값 전달 |
| `consultation_ref` | 요청 | `consultation_ref` | 없음 |
| `consent_ref` | 요청 | `survey_consent_ref` | 없음 |
| `idempotency_key` | 요청 | `event_id` | W-3 + event ID + 작업 종류 해시 |
| `send_id` | 응답 | `survey_result` | 객체 필드로 저장 |
| `status` | 응답 | `survey_result` | 객체 필드로 저장 |

## 시간 상한과 재시도

단계별 `RuntimeSettings.stage_budgets`의 시간 상한·재시도 횟수를 호출 때 전달함.  
다른 계층에는 재시도를 만들지 않으며 `ExternalTools`의 커넥터 감싸개 한 곳에서만 수행함.

재시도 간격은 ⑥ 「커넥터 호출 상한」의 커넥터·워크플로우별 값을 전달함.  
흔들림 폭은 개발 결정값 `HELP_DESK_CONNECTOR_JITTER_RATIO=0.1`로 둠.

⑥의 호출 수 상한과 연속 실패 차단은 `ConnectorGuards`가
`InvocationLimiter`와 `CircuitBreaker`를 연결하는 훅임.  
상한은 문이 너무 자주 열리지 않게 세는 장치임.  
Circuit Breaker는 반복 장애 때 잠시 문을 닫는 장치임.

## 중복 방지

쓰기 2종 `C-A4`·`C-A5`에만 Idempotency Key 적용함.  
읽기 3종에는 키를 만들지 않음.

키 조립 함수는 `build_idempotency_key` 1개임.  
성분은 ③ 재개 방안의 `W-3 + event ID + 작업 종류`임.

| 커넥터 | 외부 시스템이 키를 받나 | 우리쪽 차단 | 보관 |
|---|:---:|:---:|---|
| `C-A4` | 예 | 예 | D-08 SQLite 24시간 |
| `C-A5` | 예 | 예 | D-08 SQLite 24시간 |

Idempotency Key는 같은 작업을 두 번 요청해도 외부 실행을 한 번만 하게 만드는  
중복 방지 표식임.

## 승인 문

`C-A4`는 `S-E5`의 `R-H3` 승인 ID가 없으면 호출을 거부함.  
`C-A5`는 `R-H4` 승인 표시와 수신 동의 참조값이 없으면 호출을 거부함.

`C-A5`는 되돌림 불가 도구이므로 시간 상한 도달 때 실행 작업을 취소하지 않음.  
승인 문 뒤에서 완료 결과를 기다리며 취소를 성공으로 보고하지 않음.

기본 거부는 권한 근거가 없으면 먼저 막고 근거가 확인된 뒤 여는 보안 방식임.

## 오류 분류

| 분류 | 신호 | 재시도 | 위로 올리는 정보 |
|---|---|:---:|---|
| 인증 오류 | 자격 없음·만료 | 갱신 후 1회 | 갱신 실패 사유, 자격 값 제외 |
| 입력 오류 | 요청 규격 불일치 | 안 함 | 문제 키 이름 |
| 일시 장애 | 시간 초과·속도 제한·5xx | ③ 횟수만큼 | 시도 횟수·간격 |
| 권한 부족 | 허용 범위 밖 | 안 함 | 요청 범위·필요 범위 |
| 분류 불가 | 나머지 실패 | 안 함 | 분류 불가 값 |

오류에는 주소·자격·요청·응답 본문 원문을 담지 않음.

## Mock과 실물 교체

`HELP_DESK_CONNECTOR_MODE=mock`이 설계 기본값임.  
Mock 클래스와 HTTP 클래스가 같은 Protocol을 구현하므로 생성 시 구현체만 교체함.

실물 전환 시 필요한 값:

| 커넥터 | 베이스 URL 환경변수 | 자격 환경변수 |
|---|---|---|
| `C-A1` | `HELP_DESK_C_A1_BASE_URL` | `HELP_DESK_C_A1_CREDENTIAL` |
| `C-A2` | `HELP_DESK_C_A2_BASE_URL` | `HELP_DESK_C_A2_CREDENTIAL` |
| `C-A3` | `HELP_DESK_C_A3_BASE_URL` | `HELP_DESK_C_A3_CREDENTIAL` |
| `C-A4` | `HELP_DESK_C_A4_BASE_URL` | `HELP_DESK_C_A4_CREDENTIAL` |
| `C-A5` | `HELP_DESK_C_A5_BASE_URL` | `HELP_DESK_C_A5_CREDENTIAL` |

`.env.example`에는 키 이름만 있고 실제 주소·자격은 없음.

## `06-workflow.md` 호출 계약

1. `RuntimeSettings.stage_budgets[stage_id]`에서 시간 상한과 재시도 횟수 획득함.
2. ⑥ 정책에서 같은 워크플로우·커넥터의 재시도 간격과 Guard 인스턴스 획득함.
3. 읽기 도구는 `call_llm`·`query_analytics`·`search_official` 중 해당 함수 호출함.
4. 쓰기 도구는 중앙 함수로 만든 중복 방지 키와 승인 표시를 함께 전달함.
5. 반환 문자열은 `response_guard`를 통과한 결과만 State에 매핑함.

워크플로우 노드 배치와 승인 판정 자체는 본 모듈 범위 밖임.

## 확인필요 목록

| # | 확인필요 항목 | 영향 | 확정 주체 |
|---:|---|---|---|
| 1 | `[확인필요: C-A1 실물 인증 방식]` | 실물 연결 전 CredentialProvider 구현 필요 | LLM 제공자·보안 담당자 |
| 2 | `[확인필요: C-A1 실물 최소권한 scope]` | 실물 권한 요청 전 제공자 scope 확인 필요 | LLM 제공자·보안 담당자 |
| 3 | `[확인필요: C-A2 실물 인증 방식]` | 실물 연결 전 CredentialProvider 구현 필요 | 분석 뷰 제공자·보안 담당자 |
| 4 | `[확인필요: C-A2 실물 최소권한 scope]` | 실물 권한 요청 전 제공자 scope 확인 필요 | 분석 뷰 제공자·보안 담당자 |
| 5 | `[확인필요: C-A3 실물 인증 방식]` | 실물 연결 전 CredentialProvider 구현 필요 | 검색 제공자·보안 담당자 |
| 6 | `[확인필요: C-A3 실물 최소권한 scope]` | 실물 권한 요청 전 제공자 scope 확인 필요 | 검색 제공자·보안 담당자 |
| 7 | `[확인필요: C-A4 실물 인증 방식]` | 실물 연결 전 CredentialProvider 구현 필요 | CRM 제공자·보안 담당자 |
| 8 | `[확인필요: C-A4 실물 최소권한 scope]` | 실물 권한 요청 전 제공자 scope 확인 필요 | CRM 제공자·보안 담당자 |
| 9 | `[확인필요: C-A5 실물 인증 방식]` | 실물 연결 전 CredentialProvider 구현 필요 | 설문 제공자·보안 담당자 |
| 10 | `[확인필요: C-A5 실물 최소권한 scope]` | 실물 권한 요청 전 제공자 scope 확인 필요 | 설문 제공자·보안 담당자 |

확인필요 10건임. Mock 검증에는 영향 없으며 실물 연결 전 전건 확정 필요함.
