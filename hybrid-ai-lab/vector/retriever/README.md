# Vector Retriever

> 로컬 전용 — 인증 기능이 없으므로 외부 네트워크에 노출하면 안 됨.

KURE-v1 ChromaDB에서 문서를 검색하고 근거가 붙은 답변을 만드는 로컬 앱임.
Vector, Hybrid, Hybrid + Rerank 세 경로와 선택적 질문 변환을 지원함.

## 실행 전제

- Python 3.12 권장
- Indexer가 만든 `../indexer/data/chroma/` 필요
- 컬렉션 `card_docs`에 청크 1건 이상 필요
- 임베딩 서명 `sentence-transformers:nlpai-lab/KURE-v1:prompt-policy-v2` 필요
- 실제 동등성 평가 전제는 청크 485건과 임베딩 1,024차원임
- Rerank 최초 사용 시 `BAAI/bge-reranker-v2-m3` 약 2.2GB 다운로드 필요

Indexer 실행 방법은 `../indexer/README.md` 참고 대상임.

## 설치

```bash
cd hybrid-ai-lab/vector/retriever
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux CPU 환경에서 PyTorch 설치본을 찾지 못하면  
PyTorch CPU 인덱스를 먼저 지정해야 할 수 있음.

```bash
python -m pip install torch==2.14.0 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

설정 파일이 필요한 경우 예시 파일을 복사함. 빈 값은 코드 기본값으로 대체됨.

```bash
cp .env.example .env
```

## CLI

### 인덱스 연결 확인

`--dry-run`은 인덱스 연결·서명·건수를 확인한 뒤 검색 전에 종료함.

```bash
python run_retriever.py \
  --query "연회비 면제 조건은?" \
  --dry-run
```

### 세 가지 검색 모드

| 모드 | 처리 | 최종 결과 |
|---|---|---|
| `vector` | KURE-v1 의미 검색 | Vector Top-K |
| `hybrid` | Vector 0.6 + BM25 0.4 | 융합 Top-K |
| `hybrid_rerank` | Hybrid 후보를 Cross-Encoder로 재정렬 | Rerank Top-K |

기본 최종 Top-K 5의 후보 흐름은 다음과 같음.

| 모드 | 검색기별 원시 후보 | 질문별 융합 후보 | 최종 결과 |
|---|---:|---:|---:|
| `vector` | 20건 | 해당 없음 | 5건 |
| `hybrid` | 20건 | 5건 | 5건 |
| `hybrid_rerank` | 40건 | 10건 | Rerank 5건 |

`CANDIDATE_MULTIPLIER=4`는 질문별 검색·융합 목표 수에 적용됨.
따라서 `hybrid_rerank`는 융합 목표 10건 × 4로 검색기별 원시 후보 40건을 수집함.
질문 변환 시에도 원 질문과 각 변환 질문에 같은 후보 계약이 적용됨.

답변 LLM을 호출하지 않고 검색 결과와 프롬프트만 확인하는 예시임.

```bash
python run_retriever.py \
  --query "연회비 면제 조건은?" \
  --mode vector \
  --transform off \
  --top-k 5 \
  --prompt-only
```

```bash
python run_retriever.py \
  --query "연회비 면제 조건은?" \
  --mode hybrid \
  --transform off \
  --top-k 5 \
  --prompt-only
```

```bash
python run_retriever.py \
  --query "연회비 면제 조건은?" \
  --mode hybrid_rerank \
  --transform off \
  --top-k 5 \
  --prompt-only
```

`--prompt-only`는 답변 LLM만 차단함.
`--transform auto`에서 캐시가 없고 변환 관문을 통과하지 못하면 라우터 LLM 호출 가능함.

### 질문 변환

`--transform auto`는 원 질문 Vector Top-1 코사인 유사도가 0.70 미만일 때만 라우팅함.
가능한 기법은 rewrite, multi, HyDE, step-back, decomposition임.

```bash
python run_retriever.py \
  --query "올해 비용 면제와 포인트 적립 조건을 함께 알려주세요" \
  --mode hybrid \
  --transform auto \
  --top-k 5 \
  --prompt-only
```

질문 변환 결정은 기본적으로 `data/transform_cache.json`에 저장됨.
같은 질문의 유효한 캐시가 있으면 라우터 LLM 호출 없이 재사용함.

### CLI 옵션

| 옵션 | 기본값 | 의미 |
|---|---|---|
| `--query` | 필수 | 공백이 아닌 질문 |
| `--top-k` | `5` | 최종 검색 결과 건수 |
| `--mode` | `hybrid_rerank` | 세 검색 경로 중 하나 |
| `--transform` | `off` | `off` 또는 `auto` |
| `--role` | `agent` | `agent` 또는 `auditor` |
| `--thread-id` | 자동 생성 | 체크포인트 세션 키 |
| `--dry-run` | 꺼짐 | 인덱스 확인 후 종료 |
| `--prompt-only` | 꺼짐 | 답변 LLM 없이 프롬프트까지 실행 |
| `--max-llm-calls` | `8` | 전송 시도 상한 |

```bash
python run_retriever.py --help
```

CLI 결과는 stdout의 JSON 한 건임. 파일 저장이 필요하면 셸 리다이렉트 사용 가능함.

```bash
python run_retriever.py \
  --query "연회비 면제 조건은?" \
  --mode hybrid \
  --prompt-only > data/search_run1.json
```

중단된 CLI 작업은 같은 `--thread-id`로 재개 가능함.
새 질문에는 완료된 작업의 ID를 재사용하지 않는 것이 안전함.

## 역할과 검색 권한

| `X-Role` 또는 `--role` | 검색 가능한 등급 |
|---|---|
| `agent` | `public`, `internal` |
| `auditor` | `public`, `internal`, `restricted` |

HTTP 요청에는 `X-Role` 헤더가 필수임. 누락하거나 다른 값을 보내면 400 `invalid_role`임.

## LLM 설정

실제 답변 또는 캐시 없는 질문 변환을 실행하려면  
선택한 제공자의 키와 모델 설정이 필요함.
키 값은 문서·명령 기록·버전 관리에 넣지 않아야 함.

Groq 예시임.

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=<환경별 비밀값>
GROQ_MODEL=openai/gpt-oss-120b
```

Claude 예시임.

```dotenv
LLM_PROVIDER=claude
CLAUDE_API_KEY=<환경별 비밀값>
CLAUDE_MODEL=<사용 가능한 모델 ID>
```

OpenAI 예시임.

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=<환경별 비밀값>
OPENAI_MODEL=<사용 가능한 모델 ID>
```

설정 우선순위는 CLI 재정의, 프로세스 환경변수, 앱 `.env`, `hybrid-ai-lab/.env`, 기본값 순임.
빈 문자열과 공백은 미설정으로 처리됨.

주요 제한 기본값은 다음과 같음.

- LLM 전송 1회 제한 60초
- Vector 검색 1회 제한 10초
- Reranker 호출 1회 제한 60초
- CLI 전송 시도 상한 8회
- API 요청당 전송 시도 상한 2회
- API 서버 프로세스 누적 전송 시도 상한 200회
- API 요청 제한 120초
- 근거 자동 검증 실패 시 수정 루프 최대 2회

429·5xx·연결·타임아웃만 제한적으로 재시도함. 인증·권한·일반 4xx는 재시도하지 않음.

임베딩·Reranker 모델 최초 적재는 작업 시간 제한에서 제외됨.
시간 제한 호출은 공용 작업자 최대 4개로 실행됨.
호출자는 마감에서 복귀하지만 이미 실행 중인 Python 스레드는 강제 종료할 수 없음.
따라서 하부 작업이 끝날 때까지 작업자 하나를 계속 사용할 수 있음.

2026-09-13 검증에서는 외부 LLM 네트워크 시험을 실행하지 않았음.
답변 품질과 실제 제공자 인증은 별도 검증 대상임.

## 답변 관문과 상태

답변 전 최종 1위 결과의 원래 Vector 점수를 확인함.
점수가 없거나 0.62 미만이면 LLM을 호출하지 않고 `status=needs_check`로 종료함.

주요 상태는 다음과 같음.

| 상태 | 의미 |
|---|---|
| `ok` | 검색·답변·검증 정상 완료 |
| `needs_check` | 답변 관문 미달 또는 명확화 필요 |
| `prompt_only` | 답변 LLM 직전까지 완료 |
| `dry_run` | 인덱스 확인 완료 |
| `halted_by_limit` | 호출·수정 루프 상한에서 부분 결과 종료 |
| `error` | 입력·설정 오류 |

## HTTP API

기본 바인딩은 `127.0.0.1:8001`임.

```bash
python serve_retriever.py
```

개발 중 포트와 자동 재시작을 바꾸는 예시임.

```bash
python serve_retriever.py --host 127.0.0.1 --port 8001 --reload
```

지원 라우트는 4개임.

| 메서드 | 경로 | 용도 |
|---|---|---|
| `GET` | `/health` | 인덱스·모델 설정 상태 확인 |
| `POST` | `/search` | 검색만 실행, `answer=null` |
| `POST` | `/answer` | 검색·답변·근거 검증 실행 |
| `GET` | `/answer/stream` | 노드 진행과 최종 결과를 SSE로 전송 |

OpenAPI 화면은 `/docs`, 명세 JSON은 `/openapi.json`에서 확인 가능함.

### Health

```bash
curl -sS http://127.0.0.1:8001/health \
  -H 'X-Role: agent'
```

### Search

```bash
curl -sS http://127.0.0.1:8001/search \
  -H 'Content-Type: application/json' \
  -H 'X-Role: agent' \
  -d '{
    "query": "연회비 면제 조건은?",
    "top_k": 5,
    "mode": "hybrid",
    "transform": "off"
  }'
```

`/search`는 답변 LLM을 호출하지 않음.
다만 `transform=auto`이고 변환 캐시가 없으면 라우터 LLM 호출 가능함.

### Answer

```bash
curl -sS http://127.0.0.1:8001/answer \
  -H 'Content-Type: application/json' \
  -H 'X-Role: agent' \
  -d '{
    "query": "연회비 면제 조건은?",
    "top_k": 5,
    "mode": "hybrid_rerank",
    "transform": "off"
  }'
```

성공 응답은 CLI `SearchResult` 필드에 32자리 `request_id`가 추가된 형태임.

## SSE

`curl -N`으로 버퍼링 없이 이벤트를 확인하는 예시임.

```bash
curl -N -G http://127.0.0.1:8001/answer/stream \
  -H 'X-Role: agent' \
  --data-urlencode 'query=연회비 면제 조건은?' \
  --data 'top_k=5' \
  --data 'mode=hybrid' \
  --data 'transform=off'
```

이벤트 종류는 `node_start`, `node_end`, `final`, `error`임.
`final`은 정상 그래프 종료 시 한 번 발생하며 POST `/answer`와 같은 결과 필드를 가짐.
15초마다 SSE 주석 하트비트가 전송될 수 있음.

브라우저 `EventSource`는 임의 헤더를 붙이지 못하므로 `X-Role` 요구사항과 맞지 않음.
브라우저에서는 `fetch`와 `ReadableStream` 사용이 필요함.

```js
const response = await fetch(
  "/answer/stream?query=" + encodeURIComponent("연회비 면제 조건은?"),
  { headers: { "X-Role": "agent" } },
);
const reader = response.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  console.log(decoder.decode(value, { stream: true }));
}
```

실제 서비스 화면에서는 청크 경계가 SSE 이벤트 경계와 같다고 가정하면 안 됨.
수신 문자열을 빈 줄 기준으로 누적 파싱해야 함.

## 오류 응답

HTTP 오류 본문 형태는 다음과 같음.

```json
{
  "error_code": "invalid_role",
  "message": "X-Role 헤더가 올바르지 않음",
  "detail": null
}
```

| HTTP | `error_code` | 대표 원인 |
|---:|---|---|
| `400` | `invalid_request` | 요청 형식, LLM 설정·요청 오류 |
| `400` | `invalid_role` | `X-Role` 누락 또는 허용 밖 값 |
| `429` | `llm_call_limit` | 요청당·서버 누적·상류 호출 제한 |
| `503` | `index_unavailable` | 빈 컬렉션, 서명 불일치, 자원 준비 실패 |
| `504` | `timeout` | 요청 제한 시간 초과 |
| `500` | `internal_error` | 그 밖의 처리 오류 |

SSE 시작 전 발생한 400·503은 JSON 오류 응답임.
스트림 시작 뒤 발생한 호출 제한·시간 초과·내부 오류는 `error` 이벤트로 전송됨.

## 실행 파일과 감사 로그

| 경로 | 내용 |
|---|---|
| `data/bm25_index.pkl` | Chroma 문서로 만든 BM25 색인 캐시 |
| `data/transform_cache.json` | 질문별 변환 결정 캐시 |
| `data/checkpoints/retriever.sqlite` | CLI·POST 체크포인트 |
| `data/logs/<thread-id>.jsonl` | 본문·비밀값을 제외한 노드 감사 로그 |

감사 로그는 노드, 완료·실패, 경과 시간, 예외 종류만 기록함.
질문·검색 본문·메타데이터·API 키는 기록하지 않음.

## 동등성 평가

평가는 답변 LLM을 차단하고 저장된 질문 변환 결정을 재사용함.

```bash
python eval_equivalence.py
```

결과는 `data/equivalence_run1.json`에 저장됨.
네 조합이 모두 기준선을 충족해야 종료 코드 0이며, 하나라도 미달하면 종료 코드 1임.

2026-09-13 A안 적용 뒤 재측정 결과는 다음과 같음.

| 조합 | 기준 | 실측 | 판정 |
|---|---:|---:|---|
| `vector/off` | 6/7·2.125 | 6/7·2.125 | 통과 |
| `hybrid/off` | 6/7·2.375 | 6/7·2.375 | 통과 |
| `hybrid/auto` | 7/7·1.125 | 7/7·1.125 | 통과 |
| `hybrid_rerank/auto` | 7/7·1.375 | 7/7·1.375 | 통과 |

재측정은 48.65초에 종료 코드 0으로 끝났으며 `all_methods_meet_baseline=true`임.
답변·라우터 LLM 네트워크 호출은 0회임.
q6의 `hybrid_rerank/auto` 결과에서 `D1_0010`은 1위, `D2_0003`은 4위임.

A안 적용 전 `hybrid_rerank/auto`의 6/7·1.625 미달은 변경 전 이력임.
비교 이력은 `../COMPARISON.md`, 전체 검증 범위는 `../verify-report.md` 참고 대상임.
