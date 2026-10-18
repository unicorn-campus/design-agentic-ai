# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)

- 모델: Groq `openai/gpt-oss-120b`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 20261018
- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 3건 0개면 멈춤, 층 상한 30건

## consult_log

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 상담 전체(세그먼트 균형) | 48 | 12 | 30 | 상한 30건 |

- 호출 30건, 성공 29건, 실패 1건
- 노드 타입 후보 7개, 관계 후보 8개

노드 타입 후보(제안한 청크 수 순): Transaction(29), Request(25), Customer(24), Consultation(22), Channel(21), Card(4), Consultant(2)

관계 후보(제안한 청크 수 순): INCLUDES(29), HAS_CONSULTATION(29), CONDUCTS(29), DISCUSSES(29), FOLLOWS(22), USES_CHANNEL(21), TARGETS(17), ON_CARD(10)

자주 나온 패턴 상위 10: (Consultation)-[DISCUSSES]->(Transaction) 22; (Consultation)-[FOLLOWS]->(Consultation) 21; (Consultation)-[INCLUDES]->(Request) 19; (Customer)-[HAS_CONSULTATION]->(Consultation) 17; (Consultation)-[USES_CHANNEL]->(Channel) 16; (Request)-[TARGETS]->(Transaction) 14; (Transaction)-[ON_CARD]->(Card) 4; (Consultant)-[CONDUCTS]->(Consultation) 2; (Request)-[TARGETS]->(Card) 1

