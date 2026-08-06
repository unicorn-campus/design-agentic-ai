> **[역할|커넥니]** 교재 슬라이드 스크립트 — S15 · S16(⑥ 가드레일·관측) · S17 · S18(⑦ 배포)  
> 규격: [textbook/_spec.md](../_spec.md)  
> 예시 값 출처: [design/06](../../design/06-가드레일관측설계.md) · [design/07](../../design/07-배포설계.md)  
> **예시 값은 두 설계서가 스스로 `미검증 설계`로 표기한 문서상 판정임** — 실제 호출·측정·배포를 하지 않았음

---

## S15. ⑥ 가드레일·관측 설계 — 무엇을 정하나

- 패턴: A
- breadcrumb: Ⅱ. 산출물별 작성법 › ⑥ 가드레일·관측 설계
- 제목: 막을 곳은 세 군데뿐임
- 리드문: 가드레일(막는 규칙)은 입구·도구·출구 세 지점에만 걸림

### 좌측 — 막는 곳 · 남기는 것
- 입구 · 밖에서 온 글은 데이터로만
- 도구 · 최소 권한 · 호출 상한 · 승인
- 출구 · 나가기 전 민감정보 검사
- 기록 · 요청ID · 지연 · 토큰 · 실패 사유

### 우측 — 안 하면 나는 사고
- 루프가 한 달 예산을 며칠에 씀
- 전화번호가 응답 · 로그에 남음
- 원인 단계를 못 찾아 못 고침

### 이미지
- 파일명: `s15-guardrail-three-points.png`
- 배치: 우측
- 캡션: 막는 곳 3 · 기록은 별도임

- 이미지 프롬프트:
```
Boundary diagram of an AI agent with three checkpoints. A large rounded rectangle in the center
labeled "우리 안" holds three stacked small boxes representing agent steps. Outside the rectangle,
left side labeled "밖" with an inbound arrow entering through a shield-shaped gate labeled "입구".
Right side has an outbound arrow leaving through a second shield-shaped gate labeled "출구".
A downward arrow from the center rectangle passes a third shield-shaped gate labeled "도구"
toward a small external service box. Below the center rectangle, a thin cylinder labeled "기록"
receives a dashed arrow from the inside. Exactly six Korean labels, no other text, no sentences.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C and
bright blue #2E74C6 accents, thin gray connectors, generous white space, no gradients on text,
no 3D, no photo
```

### 강의 노트
- ⑥은 새 단계를 만드는 문서가 아님. ④가 정한 시퀀스 단계 위에 태그만 얹는 오버레이라고 못 박고 시작함
- 입구를 "사용자 입력창"으로만 읽으면 0건이 됨. 외부 API 응답과 캐시에 담긴 문자열도 입구임을 강조함
- 런치픽은 자유 입력창이 없는데도 입구가 5곳 나왔음(식당 목록 조회·검사·캐시 적재·캐시 읽기·프롬프트 적재)
- 기록은 "로그 남김"이 아니라 항목을 세어 적는 것임. 항목이 없으면 사고 후에 원인을 못 찾음

---

## S16. ⑥ — 어떻게 채우나

- 패턴: D
- breadcrumb: Ⅱ. 산출물별 작성법 › ⑥ 가드레일·관측 설계
- 제목: 가릴 곳을 표로 세어 둠
- 리드문: 출력 직전만 가리면 기록에 원문이 남음

### 표
| 가릴 곳 | 그냥 두면 | 런치픽 |
|---|---|---|
| 화면 | 근거 문장에 섞임 | 좌표 키 제거 |
| 관측 기록 | 프롬프트 원문 남음 | 키 · 건수만 |
| 오류 메시지 | 접속 문자열 통째 | 사유 코드만 |
| 접근 로그 | 6개월 살아 있음 | 주체 · 시각만 |

### 우측 — 비용 상한 세는 법
- 월 예산 ÷ 월 요청 수 = 1건당
- 재시도 배수 × 루프 배수를 곱함
- 런치픽 10원/건 · 새로고침 상한 미정

### 이미지
- 파일명: `s16-masking-flow-blocked.png`
- 배치: 하단 전폭
- 캡션: 가리는 지점이 4곳임

- 이미지 프롬프트:
```
Horizontal flow diagram with four masking checkpoints. A single left-to-right spine of thin gray
arrows starts from one rounded box and branches into four parallel lanes. Each lane ends in a
rounded box, in this order: "화면", "관측 기록", "오류 로그", "접근 로그". On every one of the four
lanes, place an identical small circular block icon (a circle with a diagonal bar) directly before
the end box, and label only the first icon "가림". Draw a thin dashed bracket spanning the lower
three lanes to show they are often forgotten. Exactly five Korean labels, no other text,
no sentences, no English abbreviations inside icons.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C and
bright blue #2E74C6 accents, thin gray connectors, generous white space, no gradients on text,
no 3D, no photo
```

### 강의 노트
- 초급자가 가장 자주 무너지는 지점임 — 마스킹(가리기)을 화면 출력 직전 1곳에만 걸고 끝냄
- 런치픽 설계서는 가리는 대상에 관측 기록 · 오류 메시지 · 감사 로그 · 접근 로그 4행을 따로 넣었음(M-1 ~ M-4)
- 접근 로그는 6개월 보관 의무라 한 번 찍힌 원문이 6개월 살아 있음. 이 자리만 위험의 수명이 다름
- 비용은 월 300만 원 ÷ 월 30만 건 = 10원/건까지 나왔으나, 새로고침 상한이 미정이라 곱할 배수가 없음
- 그래서 감시 지표를 금액이 아니라 요청당 모델 호출 건수로 바꿨음. 모델 호출 단계가 1곳뿐이라 배분이 무의미함

---

## S17. ⑦ 배포 설계 — 무엇을 정하나

- 패턴: A
- breadcrumb: Ⅱ. 산출물별 작성법 › ⑦ 배포 설계
- 제목: 몇 덩어리로 나눠 어디에 올리나
- 리드문: 배포 단위 · 포트 · 비밀값 · 저장소 4가지를 정함

### 좌측 — 나눌까 합칠까 4문
- 배포 형태가 다른가
- 늘리는 기준이 다른가
- 권한 등급이 다른가
- 나눠도 응답시간 지키나 — 아니오면 합침

### 우측 — 안 하면 나는 사고
- 배포 당일이 논쟁으로 사라짐
- 키가 저장소 이력에 영구히 남음
- 재시작하면 로그 · 데이터가 사라짐

### 표
| 축 | 되돌리는 방법 |
|---|---|
| 코드 | 직전 판본 이미지로 교체 |
| 데이터 | 안 돌아옴 · 직전 1세대 보관 |

### 이미지
- 파일명: `s17-deploy-units-layers.png`
- 배치: 우측
- 캡션: 덩어리 6개 · 저장소는 밖

- 이미지 프롬프트:
```
Layered box diagram with three horizontal tiers. Top tier: one rounded box labeled "앱", separated
by a thin dashed line to show a different delivery route. Middle tier: a large rounded container
labeled "런타임" holding five equal boxes in a row labeled "진입", "추천", "회원", "결제",
"예약 작업"; a small numeric badge "443" sits on the left edge of the "진입" box only. Bottom tier:
outside and below the container, a row of three small cylinders under one bracket labeled "저장소".
Thin gray vertical connectors link the tiers. Exactly seven Korean labels plus one number,
no other text, no sentences.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C and
bright blue #2E74C6 accents, thin gray connectors, generous white space, no gradients on text,
no 3D, no photo
```

### 강의 노트
- 기본값은 1덩어리임. 4문 중 하나라도 `예`면 나눔 후보이고, 4번째 질문이 거부권을 가짐
- 런치픽은 4문을 짝 8개에 돌려 런타임 이미지 5개 + 앱 스토어 1개 = 6개로 확정했음
- 나눈 근거를 행마다 적게 함. "깔끔해 보여서" 3개 넘게 나누는 것이 가장 흔한 실패임
- 되돌리기는 축이 2개임 — 코드는 직전 판본 이미지로 돌아가나, 덮어쓴 데이터는 이미지를 되돌려도 안 돌아옴
- 런치픽은 되돌릴 수 없는 데이터 변경 4건을 지목했음. 그중 취향 벡터 갱신에 직전 1세대 보관을 요구함

---

## S18. ⑦ — 어떻게 채우나

- 패턴: D
- breadcrumb: Ⅱ. 산출물별 작성법 › ⑦ 배포 설계
- 제목: 비밀값은 셈부터 시작함
- 리드문: 비밀값(키 · 비밀번호)은 생각이 아니라 대상에서 뽑음

### 좌측 — 뽑는 순서 3단
- 모델 · 저장소 · 커넥터에서 뽑음
- 쓰는 이미지 · 주입 경로만 적음
- 실제 값은 적지 않음

### 표
| 위반 | 왜 위험한가 | 대신 |
|---|---|---|
| 이미지에 구움 | 받은 누구나 꺼냄 | 뜰 때 주입 |
| 설정 파일 평문 | 저장소 이력에 남음 | 이름만 적음 |
| 로그에 출력 | 로그 권한 = 키 권한 | 값을 가려 기록 |

### 우측 — 런치픽 결과
- 이미지 5개 + 앱 1개 = 6개
- 저장소 6개 전부 런타임 밖

### 이미지
- 파일명: `s18-secret-safe-vs-violation.png`
- 배치: 하단 전폭
- 캡션: 왼쪽만 안전 · 오른쪽 3종은 위반

- 이미지 프롬프트:
```
Side-by-side comparison diagram split by one thin vertical gray line. Left half labeled "안전":
a padlock-shaped box labeled "보관소" with a single arrow into a rounded box labeled "이미지",
the arrow drawn as a dashed line to indicate injection at start time. Right half labeled "위반":
three stacked small rows, each ending in a circular block icon (circle with a diagonal bar);
the three rows are labeled "이미지", "설정 파일", "로그" and each carries a small numeric badge
1, 2, 3 on its left. Exactly six Korean labels plus three numbers, no other text, no sentences.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C and
bright blue #2E74C6 accents, thin gray connectors, generous white space, no gradients on text,
no 3D, no photo
```

### 강의 노트
- 비밀값 목록을 머리로 만들면 반드시 빠짐. 모델 · 정형 저장소 · 커넥터 · 이미지 저장소 · 관측처를 훑어 기계적으로 뽑음
- 문서에는 항목명 · 쓰는 이미지 · 주입 경로만 적음. 실제 키 문자열은 어디에도 적지 않음
- 위반 3종 중 3번이 가장 자주 나옴 — 접속 실패 로그에 접속 문자열이 통째로 찍힘
- 런치픽은 접근 로그를 6개월 보관하므로, 한 번 찍힌 키가 6개월 남는 구조임. 3번의 대가가 특히 큼
- 런치픽은 MCP를 안 쓰기로 판정했으나 `핸들 보관 위치` 행은 `해당 없음`으로 남겼음. 지우면 판정한 사실이 사라짐
