# Help Desk 데이터 준비

## 개요

정형 조회 3경로의 읽기 전용 접속 계층, 재현 가능한 합성 고정 응답, 카드업무용어 원본,
PostgreSQL 적재 수단, 원천 품질 리포트 제공 모듈임.  
`03-knowledge.md`는 읽기 함수와 용어 정규화 함수를 사용함.  
`09-eval.md`는 `config/reports/source_quality.md`의 합성 데이터 기준선을 사용함.

모든 원천은 기획 원문에서 존재가 확인되었으나 ② 신뢰경계표에서  
`Yes(Mock)`으로 확정됨. 따라서 접속 계층과 경로별 합성 고정 응답을 함께 제공함.  
실제 원천 접속 정보는 설정 키만 정의함.

## 적용 판정

| 경로 이름 | 원천 | 확보 판정 | 실물·대역 | 행 수 상한 | 출처 |
|---|---|---|---|---:|---|
| `S-R4` | `masked_transaction_analysis_v` | 확보 | 대역 | 100 | ⑤ 정형 접근 경로 1행, ② 신뢰경계표 |
| `S-B2` | `masked_consultation_analysis_v` | 확보 | 대역 | 10,000 | ⑤ 정형 접근 경로 2행, ② 신뢰경계표 |
| `S-B4` | `masked_consultation_analysis_v` | 확보 | 대역 | 100 | ⑤ 정형 접근 경로 3행, ② 신뢰경계표 |

합성 시드 건수는 각 경로의 행 수 상한과 같은 100건, 10,000건, 100건으로 추천·확정함.  
상한 경계 시험이 가능하고 전체 10,200건이 로컬 시험에서 부담이 낮다는 근거임.  
난수 씨앗은 `20260825`로 고정함. 같은 설정이면 같은 데이터가 생성됨.

## 가상환경 만들기와 실행

환경 예시의 비밀값과 접속값은 실제 값으로 별도 주입해야 함.  
합성 데이터 생성에는 분석 API와  
PostgreSQL 접속값이 필요하지 않음.

### Windows GitBash

```bash
cd src/services/p2-knowledge-improvement-batch
export HELP_DESK_LLM_PROVIDER=local
export HELP_DESK_LLM_MODEL=unused
export HELP_DESK_LLM_API_KEY=unused
export HELP_DESK_CHECKPOINT_URI=unused
export HELP_DESK_CHECKPOINT_ENCRYPTION_KEY=unused
uv sync --group dev
uv run python scripts/prepare_dataset.py
uv run pytest
```

### Windows PowerShell

```powershell
Set-Location src/services/p2-knowledge-improvement-batch
$env:HELP_DESK_LLM_PROVIDER="local"
$env:HELP_DESK_LLM_MODEL="unused"
$env:HELP_DESK_LLM_API_KEY="unused"
$env:HELP_DESK_CHECKPOINT_URI="unused"
$env:HELP_DESK_CHECKPOINT_ENCRYPTION_KEY="unused"
uv sync --group dev
uv run python scripts/prepare_dataset.py
uv run pytest
```

### Linux 또는 Mac

```bash
cd src/services/p2-knowledge-improvement-batch
export HELP_DESK_LLM_PROVIDER=local
export HELP_DESK_LLM_MODEL=unused
export HELP_DESK_LLM_API_KEY=unused
export HELP_DESK_CHECKPOINT_URI=unused
export HELP_DESK_CHECKPOINT_ENCRYPTION_KEY=unused
uv sync --group dev
uv run python scripts/prepare_dataset.py
uv run pytest
```

PostgreSQL 용어사전 적재는 `HELP_DESK_GLOSSARY_POSTGRES_DSN`을 비밀값 주입 수단으로 설정한 뒤  
아래 명령을 별도로 실행함. 승인 세대 ID는 지식 운영자가 확정한 값을 전달함.

```bash
uv run python scripts/load_glossary.py \
  config/glossaries/카드업무용어.toml \
  --generation-id <승인세대ID>
```

## 설정 키

| 설정 키 | 의미 | 값의 주인 |
|---|---|---|
| `HELP_DESK_ANALYTICS_BASE_URL` | 분석 뷰 REST 기본 주소 | `04-connector.md` |
| `HELP_DESK_ANALYTICS_TIMEOUT_SECONDS` | REST 접속 제한 시간 | `04-connector.md` |
| `HELP_DESK_DATASET_S_R4_MAX_ROWS` | `S-R4` 호출당 상한 | ⑤ 정형 접근 경로 |
| `HELP_DESK_DATASET_S_B2_MAX_ROWS` | `S-B2` 호출당 상한 | ⑤ 정형 접근 경로 |
| `HELP_DESK_DATASET_S_B4_MAX_ROWS` | `S-B4` 호출당 상한 | ⑤ 정형 접근 경로 |
| `HELP_DESK_DATASET_SEED` | 합성 난수 씨앗 | 순서2 되묻기 |
| `HELP_DESK_DATASET_*_SEED_ROWS` | 경로별 합성 건수 | 순서2 되묻기 |
| `HELP_DESK_DATASET_SNAPSHOT_DIR` | 실행 시각 스냅샷 위치 | 배포 환경 |
| `HELP_DESK_GLOSSARY_POSTGRES_DSN` | 용어사전 접속 비밀값 | `04-connector.md` |

## 품질 리포트 읽는 법

| 항목 | 의미 |
|---|---|
| 행 수 | 해당 고정 응답에서 실제로 센 행 개수 |
| 빈 값 비율 | 열별 빈 값 행 수를 전체 행 수로 나눈 값 |
| 중복 비율 | 경로 열쇠 값의 중복 발생 행 비율 |
| 형식 어긋남 | 열 집합 또는 날짜·숫자 형식이 설계와 다른 행 수 |
| 실측 오류율 | 빈 값·중복·형식 오류 중 하나 이상인 행 비율 |
| 갱신 지연 | 캐시 경로의 원본 시각과 캐시 시각 차이 |

이번 3경로는 외부검색 캐시 경로가 아니므로 갱신 지연은 `해당 없음`임.  
품질 문턱은 설정하지 않고 관찰값만 기록함.  
실제 원천 전환 후 같은 측정기로 다시 측정해야 함.

## 디렉터리 구조

```text
p2-knowledge-improvement-batch/
  config/
    glossaries/카드업무용어.toml
    mock_responses/*_mock_response.json
    reports/source_quality.md
  help_desk_dataset/
    glossary.py
    quality.py
    seed.py
    snapshot.py
    source.py
  scripts/
    load_glossary.py
    prepare_dataset.py
  tests/
  pyproject.toml
  README.md
```

`source.py`는 읽기 전용 REST 호출과 SQL AST 검사 소유 파일임.  
`seed.py`는 경로별 합성 고정 응답 생성 소유 파일임.  
`snapshot.py`는 실행 시각이 포함된 스냅샷 파일 생성 소유 파일임.  
`glossary.py`는 원문과 대표어를 함께 반환하는 정규화 함수 소유 파일임.  
`quality.py`는 직접 센 품질값과 측정 방법·측정일 생성 소유 파일임.

## 보존 자리

두 분석 뷰의 조회 결과 보존 기간은 0일임.  
요청 또는 배치 종료 즉시 스냅샷 파기 작업이 필요함.  
이 모듈은 실행 시각 기준 스냅샷 생성 함수만 제공함.  
실제 파기 작업은 `08-deploy.md`에서 생성함.

## 되묻기로 정한 값 목록

| 항목 | 정한 값 | 되돌려 적을 곳 |
|---|---|---|
| 원천 품질 처리 | 먼저 재고 리포트를 낸 뒤 진행 | ⑤ 별도 품질 튜닝 기록 권고 |
| 품질 문턱 | 문턱 없이 관찰값만 냄 | ⑤ 별도 품질 튜닝 기록 권고 |
| 스냅샷 기준 시점 | 실행 시각 | ⑤ 보존·삭제 운영 기록 권고 |
| 합성 시드 건수 | `S-R4` 100, `S-B2` 10,000, `S-B4` 100 | ⑤ Mock 운영 기록 권고 |
| 난수 씨앗 | `20260825` 고정 | ⑤ Mock 운영 기록 권고 |
| 용어 매핑 | TOML 원본 1벌과 PostgreSQL 적재 수단 | ⑤ 용어사전 운영 스펙 보완 권고 |
| 미등록어 처리 | 보류큐 적재 | ⑤ 용어사전 운영 스펙 확정값 |

## 확인필요 목록

| 확인필요 항목 | 영향 | 확정 주체 |
|---|---|---|
| `[확인필요: 승인 문서 원천 건수]` | 후속 문서 색인 방식 판정 | 지식 운영자 |
| `[확인필요: 승인 문서 기준일]` | 후속 재색인 증감·근거 버전 대조 | 지식 운영자 |

확인필요 2건임.

## 지식 경로 구현

### 채택 경로

| 경로 이름 | 채택·미채택 | 구현 또는 재사용 | ⑤ 출처 |
|---|---|---|---|
| 정형 조회 | 채택 | `KnowledgeQueryService` 3개 함수 | 「정형 접근 경로」 3행 |
| 제한형 NL2SQL | 채택 | `NL2SQLGenerator`와 선행 AST 검사 | `S-R4`·`S-B4` |
| 의미정보(RAG) | 채택 | `PgVectorHybridRetriever`와 색인 스크립트 | `S-1` 구축·검색 스펙 |
| 관계정보(GraphRAG) | 채택 | `GraphRetriever`와 적재·권한 스크립트 | `S-2` ⑴부터 ⑷ |
| 외부검색(웹·영상) | 채택 | `src/tools`의 `OfficialSearchConnector` 재사용 | 외부검색 2행·`C-A3` |
| 용어사전 | 채택 | 선행 `help_desk_dataset.glossary` 재사용 | `카드업무용어` |
| 별도 검색 클러스터 | 미채택 | 파일·설정·의존성 없음 | 경로 채택·미채택 |
| 관계형 재귀 SQL | 미채택 | 파일·설정·의존성 없음 | 경로 채택·미채택 |
| 비공식 포털 전체 검색 | 미채택 | 파일·설정·의존성 없음 | 경로 채택·미채택 |
| 벡터 유사도 사전 | 미채택 | 파일·설정·의존성 없음 | 경로 채택·미채택 |
| Pre 4기법 | 미채택 | 파일·설정·의존성 없음 | 질의 전처리 표 |
| 리랭킹·Compression·Fusion | 미채택 | 파일·설정·의존성 없음 | 결과 후처리 표 |

결정론 선행 필터는 만들지 않음. ⑤에 필터 입력 필드와 고정 쿼리 경로가  
구체적으로 연결된 행이 없기 때문임.  
카드 상태 고정 쿼리는 ⑤의 변경요청을 ④에 먼저 반영한 뒤  
③에 `변경요청`으로 단계 연결 필요함.

### 호출 함수

| 목적 | 호출 함수 | 반환 |
|---|---|---|
| 질문별 거래 분석 | `KnowledgeQueryService.query_s_r4()` | 허용 열의 행 목록 |
| 전일 상담 고정 조회 | `KnowledgeQueryService.query_s_b2()` | 허용 열의 행 목록 |
| 배치 통계 조회 | `KnowledgeQueryService.query_s_b4()` | 허용 열의 행 목록 |
| 제한형 SQL 생성·실행 | `KnowledgeQueryService.generate_and_query()` | 검사 완료된 조회 결과 |
| 승인 문서 검색 | `PgVectorHybridRetriever.search()` | `evidence_refs` 또는 빈 결과와 사유 |
| 관계 경로 검색 | `GraphRetriever.search()` | `evidence_refs` 또는 빈 결과와 사유 |

모든 근거는 `content`, `source`, `score`를 함께 반환함.  
용어사전 적용 결과는 원문 `original_term`과 대표어 후보 `canonical_terms`를 함께 반환함.

### 설정 옮김

| 설정 묶음 | 옮긴 스펙 | 주입 위치 |
|---|---|---|
| RAG 구축 | DB명·제품·색인 파라미터·소스·건수·기준일·추출·정제·청크·중첩·구분자·모델·차원 | `.env.example` |
| RAG 검색 | 검색 기법·융합 방식·RRF 값·다양성·top-k·후보 수 | `.env.example` |
| GraphRAG | 제품·버전·타입·고유키·관계·색인·최대 홉·결과 상한 | 환경변수와 `config/neo4j` |
| 접근 필터 | 담당자·워크플로우·role 2행 | `config/knowledge/graph_role_map.json` |
| 적재 검수 | 구조 0건·상충쌍 0건·표본 50건·정확도 95% | 코드와 환경변수 |
| Filtering | 유사도 0.35·공식 도메인·role | 환경변수·커넥터·DB role |

후보 수는 설계의 `해당 없음`에 따라 `top-k`와 같은 모집단을 사용함.  
별도 후보 수 설정은 만들지 않음.

### 색인 다시 만들기

사용자 승인 기본값인 새 이름 생성 후 교체 방식을 적용함.

1. 승인 문서 원천 건수와 기준일 확정
2. `.env`의 `HELP_DESK_KNOWLEDGE_RAG_SOURCE_COUNT`와
   `HELP_DESK_KNOWLEDGE_RAG_BASELINE_DATE` 설정
3. `uv run python scripts/build_rag_index.py <승인문서디렉터리>` 실행
4. 새 테이블에 문서 자리 출처와 함께 청크 적재
5. 실제 청크가 10,000개 이상일 때만 HNSW 색인 생성
6. 건수·근거 출처·검색 표본 검수
7. 운영 트랜잭션에서 검색 별칭을 새 테이블로 교체
8. 보존 기간이 지난 이전 테이블 파기

두 확인값이 없으면 스크립트가 색인 생성을 시작하지 않음.

### GraphRAG 운영

운영 관리자는 앱과 분리된 관리자 세션에서 다음 파일을 순서대로 실행함.

1. `config/neo4j/schema.cypher`
2. `config/neo4j/roles.cypher`
3. 용어 정규화와 적재 검수를 통과한 CSV에 `config/neo4j/load_graph.cypher` 적용

앱은 role 생성·권한 부여 문을 실행하지 않음.  
`GraphRetriever.startup_verify()`는 접속 계정의 role이 매핑과 다르면 서비스 기동을 거부함.  
`customer_ref`와 `batch_date`는 ③ State에서 꺼내 질의 파라미터로만 바인딩함.

### 허용 목록과 차단 목록

| 열 이름 | 허용·차단 | 설계 출처 |
|---|---|---|
| `masked_transaction_analysis_v.masked_customer_id` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_transaction_analysis_v.transaction_date` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_transaction_analysis_v.transaction_status` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_transaction_analysis_v.decline_reason_code` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_transaction_analysis_v.amount_bucket` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_transaction_analysis_v.merchant_category_code` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_consultation_analysis_v.consultation_ref` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_consultation_analysis_v.ended_at` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_consultation_analysis_v.topic_code` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_consultation_analysis_v.resolution_code` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_consultation_analysis_v.reopen_count` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_consultation_analysis_v.masked_summary` | 허용 | ⑤ 담당자별 허용 열 |
| `masked_transaction_analysis_v.original_customer_id`·`full_card_number`·`cvc`·`password`·`resident_registration_number`·`auth_token` | 차단 | ⑤ 정형 접근 금지 컬럼 |
| `masked_consultation_analysis_v.original_customer_id`·`raw_transcript`·`full_card_number`·`cvc`·`resident_registration_number`·`auth_token` | 차단 | ⑤ 정형 접근 금지 컬럼 |
| `consultation_event_inbox.raw_transcript` | 차단 | ⑤ 정형 접근 금지 컬럼 |
| `langgraph_checkpoints.state_ciphertext` | 차단 | ⑤ 정형 접근 금지 컬럼 |

차단 열은 조회 후 마스킹하지 않음. SQL AST 검사에서 조회 자체를 실패시킴.

### 실패 착지와 기본값

| 되묻기 항목 | 사용자 승인 값 | 설계서 되돌림 위치 |
|---|---|---|
| 재색인 | 새 이름으로 완성 후 교체 | ⑤ 의미정보 운영 절차 |
| 후보 0건·낮은 점수 | 빈 결과와 사유 반환 | ⑤ 검색 실패 착지 |
| 다중 경로 결합 | 경로별 분리 반환 | ⑤ 경로 합치기 규칙 |
| 내부 검색 결과 캐시 | 추가 저장하지 않음 | ⑤ 검색 캐시 정책 |
| 낮은 점수 문턱 | 후보 수 0건을 신호로 사용 | ⑤ 검색 실패 착지 |
| 1:N 충돌 | 보류·경고하고 원문 유지 | ⑤ 용어사전 충돌 처리 |

⑤가 값의 주인이므로 위 6건을 설계서 ⑤에 되돌려 적는 것을 권고함.

외부검색 `C-A3`의 PostgreSQL 캐시는 ⑤가 이미 웹 60분·영상 1440분으로 확정함.  
추가 캐시를 만들지 않는 기본값은 의미정보·관계정보 조회 결과에만 적용함.

### 지식 경로 파일

```text
help_desk_knowledge/
  graph.py
  graph_ingestion.py
  indexing.py
  post_filter.py
  rag.py
  results.py
  specs.py
  structured.py
config/
  knowledge/graph_role_map.json
  neo4j/load_graph.cypher
  neo4j/roles.cypher
  neo4j/schema.cypher
scripts/build_rag_index.py
tests/test_knowledge_*.py
```

### 지식 경로 시험

세 운영체제별 가상환경 명령은 이 README의 「가상환경 만들기와 실행」 절을 사용함.

```bash
uv sync --group dev
uv run pytest -q
```

실 PostgreSQL·Neo4j 시험은 `@pytest.mark.live_call`로 분리함.  
운영 Neo4j 시험은 `HELP_DESK_RUN_NEO4J_LIVE=1`과 별도 접속 비밀값을 주입한 환경에서 실행함.

## 배치 실행기와 내부 승인 API

| 진입 형태 | 경로 또는 함수 | 설계 출처 | 바깥 공개 |
|---|---|---|:---:|
| 스케줄 실행기 | `run_scheduled_batch` | ③ W-2 스케줄 배치 | 아니오 |
| 내부 승인 API | `POST /internal/faq-candidates/{candidate_id}/decisions` | ③ P-2 API | 아니오 |
| 상태 확인 | `GET /health/live`, `GET /health/ready` | ⑧ 배포 입력 | 아니오 |

내부 API 포트는 `HELP_DESK_P2_INTERNAL_PORT`로 읽으며 `.env.example` 기본값은 8081임.  
운영 배포에서는 외부 인입을 열지 않고 내부 승인 주체만 접근하도록 제한해야 함.

### Windows Git Bash

```bash
uv sync --group dev
uv run uvicorn p2_knowledge_improvement_batch.api:app --port "$HELP_DESK_P2_INTERNAL_PORT"
```

### Windows PowerShell

```powershell
uv sync --group dev
uv run uvicorn p2_knowledge_improvement_batch.api:app --port $env:HELP_DESK_P2_INTERNAL_PORT
```

### Linux 또는 macOS

```bash
uv sync --group dev
uv run uvicorn p2_knowledge_improvement_batch.api:app --port "$HELP_DESK_P2_INTERNAL_PORT"
```
