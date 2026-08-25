# Help Desk 공통 런타임

## 개요

세 워크플로우가 공유하는 State 타입, 시간예산, 설정 로더, Checkpointer 어댑터,
모델 클라이언트 어댑터 제공 모듈임.  
뒤 개발 프롬프트는 `help_desk_runtime`의 공개 이름을 그대로 가져다 쓰는 구조임.

흐름 조립과 노드 함수, 검사 훅, 실제 커넥터는 포함하지 않음.  
결정론적 담당자와 사람 담당자는 모델 어댑터를 사용하지 않고  
순수 함수로 구현하는 기준임.

## 가상환경 만들기와 시험 실행

### Windows GitBash

```bash
cd src/common
uv sync --group dev
uv run pytest
```

### Windows PowerShell

```powershell
Set-Location src/common
uv sync --group dev
uv run pytest
```

### Linux 또는 Mac

```bash
cd src/common
uv sync --group dev
uv run pytest
```

실행 전 `.env.example`을 `.env`로 복사하고 필수 값을 채우는 방식임.  
실제 외부 시스템 시험은 `pytest -m live_call`로 분리하는 규칙임.

## 상태 필드

| 필드 이름 | 타입 | 쓰는 단계 | 병합 규칙 | 출처 |
|---|---|---|---|---|
| `request_id` | `str` | `S-R1` | 없음 | ③ `W-1` State 1행 |
| `auth_session_ref` | `str` | `S-R1` | 없음 | ③ `W-1` State 2행 |
| `customer_ref` | `str` | `S-R1` | 없음 | ③ `W-1` State 3행 |
| `safe_inquiry_text` | `str` | `S-R1` | 없음 | ③ `W-1` State 4행 |
| `route_decision` | `Literal` | `S-R2` | 없음 | ③ `W-1` State 5행 |
| `sql_candidate` | `str` | `S-R3` | 없음 | ③ `W-1` State 6행 |
| `evidence_refs` | `list[str]` | `S-R5` | 없음 | ③ `W-1` State 7행 |
| `risk_result` | `dict` | `S-R7` | 없음 | ③ `W-1` State 8행 |
| `answer_draft` | `dict` | `S-R8` | 없음 | ③ `W-1` State 9행 |
| `approval_result` | `dict` | `S-R9`, 사람 | 나중 값 우선 키 병합 | ③ `W-1` State 10행 |
| `batch_id` | `str` | `S-B1` | 없음 | ③ `W-2` State 1행 |
| `batch_date` | `date` | `S-B1` | 없음 | ③ `W-2` State 2행 |
| `masked_consultation_refs` | `list[str]` | `S-B2` | 없음 | ③ `W-2` State 3행 |
| `sql_candidate` | `str` | `S-B3` | 없음 | ③ `W-2` State 4행 |
| `topic_evidence` | `list[dict]` | `S-B5` | 없음 | ③ `W-2` State 5행 |
| `priority_result` | `list[dict]` | `S-B7` | 없음 | ③ `W-2` State 6행 |
| `faq_candidates` | `list[dict]` | `S-B8` | 없음 | ③ `W-2` State 7행 |
| `review_decision` | `dict` | `S-B9`, 사람 | 나중 값 우선 키 병합 | ③ `W-2` State 8행 |
| `registration_result` | `dict` | `S-B10` | 없음 | ③ `W-2` State 9행 |
| `event_id` | `str` | `S-E1` | 없음 | ③ `W-3` State 1행 |
| `consultation_ref` | `str` | `S-E1` | 없음 | ③ `W-3` State 2행 |
| `masked_transcript` | `str` | `S-E2` | 없음 | ③ `W-3` State 3행 |
| `summary_draft` | `dict` | `S-E3` | 없음 | ③ `W-3` State 4행 |
| `risk_result` | `dict` | `S-E4` | 없음 | ③ `W-3` State 5행 |
| `review_decision` | `dict` | `S-E5`, 사람 | 나중 값 우선 키 병합 | ③ `W-3` State 6행 |
| `crm_result` | `dict` | `S-E6` | 없음 | ③ `W-3` State 7행 |
| `survey_consent_ref` | `str` | `S-E1` | 없음 | ③ `W-3` State 8행 |
| `survey_result` | `dict` | `S-E7` | 없음 | ③ `W-3` State 9행 |

복수 쓰기인 객체 필드는 키 단위로 합치며 같은 키는 나중 값 우선 적용임.  
이 병합 방식은 값의 주인인 ③ 「State 구조」에 되돌려 적을 권고 사항임.

## 시간예산과 마감선

각 단계의 `HELP_DESK_{단계}_TIMEOUT_MS`와 `HELP_DESK_{단계}_RETRY_COUNT`는 필수 설정임.  
값은 ③ 「단계별 설계」의 27개 행에서 그대로 입력해야 함.  
`calculate_worst_case_ms`는 직렬 합과 병렬 그룹 최댓값을 계산함.  
③ 대조 결과는 W-1 609,300ms, W-2 12,960,000ms, W-3 58,000ms임.

`RuntimeDeadline`은 요청 진입 시 한 번 생성하는 마감선임.  
각 노드는 `ensure_stage_can_start` 호출 후에만 실제 일을 시작하는 계약임.  
`ModelCallCounter`는 호출 횟수 자리만 제공하며 실제 증가는 가드레일 모듈의 책임임.

## 설정 값

| 환경변수 이름 | 필수 | 기본값 | 출처 |
|---|:---:|---|---|
| `HELP_DESK_LLM_PROVIDER` | 예 | 없음 | ④ 사용 모델, 제품 미확정 |
| `HELP_DESK_LLM_MODEL` | 예 | 없음 | ④ 사용 모델, 제품 미확정 |
| `HELP_DESK_LLM_API_KEY` | 예 | 없음 | D-10 비밀값 주입 |
| `HELP_DESK_LLM_REASONING_ENABLED` | 아니오 | `true` | ④ 사용 모델의 사고 켬 |
| `HELP_DESK_LLM_TEMPERATURE` | 아니오 | 벤더 기본값 | ④ 설계 범위 밖 조절값 |
| `HELP_DESK_LLM_MAX_TOKENS` | 아니오 | 벤더 기본값 | ④ 설계 범위 밖 조절값 |
| `HELP_DESK_CHECKPOINT_BACKEND` | 아니오 | `sqlite` | D-08 |
| `HELP_DESK_CHECKPOINT_URI` | 예 | 없음 | D-08, 파일 위치는 실행 환경 소유 |
| `HELP_DESK_CHECKPOINT_ENCRYPTION_KEY` | 예 | 없음 | ⑤ 민감 State 암호화 판정 |
| `HELP_DESK_CHECKPOINT_W1_RETENTION_MS` | 예 | 없음 | ⑤ 체크포인트 보존·삭제 |
| `HELP_DESK_CHECKPOINT_W2_RETENTION_MS` | 예 | 없음 | ⑤ 체크포인트 보존·삭제 |
| `HELP_DESK_CHECKPOINT_W3_RETENTION_MS` | 예 | 없음 | ⑤ 체크포인트 보존·삭제 |
| `HELP_DESK_ANALYTICS_BASE_URL` | 아니오 | 없음 | 순서2 키 정의, 값은 순서4 소유 |
| `HELP_DESK_ANALYTICS_TIMEOUT_SECONDS` | 아니오 | 없음 | 순서2 키 정의, 값은 순서4 소유 |
| `HELP_DESK_DATASET_S_R4_MAX_ROWS` | 아니오 | 100 | ⑤ 정형 접근 경로 |
| `HELP_DESK_DATASET_S_B2_MAX_ROWS` | 아니오 | 10,000 | ⑤ 정형 접근 경로 |
| `HELP_DESK_DATASET_S_B4_MAX_ROWS` | 아니오 | 100 | ⑤ 정형 접근 경로 |
| `HELP_DESK_DATASET_SEED` | 아니오 | 20260825 | 순서2 사용자 승인 추천값 |
| `HELP_DESK_DATASET_S_R4_SEED_ROWS` | 아니오 | 100 | 순서2 사용자 승인 추천값 |
| `HELP_DESK_DATASET_S_B2_SEED_ROWS` | 아니오 | 10,000 | 순서2 사용자 승인 추천값 |
| `HELP_DESK_DATASET_S_B4_SEED_ROWS` | 아니오 | 100 | 순서2 사용자 승인 추천값 |
| `HELP_DESK_DATASET_SNAPSHOT_DIR` | 아니오 | 없음 | 순서2 실행 환경 소유 |
| `HELP_DESK_GLOSSARY_POSTGRES_DSN` | 아니오 | 없음 | 순서2 키 정의, 값은 순서4 소유 |
| `HELP_DESK_W1_TOTAL_BUDGET_MS` | 예 | 없음 | ③ W-1 총 시간예산 |
| `HELP_DESK_W2_TOTAL_BUDGET_MS` | 예 | 없음 | ③ W-2 총 시간예산 |
| `HELP_DESK_W3_TOTAL_BUDGET_MS` | 예 | 없음 | ③ W-3 총 시간예산 |
| `HELP_DESK_S_R1_TIMEOUT_MS` ~ `HELP_DESK_S_R10_TIMEOUT_MS` | 예 | 없음 | ③ W-1 단계별 설계 |
| `HELP_DESK_S_R1_RETRY_COUNT` ~ `HELP_DESK_S_R10_RETRY_COUNT` | 예 | 없음 | ③ W-1 단계별 설계 |
| `HELP_DESK_S_B1_TIMEOUT_MS` ~ `HELP_DESK_S_B10_TIMEOUT_MS` | 예 | 없음 | ③ W-2 단계별 설계 |
| `HELP_DESK_S_B1_RETRY_COUNT` ~ `HELP_DESK_S_B10_RETRY_COUNT` | 예 | 없음 | ③ W-2 단계별 설계 |
| `HELP_DESK_S_E1_TIMEOUT_MS` ~ `HELP_DESK_S_E7_TIMEOUT_MS` | 예 | 없음 | ③ W-3 단계별 설계 |
| `HELP_DESK_S_E1_RETRY_COUNT` ~ `HELP_DESK_S_E7_RETRY_COUNT` | 예 | 없음 | ③ W-3 단계별 설계 |

필수 설정은 `RuntimeSettings` 생성 시 검증됨.  
모델 벤더, 모델 이름, API 키, 암호화 키는 소스와 예시 파일에 실제 값을 기록하지 않음.

## Checkpointer

개발 시 `memory`, 운영 기본값은 D-08의 `sqlite` 선택 가능 구조임.  
`create_checkpointer`가 `InMemorySaver`와 `AsyncSqliteSaver`의 차이를 흡수함.  
SQLite 스키마 준비는 사용자가 승인한 값에 따라 배포 절차에서 선행 1회 수행함.

세션 키는 설계 순서의 성분을 콜론으로 연결함.

| 워크플로우 | 조립 문법 |
|---|---|
| W-1 | `W-1:{customer_ref}:{request_id}` |
| W-2 | `W-2:{batch_date}:{data_version}` |
| W-3 | `W-3:{event_id}:{job_type}` |

⑤ 판정에 따라 W-1의 `auth_session_ref`, `safe_inquiry_text`와 W-3의
`masked_transcript`는 체크포인트에서 제외함.  
나머지 지정 민감 필드는 저장 전 암호화 어댑터를 거침.  
LangGraph SQLite Checkpointer 자체에 업무 보관 기간을 맡기지 않음.  
완료 즉시 삭제와 W-1 600,000ms, W-2 3,600,000ms, W-3 60,000ms 만료 작업은
`08-deploy.md` 단계에서 생성해야 함.

## 모델 클라이언트 어댑터

`ModelClientAdapter`는 LangChain `init_chat_model`을 한 겹 감싼 구조임.  
벤더, 모델, 인증 키, 사고 사용 여부, 온도, 출력 토큰 상한을 설정으로 전달함.  
R-L1만 이 어댑터를 사용하며 모델 미사용 담당자는 순수 함수만 사용함.

## 같은 프로세스 단계 전달 키 규칙

State와 프로세스 API에 없는 단계 내부 전달값은  
행동 1개를 소문자 밑줄 표기로 바꾼 접두와
값 이름을 밑줄로 연결함.  
예시는 `sql_검사와_읽기_전용_실행_query_result` 형식이며 상태에 올리지 않는 값임.

## 디렉터리 구조

```text
src/common/
  .env.example
  README.md
  pyproject.toml
  help_desk_runtime/
    __init__.py
    api_contracts.py
    budget.py
    checkpoint.py
    model.py
    settings.py
    state.py
  tests/
    test_budget.py
    test_checkpoint.py
    test_model.py
    test_settings.py
    test_state.py
```

`state.py`는 State 타입과 복수 쓰기 병합 함수 소유 파일임.  
`api_contracts.py`는 ③의 프로세스 API 요청·응답 키 타입 소유 파일임.  
`budget.py`는 시간예산과 마감선, 호출 횟수 자리 소유 파일임.  
`settings.py`는 환경변수 검증 소유 파일임.  
`checkpoint.py`는 세션 키, 민감 필드 처리, 멱등 자리, 저장소 교체 소유 파일임.  
`model.py`는 모델 초기화 인자 차이 흡수 파일임.

## 되묻기로 정한 값 목록

| 항목 | 정한 값 | 되돌려 적을 곳 |
|---|---|---|
| 세션 키 문법 | 설계 성분 순서대로 콜론 연결 | D-08 반영 완료 |
| 복수 쓰기 병합 | 목록형 이어 붙이기, 값형 나중 값 우선 | ③ State 구조 반영 권고 |
| 예산 단위 | W-1 요청 1건, W-2 실행 1회, W-3 이벤트 1건 | ③ 트리거 유형과 일치 |
| 스키마 준비 | 배포 절차 선행 1회 | 설계 범위 밖, 본 README 기록 |
| 단계 전달 키 | 행동 1개 접두와 값 이름의 소문자 밑줄 표기 | 본 README 기록 |

## 확인필요 목록

| 확인필요 항목 | 영향 | 확정 주체 |
|---|---|---|
| `[확인필요: LLM 벤더]` | `HELP_DESK_LLM_PROVIDER` 설정 전 모델 클라이언트 생성 불가 | 프로젝트 운영자 |
| `[확인필요: LLM 모델 이름]` | `HELP_DESK_LLM_MODEL` 설정 전 모델 클라이언트 생성 불가 | 프로젝트 운영자 |

확인필요 2건임.
