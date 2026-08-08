# 공통 런타임 — 런치픽 v1.1

뒤에 오는 개발 프롬프트 8건(`02` ~ `09`)이 공통으로 가져다 쓰는 바탕임.  
상태 타입 · 예산과 마감선 · 설정 로더 · 중간 저장 장치 · 모델 어댑터로 이뤄짐.

> 여기서 만들지 않은 것 — 흐름 조립과 노드 함수(`06`), 검사·가리기·기록(`05`),  
> 바깥 시스템 실제 연결(`04`), 검색·조회(`03`). 자리(훅)와 감싸개만 남겨 둠.

---

## 1. 뒤 프롬프트가 가져다 쓰는 것

| 무엇이 필요하면 | 어디서 가져오나 |
|---------------|---------------|
| 노드가 주고받을 상태 타입 | `common.state.LunchPickState` |
| 트리거 구분 · 구독 상태 · PG 중지 상태 | `common.state.TriggerKind` · `SubscriptionState` · `PgCancelStatus` |
| 시간 제한 · 재시도 · 반복 상한 값 | `common.config.get_settings()` |
| 마감선 계산 · 남은 시간 확인 | `common.budget` |
| 바깥 호출에 상한 씌우기 | `common.external_call.call_with_limits` |
| 중간 저장 장치 · 세션 식별자 · 중복 방지 키 | `common.checkpointer` |
| 모델 부르기 | `common.model_client.build_model_client` |
| 검사·가리기·기록 끼워 넣기 | `common.guardrail_hooks.HookSet` |
| 비용 세기 | `common.cost.CostCounter` |
| 정형 조회 · 검색기 · 결정론 선행 필터 | `common.knowledge`(자세한 설명은 `knowledge/README.md`) |

**④에 `모델 미사용`으로 적힌 담당자는 모델 어댑터를 쓰지 않음.** 그 자리는 순수 함수로 둠  
(16명 중 14명이 여기 해당함 — ④ 8-2절).

---

## 2. 계약 — 이 이름들은 뒤 8건이 그대로 씀

이름을 바꾸면 뒤 8건이 전부 어긋남. 바꿀 일이 생기면 이 표를 먼저 고침.

### 2-1. 상태 필드 표 (23개)

`③ 6절` 「상태 스키마」의 필드를 하나도 빼지 않고 옮김. 필드를 새로 만들지 않았음.

| # | 필드 이름 | 타입 | 갱신 주체 | 병합 규칙 | ③ 6절 행 |
|:-:|----------|------|----------|:--------:|:--------:|
| 1 | `trigger_kind` | `TriggerKind` | 진입 노드 1개 | 없음 | 1 |
| 2 | `deadline_at` | `int`(epoch ms) | 진입 노드 1개 | 없음 | 2 |
| 3 | `precheck_result` | `dict` | 사전 조건 확인 노드 1개 | 없음 | 3 |
| 4 | `partial_context` | `list` | 컨텍스트 수집 누적 리듀서 | **이어 붙이기** | 4 |
| 5 | `context_bundle` | `dict` | `S-R10` 1개 | 없음 | 5 |
| 6 | `candidate_set` | `list` | `S-R9` 1개 | 없음 | 6 |
| 7 | `recommendation_set` | `dict` | `S-R11` 1개 | 없음 | 7 |
| 8 | `verification_result` | `dict` | `S-R12` 1개 | 없음 | 8 |
| 9 | `fallback_reason` | `str` | 착지 노드 1개 | 없음 | 9 |
| 10 | `retry_count_by_step` | `dict[str, int]` | 재시도 래퍼 | **키별 합침 · 나중 값 우선** | 10 |
| 11 | `iteration_count` | `int` | 반복 진입 노드 1개 | 없음 | 11 |
| 12 | `error_history` | `list` | 실패 기록 리듀서 | **이어 붙이기** | 12 |
| 13 | `resume_cursor` | `dict` | 커밋 노드 1개 | 없음 | 13 |
| 14 | `preference_vector_ref` | `str` | 없음 — 읽기 전용 | 없음 | 14 |
| 15 | `subscription_state` | `SubscriptionState` | 트리거별 1개 | 없음 | 15 |
| 16 | `approval_evidence` | `dict` | 승인 게이트 1개 | 없음 | 16 |
| 17 | `payment_idempotency_key` | `str` | `S-S8` 1개 | 없음 | 17 |
| 18 | `payment_result` | `dict` | `S-S9` 1개 | 없음 | 18 |
| 19 | `cancel_schedule` | `dict` | `S-C7` 1개 | 없음 | 19 |
| 20 | `disclosure_record` | `dict` | `S-S6` 1개 | 없음 | 20 |
| 21 | `insight_aggregate` | `dict` | `S-I9` 1개 | 없음 | 21 |
| 22 | `consistency_check` | `dict` | `S-I10` 1개 | 없음 | 22 |
| 23 | `pg_cancel_status` | `PgCancelStatus` | `S-C10` 1개 | 없음 | 23 |

**병합 규칙을 붙인 필드는 3개뿐임.** 붙인 근거는 ③의 「병렬 처리」 칸이  
`누적만` 또는 `키별 증가`로 적혀 병렬 노드 여럿이 같은 자리에 쓴다고 밝힌 경우임.  
나머지 20개는 갱신 주체가 1명이라 붙이지 않았음 — 붙이면 값이 쌓여 버림.

**병합 규칙이 없다는 것이 무슨 뜻인지 1줄** — 두 노드가 같은 단계에서 그 필드에 같이 쓰면  
프레임워크가 아예 막음(`InvalidUpdateError`). 값이 조용히 덮이지 않고 바로 드러남  
(시험 `test_state_in_graph.py::test_single_writer_field_refuses_two_writers_in_one_step`).

### 2-2. 값 목록

| 이름 | 값 | 출처 |
|------|----|------|
| `TriggerKind` | `S-R` `S-B` `S-E` `S-S` `S-C` `S-I` `S-X` `S-N` | ③ 3절 트리거 인스턴스 8종 |
| `TriggerFamily` | `sync_request` `scheduled_batch` `event` | ③ 판정 1-1 트리거 유형 3종 |
| `SubscriptionState` | `무료` `프리미엄` | ③ 6절 15번 |
| `PgCancelStatus` | `중지완료` `확인 중` `실패` | ③ 6절 23번 |
| `PAYMENT_RESULT_PENDING` | `확인 중` | ③ 6절 18번 |

---

## 3. 설정 값 표

| 환경변수 이름 | 필수 | 기본값 | 어느 설계서에서 왔나 |
|-------------|:----:|-------|-------------------|
| `LUNCHPICK_STEP_TIMEOUT_MS` | 예 | 없음 | ③ 4절 「타임아웃(상한)」 |
| `LUNCHPICK_STEP_RETRY_COUNT` | 예 | 없음 | ③ 4절 「재시도」 |
| `LUNCHPICK_STEP_BACKOFF_MS` | 아니오 | `{}` | ③ 4-6절 `S-C10`(1s) |
| `LUNCHPICK_STEP_RETRY_CONDITIONAL` | 아니오 | `[]` | ③ 4-1절 `S-R11` 조건부 1회 |
| `LUNCHPICK_BUDGET_TOTAL_MS` | 아니오 | `{}` | ③ 9절 대조 2줄 |
| `LUNCHPICK_BUDGET_LANDING_MS` | 아니오 | `{}` | ③ 8-1절 착지 경로 |
| `LUNCHPICK_LOOP_MAX_ITER` | 아니오 | `{}` | ③ 8-2절 `L-1` `L-2` `L-3` |
| `LUNCHPICK_COST_LIMIT_KRW_PER_REQUEST` | 아니오 | 없음 | ① 3절 단위 환산(10원/건) |
| `LUNCHPICK_LLM_PROVIDER` | 예 | 없음 | ④ 「사용 모델」 |
| `LUNCHPICK_LLM_MODEL` | 예 | 없음 | ④ 「사용 모델」 |
| `LUNCHPICK_LLM_API_KEY` | 예 | 없음 | ⑦ 비밀값 목록 |
| `LUNCHPICK_LLM_THINKING` | 아니오 | 없음 | ④ 3-1절 `R-1` — 사고 끔 |
| `LUNCHPICK_LLM_EFFORT` | 아니오 | 없음 | ④ 3-1절 `R-1` — `low` |
| `LUNCHPICK_LLM_MAX_OUTPUT_TOKENS` | 아니오 | 없음 | ④ 3-1절 `R-1` — 2,048 |
| `LUNCHPICK_LLM_BASE_URL` | 아니오 | 없음 | 개발판단(주소 교체용) |
| `LUNCHPICK_EMBEDDING_MODEL` | 아니오 | 없음 | ④ 3-3절 `R-3` — `[확인필요]` |
| `LUNCHPICK_CHECKPOINT_BACKEND` | 아니오 | `memory` | D-08 |
| `LUNCHPICK_CHECKPOINT_DB_URL` | 조건부 | 없음 | D-08 — 백엔드가 `postgres`면 필수 |
| `LUNCHPICK_CHECKPOINT_FAILURE_POLICY` | 아니오 | `fail_fast` | 개발판단 — 운영 자동 대체 금지 |
| `LUNCHPICK_CHECKPOINT_RETENTION_DAYS` | 아니오 | 없음 | D-08 — `[확인필요]` |
| `LUNCHPICK_OTLP_ENDPOINT` | 아니오 | 없음 | D-11 — `[확인필요]` |
| `LUNCHPICK_DATASET_ROW_CAP` | 조건부 | `{}` | ⑤ 3절 「정형 접근 경로」 — 데이터를 읽으려면 필수 |
| `LUNCHPICK_DATASET_SEED` | 아니오 | `0` | 개발판단(합성 시드 재현용) |
| `LUNCHPICK_DATASET_SEED_ROWS` | 아니오 | `{}` | 비우면 그 경로의 행 수 상한만큼 만듦 |
| `LUNCHPICK_DATASET_SOURCE_DB_URL` | 아니오 | 없음 | ⑦ 비밀값 `K-02` — 값은 도구 연동·배포 몫 |
| `LUNCHPICK_DATASET_VECTOR_INDEX_URL` | 아니오 | 없음 | ⑦ 비밀값 `K-05` — `[확인필요]` |
| `LUNCHPICK_DATASET_CACHE_URL` | 아니오 | 없음 | ⑦ 비밀값 `K-06` — `[확인필요]` |
| `LUNCHPICK_DATASET_PHYSICAL_QUERY` | 아니오 | `{}` | ⑤ 14절 `[확인필요: DBMS 제품명·물리 스키마]` |
| `LUNCHPICK_DATASET_SNAPSHOT_DIR` | 아니오 | 패키지 안 폴더 | 개발판단 |
| `LUNCHPICK_DATASET_SNAPSHOT_RETENTION_DAYS` | 아니오 | `{}` | ⑤ 7절 「보존·삭제」 |
| `LUNCHPICK_DATASET_QUALITY_THRESHOLD` | 아니오 | `{}` | ⑤에 원천 품질 문턱이 없어 비어 있음 |
| `LUNCHPICK_DATASET_GLOSSARY_DIR` | 아니오 | 패키지 안 폴더 | ⑤ 14절 `[확인필요: 용어사전 파일 위치…]` |
| `LUNCHPICK_KNOWLEDGE_INDEX_NAME` | 조건부 | `{}` | ⑤ 5절 K-1 「인덱스명」 |
| `LUNCHPICK_KNOWLEDGE_INDEX_BUILD_SUFFIX` | 아니오 | 없음 | 되묻기 — 색인 재생성 절차 |
| `LUNCHPICK_KNOWLEDGE_CORPUS_SCOPE` | 아니오 | 없음 | ⑤ 5절 K-1 「대상 범위」 |
| `LUNCHPICK_KNOWLEDGE_CORPUS_AS_OF` | 아니오 | 없음 | ⑤ 5절 K-1 「기준일」 — `[확인필요]` |
| `LUNCHPICK_KNOWLEDGE_CHUNKING` | 아니오 | 없음 | ⑤ 5절 K-1 — 값이 「해당 없음」임 |
| `LUNCHPICK_KNOWLEDGE_EMBEDDING_MODEL_VERSION` | 아니오 | 없음 | ⑤ 5절 K-1 — `[확인필요]` |
| `LUNCHPICK_KNOWLEDGE_VECTOR_INDEX_PRODUCT` | 아니오 | 없음 | ⑤ 14절 — `[확인필요]` |
| `LUNCHPICK_KNOWLEDGE_SEARCH_MODE` | 아니오 | 없음 | ⑤ 5절 K-1 「검색 방식」 |
| `LUNCHPICK_KNOWLEDGE_TOP_K` | 조건부 | 없음 | ⑤ 5절 K-1 「top-k」 |
| `LUNCHPICK_KNOWLEDGE_RERANK_ENABLED` | 아니오 | 없음 | ⑤ 5절 K-1 「리랭킹 여부」 |
| `LUNCHPICK_KNOWLEDGE_RERANK_WEIGHTS` | 아니오 | `{}` | ⑤에 값 없음 — `[확인필요]` |
| `LUNCHPICK_KNOWLEDGE_RERANK_KEEP` | 아니오 | 없음 | ⑤ 5절 K-1 최종 건수 |
| `LUNCHPICK_KNOWLEDGE_METADATA_FILTER_KEYS` | 조건부 | `()` | ⑤ 5절 K-1(이름 주인은 ④ 5-3절) |
| `LUNCHPICK_KNOWLEDGE_ATTRIBUTE_AXES` | 조건부 | `{}` | ⑤ 5절 K-2 「필터 축」·「성립 여부」 |
| `LUNCHPICK_KNOWLEDGE_RADIUS_M` | 아니오 | 없음 | ⑤ 5절 K-2 거리 축 |
| `LUNCHPICK_KNOWLEDGE_SORT_PRIMARY` | 아니오 | 없음 | ⑤ 5절 K-2 「정렬 기준」 |
| `LUNCHPICK_KNOWLEDGE_GLOSSARY_APPLY_POINTS` | 아니오 | `{}` | ⑤ 5절 K-3 「적용 지점」 |
| `LUNCHPICK_KNOWLEDGE_QUERY_EXPANSION_ENABLED` | 아니오 | 없음 | ⑤ 5절 K-3 ⓐ |
| `LUNCHPICK_KNOWLEDGE_RESULT_MERGE` | 아니오 | 없음 | 되묻기 — 경로별로 따로 돌려줌 |
| `LUNCHPICK_KNOWLEDGE_RESULT_CACHE_TTL_S` | 아니오 | 없음 | 되묻기 — 저장하지 않음 |
| `LUNCHPICK_KNOWLEDGE_LOW_CONFIDENCE_SIGNAL` | 아니오 | 없음 | 되묻기 — 후보 수 0건을 신호로 씀 |

**`LUNCHPICK_DATASET_*` 12행은 데이터 준비 프롬프트(`02-dataset.md`)가 뒤에 더한 것임** —
`01-runtime`이 정한 이름은 하나도 바꾸지 않았음. 자세한 설명은
`dataset/README.md`에 있음.

**`LUNCHPICK_KNOWLEDGE_*` 21행은 지식 경로 프롬프트(`03-knowledge.md`)가 뒤에 더한 것임** —
`01-runtime`과 `02-dataset`이 정한 이름은 하나도 바꾸지 않았음(임베딩 모델 이름은
`LUNCHPICK_EMBEDDING_MODEL`을 그대로 씀). 자세한 설명은 `knowledge/README.md`에 있음.

**필수 값이 없으면 프로그램이 뜨는 시점에 실패함.** 서비스 진입점에서 `load_settings()`를  
가장 먼저 부름. 값 확인만 하려면 `python -m common.config`를 돌림.

**`LUNCHPICK_STEP_TIMEOUT_MS`와 `LUNCHPICK_STEP_RETRY_COUNT`에 채울 값** — ③ 4절 표에서
그대로 옮김. 값을 이 저장소에 박지 않으므로 아래를 보고 각자 `.env`에 채움.

| 트리거 | ③ 절 | `[확인필요]`로 비워 둘 단계 |
|-------|------|------------------------|
| `S-R` 오늘의 추천 | 4-1 | `S-R1` `S-R14`(단말 구간 · 예산 밖) |
| `S-B` 일일 취향 학습 | 4-2 | 없음 |
| `S-E` 앞 단계 완료 신호 | 4-3 | 없음 |
| `S-S` 구독 전환 | 4-5 | `S-S1` `S-S7`(사람 대기) `S-S9`(PG SLA) |
| `S-C` 구독 해지 | 4-6 | `S-C1` `S-C5`(사람 대기) `S-C10`(PG SLA) |
| `S-N` 구독 전파 | 4-7 | 없음 |
| `S-X` 만료 전환 | 4-8 | 없음 |
| `S-I` 인사이트 조회 | 4-9 | `S-I1` |

---

## 4. 가상환경 만들기와 실행

의존성은 `pyproject.toml`에 `==`로 정확히 고정돼 있음(확인일 2026-08-08).

### Windows PowerShell

```powershell
cd output\src\v1.1\common
uv venv --python 3.12
.venv\Scripts\Activate.ps1
uv sync --extra dev
python -m pytest
```

### Windows GitBash

```bash
cd output/src/v1.1/common
uv venv --python 3.12
source .venv/Scripts/activate
uv sync --extra dev
python -m pytest
```

### Linux / macOS

```bash
cd output/src/v1.1/common
uv venv --python 3.12
source .venv/bin/activate
uv sync --extra dev
python -m pytest
```

바깥을 실제로 부르는 시험은 기본 실행에서 빠져 있음. 돌리려면 `python -m pytest -m live_call`.

**`common`을 임포트하는 기준 경로는 `output/src/v1.1`임.** 시험은 pytest가 그 경로를 알아서 넣어 주고,
직접 만든 스크립트를 돌릴 때는 `output/src/v1.1`에서 돌리거나 `PYTHONPATH`에 그 경로를 넣음.

**Windows에서 중간 저장 장치를 데이터베이스로 쓸 때 반드시 할 일** — 프로세스가 뜰 때
`common.runtime.configure_event_loop_for_async_db()`를 **이벤트 루프를 만들기 전에** 부름.
안 부르면 비동기 데이터베이스 드라이버가 Windows 기본 루프에서 돌지 않고
`psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop'`로 멈춤(실제 실행으로 확인함).

```python
from common.runtime import configure_event_loop_for_async_db

configure_event_loop_for_async_db()
asyncio.run(main())
```

---

## 5. 디렉터리 구조와 파일별 설명

```
output/src/v1.1/common/
├── __init__.py              뒤 프롬프트가 쓸 이름을 한곳에 모아 내보냄
├── state.py                 상태 타입 23필드 · 병합 규칙 3개 · 값 목록. 흐름 코드 없음
├── config.py                설정 로더. 필수 값이 없으면 뜨는 시점에 실패
├── budget.py                마감선 산정 · 최악값 합계 · 남은 시간 확인 · 조건부 재시도 판정
├── external_call.py         바깥 호출에 시간 제한·재시도·백오프를 씌우는 감싸개
├── checkpointer.py          중간 저장 장치 · 세션 식별자 · 중복 방지 키 저장 자리
├── model_client.py          모델 어댑터 고르는 자리. 벤더·모델 이름이 여기 없음
├── model_adapters/
│   └── anthropic_adapter.py 벤더 하나의 인자 차이를 흡수함
├── knowledge/               지식 경로 — 조회 계층·검색기·결정론 선행 필터(03-knowledge 산출물)
├── guardrail_hooks.py       검사·가리기·기록이 끼어들 자리(훅)만
├── cost.py                  비용 카운터 자리. 실제로 세는 코드는 05 몫
├── runtime.py               뜰 때 한 번 하는 준비(비동기 DB용 이벤트 루프)
├── units.py                 단위 환산만. 설계서 값은 없음
├── pyproject.toml           의존성(== 고정) · pytest 설정 · `live_call` 표식
├── .env.example             비밀값 예시. 키 이름만
└── tests/                   단위 시험
```

---

## 6. 되묻기로 정한 값 — 설계서에 되돌려 적을 것

이번 판은 사용자 승인으로 **기본값으로 진행**했음. 아래를 설계서에 되돌려 적어야 함.

| # | 무엇을 | 무엇으로 정했나 | 어디에 되돌려 적나 |
|:-:|-------|---------------|-----------------|
| 1 | 세션 식별자 조립 규칙 | `{회원ID}:{워크플로우명}:{요청일시(UTC 초 단위)}` | `개발환경정보.md` D-08 (이미 그 값임 · 확정 표시만 필요) |
| 2 | 목록형 필드 병합 방식 | 이어 붙이기 — `partial_context` `error_history` | **③ 6절** 4번·12번 「병렬 처리」 칸 |
| 3 | 값형 필드 병합 방식 | 키별로 합치고 같은 키는 나중 값 우선 — `retry_count_by_step` | **③ 6절** 10번 「병렬 처리」 칸 |
| 4 | 비용 상한 단위 | 요청 1건당 | ① 3절(이미 10원/건 · 정본만 확정 필요) |

병합 방식의 주인은 ③이므로 **③에 위 2·3번을 적어 두어야** 다음 판에서 어긋나지 않음.

---

## 7. `[확인필요]` 목록 — 8건

값이 없어 자리만 만들어 둔 것임. 값이 오면 환경변수만 채우면 됨(코드 수정 없음).

| # | `[확인필요]` 항목 | 어느 설정이 비어 있나 | 누구에게 되묻나 |
|:-:|-----------------|-------------------|---------------|
| 1 | 체크포인트 보관 기간 | `LUNCHPICK_CHECKPOINT_RETENTION_DAYS` | 사용자 (D-08) |
| 2 | 동기 요청 응답 마감선(게이트웨이·클라이언트 타임아웃) | `LUNCHPICK_STEP_TIMEOUT_MS`의 `S-R1` `S-R14` `S-S1` `S-C1` `S-I1` | ⑦ 배포 |
| 3 | 결제·해지 사람 승인 대기의 유효 시간 | `LUNCHPICK_STEP_TIMEOUT_MS`의 `S-S7` `S-C5` | 기획 담당 |
| 4 | PG 등록·중지 호출의 응답 타임아웃(PG SLA) | `LUNCHPICK_STEP_TIMEOUT_MS`의 `S-S9` `S-C10` | 커넥니 (⑤) |
| 5 | 루프 반복 상한 `L-1` `L-2` `L-3` | `LUNCHPICK_LOOP_MAX_ITER` | 기획 담당 (③ 8-2절) |
| 6 | 건당 단가 정본 | `LUNCHPICK_COST_LIMIT_KRW_PER_REQUEST` | 기획 담당 (① 3절) |
| 7 | 취향 임베딩 모델 이름·버전 | `LUNCHPICK_EMBEDDING_MODEL` | 지식니 (⑤ 14절) |
| 8 | 관측 백엔드 제품 | `LUNCHPICK_OTLP_ENDPOINT` | 사용자 (D-11) |

---

## 8. 확인하지 않은 것 (정직한 보고)

### PostgreSQL 실패 정책

- 기본값 `fail_fast` — 연결 또는 최초 `setup()` 실패 시 `CheckpointUnavailable` 발생,
  메모리 저장소로 자동 전환하지 않음
- 개발용 명시 선택 `memory_fallback_for_development` — PostgreSQL을 요청했으나 열지 못하면
  `InMemorySaver`로 대체하고 `CheckpointerHandle.degraded = True` 및 `fallback_reason` 기록
- `AsyncPostgresSaver.setup()`은 테이블 준비를 위해 프로세스 시작 시 호출함. 운영 데이터베이스 연결 시험은
  `@pytest.mark.live_call`로 분리함
- 호출 설정은 `invocation_config()`로 조립함. `thread_id`·`checkpoint_id`는 `configurable` 아래,
  `recursion_limit`은 최상위에 둠

- **`AsyncPostgresSaver`를 실제 데이터베이스에 붙여 확인하지 못했음.** 이 개발 환경에
  Docker 데몬이 떠 있지 않고 PostgreSQL도 없음. 확인한 것은 여기까지임 —
  임포트 경로 · `from_conn_string` 인자 · `setup()`이 코루틴임(설치된 패키지에서 직접 확인),
  그리고 설정 → `open_checkpointer` → 드라이버 연결 시도까지 코드가 실제로 흐른다는 것
  (닫힌 포트로 `psycopg.errors.ConnectionTimeout`까지 도달). **`setup()`이 표를 만드는 것은
  확인하지 못했음.**
- 단위 시험이 통과하는 경로는 `memory` 백엔드임. `postgres` 백엔드 시험은
  `@pytest.mark.live_call`로 갈라 두었고 이번 실행에서 제외됨(1건).
- 모델 API를 실제로 부르지 않았음. 어댑터 시험은 전부 대역임.
