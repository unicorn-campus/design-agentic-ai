// AI 앱 아키텍처 설계 산출물 7종 — PPT 교재 빌드 스크립트
// 규격: references/pptx-guide.md 6절 · 스크립트: textbook/script/*.md
// 실행: node textbook/build.js   (cwd = 프로젝트 루트 또는 textbook 어디서든 동작)

const path = require("path");
const pptxgen = require("pptxgenjs");

const DIR = __dirname;
const IMG = (f) => path.join(DIR, "images", f);

// ── 6-1. 팔레트 상수화 ───────────────────────────────────────────────
const C = {
  navy: "1E2A5C", blue: "2E74C6", ink: "2B3242",
  slate: "4A5364", sub: "7C8598",
  tint: "EEF3FA", altRow: "F5F8FC", tableHead: "E2EEF9",
  dark: "404155", border: "D9E0EC", line: "EDF0F6",
  coverBg: "000C32", // s01 이미지 배경 실측값 — 표지 이미지가 배경에 이어지게 함
};
const FONT = "Pretendard";

// ── 6-2. 최소 폰트 크기 강제 ─────────────────────────────────────────
const MIN_FONT = 12;
const fs12 = (size) => {
  if (size < MIN_FONT) throw new Error(`fontSize ${size} < ${MIN_FONT}pt 금지! 슬라이드를 분리할 것`);
  return size;
};

// ── 레이아웃 좌표 (16 x 9 inch) ──────────────────────────────────────
const L = {
  mx: 0.55,            // 좌측 여백
  colW: 6.35,          // 좌측 텍스트 열 너비
  imgX: 7.35, imgW: 8.1, imgH: 5.4,   // 우측 이미지 (3:2)
  bodyY: 2.15,         // 콘텐츠 시작
  bodyBottom: 7.9,     // 콘텐츠 끝
  barH: 0.42, itemH: 0.37, rowH: 0.32, gap: 0.14,
};

let pptx; // main()에서 주입

// ── 6-3. 헤더 바 헬퍼 ───────────────────────────────────────────────
function headerBar(slide, { x, y, w, text, accent = false }) {
  slide.addShape(pptx.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h: L.barH, rectRadius: 0.06,
    fill: { color: accent ? C.blue : C.navy }, line: { type: "none" },
  });
  slide.addText(text, {
    x: x + 0.12, y, w: w - 0.24, h: L.barH, align: "left", valign: "middle",
    color: "FFFFFF", bold: true, fontSize: fs12(15), fontFace: FONT,
  });
}

// ── 6-4. 넘버 배지 헬퍼 ─────────────────────────────────────────────
function numBadge(slide, { x, y, n, color = C.blue, size = 0.26 }) {
  slide.addShape(pptx.shapes.ROUNDED_RECTANGLE, {
    x, y, w: size, h: size, rectRadius: 0.05, fill: { color }, line: { type: "none" },
  });
  slide.addText(String(n), {
    x, y, w: size, h: size, align: "center", valign: "middle",
    color: "FFFFFF", bold: true, fontSize: fs12(12), fontFace: FONT,
  });
}

// ── 6-5. 페이지 헤더 헬퍼 ───────────────────────────────────────────
function pageHeader(slide, { crumb, title, lead }) {
  slide.addText(crumb, {
    x: L.mx, y: 0.42, w: 12, h: 0.3, color: C.sub, fontSize: fs12(13), fontFace: FONT,
  });
  slide.addText(title, {
    x: L.mx, y: 0.70, w: 14.9, h: 0.72, color: C.navy, bold: true,
    fontSize: fs12(34), fontFace: FONT,
  });
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: L.mx, y: 1.52, w: 14.9, h: 0.04, fill: { color: C.border }, line: { type: "none" },
  });
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: L.mx, y: 1.52, w: 2.1, h: 0.04, fill: { color: C.blue }, line: { type: "none" },
  });
  if (lead) {
    slide.addText(lead, {
      x: L.mx, y: 1.64, w: 14.9, h: 0.34, color: C.slate,
      fontSize: fs12(16), fontFace: FONT,
    });
  }
}

// ── 항목 목록(불릿 또는 넘버 배지) ──────────────────────────────────
function itemList(slide, { x, y, w, items, numbered = false }) {
  let cy = y;
  items.forEach((t, i) => {
    if (numbered) {
      numBadge(slide, { x, y: cy + 0.05, n: i + 1 });
      slide.addText(t, {
        x: x + 0.36, y: cy, w: w - 0.36, h: L.itemH, valign: "middle",
        color: C.ink, fontSize: fs12(13), fontFace: FONT,
      });
    } else {
      slide.addShape(pptx.shapes.RECTANGLE, {
        x: x + 0.04, y: cy + 0.15, w: 0.09, h: 0.09,
        fill: { color: C.blue }, line: { type: "none" },
      });
      slide.addText(t, {
        x: x + 0.26, y: cy, w: w - 0.26, h: L.itemH, valign: "middle",
        color: C.ink, fontSize: fs12(13), fontFace: FONT,
      });
    }
    cy += L.itemH;
  });
  return cy;
}

// ── 6-9. 표 ─────────────────────────────────────────────────────────
function dataTable(slide, { x, y, w, head, rows }) {
  const body = [
    head.map((h) => ({ text: h, options: { fill: C.tableHead, color: C.navy, bold: true } })),
    ...rows.map((r, ri) =>
      r.map((cell) => ({
        text: cell,
        options: { fill: ri % 2 === 1 ? C.altRow : "FFFFFF", color: C.ink },
      }))
    ),
  ];
  slide.addTable(body, {
    x, y, w, rowH: L.rowH, fontSize: fs12(12), fontFace: FONT, valign: "middle",
    border: { type: "solid", color: C.line, pt: 1 },
  });
  return y + L.rowH * (rows.length + 1);
}

// ── 이미지 + 캡션 ───────────────────────────────────────────────────
function figure(slide, { x, y, w, h, file, caption }) {
  slide.addImage({ path: IMG(file), x, y, w, h });
  if (caption) {
    slide.addShape(pptx.shapes.ROUNDED_RECTANGLE, {
      x, y: y + h + 0.08, w: Math.min(w, 4.6), h: 0.30, rectRadius: 0.15,
      fill: { color: C.tint }, line: { color: C.border, pt: 1 },
    });
    slide.addText(caption, {
      x: x + 0.12, y: y + h + 0.08, w: Math.min(w, 4.6) - 0.24, h: 0.30, valign: "middle",
      color: C.navy, bold: true, fontSize: fs12(12), fontFace: FONT,
    });
  }
}

// ── 틴트 콜아웃 박스 (남는 아래 여백을 메움) ────────────────────────
function calloutBox(slide, { x, y, w, text, title = "짚고 갈 것" }) {
  const h = Math.max(0.9, Math.min(1.6, L.bodyBottom - y));
  if (h < 0.85) return y;
  slide.addShape(pptx.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: C.tint }, line: { color: C.border, pt: 1 },
  });
  slide.addShape(pptx.shapes.RECTANGLE, {
    x, y: y + 0.12, w: 0.06, h: h - 0.24, fill: { color: C.blue }, line: { type: "none" },
  });
  slide.addText(title, {
    x: x + 0.20, y: y + 0.10, w: w - 0.40, h: 0.26,
    color: C.navy, bold: true, fontSize: fs12(12), fontFace: FONT,
  });
  slide.addText(text, {
    x: x + 0.20, y: y + 0.36, w: w - 0.40, h: h - 0.48, valign: "top",
    color: C.slate, fontSize: fs12(13), fontFace: FONT, lineSpacingMultiple: 1.2,
  });
  return y + h;
}

// ────────────────────────────────────────────────────────────────────
// 슬라이드 데이터 20장
// ────────────────────────────────────────────────────────────────────
const SLIDES = [
  // S01 ─ 표지
  {
    n: 1, kind: "cover",
    title: "AI 앱 아키텍처\n설계 산출물 7종",
    lead: "설계서 7장으로 AI 앱의 뼈대를 세우는 법",
    subs: ["초급자용 교재 · 20장", "사례 통일 — 런치픽(직장인 점심 추천 앱)", "2026-08-06 · design-agentic-ai"],
    img: { file: "s01-cover-constellation.png" },
  },

  // S02
  {
    n: 2, crumb: "Ⅰ. 들어가기 › 1. 왜 설계서인가",
    title: "설계서를 안 쓰면 어디서 무너지나",
    lead: "만들다 멈추는 자리는 늘 정해져 있음",
    left: { bar: "설계서 없이 시작하면", items: [
      "성공했는지 판정할 숫자가 없음",
      "어디까지가 우리 통제 밖인지 모름",
      "실패했을 때 돌아갈 곳이 없음",
      "비용이 얼마나 드는지 아무도 모름",
    ] },
    right: { bar: "설계서 7장이 답하는 것", items: [
      "무엇을 성공이라 부르나",
      "무엇이 어디에 있나",
      "누가 무엇을 책임지나",
      "막고 · 기록하고 · 올리는 법",
    ] },
    img: { file: "s02-why-design.png", caption: "설계서가 없으면 세 지점에서 멈춤" },
    callout: "세 가지 멈춤은 실제로 관찰된 것임 — 발표에서 근거를 못 대고, 가릴 곳을 못 정해 구현이 멈추고, 장애가 나면 사람이 손으로 되돌림",
  },

  // S03
  {
    n: 3, crumb: "Ⅰ. 들어가기 › 2. 산출물 7종",
    title: "7장이 각각 무엇을 정하나",
    lead: "한 장이 한 가지 질문에만 답함",
    tableFirst: true,
    table: { head: ["설계서", "무엇을 정하나"], rows: [
      ["① 목표·품질 카드", "무엇을 성공이라 부르나"],
      ["② 논리 아키텍처", "무엇이 어디에 있나"],
      ["③ 패턴·시퀀스", "어떤 순서로 엮나"],
      ["④ 역할 계약서", "혼자 하나 여럿이 하나"],
      ["⑤ 지식·도구", "답을 어느 길로 가져오나"],
      ["⑥ 가드레일·관측", "어디를 막고 뭘 기록하나"],
      ["⑦ 배포", "몇 덩어리로 나눠 올리나"],
    ] },
    right: { bar: "읽는 순서", items: [
      "번호가 곧 쓰는 순서임",
      "먼저 흐름을 그림 → 그 다음 나눔",
      "④와 ⑤는 서로를 보며 씀",
    ] },
    img: { file: "s03-seven-cards.png", caption: "번호 = 쓰는 순서" },
    callout: "마이크로서비스를 설계할 때 논리 아키텍처 → 시퀀스 → API → 클래스·데이터 순으로 가는 것과 같음. 흐름을 먼저 확정해야 그 단계를 누가 맡고 무슨 지식이 필요한지 정해짐",
  },

  // S04 ─ 이미지 중심
  {
    n: 4, kind: "wideFigure", crumb: "Ⅰ. 들어가기 › 3. 관계도",
    title: "값이 어느 방향으로 흐르나",
    lead: "굵은 선은 없으면 못 채우는 값임",
    right: { bar: "선의 뜻", items: [
      "굵은 선 — 없으면 뒤 칸을 못 채움",
      "얇은 선 — 나중에 손봐도 됨",
      "점선 — 뒤에서 앞으로 되돌아옴",
      "짧은 점선 — ⑤가 ④에 되물음",
    ] },
    img: { file: "s04-seven-relations.png", caption: "굵은 선 4개가 임계 경로임" },
    callout: "②(구조)가 ③·⑦에 값을 넘기고, ③(순서)이 ④·⑤에 단계를 넘김. 역방향 점선은 7종을 한 번에 끝내지 않고 두 바퀴 돈다는 뜻임",
  },

  // S05
  {
    n: 5, crumb: "Ⅱ. 산출물별 작성법 › ① 목표·품질속성 카드",
    title: "① 성공을 숫자로 못 박기",
    lead: "잴 수 없는 목표는 뒤 문서를 전부 막음",
    left: { bar: "이 장에서 정하는 것", items: [
      "성공 기준 딱 3개",
      "우선 품질 딱 3개(5개 중)",
      "고치기 전 숫자(기준선)",
    ] },
    right: { bar: "대충 하면 나는 사고", items: [
      "③에서 시간 예산을 감으로 나눔",
      "⑥에서 무엇을 잴지 못 정함",
      "발표에서 “왜 이 구조냐”에 못 답함",
    ] },
    img: { file: "s05-goal-card.png", caption: "성공 기준 3개 · 품질 3개로 줄임" },
    callout: "가장 흔한 실수는 기획서 지표를 전부 옮기는 것임. 런치픽은 지표 후보 14건 중 3건만 성공 기준으로 올렸음",
  },

  // S06
  {
    n: 6, crumb: "Ⅱ. 산출물별 작성법 › ① 목표·품질속성 카드",
    title: "① 시스템이 책임질 것만 고르기",
    lead: "지표마다 네 가지를 묻고 3분류로 나눔",
    left: { bar: "지표마다 묻는 4가지", items: [
      "1  실행 기록만으로 계산되나",
      "2  시스템이 직접 바꿀 수 있나",
      "3  이번 범위 안의 목표인가",
      "4  사람의 습관이 안 끼어드나",
    ] },
    right: { bar: "런치픽 판정 결과", items: [
      "지표 후보 14건 → 성공 기준 3건",
      "공동 책임 7건 · 책임 밖 3건",
      "사람이 고르는 일은 전부 공동 책임",
    ] },
    table: { head: ["지표", "원문 목표값", "판정"], rows: [
      ["추천 조회 응답 시간", "3초 이내(95%)", "시스템 책임"],
      ["알레르기 위반 노출", "0건", "시스템 책임"],
      ["결정 소요 시간", "5분 이내", "공동 책임"],
      ["구독 전환율", "5%", "공동 책임"],
      ["BEP 구독자 수", "6,667명", "책임 밖"],
    ] },
    img: { file: "s06-metric-decision-tree.png", caption: "1·3 탈락은 책임 밖 · 2·4는 공동 책임" },
  },

  // S07
  {
    n: 7, crumb: "Ⅱ. 산출물별 작성법 › ② 논리 아키텍처",
    title: "② 어디부터가 우리 통제 밖인가",
    lead: "경계선을 못 그으면 가릴 곳을 못 정함",
    left: { bar: "이 장에서 정하는 것", items: [
      "우리 시스템 밖에 무엇이 있나",
      "우리 시스템 안을 몇 덩어리로 나누나",
      "통제 밖으로 나가는 선(경계)",
      "진짜로 붙는 것 vs 흉내(Mock)",
    ] },
    right: { bar: "대충 하면 나는 사고", items: [
      "가릴 곳을 못 정해 ⑤·⑥이 막힘",
      "⑦에서 몇 덩어리로 쪼갤지 논쟁만 함",
      "구현 때 없는 API를 부름",
    ] },
    img: { file: "s07-trust-boundary.png", caption: "경계는 데이터가 넘어가는 곳에 그음" },
    callout: "②는 위치와 경계만 정함. 흐름(④)·책임(③)·가리는 법(⑤)·배포(⑦)를 여기서 앞서 쓰면 값이 두 문서에 생김",
  },

  // S08
  {
    n: 8, crumb: "Ⅱ. 산출물별 작성법 › ② 논리 아키텍처",
    title: "② 넘기지 않기로 한 것을 적기",
    lead: "가장 중요한 판정은 아예 안 보내는 것임",
    left: { bar: "경계 판정 순서", items: [
      "1  기록을 못 보게 되나",
      "2  권한 주체가 바뀌나",
      "3  개인정보가 나가나",
      "4  안 넘기기로 한 항목이 있나",
    ] },
    right: { bar: "런치픽 핵심 판정", items: [
      "경계 6개(TB-1 ~ TB-6)를 그음",
      "알레르기 항목명은 모델에 안 보냄",
      "걸러낸 뒤의 후보 목록만 보냄",
    ] },
    table: { head: ["모델 경계(TB-2)", "넘김", "넘기지 않음"], rows: [
      ["취향 카테고리 코드", "넘김", "—"],
      ["후보 식당 목록", "넘김", "—"],
      ["알레르기 항목명", "—", "칸 자체를 없앰"],
      ["정확 좌표", "—", "넘기지 않음"],
    ] },
    img: { file: "s08-block-before-model.png", caption: "막는 자리를 모델 앞으로 옮김" },
  },

  // S09 (플로니)
  {
    n: 9, crumb: "Ⅱ. 산출물별 작성법 › ③ 패턴·시퀀스 설계",
    title: "③ 순서를 못 박고 실패 자리를 정함",
    lead: "누가 어떤 순서로 움직이고 실패하면 무엇을 하나",
    left: { bar: "순서를 엮는다는 뜻", items: [
      "시작 계기별로 따로 그림",
      "기본값은 고정 순서임",
      "순서가 곧 안전 규칙임",
    ] },
    right: { bar: "실패하면 어떻게 하나", items: [
      "같은 호출 다시 — 시간을 곱함",
      "다른 길로 감 — 시간을 더함",
      "다 쓰면 갈 곳을 미리 정함",
    ] },
    table: { head: ["빠진 것", "나는 사고"], rows: [
      ["재시도 상한", "호출이 몇 배로 쏟아짐"],
      ["루프 상한", "요청이 안 끝나고 비용만 쌈"],
      ["필드 주인", "동시 두 단계가 값을 덮음"],
    ] },
    img: { file: "s09-sequence-failure-flow.png", caption: "실패는 곱하거나 더해짐" },
    callout: "이 시점에 ④ 역할은 아직 없음. 참여 주체는 ②의 구성요소에서 가져오고, 여기서 그린 단계 목록을 ④가 나눠 맡음",
  },

  // S10 (플로니)
  {
    n: 10, crumb: "Ⅱ. 산출물별 작성법 › ③ 패턴·시퀀스 설계",
    title: "③ 3초를 쪼개고 최악값도 셈",
    lead: "목표값과 포기 시각을 두 열로 나눠 검증함",
    left: { bar: "예산 쪼개는 3단", items: [
      "총 예산을 단계에 나눠 배정",
      "최악값 = 상한 × (1+재시도)",
      "병렬은 큰 값 1건만 넣음",
    ] },
    right: { bar: "두 줄로 나눠 검증", items: [
      "p95 합계 ≤ 예산 — 큐잉 포함",
      "최악값 합계 — 초과 허용",
      "초과하면 갈 곳을 1개 지정",
    ] },
    table: { head: ["구분", "값", "판정"], rows: [
      ["p95 합계", "1,800ms", "통과(예산 3,000ms)"],
      ["최악값 합계", "3,420ms", "420ms 초과"],
      ["초과 시 착지", "캐시 폴백", "예산 안으로 들어옴"],
    ] },
    img: { file: "s10-timeout-budget-split.png", caption: "두 줄로 나눠 각각 검증" },
    callout: "`p95`는 100번 중 95번이 그 안에 드는 값임. 폴백은 더 빨라지는 것이 아니라 앞 단계 상한을 소진한 뒤 도는 경로임",
  },

  // S11 (플로니)
  {
    n: 11, crumb: "Ⅱ. 산출물별 작성법 › ④ 에이전트 역할 계약서",
    title: "④ 혼자 할 일을 나누지 않기",
    lead: "에이전트는 기본이 1개임. 나눌 이유를 못 대면 나누지 않음",
    left: { bar: "기본값은 1개", items: [
      "할 일을 3 ~ 7개 한 줄씩 적음",
      "나눌 이유가 없으면 1개로 감",
      "동사로 쪼개면 개수만 늘어남",
    ] },
    right: { bar: "안 적으면 나는 사고", items: [
      "권한 경계 없어 감사에 걸림",
      "출력 칸 이름 달라 ③에 못 붙임",
      "멈출 조건 없어 같은 호출 반복",
    ] },
    table: { head: ["나눌 조건", "“예”인 때"], rows: [
      ["섞임", "규칙 3종 이상이 한 번에 들어감"],
      ["병렬", "차례로 하면 시간 목표를 넘김"],
      ["권한", "한쪽은 읽기만, 다른 쪽은 씀"],
    ] },
    img: { file: "s11-single-vs-multi-agent.png", caption: "기본은 단일, 멀티는 예외" },
    callout: "③의 단계를 묶어 나눔. 나누는 기준은 업무 종류(동사)가 아니라 읽는 자료와 손대는 권한임",
  },

  // S12 (플로니)
  {
    n: 12, crumb: "Ⅱ. 산출물별 작성법 › ④ 에이전트 역할 계약서",
    title: "④ 3문에 “예”가 없으면 1개",
    lead: "후보안을 먼저 만들고 3문으로 검사함",
    left: { bar: "판정 사다리 3단", items: [
      "③의 단계를 묶어 할 일로 봄",
      "후보안 A(1개)·B(3개)를 만듦",
      "B에만 3문을 던짐",
    ] },
    right: { bar: "헷갈리는 칸 3개", items: [
      "중단 조건 — 횟수는 ③이 씀",
      "사용 도구 — 내부 저장소는 커넥터 아님",
      "사용 모델 — 안 쓰면 안 쓴다고 적음",
    ] },
    table: { head: ["3문", "런치픽 판정", "결과"], rows: [
      ["섞임", "아니오", "1개로 충분"],
      ["병렬", "판정 불가", "초 수 못 셈"],
      ["권한", "예", "3개로 나눔"],
    ] },
    img: { file: "s12-single-multi-decision-tree.png", caption: "런치픽은 권한에서 갈림" },
    callout: "나눈 결과가 3개여도 모델을 쓰는 에이전트는 1개일 수 있음",
  },

  // S13 (지식니) — 클로니 판정 J-1: 좌측 5항목 허용
  {
    n: 13, crumb: "Ⅱ. 산출물별 작성법 › ⑤ 지식·도구 설계",
    title: "⑤ 질문마다 답을 가져올 길이 다름",
    lead: "에이전트가 무엇을 근거로 답하는지 못 박는 문서임",
    left: { bar: "답이 오는 길 5가지", items: [
      "표 — 목록·개수·합계",
      "문서 — 뜻이 가까운 문단",
      "관계 — 선을 따라 여러 홉",
      "사전 — 낱말을 코드로 고정",
      "외부 시스템 — 커넥터로 부름",
    ] },
    right: { bar: "길을 안 고르면 나는 사고", numbered: true, items: [
      "집계를 문서 검색에 던져 숫자가 흔들림",
      "이름·전화가 안 가려진 채 밖으로 나감",
      "저장소를 못 정해 배포 설계가 멈춤",
    ] },
    img: { file: "s13-knowledge-four-paths.png", caption: "질문 하나가 여러 갈래로 갈림" },
    callout: "개수·합계는 문서 검색으로는 원리적으로 못 구함. 문단을 아무리 잘 찾아도 세는 일은 안 됨",
  },

  // S14 (지식니)
  {
    n: 14, crumb: "Ⅱ. 산출물별 작성법 › ⑤ 지식·도구 설계",
    title: "⑤ 정답지를 먼저 만들고 고침",
    lead: "질문 뽑기 → 길 고르기 → 버린 길 적기 순임",
    left: { bar: "채우는 순서", items: [
      "사용자가 치는 문장 3개 적기",
      "판정 트리로 길 고르기 — 벡터 = 문서 검색",
      "버린 길 1줄 남기기",
      "원천이 틀리면 답도 틀림",
    ] },
    right: { bar: "골든셋(정답지) 만들기", numbered: true, items: [
      "검증 요구사항 1개 = 1문항",
      "2명이 풀어 갈리면 버림",
      "런치픽은 24문항 만듦",
    ] },
    table: { head: ["런치픽 질문", "고른 길", "버린 길"], rows: [
      ["주변서 뭘 먹을까", "표 조회+먼저 걸러내기", "벡터 — 색인 비용"],
      ["30일 뭘 먹었나", "고정 집계 조회", "벡터 — 집계 불가"],
      ["땅콩은 어느 재료", "용어사전", "확률 — 위반 0건 불가"],
    ] },
    img: { file: "s14-path-decision-tree.png", caption: "위에서부터 차례로 물어 내려감" },
  },

  // S15 (커넥니)
  {
    n: 15, crumb: "Ⅱ. 산출물별 작성법 › ⑥ 가드레일·관측 설계",
    title: "⑥ 막을 곳은 세 군데뿐임",
    lead: "가드레일(막는 규칙)은 입구·도구·출구 세 지점에만 걸림",
    left: { bar: "막는 곳 · 남기는 것", items: [
      "입구 — 밖에서 온 글은 데이터로만",
      "도구 — 최소 권한 · 호출 상한 · 승인",
      "출구 — 나가기 전 민감정보 검사",
      "기록 — 요청ID · 지연 · 토큰 · 실패 사유",
    ] },
    right: { bar: "안 하면 나는 사고", items: [
      "루프가 한 달 예산을 며칠에 씀",
      "전화번호가 응답 · 로그에 남음",
      "원인 단계를 못 찾아 못 고침",
    ] },
    img: { file: "s15-guardrail-three-points.png", caption: "막는 곳 3 · 기록은 별도임" },
    callout: "입구를 사용자 입력창으로만 읽으면 0건이 됨 — 외부 API 응답과 캐시에 담긴 글도 입구임. `토큰`은 모델이 글을 세는 단위임",
  },

  // S16 (커넥니)
  {
    n: 16, crumb: "Ⅱ. 산출물별 작성법 › ⑥ 가드레일·관측 설계",
    title: "⑥ 가릴 곳을 표로 세어 둠",
    lead: "출력 직전만 가리면 기록에 원문이 남음",
    tableFirst: true,
    table: { head: ["가릴 곳", "그냥 두면", "런치픽"], rows: [
      ["화면", "근거 문장에 섞임", "좌표 키 제거"],
      ["관측 기록", "프롬프트 원문 남음", "키 · 건수만"],
      ["오류 로그", "접속 문자열 통째", "사유 코드만"],
      ["접근 로그", "6개월 살아 있음", "주체 · 시각만"],
    ] },
    right: { bar: "비용 상한 세는 법", items: [
      "월 예산 ÷ 월 요청 수 = 1건당",
      "재시도 배수 × 루프 배수를 곱함",
      "런치픽 10원/건 · 새로고침 상한 미정",
    ] },
    img: { file: "s16-masking-flow-blocked.png", caption: "가리는 지점이 4곳임" },
    callout: "접근 로그는 보관 의무가 6개월이라 한 번 찍힌 원문이 6개월 살아 있음. 이 자리만 위험의 수명이 다름",
  },

  // S17 (커넥니)
  {
    n: 17, crumb: "Ⅱ. 산출물별 작성법 › ⑦ 배포 설계",
    title: "⑦ 몇 덩어리로 나눠 어디에 올리나",
    lead: "배포 단위 · 포트 · 비밀값 · 저장소 4가지를 정함",
    left: { bar: "나눌까 합칠까 4문", items: [
      "1  배포 형태가 다른가",
      "2  늘리는 기준이 다른가",
      "3  권한 등급이 다른가",
      "4  나눠도 응답시간 지키나 — 아니오면 합침",
    ] },
    right: { bar: "안 하면 나는 사고", items: [
      "배포 당일이 논쟁으로 사라짐",
      "키가 저장소 이력에 영구히 남음",
      "재시작하면 로그 · 데이터가 사라짐",
    ] },
    table: { head: ["축", "되돌리는 방법"], rows: [
      ["코드", "직전 판본 이미지로 교체"],
      ["데이터", "안 돌아옴 · 직전 1세대 보관"],
    ] },
    img: { file: "s17-deploy-units-layers.png", caption: "런타임 5 + 앱 1 · 저장소는 밖" },
    callout: "기본값은 1덩어리임. 4번째 질문이 거부권을 가짐",
  },

  // S18 (커넥니)
  {
    n: 18, crumb: "Ⅱ. 산출물별 작성법 › ⑦ 배포 설계",
    title: "⑦ 비밀값은 셈부터 시작함",
    lead: "비밀값(키 · 비밀번호)은 생각이 아니라 대상에서 뽑음",
    left: { bar: "뽑는 순서 3단", items: [
      "모델 · 저장소 · 커넥터에서 뽑음",
      "쓰는 이미지 · 주입 경로만 적음",
      "실제 값은 적지 않음",
    ] },
    right: { bar: "런치픽 결과", items: [
      "이미지 5개 + 앱 1개 = 6개",
      "저장소 6개 전부 런타임 밖",
    ] },
    table: { head: ["위반", "왜 위험한가", "대신"], rows: [
      ["이미지에 구움", "받은 누구나 꺼냄", "뜰 때 주입"],
      ["설정 파일 평문", "저장소 이력에 남음", "이름만 적음"],
      ["로그에 출력", "로그 권한 = 키 권한", "값을 가려 기록"],
    ] },
    img: { file: "s18-secret-safe-vs-violation.png", caption: "왼쪽만 안전 · 오른쪽 3종은 위반" },
    callout: "비밀값 목록을 머리로 만들면 반드시 빠짐. 대상을 훑어 기계적으로 뽑음",
  },

  // S19
  {
    n: 19, crumb: "Ⅲ. 마무리 › 1. 실제 적용 결과",
    title: "팀이 실제로 써 본 결과",
    lead: "7종을 쓰면 마지막에 대조표 1장이 더 남음",
    left: { bar: "실제 적용 숫자", items: [
      "설계서 7종 + 교차검증 + 대조표",
      "산출물 간 충돌 9건을 조정함",
      "밖에서 다시 세어 결함 30건 찾음",
      "가이드에 빈칸 86건이 드러남",
    ] },
    right: { bar: "7종 뒤에 1장 더", items: [
      "00-반영대조표 1장을 마지막에 씀",
      "점검 항목이 어디에 반영됐나",
      "범위 밖으로 뺀 것이 어디서 막히나",
    ] },
    table: { head: ["항목", "결과"], rows: [
      ["설계서 분량", "7종 3,526줄"],
      ["전체 산출물", "4,498줄"],
      ["조정한 충돌", "9건"],
      ["교차검증 결함", "30건(심각 8건)"],
    ] },
    img: { file: "s19-what-remains.png", caption: "7종 + 대조표 1장 = 제출물" },
    note: "정직한 표기 — 교재 예시로 쓴 런치픽 설계서 7종은 구현·호출·배포·측정을 하지 않은 미검증 설계임",
  },

  // S20
  {
    n: 20, crumb: "Ⅲ. 마무리 › 2. 가이드가 못 막은 것",
    title: "점검표를 다 통과해도 남는 것",
    lead: "칸이 다 찼는지만 보면 모순이 통과함",
    left: { bar: "못 막은 3가지", items: [
      "앞 문서의 전제를 안 물려받음",
      "두 문서의 값을 곱·나눌 사람이 없음",
      "칸 사이의 모순을 점검표가 통과시킴",
    ] },
    right: { bar: "그래서 이렇게 씀", items: [
      "시작 전 파라미터 12종을 먼저 채움",
      "나누기·곱하기 담당자를 정해 둠",
      "점검표에 칸끼리 대조하는 줄을 넣음",
    ] },
    table: { head: ["무너진 자리", "실제로 일어난 일"], rows: [
      ["전제 미승계", "⑦이 없는 표를 찾다 막힘"],
      ["계산 담당 공백", "심각 결함 8건 중 5건"],
      ["모순 통과", "3판까지 10항목 전부 통과"],
    ] },
    img: { file: "s20-three-cracks.png", caption: "칸이 다 차도 모순은 남음" },
    callout: "자가 점검표는 칸의 존재와 개수만 봄. 칸끼리 맞는지는 사람이 봐야 함",
  },
];

// ── 6-8. 슬라이드 생성 함수 ─────────────────────────────────────────
async function createCover(d) {
  const slide = pptx.addSlide();
  slide.background = { color: C.coverBg };
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: 0, y: 0, w: 16, h: 9, fill: { color: C.coverBg }, line: { type: "none" },
  });
  slide.addImage({ path: IMG(d.img.file), x: 8.0, y: 1.3, w: 7.6, h: 5.07 });
  slide.addShape(pptx.shapes.RECTANGLE, {
    x: 1.0, y: 2.0, w: 0.14, h: 2.3, fill: { color: C.blue }, line: { type: "none" },
  });
  slide.addText(d.title, {
    x: 1.4, y: 1.9, w: 6.6, h: 2.5, color: "FFFFFF", bold: true,
    fontSize: fs12(44), fontFace: FONT, lineSpacingMultiple: 1.15,
  });
  slide.addText(d.lead, {
    x: 1.4, y: 4.6, w: 6.6, h: 0.5, color: "AFC3E6", fontSize: fs12(18), fontFace: FONT,
  });
  let cy = 5.5;
  d.subs.forEach((t) => {
    slide.addText(t, {
      x: 1.4, y: cy, w: 6.6, h: 0.38, color: "8FA3C8", fontSize: fs12(14), fontFace: FONT,
    });
    cy += 0.44;
  });
  return slide;
}

async function createWideFigure(d) {
  const slide = pptx.addSlide({ masterName: "MASTER" });
  pageHeader(slide, d);
  // 이미지 3:2 비율 유지 — 8.25 x 5.5 (캡션이 푸터를 침범하지 않는 최대 크기)
  figure(slide, { x: L.mx, y: L.bodyY, w: 8.25, h: 5.5, file: d.img.file, caption: d.img.caption });
  const rx = 9.0, rw = 6.45;
  headerBar(slide, { x: rx, y: L.bodyY, w: rw, text: d.right.bar, accent: true });
  const cy = itemList(slide, { x: rx, y: L.bodyY + L.barH + 0.12, w: rw, items: d.right.items });
  if (d.callout) calloutBox(slide, { x: rx, y: cy + 0.22, w: rw, text: d.callout });
  return slide;
}

async function createContent(d) {
  const slide = pptx.addSlide({ masterName: "MASTER" });
  pageHeader(slide, d);

  // 우측 이미지
  figure(slide, {
    x: L.imgX, y: L.bodyY, w: L.imgW, h: L.imgH,
    file: d.img.file, caption: d.img.caption,
  });

  // 좌측 열 — 순서: (표 우선 지정 시) 표 → 우측섹션, 아니면 좌측 → 우측 → 표
  let cy = L.bodyY;
  const blocks = d.tableFirst
    ? ["table", "left", "right"]
    : ["left", "right", "table"];

  for (const b of blocks) {
    if (b === "left" && d.left) {
      headerBar(slide, { x: L.mx, y: cy, w: L.colW, text: d.left.bar });
      cy = itemList(slide, {
        x: L.mx, y: cy + L.barH + 0.10, w: L.colW,
        items: d.left.items, numbered: d.left.numbered,
      }) + L.gap;
    }
    if (b === "right" && d.right) {
      headerBar(slide, { x: L.mx, y: cy, w: L.colW, text: d.right.bar, accent: true });
      cy = itemList(slide, {
        x: L.mx, y: cy + L.barH + 0.10, w: L.colW,
        items: d.right.items, numbered: d.right.numbered,
      }) + L.gap;
    }
    if (b === "table" && d.table) {
      cy = dataTable(slide, {
        x: L.mx, y: cy, w: L.colW, head: d.table.head, rows: d.table.rows,
      }) + L.gap;
    }
  }

  if (d.callout) cy = calloutBox(slide, { x: L.mx, y: cy + 0.10, w: L.colW, text: d.callout });

  if (d.note) {
    slide.addShape(pptx.shapes.RECTANGLE, {
      x: L.mx, y: 7.98, w: 0.06, h: 0.30, fill: { color: C.blue }, line: { type: "none" },
    });
    slide.addText(d.note, {
      x: L.mx + 0.16, y: 7.96, w: 14.6, h: 0.34, color: C.navy, bold: true, italic: true,
      fontSize: fs12(12), fontFace: FONT,
    });
  }

  if (cy - L.gap > L.bodyBottom + 0.35) {
    console.warn(`  ⚠ S${String(d.n).padStart(2, "0")} 좌측 열이 ${(cy - L.gap).toFixed(2)}″ 까지 내려감 (한계 ${L.bodyBottom}″)`);
  }
  return slide;
}

// ── 6-11. 진입점 ────────────────────────────────────────────────────
async function main() {
  pptx = new pptxgen();
  pptx.defineLayout({ name: "CUSTOM", width: 16, height: 9 });
  pptx.layout = "CUSTOM";

  pptx.defineSlideMaster({
    title: "MASTER",
    background: { color: "FFFFFF" },
    objects: [
      { rect: { x: 0.55, y: 8.34, w: 14.9, h: 0.02, fill: { color: "E9ECF3" } } },
      { text: {
          text: "AI 앱 아키텍처 설계 산출물 7종 · design-agentic-ai",
          options: { x: 0.55, y: 8.40, w: 9, h: 0.3, color: C.sub, fontSize: 12, fontFace: FONT },
      } },
    ],
    slideNumber: { x: 14.9, y: 8.40, w: 0.55, h: 0.3, align: "right", color: C.sub, fontSize: 12, fontFace: FONT },
  });

  for (const d of SLIDES) {
    if (d.kind === "cover") await createCover(d);
    else if (d.kind === "wideFigure") await createWideFigure(d);
    else await createContent(d);
  }

  const out = path.join(DIR, "AI앱아키텍처설계-산출물7종-교재.pptx");
  await pptx.writeFile({ fileName: out });
  console.log(`✅ PPT 생성 완료 — 슬라이드 ${SLIDES.length}장`);
  console.log(`   ${out}`);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
