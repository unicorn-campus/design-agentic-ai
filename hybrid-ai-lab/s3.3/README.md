# S3.3 검색 품질 진단과 개선 실습

교재 슬라이드 1~28 범위의 코드임. S3.2의 KURE-v1 인덱스와 검색·LLM 호출 코드를 복사하지 않고
그대로 불러오며, S3.3에는 베이스라인 평가와 질문 변환 코드만 추가함.

## 추가한 코드

| 파일 | 역할 |
|---|---|
| `src/s32_bridge.py` | S3.2 코드·인덱스를 패키지 이름 충돌 없이 연결 |
| `src/evaluation.py` | 고정 질문의 Top-K 정답 포함률 계산·기록표 생성 |
| `src/query_transform.py` | 조별 완성용 `transform_query` 골격 |
| `src/query_transform_ref.py` | 질문 변환 완성 예시 |
| `src/adaptive_search.py` | Top-1 관문·LLM 라우팅·가중 RRF를 연결한 적응형 검색 |
| `src/hybrid_utils.py` | BM25 색인·정규화·필터·Hit 변환 강사 제공 함수 |
| `src/hybrid_search.py` | 조별 완성용 Hybrid Search 골격 |
| `src/hybrid_search_ref.py` | 읽기 쉬운 변수명과 단계별 주석을 사용한 완성 예시 |
| `src/rerank.py` | `BAAI/bge-reranker-v2-m3` 리랭킹 함수 |
| `src/rerank_ref.py` | 슬라이드 27 리랭킹 완성 예시 |
| `src/answering.py` | Top-5의 질문 조건을 확인하고 원문 근거가 있는 LLM 답변 생성 |
| `src/groq_client.py` | Groq LPU의 `openai/gpt-oss-120b` 호출 어댑터 |
| `templates/baseline_questions.json` | 슬라이드 20의 원본 질문 8건과 사전 정답 ID |
| `run_adaptive.py` | 적응형 검색을 8개 질문에 실행하고 Markdown·JSON 결과 저장 |
| `run8.py` | 강사 제공 8문항 반복 실행기 |
| `render_comparison.py` | 기법별 실제 실행 JSON을 3열 비교표로 변환 |
| `run_lab.py` | 조별 골격 실행기 |
| `run_lab_ref.py` | 완성 예시 실행기 |
| `run_rerank.py` | Hybrid 후보를 리랭킹하고 전후 결과 저장 |
| `measure_slide28_rerank.py` | 8개 질문의 Vector·Hybrid·리랭킹 순위와 warm 지연 실측 |
| `run_answer.py` | 슬라이드 28-1의 프롬프트 확인 및 실제 LLM 답변 실행 |

## 슬라이드 27 Re-ranking

`src/rerank.py`는 Hybrid 후보를 `BAAI/bge-reranker-v2-m3`에 질문·청크 쌍으로 전달하고,
관련성 점수로 다시 정렬함. 모델은 import 때 한 번만 로드하며 기존 `Hit.score`는 보존함.
`--query-transform` 실행 시 변환 결과를 캐시에 저장하고, `--reuse-transform` 실행 시 캐시를 읽어
LLM을 다시 호출하지 않음. `multi`는 각 질문별 리랭킹 후 가중 RRF로 병합하고,
`decomposition`은 하위 질문별 Top3 후보를 보장한 뒤 리랭크 점수 최댓값 중심으로 병합함.

Decomposition 병합에서는 원 질문에 0.1, 각 하위 질문에 동일하게 0.45의 가중치를 배정함.
원 질문은 보조 후보로 유지하고, 하위 질문별 상위 3건은 최종 후보에서 탈락하지 않도록 보장함.
같은 `chunk_id`가 여러 목록에 있으면 한 번만 남기고 가장 높은 변환 질문 리랭킹 점수를 사용함.

복합 질문 병합 규칙은 `--merge-strategy`로 비교 가능함. `legacy`는 기존 가중 RRF,
`coverage`는 하위 질문별 Top3와 변환 점수 최댓값 병합임. Decomposition에는
`coverage`가 기본으로 적용됨.

```powershell
..\s3.2\.venv\Scripts\python.exe run_rerank.py --case-id q6 `
  --query-transform --output results\rerank_q6_transform_hybrid_actual.json
```

같은 변환 질문을 재사용하는 실행임. `--merge-strategy`를 바꾸면 병합 튜닝만 비교 가능함.

```powershell
..\s3.2\.venv\Scripts\python.exe run_rerank.py --case-id q6 `
  --reuse-transform --output results\rerank_q6_cached_actual.json
```

q6 실측은 `results/rerank_q6_27_1_coverage_actual.json`에 저장함. Decomposition으로
질문을 나누고 하위 질문별로 리랭킹한 결과, `D2_0003`은 1위, `D1_0010`은 4위임.
두 정답 모두 최종 결과 수인 Top-5에 포함됨.

## 슬라이드 28 Re-ranking 실측

고정 질문 8건에 Vector Top-5, Hybrid Top-5, 튜닝된 Query Transformation+Hybrid Top-5,
여기에 Re-ranking을 적용한 Top-5를 각각 실행함. 저장된 변환 결과를 재사용하므로 LLM 호출은 0회임.
q7은 현재 인덱스에 정답 청크가 없어 7건만 포함률을 계산함.

```powershell
..\s3.2\.venv\Scripts\python.exe measure_slide28_rerank.py
```

실행 결과는 `results/slide28_rerank_actual.json`에 저장함. Hybrid는 BM25 0.4와 Vector 0.6을 사용함.
q6 Decomposition은 원 질문 0.1과 하위 질문 전체 0.9를 적용하고, 하위 질문별로 리랭킹한 뒤
같은 `chunk_id`의 최댓값을 사용함. 최종 결과는 Top-5이며 모델 준비 뒤 warm 지연을 측정함.

## 슬라이드 28-1 LLM 답변

검색 단계에서 제거한 상품 불일치 감점 규칙을 답변 프롬프트의 조건 확인 규칙으로 옮김.
검색·리랭킹 Top-5는 그대로 유지하고 LLM이 질문의 상품명·고객·기간·채널 등 명시 조건과
청크 메타데이터를 주장별로 비교함. 조건이 다른 청크는 결론과 근거에서 제외함.

프롬프트는 `guide-prompt.md`에 맞춰 `[목표]`·`[역할]`·`[맥락]`·`[입력정보]`·
`[작업방법]`·`[출력]`·`[제약조건]`·`[예시]`의 8개 섹션으로 구성함.
질문에 없는 조건은 배제 기준으로 쓰지 않고, 일반 약관은 상품 메타데이터가 없어도
해당 주장을 직접 뒷받침하면 사용 가능하도록 지시함.

LLM 호출 없이 실제 Top-5와 완성 프롬프트만 확인하는 명령임.

```powershell
..\s3.2\.venv\Scripts\python.exe run_answer.py --prompt-only `
  --output results\slide28_1_prompt_actual.json
```

Groq LPU에서 `openai/gpt-oss-120b`를 한 번 호출해 답변을 만들고 원문 발췌를 검증하는 명령임.

```powershell
..\s3.2\.venv\Scripts\python.exe run_answer.py `
  --output results\slide28_1_answer_actual.json
```

q6 실측에서 Top-5의 `D2_0007`과 `D2_0136`은 질문과 다른 상품이므로 답변 근거에서 제외됨.
LLM은 일반 연회비 규정 `D1_0010`과 한빛 모아생활 혜택 `D2_0003`을 사용함.
참조 번호·원문 발췌·위치 자동 검사 결과는 `automatic_valid: true`, 검증 발췌는 2개임.
Groq API 응답 시간은 3,359.8ms이며 질문 변환·검색·리랭킹 시간은 포함하지 않음.

## 슬라이드 25 Hybrid Search

학생용 `src/hybrid_search.py`에서 `final_scores` 가중합을 완성함. 완성 예시는
`src/hybrid_search_ref.py`에서 확인함. 두 파일은 BM25 검색과 Vector 검색에 같은 질문을 각각 전달하고,
후보를 합친 뒤 두 점수를 0~1로 맞춰 가중합함.

완성 예시 실행 명령임.

```powershell
..\s3.2\.venv\Scripts\python.exe run_lab_ref.py hybrid `
  --query "연회비 면제 조건은?"
```

학생용 골격을 완성한 뒤 실행하는 명령임.

```powershell
..\s3.2\.venv\Scripts\python.exe run_lab.py hybrid `
  --query "연회비 면제 조건은?"
```

## 실행 준비

새 가상환경과 인덱스를 만들 필요 없음. `hybrid-ai-lab/s3.3`으로 이동한 뒤 S3.2 가상환경을 사용함.

```powershell
cd C:\Users\hiond\class\design-agentic-ai\hybrid-ai-lab\s3.3
..\s3.2\.venv\Scripts\python.exe run8.py --mode baseline `
  --output results\baseline.md
```

기본값은 기존 인덱스 `../s3.2/data/chroma/group1`의 `card_docs_ref` 컬렉션과
S3.2의 `retrieval_ref.search`임. S3.2 학생 검색 함수까지 완성한 조는 다음 옵션으로 바꿔 실행 가능함.

```powershell
..\s3.2\.venv\Scripts\python.exe run8.py --mode baseline `
  --student-search --collection card_docs
```

현재 학생용 `card_docs`가 비어 있으면 먼저 S3.2에서 적재해야 함.

## 슬라이드 21 질문 변환

골격 함수는 `src/query_transform.py`의 TODO 2곳을 완성함. 완성 예시는 `_ref` 파일에서 확인함.
S3.2의 `ask_llm`은 교재 축약 코드와 달리 객체의 `.text`가 아니라
`{"content": "..."}` 형태를 반환하므로 그 형식에 맞춰 본문을 꺼내야 함.

한 질문만 변환하는 명령임. `baseline`을 제외한 방식은 Claude API를 한 번 호출함.

```powershell
..\s3.2\.venv\Scripts\python.exe run_lab_ref.py transform `
  --mode multi --query "지난해 카드를 많이 썼는데 다음 연회비도 내야 하나요?"
```

같은 8건에 질문 변환을 적용하는 명령임. 질문당 한 번, 총 8회의 LLM 호출이 발생함.

```powershell
..\s3.2\.venv\Scripts\python.exe run8.py --mode rewrite `
  --output results\rewrite.md
..\s3.2\.venv\Scripts\python.exe run8.py --mode multi `
  --output results\multi.md
..\s3.2\.venv\Scripts\python.exe run8.py --mode hyde `
  --output results\hyde.md
..\s3.2\.venv\Scripts\python.exe run8.py --mode stepback `
  --output results\stepback.md
```

`multi`는 최대 3개, `rewrite`는 1개, `hyde`는 두 줄을 합친 검색문 1개를 반환함.
`stepback`은 상위 개념 질문과 원 질문을 함께 반환함. 호출 오류나 빈 응답은 원 질문 1개로 복구함.

## 평가 데이터 점검 결과

슬라이드 20의 q7은 정답을 `D2 §3`으로 적었으나 현재 S3.1 청크와 S3.2 인덱스에는
질문인 "장기 보유 고객 유지 혜택의 신청 조건"을 뒷받침하는 원문과 대응 `chunk_id`가 없음.
정답을 임의로 연결하지 않도록 q7은 `expected_chunk_ids: []`로 두고 실행 결과에서 `평가 제외`로 표시함.
8건 포함률을 확정하려면 원문·청크·인덱스를 보강하거나 현재 원문에 답이 있는 질문으로 q7을 교체한 뒤
사전 정답 `chunk_id`를 지정해야 함.

## 질문 변환 실제 비교 결과

2026-09-12에 네 기법을 각각 단독 적용해 실제 Claude 질문 변환과 KURE-v1 검색을 수행함.
질문별 Baseline 비교표는 `results/query_transform_comparison_kure.md`에 저장함.

기법별 JSON을 다시 실행한 뒤 비교표를 재생성하는 명령임.

```powershell
..\s3.2\.venv\Scripts\python.exe render_comparison.py
```

| 방식 | Top-3 통과 | Baseline 대비 |
|---|---:|---:|
| Baseline | 7/7 | 기준 |
| Rewriting | 6/7 | -1건 |
| Multi-Query | 5/7 | -2건 |
| HyDE | 6/7 | -1건 |
| Step-Back | 5/7 | -2건 |

q7은 정답 미매핑으로 공통 제외함. Rewriting은 q6, Multi-Query와 Step-Back은 q3·q6,
HyDE는 q3에서 실패함. 이번 질문 세트에서는 어느 변환 기법도 Baseline을 개선하지 못함.
질문 변환을 전체 질문에 일괄 적용하지 않고 질문 유형별로 적용 여부를 결정해야 함.

## Top-1 관문 기반 적응형 검색

`run_adaptive.py`는 다음 순서로 실행됨.  

(1) 원 질문으로 먼저 검색함  
(2) Top-1 코사인 유사도가 `0.70` 이상이면 결과를 그대로 사용하고 LLM을 호출하지 않음  
(3) `0.70` 미만이면 LLM 한 번으로 질문 유형 판정과 한 가지 변환 기법 적용을 함께 수행함  
(4) 원 질문 결과와 변환 질문 결과를 가중 RRF로 병합함  

라우터의 선택지는 Rewriting, Multi-Query, HyDE, Step-Back, Decomposition의 다섯 가지임.  
Multi-Query는 하나의 검색 의도를 다른 표현으로 확장하고, Decomposition은 독립적으로 답할 수 있는  
요구사항이 둘 이상인 복합 질문을 요구사항별 하위 질문으로 분리함.  
LLM 라우터는 같은 호출에서 `clarify`·`keep`·`transform` 중 행동도 선택함. 핵심 대상을 문맥에서  
복원할 수 없으면 사용자 확인 질문을 반환하고, 변환 이득이 없으면 원 검색 결과를 유지함.  

원 질문 목록에 0.5, 변환 질문 목록 전체에 0.5의 가중치를 배정함. Multi-Query는 세 목록이므로  
각 변환 목록에 `0.5 / 3`을 배정하여 질의 수만으로 세 배의 가중치를 얻지 않도록 처리함.  
병합 순위는 원래의 코사인 유사도 점수를 직접 비교하지 않고 RRF 점수로 결정함.  

```powershell
cd C:\Users\hiond\class\design-agentic-ai\hybrid-ai-lab\s3.3
..\s3.2\.venv\Scripts\python.exe run_adaptive.py
```

2026-09-12 Decomposition 추가 전 전체 실행 결과는 `results/adaptive_top1_070.md`에 저장함.  

| 항목 | 결과 |
|---|---:|
| 전체 질문 | 8건 |
| 관문 통과 | 5건 |
| 관문 실패·LLM 호출 | 3건 |
| 평가 가능 질문 | 7건 |
| 최종 Top-3 통과 | 6/7 |

q3·q6·q7에서만 LLM을 호출했으며 q3는 Rewriting, q6은 Decomposition을 선택함.  
q6은 Baseline에서 정답 두 건이 1·2위였지만 Top-1 점수 `0.686`으로 관문을 통과하지 못함. 변환 검색의  
혜택 청크가 RRF에서 반복 득점하여 연회비 정답 청크가 6위로 내려가고 최종 Top-3 판정은 실패함.  
q7은 현재 인덱스에 정답 청크가 없으므로 평가에서 제외함.  

이 결과는 Top-1 유사도 하나만으로 검색 충분성을 보증할 수 없음을 보여줌. q2는 Top-1 청크가 사전 정답이  
아니지만 점수 `0.740`으로 관문을 통과했고, q6은 Baseline Top-3가 이미 충분하지만 불필요한 변환을 수행함.  
따라서 `0.70`은 이번 실습의 분기 동작을 관찰하기 위한 초기 임계값이며 운영 임계값으로 확정한 값이 아님.  

## q6 Decomposition 재검증

Decomposition을 라우터 선택지에 추가한 뒤 q6만 다시 실행한 명령임. 원 질문 가중치는 0.1,
하위 질문 전체 가중치는 0.9로 적용함.  

```powershell
..\s3.2\.venv\Scripts\python.exe run_adaptive.py --case-id q6 `
  --output results\adaptive_q6_decomposition.md `
  --json-output results\adaptive_q6_decomposition.json
```

| 항목 | Decomposition 적용 결과 |
|---|---|
| Baseline Top-1 | `D2_0003`, 유사도 `0.686` |
| 관문 | 부족, LLM 1회 호출 |
| 선택 기법 | `decomposition` |
| 하위 질문 1 | 연회비 면제와 다음 청구일까지의 연체 조건 |
| 하위 질문 2 | 한빛 모아생활 카드 생활 포인트의 전월 실적 조건 |
| 최종 Top-3 | `D1_0010`, `D2_0003`, `D2_0005` |
| 정답 순위 | `D1_0010` 1위, `D2_0003` 2위 |
| 판정 | ○ |

실제 결과는 `results/adaptive_q6_weight01.md`와 `results/adaptive_q6_weight01.json`에 저장함.  

## 개선 효과 확인용 q3·q6

q3는 문서 용어인 연회비를 일상 표현인 "다음 해 고정 비용"으로 바꾸고, q6은 서로 다른 두 주제를  
한 질문에 담도록 변경함. Decomposition에서는 하위 질문별 1위 청크를 한 건씩 보존하고 나머지를  
가중 RRF 순서로 채워, 한 하위 질문의 근거가 전역 RRF에서 사라지지 않도록 처리함.  

```powershell
..\s3.2\.venv\Scripts\python.exe run_adaptive.py `
  --case-id q3 --case-id q6 `
  --output results\adaptive_q3_q6_improved.md `
  --json-output results\adaptive_q3_q6_improved.json
```

| 질문 | Baseline 정답 순위 | 적용 기법 | 변환 후 정답 순위 |
|---|---|---|---|
| q3 | `D1_0010` 2위 | Rewriting | `D1_0010` 1위 |
| q6 | `D2_0003` 3위, `D1_0010` Top-10 밖 | Decomposition | `D2_0003` 3위, `D1_0010` 1위 |

두 질문 모두 Top-1 점수가 `0.70` 미만이므로 관문 실패 후 LLM을 한 번씩 호출함.  
실제 비교 결과는 `results/adaptive_q3_q6_improved.md`에 저장함.  

같은 전략을 전체 8건에 적용한 실제 결과는 `results/adaptive_top1_070_updated.md`에 저장함.  
평가 가능한 7건은 모두 Top-3를 통과했으며, q7은 정답 원문이 없어 평가에서 제외함.  
