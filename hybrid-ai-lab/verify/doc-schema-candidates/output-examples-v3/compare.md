# 상담 이력 스키마 후보 비교

- 상담ID 순서가 첫 폴더와 같음: output-examples True, output-examples-v3 True

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

