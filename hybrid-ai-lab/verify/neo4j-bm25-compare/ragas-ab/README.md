# BM25를 Neo4j로 바꾸면 최종 답변 품질이 달라지나 — A/B 시험

직전 시험(`../README.md`)은 **순위만** 견줬고, 그 순위 차이가 최종 답변까지 바꾸는지는 재지 않았음.  
이 폴더는 그 남은 숙제를 푸는 자리임. 기존 BM25(Kiwi + bm25s, 앱 안 색인)를 "A 방식"  
(Kiwi로 미리 나눈 낱말을 Neo4j 전문 검색 인덱스에 `whitespace` 분석기로 색인)으로 바꿔 끼우고  
같은 평가셋으로 세 번 돌려 견줌.

`indexer/`, `retriever/`, `ragas/`의 코드와 계획 파일, 평가셋, 데이터는 읽기만 했고 한 줄도 고치지 않음.

## 한 줄 판정

**판정 불가 — 다만 "A 방식이 나쁘다"는 증거는 나오지 않음.**

검색 지표 4종(Recall@5, nDCG@5, Hit@5, MRR@5)과 답 없음 문항 거절은 **세 실행이 완전히 같음**.
RAGAS는 ContextRecall이 세 실행 모두 1.000이고 ContextPrecision과 AnswerRelevancy는 흔들림 안에 들어옴.
숫자만 보면 Faithfulness가 0.848에서 0.735로 떨어져 흔들림(0.061)을 넘지만, **그 차이를 만든 문항 2건이
모두 기준과 똑같은 근거 조각을 썼음** — 즉 검색 결과는 같고 답변 문장만 달라진 것이라 BM25 탓이 아님.

결론: 이 평가셋에서 **BM25 때문에 근거가 달라진 문항은 Q02 하나뿐**이고, 그 문항도 양쪽 다 같은 답을 냈음.
그러나 답변 생성 LLM의 흔들림이 지표 차이보다 커서, 기준 2회만으로는 "바꿔도 된다"를 확정할 수 없음.
**기준을 3회 더 돌려 흔들림 폭을 제대로 잡은 뒤 다시 판정하기를 권함**(아래 「남은 한 걸음」).

## 구성

| 파일 | 하는 일 |
|------|---------|
| `neo4j_keyword_index.py` | 기존 세대 색인을 감싸 `keyword_search`만 Neo4j 전문 검색으로 보내는 어댑터와 적재, 정리 도구 |
| `run_variant.py` | BM25를 바꿔 끼운 채로 기존 `evaluate_retriever.py`를 1회 돌리는 진입 스크립트 |
| `smoke_check.py` | LLM 없이(외부 API 0회) 바꿔 끼우기가 먹히는지, 순위가 얼마나 겹치는지 확인 |
| `compare.py` | 세 실행 결과를 모아 `compare.md`와 `compare.json`을 만듦 |
| `runs/{base1,base2,A}/retriever.json` | 실행별 검색과 답변 생성 결과(RAGAS 채점 입력) |
| `runs/{base1,base2,A}/ragas.json` | 실행별 RAGAS 4지표 채점 결과(문항별 점수와 반복 3회 값) |
| `smoke_check.json`, `compare.md`, `compare.json` | 결과 파일 |
| `_backup/active_generation.json` | 실행 전 사용 중 세대 포인터 백업 |

## 기존 코드를 고치지 않고 바꿔 끼운 방법

기존 검색기는 세대 색인을 `app/application/ports.py`의 `SearchIndexPort`로 씀.  
조립 지점(`app/bootstrap.py`)이 `LocalIndexProvider`를 직접 만들어 밖에서 끼워 넣을 자리가 없으므로,  
`run_variant.py`가 **그 실행 안에서만** `LocalIndexProvider.acquire`를 감싸 돌려주는 색인을  
`Neo4jKeywordIndex`로 한 겹 쌈. 파일은 그대로 두고 메모리 안에서만 바꿔 끼우는 방식임.

`Neo4jKeywordIndex`는 포트의 12개 메서드 중 **`keyword_search` 하나만** Neo4j로 보내고  
나머지(벡터 검색, 말뭉치 조회, 낱말 분석, 문서 빈도 등)는 원래 구현에 그대로 넘김.  
기존 구현과 같게 맞춘 것: 같은 Kiwi 분석기로 자른 낱말을 질의로 씀, 점수 0 이하는 버림,  
열람 등급과 회원 필터는 점수를 낸 뒤 순위 매기기 전에 적용, 같은 점수면 조각ID 오름차순.

접속은 Neo4j **HTTP Query API**(포트 7474)를 씀 — 검색기 가상환경에 `neo4j` 드라이버가 없고  
새 패키지를 깔지 않기로 했기 때문임. 주소와 사용자는 `../../neo4j-vector-search/.env.example`에서,  
비밀번호는 실습 공용 컨테이너의 `hybrid-ai-lab/neo4j/.env`에서 읽고 출력하지 않음. 포트를 바꿨으면 `NEO4J_HTTP_PORT`로 넘김.

## 실행

```bash
docker compose -f neo4j/compose.yml up -d     # hybrid-ai-lab 폴더에서. 이미 떠 있으면 하지 않아도 됨
```

```bash
# 0) LLM 없이 바꿔 끼우기 점검
retriever/vector-retriever/.venv/Scripts/python verify/neo4j-bm25-compare/ragas-ab/smoke_check.py

# 1) 세 실행(기준1, 기준2, A) — 설정은 모두 같게 두고 BM25만 바꿈
PY=retriever/vector-retriever/.venv/Scripts/python
$PY verify/neo4j-bm25-compare/ragas-ab/run_variant.py --bm25 baseline --label base1 \
    --out verify/neo4j-bm25-compare/ragas-ab/runs/base1/retriever.json
$PY verify/neo4j-bm25-compare/ragas-ab/run_variant.py --bm25 baseline --label base2 \
    --out verify/neo4j-bm25-compare/ragas-ab/runs/base2/retriever.json
$PY verify/neo4j-bm25-compare/ragas-ab/run_variant.py --bm25 neo4j --label A \
    --out verify/neo4j-bm25-compare/ragas-ab/runs/A/retriever.json

# 2) 비교표
ragas/.venv/Scripts/python verify/neo4j-bm25-compare/ragas-ab/compare.py
```

- 전용 라벨 `RagasAbChunk`와 전용 인덱스 `ragasab_tokens_ws`만 만들고 끝나면 지움
- 사용 중 세대 포인터(`active_generation.json`)는 실행 전 백업하고 실행 뒤 내용으로 같은지 확인함. 재색인은 하지 않음
- 새 패키지를 깔지 않음. `neo4j` 말고 다른 컨테이너를 켜거나 끄지 않음

## 시험 조건

| 항목 | 값 |
|------|-----|
| 세대 | `gen-birthfix-20261018b-efeb65bd`(청크 218) — 세 실행 모두 같음 |
| 평가셋 | `ragas/eval-set.json` 22문항(답 있음 17, 답 없음 5) |
| top_k | 5(세 실행 같음) |
| 답변 생성 | 프로젝트 설정 그대로 — Groq `gpt-oss-120b`(C-01 ~ C-04) |
| RAGAS 평가자 | 계획 파일 `ragas/plans/top_k.yaml`과 같은 local(Ollama Qwen3.5-9B), 반복 3회, 핵심 4지표 |
| 평가셋 지문 | `0fdb90cdd27c` — 계획 파일 `top_k.yaml`의 `eval_set.sha256`과 같음(실행 중 직접 계산해 대조) |
| Neo4j | `neo4j`(HTTP 7474, Bolt 7687) |
| 걸린 시간 | 검색과 답변 생성 114초, 112초, 117초. RAGAS 채점 12.8분, 14.1분, 11.5분(합계 약 44분) |

## 결과

### 0) 바꿔 끼우기가 먹혔는지(`smoke_check.json`)

| 항목 | 값 |
|------|-----|
| Neo4j 낱말 검색 호출 | 22회(점검)와 52회(A 실행) — 정말 Neo4j로 갔음 |
| BM25 상위 10 겹침(평가셋 22문항) | 0.955 |
| 상위 1 일치 | 21/22 |

직전 시험의 42문항 결과(겹침 0.952, 상위 1 40/42)와 같은 수준임.  
순위가 달라진 문항은 Q01, Q03, Q05, Q06, Q07, Q13, Q14, Q15, Q18, Q19이며,  
대부분 **상위 5 안에서 자리만 바뀌는 수준**임(Q03은 1위와 2위가 서로 바뀜).

### 1) 검색 지표(코드 채점 @5)

| 지표 | 기준1 | 기준2 | A | 판정 |
|---|---:|---:|---:|---|
| Recall@5 | 1.000 | 1.000 | 1.000 | 차이 없음 |
| nDCG@5 | 0.993 | 0.993 | 0.993 | 차이 없음 |
| Hit@5 | 1.000 | 1.000 | 1.000 | 차이 없음 |
| MRR@5 | 1.000 | 1.000 | 1.000 | 차이 없음 |

BM25 순위가 상위 5 안에서 조금 바뀌어도, 벡터와 합치고 리랭킹까지 거친 **첫 검색 상위 5의 품질은  
세 실행이 똑같음**. 이 평가셋에서는 정답 조각이 상위 5에 늘 들어온다는 뜻임.

### 2) RAGAS 4지표

채점 대상은 '근거를 들고 끝난 답 있음 문항'이라 실행마다 문항 수가 다름(14, 14, 12).
그래서 **세 실행이 모두 채점한 11문항**으로 다시 낸 값을 함께 봄. 로컬 평가자는 반복 3회가 모두 같은 값이라
평가자 반복 흔들림은 네 지표 모두 0.000이었음. 아래 흔들림은 기준1과 기준2의 차이임.

| 지표 | 기준1 | 기준2 | A | 흔들림 | 판정 |
|---|---:|---:|---:|---:|---|
| ContextPrecision | 0.973 | 0.990 | 0.990 | 0.017 | 차이 없음 |
| ContextRecall | 1.000 | 1.000 | 1.000 | 0.000 | 차이 없음 |
| Faithfulness | 0.848 | 0.788 | 0.735 | 0.061 | 숫자로는 악화(−0.114) |
| AnswerRelevancy | 0.813 | 0.826 | 0.829 | 0.012 | 숫자로는 개선(+0.015) |

채점 문항 전체(14, 14, 12행)로 낸 값은 `compare.md` 2장에 있음. 두 표의 방향은 같음.

**Faithfulness 하락은 BM25 탓이 아님.** 공통 11문항에서 A와 기준이 달라진 문항은 Q01, Q07, Q15 세 건인데,
**세 문항 모두 세 실행이 똑같은 근거 조각을 썼음**(`compare.md` 4장). 검색 결과가 같으니 원인은 답변 문장임.

| 문항 | Faithfulness(기준1 → 기준2 → A) | 답변이 어떻게 달랐나 |
|---|---|---|
| Q01 「연회비 면제 조건」 | 1.00 → 1.00 → 0.50 | A만 "연체가 없으면"이라는 조건을 한 문장에 더 붙임 |
| Q15 「생활비 이전을 꺼린 이유」 | 1.00 → 1.00 → 0.50 | 같은 뜻을 다른 말로 줄여 씀 |
| Q07 「생활 포인트 적립률과 월 한도」 | 0.33 → 0.33 → 0.75 | A만 두 문장으로 나눠 적어 점수가 **올라감** |

평가자가 한 문장에 든 조건을 주장 여러 개로 쪼갠 뒤 "조건을 빠뜨렸다"며 감점하는 버릇은
`ragas/README.md` 9장 3번에 이미 적힌 알려진 한계임. Q01이 꼭 그 경우임.

또한 Q02는 A의 근거가 2개에서 4개로 늘어 **BM25 차이가 있는 유일한 공통 문항**인데,
Faithfulness가 기준1 1.00, 기준2 0.33, A 0.33이었음. BM25가 같은 기준2도 0.33이므로 이 역시 흔들림임.

### 3) 끝맺음

| 항목 | 기준1 | 기준2 | A |
|---|---:|---:|---:|
| 답 있음 17문항 중 근거를 들고 끝남 | 14 | 14 | 12 |
| 그중 정답 조각을 담음 | 14 | 14 | 12 |
| 답 없음 5문항 중 확인 필요로 끝남 | 5 | 5 | 5 |

답 없음 5문항(Q18 ~ Q22)은 세 실행 모두 지어내지 않고 확인 필요로 끝냄.

A의 14 → 12는 **BM25 탓이 아니라 LLM 시간 초과 탓**임. 실행별 시간 초과 문항은  
기준1 1건(Q11), 기준2 2건(Q06과 Q13), A 3건(Q04, Q08, Q11)임.

### 4) 달라진 문항

같은 설정으로 두 번 돌린 기준1과 기준2에서도 **4문항**이 달라짐(Q06, Q08, Q11, Q13).  
기준1과 A에서 달라진 문항은 **3문항**(Q02, Q04, Q08)이며, 그중 2문항은 시간 초과가 원인임.

| 문항 | 무엇이 달랐나 | 원인 |
|---|---|---|
| Q02 「할부 철회는 며칠 안에」 | 근거 조각 2개 → 4개(같은 약관 문서, 제16조는 양쪽 다 1순위) | BM25 차이 |
| Q04 「약관이 바뀌면 언제 안내」 | answered → 확인 필요(근거 3개 → 0개) | C-03(질문 변환) 시간 초과 |
| Q08 「모아생활 포인트 재충전」 | answered → 답변 실패(근거 5개는 같음) | C-04(답변 생성) 시간 초과 |

즉 **BM25 때문에 달라진 문항은 Q02 하나**이며, 그것도 근거가 늘었을 뿐 답은 양쪽 다 나왔음.  
반면 BM25가 똑같은 기준1 대 기준2도 4문항이 달라졌으므로, A의 차이는 **실행 간 흔들림보다 작음**.

중요한 사실 하나: 기준1과 기준2는 BM25가 완전히 같은데도 Q08의 근거 묶음이 달랐음.  
검색 질의를 LLM(C-03)이 만들기 때문에, **BM25를 고정해도 근거가 실행마다 흔들림**.  
흔들림 폭을 평가자 반복만으로 재면 안 된다는 `ragas/README.md` 9장 1번 지적을 이 시험이 다시 확인함.

## RAGAS 채점을 다시 돌리는 법

검색과 답변 생성을 다시 하지 않고 채점과 비교표만 다시 만들 때 씀.

```bash
PY=ragas/.venv/Scripts/python
for V in base1 base2 A; do
  $PY ragas/evaluate_ragas.py \
    --log verify/neo4j-bm25-compare/ragas-ab/runs/$V/retriever.json \
    --provider local --repeat 3 \
    --out verify/neo4j-bm25-compare/ragas-ab/runs/$V/ragas.json
done
$PY verify/neo4j-bm25-compare/ragas-ab/compare.py
```

실측 시간: 실행당 11.5 ~ 14.1분, 세 벌 합쳐 약 44분임. 로컬 평가자(Ollama)가 떠 있어야 함.

판정 규칙은 `compare.py`에 넣어 둠 — 흔들림 = max(|기준2 − 기준1|, 평가자 반복 흔들림)이고,  
|A − 기준1|이 그보다 클 때만 개선 또는 악화로 적음. 로컬 평가자는 반복 3회가 같은 값이라  
흔들림이 0으로 나오기 쉬우므로, 그때는 "차이 있음(흔들림 0 — 확인 필요)"으로 표시함.

## 남은 한 걸음 — 기준을 더 돌려 흔들림 폭 확정

> 2026-10-19 사용자 결정으로 이 시험은 여기서 마무리함. 아래 추가 실행(기준 3회 더)은 **하지 않았음**.  
> 저장소 구성은 1-b 분리형(검색 엔진) 쪽으로 검토가 옮겨 가, 3번(Neo4j 전부 통합형) 판단용인 이 추가 실행이 꼭 필요하지 않음.  
> 판정은 "차이가 있다고 단정할 수 없음"으로 둠.

지금 흔들림은 기준 **2회**에서 잡은 값임. 그런데 Q01, Q07, Q15처럼 **근거가 완전히 같은데도**
답변 문장이 달라져 Faithfulness가 0.50씩 움직이는 문항이 있음. 기준 2회가 우연히 같은 값을 냈을 뿐이라
흔들림 폭이 실제보다 작게 잡혔을 가능성이 큼.

```bash
# 기준을 3회 더 돌려(base3 ~ base5) Faithfulness 흔들림 폭을 다시 잡음
PY=retriever/vector-retriever/.venv/Scripts/python
for V in base3 base4 base5; do
  $PY verify/neo4j-bm25-compare/ragas-ab/run_variant.py --bm25 baseline --label $V \
      --out verify/neo4j-bm25-compare/ragas-ab/runs/$V/retriever.json
done
```

기준 5회의 Faithfulness 최댓값과 최솟값 폭이 0.114보다 넓으면 **A는 차이 없음**으로 판정이 바뀜.
좁으면 A가 실제로 답변 문장을 바꾸는 효과가 있다는 뜻이므로 더 파고들어야 함.
예상 시간: 검색과 답변 생성 2분씩, RAGAS 채점 12분씩 해서 약 45분임.

## 되돌리기 확인

| 항목 | 결과 |
|------|------|
| 사용 중 세대 포인터 | 세 실행 모두 실행 전후 내용이 **같음**(`run_variant.py`가 실행마다 확인해 출력) |
| 재색인 | 하지 않음 |
| Neo4j 전용 라벨 `RagasAbChunk` | 실행 뒤 0건 |
| Neo4j 전용 인덱스 `ragasab_tokens_ws` | 실행 뒤 0건 |
| 기존 Neo4j 노드 | `__KGBuilder__` 729건 그대로 — 건드리지 않음 |
| 기존 코드 | `indexer/`와 `retriever/`와 `ragas/`에 변경 없음(`git status`로 확인) |
| Ollama | 처음엔 꺼져 있었음. 상태 확인용 `ollama list`가 Ollama 앱과 서버를 띄움(2026-10-19 10:45:08, 의도치 않음). 모델은 내려받지 않음 |

## 한계

1. **흔들림 폭을 기준 2회로만 잡음.** 근거가 같은데도 Faithfulness가 0.50씩 움직이는 문항이 있어
   2회로는 폭이 모자람. 「남은 한 걸음」대로 기준을 5회까지 늘려야 판정을 확정할 수 있음
2. **답변 생성 LLM이 자주 시간을 넘김.** 22문항 세 실행에서 시간 초과가 1건, 2건, 3건 났고,
   채점 대상 문항 수가 14, 14, 12로 달라짐. 그래서 공통 11문항 표를 따로 둠
3. **평가자의 알려진 버릇을 그대로 안고 감.** 한 문장에 든 조건을 주장 여러 개로 쪼갠 뒤 감점함
   (`ragas/README.md` 9장 3번). Q01이 그 경우이며 사람 판정으로 보정하지 않았음
4. **판정 이유 칸이 비어 있음.** ragas 0.4.3이 `MetricResult.reason`을 채우지 않아
   점수가 왜 그렇게 나왔는지는 답변 문장을 사람이 직접 읽어 가려냈음
5. **22문항은 작음.** 공통 비교는 11문항까지 줄어듦. 문항 1건이 비율을 크게 움직이므로
   직전 시험의 42문항 순위 비교와 함께 봐야 함
6. **A 방식의 점수 공식 차이는 그대로임.** Neo4j는 k1을 1.2로 고정하고 문서 길이를 1바이트로 뭉개 저장함
   (`../README.md` 「차이의 원인」). 문서가 218건보다 많아지면 영향이 달라질 수 있음
7. **보정안(Neo4j는 후보만, 앱이 재채점)은 이 시험에서 재지 않음.** A 방식만 견줬음
