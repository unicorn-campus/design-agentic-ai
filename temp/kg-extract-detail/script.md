# ④ 엔티티·관계 추출 상세: LangChain LLMGraphTransformer — PPT 스크립트

- 산출물: `temp/kg-extract-detail/엔티티관계추출상세.pptx` (1장)
- 작성: 클로니(직접 수행), 2026-10-13
- 앞 장표: 「그래프DB 인덱싱 과정」 ④ · 「엔티티·관계 추출 도구 선택」(사용자 결정: LangChain 방식)
- 스타일: `references/pptx-guide.md` — `내용_단쪽` 레이아웃, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음
- 예시는 가명처리 뒤 글(A사 · B카드 · C은행)을 씀 — 앞 장표 ② 정제·가명처리와 맞춤

## 근거(원본 코드 직접 확인, 스크립트에만 기록)

- `langchain-neo4j` 0.11.0 main `libs/neo4j/langchain_neo4j/graphs/llm.py`(로컬 사본 `.temp/lcn-llm.py`)
  - 73 ~ 108행 기본 지시문: 기본 종류 이름 쓰기(person), 일반적 관계 이름, 같은 대상은 가장 완전한 이름 하나로(Coreference)
  - 153 ~ 184행 허용 목록은 필드 설명 "Available options are …"로 전달. `enum` 강제는 `llm_type == "openai-chat"`만
  - 784 ~ 830행 도구 호출(`with_structured_output`) 가능하면 구조화 답, 불가하면 JSON 글 + `json_repair` 복구.  
    불가 경로에서 `node_properties`/`relationship_properties`를 주면 `ValueError`
  - 597 ~ 619행 이름 정리: id `.title()`, 종류 `.capitalize()`, 관계 공백 → `_` + 대문자
  - 883 ~ 921행 `strict_mode`(기본 True): 허용 밖 종류의 노드, 끝점이 허용 밖인 관계, 허용 밖 관계(3개 묶음이면 방향까지) 버림.  
    버린 개수 로그 없음
  - 923 ~ 935행 `convert_to_graph_documents` = 청크마다 `process_response` 1회(차례로),  
    1027 ~ 1038행 `aconvert_to_graph_documents` = `asyncio.gather` 동시 실행
  - 결과 `GraphDocument(nodes, relationships, source=document)`
- `.temp/lcn-graph.py`(다음 단계용, 발표자 노트에만): `add_graph_documents`는 `MERGE (:__Entity__ {id})` —  
  `baseEntityLabel=True`면 이름만 같아도 종류가 달라도 한 노드로 합쳐짐
- 실행 확인: `'iPhone'.title()` → `Iphone`, `'a사'.title()` → `A사`(Python 3, 2026-10-13)

## 슬라이드 1 — ④ 엔티티·관계 추출 상세: LangChain LLMGraphTransformer

- 리드문: 청크 하나마다 LLM을 한 번 불러 노드·관계를 뽑고, 허용 목록 밖은 걸러 GraphDocument로 넘김
- 도형 구성
  - 맨 위 흐름 6칸: 입력 → 4-1 ~ 4-4 → 출력. 단계마다 누가 하나(코드 · LLM) 표시
  - 가운데 예시 3칸: 입력 청크 → 설정 코드 → 결과 그래프(노드 · 화살표 도형, 버려진 것은 회색 점선)
  - 맨 아래 실무 포인트 카드 4개

| 칸 | 이름 | 누가 | 설명 |
|----|------|------|------|
| 입력 | 청크 1개 | — | Document(청크 글 + 메타데이터) |
| 4-1 | 프롬프트 조립 | 코드 | 기본 지시문 + 허용 목록 + 추가 지시 |
| 4-2 | LLM 호출 | LLM | 청크당 1번, 도구 호출로 정해진 틀에 답. 미지원 모델은 JSON 글을 받아 복구 |
| 4-3 | 이름 정리 | 코드 | 관계 → LAUNCHED 꼴, 종류 → Company 꼴, 영문 이름 iPhone → Iphone |
| 4-4 | 허용 목록 필터 | 코드 | strict_mode=True(기본), 목록 밖 종류 · 관계는 말없이 버림 |
| 출력 | GraphDocument | — | 노드 · 관계 · 원본 청크 → ⑤ 같은 이름 병합으로 |

- 예시
  - 입력 청크: "A사는 2025년 B카드를 출시했다. 이 카드는 C은행과 제휴했다."
  - 설정 코드:  
    `t = LLMGraphTransformer(llm=llm,`  
    `  allowed_nodes=["Company", "Product"],`  
    `  allowed_relationships=[`  
    `    ("Company", "LAUNCHED", "Product"),`  
    `    ("Product", "PARTNERED_WITH", "Company")])`  
    `docs = t.convert_to_graph_documents(chunks)`
  - 결과: (A사:Company) ─LAUNCHED→ (B카드:Product) ─PARTNERED_WITH→ (C은행:Company)  
    '이 카드' → B카드로 맞춤. LLM이 함께 뽑은 (A사) ─RELEASED_IN→ (2025:Year)는 Year가 목록 밖이라 버림(예시 설명용)
- 실무 포인트

| # | 제목 | 내용 |
|---|------|------|
| 1 | 목록은 안내, 강제는 필터 | 허용 목록은 프롬프트로 알려 줄 뿐(답을 강제하는 건 OpenAI 모델만) → 뒤에서 strict_mode가 거름 |
| 2 | 속성은 도구 호출 모델만 | node_properties · relationship_properties는 도구 호출 못 하는 모델에서 오류 |
| 3 | 청크 수 = LLM 호출 수 | aconvert_to_graph_documents로 동시 호출, 호출 한도(속도 제한) 주의 |
| 4 | 청크끼리는 못 합침 | 한 청크 안의 '이 카드'만 맞춰 줌 → 청크 사이 같은 대상은 다음 단계 병합 |

### 발표자 노트

- LLMGraphTransformer는 청크(Document) 하나를 받아 LLM을 한 번 부르고, 노드 · 관계 묶음(GraphDocument)을 돌려줌
- 4-1: 기본 지시문에 '사람은 person처럼 기본 종류로', '관계는 일반적인 이름으로', '같은 대상은 가장 완전한 이름 하나로'가 들어 있음.  
  허용 목록과 additional_instructions가 여기에 붙음
- 4-2: 모델이 도구 호출(구조화 출력)을 지원하면 정해진 틀로 답을 받음. 지원하지 않거나 ignore_tool_usage=True면 JSON 글을 받아  
  json_repair로 고쳐 읽음. 이 경우 속성 추출은 못 씀
- 4-3: 이름을 .title()로 바꿔 영문은 단어 첫 글자만 대문자가 됨(iPhone → Iphone). 한글은 그대로. 관계는 LAUNCHED처럼 대문자 + 밑줄
- 4-4: strict_mode가 기본으로 켜져 있어 허용 목록 밖 결과를 버림. 몇 개를 버렸는지 알려 주지 않으므로 처음엔 strict_mode=False로  
  한 번 돌려 무엇이 버려지는지 보는 것을 권장
- 다음 단계 예고: add_graph_documents가 이름(id)으로 MERGE해 이름이 완전히 같은 노드는 합쳐짐. baseEntityLabel=True면  
  종류가 달라도 이름만 같으면 한 노드가 됨. 'A사'와 'A사(주)'처럼 조금 다른 이름은 따로 처리해야 함
