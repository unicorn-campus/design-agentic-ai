# KG 구축 K4 적재 — PPT 스크립트

- 산출물: `temp/k4-load/K4적재.pptx` (2장: 무엇을 어떻게 쓰나, 코드와 조회 결과)
- 작성: 클로니, 2026-10-19
- 위치: K2 추출과 K3 가지치기(준비 구간) 다음. KG 구축 반영 구간(K4 ~ K6)의 첫 단계
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음(근거는 이 파일에만)
- 용어: "청크"는 검색용 청크만, LLM에 넣은 조각은 "추출 단위", Neo4j의 라벨 Chunk 노드는 "청크 노드"(검색용 청크와 1대1)로 씀. 추출 단위는 그래프에 남기지 않음  
- 2026-10-23 구조 변경: 추출 단위 노드(parent_chunk_ids)를 없애고 청크 노드를 검색용 청크와 1대1로 바꿈.  
  준비 결과의 필드 이름도 `chunk_ids`로 바꿈. 아래 표는 변경 뒤 v0 재실행(`sample-005`, `sample-006`) 실측임
- 라이브러리 내부 임시 ID(`__tmp_internal_id`)는 수강생이 알 필요가 없어 쓰지 않음(K2 장표 때 사용자 결정)

## 근거(스크립트에만 기록)

모든 코드와 수치는 `hybrid-ai-lab/indexer/graphrag/v0`(이하 v0) 기준임.

| 내용 | 근거 |
|------|------|
| 입력: 준비 결과의 chunks(검색용 청크마다 chunk_id, doc_id, doc_type, text)와 units(단위마다 unit_id, doc_id, doc_type, chunk_ids, text, text_hash, graph). graph가 없는 단위(추출 실패)는 건너뜀 | v0 `kg_build.py` `apply`, `prepare` |
| 청크 노드: 라벨 Chunk, 검색용 청크마다 1개. 속성 generation, run_id, chunk_id, doc_id, doc_type, text | `kg_build.py` `apply` |
| 엔티티마다 generation, run_id 속성을 붙이고 단위의 chunk_ids에 든 청크마다 FROM_CHUNK 관계(엔티티 → 청크 노드)를 만듦(`dict.fromkeys`로 중복 제거). 추출 관계는 그대로 더함 | `kg_build.py` `apply` |
| 예시 단위 graph: 상담 C-20260501-003 단위의 노드 6(Consultation 2, Complaint 1, Proposal 2, ReconsiderCondition 1), 관계 5 | `data/generations/gen-sample-005-dbe57d45/kg_prepared.json` |
| 쓰기: `Neo4jWriter(driver).run(Neo4jGraph(nodes, relationships))` 한 번. 노드는 CREATE로 새로 만듦(합치지 않음). 관계는 `apoc.merge.relationship` | `kg_build.py`, neo4j-graphrag 1.22.0 `neo4j_queries.py` `upsert_node_query`, `upsert_relationship_query` |
| 라벨: 엔티티에는 `__Entity__`가 붙고 Chunk에는 붙지 않음(Chunk는 어휘 그래프 라벨). K6 벡터 인덱스와 K7 고아 찾기가 `__Entity__`를 씀 | `kg_writer.py` `_nodes_to_rows`, Neo4j 조회(Chunk 라벨: `__KGBuilder__`, `Chunk`) |
| 같은 값 노드는 K4에서 합치지 않고 K5에서 합침(K4가 합칠 값을 모아 넘김) | `kg_build.py` `apply`의 `merge_keys`, `k5_merge` |
| 전체 재색인 `sample-005`(`--full-reindex`, 2026-10-23) K4: 노드 120(청크 노드 10 포함), 관계 212 | 실행 로그 `[KG K4] 적재: 노드 120개(청크 노드 10개 포함), 관계 212개` |
| 나눠 보면 청크 노드 10 + 엔티티 110(K1 단위 24개, 실패 0), FROM_CHUNK 120(두 청크에 걸친 단위의 엔티티는 2개) + 추출 관계 92 | `kg_prepared.json`으로 계산(엔티티 110, 추출 관계 92, 단위별 노드 수 × 청크 수 합 120) |
| 예시 청크 노드(Neo4j 조회, `sample-005` 직후): chunk_id `D3_C-20260501-003_3415157c2811bedd_0000`, doc_type consult_log, run_id `sample-005@20261023135905`. 속성은 chunk_id, doc_id, doc_type, generation, run_id, text | Neo4j 조회(2026-10-23). 이 상담은 뒤의 증분 색인 `sample-006`에서 바뀌어 지금 활성 세대의 노드와는 다름 |
| 예시 질의(검색용 chunk_id → Chunk → FROM_CHUNK → 엔티티) 결과: Consultation 2, Proposal 2, Complaint 1, ReconsiderCondition 1 | Neo4j 조회(2026-10-23, `sample-005` 직후). v0 ④ 검증은 청크 노드 chunk_id 집합과 검색엔진 chunk_id 집합을 맞대어 봄(`chunk_node_ids`) |
| 약관 제16조와 제16조의2 엔티티는 두 청크 노드에 FROM_CHUNK. 같은 엔티티와 청크 사이 중복 관계 0개 | Neo4j 조회(2026-10-23) |
| 적재 뒤 `__tmp_internal_id`가 남은 노드 0개 | `k4_probe.py`(장표에는 쓰지 않음) |
| 증분 색인 반영 순서: K4 ~ K6 → S3 → K7. 옛 청크 노드는 K7에서 run_id가 다른 것만 지움(`sample-006`: 옛 청크 노드 5개, 고아 엔티티 33개) | `orchestrator.py` `run_incremental`, `kg_build.py` `cleanup`, 실행 로그 |

- 장표 2 코드는 `kg_build.py` `apply` 원문 발췌임. 줄 나눔만 장표 폭에 맞게 바꾸고, 생략은 `…`로 표시, 주석 일부는 장표용

---

## 장표 1. K4 적재: 무엇을 어떻게 쓰나

- 제목: KG 구축 K4 적재
- 리드문: 보관해 둔 추출 결과를 Neo4j에 쓰고, 검색용 청크와 같은 ID의 청크 노드로 이음

**도형 구성**

1. 왼쪽 「입력: kg_prepared.json의 단위 하나」 카드: unit_id, doc_id와 doc_type, chunk_ids(이 단위가 나온 검색용 청크 ID),
   text, graph(K2와 K3 결과: 노드 6, 관계 5)
2. 가운데 「K4가 하는 일」 번호 카드 3개와 아래 네이비 상자:
   - ① 청크 노드 만들기: 라벨 Chunk. 검색용 청크마다 1개
   - ② 모든 노드에 세대 표시: generation, run_id
   - ③ FROM_CHUNK로 잇기: 엔티티마다 단위가 나온 청크로 관계
   - 네이비 상자: Neo4jWriter로 한 번에 쓰기 (노드는 새로 만듦)
3. 오른쪽 「Neo4j에 남는 모양 (상담 C-20260501-003)」:
   - 위 줄 엔티티 4개: Consultation(C-20260501-003), Proposal(거절), Proposal(수용), ReconsiderCondition
   - 엔티티 사이 추출 관계는 엔티티 칸 사이 작은 글(HAS_PROPOSAL, RECONSIDER_WHEN)로 표시
   - 엔티티마다 아래로 FROM_CHUNK 화살표 → 청크 노드(Chunk) 상자: chunk_id, 검색용 청크와 1대1
   - 맨 아래 검색엔진 문서 상자(chunk_id) ↔ 점선: 「chunk_id가 같음」
4. 아래 규칙 카드 4개:
   - 쓰기만 하고 합치지 않음: 같은 값의 노드가 여러 개 생겨도 그대로 씀. 합치기는 K5
   - 세대마다 따로: 모든 노드에 generation. 세대끼리 섞이지 않음
   - 조항이 겹치면 청크 2개로 이음: 약관 제16조 엔티티는 두 청크 노드에 FROM_CHUNK
   - 증분 색인 때 옛 노드는 잠시 남김: 새 노드를 먼저 쓰고, 옛 청크 노드는 S3 뒤 K7에서 지움

**발표자 노트**

K4는 K2와 K3에서 파일로 보관해 둔 추출 결과를 Neo4j에 쓰는 단계입니다. 쓰기 전에 세 가지를 덧붙입니다. 첫째, 추출 단위마다
라벨이 Chunk인 청크 노드를 검색용 청크마다 하나 만듭니다. 청크 노드의 chunk_id는 검색엔진의 chunk_id와 같습니다.
추출 단위는 추출할 때만 쓰고 노드로 남기지 않습니다. 둘째, 모든 노드에 세대와 실행 표시를 붙입니다. 셋째, 뽑힌 엔티티마다 그
단위가 나온 청크 노드로 FROM_CHUNK 관계를 만듭니다. 조항이 두 청크에 걸치면 관계도 두 개입니다.
그래서 검색엔진이 청크 하나를 찾으면, 같은 chunk_id의 청크 노드를 바로 찾고, FROM_CHUNK를 거꾸로 따라가
그 청크에서 나온 엔티티를 모두 얻습니다.
K4는 쓰기만 합니다. 여러 단위에서 같은 약관 문서 노드가 나와도 그대로 여러 개 쓰고, 합치는 일은 다음 단계 K5가 합니다.

---

## 장표 2. K4 적재 코드와 조회 결과

- 제목: K4 적재 코드 (kg_build.py)
- 리드문: 단위가 나온 청크마다 청크 노드와 FROM_CHUNK를 덧붙여 모은 뒤, Neo4jWriter로 한 번에 씀
- 왼쪽 코드 상자 「apply()의 K4 부분 (kg_build.py 발췌)」: 굵게 Chunk 노드 만들기, FROM_CHUNK, Neo4jWriter 호출
- 오른쪽 위 코드 상자 「적재된 청크 노드 (Neo4j 조회, 일부)」: 예시 Chunk 노드 속성
- 오른쪽 가운데 코드 상자 「검색이 찾은 chunk_id로 엔티티 찾기 (조회 예시)」: Cypher 4줄과 결과 한 줄
- 오른쪽 아래 카드(파랑): v0 표본 전체 재색인 K4: 추출 단위 24개 → 노드 120 (청크 노드 10) / 관계 212 (FROM_CHUNK 120, 추출 92)

**발표자 노트**

코드는 단위를 하나씩 돌며 노드와 관계를 목록에 모읍니다. 추출 실패로 그래프가 없는 단위는 건너뜁니다. 단위가 나온
검색용 청크마다 청크 노드를 한 번만 만들고, 엔티티마다 세대와 실행 표시를 붙인 뒤 그 청크 노드들로 FROM_CHUNK 관계를 더합니다.
LLM이 뽑은 관계도 그대로 더합니다. 다 모으면 Neo4jWriter를 한 번 불러 씁니다. 오른쪽 가운데 질의가 검색 때 그래프로 넘어가는
길입니다. 검색엔진이 돌려준 chunk_id로 청크 노드를 바로 찾습니다. 예시 상담의 chunk_id로 조회하면 상담 노드 2개, 제안 2개,
불만 1개, 재검토 조건 1개가 나옵니다. v0 표본 전체 재색인에서는 추출 단위 24개에서 엔티티 110개가 나왔고,  
청크 노드 10개와 함께 노드 120개, 관계 212개를 한 번에 썼습니다.
