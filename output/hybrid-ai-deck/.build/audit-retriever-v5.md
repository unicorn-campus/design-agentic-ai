# Retriever 교육 PPT 24~52페이지 소스 감사  

## 감사 범위와 기준  

- 대상: `review-v4-content.json`의 24~52페이지 본문·표·발표자 노트  

- 기준: Retriever 응용 그래프, 도메인 규칙, 인프라 어댑터, 설정, 관련 테스트의 정적 대조  

- 판정: 소스 계약과 일치하면 `PASS`, 오해 가능성 또는 실제 코드 불일치가 있으면 `수정 필요`  

- 검증 한계: 본 감사에서 테스트와 외부 LLM을 실행하지 않았으며, 소스와 테스트 코드를 읽어 대조함  

## 소스 경로 약어  

- `graph`: `hybrid-ai-lab/vector/retriever/app/application/graph.py`  

- `state`: `hybrid-ai-lab/vector/retriever/app/application/state.py`  

- `transform`: `hybrid-ai-lab/vector/retriever/app/domain/query_transform.py`  

- `scoring`: `hybrid-ai-lab/vector/retriever/app/domain/scoring.py`  

- `vector`: `hybrid-ai-lab/vector/retriever/app/domain/vector_search.py`  

- `chroma`: `hybrid-ai-lab/vector/retriever/app/infrastructure/chroma_store.py`  

- `bm25`: `hybrid-ai-lab/vector/retriever/app/infrastructure/bm25_index.py`  

- `tokenizer`: `hybrid-ai-lab/vector/retriever/app/domain/korean_tokenizer.py`  

- `reranker`: `hybrid-ai-lab/vector/retriever/app/infrastructure/reranker.py`  

- `llm`: `hybrid-ai-lab/vector/retriever/app/infrastructure/llm_client.py`  

- `settings`: `hybrid-ai-lab/vector/retriever/app/settings.py`  

## 핵심 오류 요약  

1. 46페이지의 분해 리랭킹 설명에 하위 질문별 그룹 가중치 `0.45`와 실제 병합 계수 `0.9`가 혼재함.  
   분해 경로는 그룹별 `0.45`를 최종 산식에 사용하지 않고, 하위 점수 최댓값에 `0.9`를 곱함.  

2. 48페이지의 `<검색결과 목록>`은 실제 `<검색결과목록>`과 다르며, `\n＇`의 전각 따옴표 때문에  
   코드 발췌가 Python 문법으로 성립하지 않음.  

3. 50페이지와 관련 프롬프트 사이에 소스 자체 모순이 존재함. 시스템 프롬프트는 주의사항이 없으면  
   빈 문자열을 허용하지만, 실제 검증기는 빈 `caution`을 `SCHEMA_ERROR`로 처리함.  

4. 28페이지 후보 수는 similarity 기준으로는 맞지만, MMR에서는 Chroma가 `raw_k`의 기본 2배를 먼저  
   조회한 뒤 `raw_k`개를 선택함. 표의 숫자를 “그래프 유지 후보”로 한정할 필요가 있음.  

5. 42·45페이지의 “확보”는 후보 풀 또는 우선 배치를 뜻함. 최종 `top_k` 절단 뒤에도 모든 하위 질문의  
   후보가 반드시 남는다는 보장은 아님.  

6. 49페이지는 실제 답변 생성 입력을 호환용 `prompt` 하나로 표현함. 실제 우선 입력은  
   `system_prompt`와 `user_prompt`의 두 메시지임.  

## 페이지별 감사  

### 24페이지 — Retrieving 구분 페이지  

- 판정: **수정 필요**  

- 근거: 본문 제목은 소스 중립적이지만 발표자 노트가 자동화·사람 승인·프롬프트 문서 이야기로 구성되어  
  Retriever 구분 페이지와 무관함. 표시된 슬라이드 번호도 `9`로 추출되어 현재 24페이지와 불일치함.  

- 권장 문구: 노트를 “Retriever는 준비 확인 → 검색 → 변환 → 병합·리랭크 → 답변·검증 순으로 진행함”으로  
  교체하고, 표시 번호의 의도 여부 확인 필요.  

### 25페이지 — check_search_readiness  

- 판정: **수정 필요**  

- 근거: 입력 검증과 인덱스 건수·서명 검사는 정확함(`graph:734-769`). 다만 입력 오류는  
  `validation_errors`로 반환되지만, 빈 컬렉션이나 서명 불일치는 `IndexUnavailableError` 발생 경로임.  
  0.86 변환 관문은 이 노드가 아니라 `assess_transform_gate` 책임임(`graph:838-850`).  

- 권장 문구: “정상 시 `index_info`, 요청값 오류 시 `validation_errors`, 인덱스 오류 시 예외 발생”으로 수정.  
  0.86 설명은 29페이지로 이동.  

### 26페이지 — vector_search 역할  

- 판정: **PASS**  

- 근거: 질문·역할·모드·`top_k`로 후보 수를 계산하고 벡터 검색을 수행하며, 첫 후보의 원 벡터 점수를  
  변환 관문 점수로 보존함(`graph:774-833`). similarity와 MMR 선택도 설정에 따름(`graph:782-807`).  

- 권장 문구: 현행 유지.  

### 27페이지 — Chroma 검색 코드  

- 판정: **PASS**  

- 근거: `query_embeddings`, `n_results=options.fetch_k(k)`, `where`, `include` 호출이 실제 코드와 일치함  
  (`chroma:126-144`). MMR일 때만 `embeddings`를 `include`에 추가함(`chroma:136-138`).  

- 권장 문구: 현행 유지. 선택 사항으로 “similarity는 `fetch_k(k)=k`” 설명 추가 가능(`vector:38-45`).  

### 28페이지 — 검색 모드별 후보 수  

- 판정: **수정 필요**  

- 근거: `top_k=5`, 배수 4일 때 일반 모드는 `fused_k=5`, `raw_k=20`, 리랭크 모드는  
  `fused_k=10`, `raw_k=40`으로 정확함(`graph:591-598`, `settings:168`). 그러나 MMR은 Chroma에서  
  기본적으로 `raw_k×2`를 조회한 뒤 `raw_k`개를 선택함(`vector:38-45`, `chroma:139-167`).  

- 권장 문구: 표의 “원시 후보”를 “그래프가 유지하는 검색 후보”로 수정. MMR 주석은  
  “Chroma 조회 풀 40/80 → MMR 선택 20/40”으로 추가.  

### 29페이지 — assess_transform_gate  

- 판정: **PASS**  

- 근거: `off`는 검토 생략, `auto`는 원 질문 첫 벡터 점수를 기본 0.86과 비교, 기준 이상은  
  `gate_pass`, 미만 또는 점수 없음은 변환 검토 경로임(`transform:57-79`, `settings:177`).  

- 권장 문구: 현행 유지.  

### 30페이지 — plan_query_transform  

- 판정: **PASS**  

- 근거: 캐시 우선 조회 후 미적중 시 Router LLM 호출, 결과 행동은 `keep·clarify·transform`임.  
  형식·규칙 검증 실패는 `keep`과 빈 변환 질문으로 대체함(`transform:82-121`, `graph:887-910`).  

- 권장 문구: 현행 유지. “전송 실패”가 아니라 “구조·질문 수 검증 실패” 시 `keep`임을 유지.  

### 31페이지 — 다섯 가지 변환 기법  

- 판정: **PASS**  

- 근거: 기법 목록과 질문 수가 정확함. `multi=3`, `decomposition=2~4`, 나머지는 1개 규칙임  
  (`transform:10-54`, `transform:156-176`). 캐시 적중 시 LLM 호출이 생략됨(`transform:91-119`).  

- 권장 문구: 현행 유지.  

### 32페이지 — bm25_search 역할  

- 판정: **PASS**  

- 근거: 원 질문, 역할별 허용 등급, `raw_k`로 BM25를 호출하고, 빈 결과에 경고를 생성함  
  (`graph:914-940`). Kiwi 토큰화와 사용자 사전 적용도 실제 구현임(`bm25:166-175`,  
  `tokenizer:64-107`).  

- 권장 문구: 현행 유지.  

### 33페이지 — BM25S 호출 코드  

- 판정: **PASS**  

- 근거: `retrieve([terms], k, weight_mask, show_progress=False)` 호출과 허용 마스크 적용이 일치함.  
  반환 시에도 마스크가 0이거나 점수가 0 이하인 문서를 제거함(`bm25:198-223`).  

- 권장 문구: 현행 유지.  

### 34페이지 — fuse_scores 가중 결합  

- 판정: **PASS**  

- 근거: 벡터와 BM25 후보 ID 합집합에 각 신호를 최소-최대 정규화한 후 기본 가중치  
  Vector 0.6, BM25 0.4로 합산함(`scoring:32-95`, `settings:172-173`).  

- 권장 문구: 현행 유지.  

### 35페이지 — 정규화 계산 예시  

- 판정: **PASS**  

- 근거: 누락 신호를 0으로 포함하고 모든 값이 같으면 모두 0으로 만드는 규칙이 정확함  
  (`scoring:11-23`). 제시된 A=0.600, B=0.933, C=0.200 계산도 코드와 일치함.  

- 권장 문구: 현행 유지.  

### 36페이지 — complete_original_results 역할  

- 판정: **PASS**  

- 근거: vector 계열은 `vector_hits`, hybrid 계열은 융합 결과를 `baseline_hits`로 보존하고,  
  현재 `hits`는 `top_k`로 절단함(`graph:987-1002`). 이후 변환·리랭크·완료 분기도 정확함  
  (`graph:403-410`).  

- 권장 문구: 현행 유지.  

### 37페이지 — 기준 후보 보존 코드  

- 판정: **PASS**  

- 근거: 리랭크 모드의 `baseline_hits`는 `top_k×2`, 현재 `hits`는 `top_k`로 보관함.  
  `top_k=5`이면 10개와 5개가 맞음(`graph:591-598`, `graph:990-1002`).  

- 권장 문구: 현행 유지. “원본 핵심 코드 출처: 페이지”의 미완성 메타 문구만 정리 권장.  

### 38페이지 — search_transformed 역할  

- 판정: **PASS**  

- 근거: 변환 질문을 같은 모드로 순차 검색하고 질문별 그룹을 같은 순서로 저장함. 실패 그룹은 빈 목록,  
  경고는 예외 클래스명으로 남김(`graph:1025-1036`). 이후 분기도 정확함(`graph:413-418`).  

- 권장 문구: 현행 유지.  

### 39페이지 — _run_search_transformed 코드  

- 판정: **PASS**  

- 근거: 실제 함수가 그대로 반영되어 있음. `_search_one` 성공 결과 추가, 실패 시 빈 그룹과 예외 클래스명  
  경고 추가, 최종 두 필드 반환이 정확함(`graph:1028-1036`).  

- 권장 문구: 현행 유지.  

### 40페이지 — _search_one 검색 분기  

- 판정: **PASS**  

- 근거: 모든 모드가 먼저 벡터 검색을 수행함. vector 계열은 `fused_k`로 절단하고, hybrid 계열은  
  같은 질문의 BM25 결과와 융합함(`graph:1004-1023`). `_uses_vector_only`는 두 vector 모드임  
  (`graph:50-70`).  

- 권장 문구: 현행 유지.  

### 41페이지 — merge_queries 가중 RRF  

- 판정: **PASS**  

- 근거: 청크별로 `weight/(rrf_k+position)`을 누적하고 점수·최고 순위·청크 ID 순으로 정렬함  
  (`transform:183-215`). 일반 변환은 원 질문 전체 0.5, 변환 질문 전체 0.5이며 변환 질문별로 균등 분할함  
  (`transform:242-293`, `settings:178-180`).  

- 권장 문구: 현행 유지. “변환 질문 전체 0.5, 각 질문은 `0.5/N`” 표기 유지 권장.  

### 42페이지 — decomposition 검색 병합  

- 판정: **수정 필요**  

- 근거: 비리랭크 분해 검색은 원 질문 0.1, 변환 전체 0.9의 RRF를 계산한 뒤 각 하위 질문의 Top-1을  
  질문 순서대로 우선 배치함(`graph:1044-1058`, `transform:217-293`). 다만 중복 청크를 제거하고 마지막에  
  `top_k`로 자르므로, `top_k`가 하위 질문 수보다 작으면 모든 하위 질문 결과가 최종 보장되지는 않음.  

- 권장 문구: “각 하위 질문 Top-1을 중복 제거해 우선 배치하고, 나머지를 RRF 순서로 채운 뒤  
  `top_k`로 절단”으로 수정.  

### 43페이지 — rerank 역할과 실패 경로  

- 판정: **PASS**  

- 근거: 원 질문과 각 변환 질문의 후보군을 해당 질문으로 각각 평가함. 일반 기법은 리랭크 순위 RRF,  
  분해 기법은 하위 점수 최댓값 중심 결합임(`graph:1070-1164`, `transform:297-427`). 변환 질문이 있는  
  리랭크 실패는 `merge_queries`, 없는 실패는 직전 결과 확정 경로임(`graph:319-330`, `graph:427-434`).  

- 권장 문구: 현행 유지.  

### 44페이지 — Cross-Encoder 호출  

- 판정: **PASS**  

- 근거: 질문과 각 본문을 쌍으로 만들고 Sigmoid 활성화로 점수를 생성함(`reranker:16-44`). 일반 변환은  
  서로 다른 그룹의 원점수 크기를 직접 더하지 않고 리랭크된 순위를 가중 RRF로 병합함  
  (`transform:411-427`).  

- 권장 문구: 현행 유지.  

### 45페이지 — decomposition 리랭크 병합  

- 판정: **수정 필요**  

- 근거: 각 하위 질문의 상위 3개를 후보 풀에 포함하고, 동일 청크는 하위 점수 최댓값을 사용함.  
  최종 점수 `0.9×max(하위 점수)+0.1×원 질문 점수`와 0.89 예시는 정확함  
  (`transform:347-409`, `settings:180-181`). 다만 최종 `top_n` 절단으로 각 하위 질문 Top-3가 모두  
  최종 결과에 남는 것은 아님.  

- 권장 문구: “각 하위 질문 Top-3를 병합 후보 풀에 포함”으로 수정하고 “최종 결과는 병합 점수 상위  
  `top_k`”를 추가.  

### 46페이지 — rerank 처리 예시  

- 판정: **수정 필요**  

- 근거: 분해 경로에서 그룹 튜플의 `0.45`는 최종 병합 산식에 사용되지 않음. 실제 코드는 하위 질문별  
  점수 최댓값을 구한 뒤 `0.9×최댓값+0.1×원 질문 점수`를 적용함(`transform:347-389`). 관련 테스트의  
  그룹 가중치 `0.45`와 실제 검증 식 `0.9×0.95+0.1×0.8`도 이 차이를 보여 줌  
  (`tests/test_knowledge_domain.py:229-255`).  

- 권장 대체 예시:  

```text  
원 질문: A=0.80, B=0.70  
하위 1: B=0.95, C=0.90  
하위 2: D=0.92, B=0.85  
B = 0.9×max(0.95, 0.85) + 0.1×0.70 = 0.925  
D = 0.9×0.92 = 0.828, C = 0.9×0.90 = 0.810, A = 0.1×0.80 = 0.080  
최종 Top-3: B → D → C  
```  

### 47페이지 — build_prompt 역할  

- 판정: **PASS**  

- 근거: 수정된 내용이 실제 책임과 일치함. 답변 관문은 진입 전 `_finalize_hits`에서 수행하고  
  (`graph:195-214`), 이 노드는 시스템·사용자·호환용 프롬프트만 조립함(`graph:333-340`,  
  `graph:1166-1256`). `prompt_only`와 검증 실패 재진입 분기도 정확함(`graph:437-438`,  
  `graph:561-563`).  

- 권장 문구: 현행 유지.  

### 48페이지 — XML 근거 구성 코드  

- 판정: **수정 필요**  

- 근거: 실제 태그는 `<검색결과목록>`인데 슬라이드는 `<검색결과 목록>`으로 공백이 들어감.  
  `f'<검색결과 순번="{index}">\n＇` 끝의 문자는 전각 따옴표여서 Python 코드가 아님. 실제 코드는  
  입력값을 `escape`하고, 근거가 없으면 `해당 없음`을 사용함(`graph:1224-1256`).  

- 권장 발췌:  

```python  
blocks = []  
for index, hit in enumerate(state.get("hits", []), start=1):  
    blocks.append(  
        f'<검색결과 순번="{index}">\n'  
        f"<청크ID>{escape(str(hit.chunk_id))}</청크ID>\n"  
        f"<문서유형>{escape(str(hit.metadata.get('doc_type', 'unknown')))}</문서유형>\n"  
        f"<원본문서>{escape(str(hit.source))}</원본문서>\n"  
        f"<위치>{escape(str(hit.location))}</위치>\n"  
        f"<본문>{escape(str(hit.text))}</본문>\n"  
        "</검색결과>"  
    )  
```  

사용자 입력 태그는 `<검색결과목록>`, `<사용자질문>`, `<수정지침>`으로 표기 필요  
(`graph:1239-1249`).  

### 49페이지 — generate_answer  

- 판정: **수정 필요**  

- 근거: 실제 호출은 `system_prompt`와 `user_prompt`를 system·human 메시지로 전달함. `prompt`는  
  `user_prompt`가 없을 때의 호환용 대체값임(`graph:1261-1291`, `llm:238-309`). 남은 호출 예산 안에서  
  최대 3회 전송 시도하고, 실제 시도 횟수를 `llm_calls`에 누적함(`graph:188-192`, `graph:343-358`).  

- 권장 문구: “입력: `system_prompt` + `user_prompt` + 남은 전송 시도 예산”으로 수정.  
  코드 발췌의 system·human 메시지 표기는 유지.  

### 50페이지 — verify_evidence 검증 항목  

- 판정: **수정 필요**  

- 근거: ref 범위, 인용의 연속 원문 포함, 위치 존재, 결론·주의사항·근거 존재 검사는 실제와 일치함  
  (`scoring:136-245`). 그러나 시스템 프롬프트는 주의사항이 없으면 빈 문자열을 허용함  
  (`graph:1200-1204`)과 달리, 검증기는 빈 `caution`을 “caution 누락” 스키마 오류로 처리하고 대체 문구를  
  넣음(`scoring:216-229`). 이는 교육자료 오류가 아니라 현재 소스 내부 계약 불일치임.  

- 권장 문구: “현재 검증 구현은 빈 `caution`을 허용하지 않음. 프롬프트의 ‘없으면 빈 문자열’ 지시와  
  불일치하며 코드 계약 정합화가 필요한 상태”를 명시.  

### 51페이지 — 근거 대조 핵심 코드  

- 판정: **PASS**  

- 근거: `ref-1`로 청크를 선택하고 공백·바깥 따옴표를 정규화한 인용이 본문에 연속 포함되는지 검사함.  
  위치는 비어 있지 않은지만 검사하며 원본 파일의 실제 위치를 다시 열어 대조하지 않음  
  (`scoring:117-125`, `scoring:150-238`).  

- 권장 문구: 현행 유지.  

### 52페이지 — 검증 실패 수정과 종료  

- 판정: **PASS**  

- 근거: 검증 실패 시 오류별 `repair_hints`를 누적하고 `build_prompt`로 돌아감. `MAX_REPAIRS=2`이면  
  최초 생성 뒤 최대 2회의 재생성 기회이며, 호출 예산이 먼저 끝나면 `halted_by_limit`으로 종료함  
  (`graph:369-382`, `graph:445-452`, `graph:561-563`). API 기본 요청 예산 2회와 CLI 기본 8회가 맞고,  
  질문 변환 전송도 같은 `llm_calls` 예산을 사용함(`settings:161-163`, `presentation/api.py:184-202`,  
  `presentation/cli.py:18-63`).  

- 권장 문구: 현행 유지. 발표 시 “API에서 auto 변환이 1회를 쓰면 답변 생성에 남는 기본 예산은 1회”를  
  덧붙이면 반복 예산 관계가 더 명확함.  

## 최종 판정 집계  

- PASS: 20개 페이지 — 26, 27, 29~41, 43, 44, 47, 51, 52  

- 수정 필요: 9개 페이지 — 24, 25, 28, 42, 45, 46, 48, 49, 50  
