# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)

- 모델: Groq `openai/gpt-oss-120b`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 20261018
- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 3건 0개면 멈춤, 층 상한 30건

## consult_log

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 상담 전체(세그먼트 균형) | 48 | 12 | 30 | 상한 30건 |

- 호출 30건, 성공 30건, 실패 0건
- 노드 타입 후보 38개, 관계 후보 43개

노드 타입 후보(제안한 청크 수 순): Customer(24), Transaction(21), CommunicationMethod(16), Consultation(14), Request(8), SupportRequest(7), FollowUpMethod(6), TransactionBatch(5), Card(5), Agent(3), TransactionSummary(3), VirtualCard(3), Statement(3), Notification(2), CardClosureRequest(2), Address(2), OrderApp(1), Location(1), Department(1), Menu(1), NotificationCategory(1), ConsultationRecord(1), Message(1), Company(1), Category(1), Application(1), Branch(1), ContactMethod(1), Preference(1), MerchantCategory(1), Receipt(1), Store(1), Order(1), Response(1), Record(1), CancellationRequest(1), OrderMethod(1), Consultant(1)

관계 후보(제안한 청크 수 순): INITIATES(24), RELATED_TO(17), HANDLES(17), INTERACTS_WITH(16), ASSOCIATED_WITH(12), USES(10), PREFERS_METHOD(10), REQUESTS(9), OWNS(9), TARGETS(8), PROVIDES_INFO(6), REQUESTS_INFO(6), HANDLED_BY(6), HAS_TRANSACTION(6), GUIDED_BY(4), PREFERS_CHANNEL(3), RECEIVES(3), HAS_SUMMARY(2), PREFERRED_METHOD(2), HAS_RECEIPT(2), HAS_CARD(2), HAS_BATCH(1), PREFERS(1), FAVORS(1), PROCESSED_BY(1), SENT_BY(1), GUIDES(1), MODIFIES(1), ASSIGNS_DELIVERY_ADDRESS(1), HAS_APPLICATION(1), HAS_CONSULTATION(1), HAS_STATEMENT(1), HAS_PREFERENCE(1), MAKES_REQUEST(1), INCLUDES(1), PLACED_ORDER(1), OCCURS_AT(1), PROVIDES(1), HAS_RECORD(1), BELONGS_TO(1), GENERATED(1), HAS_ADDRESS(1), USES_METHOD(1)

자주 나온 패턴 상위 10: (Customer)-[INITIATES]->(SupportRequest) 6; (Customer)-[INITIATES]->(Request) 6; (Customer)-[PREFERS_METHOD]->(CommunicationMethod) 6; (Consultation)-[RELATED_TO]->(Transaction) 6; (Customer)-[INITIATES]->(Consultation) 5; (SupportRequest)-[RELATED_TO]->(TransactionBatch) 3; (Customer)-[PREFERS_CHANNEL]->(CommunicationMethod) 3; (Request)-[USES]->(CommunicationMethod) 3; (Customer)-[INTERACTS_WITH]->(Agent) 2; (Customer)-[REQUESTS_INFO]->(Transaction) 2

