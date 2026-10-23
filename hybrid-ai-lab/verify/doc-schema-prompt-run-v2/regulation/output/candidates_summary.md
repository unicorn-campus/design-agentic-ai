# 스키마 후보 요약: regulation

- 모델: openai/gpt-oss-120b, 추출기: neo4j-graphrag `SchemaFromTextExtractor`, examples = 역량 질문만
- 호출 20건(성공 20, 실패 0), 노드 타입 이름 41개, 관계 이름 68개

## 묶음별 멈춤

| 묶음 | 본 건수 | 멈춘 이유 |
|---|---:|---|
| 약관 조항 전체 | 20 | 모두 봄 |

## 역량 질문별로 답할 수 있어 보이는 이름(LLM 분류, 드문 이름 포함)

| 질문 | 이름 |
|---|---|
| R1 | Clause, Article |
| R2 | Condition, Requirement, PaymentTerm, CardLoan, Application, RenewalInfo |
| R3 | RenewalInfo, NotificationType, Contract, Clause, Card |
| R4 | Action, Condition, Cancellation, Screen, Dispute, Decision |
| R5 | Clause, Contract, RenewalInfo |
| X1 | Dispute, Request, CardProduct, Clause |

## 노드 타입 이름별 나온 청크 수와 자주 나온 속성

| 노드 타입 | 청크 수 | 속성(나온 수) |
|---|---:|---|
| Clause | 13 | number(13), title(13), occurrenceDate(1), unpaidAmount(1), virtualCost(1), normalizationMethod(1) |
| Member | 6 | member_id(3), name(2), type(1), preferred_method(1), role(1) |
| CardCompany | 6 | name(6) |
| CardIssuer | 3 | name(3) |
| Report | 2 | type(1), reportNumber(1), method(1) |
| Application | 2 | amount(1), virtual_fee_rate(1), usage_period(1), payment_date(1), estimated_repayment_amount(1), decision(1), reasonCategory(1), reapplicationDate(1) |
| CardLoan | 2 | type(1), amount(1), period(1), repayment_method(1), virtual_interest_rate(1), early_repayment_condition(1) |
| Card | 2 | expirationDate(1), usageLimit(1), type(1) |
| Action | 2 | type(1), description(1) |
| Condition | 2 | description(2) |
| PaymentTerm | 1 | minimum_payment_ratio(1), virtual_fee_rate(1), expected_repayment_period(1), total_cost(1) |
| Record | 1 | category(1) |
| Dispute | 1 | within_days(1), review_days(1) |
| FinancialItem | 1 | category(1) |
| CardProduct | 1 | name(1), expiration_date(1), annual_fee(1), benefit_change(1) |
| RenewalInfo | 1 | condition(1), annual_fee(1), benefit_change(1), notification_date(1) |
| Contract | 1 | contract_id(1), start_date(1), end_date(1), status(1) |
| ReplacementCard | 1 | card_id(1), issue_date(1) |
| Approval | 1 | amount(1), datetime(1) |
| Merchant | 1 | name(1) |
| Cancellation | 1 | datetime(1) |
| Decision | 1 | outcome(1), reason_category(1) |
| Channel | 1 | name(1) |
| Requirement | 1 | description(1) |
| Party | 1 | name(1) |
| NotificationType | 1 | name(1), default_method(1), auxiliary_method(1), confirmation_records(1) |
| PartialPaymentOption | 1 | minimum_amount(1), carryover_amount(1), expected_cost(1) |
| Screen | 1 | name(1), termination_method(1) |
| Applicant | 1 | name(1), contactMethod(1), paymentAccount(1) |
| Article | 1 | number(1), title(1) |
| Evaluation | 1 | result(1), criteria(1) |
| Request | 1 | reason(1) |
| AppealPath | 1 | method(1) |
| Service | 1 | name(1) |
| Amount | 1 | category(1) |
| Investigation | 1 | phase(1) |
| Fee | 1 | name(1) |
| TransactionType | 1 | name(1) |
| ReasonCategory | 1 | name(1) |
| RepaymentSchedule | 1 | installment_number(1), principal(1), fee(1), previous_amount(1), new_amount(1), effective_date(1) |
| ExternalSystem | 1 | name(1) |

## 관계 이름별 나온 청크 수

| 관계 | 청크 수 |
|---|---:|
| APPLIES_TO | 4 |
| DESCRIBES | 3 |
| APPLIES_FOR | 3 |
| NOTIFIES | 3 |
| HAS_APPLICATION | 2 |
| REGULATES | 2 |
| REFERS_TO | 2 |
| HAS_TERM | 1 |
| OFFERS | 1 |
| HAS_FAMILY_MEMBER | 1 |
| SUBMITS_REPORT | 1 |
| RAISES_DISPUTE | 1 |
| REQUESTS_CORRECTION | 1 |
| PROVIDES_REVIEW | 1 |
| REQUESTS_INFO | 1 |
| PROVIDES_RECEIPT | 1 |
| RELATES_TO | 1 |
| SUBJECT_TO | 1 |
| HAS_CONTRACT | 1 |
| ISSUES_PRODUCT | 1 |
| PROPOSES_REPLACEMENT | 1 |
| AGREES_TO | 1 |
| TERMINATES | 1 |
| APPROVAL_FOR | 1 |
| SUBMITS | 1 |
| DESCRIBES_APPROVAL | 1 |
| REFLECTED_IN | 1 |
| DESCRIBES_CANCELLATION | 1 |
| DEFINES | 1 |
| RESULTS_IN | 1 |
| ISSUES | 1 |
| OWNS | 1 |
| ACTION_HAS_REQUIREMENT | 1 |
| CLAUSE_DEFINES_ACTION | 1 |
| CLAUSE_REFERENCES | 1 |
| ACTION_PERFORMED_BY | 1 |
| ACTION_HAS_CONDITION | 1 |
| ACTION_VIA_CHANNEL | 1 |
| NOTIFY | 1 |
| ISSUES_NOTIFICATION | 1 |
| DISPLAYS | 1 |
| SELECTS | 1 |
| REVIEWED_BY | 1 |
| ADJUSTS_LIMIT | 1 |
| PERFORMS_VERIFICATION | 1 |
| REQUESTS_REVIEW | 1 |
| MAKES_REQUEST | 1 |
| EVALUATION_OF | 1 |
| EVALUATES | 1 |
| PROCESSES | 1 |
| REQUESTS_FOR | 1 |
| HAS_INVESTIGATION | 1 |
| INVESTIGATES | 1 |
| TARGETS | 1 |
| TRIGGERS | 1 |
| HAS_CONDITION | 1 |
| ABOUT_CLAUSE | 1 |
| INVOLVES | 1 |
| REPORTS | 1 |
| HAS_REASON | 1 |
| REFERENCES | 1 |
| HAS_SCHEDULE | 1 |
| ISSUED_BY | 1 |
| REVIEWS_FULL_TEXT | 1 |
| REVIEWS_SUMMARY | 1 |
| PROVIDES_TERM | 1 |
| CONFIRMS_TERM | 1 |
| TRANSMIT_STATUS | 1 |

## 자주 나온 패턴(2건 이상)

| 패턴 | 청크 수 |
|---|---:|
