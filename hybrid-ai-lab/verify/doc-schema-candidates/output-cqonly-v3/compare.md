# 상담 이력 스키마 후보 비교

- 상담ID 순서가 첫 폴더와 같음: output-examples-v3 True, output-cq-v3 True, output-cqonly-v3 True

## output-examples-v3 (호출 30, 성공 30)

- 노드 타입 38개, 관계 43개
- 핵심 노드 타입: Customer(24), Transaction(21), CommunicationMethod(16), Consultation(14), Request(8), SupportRequest(7), FollowUpMethod(6)
- 핵심 관계: INITIATES(24), HANDLES(17), RELATED_TO(17), INTERACTS_WITH(16), ASSOCIATED_WITH(12), USES(10), PREFERS_METHOD(10), OWNS(9), REQUESTS(9), TARGETS(8), REQUESTS_INFO(6), PROVIDES_INFO(6), HANDLED_BY(6), HAS_TRANSACTION(6)
- 업무 핵심 개념에 해당하는 이름(나온 건수):
  - 불만 원인: 없음
  - 제안: 없음
  - 수용과 거절: Response(1)
  - 보류와 재검토: 없음

## output-cq-v3 (호출 30, 성공 30)

- 노드 타입 10개, 관계 10개
- 핵심 노드 타입: Transaction(30), ContactPreference(30), Issue(26), Consultation(21), Customer(20), Card(10)
- 핵심 관계: INTERACTS_WITH(30), HAS_TRANSACTION(30), HAS_PREFERENCE(30), HAS_ISSUE(26), HAS_CONSULTATION(24), FOLLOW_UP(19), HAS_CARD(17)
- 업무 핵심 개념에 해당하는 이름(나온 건수):
  - 불만 원인: Issue(26), HAS_ISSUE(26)
  - 제안: 없음
  - 수용과 거절: 없음
  - 보류와 재검토: 없음

## output-cqonly-v3 (호출 30, 성공 30)

- 노드 타입 53개, 관계 106개
- 핵심 노드 타입: Customer(29), Request(20), Transaction(18), Consultation(12), TransactionSummary(10), Agent(7), Conversation(6)
- 핵심 관계: INCLUDES(9), PARTICIPATES_IN(9), MAKES_REQUEST(7), HANDLES(7), FOLLOWS(7), REFERS_TO(7)
- 업무 핵심 개념에 해당하는 이름(나온 건수):
  - 불만 원인: Issue(5), HAS_ISSUE(3), Complaint(2), CardIssuer(1), CUSTOMER_HAS_COMPLAINT(1)
  - 제안: SUGGESTS(2), Proposal(2), SUGGESTS_ALTERNATIVE(1), MAKES_PROPOSAL(1), PROVIDES_PROPOSAL(1)
  - 수용과 거절: Response(2), PROVIDES_RESPONSE(1), RESPONSE_USES_CHANNEL(1), RESPONSE_TO_REQUEST(1), REJECTS_CHANGE(1), HAS_RESPONSE(1)
  - 보류와 재검토: Condition(2), REFERS_TO_CONDITION(1), HAS_CONDITION(1)

