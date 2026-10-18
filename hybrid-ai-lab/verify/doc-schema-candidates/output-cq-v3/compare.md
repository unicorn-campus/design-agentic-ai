# 상담 이력 스키마 후보 비교

- 상담ID 순서가 첫 폴더와 같음: output-examples True, output-examples-v3 True, output-cq-v2 True, output-cq-v3 True

## output-examples (호출 30, 성공 29)

- 노드 타입 14개, 관계 26개
- 핵심 노드 타입: Transaction(29), Customer(20), Request(20), Consultation(19), Channel(19), ContactPreference(15), Record(14), Card(11)
- 핵심 관계: INCLUDES(27), HANDLES(24), HAS_RECORD(22), HAS_REQUEST(20), MAKES_REQUEST(19), HAS_PREFERENCE(19), INITIATES(18), REQUESTS_CHANNEL(13), APPLIES_TO(12), FOR_CARD(10), INVOLVES(8)
- 업무 핵심 개념에 해당하는 이름(나온 건수):
  - 불만 원인: 없음
  - 제안: 없음
  - 수용과 거절: 없음
  - 보류와 재검토: 없음

## output-examples-v3 (호출 30, 성공 30)

- 노드 타입 38개, 관계 43개
- 핵심 노드 타입: Customer(24), Transaction(21), CommunicationMethod(16), Consultation(14), Request(8), SupportRequest(7), FollowUpMethod(6)
- 핵심 관계: INITIATES(24), HANDLES(17), RELATED_TO(17), INTERACTS_WITH(16), ASSOCIATED_WITH(12), USES(10), PREFERS_METHOD(10), OWNS(9), REQUESTS(9), TARGETS(8), REQUESTS_INFO(6), PROVIDES_INFO(6), HANDLED_BY(6), HAS_TRANSACTION(6)
- 업무 핵심 개념에 해당하는 이름(나온 건수):
  - 불만 원인: 없음
  - 제안: 없음
  - 수용과 거절: Response(1)
  - 보류와 재검토: 없음

## output-cq-v2 (호출 30, 성공 29)

- 노드 타입 7개, 관계 8개
- 핵심 노드 타입: Transaction(29), Request(25), Customer(24), Consultation(22), Channel(21)
- 핵심 관계: HAS_CONSULTATION(29), CONDUCTS(29), DISCUSSES(29), INCLUDES(29), FOLLOWS(22), USES_CHANNEL(21), TARGETS(17), ON_CARD(10)
- 업무 핵심 개념에 해당하는 이름(나온 건수):
  - 불만 원인: 없음
  - 제안: 없음
  - 수용과 거절: 없음
  - 보류와 재검토: 없음

## output-cq-v3 (호출 30, 성공 30)

- 노드 타입 10개, 관계 10개
- 핵심 노드 타입: Transaction(30), ContactPreference(30), Issue(26), Consultation(21), Customer(20), Card(10)
- 핵심 관계: INTERACTS_WITH(30), HAS_TRANSACTION(30), HAS_PREFERENCE(30), HAS_ISSUE(26), HAS_CONSULTATION(24), FOLLOW_UP(19), HAS_CARD(17)
- 업무 핵심 개념에 해당하는 이름(나온 건수):
  - 불만 원인: HAS_ISSUE(26), Issue(26)
  - 제안: 없음
  - 수용과 거절: 없음
  - 보류와 재검토: 없음

