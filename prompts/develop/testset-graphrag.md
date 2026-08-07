# dp: GraphRAG 평가 테스트셋 생성 개발 프롬프트 (런치픽 v1)

> 이 파일 전체를 AI 코딩 도구에 붙여 넣어 코드를 생성함. 이 문서 자체는 코드가 아님.  
> 채택 모듈: `references/dev-prompt-guide.md` 3.2(LLM) · 3.7(검색 품질 평가) · 3.9(개발 디렉토리)  
> 3.1(LangChain 공통) 미채택 사유 — 테스트셋 생성은 노드 간 상태 공유가 없는 **단발 배치 스크립트**라
> LangGraph 워크플로우가 필요 없음. 다만 3.1의 LCEL 실행 방식 `[기준]`과 Structured Output `[고정]` 2항만 준용함.  

> 실행 순서 — ① `gen-data` → ② `index-rag` → ③ `index-graphrag` → ④ `testset-rag` →  
> ⑤ `testset-graphrag` → ⑥ `backend` → ⑦ `frontend`.  
> ⑥ 백엔드는 ③까지 끝나면 ④⑤를 기다리지 않고 시작 가능함(평가는 백엔드를 막지 않음). ⑦ 프론트는 ⑥의 API 경계가 확정된 뒤 시작함

---

## [목표]

런치픽 v1 **GraphRAG의 평가 테스트셋(골든셋)과 평가 실행기**를 개발하여, Local 20문항 · Global 20문항 ·
방어 4문항을 검색 모드별로 나눠 라벨링하고 모드별 지표(RAGAS + NDCG) 실측값을 산출하는 파이썬 패키지를 만듦.

---

## [역할]

당신은 데이터 엔지니어 8년 + 대규모 지식그래프 구축 5년 경력의 **지식 · 데이터 엔지니어**임.  
RAGAS 평가 설계, NDCG 순위 지표 계산, 다홉 질의 골든셋 라벨링, 회귀 평가 운영에 능숙함.  
"정답지를 먼저 만들고 검색을 고친다"는 순서를 지키며, **목표 미달 값을 고쳐 통과시키지 않음**.

---

## [맥락]

- 내 상황: ③ `index-graphrag.md`가 지식그래프를 구축했으나 **검색 품질을 잴 자가 없음**.
  GraphRAG는 구축 비용이 크므로 "그 비용을 치를 값을 하는가"를 숫자로 보여야 함
- v0는 그래프 검색을 **비용 때문에 뺐음**(근거: `textbook/script/05-jisikni.md` S14 강의 노트).
  v1이 그 판단을 다시 하려면 **④ 벡터 RAG 실측값과 나란히 놓고 비교할 수 있는 숫자**가 필요함.
  그래서 지표 키 문자열과 평가 절차를 ④와 맞춤
- GraphRAG는 **검색 모드마다 재는 것이 다름**. Local은 "맞는 것을 위쪽에 올렸는가"(순위)가 중요하고,
  Global은 "요약이 근거에 붙어 있는가"(환각)가 중요함. 그래서 모드별로 지표를 나눔
- 결과물 독자: 검색 파이프라인을 손볼 개발자, GraphRAG 존치 여부를 판단할 아키텍트

---

## [입력]

우선순위 순으로 읽음. 앞 자료가 뒤 자료와 충돌하면 앞 자료를 따름.

1. **팀 규칙**: `AGENTS.md` — 마크다운 작성 가이드 · 정직한 보고 규칙
2. **프롬프트 표준**: `references/prompt-guide.md` — 8섹션 표준
3. **선행 산출물(필수)**: `src/v1/kg/store/manifest.json` — 평가 대상 그래프의 실체.
   **데이터베이스 이름 `lunchpick_kg_v1`** · 벡터 인덱스 이름 · 커뮤니티 수가 여기 있음.
   **없으면 이 작업을 시작하지 않고 사용자에게 문의함**
4. **선행 산출물(필수)**: `src/v1/kg/indexer/schema.yaml` — 확정된 개체 8종 · 관계 9종.
   **문항이 이 타입 밖의 관계를 묻지 않게** 하는 근거임
5. **선행 산출물(필수)**: `src/v1/data/kg/` — 문항의 정답과 기대 문맥을 뽑아 올 원본 문서
6. **선행 산출물(필수)**: `src/v1/data/quality_report.json` — 오염 문서 목록(**방어 문항 4건의 재료**)과
   `broken_kg_paths`(**`no_path` 기대 문항의 재료**)
7. **선행 산출물(필수)**: `src/v1/eval/metrics_config.py` — ④ `testset-rag.md`가 만든 지표 키 정의.
   **여기에 키를 추가만 하고 기존 키를 고치지 않음**
8. **선행 산출물(참조)**: `src/v1/kg/retriever/` — 평가 실행기가 호출할 리트리버.
   응답 항목 이름(`selected_mode` · `paths` · `community_summaries` · `evidence_doc_ids` ·
   `no_path`)을 그대로 씀
9. **선행 산출물(참조)**: `src/v1/eval/results/rag_eval_*.json` — ④의 벡터 RAG 실측값. **비교 대상**임
10. **교재 원고**: `textbook/script/05-jisikni.md` — 아젠다(S13 · S14)만 보고 개발에 필요한 정보만 추출
11. **라이브러리 문법 확인**: **context7 MCP** — RAGAS 지표 클래스명 · `EvaluationDataset` 필드명 ·
    Neo4j 문법은 버전에 따라 달라지므로 **반드시 여기서 확인**함

---

## [처리]

### 1단계 — 코드 base directory 확인 (가장 먼저 수행)

- 기본값 `src/v1/` 을 사용자에게 제시하고 다른 값을 받으면 **모든 산출 경로의 접두를 그 값으로 바꿈**
- 기본값을 그대로 쓰기로 하면 되묻지 않고 2단계로 진행함

### 2단계 — 평가 대상 확인

- `src/v1/kg/store/manifest.json`을 읽어 DB 이름 · 노드 수 · 관계 수 · 커뮤니티 수를 확인함
- DB 이름이 **`lunchpick_kg_v1`이 아니면 중단하고 사용자에게 문의함**(평가 대상 불일치)
- **`community_count`가 0이면 Global 문항을 만들 수 없으므로 중단**하고 ③ 단계의
  커뮤니티 탐지 · 요약(`S-KI7` · `S-KI8`)을 먼저 돌리도록 안내함
- `src/v1/eval/metrics_config.py`가 없으면 ④ `testset-rag.md`를 먼저 돌리도록 안내함

### 3단계 — 문항 수 산정 (근거 있는 숫자로 정함)

**규정** — 비율 목표를 재려면 **필요 표본 ≥ 1 ÷ (1 − 목표비율)** 이어야 함.
문항이 그보다 적으면 눈금이 커져 합격선이 사실상 100%가 됨(근거: `textbook/script/05-jisikni.md` S14).

- **목표 비율이 걸린 문항군마다 따로 적용**함. Local과 Global은 지표가 다르므로 **별개 문항군**임
- 여기에 **문항군당 하한 20문항**을 함께 적용하고, 계산값과 하한 중 **큰 쪽**을 씀
- 목표 비율이 미정이면 하한 20문항으로 만들고 목표치는 **사용자 문의**로 남김
- v1 산정 결과

  | 문항군 | 최대 목표 비율 | 계산 하한 | 문항군 하한 | **채택 문항 수** |
  |--------|--------------|----------|------------|----------------|
  | **Local** | 0.85 (Context Recall) | `1 ÷ (1 − 0.85)` = 6.67 → **7** | 20 | **20** |
  | **Global** | 0.85 (Faithfulness) | `1 ÷ (1 − 0.85)` = 6.67 → **7** | 20 | **20** |
  | **방어**(지표 제외) | — | — | — | **4** |
  | | | | **총계** | **44** |

- Local 20문항의 내부 배분 — 1홉 4 · 2홉 5 · 3홉 5 · 4홉 4 · `no_path` 기대 2.
  홉 수를 고루 섞지 않으면 "쉬운 질문만 맞히는 그래프"가 통과함

### 4단계 — 문항 생성 (`src/v1/eval/testset/build_kg_testset.py`)

#### 4-1. Local 문항군 (`Q-KG-L`, 20문항)

- **특정 개체 중심 질의**임. 회원 · 식당 · 메뉴 · 알레르겐 · 지역 중 **고유명이 1개 이상** 들어감
- 문항은 **그래프 경로에서 역으로 만듦** — 경로를 먼저 고르고 → 그 경로를 따라가야만 답이 되는 질문을 씀
  → 경로 위 문서 `doc_id`를 `reference_doc_ids`에, 경로 문자열을 `reference_path`에 적음
- `expected_mode: "local"`을 적어 **모드 판정(`S-KQ1`)이 맞는지도 함께 잼**
- `no_path` 기대 2문항은 `quality_report.json`의 `broken_kg_paths`에서 뽑음.
  기대 결과는 **답이 아니라 `no_path` 착지**임 — 지어내는지 보는 자리임
- 대표 질문 예

  | 홉 | 질문 예 |
  |----|--------|
  | 1홉 | `R-SEGNAM-042는 어느 지역에 있나요` |
  | 2홉 | `치킨커리는 어떤 카테고리에 들어가나요` |
  | 3홉 | `땅콩이 들어간 메뉴를 내는 식당은 어디인가요` |
  | 4홉 | `M-0003이 먹으면 안 되는 강남 식당은 어디인가요` |

#### 4-2. Global 문항군 (`Q-KG-G`, 20문항)

- **주제 요약형 질의**임. 고유명 없이 특징 · 경향 · 전반을 물음
- 문항은 **커뮤니티 요약에서 역으로 만듦** — `:Community` 노드의 `summary`를 고르고 →
  그 요약으로 답할 수 있는 질문을 씀 → `community_id`를 `reference_community_ids`에 적음
- `expected_mode: "global"`을 적음
- 대표 질문 예 — `강남 식당들의 원재료 구성 경향은` · `밀이 들어가는 메뉴가 많은 카테고리군은` ·
  `비건이 고를 수 있는 메뉴가 가장 적은 지역은`
- Global 문항은 **정답이 한 문장으로 딱 떨어지지 않음**. `reference`는 요약 답변의 **필수 포함 요소
  목록**으로 적음(예: `한식-국물이 다수 · ING-PORK가 최빈 · 밀 함유 메뉴는 소수`)

#### 4-3. 방어 문항 4건 (`Q-KG-X`, 지표 계산 제외)

- `quality_report.json`의 `poison_docs` 3건을 노리는 질의 3건 + 오염 문구를 정상 질문처럼 위장한 1건
- **기대 결과는 "오염 개체가 그래프에 없어 결과에 0건"** 이며 `metric_eligible: false`로 표시함
- RAGAS 평균에 넣지 않고 **통과 / 실패 2치**로 따로 집계함

#### 4-4. 문항 파일 규격 (`src/v1/eval/testset/kg_testset_v1.jsonl`)

JSON Lines 1행 = 1문항. 아래 키를 **전부** 채움. 키 이름을 바꾸지 않음.

```json
{
  "qid": "Q-KG-L-14",
  "question_group": "local",
  "expected_mode": "local",
  "hops": 4,
  "user_input": "M-0003이 먹으면 안 되는 강남 식당은 어디인가요",
  "reference": "R-SEGNAM-042 (치킨커리에 ING-PEANUT 함유)",
  "reference_contexts": ["M-0003 회원은 ... 땅콩 알레르기가 있어 ...", "..."],
  "reference_doc_ids": ["KG-MBR-0003", "KG-ING-PEANUT", "KG-RST-SEGNAM-042"],
  "reference_path": "Member(M-0003)-[AVOIDS]->Allergen(땅콩)-[MAPS_TO]->Ingredient(ING-PEANUT)
                     <-[CONTAINS]-Menu(치킨커리)<-[SERVES]-Restaurant(R-SEGNAM-042)",
  "reference_community_ids": [],
  "relevance_grades": {"KG-RST-SEGNAM-042": 3, "KG-ING-PEANUT": 2, "KG-MBR-0003": 2, "KG-RST-SEGNAM-011": 0},
  "metric_eligible": true,
  "expected_no_path": false,
  "expected_empty": false,
  "labeler_a": "정답 일치", "labeler_b": "정답 일치", "agreed": true,
  "testset_version": "v1.0.0",
  "created_at": "2026-08-07T00:00:00+09:00"
}
```

- `user_input` · `reference` · `reference_contexts` 3요소가 3.7 `[고정]`이 요구하는
  **질문 · 정답(ground truth) · 기대 문맥(reference contexts)** 임
- **`relevance_grades`는 Local 문항에만 필수**임 — NDCG 계산에 관련도 등급이 있어야 함.
  등급은 `3`(정답 자체) · `2`(경로 위 필수 근거) · `1`(같은 개체군의 참고) · `0`(무관) 4단계임.
  문항당 등급 0 항목을 **3건 이상** 넣음(전부 관련 있는 목록이면 순위 품질을 못 잼)
- Global 문항은 `relevance_grades`를 빈 객체로 두고 `reference_community_ids`를 채움
- Pydantic 모델을 `src/v1/eval/testset/schema.py`에 **추가**함(④가 만든 파일. 기존 모델을 고치지 않음)
- 문항 생성은 **Structured Output**(3.1 `[고정]` 준용)으로 받음

#### 4-5. 2인 라벨링과 폐기 규칙

- ④ `testset-rag.md`와 **같은 규칙**을 씀 — 서로 다른 시드 · 프롬프트로 2회 라벨링,
  갈리면 `agreed: false`로 `src/v1/eval/testset/discarded_kg_v1.jsonl`로 옮김
- **사람 검토와 동등하지 않음을 README에 명시**하고, 사람 검토를 붙일지는 **사용자 문의**로 남김
- 폐기 후 남은 문항이 **문항군마다 20문항 미만이면 부족분을 다시 생성**함(3단계 하한 유지)

### 5단계 — 평가 실행기 구현 (`src/v1/eval/run_kg_eval.py`)

1. `kg_testset_v1.jsonl`을 읽어 `question_group`으로 Local · Global · 방어 3갈래로 나눔
2. 각 문항의 `user_input`으로 **③ 리트리버(`src/v1/kg/retriever`)를 호출**함
3. **모드 판정 정확도**를 먼저 집계함 — `selected_mode`가 `expected_mode`와 같은 비율
4. Local — `paths`의 `evidence_doc_ids`를 `retrieved_contexts`로 놓고 아래를 계산함
5. Global — `community_summaries`를 `retrieved_contexts`로 놓고 요약 답변을 생성해 아래를 계산함
6. 방어 문항은 오염 개체가 결과에 0건인지 통과 / 실패로 집계함
7. `no_path` 기대 문항은 실제로 `no_path`로 착지했는지 통과 / 실패로 집계함
8. 결과를 파일로 남기고 **④ 벡터 RAG 결과와 나란히 비교표**를 만듦

#### 5-1. 모드별 지표 — ④와 **같은 문자열**을 씀

`src/v1/eval/metrics_config.py`에 **키를 추가만** 함(④가 만든 4개 키를 고치지 않음).

| 모드 | 지표 키(고정 문자열) | 한 줄 뜻 | 근거 |
|------|---------------------|---------|------|
| **Local** | `context_recall` | 정답에 필요한 근거를 빠짐없이 검색했는가 | 3.5 완료조건 |
| **Local** | `context_precision` | 검색된 근거 **위쪽**에 관련 항목이 있는가 | 3.5 완료조건 |
| **Local** | `ndcg_at_5` | **순위 품질** — 관련도 높은 항목이 위에 올수록 높음(0 ~ 1) | 3.7 `[기준]` 지표 보완 |
| **Global** | `faithfulness` | 요약 답변이 커뮤니티 요약에 근거하는가(환각 탐지) | 3.5 완료조건 |
| **Global** | `answer_relevancy` | 답변이 질문 의도에 부합하는가 | 3.5 완료조건 |

- **NDCG는 RAGAS가 제공하지 않으므로 별도로 계산**함(3.7 `[기준]`). `k = 5`로 고정하고
  `relevance_grades`를 등급으로 씀. 구현은 `src/v1/eval/ndcg.py`에 두고 단위 시험으로 값을 고정함
- **Local에 `faithfulness` · `answer_relevancy`를 붙이지 않고, Global에 `context_recall` ·
  `ndcg_at_5`를 붙이지 않음.** Local은 경로를 찾는 일이고 Global은 요약을 쓰는 일이라 재는 대상이 다름
- RAGAS 클래스명과 데이터셋 필드명은 **context7 MCP로 확인한 뒤** 코드에 씀

#### 5-2. 목표치 — **전부 `가정값`** 임

| 모드 | 지표 | 목표치 | 표기 | 근거 |
|------|------|--------|------|------|
| Local | `context_recall` | **≥ 0.85** | 가정값 | ④ 벡터 RAG 0.90보다 낮춰 잡음 — 다홉 경로는 한 홉만 끊겨도 통째로 빠짐 |
| Local | `context_precision` | **≥ 0.75** | 가정값 | 실측 이력 없음. 첫 회 실측 후 재조정 대상 |
| Local | `ndcg_at_5` | **≥ 0.80** | 가정값 | 실측 이력 없음. 첫 회 실측 후 재조정 대상 |
| Global | `faithfulness` | **≥ 0.85** | 가정값 | 요약 생성은 결정론이 아니므로 Local보다 여유를 둠 |
| Global | `answer_relevancy` | **≥ 0.80** | 가정값 | 요약형 질의는 답의 범위가 넓어 낮춰 잡음 |
| 공통 | 모드 판정 정확도 | **≥ 0.90** | 가정값 | 판정이 틀리면 지표 자체가 엉뚱한 것을 잼 |
| 공통 | 방어 문항 통과율 | **100%** | **가정값 아님** | v0 `M-Q4 하드필터 위반 노출 0건` 실측 통과와 같은 성격 |
| 공통 | `no_path` 착지율 | **100%** | **가정값 아님** | 경로가 없으면 지어내지 않는 것이 조건임 |

- 실데이터로 검증하지 않은 수치는 결과 보고서에 **`가정값`이라고 그대로 표기**함
- **목표에 못 미치면 목표치를 낮춰 통과시키지 않음.** 실측을 그대로 적고 원인 후보를 나열함
  (v0가 M-Q1 목표 3,000ms에 실측 6,343ms를 그대로 남긴 사례 — `src/README.md` 3절 · 4-1절)

#### 5-3. 결과 산출물

- `src/v1/eval/results/kg_eval_{YYYYMMDD-HHMM}.json` — 모드별 지표 평균 · 문항별 점수 ·
  홉 수별 점수 · 모드 판정 정확도 · 리트리버 설정 스냅샷(DB 이름 · 최대 홉 수 · 커뮤니티 수) ·
  테스트셋 버전
- `src/v1/eval/results/kg_eval_{YYYYMMDD-HHMM}.md` — 사람이 읽는 점수표.
  지표 · 목표치 · 실측값 · 판정 · `가정값` 표기 · 미달 지표의 최저 점수 문항 3건
- `src/v1/eval/results/compare_rag_vs_kg_{YYYYMMDD-HHMM}.md` — **④ 벡터 RAG와의 비교표**.
  공통 지표(`context_recall` · `context_precision`)를 나란히 놓고,
  ③ README의 **구축 비용 실측**(LLM 호출 수 · 총 소요 시간)을 함께 적어
  "그 비용을 치를 값을 하는가"를 판단할 재료를 남김. **판단 자체는 하지 않고 숫자만 제시**함

### 6단계 — 기술적 요구사항

- **API Key** — `.env`에서만 읽음. 필요 키: `GROQ_API_KEY`(문항 생성 · 요약 답변 생성 · RAGAS 평가 LLM) ·
  `OPENAI_API_KEY`(리트리버가 쓰는 임베딩) · `COHERE_API_KEY`(리트리버 리랭킹) ·
  `NEO4J_URI` · `NEO4J_USER` · `NEO4J_PASSWORD`
- **Config와 소스 분리** — 문항 수 · 목표치 · NDCG의 `k` · 테스트셋 버전 · 결과 경로는 전부
  `src/v1/app/common/config.py`가 `src/v1/app/common/settings.yaml`에서 읽음. 매직 넘버를 두지 않음
- **LLM 사양**(3.2 `[고정]`) — Groq LPU · 모델 `openai/gpt-oss-120b` · `temperature=0` ·
  `timeout=30초` · 429 응답 시 지수 백오프 재시도 2회
  - RAGAS 평가용 LLM은 **④와 같은 모델**을 씀. 다르면 두 경로의 점수를 나란히 못 놓음
  - `temperature=0`은 재현성 때문임 — 점수가 흔들리면 회귀 평가가 무의미해짐
- **시스템 프롬프트와 유저 프롬프트 분리**(3.1 `[고정]` 준용)
- **LCEL 실행 방식**(3.1 `[기준]` 준용) — 조건 → 선택

  | 조건 | 선택 |
  |------|------|
  | 문항 44건 배치 생성 | **`ainvoke`**(비동기) |
  | 평가 실행기가 문항 44건을 연속 호출 | **`ainvoke`**(비동기) |
  | 문항 1건 확인용 CLI(`--dry-run`) | **`invoke`**(동기) |

- **버전 관리**(3.7 `[고정]`) — 파일명에 버전을 박고(`kg_testset_v1.jsonl`) 각 행에도
  `testset_version`을 넣음. 문항이 1건이라도 바뀌면 **마이너 버전을 올리고 변경 이력을
  `src/v1/eval/testset/CHANGELOG.md`에 추가**함(④가 만든 파일. 기존 항목을 고치지 않음).
  옛 버전 파일을 지우지 않음

### 7단계 — 테스트 및 버그 수정

- 프레임워크 **pytest**, 모듈별 단위 테스트를 `src/v1/tests/eval/`에 작성함(④와 같은 디렉토리)
- **LLM · 리트리버 호출은 Mock/fixture로 대체**함. **Neo4j 접속 시험은
  `@pytest.mark.integration`으로 분리**함
- 최소 시험 항목
  1. `kg_testset_v1.jsonl` 전 행이 `schema.py` Pydantic 모델 검증을 통과함
  2. Local · Global 문항이 **각각 20건 이상**임(3단계 하한 규정)
  3. Local 문항의 홉 수 배분이 1 ~ 4홉을 전부 포함하고 `no_path` 기대 문항이 2건 있음
  4. 모든 `reference_doc_ids`가 `src/v1/data/kg/` 에 실재하는 `doc_id`임(끊긴 참조 0건)
  5. 모든 `reference_community_ids`가 그래프에 실재하는 `community_id`임
  6. 모든 Local 문항에 `relevance_grades`가 있고 등급 `0` 항목이 3건 이상임
  7. `ndcg.py`가 손계산한 기대값과 일치함(고정 입력 3케이스로 값을 못 박음)
  8. 지표 키가 `metrics_config.py` 문자열과 정확히 일치하고 **④가 만든 4개 키가 그대로 남아 있음**
  9. Local 문항에 `faithfulness`가, Global 문항에 `ndcg_at_5`가 계산되지 않음(모드별 분리 확인)
  10. 같은 테스트셋 · 같은 그래프로 2회 평가 시 지표 평균 차이가 0.02 이하임(재현성)
  11. 목표 미달 시 실행기가 **점수를 조정하지 않고** 판정을 `미달`로 적음

### 8단계 — README.md 작성 (`src/v1/eval/README.md`에 **절을 추가**함)

- ④가 만든 파일이므로 **기존 절을 고치지 않고 GraphRAG 절을 덧붙임**
- 추가할 내용
  - 개요 — 목적 및 주요 기능
  - 가상환경 설정 및 실행 — **Windows GitBash · Windows PowerShell · Linux/Mac 3환경** 명령어 각각 기재
  - **평가 흐름 가시화 — Mermaid 스크립트**로
    `테스트셋 → 모드 분기(Local / Global) → 리트리버 호출 → 지표 계산 → 점수표 → RAG 비교표` 흐름을 그림
  - **문항 수 산정 근거** — 문항군별 `1 ÷ (1 − 목표비율)` 계산 과정과 하한 20 적용 결과
  - **모드별 지표를 나눈 이유** — Local은 순위, Global은 환각을 재는 것이라는 설명
  - **목표치표와 `가정값` 표기** — 어느 수치가 실측 근거를 갖고 어느 수치가 가정인지 구분
  - **2인 라벨링 대체 방식의 한계**
  - **GraphRAG 비용 대비 효과** — ③ README의 구축 비용 실측과 이 단계의 품질 실측을 나란히 놓음.
    존치 여부 **판단은 적지 않고 숫자만** 제시함

### 톤앤매너

- 코드 주석과 README는 **한국어 명사체**로 씀. 목표치에는 근거 파일을 주석으로 인용함
- 전문 용어는 처음 나올 때 괄호로 쉬운 설명 1회 — 예:
  `NDCG(관련도 높은 것이 위에 올수록 높아지는 순위 점수. 0 ~ 1)` ·
  `Local 검색(특정 개체에서 출발해 선을 따라가는 검색)` ·
  `Global 검색(덩어리 요약을 훑어 전체 경향을 답하는 검색)`

---

## [출력]

| 산출물 | 경로 |
|--------|------|
| 테스트셋 생성기 | `src/v1/eval/testset/build_kg_testset.py` |
| 문항 모델 | `src/v1/eval/testset/schema.py` (④가 만든 파일에 **모델 추가만** 함) |
| 테스트셋 | `src/v1/eval/testset/kg_testset_v1.jsonl` (44문항) |
| 폐기 문항 | `src/v1/eval/testset/discarded_kg_v1.jsonl` |
| 변경 이력 | `src/v1/eval/testset/CHANGELOG.md` (④가 만든 파일에 **항목 추가만** 함) |
| 지표 정의(공용) | `src/v1/eval/metrics_config.py` (④가 만든 파일에 **키 추가만** 함) |
| NDCG 계산기 | `src/v1/eval/ndcg.py` |
| 평가 실행기 | `src/v1/eval/run_kg_eval.py` |
| 평가 결과 | `src/v1/eval/results/kg_eval_{YYYYMMDD-HHMM}.json` · `.md` |
| RAG 비교표 | `src/v1/eval/results/compare_rag_vs_kg_{YYYYMMDD-HHMM}.md` |
| 설정 | `src/v1/app/common/settings.yaml` (기존 파일에 **키 추가만** 함) |
| 의존성 | `src/v1/requirements.txt` (기존 줄 삭제 · 변경 없이 **추가만** 함) |
| 시험 | `src/v1/tests/eval/` |
| 문서 | `src/v1/eval/README.md` (**절 추가만** 함) |

---

## [제약조건]

### MUST

- 프롬프트 작성 가이드(`references/prompt-guide.md`) 준용
- **반드시 "context7 MCP" 사용** — RAGAS 지표 클래스명 · `EvaluationDataset` 필드명 · Neo4j · Cypher
  문법을 기억에 의존해 쓰지 않음
- 반드시 의존성을 `src/v1/requirements.txt`에 정의함(Python 한정)
- README.md의 가상환경 활성화는 **Windows GitBash · Windows PowerShell · Linux/Mac**별 명령어를 안내함
- **실데이터로 검증하지 않은 수치는 `가정값`으로 표기**함(정직한 보고 규칙)
- 추가정보나 의사결정이 필요하면 **사용자에게 반드시 문의**함. 이미 확인된 문의 대상은 아래임
  - 코드 base directory (기본값 `src/v1/`)
  - 6개 목표치(가정값)를 확정값으로 승격할지, 첫 회 실측 후 다시 정할지
  - Local 문항의 홉 수 배분(1홉 4 · 2홉 5 · 3홉 5 · 4홉 4 · `no_path` 2)을 바꿀지
  - NDCG의 `k` 값(기본 5, 리트리버 top-k와 맞춤)과 관련도 등급 4단계 기준
  - 2인 라벨링에 **사람 검토**를 붙일지(현재는 시드 2회 생성으로 대체함)
  - Hybrid 모드 전용 문항군을 따로 둘지(현재는 모드 판정 정확도로만 잼)

### MUST NOT

- **추측하여 생성하지 않음.** 데이터에 기반하여 수행함
  - `src/v1/data/kg/`에 없는 내용을 정답으로 적지 않음
  - 실재하지 않는 `doc_id` · `community_id`를 참조로 적지 않음
  - `schema.yaml` 밖의 개체 · 관계를 묻는 문항을 만들지 않음
- ④가 만든 지표 키 4종과 `src/v1/eval/testset/schema.py` · `CHANGELOG.md` ·
  `src/v1/eval/README.md`의 **기존 내용을 고치거나 지우지 않음**(추가만 함)
- 데이터베이스 이름 `lunchpick_kg_v1` · 벡터 인덱스 이름 `lunchpick_kg_entity_v1` ·
  확정된 개체 · 관계 타입 이름을 **임의로 바꾸지 않음**
- **Local에 생성 지표(`faithfulness` · `answer_relevancy`)를, Global에 순위 지표(`ndcg_at_5`)를
  붙이지 않음** — 모드별로 재는 대상이 다름
- **목표 미달 시 목표치를 낮추거나 문항을 빼서 통과시키지 않음**
- 문항 수를 3단계 규정(문항군마다 `1 ÷ (1 − 목표비율)`, 하한 20) 미만으로 줄이지 않음
- 방어 문항과 `no_path` 기대 문항을 RAGAS 지표 평균에 포함하지 않음
- 비교표에서 **GraphRAG 존치 여부를 판단해 적지 않음**. 숫자만 제시하고 판단은 아키텍트에게 넘김
- `src/` 아래 v0 파일을 **수정하지 않음**(읽기 전용). 산출물은 전부 `src/v1/` 아래에만 만듦
- 옛 버전 테스트셋 파일을 삭제하지 않음

### 완료조건 — 검증 가능한 증거 기준

1. **산출 파일 목록 제시** — 위 `[출력]` 표 경로의 실제 `ls` 결과 첨부
2. **pytest 실행 로그 첨부** — `python -m pytest src/v1/tests/eval -v` 결과가 **실패 0건**임
   (④가 만든 시험도 함께 통과해야 함)
3. **테스트셋 실측 집계 첨부** — 총 문항 수 · 모드별 문항 수 · 홉 수별 분포 · 방어 문항 수 ·
   `no_path` 기대 문항 수 · 폐기 문항 수와 사유
4. **샘플 문항 최소 3건의 전문 첨부** — Local 4홉 1건 · Global 1건 · `no_path` 기대 1건
5. **모드별 실측 점수표 첨부** — Local 3지표 · Global 2지표의 실측값 · 목표치 · `가정값` 표기 · 판정.
   모드 판정 정확도 · 방어 문항 통과율 · `no_path` 착지율도 함께 적음
6. **NDCG 실측값 첨부** — `ndcg_at_5` 평균과 홉 수별 값
7. **샘플 질의 최소 3건의 실행 로그(요청 → 응답) 첨부** — Local · Global · `no_path` 각 1건.
   Local 로그에는 반환된 경로와 근거 문서 ID가 보여야 함
8. **④ 벡터 RAG와의 비교표 첨부** — 공통 지표 나란히 + ③ 구축 비용 실측
9. 목표에 못 미치는 값이 나오면 **값을 고쳐 통과시키지 않고 실측을 그대로 보고**하고
   원인 후보(개체 추출 누락 · 정규화 실패 · 홉 상한 · 커뮤니티 입도 · 원천 결측)를 나열함

---

## [예시]

**Global 문항 1행의 기대 형태**

```json
{
  "qid": "Q-KG-G-07",
  "question_group": "global",
  "expected_mode": "global",
  "hops": 0,
  "user_input": "강남 식당들은 대체로 어떤 재료를 많이 쓰나요",
  "reference": "필수 포함 요소 — 한식-국물 카테고리 다수 · ING-PORK 최빈 · ING-SOY 다수 · 밀 함유 메뉴는 소수",
  "reference_contexts": ["커뮤니티 C-03 요약: 강남 지역 식당 다수가 한식-국물 카테고리이며 ..."],
  "reference_doc_ids": [],
  "reference_path": null,
  "reference_community_ids": ["C-03", "C-07"],
  "relevance_grades": {},
  "metric_eligible": true,
  "expected_no_path": false, "expected_empty": false,
  "labeler_a": "정답 일치", "labeler_b": "정답 일치", "agreed": true,
  "testset_version": "v1.0.0",
  "created_at": "2026-08-07T00:00:00+09:00"
}
```

**모드별 점수표의 기대 형태** (`kg_eval_20260807-1120.md` 일부)

| 모드 | 지표 | 목표치 | 표기 | 실측 | 판정 |
|------|------|--------|------|------|------|
| Local | `context_recall` | 0.85 | 가정값 | 0.88 | 통과 |
| Local | `context_precision` | 0.75 | 가정값 | 0.79 | 통과 |
| Local | `ndcg_at_5` | 0.80 | 가정값 | 0.71 | **미달** |
| Global | `faithfulness` | 0.85 | 가정값 | 0.90 | 통과 |
| Global | `answer_relevancy` | 0.80 | 가정값 | 0.83 | 통과 |
| 공통 | 모드 판정 정확도 | 0.90 | 가정값 | 0.93 | 통과 |
| 공통 | 방어 문항 통과율 | 100% | — | 100% (4/4) | 통과 |
| 공통 | `no_path` 착지율 | 100% | — | 100% (2/2) | 통과 |

> `ndcg_at_5` 미달을 목표치 0.70으로 낮춰 통과시키지 않음. 최저 점수 문항 3건(전부 4홉)과
> 원인 후보(홉이 길수록 리랭킹이 짧은 경로를 위로 올림)를 함께 적음.

**하지 말아야 할 형태 (anti-example)**

```json
{ "qid": "Q-KG-L-14", "user_input": "M-0003이 먹으면 안 되는 식당은",
  "reference": "R-SEGNAM-042", "reference_doc_ids": [], "relevance_grades": {} }
```

> 근거 문서와 관련도 등급이 비어 있음 = **Context Recall도 NDCG도 못 잼**.
> Local 문항은 `reference_doc_ids` · `reference_path` · `relevance_grades` 3가지가 전부 있어야 함.
