# 노드 타입 · 관계 타입 먼저 정하기(그래프 스키마 도출) — PPT 스크립트

- 산출물: `temp/kg-schema-design/그래프스키마도출.pptx` (v2: 4장, 새 2장은 `스키마7가지.pptx`로도 따로 있음)
- 작성: 클로니(장표 · 코드 확인) · 지식니(외부 자료 조사), 2026-10-14
- 위치: 「그래프DB 인덱싱 과정」 ③ 청킹과 ④ 엔티티 · 관계 추출 사이 — 사용자 질문 "추출 전에 노드 · 관계 타입을 먼저 뽑는 게 맞나" → 맞음
- 기준 문서: `.agents/skills/design-architecture/guides/05-지식도구설계-가이드.md` 443 ~ 498행(사용자 첨부 표의 원본)
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 편집 가능 도형, 출처 줄 없음(근거는 이 파일에만)

## 첨부 표와 가이드의 차이(장표는 가이드 기준)

- 첨부 표는 FK 수부터 셈(0개 · 1개 → 노드 타입). 가이드는 **"그 표 자체가 조회 대상인가"를 먼저 묻고 나서 FK를 셈**(460행).  
  순서를 바꾸면 FK 2개인 독립 엔티티(이체 기록)를 관계 타입으로 흡수해 버림 → 장표 2는 이 순서로 그림

## 근거(스크립트에만 기록)

| 내용 | 판정 | 근거 |
|------|------|------|
| 테이블 → 라벨, 행 → 노드, 열 → 속성 | 맞음 | https://neo4j.com/docs/getting-started/data-modeling/relational-to-graph-modeling/ (`.temp/n4j_rel2graph.html`, 클로니 원문 확인) |
| FK → 관계, 바꾼 뒤 FK 열 삭제 | 맞음(삭제는 가이드에 없던 내용, 장표에 추가) | 같은 문서 |
| 조인 테이블 → 관계, 그 열 → 관계 속성 | 맞음 | 같은 문서 |
| 업무 속성 연결 테이블을 조회 · 집계하면 노드 | 부분(Neo4j는 속성 · 중간 노드 둘 다 허용, '조회 대상' 판정어는 없음) | https://neo4j.com/docs/getting-started/data-modeling/modeling-designs/ |
| FK 3개 이상 → 노드(중간 노드) | 맞음 — 하이퍼엣지는 Neo4j가 지원하지 않아 중간 노드로 풂 | 같은 문서(`.temp/n4j_modeldesign.html`, 클로니 원문 확인) |
| 이벤트를 노드로 두기 | 셋 이상을 잇는 경우(고용 이벤트 = 사람 · 회사 · 역할)에만 Neo4j 예시와 맞음 | 같은 문서. 지식니 '다름' 판정 → 클로니 원문 확인 후 '셋 이상일 때만'으로 조정 |
| 이름 규칙: 라벨 PascalCase, 관계 대문자 + 밑줄 | 공식 권고 | https://neo4j.com/docs/cypher-manual/5/syntax/naming/ |
| 지침 없으면 관련 없거나 일관되지 않은 노드가 나옴 | 공식 블로그 | https://neo4j.com/blog/developer/unleashing-the-power-of-schema/ |
| 같은 뜻이 다른 라벨로 쪼개짐(Company · Gaming Company) | 공식 블로그 | https://neo4j.com/blog/developer/construct-knowledge-graphs-unstructured-text/ |
| MS GraphRAG 기본 엔티티 타입 = organization · person · geo · event | 맞음 | graphrag `config/defaults.py` 42행(`.temp/gr_defaults.py`) |
| `graphrag prompt-tune --discover-entity-types`(기본 켜짐) — 표본 청크로 엔티티 타입 생성 | 확인 | https://microsoft.github.io/graphrag/prompt_tuning/auto_prompt_tuning/ |
| LLM KG Builder 스키마 옵션: Pre-defined · Custom · Use Existing Schema · Get Schema From Text | 확인 | https://neo4j.com/labs/genai-ecosystem/llm-graph-builder-features/ |
| LlamaIndex `SchemaLLMPathExtractor(strict=True)`, LangChain `allowed_nodes`(빈 목록이면 아무 타입) | 확인 | LlamaIndex Property Graph 가이드, LangChain 레퍼런스 |
| Native: 스키마 미지정 시 SimpleKGPipeline이 입력 글로 `SchemaFromTextExtractor` 자동 실행, "FREE"는 스키마 없음 | 코드 확인 | `neo4j_graphrag/experimental/pipeline/config/template_pipeline/simple_kg_builder.py` 170 ~ 264행 |
| `GraphSchema` = 추출 안내 + 추출 뒤 정리에 함께 씀. 노드 타입을 주면 `additional_node_types` 기본 False | 코드 확인 + 실행 | `components/schema.py` 144 ~ 148 · 450행, 실행 결과 False |
| `GraphPruning`: 스키마 밖 노드 · 관계 제거 + 개수 통계 | 실행 확인 | Brand 노드 1 · OWNS 관계 1 제거, pruned 1 · 1(2026-10-14) |
| `SchemaFromExistingGraphExtractor`: 적재된 그래프에서 스키마를 읽음(기본 추가 허용 없음) | 코드 확인 | `components/schema.py` 1874행 |
| 스키마 없이 실제 LLM 추출 시 라벨 제각각 | 실측 | `hybrid-ai-lab/verify/neo4j-vector-search` `pytest -m ollama`(gemma-4 12B, 청크 2개): Channel · AnnualFee · Benefit · PerformanceCondition · Brand · Fee · Guardian · Grade · Date · Store · CardProduct — 카드가 Brand · CardProduct로, 요금이 Fee · AnnualFee로 갈림 |
| 역량 질문(Grüninger & Fox, TOVE), Ontology 101 Step 1 범위 = 답할 질문 목록 | 2차 확인 | https://eil.mie.utoronto.ca/theory/enterprise-modelling/entmethod , https://protege.stanford.edu/publications/ontology_development/ontology101-noy-mcguinness.html |
| 확인 못 함 | — | prompt-tune이 관계 타입 목록까지 뽑는지, KG Builder 'Get Schema From Text'가 문서 본문도 받는지 → 장표에 넣지 않음 |


## v3 변경(2026-10-14, 사용자 지적 · 직접 수정 반영)

- 사용자 지적: 스키마 도출은 인덱싱 파이프라인 단계가 아니라 사전 설계 → 1장 맨 위 흐름을 두 줄로 바꿈  
  설계 시(사전 1회): 원천 분석 → 후보 도출 → 3단계 확정(사람) → GraphSchema 파일(버전 관리) /  
  인덱싱 시(매 실행): 로드 → 정제 · 가명처리 → ③ 청킹 → ④ 추출 → 가지치기(Pruning) → 병합 · KG 저장.  
  스키마 파일 → ④ 추출 · 가지치기에 '읽어 씀' 점선. 메모: 인덱싱은 읽기만 함, 바뀌면 새 세대로 재인덱싱
- 1장 결론 띠: '스키마는 인덱싱 전 설계 단계에서 확정해 파일로 고정, 인덱싱은 읽어 쓰기만 함 — 2 · 3 · 4장 안내'
- 사용자 직접 수정(14:04 저장본, 백업 `그래프스키마도출.user-1404.pptx`)을 build.js에 옮김:  
  1장 제목 '1. 스키마 도출: …', 칩 '가지치기 (Pruning)' / 2장 ⑥ 예 'Card.name = KEY', ⑦ 칸 이름 3개 · '①~⑤에 지정된 목록 밖을 허용할지 여부',  
  아래 띠 둘째 줄 = 제약 3종 설명. ⑦ 칸 이름은 사용자 12pt → 14pt 하한 때문에 세 줄 · 줄 높이 0.74로 넣음

## v4 변경(2026-10-14, 사용자 지적)

- 1장 인덱싱 줄: '병합 · KG 저장' 한 칸 → 'KG 저장' · '병합'으로 나누고 '임베딩(노드 설명)' 추가(8칸 격자)
- 순서는 Native 연결 순서 writer → resolver(`simple_kg_builder.py` 403 ~ 406행)를 따라 ④ 추출 → 가지치기 → KG 저장 → 병합 → 임베딩.  
  병합기는 DB에 저장된 `__Entity__`를 대상으로 합치므로 저장 뒤. 임베딩은 합쳐진 노드 설명을 써야 해 병합 뒤.  
  청크 벡터는 기존 벡터DB 인덱싱의 벡터를 KG 저장 때 metadata로 함께 넣음(「Neo4j 벡터검색」 장표와 같은 설계)
- 참고: 처음 받은 「그래프DB 인덱싱 과정」 장표는 추출 → 같은 이름 병합 → KG 구축 순서(메모리에서 합친 뒤 저장하는 MS GraphRAG 방식)

## v5 변경(2026-10-14, 사용자 요청 · 직접 수정 반영)

- 3장(정형 테이블): 판정 결과 4개에 번호 ① 노드 타입 · ② 2개 · 업무 열 없음 → 관계로 흡수 · ③ 조인 테이블: 2개 + 업무 속성 →  
  관계 속성 · ④ 3개 이상 → 중간 노드. 오른쪽 예시도 같은 번호 순: ① 이체 · ② 사용자역할 · ③ 주문상품 · ④ 수강신청
- 예시 '회원 · 재료 · 회원재료제외'를 '사용자 · 역할 · 사용자역할(사용자FK, 역할FK) → (:사용자)-[:맡음]->(:역할)'로 바꿈 —  
  노드 타입 테이블과 연결 테이블이 한 예시에 섞여 규칙 구분이 흐렸음. 사용자가 처음 첨부한 표의 '사용자 역할 테이블' 예를 씀
- 사용자 직접 수정(14:39 저장본, 백업 `그래프스키마도출.user-1439.pptx`) 반영: 2 · 3 · 4장 제목 앞 '1. 스키마 도출: ',  
  3장 ③ '조인 테이블: 2개 + 업무 속성', 1장 결론 띠 2줄 · 16pt(사용자가 묶은 그룹은 빌드에서는 개별 도형)

## v6 변경(2026-10-14, 사용자 결정)

- 용어 통일: '관계 타입' → '관계'(관계와 관계 타입을 구별하지 않기로 함). 12곳.  
  '노드·관계 타입'은 '노드 타입·관계'로 바꿈 — '관계 타입'만 지우면 '노드·관계'(노드와 관계 인스턴스)로 뜻이 바뀌기 때문.  
  코드의 `relationship_types`는 라이브러리 칸 이름이라 그대로 둠. 아래 슬라이드 절의 옛 표기는 이력으로 남김
- 사용자 직접 수정(15:17 저장본, 백업 `그래프스키마도출.user-1517.pptx`)은 이미 build.js와 글자 차이 0건으로 맞춘 뒤 다시 빌드함

## v7 변경(2026-10-14, 사용자 요청)

- `references/pptx-guide.md` 5절에 「가운뎃점(·) 대신 뜻을 씀」 규칙과 6-12 체크리스트 17번을 추가함
- 4장의 가운뎃점 33곳을 뜻에 맞게 바꿈(본문 · 칩 · 표 · 발표자 노트). 예: '노드 타입과 관계', '설계 시(사전 1회)', '정제와 가명처리',  
  'organization, person, geo, event', 'FK가 0개 또는 1개', '조회하거나 집계하면', '조인 테이블: 2개이고 업무 열 없음'
- 빌드 뒤 확인: 덱 본문 0건, 발표자 노트 0건. 이 스크립트(.md)의 옛 절은 이력이라 그대로 둠

## v10 변경(2026-10-18, 사용자 요청)

- 5쪽 권고 절차의 단계마다 우리 예제(합성 상담 이력)의 실제 데이터로 예시 장표를 만듦: ①, ②, ③, ④ 2장(사례, 지표), ⑤ → 6장
- 기존 사례 2장(v9의 6, 7쪽)은 새 장표가 내용을 나눠 담으므로 뺌(방법 비교는 ② 장표, 채우기 지표는 ④-2, 문서 종류별 차이는 ⑤)
- 덱은 사용자가 PowerPoint에서 직접 고치는 중(21:13 저장본 8쪽, 백업 `그래프스키마도출.user-2113.pptx`)이라 다시 빌드하지 않음.
  새 장표는 `스키마도출_단계별예시.pptx`(`ONLY=steps node build.js …`)로 만든 뒤, 사용자 요청으로 본래 덱(21:45 저장본 7쪽,
  백업 `그래프스키마도출.user-2145.pptx`)의 사례 2장(6, 7쪽)을 지우고 5쪽 뒤에 옮겨 붙임(scratchpad `merge_steps.py`, 도형 XML 복사).
  1 ~ 5쪽 글자 차이 0건 확인. 덱은 11장. build.js 기본 빌드에는 사용자가 직접 고친 1 ~ 5쪽 내용이 없으므로 PowerPoint 덱이 원본임
- 용어: 사용자 결정에 따라 '뼈대' 대신 스키마 후보(② 결과), 스키마 초안(③ 결과, ④ 대상), 확정 스키마(⑤), '층' 대신 묶음
- 실측 근거: `hybrid-ai-lab/verify/doc-schema-candidates/`(output-cqonly-v3, output-fill-v3, output-fill-v3b, README),
  ⑤ 저장과 다시 읽기는 2026-10-18 scratchpad에서 시연(확정 승인 전이라 프로젝트에 저장하지 않음)
- 발견: 정제된 상담 청크 12건에 한글 표기 생년월일("1991년 1월 6일")이 남음(v2 인덱스에도 같음). 예시 글에서는 그 줄을 뺌.
  인덱서 정제 규칙 수정은 별도 작업으로 제안함

## 슬라이드 단계 ① — 역량 질문 정하기(예시: 상담 이력)

- 리드문: 실제 사용자 질문을 모아 값을 빈칸으로 바꾸고 유형으로 묶은 뒤, 유형마다 역량 질문을 씀
- 왼쪽 실제 질문 4개(출처 표시): 사용자 스토리 UFR-EVID-030, 평가셋 Q15, Q16, D3 안내문 검색 평가 질문
- 가운데 질문 유형(값을 빈칸으로): {회원}의 최근 불편은 / {회원}이 받은 제안과 응답, 이유는 / 어떤 조건이면 다시 보나 / 어느 상담과 이어지나
- 오른쪽 역량 질문 5개(실험에 쓴 문장 그대로)
- 아래: 답이 될 이름은 쓰지 않음(피함 / 권함 예), 다른 문서 예(약관 1개, 혜택 1개), 초안은 LLM이 쓰고 사람이 검토

## 슬라이드 단계 ② — 스키마 후보 넓게 뽑기

- 리드문: 묶음별 표본을 1건씩 SchemaFromTextExtractor에 넣고(역량 질문만 examples로) 나온 이름을 모두 모음
- 왼쪽: 묶음과 표본 수(약관 1묶음 10건 전부, 상담 세그먼트 6묶음 시작 12건 상한 30건, 혜택 4묶음 시작 4, 7, 10, 10건)
- 가운데: 실제 1건 C-20260701-016 글 일부 → 추출기 출력(노드 타입 6, 관계 7, Proposal과 Condition은 업무 개념, Customer의
  email과 birthdate 속성은 버릴 대상)
- 오른쪽: 30건 모은 결과(노드 타입 53, 관계 106, 많이 나온 이름 5개, 드물게 나온 업무 개념 이름) + 이름을 넘기면 14개로 모이지만
  업무 개념 0 / 4, 넘기지 않으면 53개로 흩어지지만 4 / 4

## 슬라이드 단계 ③ — 스키마 후보 확정(LLM 추천 + 사람 확정)

- 리드문: 후보 목록과 역량 질문을 LLM에 주면 병합, 제거, 추가 초안과 근거를 추천하고, 사람이 검토해 스키마 초안을 확정
- 왼쪽 LLM 추천(근거 질문 번호): 병합 5줄, 제거 4줄, 추가 3줄
- 오른쪽 위: 사람이 정한 것(응답은 Proposal 속성, Request는 topic 속성, 제약은 record_id UNIQUENESS 하나)
- 오른쪽 아래: 해당과 비해당 설명 2쌍(Complaint, Proposal) + 결과 수(노드 타입 4, 관계 5, 패턴 5, 제약 1)

## 슬라이드 단계 ④-1 — 채우기 시험: 실제 1건씩 보기

- 리드문: 스키마 초안을 schema로 주고 상담 48건 전체를 실제 추출해 강사용 정답표와 한 건씩 대조함
- 왼쪽 C-20260701-016(불만형): 불만 원인 맞음, 재검토 조건 맞음, 이전 상담 연결 맞음, 제안은 다른 대안을 골라 틀림
- 오른쪽 C-20260310-018(불만 없는 주소 변경 문의): v1은 '이사'를 불만으로 잘못 뽑고 제안 2개, v2는 불만 없음과 제안 1개와 이유가 맞음

## 슬라이드 단계 ④-2 — 채우기 시험: 전체 지표와 설명 고치기

- 리드문: 48건 지표로 보고 잘못 뽑기가 많은 타입의 설명을 고쳐 ③으로 돌아감 — 한 번 고치자 불만 오탐 22건이 4건으로
- 왼쪽: v1 → v2 짝 막대 5개(불만 오탐 22 → 4, 제안 노드 87 → 56, 응답 일치 31 → 37, 조건 오탐 6 → 0, 이전 상담 연결 34 → 36)
- 오른쪽: 고친 설명 2쌍(Complaint, Proposal의 v1과 v2) + 남은 문제(응답 엄격 일치 37 / 48, 남은 불만 오탐 4건은 실제 불편 발화)

## 슬라이드 단계 ⑤ — 고정과 그 뒤

- 리드문: 시험을 통과한 스키마 초안을 GraphSchema.save()로 파일에 고정하고, 인덱싱은 그 파일만 읽음
- 왼쪽: 코드 3줄과 실측 결과(노드 타입 4, 관계 5, 패턴 5, 제약 1, additional_* 모두 False, 다시 읽은 것과 같음)
- 가운데: 고정의 뜻(목록 밖 타입은 가지치기가 지움, 인덱싱 ④ 추출과 가지치기가 이 파일을 읽음, 바뀌면 새 세대)
  실제 예: 상담 원문 v3 반영 때 새 세대 gen-d3v3-20261018(상담 48청크 새 임베딩, 170청크 재사용)
- 오른쪽: 문서 종류별 진행 상황(상담 ① ~ ④ 완료와 확정 승인 남음, 혜택과 약관은 ②까지. 혜택 Exclusion 3 → 25건, 약관 이름 76% 흩어짐)

## v9 변경(2026-10-18, 사용자 요청)

- 5쪽(소스 문서 → 노드 타입과 관계)을 실험으로 다듬은 권고 절차로 다시 씀. 특정 문서(상담, 혜택, 약관)에 묶이지 않는 일반 가이드
- 6쪽, 7쪽에 우리 시스템 사례를 새로 넣음 → 덱 7장
- 빌드 전 사용자 직접 수정(10-14 18:07 저장본, 백업 `그래프스키마도출.user-1807.pptx`)을 build.js에 옮김:
  4쪽 칸 '2. DB 카탈로그 읽기', 띠 아래 ※ 안내 한 줄(DB 카탈로그 스키마는 원본 테이블 스키마로, 뷰 스키마는 쓰지 않음)
- 출처: 사용자 요청으로 5쪽에 출처 줄을 넣음(링크). 6쪽, 7쪽은 실측 조건 한 줄

### 출처(5쪽, 원문 확인)

| 내용 | 출처 | 확인 |
|---|---|---|
| SchemaFromTextExtractor로 글에서 스키마 자동 추출, GraphPruning 정리 규칙, additional_* | https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html | `.temp/5a656419.html` |
| LLM Graph Builder 'Get Schema From Text'(글이나 스키마 설명을 주면 LLM이 스키마 제안) | https://neo4j.com/labs/genai-ecosystem/llm-graph-builder-features/ | `.temp/090d2235.html` |
| 역량 질문 = 지식 기반이 답해야 할 질문 목록, 범위를 정하고 나중에 시금석으로 씀(Gruninger와 Fox 1995 인용) | https://protege.stanford.edu/publications/ontology_development/ontology101-noy-mcguinness.html | `.temp/9c2d3caf.html` |
| 포화 멈춤 규칙(기준 묶음, 연속 확인 수, 새 정보 기준값) | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0232076 | `.temp/plos_guest2020.txt` |
| 표본 수는 비율이 아니라 건수(드문 타입 확률 n ≥ ln(0.05)/ln(1−p), p 10%면 29건) | 계산(지식니 조사, 클로니 재계산) | 대화 기록 |

### 실측 근거(6쪽, 7쪽)

- `hybrid-ai-lab/verify/doc-schema-candidates/README.md`(2026-10-18, Groq `openai/gpt-oss-120b`, neo4j-graphrag 1.22.0)
- 상담 30건 방법 비교: 노드 타입, 관계 이름 수 = 1건씩 따로 45, 115 / 이름 다시 쓰기 14, 26 / 원문 보강 + 이름 다시 쓰기 38, 43 /
  원문 보강 + 역량 질문 + 이름 다시 쓰기 10, 10 / 원문 보강 + 역량 질문만 53, 106. 업무 개념 4개(불만, 제안, 응답, 재검토 조건) 중
  나온 수 = 0, 0, 0(Response 1건은 상담사 답이라 제외), 1(불만 26건), 4(각 1 ~ 5건)
- 뼈대 채우기(48건): v1 → v2 = 불만 오탐 22 → 4(24건 중), 제안 노드 87 → 56, 응답 엄격 일치 31 → 37(48건 중),
  재검토 조건 오탐 6 → 0(29건 중), 이전 상담 연결 34 → 36(36건 중)
- 문서 종류별: 혜택 Exclusion 3 → 25건(역량 질문), 약관 1건에서만 나온 이름 76%, 상담 업무 개념 각 1 ~ 5건

## 슬라이드 5(v9 다시 씀) — 소스 문서 → 노드 타입과 관계: 권고 절차(Neo4j)

- 리드문: LLM은 넓게 후보만 뽑고, 사람이 역량 질문 기준으로 뼈대를 확정한 뒤, 뼈대로 실제 추출해 검증하고 GraphSchema로 고정함
- 도형: 맨 위 5단계 흐름(사람 단계 파랑, LLM 단계 연한 색, 고정 네이비) + 각 단계 아래 할 일 상자 + ④ → ③ 되돌림 점선 +
  아래 주의 4개 + 출처 줄(링크)
- ① 역량 질문 정하기(사람): 문서 종류마다 답해야 할 질문 5개 안팎 / 타입 이름은 쓰지 않고 질문으로만 / 질문이 곧 범위이자 나중의 시금석
- ② 넓게 뽑기(LLM): 층별 표본, 시작 10건과 상한 30건(비율 아닌 건수) / `SchemaFromTextExtractor`에 질문을 examples로 /
  앞서 나온 이름을 다시 쓰라는 안내는 넣지 않음
- ③ 뼈대 확정(사람): 합치기, 빼기, 보태기 / 빈도가 아니라 질문 기준(드문 이름도 살림) / 타입마다 description을 좁게(무엇이 아닌지까지) /
  제약은 사람이 정함
- ④ 채우기 시험(LLM + 사람): `LLMEntityRelationExtractor`(schema=뼈대) + `GraphPruning` / 정답표나 질문의 답이 채워지는지 셈 /
  잘못 뽑기가 많으면 description을 고쳐 ③으로
- ⑤ 고정(코드): `GraphSchema.save()`, additional_* false / 인덱싱은 파일을 읽기만 함 / 바뀌면 새 세대로 다시 인덱싱
- 주의: 이름 다시 쓰기 안내는 이름을 모으지만 새 개념을 막음(④에서만) / 대화 속 행위와 규칙 구조는 LLM이 잘 못 뽑음(사람이 보탬) /
  여러 문서에 걸친 관계(비교)는 청크 추출로 안 나옴 / 멈춤: 2건 이상 나온 새 이름이 연속 3건 없으면

## 슬라이드 6(v9 추가) — 사례 ① 상담 이력: 넓게 뽑기에서 뼈대 확정까지

- 리드문: 같은 상담 30건에 방법만 바꿔 보니, 질문만 넣었을 때 비로소 불만, 제안, 응답, 재검토 조건이 후보로 나옴
- 왼쪽: 방법 5개 줄(노드 타입 이름 수 막대 + 업무 개념 4개 중 나온 수 배지)
- 오른쪽: 확정한 뼈대 그림(Consultation, Complaint, Proposal{decision, decision_reason}, ReconsiderCondition, FOLLOWS) +
  LLM 후보를 합친 것과 사람이 보탠 것 구분 + 뺀 것
- 띠: 드문 개념은 질문만으로 넓게 뽑아야 보이고, 살릴지는 빈도가 아니라 질문으로 사람이 정함

## 슬라이드 7(v9 추가) — 사례 ② 뼈대 채우기 시험과 문서 종류별 차이

- 리드문: 뼈대의 이름보다 설명(description)이 추출 품질을 좌우함 — 채우기 시험으로 설명을 고쳐 가며 확정
- 왼쪽: v1 → v2 지표 5개(짝 막대) + 바꾼 설명 한 쌍
- 오른쪽: 문서 종류 3개 카드(혜택, 상담, 약관)와 맞는 방식 + 멈춘 표본 수
- 띠: 문서 성격에 따라 LLM 후보 비중과 사람 설계 비중이 다름. 절차(①~⑤)는 같음

## v8 변경(2026-10-14, 사용자 요청)

- 3쪽(정형 테이블 변환 규칙) 뒤에 「프롬프트로 정형 테이블 스키마 도출」 1장을 넣음 → 덱 5장  
- 근거: `hybrid-ai-lab/prompts/design-graph-schema.md`(9단계 [처리], [제약조건])와 실행 확인 결과  
  - GraphSchema 검증, `save()`, `from_file()`은 네트워크를 막은 상태에서도 성공(노드 타입 7, 관계 6, 패턴 6, 제약 7 그대로)  
  - 한글 라벨도 가지치기, Neo4jWriter, Cypher, UNIQUENESS 제약에서 동작했으나 사용자 결정으로 라벨은 영문,  
    한글 이름은 description에 둠  
- 빌드 전 확인: 저장된 덱과 build.js 다시 빌드 결과의 글자 차이 0건(사용자 직접 수정 없음)

## 슬라이드 4(v8 추가) — 프롬프트로 정형 테이블 스키마 도출

- 제목: 1. 스키마 도출: 프롬프트로 정형 테이블의 스키마 도출  
- 리드문: 변환 규칙을 프롬프트에 담아 바이브 코딩 도구에 맡김 — AI는 읽고 판정하고 그리며, 사람은 세 번 답하고 승인함  
- 도형: 맨 위 두 줄 흐름(사람 줄, AI 줄)에 9단계 카드. 사람 카드는 파란색(1, 4, 8단계), AI 카드는 흰색  
  - 1 입력 받기 → 2 카탈로그 읽기 → 3 규칙 판정 → 4 규칙 ①과 이름 답 → 5 스키마 초안 → 6 기계 검증 →  
    7 Mermaid 그림 → 8 검증과 승인 → 9 저장과 다시 읽기  
  - 8에서 5로 돌아가는 점선: 수정 요청 시 5단계부터 다시(최대 5회)  
- 아래 3칸  
  - 사람이 답하는 곳 3번: 1 출력 폴더와 DB 접속 정보(비밀번호는 .env에 직접 등록) /  
    4 규칙 ① 후보(FK 2개 + 업무 열)를 노드 타입 또는 관계 + 관계 속성으로, 뺄 테이블, 이름 후보 승인 /  
    8 Mermaid 그림과 판정표를 보고 승인  
  - AI가 지키는 규칙: FK 개수는 제약 수로 셈 / DB는 읽기 전용, 비밀번호는 .env에만 / 라벨은 영문, 한글 이름은 description /  
    그림은 Mermaid만, 판정과 이름은 추측해 확정하지 않음 / 후보 표시가 남으면 GraphSchema 파일을 만들지 않음  
  - 승인 화면 예: `:Member (회원)` → `HAS_CARD (보유함)` → `:Card (카드)` 도형  
- 아래 띠: 결과는 graph_schema.json(승인본)과 approval.json(승인자, 승인 일시, 입력 파일 SHA-256). 인덱싱은 이 파일을 읽기만 함 /  
  GraphSchema 검증, 저장, 다시 읽기는 Neo4j 서버 없이 됨(실행 확인)  
- 발표자 노트: 왜 프롬프트로 하는지(규칙은 기계가, 업무 판단은 사람이), 카탈로그는 DB에 원래 있는 구조 설명 테이블이라는 점,  
  열 2개짜리 FK를 1개로 세는 이유, 영문 라벨을 쓰는 이유

## 슬라이드 1 — 노드 · 관계 타입은 추출 전에 먼저 정함

- 리드문: 스키마는 추출 결과가 아니라 추출기에 주는 허용 목록 — 먼저 정하지 않으면 같은 개념이 여러 라벨로 쪼개짐
- 도형: 맨 위 흐름 6칸(③ 청킹 → ⓪ 스키마 도출(강조, 새 단계) → GraphSchema 고정 → ④ 추출 → 가지치기 → 병합 · KG 저장) /  
  왼쪽 「스키마 없이 추출하면」(실측 라벨 칩 11개, 쪼개진 짝 강조 + 도구 기본값 3줄) / 오른쪽 「스키마를 주면」(코드 + 쓰이는 곳 2개) /  
  맨 아래 결론 띠
- 실측 칩: Brand · CardProduct(카드), Fee · AnnualFee(요금) 강조, 나머지 Channel · Benefit · PerformanceCondition · Guardian · Grade · Date · Store
- 도구 기본값: Native 스키마 미지정 → 매번 입력 글에서 자동 추출(사람 검토 없음) / MS GraphRAG 기본 = organization · person · geo · event /  
  LangChain 빈 목록 → 아무 타입이나
- 코드:  
  `schema = GraphSchema.model_validate({`  
  `    "node_types": ["Card", "Benefit", "Fee"],`  
  `    "relationship_types": ["HAS_BENEFIT", "HAS_FEE"],`  
  `    "patterns": [("Card", "HAS_BENEFIT", "Benefit"), ("Card", "HAS_FEE", "Fee")]})`  
  `graph = await extractor.run(chunks=chunks, schema=schema)`  
  `result = await GraphPruning().run(graph, schema)`
- 쓰이는 곳: ① 추출 프롬프트에 허용 목록으로 들어감 ② 가지치기가 목록 밖 노드 · 관계를 지우고 개수를 남김(실행: Brand 1 · OWNS 1 제거)
- 결론 띠: ⓪ 스키마 도출을 ④ 추출 앞에 둠 — 정형 테이블은 규칙으로(2장), 문서는 표본 → 후보 → 사람 확정으로(3장)

## v2 변경(2026-10-14, 사용자 요청)

- 「스키마에 정의하는 7가지」를 2장으로 추가 → 정형 규칙은 3장, 문서는 4장으로 밀림(덱 4장)
- 사용자가 PowerPoint에서 직접 고친 1장(13:17 저장본) 글자 4곳을 build.js에 옮김:  
  '도구 기본값에도 도메인이 없음' → 'GraphRAG 도구 기본 노드/관계 타입이 없거나 너무 일반적임' ·  
  'Native:' → 'Neo4j:' · 'LangChain:' → 'LangChain+Neo4j:' · 실행 확인 줄 짧게 · 결론 띠 끝에 '스키마를 도출함'(장 번호만 2 · 3 · 4장으로)
- 덱 파일이 PowerPoint에 열려 있어(잠금) 원본은 덮어쓰지 않음. 새 장표는 한 장짜리 `스키마7가지.pptx`(`ONLY=schema node build.js …`)로 따로 만듦

## 슬라이드 2(v2 추가) — 스키마에 정의하는 7가지

- 리드문: 노드 · 관계 타입과 각각의 속성, 연결 패턴이 뼈대 — 제약과 허용 범위로 무엇을 지킬지 정함
- 도형: 왼쪽 7줄 목록(뼈대 ① ~ ⑤ 네이비 · 지킬 규칙 ⑥ ⑦ 블루) / 오른쪽 위 카드 예 그림(번호 꼬리표로 목록과 짝) / 오른쪽 아래 코드 / 아래 띠

| # | 정의할 것 | GraphSchema 칸 | 카드 예 |
|---|-----------|----------------|---------|
| ① | 노드 타입 | node_types[].label | Card, Benefit |
| ② | 노드 속성 | node_types[].properties | Card {name, annual_fee} |
| ③ | 관계 타입 | relationship_types[].label | HAS_BENEFIT |
| ④ | 관계 속성 | relationship_types[].properties | HAS_BENEFIT {valid_until} |
| ⑤ | 연결 패턴 | patterns (출발, 관계, 도착) | (Card, HAS_BENEFIT, Benefit) |
| ⑥ | 제약 | constraints — UNIQUENESS · EXISTENCE · KEY | Card.name = KEY(필수 + 고유) |
| ⑦ | 허용 범위 | additional_* | 목록 밖은 지움(목록을 주면 기본) |

- 코드: 7칸을 채운 `GraphSchema.model_validate({...})` — 실행 확인(neo4j-graphrag 1.22.0): name 없는 Card 노드를 가지치기가  
  `MISSING_REQUIRED_PROPERTY`로 지움, `additional_node_types` False · 노드 타입별 `additional_properties` False
- 띠: 최소한 = ① · ③ · ⑤ + ⑥ 고유키, 속성은 질문에 쓰는 것만 · 타입마다 description을 적으면 LLM이 고르는 기준이 됨 /  
  최대 홉 수 · 결과 상한 · 상충 관계는 검색 규칙이라 스키마에 넣지 않음 · 값 형식(type)은 아직 검사 안 함 → 저장 전 따로 변환
- 근거: `components/schema.py`(GraphSchema 450행 · NodeType · RelationshipType · Pattern 409행 · ConstraintType 261행 ·  
  GraphConstraintType 97행), `components/graph_pruning.py`(PruningReason 40행 · `_ensure_property_types` 497행 형식 미검사)

## 슬라이드 3 — 정형 테이블 → 노드 · 관계 타입: 변환 규칙

- 리드문: 모델 없이 규칙으로 바꿈 — 단, FK를 세기 전에 '그 표 자체가 조회 대상인가'부터 물음
- 도형: 왼쪽 판정 흐름(질문 마름모 대신 둥근 상자) / 오른쪽 예시 4개(테이블 → 그래프 그림) / 아래 메모 띠
- 판정: Q1 그 표 자체가 조회 대상인가? → 예: 노드 타입(열 = 속성, FK = 관계 타입, FK 열은 지움) / 아니오: Q2 FK 수  
  → 2개 · 업무 열 없음: 관계 타입 1개로 흡수 / 2개 + 업무 속성: 관계 타입 + 관계 속성(조회 · 집계하면 노드) / 3개 이상: 노드 타입(중간 노드)

| 예 | 테이블 | 그래프 | 메모 |
|----|--------|--------|------|
| 1 | 회원 · 재료 · 회원재료제외(회원FK, 재료FK) | (:회원)-[:제외함]->(:재료) | 테이블 3 → 노드 타입 2 + 관계 타입 1 |
| 2 | 주문상품(주문FK, 상품FK, 수량, 단가) | (:주문)-[:포함 {수량, 단가}]->(:상품) | 상품별 판매 집계가 잦으면 :주문상품 노드 |
| 3 | 수강신청(학생FK, 과목FK, 학기FK) | (:학생)-[:신청]->(:수강신청)-[:대상]->(:과목) | 관계는 양 끝이 둘뿐 → 중간 노드, 홉 +1 |
| 4 | 이체(출금계좌FK, 입금계좌FK, 금액, 일시) | (:계좌)-[:출금]->(:이체)-[:입금]->(:계좌) | FK 2개지만 조회 대상 → 노드(순서가 중요한 이유) |

- 메모 띠: Neo4j 공식 변환 규칙과 같음(테이블 → 라벨, FK → 관계, 조인 테이블 → 관계 + 속성, 셋 이상 → 중간 노드) ·  
  이름에 공백 없음 · Neo4j 권고는 라벨 PascalCase, 관계 대문자 + 밑줄 · 정형에서 나온 타입은 LLM 추출 비용이 들지 않음

## 슬라이드 4 — 소스 문서 → 노드 · 관계 타입: 표본 → 후보 → 사람 확정

- 리드문: LLM은 표본에서 후보만 뽑고 확정은 사람이 함 — 확정한 목록을 GraphSchema로 고정해 추출기에 넘김
- 도형: 맨 위 흐름 5칸 / 왼쪽 「후보 뽑는 도구」 카드 4개 / 오른쪽 「3단계 확정」(번호 + 온톨로지 대응 + 예) / 아래 주의 칩
- 흐름: 문서 종류별 표본 N건 → 스키마 추출기로 후보 → 정형 후보와 합침 → 3단계 확정 → GraphSchema 고정 · 추출기에 전달

| 도구 | 후보 뽑기 | 확정 |
|------|-----------|------|
| Native neo4j-graphrag | `SchemaFromTextExtractor().run(text=표본)` → GraphSchema 후보 | 고친 확정본을 schema로 넘김(안 넘기면 매번 자동 추출) |
| Neo4j LLM KG Builder | 'Get Schema From Text'가 스키마 제안 | 화면에서 사람이 고름 |
| MS GraphRAG | `graphrag prompt-tune --discover-entity-types` | 저장된 프롬프트 파일을 사람이 고침 |
| LangChain · LlamaIndex | 자동 후보 없음 | 사람이 허용 목록을 먼저 적음(allowed_nodes · SchemaLLMPathExtractor) |

| 단계 | 할 일 | 온톨로지 공학 대응 | 예 |
|------|-------|--------------------|----|
| 1 | 같은 의미 합치고 이름 정함 | 용어 나열 · 계층 정리 | Brand · CardProduct → Card, Fee · AnnualFee → Fee |
| 2 | 쓰는 워크플로우 단계가 없는 관계 타입 제외 | 역량 질문(답해야 할 질문이 범위) | 아무 단계도 안 따라가는 관계 → 다음 회차 후보 |
| 3 | 적재 원천이 없는 노드 타입 제외 | (가이드 고유 규칙) | 어느 원천도 안 채우는 타입 → 빈 노드라 정의 안 함 |

- 주의 칩: 표본에 없던 타입은 안 나옴 → 문서 종류마다 표본, 표본 수 기록 / 도구 기본값(organization · person · geo · event) 그대로 쓰지 않음 /  
  빼면 그래프에 아예 없음(가리는 것은 접근 필터) / 확정 뒤 역량 질문으로 되짚기(가이드 보완점)

### 발표자 노트

- 1장: 같은 카드가 어떤 청크에선 Brand, 어떤 청크에선 CardProduct로 뽑히면 병합 단계에서도 못 합침(라벨이 달라서). 그래서 추출 전에 정함
- 2장: 조회 대상 질문을 먼저 하는 이유는 이체 기록 예. FK 개수만 보면 관계로 흡수되어 이체 자체를 찾을 수 없게 됨
- 3장: 자동 추출 결과는 표본에 있는 것만 담는 후보임. 사람이 3단계로 줄이고 이름을 정한 뒤 GraphSchema로 고정해야 매 실행 결과가 같아짐
