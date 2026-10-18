# 약관과 혜택: 역량 질문 없이(A) vs 역량 질문만(CQ)

## regulation (비교 건수 10)

| 지표 | A | CQ |
|---|---:|---:|
| 성공 / 실패 | 10 / 0 | 10 / 0 |
| 노드 타입 이름 수 | 42 | 38 |
| 관계 이름 수 | 78 | 71 |
| 1건에서만 나온 이름 비율 | 82% | 76% |
| 핵심 이름 수(20% 이상) | 22 | 26 |

- A 핵심 노드 타입: Member(8), Transaction(7), Card(6), Merchant(4), Company(3), CardIssuer(3), Account(3), Refund(2), Document(2), Clause(2), Statement(2), Suspension(2), CardCompany(2), Contract(2)
- A 핵심 관계: ISSUED_BY(3), MAKES_TRANSACTION(3), OWNS(2), MAKES(2), HAS_ACCOUNT(2), HANDLED_BY(2), HAS_CONTRACT(2), AT_MERCHANT(2)

- CQ 핵심 노드 타입: Member(10), Transaction(6), CardIssuer(5), Card(4), Merchant(4), Company(3), Request(3), Service(2), Refund(2), Chapter(2), Article(2), CardCompany(2), Statement(2), Account(2), Clause(2), Contract(2), Cancellation(2)
- CQ 핵심 관계: ISSUED_BY(7), REFUND_FOR(2), HAS_CHAPTER(2), HAS_ARTICLE(2), REFERS_TO(2), MAKES_PAYMENT(2), HAS_CARD(2), HAS_ACCOUNT(2), APPLIES_TO(2)

- CQ에만 나온 이름(2건 이상): Request(3), REFERS_TO(2)

## benefit_guide (비교 건수 68)

| 지표 | A | CQ |
|---|---:|---:|
| 성공 / 실패 | 68 / 0 | 64 / 4 |
| 노드 타입 이름 수 | 54 | 48 |
| 관계 이름 수 | 83 | 82 |
| 1건에서만 나온 이름 비율 | 58% | 59% |
| 핵심 이름 수(20% 이상) | 11 | 11 |

- A 핵심 노드 타입: Benefit(44), Card(42), Condition(35), Channel(23), Limit(22), Fee(15)
- A 핵심 관계: HAS_BENEFIT(25), HAS_CONDITION(24), HAS_FEE(16), APPLIES_TO(16), HAS_LIMIT(15)

- CQ 핵심 노드 타입: Card(56), Benefit(47), Condition(45), Limit(34), Channel(27), Exclusion(25), Fee(14)
- CQ 핵심 관계: HAS_CONDITION(25), HAS_BENEFIT(25), HAS_LIMIT(23), HAS_FEE(13)

- CQ에만 나온 이름(2건 이상): APPLIES_TO_MERCHANT_CATEGORY(2), HAS_CHANNEL(2), BENEFIT_HAS_BONUS(2), OFFER_BENEFIT(2), APPLIES_VIA(2), HAS_PAYMENT_TIMING(2), PROVIDES_BENEFIT(2)

