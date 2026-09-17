# Vector 구현 검증 보고서

검증일: 2026-09-13

## 최종 판정

개발계획의 검증 범위에 대한 전체 판정은 **통과**임.

- Indexer 시험 24건 통과
- Retriever 비실호출 시험 93건과 하위 시험 5건 통과
- 원천 8건에서 문서 259건·청크 485건 생성 확인
- KURE-v1 1,024차원 Chroma 컬렉션 485건 확인
- 실제 프로세스의 HTTP·SSE 경계 동작 확인
- 검색 동등성 4조합 모두 통과
- 실제 외부 LLM 네트워크 호출 미실행

완료 판정 기준은 시험 성공만이 아니라  
실모델 인덱스, API 경계, 동등성 기준을 함께 충족하는 것임.
외부 LLM Structured Output과 실제 모델 API는 별도 미검증 항목임.
따라서 전체 통과는 실제 외부 LLM 호출 성공을 뜻하지 않음.

## 증거 보존 범위

실모델 Indexer 결과와 동등성 결과는 JSON 파일로 보존됨.
시험과 API 실기동의 터미널 로그 전문은 별도 파일로 보존되지 않음.

따라서 아래 시험 결과는 구현 단계의 완료 보고에 남은 명령·요약값을 기록한 것임.
API의 정확한 당시 셸 명령과 SSE URL은 보존되지 않아 재현 예시와 실측 사실을 구분함.

## 환경

| 항목 | 값 |
|---|---|
| 운영체제 | macOS 26.2, Build 25C56 |
| 아키텍처 | arm64 |
| Indexer Python | 3.12.11 |
| Retriever Python | 3.12.11 |
| Pytest | 9.1.1 |
| 검증 시 저장소 HEAD | `bd6e791` |
| Indexer 가상환경 | `vector/indexer/.venv` |
| Retriever 가상환경 | `vector/retriever/.venv` |

주요 패키지 버전은 두 앱의 `requirements.txt`에 고정됨.
Vector 앱 작업트리는 검증 시점에 Git 미추적 상태였음.  
따라서 HEAD는 앱 소스 버전 식별자가 아님.
실제 모델 캐시의 `main` 참조는 다음과 같음.

| 모델 | Hugging Face revision |
|---|---|
| `nlpai-lab/KURE-v1` | `8b418a58414668e75532ed045c22d9ca018ae2b2` |
| `BAAI/bge-reranker-v2-m3` | `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` |

## 자동 시험

Pytest는 앱 실행 의존성이 아니어서 `requirements.txt`에 포함되지 않음.
아래 결과는 두 기존 가상환경에 설치된 Pytest 9.1.1로 실행한 값임.

### Indexer

최종 실행 명령은 다음과 같음.

```bash
cd hybrid-ai-lab/vector/indexer
.venv/bin/python -m pytest -q
```

최종 재실행 결과는 `24 passed in 3.70s`임. 실패·오류·건너뜀 0건임.

검증 범위는 9개 노드, dry-run, 종료 상태, 증분 적재, 체크포인트 재개,
상담·메타데이터·청킹·CLI 경계와 작업 단위 시간 제한임.

### Retriever

외부 LLM을 제외한 최종 실행 명령은 다음과 같음.

```bash
cd hybrid-ai-lab/vector/retriever
.venv/bin/python -m pytest -q -m "not live_call"
```

최종 재실행 결과는 `93 passed, 1 deselected, 5 subtests passed in 3.26s`임.
제외한 1건은 명시 실행 전용 외부 LLM 시험임.
AnyIO 기본 fixture 별칭의 폐기 예정 경고 1건이 있었으며 시험 실패는 아님.

검증 범위는 11개 노드, 검색·융합·권한, 질문 변환, 캐시, 근거 대조,
LLM 어댑터의 가짜 클라이언트 시험, CLI·API·SSE 경계, Vector·Rerank 시간 제한임.

## G2 Indexer 실모델 검증

결과와 같은 조건을 재현하는 전체 적재 명령은 다음과 같음.

```bash
cd hybrid-ai-lab/vector/indexer
.venv/bin/python run_indexer.py \
  --in ../../docs \
  --out data \
  --doc all \
  --embedding-backend sentence-transformers \
  --full-reindex
```

보존 증거는 `data/index_run4.json`임.

| 항목 | 실측 |
|---|---:|
| 원천 | 8건 |
| 문서 | 259건 |
| 규정 문서 | 15건 |
| 혜택 문서 | 196건 |
| 상담 문서 | 48건 |
| 상담 분리 불일치 | 0건 |
| 가명화 | `true` |
| 입력 단위 | 435건 |
| 제외 | 16건 |
| 청크 | 485건 |
| D1 청크 | 53건 |
| D2 청크 | 336건 |
| D3 청크 | 96건 |
| 검토 보류 | 0건 |
| 글자 상한 예외 | 56건 |
| 신규 임베딩 | 485건 |
| 적재 실패 | 0건 |
| 컬렉션 | 485건 |
| 임베딩 차원 | 1,024 |
| 총 시간 | 254,793ms |
| 상태·종료 | `ok`, 0 |

출력 파일 줄 수도 별도로 대조됨.

```text
documents.jsonl   259
chunks.jsonl      485
review.jsonl        0
exceptions.jsonl   56
```

`validation.json`은 checked 259, valid 259, invalid 0임.
`index_manifest.json`은 KURE-v1 서명, cosine 컬렉션, 청킹 파라미터, 청크 해시 485건을 보관함.

## 증분 적재 검증

같은 입력을 새 thread ID로 다시 실행하는 조건의 명령은 다음과 같음.

```bash
cd hybrid-ai-lab/vector/indexer
.venv/bin/python run_indexer.py \
  --in ../../docs \
  --out data \
  --doc all \
  --embedding-backend sentence-transformers
```

현재 코드 수정 뒤 보존된 최종 증거는 `data/index_run6.json`임.

| 항목 | 실측 |
|---|---:|
| 신규 임베딩 | 0건 |
| 해시 건너뜀 | 485건 |
| 적재 실패 | 0건 |
| 컬렉션 | 485건 |
| 임베딩 차원 | 1,024 |
| 총 시간 | 17,902ms |
| 상태·종료 | `ok`, 0 |

`data/index_run5.json`은 이전 중간 구현에서 차원을 0으로 보고한 기록임.
최종 확인 근거로 사용하지 않으며 수정 뒤 생성된 `index_run6.json`을 기준으로 함.

## Retriever 인덱스·모델 검증

동등성 실행이 실제 인덱스를 열어 확인한 상태는 다음과 같음.

```json
{
  "status": "ok",
  "index_connected": true,
  "collection_count": 485,
  "embedding_dimension": 1024,
  "llm_provider": "groq"
}
```

이 값은 `retriever/data/equivalence_run1.json`에 보존됨.
여기서 제공자 이름은 설정값 확인일 뿐 실제 Groq 네트워크 호출 성공 증거가 아님.

## HTTP·SSE 실기동 검증

`tests/live_api_app.py`의 fake dependency injection 앱을 실제 uvicorn 프로세스로
`127.0.0.1:18731`에 기동하여 경계를 확인함.

확인 결과는 다음과 같음.

| 대상 | 결과 |
|---|---|
| `GET /health` | HTTP 200 |
| `GET /docs` | HTTP 200 |
| `GET /openapi.json` | HTTP 200 |
| `GET /answer/stream` | HTTP 200 |
| SSE | `node_start → node_end` 8쌍 뒤 `final` 1회 |
| 종료 처리 | uvicorn 프로세스 종료, 18731 포트 폐쇄 확인 |

Fake 앱은 검색 모델과 LLM을 적재하지 않음.
따라서 이 검증은 소켓·HTTP·OpenAPI·헤더·SSE 직렬화의 증거임.  
실제 모델 API의 증거는 아님.

정확한 당시 셸 명령은 보존되지 않았음.  
다음 명령은 같은 경계를 확인하기 위한 재현 예시임.

```bash
cd hybrid-ai-lab/vector/retriever
.venv/bin/python -m uvicorn tests.live_api_app:app \
  --host 127.0.0.1 \
  --port 18731
```

별도 셸에서 사용할 재현 요청 예시임.

```bash
curl -sS http://127.0.0.1:18731/health -H 'X-Role: agent'
curl -sS http://127.0.0.1:18731/docs -o /dev/null -w '%{http_code}\n'
curl -sS http://127.0.0.1:18731/openapi.json -o /dev/null -w '%{http_code}\n'
curl -N -G http://127.0.0.1:18731/answer/stream \
  -H 'X-Role: agent' \
  --data-urlencode 'query=연회비 면제 조건은?' \
  --data 'mode=hybrid' \
  --data 'transform=off'
```

## 검색 동등성

실행 명령은 다음과 같음.

```bash
cd hybrid-ai-lab/vector/retriever
.venv/bin/python eval_equivalence.py
```

평가는 실제 KURE-v1 인덱스와 실제 Reranker를 사용함.
답변은 `prompt_only`로 차단함.  
질문 변환은 기존 저장 결과를 캐시로 옮겨 사용하여 외부 LLM 호출을 0회로 고정함.

| 조합 | 기준 포함 | 기준 순위 | 실측 포함 | 실측 순위 | 판정 |
|---|---:|---:|---:|---:|---|
| `vector/off` | 6/7 | 2.125 | 6/7 | 2.125 | 통과 |
| `hybrid/off` | 6/7 | 2.375 | 6/7 | 2.375 | 통과 |
| `hybrid/auto` | 7/7 | 1.125 | 7/7 | 1.125 | 통과 |
| `hybrid_rerank/auto` | 7/7 | 1.375 | 7/7 | 1.375 | 통과 |

전체 결과의 `all_methods_meet_baseline`은 `true`이며 평가 프로그램 종료 코드는 0임.
실행 시간은 48.65초이고 답변·라우터 LLM 네트워크 호출은 0회임.

q6의 `hybrid_rerank/auto` 결과에서 기대 청크 `D1_0010`은 1위,
`D2_0003`은 4위로 모두 최종 Top-5에 포함됨.

A안 적용 전 결과는 6/7·1.625, 종료 코드 1, 전체 부분 통과였음.
해당 값은 변경 전 이력이며 현재 판정에 사용하지 않음.

평가 평균 시간은 다음과 같음. 최초 모델 준비 시간이 일부 포함될 수 있음.

| 조합 | 검색 평균 | Rerank 평균 | 전체 평균 |
|---|---:|---:|---:|
| `vector/off` | 2,386.4ms | 0.0ms | 2,386.4ms |
| `hybrid/off` | 184.6ms | 0.0ms | 184.6ms |
| `hybrid/auto` | 223.5ms | 0.0ms | 223.5ms |
| `hybrid_rerank/auto` | 481.7ms | 3,245.0ms | 3,726.7ms |

## 설정·계약 정적 대조

두 앱의 `app/settings.py`는 바이트 단위 비교 결과 차이 0임.

```bash
cd hybrid-ai-lab
cmp -s vector/indexer/app/settings.py vector/retriever/app/settings.py
```

코드에서 확인한 계약은 다음과 같음.

- Indexer 노드 9개와 Retriever 노드 11개 등록
- CLI의 세 검색 모드와 `off`, `auto` 변환 옵션 등록
- API 라우트 4개와 `X-Role` 필수 검사 등록
- agent는 public·internal, auditor는 restricted까지 허용
- Stream 그래프는 체크포인터 없이 `astream_events(version="v2")` 사용
- CLI·POST는 SQLite 체크포인터 사용
- 답변 관문은 최종 1위 `vector_score` 사용
- `candidate_sizes()`가 모드별 원시 후보 수와 질문별 융합 후보 수 계산
- `vector`·`hybrid`는 검색기별 원시 후보 20건에서 최종 5건 반환
- `hybrid_rerank`는 검색기별 원시 후보 40건 → 융합 10건 → Rerank 최종 5건 반환
- `CANDIDATE_MULTIPLIER=4`는 질문별 검색·융합 목표 수에 적용
- PDF·청킹·임베딩·upsert·Vector·Rerank 작업 단위 시간 제한 적용
- 시간 제한 실행기 작업자 최대 4개 적용
- 노드별 안전 필드 감사 로그 적용
- `.env` 키는 `SecretStr`로 보관하고 오류 메시지에 실제 키 값 미포함

시간 제한 호출자는 마감에서 복귀하지만  
이미 실행 중인 Python 스레드는 강제 종료되지 않음.
남은 작업은 끝날 때까지 최대 4개 공용 작업자 중 하나를 사용함.

## 별도 미검증 항목

| 항목 | 상태 | 필요한 다음 증거 |
|---|---|---|
| 외부 LLM Structured Output | 미실행 | `RUN_LIVE_LLM=1` 명시 실행 성공 로그 |
| 실제 `/answer` 품질 | 미실행 | 실제 키로 대표 질문 1건의 검증된 응답 |
| 실제 모델을 붙인 uvicorn API | 미실행 | `/health`, `/search`, SSE 실응답 |
| API 실기동 로그 전문 | 미보존 | 명령·응답·종료 로그 파일 저장 |

실행하지 않은 외부 LLM 시험과 실제 모델 API는 완료로 간주하지 않음.
