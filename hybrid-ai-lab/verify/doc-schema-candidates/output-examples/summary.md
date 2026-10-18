# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)

- 모델: Groq `openai/gpt-oss-120b`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 20261018
- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 3건 0개면 멈춤, 층 상한 30건

## regulation

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 약관 전체 | 10 | 10 | 10 | 모두 봄 |

- 호출 10건, 성공 9건, 실패 1건
- 노드 타입 후보 30개, 관계 후보 52개

노드 타입 후보(제안한 청크 수 순): Member(9), Card(8), Refund(6), CardIssuer(6), Service(4), Fee(4), Transaction(4), Contract(4), Request(3), Dispute(3), Suspension(3), Merchant(3), Statement(3), Account(3), Document(2), Bank(2), Issuer(1), CardCompany(1), Point(1), CurrencyConversion(1), Limit(1), Report(1), Record(1), Objection(1), TermsChange(1), DataProcessing(1), Outsourcing(1), Termination(1), Correction(1), Loan(1)

관계 후보(제안한 청크 수 순): HAS_CARD(8), ISSUED_BY(8), INCLUDES_SERVICE(4), HAS_FEE(4), HAS_FAMILY_MEMBER(4), MAKES_TRANSACTION(4), REQUESTS_REFUND(3), PROVIDED_BY(3), HANDLES_DISPUTE(3), SUBMITS_REQUEST(3), DESCRIBES(2), TARGETS_CONTRACT(2), RAISES_DISPUTE(2), LINKED_TO(2), HAS_CONTRACT(2), TRANSACTION_AT(2), HAS_ACCOUNT(2), TERMINATED_BY(1), HAS_REFUND(1), SUBJECT_TO_SUSPENSION(1), HAS_POINT(1), WITHDRAWS_FOR(1), RECORDS_USAGE(1), ACCEPTS_CARD(1), PROCESSES(1), CONVERTED_BY(1), RECORDED_IN(1), REPORTS_FOR(1), CARD_HAS_REFUND(1), TRANSACTION_RECORDED_IN(1), SUBMITS_REPORT(1), CONTRACT_TERMINATES_REFUND(1), CARD_HAS_LIMIT(1), CARD_HAS_SUSPENSION(1), SENDS(1), RECEIVES(1), TERMINATES_CONTRACT(1), SUBMITS_OBJECTION(1), PROCESS_PERSONAL_DATA(1), HAS_SUSPENSION(1), NOTIFIES_TERMS_CHANGE(1), REQUESTS_CORRECTION(1), RECORDS(1), REINSTATED(1), OUTSOURCED_TO(1), STATEMENT_INCLUDES_TRANSACTION(1), HAS_LOAN(1), REFUND_FOR(1), CANCELS(1), HAS_STATEMENT(1), ACCOUNT_LINKED_TO_BANK(1), LOAN_REPAYMENT(1)

자주 나온 패턴 상위 10: (Member)-[HAS_CARD]->(Card) 8; (Card)-[ISSUED_BY]->(CardIssuer) 5; (Member)-[HAS_FAMILY_MEMBER]->(Member) 4; (Member)-[MAKES_TRANSACTION]->(Transaction) 4; (Member)-[SUBMITS_REQUEST]->(Request) 3; (Member)-[REQUESTS_REFUND]->(Refund) 2; (Card)-[HAS_FEE]->(Fee) 2; (Refund)-[PROVIDED_BY]->(CardIssuer) 2; (Card)-[INCLUDES_SERVICE]->(Service) 2; (Transaction)-[INCLUDES_SERVICE]->(Service) 2

## consult_log

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 상담 전체(세그먼트 균형) | 48 | 12 | 30 | 상한 30건 |

- 호출 30건, 성공 29건, 실패 1건
- 노드 타입 후보 14개, 관계 후보 26개

노드 타입 후보(제안한 청크 수 순): Transaction(29), Customer(20), Request(20), Consultation(19), Channel(19), ContactPreference(15), Record(14), Card(11), Agent(4), Preference(4), Product(2), Category(2), Statement(2), Merchant(1)

관계 후보(제안한 청크 수 순): INCLUDES(27), HANDLES(24), HAS_RECORD(22), HAS_REQUEST(20), HAS_PREFERENCE(19), MAKES_REQUEST(19), INITIATES(18), REQUESTS_CHANNEL(13), APPLIES_TO(12), FOR_CARD(10), INVOLVES(8), REFERS_TO(4), HANDLED_BY(4), RELATED_TO(4), USES_CHANNEL(3), FOR_PRODUCT(2), RESPONDS_TO(1), TARGETS(1), MAINTAINS(1), HAS(1), HAS_RECEIPT(1), CATEGORIZED_AS(1), INITIRES(1), HAS_CARD(1), FOR_CATEGORY(1), FOR_MERCHANT(1)

자주 나온 패턴 상위 10: (Request)-[INCLUDES]->(Transaction) 13; (Consultation)-[HAS_REQUEST]->(Request) 12; (Request)-[REQUESTS_CHANNEL]->(Channel) 11; (Customer)-[INITIATES]->(Consultation) 10; (Customer)-[HAS_PREFERENCE]->(ContactPreference) 9; (Consultation)-[HAS_RECORD]->(Record) 9; (Customer)-[MAKES_REQUEST]->(Request) 9; (ContactPreference)-[APPLIES_TO]->(Channel) 9; (Consultation)-[INCLUDES]->(Transaction) 8; (Transaction)-[FOR_CARD]->(Card) 7

## benefit_guide

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 공통 안내 | 4 | 4 | 4 | 모두 봄 |
| 참고 카드 | 7 | 7 | 7 | 모두 봄 |
| 카드 개요 | 64 | 10 | 30 | 상한 30건 |
| 혜택 상세 | 85 | 10 | 30 | 상한 30건 |

- 호출 71건, 성공 69건, 실패 2건
- 노드 타입 후보 13개, 관계 후보 17개

노드 타입 후보(제안한 청크 수 순): Card(65), Condition(59), Limit(58), Benefit(56), Channel(31), Fee(29), Company(18), Document(9), Account(5), Coupon(2), Offer(2), Design(2), Guardian(1)

관계 후보(제안한 청크 수 순): HAS_BENEFIT(57), HAS_LIMIT(55), HAS_CONDITION(54), HAS_FEE(29), HAS_CHANNEL(29), ISSUED_BY(18), BENEFIT_HAS_CONDITION(11), DESCRIBES(11), BENEFIT_HAS_LIMIT(6), HAS_FAMILY_CARD(4), HAS_ACCOUNT(3), BENEFIT_HAS_CHANNEL(2), TARGETS(2), HAS_DESIGN(2), PROTECTS(1), ASSOCIATED_WITH(1), HAS_COUPON(1)

자주 나온 패턴 상위 10: (Card)-[HAS_BENEFIT]->(Benefit) 53; (Benefit)-[HAS_LIMIT]->(Limit) 46; (Benefit)-[HAS_CONDITION]->(Condition) 46; (Card)-[HAS_FEE]->(Fee) 29; (Benefit)-[HAS_CHANNEL]->(Channel) 29; (Card)-[HAS_LIMIT]->(Limit) 18; (Card)-[ISSUED_BY]->(Company) 16; (Card)-[HAS_CONDITION]->(Condition) 10; (Benefit)-[BENEFIT_HAS_CONDITION]->(Condition) 10; (Document)-[DESCRIBES]->(Card) 9

