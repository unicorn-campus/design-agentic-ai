# dp: GraphRAG 구축 개발 프롬프트 — 인덱서 + 리트리버 (런치픽 v1)

> 이 파일 전체를 AI 코딩 도구에 붙여 넣어 코드를 생성함. 이 문서 자체는 코드가 아님.  
> 채택 모듈: `references/dev-prompt-guide.md` 3.1(LangChain 공통) · 3.2(LLM) · 3.5(GraphRAG) ·
> 3.6(검색 처리 기법) · 3.7(검색 품질 평가) · 3.9(개발 디렉토리)  

> 실행 순서 — ① `gen-data` → ② `index-rag` → ③ `index-graphrag` → ④ `testset-rag` →  
> ⑤ `testset-graphrag` → ⑥ `backend` → ⑦ `frontend`.  
> ⑥ 백엔드는 ③까지 끝나면 ④⑤를 기다리지 않고 시작 가능함(평가는 백엔드를 막지 않음). ⑦ 프론트는 ⑥의 API 경계가 확정된 뒤 시작함

---

## [목표]

런치픽 v1의 **GraphRAG 인덱서와 리트리버**를 LangChain + Neo4j로 개발하여, 합성 GraphRAG 소스 문서에서
개체 · 관계를 추출해 지식그래프를 만들고 Local · Global · Hybrid 3모드로 검색하는 파이썬 패키지를 만듦.

---

## [역할]

당신은 데이터 엔지니어 8년 + 대규모 지식그래프 구축 5년 경력의 **지식 · 데이터 엔지니어**임.  
LangChain + Neo4j(Cypher · 벡터 인덱스 · GDS 커뮤니티 탐지), LLM 기반 개체 · 관계 추출,
비동기 병렬 배치, RAGAS · NDCG 평가에 능숙함.  
GraphRAG는 구축 비용이 크다는 것을 알고 있어 **비용과 지연을 먼저 재고 트레이드오프를 문서에 남김**.

---

## [맥락]

- 내 상황: 런치픽 v0(`src/`)는 그래프 검색을 **의도적으로 뺐음**. 이유가 두 가지였음 —
  이을 원료 데이터가 없었고, 메뉴 텍스트 수십만 건 추출 비용이 14주 MVP 계획 밖이었음
  (근거: `textbook/script/05-jisikni.md` S14 강의 노트). v1은 ① `gen-data.md`가 **원료 데이터를
  합성으로 만들어 준** 상태이므로 첫 번째 이유가 해소됨. 두 번째 이유(비용)는 여전히 살아 있으므로
  **구축 비용을 실측해 기록하는 것이 이 작업의 절반**임
- 인덱싱 대상은 **합성 GraphRAG 소스뿐**임(`src/v1/data/kg/`). 외부 API · 크롤링 데이터를 쓰지 않음
- 이 단계의 산출물(Neo4j 데이터베이스 이름 · 개체 · 관계 타입 · 커뮤니티 요약)이 그대로
  ⑤ `testset-graphrag.md`의 평가 대상이 됨. **문자열을 임의로 바꾸지 않음**
- 결과물 독자: 검색 파이프라인을 구현할 개발자, 평가 테스트셋을 만들 담당자, 구조를 검토할 아키텍트

---

## [입력]

우선순위 순으로 읽음. 앞 자료가 뒤 자료와 충돌하면 앞 자료를 따름.

1. **팀 규칙**: `AGENTS.md` — 마크다운 작성 가이드 · 정직한 보고 규칙
2. **프롬프트 표준**: `references/prompt-guide.md` — 8섹션 표준
3. **선행 산출물(필수)**: `src/v1/data/kg/` — ① `gen-data.md`가 만든 GraphRAG 소스 문서 3종
   (`restaurant/` · `member/` · `ingredient/`). **없으면 이 작업을 시작하지 않고 사용자에게 문의함**
4. **선행 산출물(필수)**: `src/v1/data/quality_report.json` — 오염 문서 목록과 `broken_kg_paths`
   (끊어 둔 홉 목록). 차단 기대값과 경로 실패 기대값의 정답지임
5. **선행 산출물(필수)**: `src/v1/app/common/doc_schema.py` · `src/v1/app/common/config.py`
6. **선행 산출물(참조)**: `src/v1/rag/store/manifest.json` — ② 단계의 임베딩 모델 · 청킹 값.
   **같은 임베딩 모델을 써야** 두 경로를 같은 잣대로 비교할 수 있음
7. **용어사전(코드표)**: `src/common/lp_common/codes.py` — 카테고리 · 알레르겐 · 식이유형 코드.
   **개체 타입 후보의 근거**이며, 여기 없는 코드를 새로 만들지 않음
8. **v0 가드레일 참조**: `src/common/lp_common/guardrails.py` · `src/README.md` 3절
9. **교재 원고**: `textbook/script/05-jisikni.md` — 아젠다(S13 · S14)만 보고 개발에 필요한 정보만 추출
10. **라이브러리 문법 확인**: **context7 MCP** — LangChain · LangGraph · Neo4j(Cypher · GDS) 문법은
    반드시 여기서 확인

---

## [처리]

### 1단계 — 코드 base directory 확인 (가장 먼저 수행)

- 기본값 `src/v1/` 을 사용자에게 제시하고 다른 값을 받으면 **모든 산출 경로의 접두를 그 값으로 바꿈**
- 기본값을 그대로 쓰기로 하면 되묻지 않고 2단계로 진행함

### 2단계 — 체크포인트 저장소 선택 (사용자 문의, 3.1 `[고정]`)

- **`MemorySaver`(메모리) 와 `SqliteSaver`(로컬 파일) 중 어느 것을 쓸지 사용자에게 선택받음**
- 파일을 고르면 경로는 `src/v1/kg/store/checkpoint.sqlite`. 선택 근거를 README에 기록함
- GraphRAG 인덱싱은 문서 500건 규모 LLM 추출이라 **중간 실패 시 재개가 실제로 필요함**을 함께 안내함

### 3단계 — 개체 · 관계 타입 확정 (3.5 `[기준]`) — **사용자 검토 필수**

가이드 3.5는 "샘플 청크에서 후보를 추출한 뒤 **사용자 검토로 확정**하고 설정 파일로 관리"라고 규정함.

1. `src/v1/data/kg/` 에서 **문서 종류별 10건씩 총 30건**을 무작위 표본으로 뽑음
2. LLM으로 개체 · 관계 후보를 추출해 빈도순 목록을 만듦
3. 아래 **초기 후보**를 함께 제시함(근거: `src/common/lp_common/codes.py` · `src/db/init/01-schema.sql`)

   | 개체 타입 | 키 | 근거 |
   |----------|-----|------|
   | `Member` | `member_ref` | `member` 표 |
   | `Restaurant` | `restaurant_id` | `restaurant_cache` 표 |
   | `Menu` | `menu_name` | `MENU_BY_CATEGORY` |
   | `Category` | `category_code` | `codes.CATEGORY_CODES` |
   | `Ingredient` | `ingredient_code` | `restaurant_cache.allergen_codes` |
   | `Allergen` | `allergen_name` | `codes.ALLERGEN_NAME_TO_CODES` 좌변 |
   | `DietType` | `diet_type` | `codes.DIET_TYPE_TO_CODES` 좌변 |
   | `Region` | `region_code` | `member.region_code` |

   | 관계 타입 | 방향 | 근거 |
   |----------|------|------|
   | `SERVES` | `Restaurant → Menu` | 대표메뉴 |
   | `IN_CATEGORY` | `Menu → Category` | 카테고리 코드 |
   | `CONTAINS` | `Menu → Ingredient` | 원재료 |
   | `MAPS_TO` | `Allergen → Ingredient` | `ALLERGEN_NAME_TO_CODES` |
   | `BLOCKS` | `DietType → Ingredient` | `DIET_TYPE_TO_CODES` |
   | `LOCATED_IN` | `Restaurant → Region` | 지역 |
   | `AVOIDS` | `Member → Allergen` | `dietary_restriction` |
   | `PREFERS` | `Member → Category` | `preference_profile` |
   | `ATE` | `Member → Menu` | `meal_record` |

4. **사용자 검토로 확정**한 뒤 `src/v1/kg/indexer/schema.yaml`에 기록함.
   확정 전에는 전체 인덱싱을 시작하지 않음
5. 확정된 타입 **밖의 개체 · 관계는 추출하지 않고 버림**. 버린 건수를 로그에 남김
   (타입을 열어 두면 같은 뜻의 관계가 여러 이름으로 생겨 다홉 질의가 조용히 실패함)

### 4단계 — 인덱서 구현 (`src/v1/kg/indexer/`)

LangGraph `StateGraph` 단일 워크플로우로 구현함(3.1 `[고정]`). 노드 간 공유는 State(Reducer)로만 함.

| 단계 ID | 노드 | 하는 일 |
|---------|------|--------|
| `S-KI1` | `load_documents` | `src/v1/data/kg/**/*.md` 수집, front matter 파싱 |
| `S-KI2` | `guard_precheck` | **적재 전 검사** — 오염 문자열 차단 |
| `S-KI3` | `extract_graph` | 개체 · 관계 추출 (**비동기 병렬**) |
| `S-KI4` | `normalize` | 개체 표기 정규화 · 중복 병합 |
| `S-KI5` | `write_neo4j` | 노드 · 관계 적재 |
| `S-KI6` | `embed_nodes` | 개체 요약문 임베딩 → Neo4j 벡터 인덱스 |
| `S-KI7` | `detect_community` | 커뮤니티 탐지 |
| `S-KI8` | `summarize_community` | 커뮤니티 요약 생성 (**비동기 병렬**) |
| `S-KI9` | `write_manifest` | 색인 매니페스트 기록 |

#### 4-1. 적재 전 검사 (`S-KI2`)

- ② `index-rag.md`와 **같은 규칙 한 벌**을 씀. 기본 제안은 v0 `lp_common.guardrails`를
  수정 없이 임포트하는 것이며, 임포트할지 복사할지는 **사용자 문의** 대상임
- 차단 라벨 문자열은 v0 실측과 같은 값 — `G-1:instruction_injection` · `G-2:control_char` ·
  `G-2:newline` · `G-1:length_over`
- 차단 목록은 `src/v1/kg/store/blocked.jsonl`에 남김
- **차단 건수가 `quality_report.json`의 `poison_docs` 건수와 다르면 실패로 처리하고 중단함**

#### 4-2. 개체 · 관계 추출 (`S-KI3`) — 3.5 `[고정]` 비동기 병렬

- **비동기 병렬로 수행**함(고정). 동시 실행 수는 `settings.yaml`의 `kg_extract_concurrency`로 두고
  기본값 8, 429 응답이 나면 지수 백오프 재시도 2회 후 동시 실행 수를 절반으로 낮춤
- **Structured Output**(3.1 `[고정]`) — Pydantic 모델 `ExtractedGraph(nodes: list[Node],
  relations: list[Relation])`로 받음. 문자열을 정규식으로 뜯지 않음
- **시스템 프롬프트와 유저 프롬프트를 분리**함 — 시스템에 `schema.yaml`의 허용 타입 목록,
  유저에 문서 본문을 둠
- 추출 결과마다 **근거 문장(`evidence_text`)과 출처(`doc_id`)를 반드시 함께 저장**함.
  근거 없이 만들어진 관계는 버림(⑤ 단계 평가에서 근거 정확도를 못 잼)

#### 4-3. 정규화 (`S-KI4`)

- 같은 개체의 표기 변이를 합침 — 예 `돼지고기` / `ING-PORK`, `땅콩` / `땅콩 알레르기`
- 정규화 기준은 **`codes.py` 코드값**임. 코드로 매핑되지 않는 개체는 원문 표기를 그대로 두고
  `normalized: false`로 표시함. **지어내서 코드를 붙이지 않음**
- 병합 · 미매핑 건수를 로그와 매니페스트에 남김

#### 4-4. Neo4j 적재 (`S-KI5`) — 3.5 `[고정]` 프레임워크

- **개발 프레임워크: LangChain + Neo4j** (고정)
- **데이터베이스 이름 `lunchpick_kg_v1`** — ⑤ `testset-graphrag.md`가 이 문자열을 그대로 지목함.
  **바꾸지 않음**
- 접속 정보는 `.env`의 `NEO4J_URI` · `NEO4J_USER` · `NEO4J_PASSWORD`에서만 읽음
- 노드 공통 속성 — `id` · `name` · `source_doc_ids`(배열) · `evidence_text` · `normalized` · `indexed_at`
- 관계 공통 속성 — `source_doc_id` · `evidence_text` · `confidence`
- 재실행 시 **데이터베이스를 비우고 다시 만듦**(증분 갱신 금지). 부분 갱신은 옛 관계가 남아 평가값이 흔들림
- Neo4j 기동 방법(로컬 Docker / 원격)은 **사용자 문의** 대상임. 기본 제안은
  `src/v1/kg/store/docker-compose.yml`로 로컬 컨테이너를 띄우는 것임

#### 4-5. 개체 임베딩 · 벡터 인덱스 (`S-KI6`)

- Local 검색의 진입점(질의 → 시작 개체)을 만들기 위해 개체 요약문을 임베딩함
- **임베딩 모델은 `OpenAI text-embedding-3-large`** 를 씀. 가이드 3.5에는 임베딩 고정값이 없으나,
  3.4 `[고정]` 값을 준용함 — **같은 서비스에서 두 벡터 공간을 쓰면 RAG와 GraphRAG를 같은 잣대로
  비교할 수 없기 때문**임. 다른 모델을 쓰려면 **사용자 문의**
- 벡터 인덱스 이름 `lunchpick_kg_entity_v1`

#### 4-6. 커뮤니티 탐지 · 요약 (`S-KI7` · `S-KI8`) — 3.5 `[고정]`

- **Global 검색을 지원하므로 커뮤니티 탐지 · 요약 인덱싱 단계를 포함함**(고정)
- 탐지 알고리즘 선택 규칙 — 조건 → 선택

  | 조건 | 선택 |
  |------|------|
  | Neo4j GDS 플러그인 사용 가능 | GDS **Louvain**(모듈성 기반 군집화) |
  | GDS 사용 불가 | Python `networkx` **Louvain**으로 그래프를 내려받아 계산 후 결과만 Neo4j에 다시 씀 |

- 커뮤니티마다 LLM으로 요약문을 만들고 `:Community` 노드에 저장함 —
  속성 `community_id` · `level` · `summary` · `member_node_ids` · `size`
- 요약 생성은 **비동기 병렬**로 수행함
- **트레이드오프를 반드시 문서에 남김** — 커뮤니티 요약은 커뮤니티 수만큼 LLM 호출이 늘어
  구축 시간과 단가가 커짐. README에 **커뮤니티 수 · 총 LLM 호출 수 · 총 소요 시간 · 재구축 주기 제안**을
  실측으로 적음. 값을 추정으로 적지 않음

#### 4-7. 매니페스트 (`S-KI9`)

- `src/v1/kg/store/manifest.json`에 아래를 기록함

  ```json
  {
    "database_name": "lunchpick_kg_v1",
    "entity_vector_index": "lunchpick_kg_entity_v1",
    "embedding_model": "text-embedding-3-large",
    "schema_file": "src/v1/kg/indexer/schema.yaml",
    "source_dir": "src/v1/data/kg",
    "doc_count_in": 0, "doc_count_blocked": 0, "doc_count_indexed": 0,
    "node_count_by_label": {}, "relation_count_by_type": {},
    "normalized_false_count": 0, "dropped_out_of_schema_count": 0,
    "community_count": 0, "community_levels": 0,
    "llm_call_count_extract": 0, "llm_call_count_summary": 0,
    "elapsed_sec_total": 0,
    "indexed_at": "2026-08-07T00:00:00+09:00"
  }
  ```

### 5단계 — 리트리버 구현 (`src/v1/kg/retriever/`)

LangGraph `StateGraph` 단일 워크플로우로 구현함. 병렬 노드는 서로 다른 State 필드에 씀.

| 단계 ID | 노드 | 하는 일 |
|---------|------|--------|
| `S-KQ1` | `route_mode` | 검색 모드 판정(Local / Global / Hybrid) |
| `S-KQ2` | `pre_process` | Pre Technique 적용(3.6) |
| `S-KQ3` | `seed_entities` | 벡터 인덱스로 시작 개체 찾기 |
| `S-KQ4` | `traverse_local` | Cypher 다홉 탐색 (Local · Hybrid) |
| `S-KQ5` | `search_global` | 커뮤니티 요약 검색 (Global · Hybrid) |
| `S-KQ6` | `rerank` | Cohere 리랭킹 |
| `S-KQ7` | `finalize` | 근거 경로 · 출처 문서 동봉하여 반환 |

#### 5-1. 검색 모드 판정 (`S-KQ1`) — 3.5 `[기준]` 조건 → 선택

| 조건(판정 가능한 형태) | 선택 모드 | 런치픽 예 |
|----------------------|----------|----------|
| 질의에 특정 개체 식별자 · 고유명이 1개 이상 있음(회원 · 식당 · 메뉴 · 알레르겐) | **Local** | `M-0003이 먹으면 안 되는 강남 식당` |
| 질의가 주제 요약형(특징 · 경향 · 전반 · 무엇이 많은가)이고 고유명이 없음 | **Global** | `강남 식당들의 원재료 구성 경향` |
| 위 두 조건이 **동시에** 성립하거나 어느 쪽도 성립하지 않음 | **Hybrid** | `밀 알레르기 회원들이 강남에서 겪는 문제` |

- 판정 결과를 응답 메타데이터 `selected_mode`와 `route_reason`으로 반환함(평가 시 원인 추적에 필요함)

#### 5-2. 다홉 탐색 (`S-KQ4`)

- **최대 홉 수 4**를 기본값으로 두고 `settings.yaml`의 `kg_max_hops`로 관리함.
  근거 — ① `gen-data.md`가 만든 최장 경로가 4홉임(회원 → 알레르겐 → 원재료 → 메뉴 → 식당)
- 반환 상한 — 경로 20개 · 노드 100개. 초과하면 잘라 내고 `truncated: true`를 남김
- **경로를 반드시 함께 반환함** — `path`(노드 · 관계 나열) · `evidence_doc_ids` · `evidence_texts`.
  경로 없이 결론만 반환하면 근거 정확도를 잴 수 없음
- 경로가 끊겨 답이 안 나오면 **결과를 지어내지 않고** `no_path` 사유와 끊긴 지점을 반환함
  (`quality_report.json`의 `broken_kg_paths`가 이 동작의 기대값임)

#### 5-3. Pre / Post 기법 (3.6)

- **Pre Techniques `[기준]`** — ② `index-rag.md`와 **같은 조건 → 선택 표**를 씀(규칙이 갈리면
  두 경로의 평가값을 비교할 수 없음)

  | 조건 | 적용 기법 |
  |------|----------|
  | 질의 길이 8자 미만 또는 명사 1개로만 구성 | Query Rewriting |
  | 질의에 조건이 2개 이상 | Multi Query |
  | 구어체 · 은어가 있고 문서 어휘와 다름 | HyDE |
  | 추상 개념어로만 구성 | Step-back |

- **Post Technique `[고정]`** — Cohere 리랭킹 모델. API Key는 `.env`의 `COHERE_API_KEY`.
  Local은 경로 후보를, Global은 커뮤니티 요약 후보를 리랭킹함.
  호출 실패 시 원 점수 순서를 쓰고 `rerank_skipped: true`를 남김

#### 5-4. 응답 규격

- 반환 항목 — `selected_mode` · `route_reason` · `applied_pre_techniques` · `paths`(Local · Hybrid) ·
  `community_summaries`(Global · Hybrid) · `evidence_doc_ids` · `rerank_score` · `rerank_skipped` ·
  `truncated` · `no_path`
- **Structured Output**(3.1 `[고정]`)으로 Pydantic 모델을 반환함

### 6단계 — 기술적 요구사항

- **API Key** — `.env`에서만 읽음. 필요 키: `OPENAI_API_KEY`(임베딩) · `GROQ_API_KEY`(추출 · 요약 LLM) ·
  `COHERE_API_KEY`(리랭킹) · `NEO4J_URI` · `NEO4J_USER` · `NEO4J_PASSWORD`.
  `src/v1/.env.example`에 키 이름만 추가함
- **Config와 소스 분리** — 동시 실행 수 · 최대 홉 수 · 반환 상한 · DB 이름은 전부
  `src/v1/app/common/config.py`가 `src/v1/app/common/settings.yaml`에서 읽음. 매직 넘버를 두지 않음
- **LLM 사양**(3.2 `[고정]`) — Groq LPU · 모델 `openai/gpt-oss-120b` · `temperature=0` ·
  `timeout=30초` · 429 응답 시 지수 백오프 재시도 2회
- **LCEL 실행 방식**(3.1 `[기준]`) — 조건 → 선택

  | 조건 | 선택 |
  |------|------|
  | 인덱서 개체 추출 · 커뮤니티 요약(수백 건 병렬) | **`ainvoke`**(비동기) — 3.5 `[고정]` 비동기 병렬과 일치 |
  | 평가 실행기가 문항 수십 건을 연속 호출 | **`ainvoke`**(비동기) |
  | 개발자 CLI 단발 질의 확인 | **`invoke`**(동기) |
  | UI 스트리밍 | **해당 없음** — v1 이 단계에 UI가 없음. 붙일 때 사용자 문의 |

### 7단계 — 테스트 및 버그 수정

- 프레임워크 **pytest**, 모듈별 단위 테스트를 `src/v1/tests/kg/`에 작성함
- **외부 호출(Groq · OpenAI 임베딩 · Cohere)은 Mock/fixture로 대체**함.
  **Neo4j 접속 시험은 `@pytest.mark.integration`으로 분리**함
- 최소 시험 항목
  1. 오염 문서 3건이 `S-KI2`에서 전부 차단되고 그래프에 노드가 0건 생김
  2. `schema.yaml` 밖 타입이 추출되면 버려지고 `dropped_out_of_schema_count`가 올라감
  3. 4홉 경로(회원 → 알레르겐 → 원재료 → 메뉴 → 식당)가 실제로 이어짐
  4. `broken_kg_paths`에 있는 회원 질의는 `no_path`로 착지하고 답을 지어내지 않음
  5. 모드 판정이 조건 3종에 대해 기대한 모드를 고름
  6. 모든 관계에 `evidence_text`와 `source_doc_id`가 있음(빈 값 0건)
  7. `kg_max_hops`를 2로 낮추면 4홉 질의가 `no_path`로 떨어짐(상한이 실제로 걸림)
  8. Cohere 실패를 주입하면 `rerank_skipped: true`가 반환되고 결과가 비지 않음

### 8단계 — README.md 작성 (`src/v1/kg/README.md`)

- 개요 — 목적 및 주요 기능
- 가상환경 설정 및 실행 — **Windows GitBash · Windows PowerShell · Linux/Mac 3환경** 명령어 각각 기재
- Neo4j 기동 방법(선택 결과와 근거)
- **Graph 구성 가시화 — Mermaid 스크립트**로 인덱서(`S-KI1` ~ `S-KI9`)와
  리트리버(`S-KQ1` ~ `S-KQ7`) 두 그래프를 각각 그림. 병렬 구간을 눈에 보이게 그림
- **지식그래프 스키마 도식 — Mermaid**로 개체 8종 · 관계 9종을 그림
- 디렉토리 구조와 주요 소스 설명
- **선택 결과 기록**(3.5 `[기준]` 요구) — 개체 · 관계 타입 확정 내역과 사용자 검토 결과,
  커뮤니티 탐지 알고리즘 선택, 체크포인트 저장소 선택
- **비용 · 지연 트레이드오프 실측표** — 아래를 실측으로 채움. 추정값을 적지 않음

  | 항목 | 실측 |
  |------|------|
  | 개체 추출 LLM 호출 수 · 소요 시간 | |
  | 커뮤니티 수 · 요약 LLM 호출 수 · 소요 시간 | |
  | 임베딩 호출 수 | |
  | 총 구축 시간 | |
  | Local 질의 p50 · p95 응답 시간 | |
  | Global 질의 p50 · p95 응답 시간 | |
  | ② 벡터 RAG 대비 구축 시간 배수 | |

### 톤앤매너

- 코드 주석과 README는 **한국어 명사체**로 씀. 고정값에는 근거 절 번호를 주석으로 인용함
- 전문 용어는 처음 나올 때 괄호로 쉬운 설명 1회 — 예:
  `커뮤니티 탐지(서로 촘촘히 이어진 개체들을 한 덩어리로 묶는 일)`

---

## [출력]

| 산출물 | 경로 |
|--------|------|
| 인덱서 | `src/v1/kg/indexer/` (`graph.py` · `nodes.py` · `state.py` · `extract.py` · `community.py`) |
| 인덱서 설정 | `src/v1/kg/indexer/schema.yaml` — 확정된 개체 · 관계 타입 |
| 리트리버 | `src/v1/kg/retriever/` (`graph.py` · `nodes.py` · `state.py` · `cypher.py` · `rerank.py`) |
| 그래프 저장소 | `src/v1/kg/store/` — `docker-compose.yml`(선택) · `manifest.json` · `blocked.jsonl` |
| Neo4j 데이터베이스 | `lunchpick_kg_v1` (벡터 인덱스 `lunchpick_kg_entity_v1`) |
| 설정 | `src/v1/app/common/settings.yaml` (기존 파일에 **키 추가만** 함) |
| 의존성 | `src/v1/requirements.txt` (기존 줄 삭제 · 변경 없이 **추가만** 함) |
| 시험 | `src/v1/tests/kg/` |
| 문서 | `src/v1/kg/README.md` |

---

## [제약조건]

### MUST

- 프롬프트 작성 가이드(`references/prompt-guide.md`) 준용
- **반드시 "context7 MCP" 사용** — LangChain · LangGraph · Neo4j · Cypher · GDS · Cohere 문법을
  기억에 의존해 쓰지 않음
- 반드시 의존성을 `src/v1/requirements.txt`에 정의함(Python 한정)
- README.md의 가상환경 활성화는 **Windows GitBash · Windows PowerShell · Linux/Mac**별 명령어를 안내함
- 추가정보나 의사결정이 필요하면 **사용자에게 반드시 문의**함. 이미 확인된 문의 대상은 아래임
  - 코드 base directory (기본값 `src/v1/`)
  - 체크포인트 저장소 — `MemorySaver` / `SqliteSaver`
  - **개체 · 관계 타입 확정**(3.5 `[기준]`이 명시적으로 요구하는 사용자 검토)
  - Neo4j 기동 방법 — 로컬 Docker / 원격 인스턴스
  - GraphRAG 임베딩 모델을 3.4 고정값과 다르게 가져갈지
  - v0 `lp_common.guardrails`를 임포트할지 v1으로 복사할지
  - 커뮤니티 요약 재구축 주기(비용이 큼)

### MUST NOT

- **추측하여 생성하지 않음.** 데이터에 기반하여 수행함
  - `codes.py`에 없는 개체명 · 코드값을 새로 만들지 않음
  - 경로가 끊긴 질의에 그럴듯한 답을 만들어 내지 않음. `no_path`로 착지함
  - 근거 문장(`evidence_text`) 없는 관계를 그래프에 넣지 않음
- 가이드 3.5 · 3.6 `[고정]` 값(LangChain + Neo4j · 비동기 병렬 · 커뮤니티 탐지 · 요약 인덱싱 ·
  Cohere 리랭킹)을 **임의로 바꾸지 않음**
- 데이터베이스 이름 `lunchpick_kg_v1` · 벡터 인덱스 이름 `lunchpick_kg_entity_v1` ·
  확정된 개체 · 관계 타입 이름을 **임의로 바꾸지 않음**(⑤ `testset-graphrag.md`가 같은 문자열을 지목함)
- `schema.yaml` 확정 전에 전체 인덱싱을 시작하지 않음
- 오염 문서를 그래프에 넣지 않음. 반대로 소스에서 지우지도 않음(차단 시험 대상임)
- `src/` 아래 v0 파일을 **수정하지 않음**(읽기 전용). 산출물은 전부 `src/v1/` 아래에만 만듦
- `src/v1/requirements.txt`의 기존 줄을 삭제하거나 버전을 낮추지 않음

### 완료조건 — 검증 가능한 증거 기준

1. **산출 파일 목록 제시** — 위 `[출력]` 표 경로의 실제 `ls` 결과 첨부
2. **pytest 실행 로그 첨부** — `python -m pytest src/v1/tests/kg -v` 결과가 **실패 0건**임
3. **인덱싱 실행 로그 첨부** — 문서 수 · 차단 수 · 라벨별 노드 수 · 타입별 관계 수 ·
   스키마 밖 폐기 수 · 커뮤니티 수 · LLM 호출 수 · 총 소요 시간.
   차단 수가 `quality_report.json`의 `poison_docs` 건수와 **같음**을 보임
4. **샘플 질의 최소 3건의 실행 로그(요청 → 응답) 첨부** — 아래 3건을 반드시 포함함
   - Local — `M-0003이 먹으면 안 되는 강남 식당` (4홉 경로와 근거 문서 ID가 함께 나옴)
   - Global — `강남 식당들의 원재료 구성 경향` (커뮤니티 요약이 근거로 나옴)
   - 경로 끊김 — `quality_report.json`의 `broken_kg_paths` 회원 1명 질의 (`no_path`로 착지함)
5. **비용 · 지연 실측표 첨부** — 8단계 트레이드오프 표를 실측으로 채움
6. **RAGAS · NDCG 실측값은 ⑤ `testset-graphrag.md` 단계에서 기록함.** 이 단계에서는 테스트셋이
   없으므로 점수를 만들어 적지 않음(3.5 완료조건 연계 · 3.7 절차 준용)
7. 목표에 못 미치는 값이 나오면 **값을 고쳐 통과시키지 않고 실측을 그대로 보고**함

---

## [예시]

**Local 질의 응답의 기대 형태**

```json
{
  "query": "M-0003이 먹으면 안 되는 강남 식당",
  "selected_mode": "local",
  "route_reason": "고유명 M-0003 · 강남 검출 → Local",
  "applied_pre_techniques": [],
  "paths": [
    {
      "path": "Member(M-0003)-[AVOIDS]->Allergen(땅콩)-[MAPS_TO]->Ingredient(ING-PEANUT)
               <-[CONTAINS]-Menu(치킨커리)<-[SERVES]-Restaurant(R-SEGNAM-042)",
      "hops": 4,
      "evidence_doc_ids": ["KG-MBR-0003", "KG-ING-PEANUT", "KG-RST-SEGNAM-042"],
      "rerank_score": 0.91
    }
  ],
  "truncated": false, "no_path": false, "rerank_skipped": false
}
```

**경로 끊김의 기대 형태**

```json
{
  "query": "M-0007이 먹으면 안 되는 여의도 식당",
  "selected_mode": "local",
  "no_path": true,
  "no_path_reason": "Allergen(호두) → Ingredient 매핑 문서 없음(결측 주입분)",
  "paths": []
}
```

**하지 말아야 할 형태 (anti-example)**

```json
{ "answer": "M-0007은 여의도 파스타집을 피하는 것이 좋겠습니다.", "paths": [] }
```

> 경로가 없는데 결론만 나옴 = **근거 없는 생성**임. `no_path`로 착지해야 함.
> 이런 응답은 ⑤ 단계 Faithfulness(충실성) 지표를 무너뜨림.
