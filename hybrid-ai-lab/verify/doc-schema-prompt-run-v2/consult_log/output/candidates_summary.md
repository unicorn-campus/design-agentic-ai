# 스키마 후보 요약: consult_log

- 모델: openai/gpt-oss-120b, 추출기: neo4j-graphrag `SchemaFromTextExtractor`, examples = 역량 질문만
- 호출 30건(성공 30, 실패 0), 노드 타입 이름 57개, 관계 이름 125개

## 묶음별 멈춤

| 묶음 | 본 건수 | 멈춘 이유 |
|---|---:|---|
| D3_S01_신규가입_상담이력_합성.txt | 5 | 모두 봄 |
| D3_S02_장기보유_상담이력_합성.txt | 5 | 모두 봄 |
| D3_S03_VIP_상담이력_합성.txt | 5 | 모두 봄 |
| D3_S04_휴면직전_상담이력_합성.txt | 5 | 모두 봄 |
| D3_S05_다중카드_상담이력_합성.txt | 5 | 모두 봄 |
| D3_S06_연회비부담_상담이력_합성.txt | 5 | 모두 봄 |

## 역량 질문별로 답할 수 있어 보이는 이름(LLM 분류, 드문 이름 포함)

| 질문 | 이름 |
|---|---|
| C1 | Issue, Concern, Request |
| C2 | Proposal, Guidance, Response |
| C3 | Response, Interaction, Preference |
| C4 | Preference, Comparison, WaiverCondition |
| C5 | Consultation, ConsultationSession, Conversation, Record |
| X1 | Request, Benefit, Card, CardTier |
| X2 | Benefit, Card |
| A1 | Customer, Issue, Concern, Request |
| A2 | Proposal, Response |

## 노드 타입 이름별 나온 청크 수와 자주 나온 속성

| 노드 타입 | 청크 수 | 속성(나온 수) |
|---|---:|---|
| Transaction | 21 | count(18), total_amount(18), date(10), month(9), amount(2), transaction_month(1), status(1), period(1) |
| Request | 20 | description(9), request_date(4), request_id(4), request_type(4), type(2), follow_up_method(2), topic(2), mode(1) |
| Customer | 19 | name(8), email(7), age_group(4), birth_decade(2), contact_phone(2), contact(2), contact_preference(1), communication_preference(1) |
| Card | 11 | masked_number(3), name(3), card_id(2), last_four_digits(1), annual_fee(1), purpose(1), last_month(1), transaction_count(1) |
| Record | 7 | record_id(7), date(4), record_date(3), topic(1) |
| Conversation | 5 | date(5), topic(3), id(2), conversation_id(2), record_id(1) |
| CommunicationChannel | 5 | type(2), channel_type(2), method(1) |
| VirtualCard | 4 | masked_number(4), last_four(1) |
| Issue | 4 | description(4) |
| CommunicationMethod | 4 | method(3), time_of_day(2), method_type(1) |
| Benefit | 4 | description(3), name(1), automatic(1) |
| TransactionSummary | 4 | total_amount(4), month(3), transaction_count(2), approved_count(2), period(1) |
| Consultation | 3 | id(3), date(3), topic(2) |
| Preference | 3 | type(2), value(2), action(1) |
| Statement | 2 | month(1), transaction_count(1), total_amount(1), format(1), type(1) |
| Inquiry | 2 | topic(1), content(1), inquiry_id(1), date(1) |
| Department | 2 | name(2) |
| Proposal | 2 | description(1), suggestion(1) |
| Comparison | 2 | condition(1), type(1) |
| Branch | 2 | branch_name(1), method(1) |
| Concern | 1 | description(1) |
| ConsultationSession | 1 | session_id(1), date(1) |
| Device | 1 | device_type(1) |
| Channel | 1 | name(1) |
| TransactionInfo | 1 | approval_count(1), total_amount(1) |
| Interaction | 1 | id(1), date(1), summary(1) |
| Period | 1 | start_date(1), end_date(1) |
| FollowUp | 1 | method(1) |
| Agent | 1 | name(1) |
| Guidance | 1 | description(1) |
| WaiverCondition | 1 | description(1) |
| CardTier | 1 | tier_name(1) |
| MenuItem | 1 | name(1) |
| Counselor | 1 | name(1) |
| Notification | 1 | frequency(1) |
| Product | 1 | category(1) |
| WarrantyRequest | 1 | description(1) |
| CancellationRequest | 1 | request_type(1), request_date(1) |
| Person | 1 | role(1), email(1), birth_decade(1) |
| NotificationItem | 1 | name(1) |
| ContactMethod | 1 | method(1) |
| CallRecord | 1 | record_id(1), date(1) |
| NotificationChannel | 1 | name(1) |
| Address | 1 | address_line(1), address_type(1) |
| Consultant | 1 | consultant_id(1) |
| PreventionGuideline | 1 | description(1) |
| Message | 1 | content(1) |
| CardIssuer | 1 | name(1) |
| OrderMethod | 1 | method_type(1) |
| ExpenseCategory | 1 | name(1) |
| Setting | 1 | name(1) |
| PaymentMethod | 1 | name(1) |
| ConsultationRecord | 1 | record_id(1), date(1) |
| TransactionBatch | 1 | year_month(1), approved_count(1), total_amount(1) |
| MerchantCategory | 1 | name(1) |
| TransactionPeriod | 1 | month(1), approved_count(1), total_amount(1) |
| Response | 1 | suggestion(1) |

## 관계 이름별 나온 청크 수

| 관계 | 청크 수 |
|---|---:|
| MAKES_REQUEST | 9 |
| PARTICIPATES_IN | 8 |
| HAS_TRANSACTION | 8 |
| INTERACTS_WITH | 7 |
| REFERS_TO | 5 |
| RESPONDS_TO | 5 |
| HANDLES | 5 |
| MAKES | 5 |
| USES_METHOD | 3 |
| PROVIDES | 3 |
| OWNS | 3 |
| HAS_CONVERSATION | 3 |
| FOLLOWS | 3 |
| USES_CARD | 3 |
| HAS_ISSUE | 2 |
| HAS_REQUEST | 2 |
| ABOUT | 2 |
| HAS_BENEFIT | 2 |
| MENTIONS | 2 |
| LINKED_TO | 2 |
| REFERENCES | 2 |
| INCLUDES | 2 |
| MADE_TRANSACTION | 2 |
| ADDRESSES | 2 |
| USES_CHANNEL | 2 |
| HAS_PREFERENCE | 2 |
| HANDLES_REQUEST | 2 |
| COVERS | 1 |
| RAISED_CONCERN | 1 |
| SUGGESTED_DEVICE | 1 |
| OWNED_CARD | 1 |
| ADDRESSED_CONCERN | 1 |
| INQUIRY_ABOUT | 1 |
| DISCUSSED_TRANSACTION | 1 |
| CONTINUES_WITH | 1 |
| ASKED | 1 |
| PROVIDED | 1 |
| RESPONDED | 1 |
| REQUESTED | 1 |
| RECORDED_FOR | 1 |
| MADE | 1 |
| HAS_WAIVER_CONDITION | 1 |
| CONNECTS_TO | 1 |
| CUSTOMER_OWNS_CARD | 1 |
| PROPOSAL_RELATES_TO_CARD | 1 |
| CONVERSATION_HAS_PROPOSAL | 1 |
| CONVERSATION_HAS_REQUEST | 1 |
| CONVERSATION_HAS_TRANSACTION_SUMMARY | 1 |
| BELONGS_TO | 1 |
| ASSOCIATES_WITH | 1 |
| TRANSACTION_FOR | 1 |
| HAS_COMPARISON | 1 |
| HAS_TIER | 1 |
| RECORDED_IN | 1 |
| ADDRESSES_REQUEST | 1 |
| DOCUMENTS | 1 |
| CREATED_BY | 1 |
| RAISES | 1 |
| FOR | 1 |
| INCLUDES_BENEFIT | 1 |
| PROVIDES_COMPARISON | 1 |
| TRIGGERED_BY | 1 |
| RECORDS_REQUEST | 1 |
| APPLIES_TO_CARD | 1 |
| RELATES_TO_CARD | 1 |
| RECEIVES_COMPARISON | 1 |
| RESPONDS_VIA | 1 |
| MAKES_PURCHASE | 1 |
| REFERS_TO_PRODUCT | 1 |
| REQUESTS_CANCELLATION | 1 |
| LINKED_RECORD | 1 |
| COMMUNICATED_VIA | 1 |
| ASSOCIATED_WITH | 1 |
| LINKED_WITH | 1 |
| PREFERRED_METHOD | 1 |
| TARGETS | 1 |
| REQUESTS | 1 |
| RELATED_TO_ISSUE | 1 |
| HAS_CALL_RECORD | 1 |
| PROVIDED_GUIDANCE | 1 |
| OFFERS_BENEFIT | 1 |
| RAISES_ISSUE | 1 |
| REQUESTED_PREFERENCE | 1 |
| PROVIDES_TRANSACTION | 1 |
| REQUESTS_PREFERENCE | 1 |
| CUSTOMER_REFERENCES_TRANSACTION | 1 |
| PREFERENCE_FOR_CHANNEL | 1 |
| SUGGESTS_PREFERENCE | 1 |
| TARGETS_ADDRESS | 1 |
| INCLUDES_TRANSACTION | 1 |
| INITIATES | 1 |
| REFERS_TO_BRANCH | 1 |
| REFERS_TO_CARD | 1 |
| INCLUDES_SUMMARY | 1 |
| INVOLVES_BRANCH | 1 |
| HAS_CARD | 1 |
| PROPOSAL_FOR_CARD | 1 |
| REQUEST_TARGETS_CARD | 1 |
| PROVIDES_PROPOSAL | 1 |
| HANDLED_AT | 1 |
| HAS_TRANSACTION_SUMMARY | 1 |
| REFERENCES_CARD | 1 |
| LINKED_TO_INQUIRY | 1 |
| FOLLOWS_RECORD | 1 |
| REFERENCES_TRANSACTION | 1 |
| INCLUDES_GUIDELINE | 1 |
| LINKED_TO_RECORD | 1 |
| REFERENCES_VIRTUAL_CARD | 1 |
| SENT_BY | 1 |
| DISCUSSES | 1 |
| HAS_MESSAGE | 1 |
| PREFERRED_CHANNEL | 1 |
| USES_ORDER_METHOD | 1 |
| PREFERS_METHOD | 1 |
| MENTIONS_CATEGORY | 1 |
| HAS_COMMUNICATION_CHANNEL | 1 |
| INVOLVES_PAYMENT_METHOD | 1 |
| REFERS_TO_TRANSACTION | 1 |
| INVOLVES_SETTING | 1 |
| INCLUDES_REQUEST | 1 |
| INVOLVES_CARD | 1 |
| INVOLVES | 1 |
| DELIVERED_VIA | 1 |
| HAS_MERCHANT_CATEGORY | 1 |
| USES | 1 |

## 자주 나온 패턴(2건 이상)

| 패턴 | 청크 수 |
|---|---:|
| (Customer)-[MAKES_REQUEST]->(Request) | 7 |
| (Customer)-[HAS_TRANSACTION]->(Transaction) | 5 |
| (Customer)-[MAKES]->(Request) | 4 |
| (Request)-[LINKED_TO]->(Record) | 2 |
| (Request)-[USES_CHANNEL]->(CommunicationChannel) | 2 |
| (Customer)-[PARTICIPATES_IN]->(Conversation) | 2 |
