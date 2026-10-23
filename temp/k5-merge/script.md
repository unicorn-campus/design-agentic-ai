# KG 구축 K5 병합 — PPT 스크립트

- 산출물: `temp/k5-merge/K5병합.pptx` (3장: 병합의 원리, 무엇을 어떻게 합치나, 코드와 결과)
- 작성: 클로니, 2026-10-19
- 위치: K4 적재 다음. KG 구축 반영 구간(K4 ~ K6)의 두 번째 단계
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음(근거는 이 파일에만)
- 용어: "청크"는 검색용 청크만, Neo4j의 라벨 Chunk 노드는 "청크 노드"(검색용 청크와 1대1)  
- 2026-10-23 구조 변경: 추출 단위 노드를 없앰. 아래 표의 v0 수치는 변경 뒤 재실행(`sample-005`, `sample-006`) 실측임.  
  합쳐진 약관 문서 노드는 약관 청크 노드 2개로 이어짐(Neo4j 조회로 확인)

## 근거(스크립트에만 기록)

모든 코드와 수치는 `hybrid-ai-lab/indexer/graphrag/v0`(이하 v0) 기준임.

| 내용 | 근거 |
|------|------|
| 합치는 기준: 스키마의 UNIQUENESS 제약. 약관 TermsDocument.version, 혜택 안내 ProductGuide.product_id, 상담 기록 Consultation.record_id. 다른 라벨(Clause, Proposal 등)은 제약이 없어 합치지 않음 | `schema/doc/*/graph_schema.json`의 constraints, scratchpad `k5_probe.py` |
| 합칠 값은 K4가 모음: 이번에 쓴 엔티티 가운데 제약 라벨이고 값이 있는 것만 (라벨, 속성, 값)으로 | v0 `kg_build.py` `apply`의 `merge_keys` |
| 같은 세대에서 값이 같은 노드를 모아 2개 이상이면 `apoc.refactor.mergeNodes(ns, {properties: 'discard', mergeRels: true})` | `kg_build.py` `k5_merge` |
| `discard`: 첫 노드에 값이 있으면 그 값을 남기고, 없으면 목록의 첫 값을 씀. `mergeRels: true`: 같은 타입과 방향의 관계를 합침. 모든 관계는 남는 노드로 옮겨짐 | APOC 문서 `apoc.refactor.mergeNodes`(context7 `/websites/neo4j_apoc_current`, 2026-10-19 조회) |
| v0는 `collect(n)`에 정렬을 주지 않아 어느 노드가 첫 노드인지 정해져 있지 않음 | `k5_merge` 질의. v0 README 한계에 추가함 |
| 전체 재색인 `sample-005`: 병합 3묶음, K3 엔티티 110 → 병합 뒤 91(19개가 줄어듦) | 실행 로그, Neo4j 조회 `__Entity__` 91개 |
| 3묶음의 내용: TermsDocument version 1.2(16 → 1), ProductGuide D2-C021(4 → 1), Consultation C-20260302-002(2 → 1). 15 + 3 + 1 = 19로 위 수치와 맞음 | `gen-sample-005-dbe57d45/kg_prepared.json`에서 고유 속성 값별 노드 수를 셈(16, 4, 2) |
| 합쳐진 TermsDocument: version 1.2, effective_date 2027-01-15, supersedes 1.1, HAS_CLAUSE 16, FROM_CHUNK 청크 노드 2개 | Neo4j 조회(2026-10-23, `sample-005` 직후) |
| 합쳐진 Consultation C-20260302-002: 속성 5개(channel 영업점, consult_date 2026-03-02 등), FROM_CHUNK 2(Neo4j 조회, 2026-10-23), 들어오는 FOLLOWS 1. 앞 상담 참조로 생긴 노드는 record_id만 있었음(K2 예시 추출 결과) | `k5_probe2.py`, `kg_prepared.json` |
| 증분 색인 `sample-006`: 병합 3묶음, 새 엔티티 31(노드 35 중 청크 노드 4) → 남은 새 노드 26(임베딩 26). 새 노드 5개가 기존 노드와 합쳐짐 | 실행 로그, Neo4j 조회(run_id가 sample-006인 엔티티 26개) |
| 제약을 정하는 곳: 스키마 설계의 `schema_spec.json` `constraints` → `finalize.py`가 `graph_schema.json`으로 옮김. 약관 제약은 `{"type": "UNIQUENESS", "node_type": "TermsDocument", "property_name": "version"}` 하나 | `schema/doc/regulation/schema_spec.json`, `graph_schema.json` |
| 인덱싱 준비에서 `load_schemas()`가 `GraphSchema.from_file`로 읽음 | v0 `kg_build.py` `load_schemas` |
| K2: 스키마 전체(`schema.model_dump(exclude_none=True)`)가 추출 지시에 들어가 LLM에 제약도 보임. 단위마다 따로 불러 다른 단위 결과를 모름 | neo4j-graphrag 1.22.0 `entity_relation_extractor.py` `extract_for_chunk` |
| K3: 필수 속성 제약(EXISTENCE, KEY)만 보고 UNIQUENESS는 보지 않음 | `graph_pruning.py` `_check_required_properties` |
| Neo4j에는 제약을 걸지 않음(`SHOW CONSTRAINTS` 결과 없음). 걸려 있으면 K4의 CREATE가 같은 값 두 번째 노드에서 실패함 | scratchpad `show_constraints.py`(2026-10-19) |
| 약관 제16조 단위의 실제 노드 라벨: TermsDocument, Clause, Requirement, Handling. 제약과 비교하면 TermsDocument만 참 → `('TermsDocument', 'version', '1.2')`. 조항 16개 단위가 같은 키를 넣어도 `set`이라 1개 | `kg_prepared.json` 출력, `apply` 코드 |
| 2장(예시) 리드문은 사용자가 장표에서 직접 고친 문구(「노드를 합칠 때 사용 하는 …」, 띄어쓰기 포함 그대로 둠) | 2026-10-19 장표와 새 빌드 비교 |

- 장표 3 코드는 `kg_build.py` 원문 발췌임. 줄 나눔만 장표 폭에 맞게 바꿈(긴 `if` 조건은 괄호로 감싸 두 줄, 긴 질의 문자열은
  이어 붙는 조각으로 나눔), 생략은 `…`로 표시, 주석 일부는 장표용

---

## 장표 1. K5 병합의 원리: 스키마 제약이 병합 기준이 되기까지

- 사용자가 장표에서 이 장을 맨 앞으로 옮김

- 제목: K5 병합의 원리
- 리드문: 스키마 설계에서 정한 고유 속성 제약을 K4가 노드와 맞춰 보고 값을 모으면, K5가 그 값으로 같은 세대의 노드를 찾아 합침

**도형 구성**

1. 위 흐름 4칸(왼쪽에서 오른쪽, 화살표):
   - ① 스키마 설계 (정함): schema_spec.json에 정하고 graph_schema.json으로 확정 / 제약 JSON 3줄
   - ② 인덱싱 준비 (읽음): load_schemas()가 문서 유형별 제약을 읽음 / 약관: TermsDocument.version
   - ③ K4 적재 (모음): 노드 라벨이 제약 라벨과 같고 값이 있으면 모음 / merge_keys = {(TermsDocument, version, 1.2)}
   - ④ K5 병합 (합침): 같은 세대에서 값이 같은 노드를 찾아 2개 이상이면 mergeNodes / TermsDocument 16 → 1
2. 왼쪽 아래 표 「③의 비교: 약관 제16조 단위에서 뽑힌 노드」: n.label, c.node_type == n.label, 결과
   - TermsDocument: 참, 모음 (version 1.2) / Clause, Requirement, Handling: 거짓, 건너뜀
   - 표 아래 한 줄: 조항 16개 단위가 같은 키를 넣어도 set이라 키는 1개
3. 오른쪽 아래 「제약을 쓰는 곳과 안 쓰는 곳」 4줄:
   - K2 추출: LLM에 보이지만 단위끼리 서로 몰라 중복이 생김
   - K3 가지치기: 필수 속성만 보고 고유 속성은 안 봄
   - Neo4j: 제약을 걸지 않음. 걸면 K4 쓰기가 실패함
   - K4와 K5: 실제로 쓰는 곳 (모으고 합침)

**발표자 노트**

병합 기준은 인덱싱이 새로 정하는 것이 아니라 스키마 설계에서 이미 정해져 넘어옵니다. 약관 스키마에는 약관 문서 노드의 버전이
고유 속성이라는 제약이 하나 있습니다. 인덱싱은 이 제약을 읽어 두었다가, K4에서 노드를 쓸 때 노드마다 라벨을 제약의 라벨과
비교합니다. 약관 제16조 단위에서 뽑힌 노드 네 개 가운데 라벨이 같은 것은 약관 문서 노드 하나뿐이라, 그 노드의 버전 값만
합칠 값으로 모입니다. 조항 노드는 라벨이 달라 건너뜁니다.
K5는 모인 값마다 같은 세대에서 값이 같은 노드를 찾아 합칩니다. 제약은 LLM에게도 보이지만, LLM은 단위마다 따로 불려서 중복을
피할 수 없습니다. Neo4j에도 제약을 걸지 않습니다. 걸어 두면 같은 값의 두 번째 노드를 쓰는 순간 실패하기 때문입니다. 그래서
제약은 막는 데가 아니라 나중에 합치는 기준으로만 씁니다.

---

## 장표 2. K5 병합: 무엇을 어떻게 합치나 (예시)

- 제목: KG 구축 K5 병합
- 리드문(사용자 문구): 노드를 합칠 때 사용 하는 스키마의 고유 속성 값이 같은 노드를 하나로 합쳐, 여러 추출 단위에 흩어진 같은 대상을 한 노드로 모음

**도형 구성**

1. 왼쪽 「합치는 기준: 스키마의 고유 속성」 카드 3개와 아래 안내:
   - 약관: TermsDocument.version
   - 혜택 안내: ProductGuide.product_id
   - 상담 기록: Consultation.record_id
   - 안내(점선 카드): 고유 속성이 없는 라벨(Clause, Proposal 등)은 합치지 않음
2. 오른쪽 위 「예 1. 약관 문서 노드 (조항 16개에서 각각 뽑힘)」: 합치기 전과 뒤
   - 전: TermsDocument(1.2)와 Clause 짝 3줄 + "… 16쌍"
   - 가운데 화살표: mergeNodes
   - 뒤: TermsDocument(1.2) 하나에서 Clause 3개로 HAS_CLAUSE + "… 16개"
3. 오른쪽 아래 「예 2. 상담 노드 (앞 상담 참조와 본문)」:
   - 전: Consultation C-20260302-002 (record_id만, 다른 상담의 FOLLOWS로 생김) / Consultation C-20260302-002 (속성 5개, 본문에서 뽑힘)
   - 뒤: Consultation C-20260302-002 하나 (속성 5개, FOLLOWS와 FROM_CHUNK 2개 유지)
4. 아래 규칙 카드 2개(넓게):
   - 이번에 들어온 값만: K4가 모은 값만 검사. 관련 엔티티만 건드림
   - 같은 세대 안에서만: generation이 같은 노드끼리 합침
   - 「관계도 함께 옮김」은 위 예시 그림이 이미 보여 주고, 「값이 다르면 첫 노드 값」은 v0 한계라 README에만 둠(사용자 결정)

**발표자 노트**

앞 장의 원리가 실제로 어떻게 나타나는지 봅니다. K4는 쓰기만 하기 때문에, 약관 조항 16개에서 각각 뽑힌 약관 문서 노드 16개가
그대로 들어가 있습니다. K5는 버전 값이 같은 이 노드들을 하나로 합칩니다. 혜택 안내는 상품 ID, 상담 기록은 상담 번호가 같은
노드를 합칩니다. 고유 속성이 없는 조항이나 제안 노드는 합치지 않습니다.
합칠 때 관계도 남는 노드로 옮깁니다. 그래서 합쳐진 약관 문서 노드는 조항 16개와 이어지고, 근거 청크 노드 2개와
이어집니다. 같은 청크로 가는 관계는 하나로 합쳐집니다. 상담 예시에서는 다른 상담이 앞 상담을 가리키며 만든 번호만 있는 노드와, 그 상담 본문에서 뽑힌 노드가 하나로
합쳐져 이전 상담과 다음 상담이 실제로 이어집니다.

---

## 장표 3. K5 병합 코드와 결과

- 제목: K5 병합 코드 (kg_build.py)
- 리드문: K4에서 모은 (라벨, 속성, 값)마다 같은 세대의 노드를 찾아, 2개 이상이면 APOC로 하나로 합침
- 왼쪽 코드 상자 「합칠 값 모으기(apply)와 k5_merge (kg_build.py 발췌)」: 굵게 merge_keys.add, apoc.refactor.mergeNodes 줄
- 오른쪽 위 표 상자 「v0 표본에서 합쳐진 묶음 (전체 재색인)」: 3줄(라벨과 값, 전 → 뒤)
- 오른쪽 가운데 코드 상자 「합쳐진 약관 문서 노드 (Neo4j 조회)」: 속성과 관계 수
- 오른쪽 아래 카드(파랑): 전체 재색인 엔티티 110 → 91 / 증분 색인 새 엔티티 31 중 5개가 기존 노드와 합쳐짐

**발표자 노트**

합칠 값은 K4가 노드를 쓰면서 미리 모읍니다. 스키마의 고유 속성 제약을 보고, 이번에 쓴 노드 가운데 그 라벨이면서 값이 있는
것만 모읍니다. k5_merge는 그 값마다 같은 세대에서 값이 같은 노드를 찾고, 두 개 이상이면 APOC의 mergeNodes로 합칩니다.
v0 표본 전체 재색인에서는 세 묶음이 합쳐져 엔티티가 110개에서 91개로 줄었습니다. 증분 색인에서는 새로 쓴 엔티티 31개 가운데
5개가 이미 있던 노드와 합쳐졌습니다.
