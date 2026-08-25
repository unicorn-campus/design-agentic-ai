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
