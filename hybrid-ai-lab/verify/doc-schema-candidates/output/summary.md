# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)

- 모델: Groq `openai/gpt-oss-120b`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 20261018
- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 3건 0개면 멈춤, 층 상한 30건

## regulation

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 약관 전체 | 10 | 10 | 10 | 모두 봄 |

- 호출 10건, 성공 10건, 실패 0건
- 노드 타입 후보 42개, 관계 후보 78개

노드 타입 후보(제안한 청크 수 순): Member(8), Transaction(7), Card(6), Merchant(4), Company(3), Account(3), CardIssuer(3), Refund(2), Document(2), Clause(2), Statement(2), Suspension(2), Contract(2), CardCompany(2), Fee(1), Chapter(1), Paragraph(1), Article(1), Installment(1), RevocationRequest(1), CurrencyConversion(1), PointRecord(1), Service(1), Device(1), Investigation(1), ServiceProvider(1), Procedure(1), Replacement(1), Report(1), Renewal(1), LimitAdjustment(1), ContactMethod(1), Notification(1), FamilyMember(1), Application(1), PrimaryMember(1), Channel(1), Appeal(1), Cancellation(1), Loan(1), Delinquency(1), Agreement(1)

관계 후보(제안한 청크 수 순): ISSUED_BY(3), MAKES_TRANSACTION(3), OWNS(2), MAKES(2), HAS_ACCOUNT(2), HANDLED_BY(2), HAS_CONTRACT(2), AT_MERCHANT(2), HAS_FEE(1), REFUND_FOR(1), ON_CARD(1), MADE_TRANSACTION(1), REFUND_TO(1), HAS_ARTICLE(1), HAS_PARAGRAPH(1), HAS_CHAPTER(1), MAKES_PAYMENT(1), DEFINED_IN(1), GENERATES_DOCUMENT(1), USING_CARD(1), ASSIGNED_TO(1), ISSUED_CARD(1), AT(1), WITHDRAWS(1), INCLUDES_SERVICE(1), REVOCATION_FOR(1), SUBMITS(1), RECORDED_IN(1), HAS_CURRENCY_CONVERSION(1), HAS_POINT(1), HAS_INSTALLMENT(1), PROCESSED_BY(1), OWNS_CARD(1), TRANSACTION_USES_ACCOUNT(1), TRANSACTION_AT_MERCHANT(1), INITIATES_INVESTIGATION(1), INVESTIGATION_USES_DEVICE(1), PROVIDES_SERVICE(1), INVESTIGATION_INVOLVES_TRANSACTION(1), TRANSACTION_RELATED_DEVICE(1), HAS_SUSPENSION(1), NOTIFIES(1), CHANGES(1), TERMINATED_BY(1), INCLUDES(1), ISSUES(1), FOLLOWS(1), REPORTS(1), APPROVES(1), RENEWS(1), ISSUED(1), ISSUES_REPLACEMENT(1), SUSPENDS(1), ADJUSTS_LIMIT(1), CANCELS(1), APPLIES_TO(1), DELIVERED_VIA(1), OWNED_BY(1), HAS_FAMILY_MEMBER(1), SENT_TO(1), SUBMITS_APPLICATION(1), USES_CONTACT_METHOD(1), APPLICATION_FOR(1), TERMINATES_CONTRACT(1), SUBMITS_APPEAL(1), HANDLES_APPEAL(1), ISSUES_TRANSACTION(1), USES_CHANNEL(1), HAS_AGREEMENT(1), FUNDS_FOR(1), DELINQUENCY_RELATED_TO(1), HAS_CANCELLATION(1), CARD_USED_IN(1), HAS_REFUND(1), HAS_CARD(1), LOAN_GRANTED_TO(1), INCLUDED_IN_STATEMENT(1), STATEMENT_FOR(1)

자주 나온 패턴 상위 10: (Member)-[MAKES_TRANSACTION]->(Transaction) 3; (Member)-[OWNS]->(Card) 2; (Member)-[MAKES]->(Transaction) 2; (Member)-[HAS_ACCOUNT]->(Account) 2; (Member)-[HAS_CONTRACT]->(Contract) 2; (Transaction)-[AT_MERCHANT]->(Merchant) 2; (Transaction)-[ON_CARD]->(Card) 1; (Member)-[MADE_TRANSACTION]->(Transaction) 1; (Refund)-[REFUND_FOR]->(Transaction) 1; (Refund)-[REFUND_TO]->(Member) 1

## consult_log

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 상담 전체(세그먼트 균형) | 48 | 12 | 30 | 상한 30건 |

- 호출 30건, 성공 29건, 실패 1건
- 노드 타입 후보 45개, 관계 후보 115개

노드 타입 후보(제안한 청크 수 순): Transaction(22), Customer(19), Request(14), Record(9), Inquiry(6), TransactionSummary(6), Channel(5), Person(4), Card(4), CommunicationMethod(3), Agent(3), Conversation(2), Company(2), Address(2), Budget(2), Category(2), Consultation(2), Consultant(2), CommunicationChannel(2), Interaction(1), Warranty(1), Product(1), Notification(1), Setting(1), ContactMethod(1), TransactionRecord(1), SupportTicket(1), NotificationItem(1), PaymentMethod(1), Purpose(1), ConversationRecord(1), Condition(1), Payment(1), Preference(1), Message(1), Receipt(1), SupportAgent(1), Statement(1), InteractionRecord(1), Branch(1), Region(1), Store(1), Cancellation(1), VirtualCard(1), OrderMethod(1)

관계 후보(제안한 청크 수 순): INTERACTS_WITH(7), REFERS_TO(7), HANDLES(6), MAKES_REQUEST(5), MAKES_INQUIRY(4), HAS_TRANSACTION(4), USES(4), USES_CARD(3), USES_CHANNEL(3), INCLUDES(3), INITIATES(3), HANDLED_BY(3), PARTICIPATES_IN(2), INCLUDES_TRANSACTION(2), MAKES(2), HAS_SUMMARY(2), TARGETS(2), CREATES_RECORD(2), RESPONDS(2), DISCUSSES(2), LOGS(2), PREFERS(2), ADDRESSES(2), MADE(2), REFERENCES_RECORD(2), MAKES_TRANSACTION(2), HAS_RECEIPT(2), ON_CARD(2), INCLUDES_INQUIRY(1), REFERS_TO_TRANSACTION(1), RESPONDS_TO(1), LINKED_TO_RECORD(1), REGISTERED_WARRANTY(1), WARRANTY_FOR(1), FOLLOWUP_VIA(1), PURCHASED_PRODUCT(1), MADE_PURCHASE(1), SOLD_BY(1), SENT_VIA(1), RELATED_TO(1), HAS_SETTING(1), RECEIVED_BY(1), APPLIES_TO(1), OWNS(1), PREFERS_METHOD(1), CONTACTED_VIA(1), REPORTS_ISSUE(1), RELATED_TO_TRANSACTION(1), REQUIRES_VERIFICATION(1), ASSOCIATED_WITH(1), CREATES(1), INITIATED(1), PARTICIPATED_IN(1), HAS_RECORD(1), RECEIVED_CONTACT(1), VERIFIES(1), MADE_TRANSACTION(1), RECORDS(1), HAS_PURPOSE(1), ABOUT(1), RESULTED_IN(1), CONCERNS(1), RECORDED_IN(1), INVOLVES_PAYMENT(1), FOR_CUSTOMER(1), CREATED_BY(1), SELECTS(1), HAS_ADDRESS(1), RESPONDS_TO_REQUEST(1), INITIATES_REQUEST(1), RELATES_TO_TRANSACTION(1), INCLUDES_MESSAGE(1), ORIGINATES_FROM_COMPANY(1), ASSOCIATED_WITH_TRANSACTION(1), ASSIGNS_BUDGET(1), ABOUT_CATEGORY(1), IN_CATEGORY(1), OCCURS_ON(1), BUDGET_FOR(1), CONTACTS(1), SUBMITS_INQUIRY(1), CONTAINS_TRANSACTION(1), ABOUT_STATEMENT(1), HAS_SUBSCRIPTION(1), GENERATES(1), ASSISTS(1), REQUESTS(1), REQUEST_ASSOCIATED_WITH_CONSULTATION(1), CONSULTATION_WITH_AGENT(1), REQUEST_REFERS_TO_CARD(1), CONSULTATION_FOR_CUSTOMER(1), REQUEST_REFERS_TO_TRANSACTION(1), CUSTOMER_MADE_REQUEST(1), REQUEST_REFERS_TO_BRANCH(1), REQUEST_HANDLED_BY(1), REFERS_TO_CARD(1), HANDLES_REQUEST(1), BELONGS_TO_CATEGORY(1), USES_COMM_METHOD(1), HAS_BUDGET(1), HAS_ORDER(1), LOCATED_IN(1), OCCURS_AT(1), HAS(1), RELATES_TO(1), SUBMITS(1), CHARGED_TO(1), CANCELS(1), TARGETS_ADDRESS(1), REQUEST_INCLUDES_TRANSACTION(1), REQUEST_FOLLOWS(1), REQUEST_INCLUDES_CARD(1), AGENT_HANDLES(1), CUSTOMER_MAKES(1), COMMUNICATES_VIA(1)

자주 나온 패턴 상위 10: (Customer)-[MAKES_INQUIRY]->(Inquiry) 3; (Customer)-[MAKES_REQUEST]->(Request) 3; (Request)-[REFERENCES_RECORD]->(Record) 2; (Customer)-[MAKES_TRANSACTION]->(Transaction) 2; (Person)-[INTERACTS_WITH]->(Person) 1; (Person)-[PARTICIPATES_IN]->(Interaction) 1; (Interaction)-[INCLUDES_TRANSACTION]->(Transaction) 1; (Customer)-[PARTICIPATES_IN]->(Conversation) 1; (Inquiry)-[REFERS_TO_TRANSACTION]->(Transaction) 1; (Inquiry)-[LINKED_TO_RECORD]->(Record) 1

## benefit_guide

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 공통 안내 | 4 | 4 | 4 | 모두 봄 |
| 참고 카드 | 7 | 7 | 7 | 모두 봄 |
| 카드 개요 | 64 | 10 | 27 | 연속 3건 새 타입 0개 |
| 혜택 상세 | 85 | 10 | 30 | 상한 30건 |

- 호출 68건, 성공 68건, 실패 0건
- 노드 타입 후보 54개, 관계 후보 83개

노드 타입 후보(제안한 청크 수 순): Benefit(44), Card(42), Condition(35), Channel(23), Limit(22), Fee(15), CardProduct(13), Transaction(8), Company(4), Brand(4), Merchant(3), Exclusion(3), Bonus(3), TransactionType(3), Document(2), Provider(2), Issuer(2), CreditCard(2), MerchantCategory(2), CardVariant(2), BenefitPlan(2), FeeCategory(2), Payment(2), Program(2), BenefitProgram(2), Offer(2), DiscountOffer(2), Restriction(2), CardDesign(2), DesignOption(2), TransactionCategory(2), VirtualCard(1), CardSection(1), Section(1), FeeComponent(1), TelecomProvider(1), RewardCategory(1), CashBackOffer(1), TransactionChannel(1), Payout(1), VirtualAccount(1), Service(1), ExclusionCategory(1), Coupon(1), ServiceOffer(1), Business(1), FinancialInstitution(1), CardAccount(1), RewardProgram(1), Industry(1), PointBox(1), AccountType(1), PaymentTiming(1), EffectiveDate(1)

관계 후보(제안한 청크 수 순): HAS_BENEFIT(25), HAS_CONDITION(24), HAS_FEE(16), APPLIES_TO(16), HAS_LIMIT(15), ISSUED_BY(7), APPLIES_TO_CHANNEL(7), OFFERS_BENEFIT(6), BENEFIT_HAS_CONDITION(5), CARD_HAS_BENEFIT(5), TARGETS(4), OFFERS(4), BENEFIT_APPLIES_TO_CHANNEL(3), BENEFIT_HAS_LIMIT(3), HAS_BONUS(3), CARD_HAS_CONDITION(3), HAS_VARIANT(2), APPLICABLE_CHANNEL(2), TARGETS_CHANNEL(2), REQUIRES_CONDITION(2), HAS_FEE_CATEGORY(2), HAS_EXCLUSION(2), EXCLUDES(2), HAS_FAMILY_CARD(2), CARD_HAS_LIMIT(2), BENEFIT_APPLIES_TO_TRANSACTION(2), REQUIRES(2), DESCRIBES(1), BELONGS_TO(1), DOCUMENTED_IN(1), IN_SECTION(1), CARD_BRAND_FEE(1), CARD_HAS_BRAND(1), CARD_HAS_FEE(1), CONDITION_HAS_LIMIT(1), PROVIDED_BY(1), ALLOCATES_PERCENTAGE(1), HAS_REWARD_CATEGORY(1), BENEFIT_HAS_EXCLUSION(1), ANNUAL_FEE(1), HAS_OFFER(1), HAS_BRAND(1), BENEFIT_PAID_ON(1), HAS_PAYOUT(1), CREDITED_TO(1), HAS_ACCOUNT(1), PROVIDES(1), INCLUDES(1), FOR_CARD(1), MAKES_TRANSACTION(1), HAS_RESTRICTION(1), HAS_PAYMENT(1), BENEFIT_APPLIES_TO(1), BENEFIT_EXCLUDED_FOR(1), QUALIFIES_FOR(1), TRANSACTION_HAS_LIMIT(1), PROTECTS(1), HAS_DESIGN(1), DESIGN_HAS_OPTION(1), TRANSACTION_ALERTED_TO(1), TRANSACTION_RESTRICTED_BY(1), CONDITION_APPLIES_TO_TRANSACTION(1), EARNED_UNDER(1), MADE_BY(1), REWARD_HAS_BENEFIT(1), HAS_REWARD(1), BENEFIT_TARGET_INDUSTRY(1), APPLICABLE_TO(1), BENEFIT_APPLIED_IN(1), HAS_OPTION(1), AVAILABLE_FOR(1), CAN_STACK_WITH(1), APPLIES_BENEFIT(1), DEDUCTED_IN_MONTH(1), PROVIDED_VIA(1), EXCLUDED_FOR(1), APPLIES_TO_CARD(1), PAID_AT(1), BENEFIT_APPLICABLE_TO_TRANSACTION(1), EFFECTIVE_ON(1), OFFERED_BY(1), CARD_OFFER_BENEFIT(1), CONDITION_EXCLUDES_TRANSACTION(1)

자주 나온 패턴 상위 10: (Card)-[HAS_BENEFIT]->(Benefit) 16; (Benefit)-[HAS_CONDITION]->(Condition) 15; (CardProduct)-[HAS_FEE]->(Fee) 8; (Card)-[HAS_LIMIT]->(Limit) 7; (CardProduct)-[HAS_BENEFIT]->(Benefit) 6; (Card)-[CARD_HAS_BENEFIT]->(Benefit) 5; (Benefit)-[BENEFIT_HAS_CONDITION]->(Condition) 5; (Benefit)-[APPLIES_TO_CHANNEL]->(Channel) 5; (Card)-[HAS_CONDITION]->(Condition) 4; (Card)-[HAS_FEE]->(Fee) 4

