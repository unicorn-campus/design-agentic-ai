> **[역할|지식니]** 설계 산출물 ⑤ 지식·도구 설계 — 교재 슬라이드 S13·S14 스크립트

# ⑤ 지식·도구 설계 — 슬라이드 스크립트 2장

작성: 2026-08-06 · 작성자: 지식니(지식·데이터 엔지니어)  
근거: [guides/05-지식도구설계-가이드.md](../../guides/05-지식도구설계-가이드.md) ·
[design/05-지식도구설계.md](../../design/05-지식도구설계.md)  
규격: [textbook/_spec.md](../_spec.md) 3·4·5절 준수. 예시 값은 `design/05` 원문에서 확인된 것만 씀

---

## S13. ⑤ 지식·도구 설계 — 무엇을 정하나

- 패턴: A
- breadcrumb: Ⅱ. 산출물별 작성법 › ⑤ 지식·도구 설계
- 제목: 질문마다 답을 가져올 길이 다름
- 리드문: 에이전트가 무엇을 근거로 답하는지 못 박는 문서임

### 좌측 — 답이 오는 길 4가지

- 표 — 목록·개수·합계
- 문서 — 뜻이 가까운 문단
- 관계 — 선을 따라 여러 홉
- 외부 시스템 — 커넥터로 부름

### 우측 — 길을 안 고르면 나는 사고

1. 집계를 문서 검색에 던져 숫자가 흔들림
2. 이름·전화가 안 가려진 채 밖으로 나감
3. 저장소를 못 정해 배포 설계가 멈춤

### 이미지

- 파일명: `s13-knowledge-four-paths.png`
- 배치: 하단 전폭
- 캡션: 질문 하나가 네 갈래로 갈림
- 이미지 프롬프트:

```
A hierarchical box diagram, top-down, three tiers. Top tier: one rounded rectangle
labeled "질문" in deep navy fill with white text, centered. Thin gray connectors fan
out downward to the middle tier of four equal-width rectangles side by side, left to
right, each with a bright blue top border and white body: "표 조회", "문서 검색",
"관계 검색", "외부 호출". Inside each middle box place one simple line icon above the
label: a small grid table, a stacked document sheet, three dots joined by two lines,
a plug-and-socket. Bottom tier: four thin gray arrows converge from the four boxes
into one wide light-tint bar labeled "답" in navy text. Korean labels only, exactly
six labels total, no other text anywhere in the image.
clean flat vector infographic, corporate consulting style, white background,
deep navy #1E2A5C and bright blue #2E74C6 accents, thin gray connectors,
generous white space, no gradients on text, no 3D, no photo
```

- 크기 `1536x1024` · 품질 `medium` · 형식 `png`

### 강의 노트

- 이 장의 한 문장은 "질문을 먼저 보고 길을 고른다"임. 스택(어떤 DB·어떤 모델)은 뒤 순서임
- 길 4가지에 다섯째가 하나 더 있음 — 용어사전(낱말을 코드로 1:1 고정). 알레르기·규제 낱말처럼
  틀리면 되돌릴 수 없는 값은 확률 검색에 맡기지 않고 사전으로 못 박음. S14 표 3행이 그 예임
- 우측 사고 3가지는 `guides/05` 1절 원문임. 3번은 실제로 일어남 — 저장소 종류가 안 정해지면
  ⑦ 배포 설계가 시작 지점에서 멈춤
- 초급자가 가장 많이 하는 실수는 "전부 문서 검색으로"임. 개수·합계는 뜻이 가까운 문단을 찾는
  방식으로는 원리적으로 못 구함. 문단을 아무리 잘 찾아도 세는 일은 안 됨
- 런치픽 실제 결과를 미리 알려 주면 좋음 — 질문 유형 5종 중 문서 검색(벡터 RAG) 채택이 **0건**임
  (`design/05` 2절). 길을 나눠 판정했더니 한 길이 통째로 빠진 사례임

---

## S14. ⑤ — 어떻게 채우나

- 패턴: D
- breadcrumb: Ⅱ. 산출물별 작성법 › ⑤ 지식·도구 설계
- 제목: 정답지를 먼저 만들고 검색을 고침
- 리드문: 질문 뽑기 → 길 고르기 → 버린 길 적기 순임

### 좌측 — 채우는 순서

- 사용자가 치는 문장 3개 적기
- 판정 트리로 길 고르기
- 버린 길 1줄 남기기
- 원천이 틀리면 답도 틀림

### 우측 — 골든셋(정답지) 만들기

1. 검증 요구사항 1개 = 1문항
2. 2명이 풀어 갈리면 버림
3. 런치픽은 24문항 만듦

### 표

| 런치픽 질문 | 고른 길 | 버린 길 |
|---|---|---|
| 주변서 뭘 먹을까 | 표 조회+하드필터 | 벡터 — 색인 비용 |
| 30일 뭘 먹었나 | 고정 집계 조회 | 벡터 — 집계 불가 |
| 땅콩은 어느 재료 | 용어사전 | 확률 — 위반 0건 불가 |

### 이미지

- 파일명: `s14-path-decision-tree.png`
- 배치: 우측
- 캡션: 위에서부터 차례로 물어 내려감
- 이미지 프롬프트:

```
A vertical decision tree, five rungs, read top to bottom. At the top a rounded
rectangle labeled "질문" in deep navy fill with white text. Below it a single vertical
spine of five small diamonds in bright blue outline, containing only the numerals
1, 2, 3, 4, 5 — one numeral per diamond, no words inside the diamonds. From each
diamond one short arrow branches to the RIGHT into a white rectangle with a bright
blue left edge, labeled in order: "표 조회", "집계", "벡터", "그래프", "사전". The
spine continues straight down from each diamond to the next with a thin gray
connector. Korean labels appear only at the top box and the five right-hand boxes,
six Korean labels total; the only other characters in the image are the numerals
1 to 5. No sentences anywhere.
clean flat vector infographic, corporate consulting style, white background,
deep navy #1E2A5C and bright blue #2E74C6 accents, thin gray connectors,
generous white space, no gradients on text, no 3D, no photo
```

- 크기 `1536x1024` · 품질 `medium` · 형식 `png`
- 도식의 번호 1 ~ 5가 무엇을 묻는지는 아래 강의 노트로 말함(규격 5절 규칙 6 적용)

### 강의 노트

- 판정 트리 번호 1 ~ 5가 묻는 것임. 위에서부터 예/아니오로 내려가며, 예가 나오면 거기서 멈춤
  1. 답이 조건에 맞는 **목록**인가(반경·필터·정렬) → **표 조회**
  2. 답이 **개수·합계·추이**인가 → **집계**
  3. 답이 문서 1 ~ 2군데 문장인가 → **벡터**(뜻이 가까운 문단 찾기)
  4. 관계를 2번 이상 건너가야 하나 → **그래프**
  5. 사내 코드·용어를 1:1로 고정해야 하나 → **사전**(용어사전·온톨로지)
- 첫 줄이 왜 맨 위인가 — 데이터가 대부분 표인 앱은 답이 `목록`임. 이 줄이 없으면 넷 다 아니오가
  되어 전부 `[확인필요]`로 떨어짐
- **원천 오류율을 먼저 재는 이유** — 검색을 손봐도 원본이 틀리면 답도 틀림. 순서가 2단임.
  1단 그 원천이 실제로 있나(없으면 오류율이 아니라 `경로 불가`), 2단 오류율을 쟀나
- 런치픽에서 이 2단이 실제로 걸렸음 — 알레르기 하드필터가 쓸 식재료·알레르겐 원천이 외부 API에
  있는지 확인되지 않아 `[확인필요: 식당 식재료·알레르겐 정보 원천]`으로 남음. 원천이 없으면
  페일세이프가 반경 내 전 식당을 제외해 **추천 0개**가 됨. `design/05` 설계서에서 가장 무거운 미확정임
- 골든셋 만드는 법 — 문의 로그가 없는 신규 서비스는 유저스토리 `[검증 요구사항]` 1항목을 문항
  1개로 바꿈. 그것이 곧 정답 조건임. 문항마다 `질문 / 정답 / 근거 문서·행`을 적고 2명이 따로 풀어
  답이 갈리면 버림
- 비율 목표는 문항 수를 먼저 셈 — 목표가 `95%`면 필요 표본이 `1 ÷ (1 − 0.95) = 20`개임.
  6문항이면 눈금이 커서 합격선이 사실상 100%가 됨
- 런치픽 합격선(`design/05` 11절 원문) — 정답 포함률 **90% 이상**, 알레르기 위반 **0건(100% 통과)**,
  근거 동반 노출률 **100%**, 근거 태그 일치율 **95% 이상**(①에서 인용한 `추정`값)
- 버린 길도 반드시 1줄 적음. 런치픽은 그래프 검색을 뺐는데 이유가 두 개임 — 이을 원료 데이터가
  없고, 메뉴 텍스트 수십만 건 추출 비용이 14주 MVP 계획 밖임. 안 적으면 다음 분기에 다시 못 판단함
- 조회 경로는 **읽기 전용 계정**만 씀. `INSERT`·`UPDATE`·`DELETE`를 막고 1회 응답 행 수 상한을 걺.
  런치픽은 프리미엄 무제한 이력의 상한 숫자가 원문에 없어 `[확인필요]`로 되물음. 지어내지 않음
