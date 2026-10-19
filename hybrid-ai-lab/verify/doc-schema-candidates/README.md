# 문서 종류별 표본으로 스키마 후보 뽑기 시험(2026-10-18)  

문서(약관, 혜택 안내, 상담 이력)에서 표본을 뽑아 neo4j-graphrag `SchemaFromTextExtractor`로 노드 타입과 관계 후보를 뽑고,  
제안한 표본 규칙(시작 수, 연속 3건 새 타입 0개면 멈춤, 층 상한 30건)이 실제로 어떻게 움직이는지 확인함.  
기존 indexer, retriever 코드는 고치지 않고, 벡터 인덱스의 청크 파일을 읽기만 함.  

## 실행  

```bash
../neo4j-vector-search/.venv/Scripts/python sample_schema.py
../neo4j-vector-search/.venv/Scripts/python analyze.py
```

- LLM: Groq `openai/gpt-oss-120b`(JSON 모드, `include_reasoning: false`, `reasoning_effort: medium`, temperature 0)  
- 키: `hybrid-ai-lab/.env` 또는 프로젝트 루트 `.env`의 `GROQ_API_KEY`(값은 출력하지 않음)  
- 입력: `indexer/vector-bm25/data/artifacts/ch2-20261003-001/prepared-chunks.json`(정제와 가명처리 뒤 청크 218개)  

## 결과(무작위 시드 20261018)  

| 문서 | 층(전체 → 본 건수) | 멈춘 이유 | 노드 타입 후보 | 관계 후보 | 핵심 타입이 모두 나온 시점 |
|---|---|---|---:|---:|---|
| 약관 | 10 → 10 | 모두 봄 | 42 | 78 | 7번째 건 |
| 상담 이력 | 48 → 30 | 상한 30건 | 45 | 115 | 5번째 건 |
| 혜택 안내 | 공통 4 → 4, 참고 카드 7 → 7, 카드 개요 64 → 27, 혜택 상세 85 → 30 | 카드 개요만 멈춤 규칙, 혜택 상세는 상한 | 54 | 83 | 15번째 건 |

- 핵심 타입: 성공 호출의 20% 이상에서 제안된 이름(`output/saturation.md`)  
- 호출 108건(실패 1건), 토큰 427,773개  
- 실패 1건: LLM이 같은 속성에 EXISTENCE와 KEY 제약을 함께 넣어 GraphSchema 검증이 거부함  

## 알게 된 것  

- 이름 그대로 세면 포화가 안 옴: 1건에서만 나온 이름이 노드 타입의 43 ~ 67%, 관계의 67 ~ 90%임.  
  LLM이 같은 뜻을 다른 이름으로 계속 만듦(예: Card, CardProduct, CreditCard / HAS_BENEFIT, CARD_HAS_BENEFIT, OFFERS_BENEFIT)  
- 자주 나오는 핵심 타입은 일찍 다 나옴(5 ~ 15번째 건). 시작 수 10건이면 핵심은 대부분 잡힘  
- 그래서 멈춤 규칙은 이름 그대로가 아니라 "같은 뜻 합친 뒤" 또는 "2건 이상에서 나온 이름"으로 세야 함  

## 비교: examples로 이어 뽑기(2026-10-18)  

- 같은 문서 종류에서 앞서 나온 이름(빈도 상위 노드 타입 25, 관계 30, 패턴 15)을 다음 호출의 `examples`로 넘김  
  (`sample_schema.py --examples`, 출력 `output-examples/`). 같은 시드와 순서, 멈춤 규칙 없이 층 상한까지 봄  
- `compare.py`: 층마다 두 실행 중 적게 본 건수까지만 비교(`output-examples/compare.md`)  

| 문서 | 노드 타입 이름 수 A → B | 1건에서만 나온 노드 타입 | 관계 이름 수 A → B | 1건에서만 나온 관계 | 핵심 타입 겹침 |
|---|---|---|---|---|---:|
| 약관(10건) | 42 → 30 | 67% → 47% | 78 → 52 | 90% → 67% | 0.38 |
| 상담(30건) | 45 → 14 | 58% → 7% | 115 → 26 | 76% → 38% | 0.22 |
| 혜택(68건) | 54 → 13 | 43% → 8% | 83 → 17 | 67% → 18% | 0.71 |

- 멈춤 규칙: A(따로)는 이름 그대로 세면 상담과 혜택 상세가 상한까지 감. B(examples)는 상담 13건(이름 그대로) 또는  
  20건(2건 이상 나온 이름만), 혜택 층들은 10 ~ 14건에서 멈춤  
- 굳어짐 점검(`lockin_check.py`, 낱말 사전 기반 대략값): Channel 50건 중 4건, ContactPreference 15건 중 1건이  
  글에 근거 낱말 없이 나옴. Company는 낱말 사전이 약해 판단 보류  
- 실패: A 1건, B 4건(대부분 같은 속성에 UNIQUENESS와 KEY 또는 EXISTENCE와 KEY를 함께 넣어 GraphSchema가 거부)  
- 토큰: A 427,773(108건), B 482,530(111건)  

## 상담 원문 v3로 다시 뽑기(2026-10-18)  

- 상담 원문을 v3로 고침(불만 원인, 제안, 수용 또는 거절과 이유, 보류 조건을 문장으로 넣음, `docs/D3_README.md` 「v3 변경」)  
- 인덱서 전체 재실행(`run_indexer.py --thread-id d3v3-20261018`, 세대 `gen-d3v3-20261018-d47a6d6e`, 상담 48청크 새 임베딩)  
- `sample_schema.py --examples consult_log --chunks=…/d3v3-20261018/prepared-chunks.json --out=output-examples-v3`,  
  비교는 `compare_v3.py`(`output-examples-v3/compare.md`). 상담ID 순서는 v2와 같음  

| 항목 | v2 원문 | v3 원문 |
|---|---|---|
| 성공 호출 | 29 / 30 | 30 / 30 |
| 노드 타입 이름, 관계 이름 | 14, 26 | 38, 43 |
| 불만 원인, 제안, 수용과 거절, 보류(역량 질문 1 ~ 4)에 해당하는 노드 타입이나 관계 | 없음 | Response 1건뿐 |
| 이전 상담 연결(역량 질문 5)에 해당하는 상담 → 상담 관계 | 없음 | 없음 |
| 그 개념을 담은 속성 | Request.reason 2건 | SupportRequest.reason 1건 |

- 결론: 글에 문장을 넣는 것만으로는 추출기가 그 개념을 타입으로 뽑지 않음. 기본 프롬프트가 "글에 나오는 개체"를 찾게 되어 있어  
  고객, 거래, 요청 같은 명사 쪽으로 모이고, 대화 행위(불만, 제안, 응답)는 타입이 되지 않음  
## 역량 질문 넣어 뽑기(2026-10-18)  

- `sample_schema.py --examples --cq consult_log --chunks=… --out=output-cq-v2|output-cq-v3`  
- 역량 질문 5개(`COMPETENCY_QUESTIONS`): 불만 원인, 상담사 제안, 수용과 거절과 보류와 이유, 재검토 조건, 이전 상담 연결.  
  답이 될 타입 이름은 일부러 적지 않음  
- 비교: `compare_v3.py output-examples output-examples-v3 output-cq-v2 output-cq-v3` → `output-cq-v3/compare.md`  

| 항목 | examples, v2 | examples, v3 | 역량 질문, v2 | 역량 질문, v3 |
|---|---|---|---|---|
| 노드 타입, 관계 이름 수 | 14, 26 | 38, 43 | 7, 8 | 10, 10 |
| 불만 원인(질문 1) | 없음 | 없음 | 없음 | `Issue` 26건, `HAS_ISSUE` 26건 |
| 제안, 응답, 재검토 조건(질문 2 ~ 4) | 없음 | `Response` 1건 | 없음 | 없음 |
| 이전 상담 연결(질문 5) | 없음 | 없음 | `(Consultation)-[FOLLOWS]->(Consultation)` 21건 | `FOLLOW_UP` 18건 |

- 알게 된 것  
  - 역량 질문을 넣으면 이름이 크게 모임(노드 타입 7 ~ 10개). 글에 신호가 분명한 질문(이전 상담 연결)은 v2에서도 타입이 됨  
  - 불만 원인은 글(v3)과 질문이 함께 있어야 타입이 됨. 어느 하나만으로는 안 나옴  
  - 제안, 응답, 재검토 조건은 둘 다 있어도 안 나옴. 앞서 나온 이름을 다시 쓰라는 examples 안내가 첫 몇 건의 이름을  
    굳혀서 새 타입이 들어설 자리가 줄었을 가능성이 있음(시험하지 않은 가설)  
- 실패: 역량 질문 v2 1건(같은 속성에 EXISTENCE와 KEY), v3 0건. 토큰: v2 125,772, v3 131,519  

## 역량 질문만 넣기(이름 다시 쓰기 안내 없음, 2026-10-18)  

- `sample_schema.py --cq --no-stop consult_log --chunks=…/d3v3-20261018/… --out=output-cqonly-v3`(v3 원문만)  
  토큰 122,540, 실패 0  
- 결과: 노드 타입 53개, 관계 106개로 다시 흩어짐. 대신 역량 질문 5개에 답할 이름이 모두 나옴  
  (질문 1 ~ 4는 드물게, 질문 5는 상담 → 상담 연결 패턴이 30건 중 15건)  

| 역량 질문 | 나온 이름(30건 중 건수) |
|---|---|
| 1. 불만 원인 | Issue 5, HAS_ISSUE 3, Complaint 2(속성 reason 1), CUSTOMER_HAS_COMPLAINT 1 |
| 2. 제안 | Proposal 2, SUGGESTS 2, MAKES_PROPOSAL 1, SUGGESTS_ALTERNATIVE 1 |
| 3. 수용과 거절 | REJECTS_CHANGE 1. `Response` 2건은 고객 응답이 아니라 상담사가 요청에 답한 것이라 해당 안 됨 |
| 4. 재검토 조건 | Condition 2, HAS_CONDITION 1 |
| 5. 이전 상담 연결 | (Consultation)-[FOLLOWS] 3, (Conversation)-[FOLLOWS] 2, PREVIOUS_SESSION 1, CONNECTS_TO 1 등(이름이 흩어짐) |

방법별로 역량 질문 5개 중 답할 이름이 나온 수(상담 30건, 같은 순서)  

| 방법 | 노드 타입 이름 수 | 역량 질문 5개 중 |
|---|---:|---:|
| 1건씩 따로 뽑기(`output/`) | 45 | 0 / 5 |
| 이름 다시 쓰기(`output-examples/`) | 14 | 0 / 5 |
| 원문 보강 + 이름 다시 쓰기(`output-examples-v3/`) | 38 | 0 / 5 |
| 원문 보강 + 역량 질문 + 이름 다시 쓰기(`output-cq-v3/`) | 10 | 2 / 5(질문 1, 5) |
| 원문 보강 + 역량 질문만(`output-cqonly-v3/`) | 53 | 5 / 5 |

- 질문 5의 판정: 상담 계열 노드(Consultation, Record, Conversation, Session) 사이 같은 라벨 연결이나 이름에  
  FOLLOW, CONTINU, PREVIOUS가 든 관계. 1건씩 따로 뽑기의 `(Request)-[REQUEST_FOLLOWS]->(Request)` 1건은 상담 연결로 보지 않음  
- 원문에는 "C-…과 이어지는 기록으로 남겨 주세요"가 처음부터 있었는데도 질문 없이는 타입이 되지 않음(질문을 넣은 두 방법에서만 나옴)  

- 해석  
  - 이름 다시 쓰기 안내가 새 개념을 막았다는 가설은 일부 맞음: 빼니까 제안, 조건 같은 이름이 처음 나옴  
  - 그러나 질문 1 ~ 4는 2 ~ 5건뿐이라 "20% 이상 나온 이름" 같은 빈도 기준으로 거르면 전부 잡음으로 버려짐  
  - 고객의 수용과 거절은 거의 잡히지 않음(1건)  
  - 실무 절차: 역량 질문만으로 넓게 뽑아 드문 이름까지 사람이 역량 질문에 비춰 살리고 합친 뒤(예: Issue와 Complaint →  
    하나), 확정한 뼈대를 examples로 넣어 다시 뽑는 2단계가 맞아 보임  

## 뼈대 추천(상담 이력, 사람 확정 전, 2026-10-18)  

- 입력: `output-cqonly-v3`(역량 질문만, 노드 타입 53, 관계 106). 결과: `skeleton_consult_draft.json`(GraphSchema 검증 통과)  
- 3단계 확정 규칙을 역량 질문 기준으로 적용함  
  1. 같은 뜻 합치기: Consultation, Conversation, Session, Record → `Consultation` / Issue, Complaint → `Complaint` /  
     Proposal, SUGGESTS, MAKES_PROPOSAL, SUGGESTS_ALTERNATIVE → `Proposal` / Condition → `ReconsiderCondition` /  
     FOLLOWS, CONTINUES_FROM, PREVIOUS_SESSION, RECORD_FOLLOWS → `FOLLOWS`  
  2. 역량 질문에 안 쓰는 것 빼기: Request, Menu, Address, Order, ContactPreference 등(필요하면 Consultation 속성 topic으로)  
  3. 원천이 따로 있는 것 빼기: Transaction, TransactionSummary(RDB 집계), Customer, Card(RDB 키로 이음. 이름, 이메일, 생년월일  
     속성 제안은 가명처리 대상이라 버림), Agent, Counselor(메타데이터 agent_pseudo_id로 충분)  
- 사람이 보탠 것(LLM 근거가 약하거나 없음): `Proposal.decision`과 `decision_reason`(근거 REJECTS_CHANGE 1건),  
  `(Proposal)-[ADDRESSES]->(Complaint)`(근거 ADDRESSES 3건), `RECONSIDER_WHEN`  

## 뼈대 채우기 시험(상담 48건, 2026-10-18)  

- `fill_skeleton.py`: 뼈대를 스키마로 주고 `LLMEntityRelationExtractor` + `GraphPruning`으로 실제 노드와 관계를 뽑아  
  강사용 대조표 정답과 비교(`output-fill-v3/fill_report.md`). 입력 글 앞에 메타데이터 머리줄([상담ID], 상담일, 채널, 주제)을 붙임  
- 처음 실행에서 "LLM response has improper format"으로 실패 → 원인: Neo4jNode, Neo4jRelationship이 정해진 칸 밖 키를  
  거부(extra="forbid")하고 id를 글자로 요구함. 응답을 다듬는 `SanitizingLLM`과 최대 2회 재시도를 넣어 실패 0건(재시도 2건)  
- 토큰 159,905, 가지치기로 지운 뼈대 밖 노드 0개  

| 타입 | 정답 있는 기록에서 뽑음 | 정답 없는 기록에서 잘못 뽑음 |
|---|---|---|
| Complaint(불만) | 24 / 24 | 22 / 24 |
| Proposal(제안) | 47 / 48 | 정답 없는 기록 없음 |
| Proposal.decision(응답) | 너그럽게 42 / 48, 엄격하게 31 / 48 | 해당 없음 |
| ReconsiderCondition(재검토 조건) | 17 / 19 | 6 / 29 |
| FOLLOWS(이전 상담 연결) | 34 / 36 | 0 / 12 |

- 응답 너그럽게: 뽑은 제안 중 하나라도 정답 응답과 같음. 엄격하게: 뽑은 응답이 정답 하나뿐(제안을 여러 개 뽑아 "안내해 드릴까요"  
  같은 작은 제안을 수용으로 붙이는 경우가 많음)  
- 불만 오탐: 일반형 고객의 문의 목적이나 사정("이사", "영수증 필요", "의심 문자 진위 확인")을 Complaint로 뽑음 →  
  뼈대의 Complaint 설명을 좁히거나(분명히 불만이나 불편을 말한 경우만), 문의 목적을 받을 타입을 따로 두는 수정이 필요  

## 뼈대 v2(설명 좁힘) 채우기 시험(2026-10-18)  

- `fill_skeleton.py --skeleton=skeleton_consult_v2.json --out=output-fill-v3b`, 토큰 155,684, 실패 0  
- 바꾼 것: Complaint(분명한 불만이나 불편만, 문의 목적과 개인 사정 제외), Proposal(받아들이거나 거절할 수 있는 구체적 대안만,  
  절차 안내 제외, 보통 1개), ReconsiderCondition(분명히 말한 조건만), decision 속성 설명(수용, 거절, 보류 중 하나)  

| 지표 | 뼈대 v1 | 뼈대 v2 |
|---|---|---|
| 불만: 정답 있는 기록에서 뽑음 / 정답 없는 기록에서 잘못 뽑음 | 24/24, 22/24 | 24/24, 4/24 |
| 제안 노드 수 합(48건) | 87 | 56 |
| 응답 엄격 일치 / 너그러운 일치 | 31/48, 42/48 | 37/48, 41/48 |
| 재검토 조건: 뽑음 / 잘못 뽑음 | 17/19, 6/29 | 16/19, 0/29 |
| 이전 상담 연결: 뽑음 / 잘못 뽑음 | 34/36, 0/12 | 36/36, 0/12 |

- 남은 불만 오탐 4건은 "종이 영수증이 없어 불편", "우편은 늦게 와서 한참 기다려야 했어요"처럼 고객이 불편을 실제로 말한 경우가 많음  
  (정답표는 일반형 고객이라 불만 없음으로 둠). 정답 기준을 다시 볼 대상  

### 본 문서와 안 본 문서로 나눠 보기(뼈대 v2)  

이 시험은 정답표가 48건 모두에 있어 전체로 했음. 그런데 48건에는 스키마 후보를 뽑을 때(`output-cqonly-v3`) 본 30건이 들어 있어,  
본 문서로 시험하면 결과가 좋게 나올 수 있음. 그래서 나눠 셈.  

| 지표 | ②에서 본 30건 | ②에서 안 본 18건 | 전체 48건 |
|---|---|---|---|
| 불만: 뽑음 / 잘못 뽑음 | 15/15, 1/15 | 9/9, 3/9 | 24/24, 4/24 |
| 제안 뽑음 | 29/30 | 18/18 | 47/48 |
| 응답 엄격 일치 | 22/30(73%) | 15/18(83%) | 37/48 |
| 재검토 조건: 뽑음 / 잘못 뽑음 | 10/13, 0/17 | 6/6, 0/12 | 16/19, 0/29 |
| 이전 상담 연결: 뽑음 / 잘못 뽑음 | 22/22, 0/8 | 14/14, 0/4 | 36/36, 0/12 |

- 대부분 지표는 안 본 문서에서도 비슷하거나 더 좋음. 불만 오탐만 안 본 문서에서 3 / 9(33%)로 본 문서(1 / 15, 7%)보다 높음  
  → 건수가 작아 단정하기 어렵지만 Complaint 설명을 더 좁힐 여지  

### 실무 권고: 시험은 표본으로  

- 정답(기대 답)은 사람이 붙여야 하므로 표본에만 있고, ③과 ④를 되풀이할 때마다 전체를 돌리면 비용이 큼(이 시험도 1회 약 15만 토큰)  
- 시험 표본은 ②의 표본과 겹치지 않게 따로 뽑고, 묶음별로 고르게, 답이 없어야 하는 문서를 일부러 넣음  
- 건수는 원하는 정확도로 정함: 비율을 95% 신뢰로 ±10%p 안에서 알려면 지표당 약 96건, ±15%p면 약 43건  
  (`n = 1.96² × p(1−p) / 오차²`, p = 0.5일 때 가장 큼). 이 시험의 불만 없는 24건은 약 ±20%p 수준  
- 시작은 문서 종류마다 30 ~ 50건에 기대 답을 붙이고, 지표가 기준 근처에서 오락가락하면 늘림  
- 전체 청크는 ⑤ 고정 뒤 인덱싱이 추출하고, 결과 일부를 무작위로 골라 사람이 점검함(가지치기 통계 함께)  

## 약관과 혜택을 역량 질문만으로 넓게 뽑기(2026-10-18)  

- `sample_schema.py --cq --no-stop regulation benefit_guide --chunks=…/d3v3-20261018/… --out=output-cqonly-docs`,  
  토큰 345,322, 실패 5(모두 혜택, LLM이 같은 속성에 UNIQUENESS와 KEY 또는 EXISTENCE와 KEY)  
- 역량 질문(`COMPETENCY_QUESTIONS`): 약관 5개(면제 조건, 해지와 철회와 항변 절차와 기한, 수수료 부과와 공제와 반환,  
  조항 참조와 예외, 회원과 카드사 의무), 혜택 5개(혜택, 조건, 한도와 제외, 브랜드별 연회비, 비슷한 카드)  
- 비교: `compare_docs.py` → `output-cqonly-docs/compare.md`(역량 질문 없이 뽑은 `output/`과 같은 건수로)  

| 문서 | 이름 수(노드, 관계) A → CQ | 질문으로 새로 늘어난 이름 | 질문에 답할 이름이 안 나온 것 |
|---|---|---|---|
| 약관(10건) | 42, 78 → 38, 71 | Exemption 1, EXEMPT_FROM 1, REFERS_TO 2, Chapter와 Article 2 | 기한, 절차 단계, 회원과 카드사 의무 |
| 혜택(68건) | 54, 83 → 48, 82 | Exclusion 3 → 25(핵심), Brand 4 → 10, HAS_EXCLUSION 9 | 비슷한 카드(청크 하나 안에 비교가 없음) |

- 해석: 혜택은 질문 3(제외 대상)이 바로 핵심 타입이 됨. 약관은 청크마다 조항이 달라 이름이 계속 흩어지고(1건에서만 나온 이름 76%),  
  조항 규칙(조건, 기한, 의무)의 구조는 거의 안 나옴 → 약관은 조항 구조 뼈대를 사람이 먼저 그리는 쪽이 맞아 보임.  
  "비슷한 카드"처럼 여러 문서에 걸친 관계는 청크 단위 추출로는 안 나오며 검색 단계나 따로 계산할 대상임  

## 파일  

| 파일 | 내용 |
|---|---|
| `sample_schema.py` | 표본 뽑기, 1건씩 추출, 멈춤 규칙 적용 |
| `analyze.py` | 포화 모양 분석(핵심 타입, 처음 나온 시점, 건별 새 이름 수) |
| `output/calls.jsonl` | 호출마다 추출 결과(노드 타입, 속성, 관계, 패턴, 새 이름) |
| `output/candidates_{문서종류}.json` | 문서 종류별 후보와 제안한 청크 수 |
| `output/summary.md`, `output/saturation.md` | 요약 |
| `compare.py`, `lockin_check.py` | 두 방식 비교, examples 굳어짐 대략 점검 |
| `output-examples/` | examples 방식 결과와 `compare.md` |
