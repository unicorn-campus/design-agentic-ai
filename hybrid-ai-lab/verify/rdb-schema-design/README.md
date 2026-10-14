# RDB 구조 읽기(apoc.model.jdbc) 시험

정형 테이블에서 그래프 스키마를 도출하는 흐름의 1단계: `apoc.model.jdbc`로 RDB 구조를 읽어 다음 단계(바이브 코딩 툴 프롬프트)의
입력 형식을 확정함. 기존 indexer, retriever, rdb 코드는 고치지 않고, DB는 읽기 전용으로만 조회함.

## 구성

| 파일 | 하는 일 |
|------|---------|
| `tools/run_apoc_model.py` | 시험용 Neo4j에서 `apoc.model.jdbc` 실행 → `output/apoc_model.json`(계정 값은 저장 안 함, `write: false`) |
| `tools/export_fk_constraints.py` | `pg_constraint`에서 FK 제약을 제약 단위로 뽑음 → `output/fk_constraints.json` |
| `tools/render_structure.py` | 두 결과를 합쳐 원본 구조를 그림 → `raw_structure.mmd`(Mermaid), `raw_structure.puml`(PlantUML), `structure_input.json`(다음 단계 입력) |

## 실행 환경(2026-10-14)

- APOC Extended 최신판이 2026.04.0이라 Neo4j 2026.09에서는 `apoc.model.jdbc`가 실패함(Woodstox XML 라이브러리 없음).  
  그래서 구조 읽기 전용으로 버전이 맞는 컨테이너를 따로 띄움
- 받은 파일: `apoc-2026.04.0-extended.jar`(GitHub 릴리스 SHA-256 일치), `postgresql-42.7.7.jar`(Maven SHA-1 일치),  
  이미지 `neo4j:2026.04.0-community`

```bash
docker run -d --name verify-neo4j-apoc -p 27474:7474 -p 27687:7687 -e NEO4J_AUTH=neo4j/verify-neo4j-pass -e NEO4J_PLUGINS='["apoc"]' -e SC_WITHOUT_DATABASE_PLUGIN=postgresql -v {플러그인 폴더}:/plugins neo4j:2026.04.0-community
```

- `{플러그인 폴더}`에는 위 두 jar를 넣음. `SC_WITHOUT_DATABASE_PLUGIN=postgresql`이 없으면 SchemaCrawler가  
  'PostgreSQL용 데이터베이스 플러그인을 넣으라'며 실패함(플러그인 대신 환경변수로 해결, 추가 다운로드 없음)
- DB 계정은 관리 계정 `cardlab`(원본 테이블 구조를 읽어야 하므로, `rdb/README.md` 접속 정보 참조). 값은 환경변수로만 넘김

## 결과(hybrid-ai-lab-rdb, public 스키마)

- `apoc.model.jdbc`: 노드 45개(Schema 1, Table 8, Column 36), 관계 44개(IN_SCHEMA 8, IN_TABLE 36). 실제 DB의 BASE TABLE 8개와 같음
- **FK 대상이 없음**: FK 열에 `ForeignKey` 라벨만 붙고, 가리키는 테이블과 열을 잇는 관계나 속성이 없음
- **복합 FK**: `card (product_id, brand) → product_annual_fee`는 열 2개, 제약 1개. FK 열은 7개, FK 제약은 6개  
  → 변환 규칙의 'FK 개수'는 **제약 수**로 세야 함. 그래서 `pg_constraint`로 보강함
- `information_schema`를 단순 조인하면 복합 FK의 열 짝이 엇갈려 곱해짐 → `pg_constraint`의 conkey와 confkey를 순서대로 짝지음
- 테이블별 FK 제약 수: card 2, card_txn 2, delinquency 1, product_annual_fee 1, 나머지(lab_metadata, member, merchant, product) 0
- Mermaid 그림은 내장 브라우저에서 그려 문법을 확인함(`output/raw_structure_preview.html`). PlantUML은 Java가 없어 그려 보지 못함

## 그래프 스키마 초안(2026-10-14)

- `decisions.json`: 사람이 정한 값만 모음 — 규칙 ① 판정(card_txn = 노드), 제외 표(lab_metadata), 한국어 노드 이름, 관계 이름과 방향(후보)
- `tools/draft_schema.py`: 규칙 ②③④ 자동 적용 → `schema_draft.json`(GraphSchema 입력) → `schema.mmd`, `schema.puml`
  - 다른 표가 가리키는 표는 노드(관계는 FK 대상이 될 수 없음) → card는 FK 2개 + 업무 열이지만 자동으로 노드
  - FK 열은 관계로 바꾼 뒤 노드 속성에서 지움. 키(PK)에 들어가는 FK 열(연체의 member_id 등)은 남김
  - 제약은 Community에서 되는 UNIQUENESS로만 만듦(복합 키 포함)
- 결과: 노드 타입 7, 관계 6, 패턴 6, 제약 7. GraphSchema 검증 통과, 같은 라벨 중복 없음. Mermaid는 브라우저에서 그려 확인(`schema_mermaid.jpg`)
- `GraphSchema.model_validate()`는 넘겨준 dict의 patterns를 Pattern 객체로 바꿔 놓아서 사본으로 검증함(neo4j-graphrag 1.22.0)

## 한계

- PostgreSQL에서만 시험함. `SC_WITHOUT_DATABASE_PLUGIN`은 SchemaCrawler의 DB별 플러그인 없이 일반 JDBC 메타데이터만 쓰는 설정임
- 뷰는 결과에 들어오지 않음(BASE TABLE만)
