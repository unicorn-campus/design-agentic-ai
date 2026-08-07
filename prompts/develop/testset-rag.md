# dp: RAG 평가 테스트셋 생성 개발 프롬프트 (런치픽 v1)

> 이 파일 전체를 AI 코딩 도구에 붙여 넣어 코드를 생성함. 이 문서 자체는 코드가 아님.  
> 채택 모듈: `references/dev-prompt-guide.md` 3.2(LLM) · 3.7(검색 품질 평가) · 3.9(개발 디렉토리)  
> 3.1(LangChain 공통) 미채택 사유 — 테스트셋 생성은 노드 간 상태 공유가 없는 **단발 배치 스크립트**라
> LangGraph 워크플로우가 필요 없음. 다만 3.1의 LCEL 실행 방식 `[기준]`과 Structured Output `[고정]` 2항만 준용함.  

> 실행 순서 — ① `gen-data` → ② `index-rag` → ③ `index-graphrag` → ④ `testset-rag` →  
> ⑤ `testset-graphrag` → ⑥ `backend` → ⑦ `frontend`.  
> ⑥ 백엔드는 ③까지 끝나면 ④⑤를 기다리지 않고 시작 가능함(평가는 백엔드를 막지 않음). ⑦ 프론트는 ⑥의 API 경계가 확정된 뒤 시작함

---

## [목표]

런치픽 v1 **벡터 RAG의 평가 테스트셋(골든셋)과 RAGAS 평가 실행기**를 개발하여, 질문 · 정답 · 기대 문맥
3요소를 라벨링한 28문항을 버전 관리 파일로 만들고 RAGAS 4지표 실측값을 산출하는 파이썬 패키지를 만듦.

---

## [역할]

당신은 데이터 엔지니어 8년 + 대규모 RAG 구축 5년 경력의 **지식 · 데이터 엔지니어**임.  
RAGAS 평가 설계, 골든셋 라벨링, 회귀 평가 운영에 능숙하며 문항 수가 합격선의 눈금을 결정한다는 것을
계산으로 다룰 줄 앎.  
"정답지를 먼저 만들고 검색을 고친다"는 순서를 지키며, **목표 미달 값을 고쳐 통과시키지 않음**.

---

## [맥락]

- 내 상황: ② `index-rag.md`가 벡터 RAG를 구축했으나 **검색 품질을 잴 자가 없음**. 런치픽은 미출시
  서비스라 문의 로그가 0건이므로, 골든셋을 **유저스토리 `[검증 요구사항]` 1항목 = 1문항** 방식으로 만듦
  (근거: `textbook/script/05-jisikni.md` S14 강의 노트). v1은 그 방식을 합성 소스에 맞춰 적용함
- 이 테스트셋은 **회귀 평가용**임. 청킹 값 · 가중치 · 리랭킹을 바꿀 때마다 같은 문항으로 다시 재서
  좋아졌는지 나빠졌는지 봄. 그래서 문항이 바뀌면 버전을 올림
- 결과물 독자: 검색 파이프라인을 손볼 개발자, 품질 목표를 검토할 아키텍트

---

## [입력]

우선순위 순으로 읽음. 앞 자료가 뒤 자료와 충돌하면 앞 자료를 따름.

1. **팀 규칙**: `AGENTS.md` — 마크다운 작성 가이드 · 정직한 보고 규칙
2. **프롬프트 표준**: `references/prompt-guide.md` — 8섹션 표준
3. **선행 산출물(필수)**: `src/v1/rag/store/manifest.json` — 평가 대상 인덱스의 실체.
   **컬렉션 이름 `lunchpick_rag_v1`** · 임베딩 모델 · 청킹 값이 여기 있음.
   **없으면 이 작업을 시작하지 않고 사용자에게 문의함**
4. **선행 산출물(필수)**: `src/v1/data/rag/` — 문항의 정답과 기대 문맥을 뽑아 올 원본 문서
5. **선행 산출물(필수)**: `src/v1/data/quality_report.json` — 오염 문서 목록. **방어 문항 4건의 재료**임
6. **선행 산출물(필수)**: `src/v1/app/common/doc_schema.py` — 메타데이터 키. `reference_doc_ids`가
   이 모델의 `doc_id`와 같은 값이어야 함
7. **선행 산출물(참조)**: `src/v1/rag/retriever/` — 평가 실행기가 호출할 리트리버.
   응답 항목 이름(`chunk_text` · `doc_id` · `rerank_score`)을 그대로 씀
8. **교재 원고**: `textbook/script/05-jisikni.md` — 아젠다(S13 · S14)만 보고 개발에 필요한 정보만 추출.
   골든셋 만드는 법 · 2인 라벨링 · 합격선 수치가 여기 있음
9. **라이브러리 문법 확인**: **context7 MCP** — RAGAS 지표 클래스명 · `EvaluationDataset` 필드명은
   버전에 따라 달라지므로 **반드시 여기서 확인**함

---

## [처리]

### 1단계 — 코드 base directory 확인 (가장 먼저 수행)

- 기본값 `src/v1/` 을 사용자에게 제시하고 다른 값을 받으면 **모든 산출 경로의 접두를 그 값으로 바꿈**
- 기본값을 그대로 쓰기로 하면 되묻지 않고 2단계로 진행함

### 2단계 — 평가 대상 확인

- `src/v1/rag/store/manifest.json`을 읽어 컬렉션 이름 · 임베딩 모델 · 청킹 값 · 색인 문서 수를 확인함
- 컬렉션 이름이 **`lunchpick_rag_v1`이 아니면 중단하고 사용자에게 문의함**(평가 대상 불일치)
- 색인이 비어 있으면 중단하고 ② `index-rag.md`를 먼저 돌리도록 안내함

### 3단계 — 문항 수 산정 (근거 있는 숫자로 정함)

**규정** — 비율 목표를 재려면 **필요 표본 ≥ 1 ÷ (1 − 목표비율)** 이어야 함.
문항이 그보다 적으면 눈금이 커져 합격선이 사실상 100%가 됨(근거: `textbook/script/05-jisikni.md` S14).

- 여기에 **문항군당 하한 20문항**을 함께 적용함. 계산값과 하한 중 **큰 쪽**을 씀
- 목표 비율이 미정이면 하한 20문항으로 만들고 목표치는 **사용자 문의**로 남김
- v1 산정 결과

  | 항목 | 값 | 산출 근거 |
  |------|-----|----------|
  | 최대 목표 비율 | 0.90 (Context Recall) | 아래 6단계 목표표 |
  | 계산 하한 | `1 ÷ (1 − 0.90)` = **10** | 위 규정 |
  | 문항군 하한 | **20** | 위 규정 |
  | 지표 문항 수 | **24** (문항군 3종 × 8) | 20 이상이면서 3으로 나눠떨어지는 최소값 |
  | 방어 문항 수 | **4** | `quality_report.json` 오염 문서 3건 + 정상 위장 1건 |
  | **총 문항 수** | **28** | |

### 4단계 — 문항 생성 (`src/v1/eval/testset/build_rag_testset.py`)

#### 4-1. 문항군 3종 (각 8문항, 지표 계산 대상)

| 문항군 | ID 접두 | 답이 나오는 방식 | 대표 질문 예 |
|--------|--------|----------------|-------------|
| 사실 조회 | `Q-RAG-A` | 메뉴 문서 1 ~ 2청크에 답이 있음 | `돼지국밥에 들어가는 재료는` |
| 이유 해석 | `Q-RAG-B` | 추천 이유 예문 여러 건을 모아야 답이 됨 | `비 오는 날 국물 요리를 추천하는 이유는` |
| 조건 결합 | `Q-RAG-C` | 지역 · 카테고리 메타데이터 필터가 함께 걸림 | `여의도에 있는 파스타집은 어떤 곳인가` |

- 문항은 **원본 문서에서 역으로 만듦**. 문서를 먼저 고르고 → 그 문서로만 답할 수 있는 질문을 씀 →
  그 문서 `doc_id`를 `reference_doc_ids`에 적음. 순서를 거꾸로 하면 정답 문서를 특정할 수 없음
- 질문 문장은 **사용자가 실제로 칠 법한 구어체**로 씀. 문서 문장을 그대로 베끼면 검색이 너무 쉬워져
  지표가 부풀음. 같은 뜻을 **다른 낱말**로 씀(예 문서 `육수가 진함` → 질문 `국물 진한가`)
- 문항군마다 **결측 주입 문서를 근거로 하는 문항 1건 이상**을 넣음(`missing_fields`가 빈 배열이 아닌 문서).
  원천이 비면 검색이 어떻게 되는지 재는 자리임

#### 4-2. 방어 문항 4건 (`Q-RAG-X`, 지표 계산 제외)

- `quality_report.json`의 `poison_docs` 3건을 노리는 질의 3건 + 오염 문구를 정상 질문처럼 위장한 1건
- **기대 결과는 "검색 결과 0건 또는 오염 문서 미포함"** 이며, `metric_eligible: false`로 표시함
- 이 4건은 RAGAS 점수에 넣지 않고 **통과 / 실패 2치**로 따로 집계함

#### 4-3. 문항 파일 규격 (`src/v1/eval/testset/rag_testset_v1.jsonl`)

JSON Lines 1행 = 1문항. 아래 키를 **전부** 채움. 키 이름을 바꾸지 않음.

```json
{
  "qid": "Q-RAG-A-01",
  "question_group": "fact",
  "user_input": "돼지국밥에 뭐가 들어가나요",
  "reference": "돼지고기와 간장(대두)이 들어감. 새우젓으로 간을 맞춤.",
  "reference_contexts": ["돼지고기를 오래 고아 낸 육수에 밥을 말아 내는 국물 요리임 ..."],
  "reference_doc_ids": ["RAG-MNU-000001"],
  "metric_eligible": true,
  "expected_empty": false,
  "source_missing_fields": [],
  "labeler_a": "정답 일치",
  "labeler_b": "정답 일치",
  "agreed": true,
  "testset_version": "v1.0.0",
  "created_at": "2026-08-07T00:00:00+09:00"
}
```

- `user_input` · `reference` · `reference_contexts` 3요소가 3.7 `[고정]`이 요구하는
  **질문 · 정답(ground truth) · 기대 문맥(reference contexts)** 임
- Pydantic 모델을 `src/v1/eval/testset/schema.py`에 두고 생성 · 검증 · 실행기가 전부 이 모델을 씀
- 문항 생성은 **Structured Output**(3.1 `[고정]` 준용)으로 받음. 문자열을 정규식으로 뜯지 않음

#### 4-4. 2인 라벨링과 폐기 규칙

- 원칙은 **사람 2명이 따로 풀어 답이 갈리면 그 문항을 버리는 것**임
  (근거: `textbook/script/05-jisikni.md` S14)
- 이 구현에서는 **서로 다른 시드 · 서로 다른 프롬프트로 2회 라벨링**하여 대체함.
  두 결과가 다르면 `agreed: false`로 두고 `src/v1/eval/testset/discarded_v1.jsonl`에 사유와 함께 옮김
- **이 대체가 사람 검토와 동등하지 않음을 README에 명시**하고, 사람 검토를 붙일지는 **사용자 문의**로 남김
- 폐기 후 남은 지표 문항이 **20문항 미만이면 부족분을 다시 생성**함(3단계 하한 유지)

### 5단계 — 평가 실행기 구현 (`src/v1/eval/run_rag_eval.py`)

1. `rag_testset_v1.jsonl`을 읽어 `metric_eligible: true` 문항만 지표 대상으로 분리함
2. 각 문항의 `user_input`으로 **② 리트리버(`src/v1/rag/retriever`)를 호출**해
   `retrieved_contexts`(상위 5건 `chunk_text`)와 `retrieved_doc_ids`를 받음
3. 검색 문맥으로 답변을 생성해 `response`를 만듦(생성 지표 2종에 필요함)
4. RAGAS로 4지표를 계산함
5. 방어 문항 4건은 별도로 돌려 **오염 문서가 결과에 0건**인지 통과 / 실패로 집계함
6. 결과를 파일로 남김

#### 5-1. 지표 이름 — 4개 파일이 **같은 문자열**을 씀

`src/v1/eval/metrics_config.py`에 **한 벌만** 정의하고 ⑤ `testset-graphrag.md`가 여기에 추가만 함.

| 우리 키(고정 문자열) | 한 줄 뜻 | RAGAS 대응 |
|---------------------|---------|-----------|
| `context_recall` | 정답에 필요한 문맥을 빠짐없이 검색했는가 | Context Recall |
| `context_precision` | 검색된 문맥 **위쪽**에 관련 청크가 있는가 | Context Precision |
| `faithfulness` | 생성 답변이 검색 문맥에 근거하는가(환각 탐지) | Faithfulness |
| `answer_relevancy` | 답변이 질문 의도에 부합하는가 | Answer Relevancy |

- RAGAS 클래스명과 데이터셋 필드명(`user_input` · `response` · `retrieved_contexts` · `reference`)은
  버전에 따라 달라지므로 **context7 MCP로 확인한 뒤** 코드에 씀. 기억으로 쓰지 않음
- **NDCG는 이 파일에서 계산하지 않음.** 순위 지표는 ⑤ GraphRAG Local 질의에만 붙임
  (근거: dev-prompt-guide 3.4 완료조건은 RAGAS 4지표만 요구함)

#### 5-2. 목표치 — **전부 `가정값`** 임

| 지표 | 목표치 | 표기 | 근거 |
|------|--------|------|------|
| `context_recall` | **≥ 0.90** | 가정값 | v0 합격선 `정답 포함률 90% 이상`을 준용(`textbook/script/05-jisikni.md` S14) |
| `context_precision` | **≥ 0.80** | 가정값 | 실측 이력 없음. 첫 회 실측 후 재조정 대상 |
| `faithfulness` | **≥ 0.90** | 가정값 | v0 `근거 동반 노출률 100%`보다 낮춰 잡음 — 생성 문장은 결정론이 아님 |
| `answer_relevancy` | **≥ 0.85** | 가정값 | v0 `근거 태그 일치율 95% 이상`이 이미 `추정`값이라 그대로 쓰지 않음 |
| 방어 문항 통과율 | **100%** | **가정값 아님** | v0 `M-Q4 하드필터 위반 노출 0건` 실측 통과와 같은 성격 |

- 실데이터로 검증하지 않은 수치는 결과 보고서에 **`가정값`이라고 그대로 표기**함
- **목표에 못 미치면 목표치를 낮춰 통과시키지 않음.** 실측을 그대로 적고 원인 후보를 나열함
  (v0가 M-Q1 목표 3,000ms에 실측 6,343ms를 그대로 남긴 사례 — `src/README.md` 3절 · 4-1절)

#### 5-3. 결과 산출물

- `src/v1/eval/results/rag_eval_{YYYYMMDD-HHMM}.json` — 지표별 평균 · 문항별 점수 ·
  리트리버 설정 스냅샷(컬렉션 이름 · 청킹 값 · 가중치 · top-k) · 테스트셋 버전
- `src/v1/eval/results/rag_eval_{YYYYMMDD-HHMM}.md` — 사람이 읽는 점수표.
  지표 · 목표치 · 실측값 · 판정(통과 / 미달) · `가정값` 표기 · 미달 지표의 최저 점수 문항 3건

### 6단계 — 기술적 요구사항

- **API Key** — `.env`에서만 읽음. 필요 키: `GROQ_API_KEY`(문항 생성 · 답변 생성 · RAGAS 평가 LLM) ·
  `OPENAI_API_KEY`(리트리버가 쓰는 임베딩) · `COHERE_API_KEY`(리트리버 리랭킹)
- **Config와 소스 분리** — 문항 수 · 목표치 · 테스트셋 버전 · 결과 경로는 전부
  `src/v1/app/common/config.py`가 `src/v1/app/common/settings.yaml`에서 읽음. 매직 넘버를 두지 않음
- **LLM 사양**(3.2 `[고정]`) — Groq LPU · 모델 `openai/gpt-oss-120b` · `temperature=0` ·
  `timeout=30초` · 429 응답 시 지수 백오프 재시도 2회
  - RAGAS 평가용 LLM도 **같은 모델**을 씀. 다른 모델을 쓰려면 **사용자 문의**
  - `temperature=0`은 재현성 때문임 — 같은 테스트셋을 다시 돌려 점수가 흔들리면 회귀 평가가 무의미해짐
- **시스템 프롬프트와 유저 프롬프트 분리**(3.1 `[고정]` 준용) — 문항 생성 규칙은 시스템, 원본 문서는 유저에 둠
- **LCEL 실행 방식**(3.1 `[기준]` 준용) — 조건 → 선택

  | 조건 | 선택 |
  |------|------|
  | 문항 28건 배치 생성 | **`ainvoke`**(비동기) |
  | 평가 실행기가 문항 28건을 연속 호출 | **`ainvoke`**(비동기) |
  | 문항 1건 확인용 CLI(`--dry-run`) | **`invoke`**(동기) |

- **버전 관리**(3.7 `[고정]`) — 파일명에 버전을 박고(`rag_testset_v1.jsonl`) 각 행에도
  `testset_version`을 넣음. 문항이 1건이라도 바뀌면 **마이너 버전을 올리고 변경 이력을
  `src/v1/eval/testset/CHANGELOG.md`에 남김**. 옛 버전 파일을 지우지 않음(회귀 비교 대상임)

### 7단계 — 테스트 및 버그 수정

- 프레임워크 **pytest**, 모듈별 단위 테스트를 `src/v1/tests/eval/`에 작성함
- **LLM · 리트리버 호출은 Mock/fixture로 대체**함. 실제 호출 시험은 `@pytest.mark.integration`으로 분리함
- 최소 시험 항목
  1. `rag_testset_v1.jsonl` 전 행이 `schema.py` Pydantic 모델 검증을 통과함
  2. 지표 문항이 **20건 이상**이고 문항군 3종이 각각 존재함(3단계 하한 규정)
  3. 모든 `reference_doc_ids`가 `src/v1/data/rag/` 에 실재하는 `doc_id`임(끊긴 참조 0건)
  4. 방어 문항 4건이 전부 `metric_eligible: false`이고 `expected_empty: true`임
  5. `agreed: false` 문항이 본 파일에 남아 있지 않음(폐기 파일로 옮겨짐)
  6. 지표 키 4종이 `metrics_config.py` 문자열과 정확히 일치함
  7. 같은 테스트셋 · 같은 인덱스로 2회 평가 시 지표 평균 차이가 0.02 이하임(재현성)
  8. 목표 미달 시 실행기가 **점수를 조정하지 않고** 판정을 `미달`로 적음

### 8단계 — README.md 작성 (`src/v1/eval/README.md`)

- 개요 — 목적 및 주요 기능
- 가상환경 설정 및 실행 — **Windows GitBash · Windows PowerShell · Linux/Mac 3환경** 명령어 각각 기재
- **평가 흐름 가시화 — Mermaid 스크립트**로 `테스트셋 → 리트리버 호출 → 답변 생성 → RAGAS → 점수표` 흐름을 그림
- 디렉토리 구조와 주요 소스 설명
- **문항 수 산정 근거** — `1 ÷ (1 − 목표비율)` 계산 과정과 하한 20 적용 결과
- **목표치표와 `가정값` 표기** — 어느 수치가 실측 근거를 갖고 어느 수치가 가정인지 구분해 적음
- **2인 라벨링 대체 방식의 한계**를 명시함

### 톤앤매너

- 코드 주석과 README는 **한국어 명사체**로 씀. 목표치에는 근거 파일을 주석으로 인용함
- 전문 용어는 처음 나올 때 괄호로 쉬운 설명 1회 — 예:
  `골든셋(정답을 미리 적어 둔 시험지)` · `회귀 평가(고친 뒤에도 예전만큼 나오는지 다시 재는 일)`

---

## [출력]

| 산출물 | 경로 |
|--------|------|
| 테스트셋 생성기 | `src/v1/eval/testset/build_rag_testset.py` · `src/v1/eval/testset/schema.py` |
| 테스트셋 | `src/v1/eval/testset/rag_testset_v1.jsonl` (28문항) |
| 폐기 문항 | `src/v1/eval/testset/discarded_v1.jsonl` |
| 변경 이력 | `src/v1/eval/testset/CHANGELOG.md` |
| 지표 정의(공용) | `src/v1/eval/metrics_config.py` (**신규 생성** — ⑤가 여기에 추가만 함) |
| 평가 실행기 | `src/v1/eval/run_rag_eval.py` |
| 평가 결과 | `src/v1/eval/results/rag_eval_{YYYYMMDD-HHMM}.json` · `.md` |
| 설정 | `src/v1/app/common/settings.yaml` (기존 파일에 **키 추가만** 함) |
| 의존성 | `src/v1/requirements.txt` (기존 줄 삭제 · 변경 없이 **추가만** 함) |
| 시험 | `src/v1/tests/eval/` |
| 문서 | `src/v1/eval/README.md` |

---

## [제약조건]

### MUST

- 프롬프트 작성 가이드(`references/prompt-guide.md`) 준용
- **반드시 "context7 MCP" 사용** — RAGAS 지표 클래스명 · `EvaluationDataset` 필드명 · LangChain 문법을
  기억에 의존해 쓰지 않음
- 반드시 의존성을 `src/v1/requirements.txt`에 정의함(Python 한정)
- README.md의 가상환경 활성화는 **Windows GitBash · Windows PowerShell · Linux/Mac**별 명령어를 안내함
- **실데이터로 검증하지 않은 수치는 `가정값`으로 표기**함(정직한 보고 규칙)
- 추가정보나 의사결정이 필요하면 **사용자에게 반드시 문의**함. 이미 확인된 문의 대상은 아래임
  - 코드 base directory (기본값 `src/v1/`)
  - 4개 목표치(가정값)를 확정값으로 승격할지, 첫 회 실측 후 다시 정할지
  - 2인 라벨링에 **사람 검토**를 붙일지(현재는 시드 2회 생성으로 대체함)
  - RAGAS 평가용 LLM을 Groq `gpt-oss-120b`가 아닌 다른 모델로 쓸지

### MUST NOT

- **추측하여 생성하지 않음.** 데이터에 기반하여 수행함
  - `src/v1/data/rag/`에 없는 내용을 정답으로 적지 않음
  - 실재하지 않는 `doc_id`를 `reference_doc_ids`에 적지 않음
- 지표 키 4종(`context_recall` · `context_precision` · `faithfulness` · `answer_relevancy`)과
  컬렉션 이름 `lunchpick_rag_v1`을 **임의로 바꾸지 않음**(② · ⑤와 문자열이 같아야 함)
- **목표 미달 시 목표치를 낮추거나 문항을 빼서 통과시키지 않음**
- 문항 수를 3단계 규정(`1 ÷ (1 − 목표비율)`, 하한 20) 미만으로 줄이지 않음
- 방어 문항을 RAGAS 지표 평균에 포함하지 않음
- `src/` 아래 v0 파일을 **수정하지 않음**(읽기 전용). 산출물은 전부 `src/v1/` 아래에만 만듦
- 옛 버전 테스트셋 파일을 삭제하지 않음

### 완료조건 — 검증 가능한 증거 기준

1. **산출 파일 목록 제시** — 위 `[출력]` 표 경로의 실제 `ls` 결과 첨부
2. **pytest 실행 로그 첨부** — `python -m pytest src/v1/tests/eval -v` 결과가 **실패 0건**임
3. **테스트셋 실측 집계 첨부** — 총 문항 수 · 문항군별 문항 수 · 방어 문항 수 · 폐기 문항 수와 사유
4. **샘플 문항 최소 3건의 전문 첨부** — 문항군 3종에서 1건씩(3요소가 다 채워졌음을 보임)
5. **RAGAS 실측 점수표 첨부** — 지표 4종의 실측값 · 목표치 · `가정값` 표기 · 판정.
   방어 문항 4건의 통과 / 실패도 함께 적음
6. **샘플 질의 최소 3건의 실행 로그(요청 → 응답) 첨부** — 평가 실행기가 리트리버를 호출해
   상위 5건을 받아 답변을 만든 전 과정
7. 목표에 못 미치는 값이 나오면 **값을 고쳐 통과시키지 않고 실측을 그대로 보고**하고
   원인 후보(청킹 값 · 가중치 · 리랭킹 · 원천 결측)를 나열함

---

## [예시]

**테스트셋 1행의 기대 형태** (조건 결합 문항군)

```json
{
  "qid": "Q-RAG-C-03",
  "question_group": "condition",
  "user_input": "여의도에 파스타 하는 데 어떤 곳 있어요",
  "reference": "여의도 지역의 양식-파스타 카테고리 식당 소개 문서에 있는 상호 · 도보 시간 · 분위기",
  "reference_contexts": ["[restaurant] 소담키친 · 양식-파스타 · 여의도\n경로: ...\n---\n..."],
  "reference_doc_ids": ["RAG-RST-000212", "RAG-RST-000377"],
  "metric_eligible": true,
  "expected_empty": false,
  "source_missing_fields": [],
  "labeler_a": "정답 일치", "labeler_b": "정답 일치", "agreed": true,
  "testset_version": "v1.0.0",
  "created_at": "2026-08-07T00:00:00+09:00"
}
```

**평가 결과 점수표의 기대 형태** (`rag_eval_20260807-1030.md` 일부)

| 지표 | 목표치 | 표기 | 실측 | 판정 |
|------|--------|------|------|------|
| `context_recall` | 0.90 | 가정값 | 0.83 | **미달** |
| `context_precision` | 0.80 | 가정값 | 0.86 | 통과 |
| `faithfulness` | 0.90 | 가정값 | 0.94 | 통과 |
| `answer_relevancy` | 0.85 | 가정값 | 0.88 | 통과 |
| 방어 문항 통과율 | 100% | — | 100% (4/4) | 통과 |

> `context_recall` 미달을 목표치 0.80으로 낮춰 통과시키지 않음. 최저 점수 문항 3건과
> 원인 후보(원천 결측 문서 근거 문항 3건이 전부 하위에 있음)를 함께 적음.

**하지 말아야 할 형태 (anti-example)**

```json
{ "qid": "Q-RAG-A-01", "user_input": "돼지국밥 재료는?", "reference": "돼지고기 등" }
```

> `reference_contexts` · `reference_doc_ids`가 없음 = **기대 문맥이 없어 Context Recall을 못 잼**.
> 3.7 `[고정]`이 요구하는 3요소가 다 채워져야 함.
