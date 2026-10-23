# 문서 스키마 설계 v2 실행 결과(2026-10-23 ~ 24)

> 프롬프트: `hybrid-ai-lab/prompts/design-kg-schema-doc.md`(질문 범위, 공통 개념, 참조 노드, 연결 검사, 승인 검토 파일 규칙을 넣은 판)

> 승인: 1, 2, 3, 5, 7, 8단계를 사용자가 검토 파일로 직접 승인함(기록은 `decisions.json`, 검토 파일은 `review/`)

## 1. 한눈에 보기

| 문서 종류 | 9단계 | 8단계 판정 | 미달 질문 |
|---|---|---|---|
| 혜택 안내 | 확정(통과) | 4, 5라운드 모두 6/6 통과 | 없음 |
| 약관 | 확정(미달 사유 기록) | 세 번 평균 5/6 통과 | R3 기한(평균 뽑음 75%, 흔들림) |
| 상담 기록 | 확정(미달 사유 기록) | 세 번 평균 5/9 통과 | C1, X1, A1(같은 상담 2건에서 매번 불만을 잘못 뽑음), X2(카드 뽑음 78%) |

- 연결 검사(공통 노드를 거쳐 문서 종류끼리 이어지는지)는 1 ~ 5라운드와 측정 2번 모두 통과함
- 최종 파일: `{doc}/graph_schema.json`, `{doc}/approval.json`, `shared_concepts.json`
- LLM: Groq `openai/gpt-oss-120b`. 4 ~ 8단계 토큰 합계 약 270만 개(후보 약 37만, 기대 답 초안, 8단계 약 205만, 측정 약 46만)

## 2. 이번 판에서 새로 생긴 것

| 구분 | 내용 |
|---|---|
| 역량 질문 범위 | 문서 하나 15개에 여러 문서 종류 범위(X1, X2)와 전체 모음 범위(A1, A2)를 더함(Q23 ~ Q25 근거) |
| 공통 노드 | Topic(주제 15개 목록), MerchantCategory(업종 18개 목록). 약관, 혜택 안내, 상담 기록을 이음 |
| 참조 노드 | Product(정형 스키마의 Product와 같은 라벨, product_id) |
| 메타데이터 노드 | CustomerSegment(고객군), PseudoMember(가명 회원), 상담 주제, 앞 상담 연결(FOLLOWS)은 코드가 메타데이터로 채움 |
| 추출 제외 | 혜택 안내의 설계 참고 출처, 표지, 카드 목록 청크 |
| 원천 데이터 | 상담 원문을 v4로 고쳐 상담마다 회원 보유 카드 이름을 넣음(`docs/D3_README.md` 「v4 변경」) |

## 3. 인덱싱에 쓰기 전에 남은 일

1. **인덱서 코드 규칙 구현:** 공통 노드 이름 맞추기, 목록 밖 이름 지우기, 정형 상품 ID 찾기, 메타데이터 노드와 앞 상담 연결,
   추출 제외 청크, 구조용 관계(약관 HAS_CLAUSE) 표시. GraphRAG v0에는 아직 없음. 각 `approval.json`의 `indexer_code_rules`와 `shared_concepts.json`에 정리함
2. **상담 기록의 LLM 추출 스키마:** `consult_log/graph_schema.json`에는 메타데이터 노드까지 들어 있음. LLM에는 이 노드와 관계를 뺀 스키마를 넘겨야 함
   (시험은 `tools/fill_test_v2.py`의 `extraction_schema`로 그렇게 함)
3. **스키마 파일 위치:** 지금 인덱서는 `indexer/graphrag/schema/doc`의 이전 판(2026-10-18)을 읽음. 이번 판을 쓰려면 옮겨야 하고, 옮기면 전체 다시 추출이 필요함
4. **상담 원문 v4 다시 인덱싱:** 검색엔진, 벡터 색인, GraphRAG 그래프는 아직 v3 원문 기준임

## 4. 알아 둘 한계

- 시험용 표본이 작음(상담 기록 18건). 한 건이 비율을 11 ~ 25% 움직임
- 같은 설명으로도 추출 결과가 돌릴 때마다 달라, 약관 R3은 세 번에 58%, 83%, 83%였음
- 8단계에서 기대 답 오류를 라운드마다 찾아 고침(2라운드 이후 87칸, 약관 R2 ~ R4는 사람 판단(AI)으로 다시 씀). 근거는 모두 기록했으나 사람이 한 번 더 확인하는 것이 좋음
- 프롬프트 완료조건 중 "fill_report.md에 연결 검사 결과가 있음"은 연결 검사를 문서 종류를 합쳐 하므로 `output/connect_report.md`에 따로 둠

## 5. 파일 안내

| 파일 | 내용 |
|---|---|
| `review/step1.md` ~ `review/step7.md` | 1 ~ 7단계 승인 검토 파일 |
| `review/step8.md`, `step8_r2_prep.md`, `step8_round2.md` ~ `step8_round4.md`, `step8_final.md`, `step8_measure.md` | 8단계 라운드별 결과, 2라운드 준비, 최종, 측정 반복 |
| `decisions.json` | 단계별 승인과 결정(판정자, 날짜, 검토 파일 해시, 사용자 답 원문) |
| `competency_questions.md`, `.json` | 역량 질문 19개 |
| `sample_plan.json` | 묶음과 표본(상담 청크 ID는 v4 원문 기준으로 바꿈) |
| `shared_concepts.json` | 공통 노드, 참조 노드, 메타데이터 노드, 추출 제외, 목록 강제 규칙 |
| `{doc}/schema_spec.json`, `{doc}/output/schema_draft.json` | 최종 명세와 초안. 라운드별 판은 `schema_spec.r1.json` ~ `r4.json` |
| `{doc}/expected_answers.json` | 최종 기대 답. 판별 파일 `expected_answers.r1.json` ~ `r4.json` |
| `{doc}/output/fill_report_round{1 ~ 5, 5m1, 5m2}.md` | 채우기 시험 보고서 |
| `output/measure_avg.json` | 약관과 상담 기록 세 번 평균 |
| `tools/` | 실행 스크립트(후보, 초안, 기대 답, 시험, 라운드별 고침, 원문 카드 이름 넣기) |
