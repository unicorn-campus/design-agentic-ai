# GraphRAG 그래프 스키마

GraphRAG 인덱서가 지식 그래프(KG)를 만들 때 따르는 그래프 스키마 모음.  
데이터 출처(정형 테이블, 비정형 문서)마다 하위 폴더를 따로 두고, 각 폴더가 설계 프롬프트의 `{base_dir}` 역할을 함.

## 폴더 구조

```text
schema/
├── README.md                  # 이 문서
├── rdb/                       # 정형 테이블 → KG 스키마 (prompts/design-kg-schema-rdb.md)
│   ├── graph_schema.json      # 최종 그래프 스키마 (인덱서가 읽는 파일)
│   ├── approval.json          # 승인 기록
│   ├── decisions.json         # 사람의 결정 기록
│   ├── output/                # 중간 산출물 (DB 구조, 판정표, 초안, 그림)
│   ├── tools/                 # 설계 도구 (read_catalog.py, draft_schema.py)
│   ├── requirements.txt
│   └── .venv/                 # 가상환경 (git 제외, 아래 「가상환경」 참고)
└── doc/                       # 비정형 문서 → KG 스키마 (prompts/design-kg-schema-doc.md)
    ├── competency_questions.md    # 역량 질문 (문서 종류 공통)
    ├── sample_plan.json           # 표본 계획 (문서 종류 공통)
    ├── decisions.json             # 사람의 결정 기록 (문서 종류 공통)
    ├── pass_criteria.json         # 합격 기준
    ├── RESULT.md                  # 실행 결과 요약
    ├── output/                    # 공통 중간 산출물과 실행 로그
    ├── tools/                     # 설계 도구 (후보 추출, 스키마 작성, 채움 시험, 확정)
    ├── benefit_guide/             # 문서 종류별 폴더: 혜택 안내서
    ├── consult_log/               # 문서 종류별 폴더: 상담 기록
    ├── regulation/                # 문서 종류별 폴더: 약관과 규정
    ├── requirements.txt
    └── .venv/
```

- 정형과 비정형을 같은 폴더에 두지 않는 이유: 두 프롬프트 모두 `{base_dir}` 바로 아래에 `decisions.json`,  
  `output/`, `tools/`를 만들어 한 폴더에 두면 파일이 서로 덮어써짐
- 문서 종류별 폴더 안에는 `graph_schema.json`, `approval.json`, `expected_answers.json`, `schema_spec.json`,  
  `output/`(후보, 초안, 채움 시험 결과)이 있음

## 최종 스키마 현황

| 출처 | 파일 | 노드 타입 | 관계 | 패턴 | 승인 |
|------|------|----------|------|------|------|
| 정형 테이블 | `rdb/graph_schema.json` | 7 | 6 | 6 | hiondal, 2026-10-14 |
| 혜택 안내서 | `doc/benefit_guide/graph_schema.json` | 5 | 4 | 4 | 자동 승인, 2026-10-18 |
| 상담 기록 | `doc/consult_log/graph_schema.json` | 4 | 4 | 4 | 자동 승인, 2026-10-18 |
| 약관과 규정 | `doc/regulation/graph_schema.json` | 5 | 4 | 4 | **합격 기준 미달 상태로 확정**, 2026-10-19 |

- 숫자는 `GraphSchema.from_file()`로 다시 읽어 센 값 (2026-10-19)
- 비정형 스키마는 사람 승인이 아닌 자동 승인 상태임. 인덱싱에 쓰기 전에 사람이 검토하고 승인해야 함
- 약관은 채움 시험 라운드 3에서 R1만 통과하고 R2 ~ R5가 미달인 초안을 사용자 요청으로 현재 수준 그대로 확정함.  
  `approval.json`의 `below_criteria`에 미달 질문(R2, R3, R4, R5)과 사유를 남김. 스키마 설명을 보완해 다시 시험해야 함
  - 노드: TermsDocument, Clause, Requirement, Deadline, Handling / 관계: HAS_CLAUSE, SETS_REQUIREMENT, SETS_DEADLINE, DEFINES_HANDLING
  - 약관만 추출 단위 규칙(조항 제목 줄로 나눔)이 있어 `approval.json`의 `extraction_unit_rule`에 함께 남김
- `doc/tools/finalize.py`는 기본적으로 미달이면 멈춤. 미달 상태로 확정하려면 `--accept-below=사유`를 줘야 하고,  
  그 사유가 승인 기록에 남음(verify 원본 도구에는 이 옵션이 없음)
- 인덱서는 출처마다 `graph_schema.json`을 따로 읽음. 어떤 스키마를 어디까지 적재할지는 인덱싱 단계에서 정함

## 가상환경

폴더마다 필요한 패키지가 달라 가상환경을 따로 둠.

| 폴더 | 패키지 | 이유 |
|------|--------|------|
| `rdb/` | `psycopg[binary]`, `neo4j-graphrag` | DB 카탈로그 조회와 스키마 저장 |
| `doc/` | `neo4j-graphrag` | 후보 추출과 채움 시험. LLM 호출은 표준 라이브러리(urllib)로 함 |

다시 만들 때는 해당 폴더에서 아래처럼 실행함.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

## 주의 사항

- `doc/`은 `verify/doc-schema-prompt-run/`의 복사본임 (2026-10-19 복사). 실험 원본은 verify에 그대로 남아 있음
- `doc/decisions.json`에 적힌 경로(`base_dir`, `structured_schema` 등)는 실행 당시 경로임.  
  승인 기록의 해시가 이 파일을 가리키므로 고치지 않았음. 정형 스키마의 현재 위치는 `rdb/graph_schema.json`
- 도구 스크립트는 자기 위치 기준으로 폴더를 찾으므로 폴더째 옮겨도 그대로 동작함
- 승인 기록의 입력 파일 해시가 지금 파일과 다름 (옮기기 전부터 있던 상태)
  - `rdb/`: `output/structure.json`이 승인(10-14 18:00) 뒤에 다시 만들어짐(10-14 21:57)
  - `doc/`: 공통 파일(`competency_questions.md`, `sample_plan.json`, `decisions.json`)이  
    문서 종류별 승인 뒤 다른 문서 종류를 진행하며 바뀜. 문서 종류별 `expected_answers.json`은 일치함
  - 인덱싱에 쓰기 전에 다시 승인해 해시를 맞추는 것을 권장함
