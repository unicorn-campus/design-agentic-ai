# 정형 테이블에서 스키마를 도출하는 도구 4종 — PPT 스크립트

- 산출물: `temp/schema-tools/스키마도출도구.pptx` (1장)
- 작성: 클로니(직접 확인), 지식니(1차 조사), 2026-10-14
- 위치: 「그래프 스키마 도출」 덱 3장(정형 테이블 변환 규칙) 뒤에 넣을 장표
- 대상 도구(사용자 지정): Aura Import, Data Importer, Data Modeling MCP, apoc.model.jdbc
- 스타일: `references/pptx-guide.md` — `내용_단쪽`, Pretendard, 14pt 이상, 가운뎃점 대신 뜻을 씀(5절)
- 출처 링크는 사용자 요청으로 장표 카드마다 넣음(누르면 열리는 링크)

## v2 변경(2026-10-14, 사용자 결정)

- RDB에 직접 연결해 테이블 구조를 분석하는 도구는 Aura Import와 apoc.model.jdbc 두 가지뿐이라는 사용자 지적에 따라 두 도구만 남김.  
  Data Importer(CSV 머리글만 읽음), Data Modeling MCP(DB에 붙지 않음)는 뺌. 같은 일을 하던 Neo4j ETL Tool은 2022-11 이후 멈춰 제외
- 제목: '1. 스키마 도출: RDB에 연결해 스키마를 설계하는 도구 2종'
- 리드문: 'RDB 테이블을 직접 분석하는 도구는 둘뿐 — Aura Import는 후보 모델까지, apoc.model.jdbc는 원본 구조까지 만들어 줌'
- 좌우 카드: 머리 띠(이름, 꼬리표 2개) → 단계 흐름 5칸 → 분석 방법, 결과물, 연결 대상, 로컬 Neo4j, 주의 또는 코드, 상태 → 출처 링크
  - Aura Import 단계: 데이터 원천 연결 → 모델 생성(자동 또는 AI) → 사람이 검토, 수정 → 매핑, 인덱스와 제약 → 가져오기 실행  
    (공식 문서 목차 Data provision, Model data, Map data, Indexes and constraints, Run the import와 같은 순서)
  - apoc.model.jdbc 단계: JDBC로 RDB 연결 → 테이블, 열, FK 읽기 → nodes, relationships → 변환 규칙 ①~④ 적용 → 사람이 확정
  - apoc.model.jdbc 코드: `CALL apoc.model.jdbc('jdbc:postgresql://localhost:5432/app', {schema: 'public',  
    credentials: {user: $user, password: $pw}, filters: {tables: ['^tmp_.*']}}) YIELD nodes, relationships`  
    (credentials 설정은 공식 문서 예시와 같은 꼴, 실행은 아직 안 해 봄)
- 아래 띠(우리 환경, CE 로컬): Aura Import는 쓸 수 없음 / apoc.model.jdbc로 구조 읽기 → 변환 규칙 ①~④ 스크립트로 초안 →  
  사람이 확정(조회 대상, 이름) → GraphSchema 파일로 고정
- 출처 링크 4개: Aura Import 문서, 공식 블로그, APOC Database Modeling 문서, GitHub neo4j-apoc-procedures

## 확인한 사실(2026-10-14, 원문 직접 확인)

| 도구 | 사실 | 출처 |
|------|------|------|
| Aura Import | PostgreSQL, MySQL, SQL Server, Oracle, BigQuery, Databricks, Redshift, Snowflake, Azure Synapse, AWS S3, Azure Blob, Google Cloud Storage, CSV에서 코드 없이 가져옴. 인덱스와 제약을 만듦 | https://neo4j.com/docs/aura/import/introduction/ |
| Aura Import | 테이블의 PK와 FK로 모델을 자동 생성, 키가 없으면 'Generate with AI'로 키를 추정해 모델 생성. AI 모델은 의도와 맞는지 검토하라고 안내 | https://neo4j.com/blog/auradb/auradb-direct-import/ (2025-03-26) |
| Aura Import | 적재 대상은 Aura 인스턴스. 현행 문서에는 AI 모델 생성 언급이 없음(블로그 기준) | 위 두 출처 |
| Data Importer | UI 도구, flat file(CSV, TSV, 머리글 행 필수)만 받음. 단독판은 자기관리 Neo4j 대상, data-importer.neo4j.io. graphapp.io 판은 localhost에만 비보안 연결 허용 | https://neo4j.com/docs/data-importer/current/introduction/ , https://neo4j.com/docs/data-importer/current/file-provision/ |
| Data Importer | 에디션(Community 가능 여부) 조건은 문서에 없음 → 장표에는 '자기관리 Neo4j 대상'까지만 | 위 출처 |
| Data Modeling MCP | 도구: validate_data_model, get_mermaid_config_str, load_from_arrows_json, export_to_neo4j_graphrag_pkg_schema, get_constraints_cypher_queries, get_node_cypher_ingest_query 등. uvx로 실행 | https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-data-modeling (README, `.temp/mcp_datamodel_readme.md`) |
| Data Modeling MCP | PyPI 0.8.2(2025-12-22), 저장소 MIT, 마지막 푸시 2026-09-09 | PyPI JSON, GitHub API |
| apoc.model.jdbc | APOC Extended 프로시저. `apoc.model.jdbc('key or url', {schema, write, filters: {tables, views, columns}}) YIELD nodes, relationships`. filters는 정규식으로 제외 | https://neo4j.com/apoc/2026/database-integration/database-modeling/ |
| apoc.model.jdbc | 저장소 neo4j-contrib/neo4j-apoc-procedures(Apache-2.0, 마지막 푸시 2026-10-09). 시험용 이미지에는 APOC Core만 들어 있음(labs/apoc-2026.09.0-core.jar) | GitHub API, 시험 컨테이너 확인 |
| apoc.model.jdbc | 결과 모양(라벨, 관계 이름)은 문서에 그림으로만 있어 글로 확인 못 함 → 장표에 쓰지 않음 | — |

## 슬라이드 1 — 1. 스키마 도출: 정형 테이블에서 스키마를 도출하는 도구 4종

- 리드문: 모델을 자동으로 그려 주는 도구는 Aura 전용 — 로컬 Neo4j는 구조 읽기와 검증 도구를 이어 붙여 반자동으로 함
- 도형: 2 × 2 카드(머리 띠에 이름과 꼬리표 2개: LLM 사용 여부, 로컬 CE 사용 가능 여부) / 카드 안 5줄(하는 일, 입력 → 출력, 로컬 Neo4j,  
  상태, 출처 링크) / 아래 띠: 추천 조합 칩 흐름 4칸

| 도구 | 하는 일 | 입력 → 출력 | 로컬 Neo4j | 상태 | 출처 |
|------|---------|-------------|------------|------|------|
| Aura Import | PK와 FK로 그래프 모델 자동 생성, 키가 없으면 'Generate with AI'로 추정. 인덱스와 제약도 만듦 | RDB 등 12종과 CSV → Aura 인스턴스 | 못 씀(적재 대상이 Aura) | 운영 중. AI 생성은 2025-03 블로그 기준 | 문서, 블로그 |
| Data Importer(단독판) | 화면에서 파일을 모델에 매핑해 적재. 모델은 사람이 그림 | CSV, TSV 파일 → 자기관리 Neo4j | 됨. RDB는 CSV로 내보낸 뒤 사용 | 운영 중(2026 문서) | 문서, 앱 |
| Data Modeling MCP | 에이전트가 만든 모델을 검증하고, 제약과 적재 Cypher 생성, neo4j-graphrag 스키마로 변환 | 모델 JSON, Arrows → 검증 결과, Mermaid, Cypher, GraphSchema | 됨(uvx 로컬 실행, DB 연결 불필요) | 유지 중(0.8.2, 2026-09 갱신, MIT) | GitHub |
| apoc.model.jdbc | JDBC로 테이블, 열, FK 구조를 읽어 그래프로 돌려줌. 최종 모델이 아니라 원본 구조 | JDBC URL → nodes, relationships | 됨(APOC Extended와 JDBC 드라이버 따로 설치) | 유지 중(2026 문서, Apache-2.0) | 문서, GitHub |

- 아래 띠(추천 조합, Neo4j CE 로컬): apoc.model.jdbc로 구조 읽기 → 변환 규칙 ① ~ ④ 스크립트 → 사람이 확정(조회 대상, 이름) →  
  Data Modeling MCP로 검증하고 GraphSchema로 변환

### 발표자 노트

- 모델까지 자동으로 그려 주는 것은 Aura Import뿐이며 대상이 Aura 클라우드라 로컬 Community에서는 못 씀
- Data Importer는 파일 전용이라 RDB 테이블은 CSV로 내보내야 하고, 모델은 사람이 화면에서 그림
- 로컬에서는 apoc.model.jdbc가 구조를 읽고, 변환 규칙을 스크립트로 적용한 초안을 사람이 확정한 뒤, Data Modeling MCP로 검증하고  
  neo4j-graphrag의 GraphSchema로 바꿈
- AI가 만든 모델은 의도와 맞는지 반드시 검토하라고 Neo4j도 안내함
