> **[역할|오케스트레이터|클로니]** 담당 슬라이드 S01 ~ S08 · S19 · S20 스크립트  
> 규격: [_spec.md](../_spec.md) · 예시 원문: `design/01-목표품질속성카드.md`, `design/02-논리아키텍처.md`  
> 예시로 쓴 런치픽 설계서 7종은 **미검증 설계**임(구현·호출·배포·측정을 하지 않음). S19에서 1회 명시함

---

## S01. 표지

- 패턴: E
- breadcrumb: (없음)
- 제목: AI 앱 아키텍처 설계 산출물 7종
- 리드문: 설계서 7장으로 AI 앱의 뼈대를 세우는 법

### 좌측 — (없음)
- (표지는 텍스트 4줄만 둠)

### 우측 — (없음)
- 부제: 초급자용 교재 · 20장
- 하단: 2026-08-06 · design-agentic-ai
- 하단: 사례 통일 — 런치픽(직장인 점심 추천 앱)

### 이미지
- 파일명: `s01-cover-constellation.png`
- 배치: 우측
- 캡션: (없음)
- 이미지 프롬프트:
```
Abstract minimal constellation of seven rounded rectangle nodes connected by thin lines,
arranged as a loose network, no text and no labels at all, deep navy #1E2A5C and bright
blue #2E74C6 shapes on a very dark navy background, subtle glow, generous empty space,
clean flat vector infographic, corporate consulting style, no gradients on text, no 3D,
no photo, no letters, no numbers
```

### 강의 노트
AI 앱은 프롬프트를 잘 쓰면 되는 일로 오해받음. 실제로 무너지는 곳은 프롬프트가 아니라 구조임.
이 교재는 그 구조를 문서 7장으로 나눠 쓰는 법을 다룸.
20장 전체가 하나의 사례(점심 추천 앱 런치픽)로 관통하므로 도메인 지식은 필요 없음.

---

## S02. 설계서를 왜 쓰나

- 패턴: A
- breadcrumb: Ⅰ. 들어가기 › 1. 왜 설계서인가
- 제목: 설계서를 안 쓰면 어디서 무너지나
- 리드문: 만들다 멈추는 자리는 늘 정해져 있음

### 좌측 — 설계서 없이 시작하면
- 성공했는지 판정할 숫자가 없음
- 어디까지가 우리 통제 밖인지 모름
- 실패했을 때 돌아갈 곳이 없음
- 비용이 얼마나 드는지 아무도 모름

### 우측 — 설계서 7장이 답하는 것
- 무엇을 성공이라 부르나
- 무엇이 어디에 있나
- 누가 무엇을 책임지나
- 막고 · 기록하고 · 올리는 법

### 이미지
- 파일명: `s02-why-design.png`
- 배치: 하단 전폭
- 캡션: 설계서가 없으면 세 지점에서 멈춤
- 이미지 프롬프트:
```
Clean flat vector infographic, corporate consulting style, white background. A horizontal
process arrow going left to right with three red-orange break marks cutting across it.
Above the arrow, three small rounded rectangle cards in deep navy #1E2A5C with short Korean
labels: "기준 없음", "경계 없음", "복구 없음". At the far right a single bright blue #2E74C6
rounded rectangle labeled "멈춤". Thin gray connectors, generous white space, no other text,
no gradients on text, no 3D, no photo
```

### 강의 노트
세 가지 멈춤이 실제로 관찰된 것임을 강조함.
기준 없음 → 발표 때 "왜 이 구조인가"에 답을 못 함.
경계 없음 → 개인정보를 어디서 가릴지 못 정해 구현이 멈춤.
복구 없음 → 장애가 나면 사람이 손으로 되돌림.

---

## S03. 산출물 7종 한눈에

- 패턴: D
- breadcrumb: Ⅰ. 들어가기 › 2. 산출물 7종
- 제목: 7장이 각각 무엇을 정하나
- 리드문: 한 장이 한 가지 질문에만 답함

### 좌측 — 설계서 7종
| 설계서 | 무엇을 정하나 |
|--------|-------------|
| ① 목표·품질 카드 | 무엇을 성공이라 부르나 |
| ② 논리 아키텍처 | 무엇이 어디에 있나 |
| ③ 패턴·시퀀스 | 어떤 순서로 엮나 |
| ④ 역할 계약서 | 혼자 하나 여럿이 하나 |
| ⑤ 지식·도구 | 답을 어느 길로 가져오나 |
| ⑥ 가드레일·관측 | 어디를 막고 뭘 기록하나 |
| ⑦ 배포 | 몇 덩어리로 나눠 올리나 |

### 우측 — 읽는 순서
- 번호가 곧 쓰는 순서임
- 먼저 흐름을 그림 → 그 다음 나눔
- ④와 ⑤는 서로를 보며 씀

### 이미지
- 파일명: `s03-seven-cards.png`
- 배치: 우측
- 캡션: 번호 = 쓰는 순서
- 이미지 프롬프트:
```
Clean flat vector infographic, corporate consulting style, white background. Seven wide
rounded rectangle bars stacked in a vertical column. Each bar contains a white circled
number on its left AND a large Korean label centered in the bar. From top to bottom the
pairs are exactly: circled 1 with label "목표", circled 2 with label "구조", circled 3 with
label "순서", circled 4 with label "역할", circled 5 with label "지식/도구", circled 6 with label
"가드레일/관측", circled 7 with label "배포". Bars alternate deep navy #1E2A5C and bright blue
#2E74C6 fill, label text in white. A thin gray vertical arrow runs down the left side of
the column from top to bottom. One curved thin gray double-headed arrow on the right side
links the bar labeled "역할" with the bar labeled "지식/도구". EVERY bar must contain its Korean
label — no empty bars. Exactly seven Korean labels and seven numbers, no other text, no
sentences. Generous white space, no gradients on text, no 3D, no photo, no extra letters
```

### 강의 노트
7종은 서로 다른 질문에 답하므로 하나를 빼면 다른 문서가 그 자리를 대신 채우려다 값이 두 곳에 생김.
**번호가 곧 쓰는 순서임.** 마이크로서비스를 설계할 때 `논리 아키텍처 → 시퀀스 → API → 클래스·데이터`
순으로 가는 것과 같음 — 흐름을 먼저 확정해야 그 단계를 누가 맡고(④) 무슨 지식이 필요한지(⑤) 정해짐.
④와 ⑤는 서로를 참고함(민감 필드 ID ↔ 에이전트 권한).

---

## S04. 7종의 관계도

- 패턴: E
- breadcrumb: Ⅰ. 들어가기 › 3. 관계도
- 제목: 값이 어느 방향으로 흐르나
- 리드문: 굵은 선은 없으면 못 채우는 값임

### 좌측 — (없음)
- (이미지 전폭 슬라이드)

### 우측 — (없음)
- 굵은 선 = 없으면 뒤 칸을 못 채움
- 얇은 선 = 나중에 손봐도 됨
- 점선 = 뒤에서 앞으로 되돌아옴
- 짧은 점선 = ⑤가 ④에 되물음

### 이미지
- 파일명: `s04-seven-relations.png`
- 배치: 하단 전폭
- 캡션: 굵은 선 4개가 임계 경로임
- 이미지 프롬프트:
```
Clean flat vector infographic dependency diagram, corporate consulting style, white
background, landscape layout. Seven rounded rectangle nodes with short Korean labels placed
in a single horizontal row, evenly spaced, in this exact order: "목표", "구조", "순서",
"역할", "지식/도구", "가드레일/관측", "배포". Each node's width adapts to its label so every
label sits on ONE line without wrapping. Arrows, all starting and ending exactly on a node edge — no
arrow may end in empty space:
(a) thick deep navy #1E2A5C arrows between adjacent nodes: 구조 to 순서, 순서 to 역할,
역할 to 지식/도구;
(b) one thick deep navy line routed ABOVE the row, leaving the top edge of 목표 and entering
the top edge of 순서 with the arrowhead pointing DOWN into 순서;
(c) one thin light gray line routed ABOVE the row, higher than (b), leaving the top edge of
구조 and entering the top edge of 배포 with the arrowhead pointing DOWN into 배포;
(d) thin light gray adjacent arrows: 목표 to 구조, 지식/도구 to 가드레일/관측,
가드레일/관측 to 배포;
(e) two dashed bright blue #2E74C6 curved arrows routed BELOW the row: one leaving 순서 and
entering 목표, one leaving 가드레일/관측 and entering 순서;
(f) one short dashed bright blue arrow below the row from 지식/도구 into 역할.
EVERY node must contain its Korean label — exactly seven Korean labels, no other text,
no legend, no numbers, no sentences. Generous white space, no gradients on text, no 3D,
no photo, no extra letters
```

### 강의 노트
굵은 선 4개가 임계 경로임 — 이 4개가 늦으면 뒤 문서 여러 개가 한꺼번에 멈춤.
②(구조)가 ③·⑦에 값을 넘기고, ③(순서)이 ④·⑤에 단계를 넘김. 그래서 ③이 늦으면 두 개가 함께 멈춤.
점선 2개는 실제로 필요함 — ③이 시간 예산을 쪼갠 결과를 ①에 되돌려 줘야 ①이 옳은 채로 닫힘.
역방향 화살표가 있다는 것은 7종을 한 번에 완성하지 않고 두 바퀴 돈다는 뜻임.

---

## S05. ① 목표·품질속성 카드 — 무엇을 정하나

- 패턴: A
- breadcrumb: Ⅱ. 산출물별 작성법 › ① 목표·품질속성 카드
- 제목: 성공을 숫자로 못 박기
- 리드문: 잴 수 없는 목표는 뒤 문서를 전부 막음

### 좌측 — 이 장에서 정하는 것
- 성공 기준 딱 3개
- 우선 품질 딱 3개(5개 중)
- 고치기 전 숫자(기준선)

### 우측 — 대충 하면 나는 사고
- ③에서 시간 예산을 감으로 나눔
- ⑥에서 무엇을 잴지 못 정함
- 발표에서 "왜 이 구조냐"에 못 답함

### 이미지
- 파일명: `s05-goal-card.png`
- 배치: 우측
- 캡션: 성공 기준 3개 · 품질 3개로 줄임
- 이미지 프롬프트:
```
Clean flat vector infographic, corporate consulting style, white background. Left side
shows a cluster of about twelve small light gray rounded squares labeled only with tiny
gray dots, representing many candidate metrics. A thin gray funnel shape narrows toward
the right. Right side shows exactly three deep navy #1E2A5C rounded rectangle cards in a
column with short Korean label "성공 기준" above them, and beside them three bright blue
#2E74C6 rounded rectangle cards with short Korean label "우선 품질" above them. Generous
white space, no sentences, no gradients on text, no 3D, no photo
```

### 강의 노트
가장 흔한 실수는 기획서의 지표를 전부 옮기는 것임. 시스템이 책임질 수 있는 것만 골라야 함.
런치픽 사례에서 지표 후보 14건 중 성공 기준으로 올라간 것은 3건뿐임.
5개 품질(정확성·응답시간·설명가능성·안전성·비용효율성) 중 3개만 고르고, 버린 2개에도 이유를 1줄 남김.

---

## S06. ① — 어떻게 채우나

- 패턴: D
- breadcrumb: Ⅱ. 산출물별 작성법 › ① 목표·품질속성 카드
- 제목: 시스템이 책임질 수 있는 것만 고르기
- 리드문: 지표마다 네 가지를 묻고 3분류로 나눔

### 좌측 — 지표마다 묻는 4가지
- 실행 기록만으로 계산되나
- 시스템이 직접 바꿀 수 있나
- 이번 범위 안의 목표인가
- 사람의 습관이 안 끼어드나

### 우측 — 런치픽 판정 결과
- 지표 후보 14건 → 성공 기준 3건
- 공동 책임 7건 · 책임 밖 3건
- 사람이 고르는 일은 전부 공동 책임

### 표
| 지표 | 원문 목표값 | 판정 |
|------|-----------|------|
| 추천 조회 응답 시간 | p95 3초 이내 | 시스템 책임 |
| 알레르기 위반 노출 | 0건 | 시스템 책임 |
| 결정 소요 시간 | 5분 이내 | 공동 책임 |
| 구독 전환율 | 5% | 공동 책임 |
| BEP 구독자 수 | 6,667명 | 책임 밖 |

### 이미지
- 파일명: `s06-metric-decision-tree.png`
- 배치: 우측
- 캡션: 네 질문 중 하나만 아니오면 탈락
- 이미지 프롬프트:
```
Clean flat vector infographic decision tree, corporate consulting style, white background,
top to bottom flow. One bright blue #2E74C6 rounded rectangle at top with short Korean
label "지표". Below it four gray diamond shapes in a vertical chain, each containing only
a single large number 1, 2, 3, 4. From each diamond a thin gray arrow branches right to a
small light gray rounded rectangle. The box right of diamond 1 has Korean label "책임 밖",
right of diamond 2 "공동 책임", right of diamond 3 "책임 밖", right of diamond 4
"공동 책임". At the bottom of the chain
a deep navy #1E2A5C rounded rectangle with short Korean label "성공 기준". Generous white
space, no sentences, no gradients on text, no 3D, no photo
```

### 강의 노트
네 질문은 순서대로 물음 — 실행 기록으로 계산되나(1) · 직접 바꿀 수 있나(2) · 이번 범위인가(3) ·
사람 습관이 안 끼나(4). 1·3에서 탈락하면 책임 밖이고 2·4에서 탈락하면 공동 책임임.
공동 책임은 버리지 않고 별도 표에 `목표값 = 공동 책임 — 목표 미설정`으로 남겨 ⑥에 넘김.
런치픽은 4번(사람 습관) 탈락이 7건으로 절반을 넘었음 — 소비자 앱의 특징임.
목표값에 숫자와 단위가 없으면 그 줄은 미완성임. 지어내지 말고 `[확인필요]`로 남김.

---

## S07. ② 논리 아키텍처 — 무엇을 정하나

- 패턴: A
- breadcrumb: Ⅱ. 산출물별 작성법 › ② 논리 아키텍처
- 제목: 어디부터가 우리 통제 밖인가
- 리드문: 경계선을 못 그으면 가릴 곳을 못 정함

### 좌측 — 이 장에서 정하는 것
- 우리 시스템 밖에 무엇이 있나
- 우리 시스템 안을 몇 덩어리로 나누나
- 통제 밖으로 나가는 선(경계)
- 진짜로 붙는 것 vs 흉내(Mock)

### 우측 — 대충 하면 나는 사고
- 가릴 곳을 못 정해 ⑤·⑥이 막힘
- ⑦에서 몇 덩어리로 쪼갤지 논쟁만 함
- 구현 때 없는 API를 부름

### 이미지
- 파일명: `s07-trust-boundary.png`
- 배치: 우측
- 캡션: 경계는 데이터가 넘어가는 곳에 그음
- 이미지 프롬프트:
```
Clean flat vector infographic boundary diagram, corporate consulting style, white
background. In the center one large deep navy #1E2A5C rounded rectangle with short Korean
label "우리 시스템". Around it four smaller light gray rounded rectangles each enclosed by
its own bright blue #2E74C6 dashed border box, with short Korean labels "모델", "지도",
"결제", "로그인". Thin gray arrows run from the center box to each of the four boxes,
crossing the dashed borders. Generous white space, no sentences, no legend, no gradients
on text, no 3D, no photo
```

### 강의 노트
경계는 조직 경계가 아니라 데이터가 넘어가는 곳에 그음. 세 가지를 물어 판정함 —
넘으면 우리가 기록을 못 보나 · 권한 주체가 바뀌나 · 개인정보가 나가나.
②는 위치와 경계만 정함. 흐름(④)·책임(③)·가리는 방법(⑤)·배포(⑦)를 여기서 앞서 쓰면
같은 값이 두 문서에 생겨 반드시 어긋남.
Mock은 `실물(예정)`으로 적지 않음 — 값은 `실물`·`Mock` 둘뿐이고 계획은 사유 칸에 씀.

---

## S08. ② — 어떻게 채우나

- 패턴: D
- breadcrumb: Ⅱ. 산출물별 작성법 › ② 논리 아키텍처
- 제목: 넘기지 않기로 한 것을 표로 적기
- 리드문: 가장 중요한 판정은 아예 안 보내는 것임

### 좌측 — 경계 판정 순서
- 기록을 못 보게 되나
- 권한 주체가 바뀌나
- 개인정보가 나가나
- 안 넘기기로 한 항목이 있나

### 우측 — 런치픽 핵심 판정
- 경계 6개를 그어 번호를 붙임
- TB = 신뢰 경계(Trust Boundary)
- 알레르기 항목명은 모델에 안 보냄
- 걸러낸 뒤의 후보 목록만 보냄

### 표
| 모델 경계 | 넘김 | 넘기지 않음 |
|----------------|------|-----------|
| 취향 카테고리 코드 | 넘김 | — |
| 후보 식당 목록 | 넘김 | — |
| 알레르기 항목명 | — | 칸 자체를 없앰 |
| 정확 좌표 | — | 넘기지 않음 |

### 이미지
- 파일명: `s08-block-before-model.png`
- 배치: 우측
- 캡션: 막는 자리를 모델 앞으로 옮김
- 이미지 프롬프트:
```
Clean flat vector infographic side by side comparison, corporate consulting style, white
background, split by a thin vertical gray line. Left half titled with short Korean label
"위험" shows a horizontal flow of three boxes with a red-orange X mark on the last one and
short Korean labels "입력", "모델", "필터". Right half titled with short Korean label "안전"
shows a horizontal flow of three boxes with a green check mark and short Korean labels
"입력", "필터", "모델", where the filter box is deep navy #1E2A5C and the model box is
bright blue #2E74C6. Generous white space, no sentences, no gradients on text, no 3D,
no photo
```

### 강의 노트
경계 판정에서 가장 중요한 것은 네 번째 질문임 — 아예 안 넘기기로 한 항목이 있나.
런치픽은 알레르기 항목명을 모델에 보내지 않기로 정했고, 입력 규격에서 칸 자체를 없앰.
칸이 없으면 넣을 경로가 없어 스키마가 규칙을 강제함. ⑤·⑥의 가리기보다 앞선 방어선임.
그래서 하드필터(걸러내기)를 모델 호출 앞에 둠 — 모델은 이미 걸러진 목록만 받음.
경계에 번호를 붙이는 이유는 ⑤·⑥이 그 번호로 인용하기 때문임. `TB`는 Trust Boundary(신뢰 경계)의 약자임.

---

## S19. 7종을 다 쓰면 무엇이 남나

- 패턴: D
- breadcrumb: Ⅲ. 마무리 › 1. 실제 적용 결과
- 제목: 팀이 실제로 써 본 결과
- 리드문: 7종을 쓰면 마지막에 대조표 1장이 더 남음

### 좌측 — 실제 적용 숫자
- 설계서 7종 + 검증 + 대조표
- 산출물 간 충돌 9건을 조정함
- 밖에서 다시 세어 결함 30건 찾음
- 가이드에 빈칸 86건이 드러남

### 우측 — 7종 뒤에 1장 더
- `00-반영대조표` 1장을 마지막에 씀
- 점검 항목이 어디에 반영됐나
- 범위 밖으로 뺀 것이 어디서 막히나

### 표
| 항목 | 결과 |
|------|------|
| 설계서 분량 | 7종 3,526줄 |
| 전체 산출물 | 4,498줄 |
| 조정한 충돌 | 9건 |
| 교차검증 결함 | 30건(심각 8건) |

### 이미지
- 파일명: `s19-what-remains.png`
- 배치: 우측
- 캡션: 7종 + 대조표 1장 = 제출물
- 이미지 프롬프트:
```
Clean flat vector infographic, corporate consulting style, white background. Seven small
deep navy #1E2A5C rounded rectangle document icons arranged in a horizontal row, each with
two thin white lines suggesting text. Thin gray arrows from all seven converge into one
larger bright blue #2E74C6 rounded rectangle document icon on the right, with short Korean
label "대조표" beneath it. Above the seven icons a short Korean label "설계서 7종".
Generous white space, no sentences, no gradients on text, no 3D, no photo
```

### 강의 노트
이 숫자는 팀원 5명이 런치픽 기획 자료에 가이드 7종을 실제로 적용해 본 결과임.
중요한 것은 결함 30건이 **가이드를 지켜 쓴 뒤에도** 남았다는 점임 — 바깥에서 다시 세야 나옴.
정직한 표기 1건 — 런치픽 설계서 7종은 구현·호출·배포·측정을 하지 않은 **미검증 설계**임.
문서가 완성됐다는 것이 동작한다는 뜻이 아님.

---

## S20. 흔히 무너지는 3가지

- 패턴: A
- breadcrumb: Ⅲ. 마무리 › 2. 가이드가 못 막은 것
- 제목: 점검표를 다 통과해도 남는 것
- 리드문: 칸이 다 찼는지만 보면 모순이 통과함

### 좌측 — 못 막은 3가지
- 앞 문서의 전제를 안 물려받음
- 두 문서의 값을 곱·나눌 사람이 없음
- 칸 사이의 모순을 점검표가 통과시킴

### 우측 — 그래서 이렇게 씀
- 시작 전 파라미터 12종을 먼저 채움
- 나누기·곱하기 담당자를 정해 둠
- 점검표에 칸끼리 대조하는 줄을 넣음

### 표
| 무너진 자리 | 실제로 일어난 일 |
|-----------|---------------|
| 전제 미승계 | ⑦이 없는 표를 찾다 막힘 |
| 계산 담당 공백 | 심각 결함 8건 중 5건 |
| 모순 통과 | 3판까지 10항목 전부 통과 |

### 이미지
- 파일명: `s20-three-cracks.png`
- 배치: 우측
- 캡션: 칸이 다 차도 모순은 남음
- 이미지 프롬프트:
```
Clean flat vector infographic, corporate consulting style, white background. A checklist
panel on the left as a light gray rounded rectangle containing five rows, each row a green
check mark next to a short thin gray bar, no text. On the right three deep navy #1E2A5C
rounded rectangle cards in a column, each split by a red-orange jagged crack line down the
middle, with short Korean labels "전제", "계산", "모순". A thin gray arrow points from the
checklist panel to the three cards. Generous white space, no sentences, no gradients on
text, no 3D, no photo
```

### 강의 노트
세 가지 모두 실제 테스트에서 관찰된 것임. 특히 두 번째가 뼈아픔 —
①은 총량, ④는 단계 배정, ⑦은 자원 상한, ⑥은 비용 상한을 각자 규격대로 지켰는데
`총량 ÷ 단계`, `동시 사용자 × 점유 비율`을 아무도 하지 않았음. 심각 결함 8건 중 5건이 그 자리임.
세 번째 — ③에 모델은 적혀 있는데 그 모델을 부르는 도구가 없는 모순이 점검 3판을 통과함.
자가 점검표는 칸의 존재와 개수만 봄. 칸끼리 맞는지는 사람이 봐야 함.
마무리 한 줄 — 설계서는 완성되는 것이 아니라 두 바퀴 돌며 틀린 곳을 드러내는 도구임.
