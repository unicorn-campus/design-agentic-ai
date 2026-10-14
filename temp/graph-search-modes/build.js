// node build.js — 그래프 검색 3가지 방식 한 장 빌드 (script.md 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const GAP = 0.25;
const COL_W = (CW - GAP * 2) / 3;
const TOP = 1.9;

const GH = 1.1;                      // 미니 그래프 높이
const H = 4.7;                       // 방식 카드 높이

// 미니 그래프용 원 — rectRadius를 넘기지 않아 adj가 붙지 않게 함(pptxgenjs 4 손상 방지)
function dot(s, { cx, cy, d, fill, line }) {
  s.addShape(L.getPptx().shapes.OVAL, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: fill },
    line: { color: line || fill, width: 1.25 } });
}

const edge = (s, x1, y1, x2, y2, color, dash) =>
  L.arrow(s, { x1, y1, x2, y2, color, width: dash ? 1 : 1.5, head: "none", dash });

// 원문 조각 아이콘 — 사각형 + 글줄 3개. FOLDED_CORNER는 pptxgenjs가 잘못된 이름(folderCorner)으로 써서 쓰지 않음
function doc(s, { x, y, w = 0.2, h = 0.24 }) {
  L.box(s, { x, y, w, h, fill: C.white, line: C.slate, lw: 1 });
  [0.3, 0.5, 0.7].forEach((t) => L.hline(s, { x: x + w * 0.2, y: y + h * t, w: w * 0.6, color: C.slate, width: 0.75 }));
}

// Local: Q와 뜻이 가까운 엔티티 몇 개가 진입점(점선 = 뜻 거리), 진입점에서 1홉 관계만 모으고(실선),
// 원문 조각은 진입점이 나온 조각만 붙임 — MS GraphRAG mixed_context · LightRAG operate 기준
function drawLocal(s, x, y, color) {
  const cy = y + GH / 2;
  const q = { cx: x + 1.0, cy };
  const entries = [[x + 1.55, cy - 0.18], [x + 1.6, cy + 0.3]];   // 거리 0.58 · 0.67 — 가까운 2개
  const far = [[x + 0.3, cy - 0.35], [x + 0.2, cy + 0.32]];       // 거리 0.78 · 0.86 — 진입점에서 탈락
  const hop1 = [[x + 2.15, cy - 0.45, 0], [x + 2.35, cy - 0.12, 0], [x + 2.3, cy + 0.22, 1], [x + 2.1, cy + 0.5, 1]];
  // 선을 먼저 그려 노드 아래로 깔림
  [...far, ...entries].forEach(([fx, fy]) => edge(s, q.cx, q.cy, fx, fy, C.sub, "dash"));
  edge(s, entries[0][0], entries[0][1], entries[1][0], entries[1][1], color);
  hop1.forEach(([hx, hy, p]) => edge(s, entries[p][0], entries[p][1], hx, hy, color));
  far.forEach(([fx, fy]) => dot(s, { cx: fx, cy: fy, d: 0.2, fill: C.white, line: C.sub }));
  hop1.forEach(([hx, hy]) => dot(s, { cx: hx, cy: hy, d: 0.22, fill: C.white, line: color }));
  // 진입점마다 그 엔티티가 나온 원문 조각을 짧은 회색 선으로 붙임
  [[entries[0], -0.36, -0.4], [entries[1], -0.38, 0.02]].forEach(([[ex, ey], dx, dy]) => {
    edge(s, ex + dx + 0.2, ey + dy + 0.12, ex, ey, C.sub);
    doc(s, { x: ex + dx, y: ey + dy });
  });
  entries.forEach(([ex, ey]) => dot(s, { cx: ex, cy: ey, d: 0.28, fill: color }));
  s.addText("Q", { shape: L.getPptx().shapes.OVAL, x: q.cx - 0.21, y: q.cy - 0.21, w: 0.42, h: 0.42,
    fill: { color: C.blue }, line: { color: C.blue, width: 1 }, fontFace: FONT, fontSize: fs(16), bold: true,
    color: C.white, align: "center", valign: "middle", margin: 0 });
  // 범례: 진입점 · 뜻 거리(점선) · 관계 1홉(실선) · 원문 조각
  const lx = x + 3.0, rows = [cy - 0.42, cy - 0.14, cy + 0.14, cy + 0.42];
  dot(s, { cx: lx + 0.12, cy: rows[0], d: 0.2, fill: color });
  edge(s, lx, rows[1], lx + 0.25, rows[1], C.sub, "dash");
  edge(s, lx, rows[2], lx + 0.25, rows[2], color);
  doc(s, { x: lx + 0.03, y: rows[3] - 0.12, w: 0.18, h: 0.22 });
  ["진입점", "뜻 거리", "관계 (1홉)", "원문 조각"].forEach((t, i) =>
    L.text(s, t, { x: lx + 0.3, y: rows[i] - 0.14, w: COL_W - 3.35, h: 0.28, size: 14, color: C.slate, bold: true }));
}

// Global: 리포트 묶음마다 따로 답하고(map), 요점 점수로 골라 한 답으로 합침(reduce)
function drawGlobal(s, x, y, color) {
  const bw = 1.0, bh = 0.26, x1 = x + 0.2, x2 = x + 1.75, x3 = x + 3.3, ry = y + 0.3;
  L.text(s, "리포트 묶음", { x: x1 - 0.1, y, w: bw + 0.2, h: 0.28, size: 14, color: C.sub, bold: true, align: "center" });
  L.text(s, "map", { x: x2, y, w: bw, h: 0.28, size: 14, color, bold: true, align: "center" });
  L.text(s, "reduce", { x: x3, y, w: COL_W - 3.45, h: 0.28, size: 14, color, bold: true,
    align: "center" });
  const midY = ry + 1.5 * (bh + 0.02) - 0.01;
  [0, 1, 2].forEach((i) => {
    const by = ry + i * (bh + 0.02);
    L.card(s, "리포트", { x: x1, y: by, w: bw, h: bh, fill: C.tint, line: C.pill, color: C.navy, size: 14, r: 0.04 });
    L.card(s, "중간 답", { x: x2, y: by, w: bw, h: bh, fill: C.white, line: color, color, size: 14, r: 0.04 });
    L.arrow(s, { x1: x1 + bw + 0.04, y1: by + bh / 2, x2: x2 - 0.04, y2: by + bh / 2, color: C.sub, width: 1.25 });
    L.arrow(s, { x1: x2 + bw + 0.04, y1: by + bh / 2, x2: x3 - 0.04, y2: midY, color: C.sub, width: 1.25 });
  });
  L.card(s, "최종 답", { x: x3, y: midY - 0.2, w: COL_W - 3.45, h: 0.4, fill: color, line: null, color: C.white,
    size: 15, bold: true, r: 0.06 });
}

// Hybrid: 세부 근거(Local)와 전체 맥락(Global)을 한 답에 묶음 — 묶는 방법은 프레임워크마다 다름
function drawHybrid(s, x, y, color) {
  const bw = 1.45, bh = 0.72, cy = y + GH / 2;
  L.card(s, "Local\n세부 근거", { x: x + 0.15, y: cy - bh / 2, w: bw, h: bh, fill: C.tint, line: C.pill, color: C.navy,
    size: 14, bold: true, r: 0.06 });
  L.card(s, "Global\n전체 맥락", { x: x + COL_W - 0.15 - bw, y: cy - bh / 2, w: bw, h: bh, fill: C.tint, line: C.pill,
    color: C.navy, size: 14, bold: true, r: 0.06 });
  const mx = x + 0.15 + bw + 0.32, mw = COL_W - 2 * (0.15 + bw + 0.32);
  L.card(s, "결합", { x: mx, y: cy - 0.2, w: mw, h: 0.4, fill: color, line: null, color: C.white, size: 15, bold: true,
    r: 0.06 });
  L.arrow(s, { x1: x + 0.15 + bw + 0.03, y1: cy, x2: mx - 0.03, y2: cy, color: C.sub, width: 1.25 });
  L.arrow(s, { x1: x + COL_W - 0.15 - bw - 0.03, y1: cy, x2: mx + mw + 0.03, y2: cy, color: C.sub, width: 1.25 });
}

const MODES = [
  {
    name: "Local Search", color: C.navy, draw: drawLocal,
    kind: "한 대상을 깊게 묻는 질문", ask: "예) A카드의 해외 결제 혜택은?",
    steps: ["Q와 뜻이 가까운 엔티티 몇 개를 진입점으로 찾기", "진입점에서 뻗은 관계(1홉)와 관계 설명을\n근거 후보에 넣기",
      "진입점의 원문 조각 · 리포트도 근거 후보에 넣기", "토큰 한도에 맞게 추려 LLM이 답변"],
    note: "LightRAG는 1단계를 세부(Low-level) 키워드로 수행",
  },
  {
    name: "Global Search", color: C.blue, draw: drawGlobal,
    kind: "문서 전체를 조망하는 질문", ask: "예) 고객 불만의 주요 주제는?",
    steps: ["한 계층의 커뮤니티 리포트를 묶음으로 나누기", "map: 묶음마다 따로 중간 답 쓰기",
      "reduce: 중간 답 안의 요점별 중요도 점수로 골라 합치기", "전체 조망 답변 생성"],
    note: "관련 리포트만 골라 사용하는 동적 선택은 옵션",
  },
  {
    name: "Hybrid Search", color: C.dark, draw: drawHybrid,
    kind: "한 대상 + 전체 흐름을 함께 묻는 질문", ask: "예) A카드 혜택은 업계 흐름과 어떻게 다른가?",
    rowsTitle: "결합 방법은 프레임워크마다 다름",
    rows: [
      ["Neo4j", "'Hybrid' = 벡터 + 키워드 검색\nLocal + Global 결합은 직접 설계"],
      ["MS GraphRAG", "DRIFT: 요약으로 큰 답 →\n후속 질문마다 Local 검색 (순서대로)"],
      ["LightRAG", "듀얼 레벨: 세부 키워드 → 엔티티\n+ 상위 키워드 → 관계, 둘 다 사용"],
    ],
  },
];

function modeCard(s, m, x) {
  L.rr(s, { x, y: TOP, w: COL_W, h: H, fill: C.white, line: C.border, r: 0.08 });
  L.card(s, m.name, { x, y: TOP, w: COL_W, h: 0.5, fill: m.color, line: null, color: C.white, size: 20, bold: true,
    r: 0.06 });
  // 질문 유형 + 예시
  L.rr(s, { x: x + 0.15, y: TOP + 0.6, w: COL_W - 0.3, h: 0.7, fill: C.tint, line: null, r: 0.06 });
  s.addText([
    { text: m.kind, options: { fontSize: fs(15), bold: true, color: m.color === C.blue ? C.blue : C.navy, breakLine: true } },
    { text: m.ask, options: { fontSize: fs(14), color: C.ink } },
  ], { x: x + 0.22, y: TOP + 0.6, w: COL_W - 0.44, h: 0.7, fontFace: FONT, valign: "middle", margin: 0.04,
    isTextBox: true, paraSpaceAfter: 0 });
  m.draw(s, x + 0.05, TOP + 1.36, m.color);
  const sy = TOP + 1.36 + GH + 0.08;
  if (m.rows) {
    // Hybrid는 단계 대신 프레임워크별 결합 방법을 나란히 보여 줌
    L.text(s, m.rowsTitle, { x: x + 0.15, y: sy, w: COL_W - 0.3, h: 0.32, size: 15, color: m.color, bold: true });
    const rh = (TOP + H - 0.06 - sy - 0.34) / m.rows.length;
    m.rows.forEach(([who, how], i) => {
      const y = sy + 0.34 + i * rh;
      if (i) L.hline(s, { x: x + 0.15, y, w: COL_W - 0.3, color: C.line });
      L.card(s, who, { x: x + 0.15, y: y + rh / 2 - 0.18, w: 1.4, h: 0.36, fill: C.tint, line: C.pill, color: C.navy,
        size: 14, bold: true, r: 0.18 });
      L.text(s, how, { x: x + 1.62, y, w: COL_W - 1.7, h: rh, size: 14, color: C.ink });
    });
    return;
  }
  const rh = 0.43;
  m.steps.forEach((t, i) => {
    const y = sy + i * rh;
    L.numBadge(s, i + 1, { x: x + 0.15, y: y + 0.045, size: 0.34, fill: m.color, fsz: 14 });
    L.text(s, t, { x: x + 0.58, y, w: COL_W - 0.68, h: rh, size: 15, color: C.ink });
  });
  // 구현 차이 각주
  const ny = sy + 4 * rh + 0.05;
  L.hline(s, { x: x + 0.15, y: ny, w: COL_W - 0.3, color: C.line });
  L.text(s, m.note, { x: x + 0.15, y: ny + 0.02, w: COL_W - 0.3, h: TOP + H - ny - 0.04, size: 14, color: C.sub });
}

// 순서는 사용자 지정(Neo4j → MS GraphRAG → LightRAG). 대표 선정 근거는 script.md 참조
const IMPLS = [
  { name: "① Neo4j GraphRAG", way: "Text2Cypher", how: "질문을 Cypher로 바꿔 그래프 전체를 집계",
    fit: "조건으로 대상을 좁혀 정확히 집계 · 요약은 LLM" },
  { name: "② MS GraphRAG※", way: "커뮤니티 요약", how: "미리 만든 커뮤니티 요약을 나눠 답하고 합침",
    fit: "전체 리포트를 다 훑음 · 빠짐없지만 비용 큼" },
  { name: "③ LightRAG", way: "High-level 키워드", how: "질문의 상위(High-level) 키워드로 관계 벡터 검색",
    fit: "맞는 관계만 골라 봄 · 가볍지만 놓칠 수 있음" },
];

function implStrip(s) {
  const y = TOP + 4.7 + 0.12, h = 7.88 - y, LW = 2.25, gap = 0.15;
  L.card(s, "대표 프레임워크의\nGlobal 질문 처리", { x: X0, y, w: LW, h, fill: C.dark, line: null, color: C.white,
    size: 16, bold: true, r: 0.06 });
  const bw = (CW - LW - gap * 3) / 3;
  IMPLS.forEach((m, i) => {
    const x = X0 + LW + gap + i * (bw + gap);
    L.rr(s, { x, y, w: bw, h, fill: C.altRow, line: C.border, r: 0.06 });
    s.addText([
      { text: m.name, options: { fontSize: fs(16), bold: true, color: C.navy } },
      { text: `  ${m.way}`, options: { fontSize: fs(14), bold: true, color: C.slate, breakLine: true } },
      { text: m.how, options: { fontSize: fs(14), color: C.ink, breakLine: true } },
      { text: m.fit, options: { fontSize: fs(14), bold: true, color: C.blue } },
    ], { x: x + 0.12, y, w: bw - 0.24, h, fontFace: FONT, valign: "middle", margin: 0.04, isTextBox: true,
      paraSpaceAfter: 0 });
  });
  // 유지보수 모드 각주 — README 공지(2026-08-14 추가) 기준
  L.text(s, "※ MS GraphRAG는 현재 유지보수 모드: 새 기능 추가 없이 버그 · 보안 수정만 이어 가는 상태 (2026-08 공지). "
    + "Local · Global · DRIFT 개념의 원형으로 참고", { x: X0, y: y + h + 0.04, w: CW, h: 0.34, size: 14, color: C.sub });
}

async function main() {
  L.createDeck();
  const s = L.newSlide({
    title: "그래프 검색 3가지 방식: Local · Global · Hybrid",
    lead: "질문이 묻는 범위(한 대상 / 전체 / 둘 다)에 따라 그래프에서 꺼내는 재료와 순서가 달라짐",
    notes: "Local은 '한 점에서 출발해 이웃으로 넓히기', Global은 '미리 만든 요약들을 나눠 읽고 합치기'임. "
      + "Hybrid라는 이름은 LightRAG의 모드 이름이고, MS GraphRAG에서 같은 역할은 DRIFT가 맡음. "
      + "DRIFT는 동시에 돌리지 않고 '요약으로 큰 답 → 후속 질문 → Local 반복' 순서로 진행함. "
      + "Global의 기본 동작은 한 계층의 리포트를 전부 나눠 읽는 것이라 비용이 큼. 관련 리포트만 고르는 동적 선택은 "
      + "비용을 줄이는 옵션임. Cypher 집계는 '몇 개' · '가장 많은' 같은 숫자형 거시 질문에 강함. "
      + "MS GraphRAG는 2026-08부터 유지보수 모드(새 기능 없음, 버그 · 보안 수정만)이지만 검색 방식 개념의 원형이라 소개함.",
  });
  MODES.forEach((m, i) => modeCard(s, m, X0 + i * (COL_W + GAP)));
  implStrip(s);
  const out = process.argv[2] || path.join(__dirname, "그래프검색방식.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
