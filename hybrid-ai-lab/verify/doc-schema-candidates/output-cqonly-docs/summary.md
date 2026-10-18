# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)

- 모델: Groq `openai/gpt-oss-120b`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 20261018
- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 3건 0개면 멈춤, 층 상한 30건

## regulation

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 약관 전체 | 10 | 10 | 10 | 모두 봄 |

- 호출 10건, 성공 10건, 실패 0건
- 노드 타입 후보 38개, 관계 후보 71개

노드 타입 후보(제안한 청크 수 순): Member(10), Transaction(6), CardIssuer(5), Card(4), Merchant(4), Company(3), Request(3), Service(2), Refund(2), Chapter(2), Article(2), CardCompany(2), Statement(2), Account(2), Clause(2), Contract(2), Cancellation(2), Fee(1), Exemption(1), CardProduct(1), Document(1), Investigation(1), Device(1), Suspension(1), Procedure(1), Report(1), Renewal(1), Approval(1), ReplacementCard(1), LimitAdjustment(1), Application(1), Notification(1), Record(1), Dispute(1), OutsourcedTask(1), Agreement(1), Loan(1), Payment(1)

관계 후보(제안한 청크 수 순): ISSUED_BY(7), REFUND_FOR(2), REFERS_TO(2), HAS_CHAPTER(2), HAS_ARTICLE(2), HAS_CARD(2), APPLIES_TO(2), MAKES_PAYMENT(2), HAS_ACCOUNT(2), ISSUED_TO(1), EXEMPT_FROM(1), CALCULATED_FROM(1), ON_CARD(1), PERFORMED_BY(1), GRANTED_TO(1), CHARGED_TO(1), ASSOCIATED_WITH(1), ISSUES_CARD(1), ISSUES_STATEMENT(1), SUBMITS_REQUEST(1), REQUESTED_TO_CARD(1), HANDLED_BY_CARD(1), HANDLED_BY_MERCHANT(1), MAKES_TRANSACTION(1), REQUESTED_TO_MERCHANT(1), INCLUDES_SERVICE(1), INCLUDED_IN_STATEMENT(1), LIFTS_FOR(1), USES_DEVICE(1), REPORTS(1), OCCURS_AT(1), INVESTIGATES(1), REFUND_TO(1), AMENDS(1), HELD_BY(1), TARGETS_CONTRACT(1), HAS_CLAUSE(1), RESULTS_IN(1), MAKES_REQUEST(1), HAS_APPROVAL(1), RENEWED_WITH(1), HAS_LIMIT_ADJUSTMENT(1), HAS_CANCELLATION(1), PROVIDES(1), REPORTS_FOR(1), USED_IN(1), REPORTED(1), REPLACED_WITH(1), FAMILY_MEMBER_OF(1), REVIEWED_BY(1), MAKES(1), APPLIES_FOR(1), SENT_BY(1), OWNS_CARD(1), RECEIVES(1), RECORD_RELATED_TO_DISPUTE(1), CONTRACT_WITH_COMPANY(1), CARD_COMPANY_PROCESSES_REQUEST(1), CARD_COMPANY_OUTSOURCES_TASK(1), MEMBER_MAKES_REQUEST(1), MEMBER_HAS_CONTRACT(1), OUTSOURCED_TASK_HANDLES_RECORD(1), REQUEST_GENERATES_RECORD(1), RECEIVES_STATEMENT(1), INCLUDES_TRANSACTION(1), AT_MERCHANT(1), PAYMENT_FOR(1), CANCELLATION_OF(1), INCLUDES_LOAN(1), REQUESTS_CANCELLATION(1), HAS_AGREEMENT(1)

자주 나온 패턴 상위 10: (Card)-[ISSUED_BY]->(CardIssuer) 3; (Chapter)-[HAS_ARTICLE]->(Article) 2; (Member)-[HAS_ACCOUNT]->(Account) 2; (Member)-[HAS_CARD]->(Card) 2; (Exemption)-[GRANTED_TO]->(Member) 1; (Exemption)-[EXEMPT_FROM]->(Fee) 1; (Card)-[ISSUED_BY]->(Company) 1; (Transaction)-[PERFORMED_BY]->(Member) 1; (Fee)-[CHARGED_TO]->(Member) 1; (Refund)-[CALCULATED_FROM]->(Fee) 1

## benefit_guide

| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |
|---|---:|---:|---:|---|
| 공통 안내 | 4 | 4 | 4 | 모두 봄 |
| 참고 카드 | 7 | 7 | 7 | 모두 봄 |
| 카드 개요 | 64 | 10 | 30 | 상한 30건 |
| 혜택 상세 | 85 | 10 | 30 | 상한 30건 |

- 호출 71건, 성공 66건, 실패 5건
- 노드 타입 후보 48개, 관계 후보 83개

노드 타입 후보(제안한 청크 수 순): Card(58), Benefit(49), Condition(46), Limit(34), Channel(28), Exclusion(25), Fee(16), Brand(10), MerchantCategory(5), Issuer(4), Bonus(4), PaymentTiming(4), BenefitProgram(3), TransactionType(3), Restriction(3), Document(2), Provider(2), Company(2), CardVariant(2), CardProduct(2), PDFDocument(1), VirtualCard(1), CreditCard(1), Merchant(1), CardFee(1), Payout(1), TelecomCompany(1), FeeStructure(1), AnnualFee(1), BrandVariant(1), BenefitPlan(1), Category(1), Payment(1), PointProgram(1), TransactionChannel(1), DiscountBenefit(1), Coupon(1), Offer(1), Settlement(1), DesignOption(1), Account(1), Transaction(1), Implementation(1), CardProgram(1), TransactionCategory(1), Partner(1), Promotion(1), FamilyCard(1)

관계 후보(제안한 청크 수 순): HAS_BENEFIT(27), HAS_CONDITION(26), HAS_LIMIT(23), HAS_FEE(15), ISSUED_BY(12), BENEFIT_HAS_CONDITION(11), APPLIES_TO_CHANNEL(10), HAS_EXCLUSION(9), EXCLUDES(8), BENEFIT_HAS_LIMIT(8), OFFERS(7), CARD_HAS_BENEFIT(6), BENEFIT_HAS_EXCLUSION(6), APPLIES_TO(5), REQUIRES(5), BENEFIT_APPLIES_TO_CHANNEL(3), CARD_HAS_FEE(3), HAS_BRAND(3), REQUIRES_CONDITION(3), DOCUMENTED_IN(2), PROVIDES(2), OFFERS_BENEFIT(2), APPLIES_TO_MERCHANT_CATEGORY(2), HAS_CHANNEL(2), BENEFIT_HAS_BONUS(2), OFFER_BENEFIT(2), HAS_VARIANT(2), APPLIES_VIA(2), HAS_PAYMENT_TIMING(2), HAS_BONUS(2), PROVIDES_BENEFIT(2), HAS_FAMILY_CARD(2), APPLICABLE_TO(2), CARD_ASSOCIATED_WITH_BRAND(1), HAS_DOCUMENT(1), REFERS_TO(1), BENEFIT_APPLIES_TO_MERCHANT_CATEGORY(1), VIA_CHANNEL(1), VARIANT_HAS_BENEFIT(1), CARD_HAS_VARIANT(1), HAS_PAYOUT(1), ASSOCIATED_WITH_TELECOM(1), HAS_FEE_STRUCTURE(1), ALLOCATES(1), HAS_PLAN(1), HAS_PAYMENT(1), HAS_TARGET(1), BENEFIT_FOR_CHANNEL(1), ACCRUES_VIA(1), ASSOCIATED_WITH(1), BENEFIT_HAS_CHANNEL(1), BENEFIT_HAS_PAYMENT_TIMING(1), BENEFIT_VIA_CHANNEL(1), USES_CHANNEL(1), BENEFIT_EXCLUDES_TRANSACTION(1), CARD_SUPPORTS_TRANSACTION(1), CARD_OFFER_BENEFIT(1), CARD_OFFER(1), BENEFIT_HAS_RESTRICTION(1), OFFER_HAS_LIMIT(1), OFFER_HAS_CONDITION(1), OFFER_INCLUDES_COUPON(1), OFFER_PROVIDED_BY(1), OFFER_ASSOCIATED_CARD(1), OFFER_HAS_EXCLUSION(1), SETTLED_ON(1), HAS_RESTRICTION(1), EXCLUDED_FOR(1), CARD_PROVIDES_BENEFIT(1), CARD_HAS_TRANSACTION(1), GUARDIAN_OF(1), CARD_HAS_RESTRICTION(1), CARD_HAS_DESIGN(1), TRANSACTION_RESTRICTED_BY(1), ACCOUNT_HAS_CARD(1), EXCLUDES_TRANSACTION_TYPE(1), IMPLEMENTED_ON(1), PAYOUT_ON(1), USES_TRANSACTION(1), REQUIRES_TRANSACTION_TYPE(1), CARD_HAS_LIMIT(1), HAS_PARTNER(1), LIMITED_BY(1)

자주 나온 패턴 상위 10: (Benefit)-[HAS_CONDITION]->(Condition) 23; (Card)-[HAS_BENEFIT]->(Benefit) 23; (Benefit)-[HAS_LIMIT]->(Limit) 15; (Benefit)-[BENEFIT_HAS_CONDITION]->(Condition) 11; (Card)-[HAS_FEE]->(Fee) 11; (Benefit)-[APPLIES_TO_CHANNEL]->(Channel) 9; (Benefit)-[BENEFIT_HAS_LIMIT]->(Limit) 8; (Benefit)-[EXCLUDES]->(Exclusion) 7; (Card)-[CARD_HAS_BENEFIT]->(Benefit) 6; (Card)-[ISSUED_BY]->(Brand) 6

