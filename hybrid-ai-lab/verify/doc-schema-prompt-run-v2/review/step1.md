# 1단계 승인: 사용자 입력값

- 승인할 것: 문서 스키마 설계에 쓸 입력 파일, 칸, LLM, 도구와 개인정보 점검 결과
- 승인하면: 2단계에서 이 입력값으로 역량 질문 초안을 만듦

## 입력값

| 입력 | 추천값 | 근거 | 이전 실행과 다른 곳 |
|---|---|---|---|
| 출력 기준 폴더 | `hybrid-ai-lab/verify/doc-schema-prompt-run-v2` | 지금 인덱서가 쓰는 스키마 `indexer/graphrag/schema/doc`를 건드리지 않음 | 새 폴더 |
| 청크 위치 파일 | `indexer/vector-bm25/data/active_generation.json` | 인덱서의 활성 세대 기록 | 같음 |
| 찾은 청크 파일 | `indexer/vector-bm25/data/artifacts/birthfix-20261018b/prepared-chunks.json` | 세대 이름 속 실행 ID와 폴더 이름이 같음. 청크 수 218개 일치 | 같음 |
| 본문 칸 | `text` | 정제 본문. `index_text`는 검색용 별칭을 덧붙인 칸이라 뺌 | 같음 |
| 문서 종류 칸 | `metadata.doc_type` | 값 3종: 약관(regulation) 10, 혜택 안내(benefit_guide) 160, 상담 기록(consult_log) 48 | 같음 |
| 설계할 문서 종류 | 세 종류 모두 | 공통 개념은 세 종류를 함께 봐야 정할 수 있음 | 같음 |
| 사용자 질문 출처 | `ragas/eval-set.json`(Q01 ~ Q25)<br/>`indexer/vector-bm25/evaluation/group2_questions.json`(E01 ~ E20)<br/>`specs/userstory.md` | 평가셋에 거시 질문 Q23 ~ Q25가 들어 있음을 확인함 | **Q23 ~ Q25 추가** |
| 정형 데이터 그래프 스키마 | `indexer/graphrag/schema/rdb/graph_schema.json` | RDB에서 만든 스키마(상품, 카드, 회원 등) | **경로 바뀜**(폴더를 rdb와 doc로 나눔) |
| 기존 정답표 | `docs/_instructor/D3/상담근거_대조표.jsonl`<br/>`docs/_instructor/D3/정제검증_기대값.json` | 상담 기록에만 있음. 약관과 혜택은 7단계에서 AI가 기대 답 초안을 씀 | 같음 |
| LLM | Groq `openai/gpt-oss-120b` | 프로젝트 공용 모델 | 같음 |
| 비밀값 | `secrets/.env`의 `GROQ_API_KEY` | 값이 있는지만 확인함(값은 보지 않음) | 같음 |
| 도구 | neo4j-graphrag 1.22.0 | `indexer/graphrag/v0/.venv`에 설치되어 있음 | 가상환경 위치 바뀜 |
| Neo4j 판 | Community(`neo4j:2026.09.0-community`) | `hybrid-ai-lab/neo4j/compose.yml`. 제약은 UNIQUENESS만 씀 | 같음 |

## 개인정보 점검(정규식)

| 항목 | 건수 |
|---|---|
| 전화번호 | 0 |
| 이메일 | 0 |
| 카드나 계좌 번호 | 0 |
| 주민번호 | 0 |
| 생년월일 | 0 |

- 남은 개인정보가 없으므로 외부 LLM으로 보내도 됨

## 함께 볼 파일

- 청크 구조와 메타데이터 분포: `hybrid-ai-lab/verify/doc-schema-prompt-run-v2/output/input_scan.json`
- 스키마 설계 프롬프트: `hybrid-ai-lab/prompts/design-kg-schema-doc.md`
