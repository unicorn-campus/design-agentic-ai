# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)

- 모델: Groq `openai/gpt-oss-120b`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 20261018
- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 3건 0개면 멈춤, 층 상한 30건

## consult_log

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 상담 전체(세그먼트 균형) | 48 | 12 | 30 | 상한 30건 |

- 호출 30건, 성공 30건, 실패 0건
- 노드 타입 후보 10개, 관계 후보 10개

노드 타입 후보(제안한 청크 수 순): Transaction(30), ContactPreference(30), Issue(26), Consultation(21), Customer(20), Card(10), Menu(3), PaymentMethod(3), Agent(2), OrderMethod(1)

관계 후보(제안한 청크 수 순): INTERACTS_WITH(30), HAS_TRANSACTION(30), HAS_PREFERENCE(30), HAS_ISSUE(26), HAS_CONSULTATION(24), FOLLOW_UP(19), HAS_CARD(17), USES_MENU(3), HAS_PAYMENT_METHOD(3), HAS_ORDER_METHOD(1)

자주 나온 패턴 상위 10: (Consultation)-[FOLLOW_UP]->(Consultation) 18; (Consultation)-[HAS_PREFERENCE]->(ContactPreference) 17; (Consultation)-[HAS_TRANSACTION]->(Transaction) 16; (Consultation)-[HAS_ISSUE]->(Issue) 15; (Customer)-[HAS_PREFERENCE]->(ContactPreference) 14; (Customer)-[HAS_CONSULTATION]->(Consultation) 13; (Customer)-[HAS_TRANSACTION]->(Transaction) 12; (Customer)-[HAS_ISSUE]->(Issue) 8; (Card)-[HAS_TRANSACTION]->(Transaction) 7; (Customer)-[HAS_CARD]->(Card) 5

