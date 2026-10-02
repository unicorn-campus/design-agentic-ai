# Vector Retriever

> 로컬 전용 — 인증 기능이 없으므로 외부 네트워크에 노출하면 안 됨.

KURE-v2(`nlpai-lab/KURE-v2`) ChromaDB에서 문서를 검색하고 근거가 붙은 답변을 만드는 로컬 앱임.
Vector, Hybrid, Hybrid + Rerank 세 경로와 선택적 질문 변환을 지원함.

## 실행 전제

- Python 3.12 권장
- Indexer가 게시한 활성 세대 포인터 `../../indexer/vector-bm25/data/active_generation.json` 필요  
  포인터가 가리키는 같은 세대의 `chroma`와 `search_indexes`를 함께 사용함
- 컬렉션 `card_docs`에 청크 1건 이상 필요
- 임베딩 모델은 `nlpai-lab/KURE-v2`(설정 `EMBED_MODEL` 기본값)임
- 임베딩 서명 `sentence-transformers:nlpai-lab/KURE-v2:prompt-policy-v2` 필요
- 현재 활성 세대는 `gen-rebuild-20261002-c8f87e7e`, 청크 195건 · 768차원임(2026-10-02 재색인 기준)
- 아래 「동등성 평가」 수치는 이전 Indexer 색인(청크 483건) 기준 기록이므로 현재 세대에 그대로 적용되지 않음
- Rerank 최초 사용 시 `BAAI/bge-reranker-v2-m3` 약 2.2GB 다운로드 필요

Indexer 실행 방법은 `../../indexer/vector-bm25/README.md` 참고 대상임.

## 설치

```bash
cd hybrid-ai-lab/retriever/vector-retriever
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

`VECTOR_STORE_BACKEND` 기본값은 `chroma`임. `memory`는 자동화 시험용 비영속 저장소임.

색인 경로는 `CHROMA_PATH`·`SEARCH_INDEX_ROOT`를 비워 두면 `ACTIVE_GENERATION_POINTER`에서 읽음.  
기본 포인터는 `../../indexer/vector-bm25/data/active_generation.json`이며,  
포인터의 `chroma_path`·`search_index_root`·`collection`을 같은 세대에서 함께 사용함.  
Indexer가 새 세대를 게시하면 검색기를 다시 시작할 때 새 세대를 읽음.

`SEARCH_INDEX_ROOT`는 Indexer가 발행한 `active_index.json`의 루트임.  
경로를 직접 지정할 때는 `CHROMA_PATH`와 `SEARCH_INDEX_ROOT`를 **같은 세대로 함께** 적어야 함.  
한쪽만 적으면 벡터와 BM25가 다른 세대를 가리키므로 설정 오류로 중단함.  
Indexer에서 `--output`을 바꾼 경우에는 그 폴더의 `active_generation.json`을 `ACTIVE_GENERATION_POINTER`로 지정함.  
포인터 파일이 없으면 이전 고정 배치(`data/chroma`, `data/search_indexes`)를 기본값으로 사용함.

`KOREAN_USER_DICTIONARY`는 Indexer와 같은 파일을 지정해야 하며 파일 내용은 토크나이저 서명에 포함됨.

`KOREAN_TOKENIZER_WORKERS`는 실시간 Kiwi 질의 분석 작업자 수이며 기본값은 1임.  
BM25는 ACL 적용 후 Top-K만 조회하고 0점 후보를 제거함. 원 질의 결과가 없을 때만  
Kiwi `basic` 오타 교정 질의를 한 번 사용하므로 상품 코드의 과도한 교정 가능성을 제한함.

새 운영 벡터 DB는 DB 중립 필터를 변환하는 어댑터와 생성 팩터리에 등록함.

## CLI

### 인덱스 연결 확인

`--dry-run`은 인덱스 연결·서명·건수를 확인한 뒤 검색 전에 종료함.

```bash
python run_retriever.py \
  --query "연회비 면제 조건은?" \
  --dry-run
```

### 네 가지 검색 모드

| 모드 | 처리 | 최종 결과 |
|---|---|---|
| `vector` | KURE-v2 의미 검색 | Vector Top-K |
| `vector_rerank` | Vector 후보를 Cross-Encoder로 재정렬 | Rerank Top-K |
| `hybrid` | Vector 0.6 + BM25 0.4 | 융합 Top-K |
| `hybrid_rerank` | Hybrid 후보를 Cross-Encoder로 재정렬 | Rerank Top-K |

기본 최종 Top-K 5의 후보 흐름은 다음과 같음.

| 모드 | 검색기별 원시 후보 | 질문별 융합 후보 | 최종 결과 |
|---|---:|---:|---:|
| `vector` | 20건 | 해당 없음 | 5건 |
| `vector_rerank` | 40건 | Vector 10건 | Rerank 5건 |
| `hybrid` | 20건 | 5건 | 5건 |
| `hybrid_rerank` | 40건 | 10건 | Rerank 5건 |

`CANDIDATE_MULTIPLIER=4`는 질문별 검색·융합 목표 수에 적용됨.
따라서 `vector_rerank`와 `hybrid_rerank`는 리랭크 목표 10건 × 4로 검색기별 원시 후보 40건을 수집함.
질문 변환 시에도 원 질문과 각 변환 질문에 같은 후보 계약이 적용됨.

벡터 후보 선택은 기본적으로 `VECTOR_SEARCH_STRATEGY=similarity`를 사용하므로 기존 cosine 유사도 순서를 유지함.
`VECTOR_SEARCH_STRATEGY=mmr`로 설정하면 유사 후보를 넓게 조회한 뒤 관련성과 문서 간 다양성을 함께 고려해 후보를 선택함.
`MMR_FETCH_MULTIPLIER=2`는 MMR 반환 목표 수보다 몇 배 많은 유사 후보를 먼저 조회할지 지정함.
`MMR_LAMBDA_MULT=0.5`는 0 이상 1 이하이며, 1에 가까울수록 질의 유사도, 0에 가까울수록 후보 다양성을 우선함.
MMR을 사용해도 결과의 `score`와 `vector_score`에는 MMR 합성값이 아니라 원래 질의 cosine 유사도를 유지함.

BM25는 Vector DB의 전체 문서를 다시 읽지 않음.

활성 세대의 `corpus.jsonl`과 BM25S 파일을 로딩하고, 질의에도 색인과 동일한 Kiwi 토크나이저를 적용함.

NFKC·숫자 쉼표·영문 대소문자를 정규화하며 형태소와 복합어 원형을 함께 보존함.

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
  --mode vector_rerank \
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

`--transform auto`는 원 질문 Vector Top-1 코사인 유사도가 0.86 미만일 때만 라우팅함.
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
| `--mode` | `hybrid_rerank` | 네 검색 경로 중 하나 |
| `--transform` | `off` | `off` 또는 `auto` |
| `--role` | `agent` | `agent` 또는 `auditor` |
| `--thread-id` | 자동 생성 | 체크포인트 세션 키 |
| `--dry-run` | 꺼짐 | 인덱스 확인 후 종료 |
| `--prompt-only` | 꺼짐 | 답변 LLM 없이 프롬프트까지 실행 |
| `--max-llm-calls` | `8` | 전송 시도 상한 |
| `--out` | 저장 안 함 | 결과 JSON 저장 위치 |

```bash
python run_retriever.py --help
```

CLI 결과는 stdout의 JSON 한 건임. 파일로도 남기려면 `--out` 사용함.

```bash
# 폴더로 지정: {thread_id}.json 으로 저장되어 data/logs/{thread_id}.jsonl 실행 로그와 이름이 대응됨
python run_retriever.py --query "연회비 면제 기준은?" --out data/answers

# .json 으로 끝나면 그 파일에 그대로 저장함(덮어씀)
python run_retriever.py --query "연회비 면제 기준은?" --out data/answers/my_answer.json
```

저장 경로는 stderr에 `결과 저장: {경로}`로 표시됨.  
실패한 실행도 같은 규칙으로 저장하므로, 검색까지 성공한 부분 결과와 `route.error`의 오류 상세를 남길 수 있음.

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

BM25 권한 마스크는 점수 융합 전에 적용됨. 제한 문서가 후보 자리를 먼저 차지하지 않음.

융합 뒤에도 동일한 권한 필터를 다시 적용하여 방어선을 유지함.

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

## 카드명 별칭과 날짜 표기 통일

색인이 만든 **별칭 사전**을 질의에도 똑같이 적용해, 사람이 줄여 부른 카드명과 문서의 정식 카드명이
같은 토큰이 되게 함. 날짜도 `2026년 2월`과 `2026-02`를 같은 토큰(`2026-02`)으로 맞춤.
규칙과 산출물은 인덱서가 만들며 자세한 내용은 `indexer/vector-bm25/README.md`에 있음.

- 활성 세대 포인터(`active_index.json`)의 `card_aliases`·`card_aliases_sha256`·`card_aliases_count`와
  manifest의 `card_aliases`를 읽어 파일 해시·건수·정렬 형식을 모두 검사함
- 검사를 통과한 별칭을 질의 토크나이저에 넣고, `alias_map_sha256`이 파일 해시와 같은지 다시 확인함
- manifest의 `tokenizer_signature`가 질의 토크나이저 서명과 다르면 시작하지 않음
  (토큰화 정책 버전 4. 별칭·날짜 규칙이 서명에 들어 있음)
- 별칭 산출물이 없는 이전 세대는 빈 별칭으로 읽어 그대로 검색 가능함.
  다만 서명이 정책 버전 4가 아니면 색인을 다시 만들어야 함

별칭 파일 1열은 **형태소 분석기에 등록할 표면형**이라 낱말 사이 공백을 가질 수 있음
(예: `가게모음 프리미엄<탭>한빛가게모음프리미엄`). 이 띄어 쓴 표면형 덕분에
"가게모음 프리미엄 혜택"처럼 띄어 쓴 질문이 기본 카드(`한빛가게모음`)로 잘못 치환되지 않음.
2열 정식 토큰에는 공백이 없어야 하며, 공백이 있으면 색인을 띄우지 않음.

## 색인용 텍스트(`index_text`)

인덱서는 D2 혜택 안내 청크에 `[카드: 한빛 가게모음 프리미엄 (D2-C040)]` 같은 머리말을 붙여 색인합니다.
이 머리말은 **색인에만** 들어가고 표시·인용에는 쓰지 않습니다.

| corpus 필드 | 뜻 | 검색기에서 쓰는 곳 |
|---|---|---|
| `text` | 원래 본문. 머리말 없음 | 검색 결과 표시, 프롬프트 근거, 인용 검증 |
| `index_text` | 머리말 + 본문. 머리말이 붙은 청크에만 있음 | BM25 색인·임베딩이 만들어진 기준이며, 문서빈도 통계도 이 값으로 셈 |

`index_text`가 없는 레코드는 `text`가 곧 색인용 텍스트이므로, 이 필드를 만들기 전 세대도 그대로 읽힙니다.
Chroma에 저장되는 document 본문도 머리말이 없는 원래 본문이므로 벡터 검색 결과의 인용문이 달라지지 않습니다.

## 질문 핵심어가 결과에 있는지 보기

"질문이 꼭 집어 물은 말이 검색 결과 안에 실제로 들어 있는가"를 판정하는 부품임.
**아직 검색 그래프나 API 응답에 연결하지 않았고**, 이후 근거 충분성 판정에서 쓰려고 따로 만들어 둠.
`app.bootstrap.create_keyword_coverage_service()`로 꺼내 씀.

| 단계 | 하는 일 | 두는 곳 |
|---|---|---|
| ① 형태소 분석 | 명사·숫자·코드만 남기고 동사·형용사·어미를 버림 | `infrastructure/korean_tokenizer.py` |
| ② 대상명 묶기·통일 | 사용자 사전으로 고유이름을 한 덩어리로, 별칭 사전으로 정식 이름으로 바꿈 | 같은 토크나이저(BM25 색인과 동일 경로) |
| ③ 핵심어 선별 | 드문 말(IDF 높은 말)만 남김 | `domain/keywords.py`(순수 함수) |
| ④ 결과와 대조 | 검색 결과도 같은 분석기로 잘라 핵심어가 있는지 확인 | `application/keyword_service.py` |

③의 세부 규칙은 다음과 같음. 별도 불용어표는 두지 않음 — 흔한 말은 IDF가 낮아 저절로 빠짐.

- 색인에 없는(df=0) **고유이름**은 남김. 카드명·별칭 사전 항목, Kiwi 고유명사(NNP), 숫자·코드·날짜 표준형이 해당함
- 색인에 없는(df=0) **일반명사**는 뺌. 질문자가 쓴 다른 표현일 뿐이라 결과 대조 기준이 되지 못함
- 전체 청크 중 `KEYWORD_MAX_DOC_RATIO` 이상에 나오는 말은 뺌

| 설정 | 뜻 | 기본값 |
|---|---|---|
| `KEYWORD_MAX_DOC_RATIO` | 이 비율 이상의 청크에 나오면 흔한 말로 보고 핵심어에서 뺌 | `0.80` |
| `KEYWORD_TOP_N` | "상위 핵심어가 결과에 없음"을 볼 때 상위 몇 개를 볼지 | `3` |

**기본값 0.80을 고른 근거**: 평가 질문 13건에 대해 사람이 고른 핵심어와 비교한 13건 평균임.

| ratio | 정밀도 | 재현율 | 평균 핵심어 수 |
|---|---|---|---|
| 1.0 | 0.65 | 0.89 | 7.9 |
| 0.8 | 0.65 | 0.82 | 7.3 |
| 0.7 | 0.67 | 0.75 | 6.5 |
| 0.6 | 0.56 | 0.49 | 4.9 |

0.7과 0.6 사이에서 재현율이 0.75 → 0.49로 급락함(`연회비`·`전월`·`실적`·`포인트`가 한꺼번에 빠짐).
절벽에서 떨어진 0.8을 기본값으로 두었고, 손으로 관리하던 불용어표 방식(0.66/0.81)과 같은 수준을 사전 없이 냄.
**이 수치는 현재 문서 묶음 195청크에서 잰 값이므로, 문서가 바뀌면 평가셋으로 다시 보정해야 함.**

출력은 핵심어 목록(토큰·df·idf·고유이름 여부), 결과별 포함 여부(`coverage`),
어느 결과에도 없는 핵심어(`missing`), 상위 핵심어 중 미포함(`top_missing(n)`)임.

순수 함수 규칙 시험은 `tests/check_keyword_rules.py`에 있음.
이 가상환경에는 pytest가 없으므로 그대로 실행해 확인함(통과하면 `keyword-rules-ok` 출력).

```powershell
.venv/Scripts/python.exe tests/check_keyword_rules.py
```

인덱서의 `pytest`도 이 스크립트를 하위 프로세스로 실행해 회귀를 함께 지킴.

## 코드 구조

계층별 의존 방향은 presentation → application ← infrastructure이며, 조립은 `app/bootstrap.py`만 담당함.  
domain은 표준 라이브러리만 사용하고, application은 포트(인터페이스)와 서비스를 소유함.

```text
vector-retriever/
├── run_retriever.py          # CLI 진입점 → presentation/cli.py
├── serve_retriever.py        # HTTP 서버 진입점 → presentation/api.py (설정은 bootstrap 경유)
├── eval_equivalence.py       # 4조합 동등성 평가 (bootstrap.create_service에 ForbiddenLLM 주입)
├── eval_retriever_matrix.py  # 질문 10건 × 4모드 검색 평가 (bootstrap.create_service 사용)
└── app/
    ├── bootstrap.py          # 설정 로딩 → 구현체 생성 → 서비스 조립 (create_resources·create_service)
    ├── domain/               # 표준 라이브러리만 쓰는 규칙
    │   ├── access.py         #   역할별 접근 등급·권한 필터
    │   ├── corpus.py         #   corpus 스냅샷 값 객체
    │   ├── keywords.py       #   질문 핵심어 선별·결과 대조 규칙
    │   ├── location.py       #   청크 위치 표기
    │   ├── search_filter.py  #   DB 중립 메타데이터 필터
    │   └── vector_search.py  #   벡터 검색 옵션·MMR 계산
    ├── application/          # 유스케이스·포트·DTO (외부 기술 import 없음, pydantic만 허용)
    │   ├── retriever_service.py  # RetrieverService: search·answer·stream·health 진입점
    │   ├── keyword_service.py    # KeywordCoverageService: 질문 핵심어 유무 판정(그래프 미연결)
    │   ├── ports.py              # 포트(Protocol + @abstractmethod), RetrieverGraphPort 포함
    │   ├── state.py              # 요청·결과·State DTO
    │   ├── errors.py             # 응용 오류 계약·오류 요약
    │   ├── llm_budget.py         # 서버 누적 LLM 호출 예산
    │   ├── query_transform.py    # 질문 변환 판정·가중 RRF·분해 질의 규칙
    │   ├── scoring.py            # 점수 융합·리랭크 적용·근거 검증
    │   └── runtime.py            # 타임아웃 실행기·감사 로그
    ├── infrastructure/       # 포트 구현체(포트를 명시적으로 상속)와 설정
    │   ├── graph.py              # LangGraph StateGraph 구성·노드, LangGraphRetrieverRunner
    │   ├── settings.py           # .env·환경변수 설정 로더
    │   ├── embedder.py           # KURE-v2 임베더(LazyHuggingFaceEmbedder)
    │   ├── chroma_store.py       # Chroma·메모리 벡터 저장소
    │   ├── bm25_index.py         # BM25S 키워드 검색
    │   ├── corpus_store.py       # 버전형 corpus 읽기
    │   ├── keyword_analyzer.py   # 핵심어 분석기(BM25 질의 토크나이저·corpus 통계 재사용)
    │   ├── korean_tokenizer.py   # Kiwi 한국어 토크나이저(카드명 사전·별칭 치환·날짜 표기 통일)
    │   ├── reranker.py           # Cross-Encoder 리랭커
    │   ├── llm_client.py         # Groq·Claude·OpenAI 구조화 출력 클라이언트
    │   └── transform_cache.py    # 질문 변환 결정 캐시
    └── presentation/         # application 서비스만 사용
        ├── api.py                # FastAPI·SSE, create_app(service=None)
        └── cli.py                # CLI, main(argv, service=None)
```

`create_app(service=None)`과 `cli.main(argv, service=None)`은 서비스를 넘기면 그대로 사용하고,  
넘기지 않으면 `app.bootstrap.create_service()`로 조립함.

## 실행 파일과 감사 로그

| 경로 | 내용 |
|---|---|
| `../../indexer/vector-bm25/data/active_generation.json` | Indexer가 게시한 활성 세대 포인터(두 색인 경로) |
| `../../indexer/vector-bm25/data/generations/<세대>/` | 세대별 Chroma와 버전형 corpus·BM25S 색인 |
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

2026-09-29 KURE-v2 색인(483건·768차원) 측정 결과는 다음과 같음.  
기준 값은 KURE-v1 시절 확정한 기준선이며 변경하지 않았음.

| 조합 | 기준 | 실측 | 판정 |
|---|---:|---:|---|
| `vector/off` | 6/7·2.125 | 6/7·1.875 | 통과 |
| `hybrid/off` | 6/7·2.375 | 6/7·1.625 | 통과 |
| `hybrid/auto` | 7/7·1.125 | 6/7·1.625 | 미달 |
| `hybrid_rerank/auto` | 7/7·1.375 | 6/7·1.625 | 미달 |

측정은 198초에 종료 코드 1로 끝났으며 `all_methods_meet_baseline=false`임.  
답변·라우터 LLM 네트워크 호출은 0회임.  
네 조합 모두 q6에서 `D1_0010`은 1위지만 `D2_0003`이 Top-5 밖이라 실패함.  
구조 정리 전 코드로 같은 조건을 다시 측정해도 순위·점수가 행 단위로 같았으므로  
미달 원인은 코드 변경이 아니라 색인 모델 교체(KURE-v1 → KURE-v2)로 판단됨.  
기준선을 KURE-v2 기준으로 다시 정할지, 검색 설정을 조정할지는 결정 필요 사항임.

KURE-v1 색인(485건·1,024차원)에서는 2026-09-13 A안 적용 뒤 네 조합 모두 기준선을 통과했음.  
A안 적용 전 `hybrid_rerank/auto`의 6/7·1.625 미달은 KURE-v1 시점의 변경 전 이력임.
비교 이력은 `../COMPARISON.md`, 전체 검증 범위는 `../verify-report.md` 참고 대상임.
