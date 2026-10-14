// node build.js — 우리 시스템에 그래프 검색이 필요한 이유 한 장 빌드 (script.md 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const LEFT_W = 4.55;                 // 왼편(지금 검색) 폭
const RX = X0 + LEFT_W + 0.2;        // 오른편(관계망) 시작 x
const RW = X0 + CW - RX;             // 오른편 폭

// 원천별 노드 색 — 정형 DB · 카드 혜택 문서 · 상담 이력
const SRC = { db: C.navy, doc: C.blue, talk: C.dark };

// 관계망 노드: 원천 색으로 채운 둥근 상자
function node(s, t, { x, y, src, w = 1.55, h = 0.5 }) {
  L.card(s, t, { x, y, w, h, fill: SRC[src], line: null, color: C.white, size: 16, bold: true, r: 0.12 });
  return { x, y, w, h, cx: x + w / 2, cy: y + h / 2, r: x + w, b: y + h };
}

// 관계 이름표: 선 위에 흰 바탕 글자를 얹어 선과 겹쳐도 읽히게 함
function edgeLabel(s, t, { cx, cy, w = 0.8 }) {
  L.card(s, t, { x: cx - w / 2, y: cy - 0.15, w, h: 0.3, fill: C.white, line: null, color: C.slate, size: 14, r: 0.05 });
}

// 지금 검색 카드: 굵은 이름 + 예시 질문, 오른쪽에 판정 필
function searchCard(s, { y, h, name, how, ask, verdict, dark = false }) {
  const fill = dark ? C.dark : C.white;
  L.rr(s, { x: X0, y, w: LEFT_W, h, fill, line: dark ? null : C.border, r: 0.08 });
  const runs = [
    { text: name, options: { fontSize: fs(16), bold: true, color: dark ? C.white : C.navy } },
    { text: how ? `  ${how}` : "", options: { fontSize: fs(14), color: dark ? C.white : C.slate, breakLine: !!ask } },
  ];
  if (ask) runs.push({ text: ask, options: { fontSize: fs(14), color: C.ink } });
  s.addText(runs, { x: X0 + 0.1, y, w: LEFT_W - 1.0, h, fontFace: FONT, valign: "middle", margin: 4, isTextBox: true,
    paraSpaceAfter: 0 });
  L.card(s, verdict, { x: X0 + LEFT_W - 0.82, y: y + h / 2 - 0.18, w: 0.7, h: 0.36, size: 14, bold: true, r: 0.18,
    fill: dark ? C.white : C.tint, line: dark ? null : C.pill, color: dark ? C.dark : C.blue });
}

// 질문 카드: 번호 · 유형 / 예시 질문 / 따라가는 길 / 지금 검색으로 안 되는 이유
function questionCard(s, { x, y, w, h, n, kind, ask, route, why }) {
  L.rr(s, { x, y, w, h, fill: C.white, line: C.border, r: 0.08 });
  L.numBadge(s, n, { x: x + 0.15, y: y + 0.15, size: 0.42 });
  L.text(s, kind, { x: x + 0.65, y: y + 0.12, w: w - 0.75, h: 0.48, size: 16, bold: true, color: C.navy });
  L.card(s, ask, { x: x + 0.15, y: y + 0.7, w: w - 0.3, h: 0.84, fill: C.tint, line: null, color: C.ink, size: 15,
    bold: true, align: "left", r: 0.06 });
  L.pill(s, "경로", { x: x + 0.15, y: y + 1.66, w: 0.62, h: 0.34 });
  L.text(s, route, { x: x + 0.85, y: y + 1.64, w: w - 0.95, h: 0.38, size: 14, bold: true, color: C.blue });
  L.text(s, why, { x: x + 0.15, y: y + 2.06, w: w - 0.3, h: 0.5, size: 14, color: C.slate, valign: "top" });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "우리 시스템에 그래프 검색이 필요한 이유",
    lead: "회원·카드·거래·혜택·상담이 얽힌 우리 데이터는 '이어서 답할 질문'에 그래프 검색이 필요함",
    notes: "일반론의 비유(소크라테스 → 플라톤 → 아리스토텔레스 사제 관계를 따라 '할아버지 스승'을 찾음)가 "
      + "우리 시스템에서는 '회원 → 가진 카드 → 그 카드의 혜택'을 따라가는 질문임. "
      + "문서 검색은 질문과 비슷한 문단을 찾을 뿐, 그 문단이 '이 회원'과 어떻게 연결되는지는 모름. "
      + "한 조항(약관·혜택 1건)이나 한 숫자(승인액)로 끝나는 질문은 지금의 문서·SQL 검색이 더 빠르고 싸므로 "
      + "그래프 검색은 아래 3가지 질문 유형에만 붙임.",
  });

  // ① 위쪽 왼편 — 지금 검색으로 되는 질문
  const top = 1.9;
  L.headerBar(s, "지금 검색으로 되는 질문", { x: X0, y: top, w: LEFT_W, h: 0.42, size: 17 });
  searchCard(s, { y: 2.45, h: 0.76, name: "문서 검색", how: "비슷한 문단 5개 찾기",
    ask: "\"한빛 모아생활 카드 적립률은?\"", verdict: "됨" });
  searchCard(s, { y: 3.31, h: 0.76, name: "SQL 검색", how: "표에서 숫자 세기",
    ask: "\"M-1042 회원의 8월 승인액은?\"", verdict: "됨" });
  searchCard(s, { y: 4.17, h: 0.58, name: "빈틈", how: "DB 사실과 문서를 잇는 질문", verdict: "안 됨", dark: true });

  // ② 위쪽 오른편 — 우리 데이터를 이으면 하나의 관계망이 됨
  L.headerBar(s, "우리 데이터를 이으면 하나의 관계망(지식 그래프)이 됨", { x: RX, y: top, w: RW, h: 0.42, size: 17,
    accent: true });
  L.rr(s, { x: RX, y: 2.45, w: RW, h: 2.3, fill: C.altRow, line: C.border, r: 0.08 });

  const c0 = RX + 0.3, gap = 2.55, r1 = 2.62, r2 = 3.8;
  const 회원 = node(s, "회원", { x: c0, y: r1, src: "db" });
  const 카드 = node(s, "카드", { x: c0 + gap, y: r1, src: "db" });
  const 거래 = node(s, "거래", { x: c0 + gap * 2, y: r1, src: "db" });
  const 업종 = node(s, "업종", { x: c0 + gap * 3, y: r1, src: "db" });
  const 상담 = node(s, "상담", { x: c0, y: r2, src: "talk" });
  const 불만 = node(s, "불만 주제", { x: c0 + gap, y: r2, src: "talk" });
  const 혜택 = node(s, "상품·혜택", { x: c0 + gap * 2 + 1.25, y: r2, src: "doc" });

  const A = { color: C.slate, width: 1.75 };
  // 화살표를 먼저 그리고 이름표를 위에 얹음
  L.arrow(s, { x1: 회원.r, y1: 회원.cy, x2: 카드.x, y2: 카드.cy, ...A });
  L.arrow(s, { x1: 카드.r, y1: 카드.cy, x2: 거래.x, y2: 거래.cy, ...A });
  L.arrow(s, { x1: 거래.r, y1: 거래.cy, x2: 업종.x, y2: 업종.cy, ...A });
  L.arrow(s, { x1: 회원.cx, y1: 회원.b, x2: 상담.cx, y2: 상담.y, ...A });
  L.arrow(s, { x1: 상담.r, y1: 상담.cy, x2: 불만.x, y2: 불만.cy, ...A });
  L.arrow(s, { x1: 불만.r, y1: 불만.cy, x2: 혜택.x, y2: 혜택.cy, ...A });
  L.arrow(s, { x1: 카드.r - 0.2, y1: 카드.b, x2: 혜택.x + 0.35, y2: 혜택.y, ...A });
  L.arrow(s, { x1: 혜택.r - 0.35, y1: 혜택.y, x2: 업종.cx, y2: 업종.b, ...A });

  edgeLabel(s, "보유", { cx: (회원.r + 카드.x) / 2, cy: 회원.cy });
  edgeLabel(s, "이용", { cx: (카드.r + 거래.x) / 2, cy: 카드.cy });
  edgeLabel(s, "분류", { cx: (거래.r + 업종.x) / 2, cy: 거래.cy });
  edgeLabel(s, "상담 기록", { cx: 회원.cx, cy: (회원.b + 상담.y) / 2, w: 1.0 });
  edgeLabel(s, "언급", { cx: (상담.r + 불만.x) / 2, cy: 상담.cy });
  edgeLabel(s, "관련 혜택", { cx: (불만.r + 혜택.x) / 2, cy: 불만.cy, w: 1.0 });
  edgeLabel(s, "상품", { cx: (카드.r - 0.2 + 혜택.x + 0.35) / 2, cy: (카드.b + 혜택.y) / 2 });
  edgeLabel(s, "혜택 대상", { cx: (혜택.r - 0.35 + 업종.cx) / 2, cy: (혜택.y + 업종.b) / 2, w: 1.0 });

  // 범례: 색 = 데이터 원천
  [["정형 DB", SRC.db], ["카드 혜택 문서", SRC.doc], ["상담 이력", SRC.talk]].forEach(([t, col], i) => {
    const lx = RX + RW - 5.9 + i * 1.95;
    L.rr(s, { x: lx, y: 4.42, w: 0.24, h: 0.24, fill: col, line: null, r: 0.04 });
    L.text(s, t, { x: lx + 0.3, y: 4.38, w: 1.6, h: 0.32, size: 14, color: C.slate });
  });

  // ③ 아래 — 그래프 검색이 필요한 질문 3가지
  const qy = 4.88, qh = 2.6, qg = 0.2, qw = (CW - qg * 2) / 3;
  const qs = [
    { kind: "여러 단계 건너 찾기 (멀티홉)",
      ask: "\"M-5001 회원이 가진 카드 4장 중 혜택이 겹치는 카드는?\"",
      route: "회원 → 카드 → 상품·혜택",
      why: "가진 카드는 DB에, 혜택은 문서에 따로 있음\n→ 문서 검색은 이 회원의 카드를 모름" },
    { kind: "불만과 이용 습관을 이어 대안 찾기",
      ask: "\"혜택 불일치를 말한 M-6001 회원이 많이 쓰는 업종에 혜택을 주는 카드는?\"",
      route: "상담→회원→카드→거래→업종←혜택",
      why: "상담·거래·혜택 세 원천을 5단계로 이어야 함\n→ 한 번의 검색으로 못 찾음" },
    { kind: "전체 경향 보기 (거시적 통찰)",
      ask: "\"연회비·혜택 불만으로 해지를 문의한 회원들의 공통 원인과 거절한 제안은?\"",
      route: "여러 회원 → 상담 → 불만 주제별 요약",
      why: "문서 검색은 비슷한 문단 5개만 봄\n→ 회원 전체의 경향은 못 봄" },
  ];
  qs.forEach((q, i) => questionCard(s, { x: X0 + i * (qw + qg), y: qy, w: qw, h: qh, n: i + 1, ...q }));

  // ④ 맨 아래 — 선택 기준
  const by = 7.58, bh = 0.37;
  L.darkBadge(s, "선택 기준", { x: X0, y: by, w: 1.4, h: bh, size: 15 });
  s.addText([
    { text: "2단계 이상 연결 · 표와 문서 결합 · 회원 전체 경향이면 ", options: { color: C.ink } },
    { text: "그래프 검색", options: { color: C.blue, bold: true } },
    { text: "   /   한 조항·한 숫자면 ", options: { color: C.ink } },
    { text: "지금 검색으로 충분", options: { color: C.navy, bold: true } },
  ], { x: X0 + 1.55, y: by, w: CW - 1.55, h: bh, fontFace: FONT, fontSize: fs(15), valign: "middle", margin: 0,
    isTextBox: true });
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  const out = process.argv[2] || path.join(__dirname, "그래프검색필요성.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
