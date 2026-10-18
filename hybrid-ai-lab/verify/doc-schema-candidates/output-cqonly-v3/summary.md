# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)

- 모델: Groq `openai/gpt-oss-120b`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 20261018
- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 3건 0개면 멈춤, 층 상한 30건

## consult_log

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 상담 전체(세그먼트 균형) | 48 | 12 | 30 | 상한 30건 |

- 호출 30건, 성공 30건, 실패 0건
- 노드 타입 후보 53개, 관계 후보 106개

노드 타입 후보(제안한 청크 수 순): Customer(29), Request(20), Transaction(18), Consultation(12), TransactionSummary(10), Agent(7), Conversation(6), Issue(5), Card(4), Record(4), Counselor(3), CommunicationChannel(3), Menu(2), FollowUp(2), Proposal(2), Complaint(2), Preference(2), Condition(2), Response(2), Address(2), Order(2), Session(1), ContactPreference(1), WarrantyRequest(1), Seller(1), Product(1), Notification(1), ServiceChannel(1), Discount(1), Application(1), CommunicationMethod(1), Department(1), NotificationItem(1), Channel(1), PaymentMethod(1), Inquiry(1), CardIssuer(1), Message(1), ContactMethod(1), Receipt(1), Item(1), Category(1), BillingPeriod(1), Statement(1), Period(1), TransactionBatch(1), CommunicationPreference(1), Document(1), CardApplication(1), MerchantCategory(1), Store(1), CancellationRequest(1), Branch(1)

관계 후보(제안한 청크 수 순): INCLUDES(9), PARTICIPATES_IN(9), HANDLES(7), MAKES_REQUEST(7), FOLLOWS(7), REFERS_TO(7), MAKES(5), HAS_CONSULTATION(5), HAS_PREFERENCE(4), INTERACTS_WITH(4), HAS_REQUEST(4), ADDRESSES(3), INITIATES(3), HAS_SUMMARY(3), HAS_ISSUE(3), HANDLED_BY(3), SUGGESTS(2), RESPONDS(2), USES(2), OWNS(2), TARGETS(2), CONNECTS_TO(2), RELATED_TO(2), INCLUDES_TRANSACTION(2), RESPONDS_TO(2), HAS_TRANSACTION(2), CONDUCTS(2), GENERATES(2), REFERENCES(2), PREVIOUS_SESSION(1), COUNSELOR_IN(1), HAS_SESSION(1), GUIDES(1), SOLD_BY(1), INVOLVES(1), CONTAINS(1), HAS_TRANSACTION_SUMMARY(1), TARGETS_CHANNEL(1), TARGETS_NOTIFICATION(1), ADDRESSES_REQUEST(1), MAKES_PROPOSAL(1), PROVIDES_GUIDANCE(1), PREFERS_METHOD(1), USES_METHOD(1), HAS_DISCOUNT(1), REJECTS_CHANGE(1), SUGGESTS_ALTERNATIVE(1), REPORTS(1), PREFERS(1), HAS_CUSTOMER(1), SENT_VIA(1), HAS_RECORD(1), CONTINUES_FROM(1), COMPARES(1), INCLUDES_REQUEST(1), REFERENCES_TRANSACTION(1), MAKES_INQUIRY(1), PROVIDES_PROPOSAL(1), REFERS_TO_RECORD(1), CONTINUES_WITH(1), HAS_CONDITION(1), SENT_BY(1), CONSULTED_WITH(1), HAS_ITEM(1), BELONGS_TO(1), USES_CARD(1), HAS_RECEIPT(1), USES_CONTACT_METHOD(1), HAS_RESPONSE(1), REFERS_TO_TRANSACTION(1), CONTINUES(1), REFERS_TO_CONDITION(1), REFERS_TO_CARD(1), SPECIFIES(1), HAS_BATCH(1), LINKED_TO(1), HAS_ADDRESS(1), RELATES_TO(1), MADE_APPLICATION(1), USES_ADDRESS(1), ASSOCIATED_WITH(1), MENTIONS(1), ADDRESSED_BY(1), MADE_BY(1), REQUEST_HAS_FOLLOWUP(1), CARD_HAS_TRANSACTION(1), TRANSACTION_IN_CATEGORY(1), MADE_REQUEST(1), HAS_CARD(1), DISCUSSES(1), REQUEST_REFERS_TRANSACTION(1), CUSTOMER_HAS_COMPLAINT(1), PROVIDES_RESPONSE(1), REQUEST_REFERS_RECORD(1), INTERACTION(1), RECORD_FOLLOWS(1), MADE(1), INCLUDES_SUMMARY(1), TARGETS_ADDRESS(1), AT_BRANCH(1), REQUEST_RELATES_TO_ORDER(1), RESPONDS_WITH(1), RESPONSE_TO_REQUEST(1), REQUEST_HAS_TRANSACTION(1), RESPONSE_USES_CHANNEL(1), REQUEST_USES_CHANNEL(1)

자주 나온 패턴 상위 10: (Customer)-[MAKES_REQUEST]->(Request) 6; (Customer)-[PARTICIPATES_IN]->(Consultation) 5; (Customer)-[MAKES]->(Request) 4; (Customer)-[HAS_CONSULTATION]->(Consultation) 4; (Customer)-[PARTICIPATES_IN]->(Conversation) 3; (Consultation)-[HAS_REQUEST]->(Request) 3; (Consultation)-[FOLLOWS]->(Consultation) 3; (Consultation)-[INCLUDES]->(Transaction) 2; (Request)-[TARGETS]->(Card) 2; (Consultation)-[HAS_ISSUE]->(Issue) 2

