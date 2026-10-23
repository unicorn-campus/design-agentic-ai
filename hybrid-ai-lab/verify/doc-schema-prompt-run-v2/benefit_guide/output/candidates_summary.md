# 스키마 후보 요약: benefit_guide

- 모델: openai/gpt-oss-120b, 추출기: neo4j-graphrag `SchemaFromTextExtractor`, examples = 역량 질문만
- 호출 39건(성공 38, 실패 1), 노드 타입 이름 18개, 관계 이름 41개

## 묶음별 멈춤

| 묶음 | 본 건수 | 멈춘 이유 |
|---|---:|---|
| 본문 아님 | 8 | 모두 봄 |
| 카드 개요 | 18 | 시작 수 뒤 연속 3건 새 타입 없음 |
| 혜택 상세 | 13 | 시작 수 뒤 연속 3건 새 타입 없음 |

## 역량 질문별로 답할 수 있어 보이는 이름(LLM 분류, 드문 이름 포함)

| 질문 | 이름 |
|---|---|
| B1 | Card, Benefit |
| B2 | Benefit, Condition, MerchantCategory |
| B3 | Limit, TimeWindow |
| B4 | Benefit, Exclusion |
| B5 | Card, Fee, CardVariant |
| X1 | Document, Benefit, Condition |
| X2 | Card, Benefit, Condition |

## 노드 타입 이름별 나온 청크 수와 자주 나온 속성

| 노드 타입 | 청크 수 | 속성(나온 수) |
|---|---:|---|
| Card | 38 | name(30), code(21), virtualEffectiveDate(8), effective_date(8), virtual_effective_date(7), public_grade(6), publicGrade(4), annual_fee_domestic(4) |
| Benefit | 31 | name(20), description(7), exclusions(7), code(6), type(5), discount_rate(5), payment_timing(5), unit(5) |
| Limit | 23 | period(18), amount(16), unit(3), monthlyAggregateAmount(2), perBenefitAmount(2), additionalAmount(1), overall_monthly(1), per_item(1) |
| Condition | 21 | description(19), minimum_spending(3), excluded_items(3), threshold_amount(3), minSpend(2), currency(2), condition_type(1), thresholdAmount(1) |
| Channel | 14 | name(8), description(7), channel_type(1) |
| TransactionType | 6 | name(6) |
| Exclusion | 5 | description(5) |
| Provider | 4 | name(4) |
| Fee | 4 | amount(4), type(2), fee_type(1), region(1), category(1), scope(1) |
| MerchantCategory | 4 | name(3), description(1), channel_type(1) |
| FeeComponent | 4 | type(2), service(2), total(2), basic_fee(1), service_fee(1), total_fee(1), base(1), brand(1) |
| Document | 3 | format(2), document_id(1), version(1), effective_date(1) |
| TransactionCategory | 3 | name(2), category(1) |
| Issuer | 1 | name(1) |
| CardVariant | 1 | name(1), baseFee(1), serviceFee(1), totalFee(1) |
| PaymentTiming | 1 | dayOfMonth(1) |
| Payout | 1 | day(1), method(1) |
| TimeWindow | 1 | time_range(1) |

## 관계 이름별 나온 청크 수

| 관계 | 청크 수 |
|---|---:|
| HAS_BENEFIT | 21 |
| HAS_LIMIT | 15 |
| HAS_CONDITION | 13 |
| BENEFIT_HAS_LIMIT | 8 |
| BENEFIT_HAS_CONDITION | 8 |
| HAS_FEE | 6 |
| ISSUED_BY | 5 |
| OFFERS_BENEFIT | 5 |
| APPLIES_TO | 4 |
| CARD_HAS_BENEFIT | 3 |
| APPLIES_TO_CHANNEL | 3 |
| HAS_EXCLUSION | 3 |
| EXCLUDES | 3 |
| EXCLUDED_FOR | 3 |
| BENEFIT_VIA_CHANNEL | 2 |
| HAS_FEE_COMPONENT | 2 |
| HAS_CHANNEL | 2 |
| BENEFIT_EXCLUDES_TRANSACTION | 2 |
| DESCRIBES | 1 |
| ASSOCIATED_WITH | 1 |
| MENTIONED_IN | 1 |
| GUIDES | 1 |
| BENEFIT_APPLIES_TO_CATEGORY | 1 |
| HAS_VARIANT | 1 |
| TARGETS | 1 |
| OFFERS | 1 |
| PAYMENT_ON | 1 |
| FAMILY_CARD | 1 |
| PAYOUT_ON | 1 |
| APPLIES_VIA | 1 |
| BENEFIT_APPLIES_TO_CHANNEL | 1 |
| BENEFIT_TARGETS | 1 |
| CARD_OFFERS | 1 |
| BENEFIT_APPLIES_DURING | 1 |
| CONDITION_APPLIES_TO_TRANSACTION | 1 |
| APPLICABLE_VIA | 1 |
| APPLICABLE_TO | 1 |
| BENEFIT_APPLIES_TO_MERCHANT | 1 |
| EXCLUDES_TRANSACTION | 1 |
| BENEFIT_HAS_EXCLUSION | 1 |
| EXCLUSION_APPLIES_TO_TRANSACTION | 1 |

## 자주 나온 패턴(2건 이상)

| 패턴 | 청크 수 |
|---|---:|
| (Card)-[HAS_BENEFIT]->(Benefit) | 21 |
| (Benefit)-[HAS_LIMIT]->(Limit) | 15 |
| (Benefit)-[HAS_CONDITION]->(Condition) | 13 |
| (Benefit)-[BENEFIT_HAS_LIMIT]->(Limit) | 8 |
| (Benefit)-[BENEFIT_HAS_CONDITION]->(Condition) | 8 |
| (Card)-[OFFERS_BENEFIT]->(Benefit) | 5 |
| (Card)-[ISSUED_BY]->(Provider) | 4 |
| (Card)-[HAS_FEE]->(Fee) | 4 |
| (Card)-[CARD_HAS_BENEFIT]->(Benefit) | 3 |
| (Benefit)-[APPLIES_TO_CHANNEL]->(Channel) | 3 |
| (Benefit)-[HAS_EXCLUSION]->(Exclusion) | 3 |
| (Benefit)-[APPLIES_TO]->(Channel) | 3 |
| (Benefit)-[BENEFIT_VIA_CHANNEL]->(Channel) | 2 |
| (Card)-[HAS_FEE]->(FeeComponent) | 2 |
| (Card)-[HAS_FEE_COMPONENT]->(FeeComponent) | 2 |
| (Benefit)-[HAS_CHANNEL]->(Channel) | 2 |
| (Benefit)-[EXCLUDED_FOR]->(TransactionType) | 2 |

## 실패한 호출

- 혜택 상세 2번 `D2_5a3c0df949be0524_01e79b557379369a_0000`: SchemaValidationError: UNIQUENESS and KEY constraints cannot apply to the same node type and properties ('Card', ('code',)).
