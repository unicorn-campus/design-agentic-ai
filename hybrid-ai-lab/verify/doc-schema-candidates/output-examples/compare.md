# 1건씩 따로 뽑기(A) vs examples로 이어 뽑기(B)

- 같은 시드, 같은 순서. 층마다 두 실행 중 적게 본 건수까지만 비교
- 핵심 타입: 성공 호출의 20% 이상에서 나온 이름. 멈춤 규칙 A는 이름 그대로, B는 두 번째 건에서 나온 이름만 셈

## regulation (비교 건수 10)

| 지표 | A 따로 | B examples |
|---|---:|---:|
| 성공 / 실패 | 10 / 0 | 9 / 1 |
| 노드 타입 이름 수 | 42 | 30 |
| 그중 1건에서만 나온 것 | 28 (67%) | 14 (47%) |
| 관계 이름 수 | 78 | 52 |
| 그중 1건에서만 나온 것 | 70 (90%) | 35 (67%) |
| 핵심 타입 수(노드 + 관계) | 22 | 33 |
| 핵심 타입이 모두 나온 시점 | 7번째 | 7번째 |

- 두 실행의 핵심 타입 겹침(자카드): 0.38
- A에만 있는 핵심: atmerchant, cardcompany, clause, company, handledby, makes, owns
- B에만 있는 핵심: bank, describes, dispute, fee, handlesdispute, hascard, hasfamilymember, hasfee, includesservice, linkedto, providedby, raisesdispute, request, requestsrefund, service, submitsrequest, targetscontract, transactionat
- B 핵심 상위(나온 건수): member(9), card(8), issuedby(8), hascard(8), refund(6), cardissuer(6), service(4), hasfamilymember(4), includesservice(4), hasfee(4), fee(4), contract(4), makestransaction(4), transaction(4), providedby(3), requestsrefund(3), dispute(3), handlesdispute(3), request(3), suspension(3), submitsrequest(3), account(3), merchant(3), statement(3), describes(2), document(2), targetscontract(2), raisesdispute(2), bank(2), linkedto(2), hascontract(2), transactionat(2), hasaccount(2)

| 층 | 전체 | 시작 | 비교 건수 | A에서 규칙 A | A에서 규칙 B | B에서 규칙 A | B에서 규칙 B |
|---|---:|---:|---:|---:|---:|---:|---:|
| 약관 전체 | 10 | 10 | 10 | 안 멈춤 | 안 멈춤 | 안 멈춤 | 안 멈춤 |

## consult_log (비교 건수 30)

| 지표 | A 따로 | B examples |
|---|---:|---:|
| 성공 / 실패 | 29 / 1 | 29 / 1 |
| 노드 타입 이름 수 | 45 | 14 |
| 그중 1건에서만 나온 것 | 26 (58%) | 1 (7%) |
| 관계 이름 수 | 115 | 26 |
| 그중 1건에서만 나온 것 | 87 (76%) | 10 (38%) |
| 핵심 타입 수(노드 + 관계) | 9 | 19 |
| 핵심 타입이 모두 나온 시점 | 5번째 | 8번째 |

- 두 실행의 핵심 타입 겹침(자카드): 0.22
- A에만 있는 핵심: inquiry, interactswith, refersto, transactionsummary
- B에만 있는 핵심: appliesto, card, channel, consultation, contactpreference, forcard, haspreference, hasrecord, hasrequest, includes, initiates, involves, makesrequest, requestschannel
- B 핵심 상위(나온 건수): transaction(29), includes(27), handles(24), hasrecord(22), customer(20), hasrequest(20), request(20), makesrequest(19), haspreference(19), consultation(19), channel(19), initiates(18), contactpreference(15), record(14), requestschannel(13), appliesto(12), card(11), forcard(10), involves(8)

| 층 | 전체 | 시작 | 비교 건수 | A에서 규칙 A | A에서 규칙 B | B에서 규칙 A | B에서 규칙 B |
|---|---:|---:|---:|---:|---:|---:|---:|
| 상담 전체(세그먼트 균형) | 48 | 12 | 30 | 안 멈춤 | 안 멈춤 | 13 | 20 |

## benefit_guide (비교 건수 68)

| 지표 | A 따로 | B examples |
|---|---:|---:|
| 성공 / 실패 | 68 / 0 | 66 / 2 |
| 노드 타입 이름 수 | 54 | 13 |
| 그중 1건에서만 나온 것 | 23 (43%) | 1 (8%) |
| 관계 이름 수 | 83 | 17 |
| 그중 1건에서만 나온 것 | 56 (67%) | 3 (18%) |
| 핵심 타입 수(노드 + 관계) | 11 | 13 |
| 핵심 타입이 모두 나온 시점 | 15번째 | 22번째 |

- 두 실행의 핵심 타입 겹침(자카드): 0.71
- A에만 있는 핵심: appliesto
- B에만 있는 핵심: company, haschannel, issuedby
- B 핵심 상위(나온 건수): card(62), condition(56), limit(55), hasbenefit(54), benefit(53), haslimit(52), hascondition(51), channel(28), hasfee(26), fee(26), haschannel(26), company(16), issuedby(16)

| 층 | 전체 | 시작 | 비교 건수 | A에서 규칙 A | A에서 규칙 B | B에서 규칙 A | B에서 규칙 B |
|---|---:|---:|---:|---:|---:|---:|---:|
| 공통 안내 | 4 | 4 | 4 | 안 멈춤 | 안 멈춤 | 4 | 안 멈춤 |
| 참고 카드 | 7 | 7 | 7 | 7 | 안 멈춤 | 안 멈춤 | 7 |
| 카드 개요 | 64 | 10 | 27 | 27 | 10 | 10 | 10 |
| 혜택 상세 | 85 | 10 | 30 | 안 멈춤 | 19 | 10 | 14 |

