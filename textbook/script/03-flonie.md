> **[역할|플로니]** 교재 슬라이드 스크립트 — 담당 4장(S09·S10·S11·S12). 공통 규격: [_spec.md](../_spec.md)  
> **2026-08-06 순서 판정 반영** — 시퀀스가 `③`(S09·S10), 역할 계약서가 `④`(S11·S12)로 번호와 순서가 바뀜.
> 강의 노트 본문의 `③`·`④` 표기는 옛 번호가 남아 있을 수 있으므로 위 슬라이드 제목을 기준으로 읽음

# PPT 교재 스크립트 — ③ 에이전트 역할 계약서 · ④ 패턴·시퀀스 설계

작성: 2026-08-06 · 작성자: 플로니(오케스트레이션 엔지니어)  
원문 출처: [③ 설계서](../../design/04-에이전트역할계약서.md) · [④ 설계서](../../design/03-패턴시퀀스설계.md) ·
[③ 가이드](../../guides/04-에이전트역할계약서-가이드.md) · [④ 가이드](../../guides/03-패턴시퀀스설계-가이드.md)

**예시 값 원칙** — 슬라이드에 실은 숫자는 전부 `design/03`·`design/04` 원문에서 확인한 값임.
원문에 없는 값은 `[확인필요]`로 남기고 지어내지 않음.

---

## S09. ③ 패턴·시퀀스 설계 — 무엇을 정하나

- 패턴: A
- breadcrumb: Ⅱ. 산출물별 작성법 › ③ 패턴·시퀀스 설계
- 제목: 순서를 못 박고 실패 자리를 미리 정함
- 리드문: 누가 어떤 순서로 움직이고 실패하면 무엇을 하나

### 좌측 — 순서를 엮는다는 뜻

- 시작 계기별로 따로 그림
- 기본값은 고정 순서임
- 순서가 곧 안전 규칙임

### 우측 — 실패하면 어떻게 하나

- 같은 호출 다시 — 시간을 곱함
- 다른 길로 감 — 시간을 더함
- 다 쓰면 갈 곳을 미리 정함

### 표

| 빠진 것 | 나는 사고 |
|---------|-----------|
| 재시도 상한 | 호출이 몇 배로 쏟아짐 |
| 루프 상한 | 요청이 안 끝나고 비용만 쌈 |
| 필드 주인 | 동시 두 단계가 값을 덮음 |

### 이미지

- 파일명: `s09-sequence-failure-flow.png`
- 배치: 우측
- 캡션: 실패는 곱하거나 더해짐
- 이미지 프롬프트:

```
Horizontal flow diagram infographic, left to right, thin gray connector lines with small arrowheads.
Main line: four rounded boxes in a row labeled "시작", "순서", "확인", "종료".
From the "확인" box, one downward branch to a small diamond labeled "실패".
From that diamond, two divergent paths drawn in bright blue:
the upper one loops back to "순서" with a small circular arrow labeled "다시",
the lower one goes to a separate box labeled "다른 길" which rejoins the main line before "종료".
Below the lower path, one distinct box with a thicker navy border labeled "착지",
connected upward into the "다른 길" box.
Korean labels only, no sentences inside the image, exactly these labels and nothing else.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C
and bright blue #2E74C6 accents, thin gray connectors, generous white space,
no gradients on text, no 3D, no photo
```

### 강의 노트

- 쉬운 말 먼저 — `트리거(처리를 시작시키는 계기)` · `직렬(차례로)` · `병렬(동시에)` ·
  `최악값(재시도까지 다 겹쳤을 때의 소요시간)`. 다음 장 계산이 이 4개 낱말로 굴러감.
- 런치픽 트리거는 3종임 — 동기 요청 `S-R`(사용자가 기다림) · 스케줄 배치 `S-B` · 이벤트 `S-E`.
  섞으면 예산이 엉키므로 도식을 따로 그림(`design/04` 1절).
- 패턴 후보 5종 중 **고정 워크플로우**를 골랐음. 이유가 취향이 아니라 안전 요건임 —
  필터가 LLM보다 먼저 돌아야 하는데 모델이 순서를 고르게 하면 필터를 건너뛸 경로가 생김(`design/04` 2절).
- 우측 3줄이 다음 장 계산 규칙의 예고임. "곱하나 더하나"가 최악값 계산의 전부임.
- 표 3행은 가이드 1절의 사고 3줄과 같음. 재시도 폭주 · 무한 루프 · 병렬 덮어쓰기가 실무 3대 장애임.

---

## S10. ③ — 어떻게 채우나

- 패턴: D
- breadcrumb: Ⅱ. 산출물별 작성법 › ③ 패턴·시퀀스 설계
- 제목: 3초를 단계로 쪼개고 최악값도 함께 셈
- 리드문: 목표값과 포기 시각을 두 열로 나눠 검증함

### 좌측 — 예산 쪼개는 3단

- 총 예산을 단계에 나눠 배정
- 최악값 = 상한 × (1+재시도)
- 병렬은 큰 값 1건만 넣음

### 우측 — 두 줄로 나눠 검증

- p95 합계 ≤ 예산 — 큐잉 포함
- 최악값 합계 — 초과 허용
- 초과하면 갈 곳을 1개 지정

### 표

| 구분 | 값 | 판정 |
|------|-----|------|
| p95 합계 | 1,800ms | 통과(예산 3,000ms) |
| 최악값 합계 | 3,420ms | 420ms 초과 |
| 초과 시 착지 | 캐시 폴백 | 예산 안으로 들어옴 |

### 이미지

- 파일명: `s10-timeout-budget-split.png`
- 배치: 하단 전폭
- 캡션: 두 줄로 나눠 각각 검증
- 이미지 프롬프트:

```
Layered box diagram with a numeric sum, arranged as two horizontal tracks stacked vertically.
Upper track labeled "배정값": a row of eight small rounded boxes of varying widths containing
only the numbers 50, 20, 100, 150, 200, 900, 100, 50; one pair of boxes is bracketed together
with a small tag labeled "병렬"; the row ends at a bold total box containing 1,800.
Lower track labeled "상한": a matching row of eight wider boxes containing only the numbers
100, 50, 200, 300, 800, 1,200, 200, 100, ending at a bold total box containing 3,420;
a small tag labeled "최악값" sits above this total.
To the right of both totals, one vertical reference bar containing 3,000 with a tag labeled "예산";
the lower total overshoots past the bar, marked with a small tag labeled "초과",
and an arrow from it points down to one rounded box with a thicker navy border labeled "착지".
Numbers and the Korean labels only, no sentences inside the image, exactly these labels and nothing else.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C
and bright blue #2E74C6 accents, thin gray connectors, generous white space,
no gradients on text, no 3D, no photo
```

### 강의 노트

- 열을 왜 2개로 나누나 — 1열로 쓰면 `여유`가 오독됨. `p95 배정값`은 목표할 시간(재시도를 곱하지 않음),
  `타임아웃(상한)`은 포기할 시각(곱함)임. 두 개념을 한 칸에 섞은 것이 초기 판의 실제 오류였음(`design/04` 9-1절 D-9).
- 런치픽 계산을 숨기지 않고 보임 — p95 합계 `50+20+100+150+200+50+150+10+900+20+100+50 = 1,800ms`,
  최악값 합계 `100+50+200+300+800+100+300+20+1,200+50+200+100 = 3,420ms`. 병렬 구간은 최댓값 1건만 넣음.
- 판정 2줄 — p95 1,800 ≤ 3,000 통과(큐잉에 쓸 여유 1,200ms) / 최악값 3,420 > 3,000 초과 420ms.
  **초과를 값을 낮춰 없애지 않았음.** 최악값은 초과가 허용되나 착지 노드가 필수임 → `L-3 캐시 폴백`.
- 재시도를 붙이지 않은 곳도 이유를 남김 — LLM 호출(`S-R10`)은 상한 1,200ms이라 재시도 1회를 붙이면
  최악값이 4,620ms가 됨. 재시도 대신 폴백으로 감(`design/04` 9-1절).
- 폴백은 "더 빨라지는 것"이 아님. 앞 단계 타임아웃을 **소진한 뒤** 도는 경로이므로 조립 시간이 더해짐 —
  `L-2 경로 폴백`은 최악값 3,570ms로 오히려 늘어남. `L-3 캐시 폴백`만 단계가 빠져 줄어듦(2,120ms).
- 루프는 3개이며 `max_iter` 값 2건은 원문에 없어 `[확인필요]`로 남겼으나 **착지 노드는 지금 정함**(안전 종료).
  상한이 열려 있으면 시간이 아니라 요청당 비용에 천장이 없어짐(`design/04` 10절).
- 상태 필드는 23종이며 필드마다 갱신 주체를 1개만 둠. 병렬 구간은 애초에 다른 필드로 갈라 두어
  덮어쓰기로도 값이 사라지지 않게 함(`design/04` 7절).
- 구현 프레임워크를 묻는 질문이 나오면 — LangGraph는 노드 단위로 타임아웃과 재시도를 따로 걸 수 있고,
  재시도마다 타임아웃 시계가 다시 시작됨(context7 확인일 2026-08-06 · LangGraph fault-tolerance 문서).
  즉 `최악값 = 상한 × (1+재시도)` 산식이 이 런타임 동작과 어긋나지 않음. 단 ④는 패턴만 정하고
  프레임워크를 지정하지 않음(`design/04` 2절).

---
## S11. ④ 에이전트 역할 계약서 — 무엇을 정하나

- 패턴: A
- breadcrumb: Ⅱ. 산출물별 작성법 › ④ 에이전트 역할 계약서
- 제목: 혼자 할 일을 여럿에게 나누지 않기
- 리드문: 에이전트는 기본이 1개임. 나눌 이유를 못 대면 나누지 않음

### 좌측 — 기본값은 1개

- 할 일을 3 ~ 7개 한 줄씩 적음
- 나눌 이유가 없으면 1개로 감
- 동사로 쪼개면 개수만 늘어남

### 우측 — 안 적으면 나는 사고

- 권한 경계 없어 감사에 걸림
- 출력 칸 이름 달라 ④가 못 붙임
- 멈출 조건 없어 같은 호출 반복

### 표

| 나눌 조건 | "예"인 때 |
|-----------|-----------|
| 섞임 | 규칙 3종 이상이 한 번에 들어감 |
| 병렬 | 차례로 하면 시간 목표를 넘김 |
| 권한 | 한쪽은 읽기만, 다른 쪽은 씀 |

### 이미지

- 파일명: `s11-single-vs-multi-agent.png`
- 배치: 우측
- 캡션: 기본은 단일, 멀티는 예외
- 이미지 프롬프트:

```
Side-by-side comparison infographic, two panels separated by a thin vertical gray divider.
Left panel: one large rounded box labeled "단일" with a small badge above it labeled "기본값";
three small gray task chips stacked inside the single box, connected by thin gray lines to
one tool icon row below (simple abstract cylinder and cloud shapes, no letters inside).
Right panel: three separate rounded boxes labeled "멀티", each with a distinct border weight,
with a small badge above them labeled "예외"; three short vertical gates below the boxes
labeled "섞임", "병렬", "권한", and one small badge labeled "3문" attached to the gate row.
The right panel is visually gated behind the three labels so it reads as conditional.
Korean labels only, no sentences inside the image, exactly these labels and nothing else.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C
and bright blue #2E74C6 accents, thin gray connectors, generous white space,
no gradients on text, no 3D, no photo
```

### 강의 노트

- 이 장의 결론 한 줄임 — "나눌 이유를 대라." 근거는 A01(단일이 기본값)이며 가이드 2-1절 판정 사다리에 그대로 들어가 있음.
- 우측 사고 3건은 실제 장애 순서로 읽으면 이해가 빠름. 권한 경계 누락은 감사에서, 출력 키 불일치는 통합 시점에,
  중단 조건 누락은 운영 중 재시도 폭주로 각각 다른 시점에 터짐.
- 표의 3조건은 "후보안을 검사하는 도구"임. 후보안 없이 3문만 던지면 판정 자체가 성립하지 않음을 강조함.
- 초급자가 가장 많이 넘어지는 곳 — 업무 종류(동사)로 쪼개는 습관임. 나누는 기준은 읽는 자료와 손대는 권한임.
- 다음 장에서 런치픽으로 실제 판정을 밟아 보인다고 예고함.

---

## S12. ④ — 어떻게 채우나

- 패턴: D
- breadcrumb: Ⅱ. 산출물별 작성법 › ④ 에이전트 역할 계약서
- 제목: 3문에 하나도 "예"가 없으면 1개
- 리드문: 후보안을 먼저 만들고 3문으로 검사함

### 좌측 — 판정 사다리 3단

- 할 일을 7개 뽑음
- 후보안 A(1개)·B(3개)를 만듦
- B에만 3문을 던짐

### 우측 — 헷갈리는 칸 3개

- 중단 조건 — 횟수는 ④가 씀
- 사용 도구 — 내부 저장소는 커넥터 아님
- 사용 모델 — 안 쓰면 안 쓴다고 적음

### 표

| 3문 | 런치픽 판정 | 결과 |
|-----|-------------|------|
| 섞임 | 아니오 | 1개로 충분 |
| 병렬 | 판정 불가 | 초 수 못 셈 |
| 권한 | 예 | 3개로 나눔 |

### 이미지

- 파일명: `s12-single-multi-decision-tree.png`
- 배치: 하단 전폭
- 캡션: 런치픽은 권한에서 갈림
- 이미지 프롬프트:

```
Top-down decision tree infographic, three levels, thin gray connector lines with small arrowheads.
Level 1: one rounded box labeled "할 일" (7 small gray dots inside representing items).
Level 2: two boxes side by side labeled "후보안", the right one drawn with a thicker navy border.
Level 3: three diamond decision nodes in a row labeled "섞임", "병렬", "권한";
the first two diamonds branch left with a small tag labeled "아니오",
the third diamond branches right with a small tag labeled "예".
Bottom: two terminal boxes, a grayed-out one labeled "단일" and a highlighted bright blue one
labeled "3개", with the highlighted path traced in bright blue from "권한" down to "3개".
Korean labels only, no sentences inside the image, exactly these labels and nothing else.
clean flat vector infographic, corporate consulting style, white background, deep navy #1E2A5C
and bright blue #2E74C6 accents, thin gray connectors, generous white space,
no gradients on text, no 3D, no photo
```

### 강의 노트

- 런치픽 실제 판정임 — 할 일 7개(J-1 ~ J-7) → 후보안 A(단일)·B(3개) → Q1 아니오 · Q2 판정 불가 · Q3 예 → 3개 분할.
  출처는 `design/03` 1절임.
- Q2를 "예"로 쓰지 않은 이유를 꼭 짚음 — 순차 실행이 3초를 몇 초 넘기는지 셀 근거가 기획 산출물에 없었음.
  넘기는 초 수를 못 적으면 "예"로 판정하지 않음. `[확인필요: 단계별 지연 예산]`으로 남긴 자리임.
- 나눈 결과는 3개이나 **LLM을 쓰는 에이전트는 1개**임. 나머지 2개는 `모델 미사용(결정론적 실행)`임(`design/03` 3절).
  "나눴다 = 모델이 3개다"가 아님을 분명히 함.
- 우측 3칸이 실제 리뷰에서 가장 많이 반려되는 칸임. 특히 중단 조건에 "재시도 2회 후 중단"을 적는 실수는
  ③·④ 경계 위반임(G-5). ③은 "무엇을 보면 멈추나"까지만 씀.
- 금지어 4종(`전체`·`필요시`·`관련 데이터`·`적절한`) 검색으로 자가 점검함. 런치픽은 4종 모두 0건임.

---


## 작성 기록 (슬라이드에는 들어가지 않음)

| 항목 | 결과 |
|------|------|
| 담당 슬라이드 수 | 4장(S09·S10·S11·S12) — 규격 2절과 일치함 |
| 이미지 블록 | 4개. 파일명·배치·캡션·프롬프트 4항목 전부 채움 |
| 도식 유형 | S11 비교 대조(좌우) · S12 판정 트리 · S09 흐름도 · S10 계층 박스 + 숫자 합계 — 4장 모두 다름 |
| 한글 라벨 수 | S11 8개 · S12 8개 · S09 8개 · S10 6개 — 전부 8개 이하, 1개 6자 이하 |
| 슬라이드 총 글자 수 | 4장 모두 250자 이하(제목·리드문·좌우 항목·표·캡션 합산 기준) |
| 지어낸 숫자 | 0건. 1,800ms · 3,420ms · 3,000ms · 420ms는 `design/04` 9-1절 원문 값임 |
| 이미지 생성 | 수행하지 않음(규격 7절 — 생성은 모달니 담당) |

**미검증 항목** — 이미지 프롬프트는 실제로 생성해 보지 않은 상태임. 한글 라벨 렌더링 결과와
숫자 8개가 들어간 S10 도식의 가독성은 1장 생성 후 확인이 필요함.
