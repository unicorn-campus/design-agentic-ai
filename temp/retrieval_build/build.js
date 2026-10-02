// 검색 테크닉 4장 덱 빌드 — 모든 도식은 편집 가능한 기본 도형으로 그림
const pptxgen = require("pptxgenjs");
const path = require("path");

const FONT = "Pretendard";
const C = {
  navy: "1E2A5C", blue: "2E74C6", ink: "2B3242", slate: "4A5364", sub: "7C8598",
  tint: "EEF3FA", altRow: "F5F8FC", tableHead: "E2EEF9", dark: "404155",
  border: "D9E0EC", line: "EDF0F6", footer: "E9ECF3", pill: "C3CEE0", body: "3B4557", white: "FFFFFF",
};
const MIN_FONT = 14;
const fsMin = (size) => {
  if (size < MIN_FONT) throw new Error(`fontSize ${size} < ${MIN_FONT}pt 금지! 슬라이드를 분리할 것`);
  return size;
};
const TOTAL = 4;
let pptx;

// ---------- 공통 헬퍼 ----------
function text(slide, t, o) {
  slide.addText(t, {
    fontFace: FONT, color: C.ink, margin: 0, valign: "middle", ...o, fontSize: fsMin(o.fontSize || 18),
  });
}

// 글자가 들어간 도형 — 도형과 글이 한 개체라 PowerPoint에서 그대로 편집 가능
function box(slide, t, o) {
  const fill = o.fill || C.tint;
  const align = o.align || "center";
  // run 끝의 줄바꿈을 breakLine 문단으로 바꿔야 줄마다 정렬이 유지됨
  if (Array.isArray(t)) {
    t = t.map((r) => r.text.endsWith("\n")
      ? { text: r.text.slice(0, -1), options: { align, ...r.options, breakLine: true } }
      : { text: r.text, options: { align, ...r.options } });
  }
  const shape = o.shape || pptx.shapes.ROUNDED_RECTANGLE;
  slide.addText(t, {
    shape, ...roundOpt(shape, o.r ?? 0.15, o.w, o.h),
    x: o.x, y: o.y, w: o.w, h: o.h,
    fill: { color: fill }, line: { color: o.line || fill, width: o.lw || 1 },
    fontFace: FONT, fontSize: fsMin(o.fontSize || 16), color: o.color || C.navy, bold: o.bold ?? true,
    align: o.align || "center", valign: o.valign || "middle", margin: o.margin ?? 3, strike: o.strike,
  });
}

// 둥글기는 둥근 사각형에만 붙임. pptxgenjs는 adj = rectRadius ÷ 짧은 변 × 100000으로 쓰고
// PowerPoint 허용 범위는 0 ~ 50000이므로, r을 "짧은 변 대비 비율(0 ~ 0.5)"로 받아 인치로 환산함
function roundOpt(shape, r, w, h) {
  if (shape !== pptx.shapes.ROUNDED_RECTANGLE) return {};
  return { rectRadius: Math.min(Math.max(r, 0), 0.5) * Math.min(w, h) };
}

function rect(slide, o) {
  const shape = o.round ? pptx.shapes.ROUNDED_RECTANGLE : pptx.shapes.RECTANGLE;
  slide.addShape(shape, {
    x: o.x, y: o.y, w: o.w, h: o.h, ...roundOpt(shape, o.r ?? 0.08, o.w, o.h),
    fill: { color: o.fill || C.white }, line: { color: o.line || o.fill || C.white, width: o.lw || 1 },
  });
}

function oval(slide, o) {
  slide.addShape(pptx.shapes.OVAL, {
    x: o.x, y: o.y, w: o.d, h: o.d, fill: { color: o.fill }, line: { color: o.line || o.fill, width: o.lw || 1.5 },
  });
}

// 시작점→끝점 직선 화살표. 방향은 flipH/flipV로 표현
function arrow(slide, x1, y1, x2, y2, { color = C.blue, width = 2, head = true, dash } = {}) {
  slide.addShape(pptx.shapes.LINE, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width, ...(dash ? { dashType: dash } : {}), ...(head ? { endArrowType: "triangle" } : {}) },
  });
}

function stepArrow(slide, x, yMid) {
  slide.addShape(pptx.shapes.RIGHT_ARROW, {
    x, y: yMid - 0.17, w: 0.32, h: 0.34, fill: { color: C.blue }, line: { color: C.blue },
  });
}

function numBadge(slide, { x, y, n, color = C.blue, size = 0.45 }) {
  box(slide, String(n), { x, y, w: size, h: size, r: 0.15, fill: color, color: C.white, fontSize: 18 });
}

function headerBar(slide, { x, y, w, t, accent = false, fontSize = 22, h = 0.55, fill }) {
  box(slide, t, { x, y, w, h, r: 0.12, fill: fill || (accent ? C.blue : C.navy), color: C.white, fontSize });
}

function pageHeader(slide, { crumb, title, lead }) {
  text(slide, crumb, { x: 0.55, y: 0.38, w: 12, h: 0.3, color: C.sub, fontSize: 15, bold: true });
  text(slide, title, { x: 0.55, y: 0.7, w: 14.9, h: 0.75, color: C.navy, bold: true, fontSize: 40 });
  rect(slide, { x: 0.55, y: 1.52, w: 14.9, h: 0.04, fill: C.border });
  rect(slide, { x: 0.55, y: 1.52, w: 2.1, h: 0.04, fill: C.blue });
  if (lead) text(slide, lead, { x: 0.55, y: 1.66, w: 14.9, h: 0.45, color: C.slate, fontSize: 18 });
}

function footer(slide, src, n) {
  rect(slide, { x: 0.55, y: 8.33, w: 14.9, h: 0.02, fill: C.footer });
  text(slide, src, { x: 0.55, y: 8.4, w: 13.7, h: 0.5, color: C.sub, fontSize: 14, valign: "top" });
  text(slide, `${n} / ${TOTAL}`, { x: 14.35, y: 8.4, w: 1.1, h: 0.3, color: C.sub, fontSize: 14, align: "right", valign: "top" });
}

function callout(slide, t, { x, y, w, h = 0.45, fontSize = 16 }) {
  rect(slide, { x, y, w: 0.07, h, fill: C.blue });
  text(slide, t, { x: x + 0.2, y, w: w - 0.2, h, color: C.navy, bold: true, italic: true, fontSize });
}

function chip(slide, t, { x, y, w, h = 0.42, on = true, strike = false, fontSize = 15 }) {
  box(slide, t, {
    x, y, w, h, r: 0.5, fontSize, strike: strike ? "sngStrike" : undefined,
    fill: on ? C.blue : C.white, line: on ? C.blue : C.pill, color: on ? C.white : C.sub,
  });
}

function card(slide, { x, y, w, h }) {
  rect(slide, { x, y, w, h, round: true, r: 0.05, fill: C.white, line: C.border, lw: 1.25 });
}

// ---------- 슬라이드 1: 검색 방식 4종 ----------
async function createSlide01() {
  const s = pptx.addSlide({ masterName: "MASTER" });
  pageHeader(s, {
    crumb: "RAG › 4. Techniques › 4.2 Retrieval",
    title: "검색 방식 4종 한눈에",
    lead: "같은 질문도 \"낱말로 찾기\"와 \"뜻으로 찾기\"는 서로 다른 문서를 데려옴",
  });

  const cards = [
    { name: "Sparse (BM25)", how: "낱말이 문서에 있는지", color: C.navy,
      good: "조항 번호·상품 코드 등 정확한 용어", bad: "다른 말로 물으면 못 찾음" },
    { name: "Dense (임베딩)", how: "문장 뜻이 얼마나 가까운지", color: C.navy,
      good: "구어체·돌려 말한 질문", bad: "드문 고유명사·숫자 코드" },
    { name: "Hybrid", how: "두 점수를 합쳐서", color: C.blue,
      good: "용어와 자연어가 섞인 질문", bad: "검색기 2개 관리·비중 조정" },
    { name: "GraphRAG", how: "뜻 + 개체 사이의 관계", color: C.dark,
      good: "\"A와 이어진 B\" 관계 추적", bad: "그래프 구축 비용이 큼" },
  ];
  const cw = (14.9 - 3 * 0.25) / 4;
  const cy = 2.3;
  cards.forEach((c, i) => {
    const x = 0.55 + i * (cw + 0.25);
    card(s, { x, y: cy, w: cw, h: 4.55 });
    headerBar(s, { x, y: cy, w: cw, t: c.name, fontSize: 22, h: 0.6, fill: c.color });
    text(s, c.how, { x: x + 0.15, y: cy + 0.68, w: cw - 0.3, h: 0.42, color: C.slate, fontSize: 16, align: "center", bold: true });

    // 미니 도식 영역
    const dx = x + 0.18, dy = cy + 1.2, dw = cw - 0.36, dh = 1.95;
    rect(s, { x: dx, y: dy, w: dw, h: dh, round: true, r: 0.06, fill: C.altRow, line: C.border });
    if (i === 0) drawSparseMini(s, dx, dy, dw);
    if (i === 1) drawDenseMini(s, dx, dy);
    if (i === 2) drawHybridMini(s, dx, dy);
    if (i === 3) drawGraphMini(s, dx, dy);

    // 강점 / 약점
    [["강점", c.good, C.blue], ["약점", c.bad, C.sub]].forEach(([label, t, col], k) => {
      const ry = cy + 3.3 + k * 0.6;
      box(s, label, { x: x + 0.18, y: ry + 0.05, w: 0.72, h: 0.4, r: 0.5, fill: col, color: C.white, fontSize: 14 });
      text(s, t, { x: x + 1.0, y: ry, w: cw - 1.12, h: 0.5, color: C.ink, fontSize: 15 });
    });
  });

  // 하단: 이 프로젝트의 선택
  rect(s, { x: 0.55, y: 7.05, w: 14.9, h: 1.0, round: true, r: 0.12, fill: C.tint, line: C.border });
  box(s, "이 프로젝트의 선택", { x: 0.75, y: 7.3, w: 2.3, h: 0.5, r: 0.15, fill: C.dark, color: C.white, fontSize: 16 });
  const pills = ["Sparse · BM25S + Kiwi", "Dense · KURE-v2 + Chroma", "Hybrid · 벡터 6 : BM25 4", "GraphRAG · 미적용"];
  const px0 = 3.25, pw = (15.25 - px0 - 3 * 0.15) / 4;
  pills.forEach((p, k) => box(s, p, {
    x: px0 + k * (pw + 0.15), y: 7.3, w: pw, h: 0.5, r: 0.5, fill: k === 2 ? C.blue : C.white,
    line: k === 2 ? C.blue : C.pill, color: k === 2 ? C.white : C.navy, fontSize: 14,
  }));

  footer(s, "출처: cna-bootcamp/aistudy 교재 10.RAG.md §4.2 Retrieval · hybrid-ai-lab retriever/vector-retriever/README.md", 1);
  s.addNotes(
    "Sparse는 벡터 대부분이 0이라 '드문(sparse)', Dense는 모든 칸에 숫자가 차 있어 '빽빽한(dense)'이라는 이름이 붙음.\n" +
    "네 방식은 경쟁 관계가 아니라 들어오는 질문에 따라 고르는 선택지임.\n" +
    "우리 프로젝트는 약관 조항 번호(Sparse 유리)와 상담 대화체 질문(Dense 유리)이 함께 들어오므로 Hybrid를 기본으로 둠. GraphRAG는 별도 교재 주제임."
  );
}

function drawSparseMini(s, dx, dy) {
  const xs = [dx + 0.1, dx + 1.12, dx + 2.14];
  chip(s, "연회비", { x: xs[0], y: dy + 0.15, w: 0.92 });
  chip(s, "면제", { x: xs[1], y: dy + 0.15, w: 0.92 });
  text(s, "← 질문", { x: xs[2], y: dy + 0.15, w: 0.92, h: 0.42, color: C.sub, fontSize: 14 });
  rect(s, { x: dx + 0.05, y: dy + 0.98, w: 3.08, h: 0.8, round: true, r: 0.1, fill: C.white, line: C.blue, lw: 1.5 });
  chip(s, "연회비", { x: xs[0], y: dy + 1.17, w: 0.92 });
  chip(s, "면제", { x: xs[1], y: dy + 1.17, w: 0.92 });
  chip(s, "조건", { x: xs[2], y: dy + 1.17, w: 0.92, on: false });
  arrow(s, xs[0] + 0.46, dy + 0.58, xs[0] + 0.46, dy + 1.15, { color: C.blue, width: 2 });
  arrow(s, xs[1] + 0.46, dy + 0.58, xs[1] + 0.46, dy + 1.15, { color: C.blue, width: 2 });
  text(s, "문서", { x: xs[2], y: dy + 0.62, w: 0.92, h: 0.32, color: C.sub, fontSize: 14 });
}

function drawDenseMini(s, dx, dy) {
  const ox = dx + 0.3, oy = dy + 1.75;
  arrow(s, ox, oy, ox + 2.4, oy - 0.3, { color: C.sub, width: 2 });
  arrow(s, ox, oy, ox + 1.4, oy - 1.55, { color: C.navy, width: 2.5 });
  arrow(s, ox, oy, ox + 2.0, oy - 1.1, { color: C.blue, width: 3.5 });
  oval(s, { x: ox - 0.07, y: oy - 0.07, d: 0.14, fill: C.ink });
  text(s, "질문", { x: ox + 2.05, y: oy - 1.32, w: 0.75, h: 0.32, color: C.blue, bold: true, fontSize: 14 });
  text(s, "가까운 문서", { x: ox + 1.45, y: dy + 0.03, w: 1.3, h: 0.32, color: C.navy, bold: true, fontSize: 14 });
  text(s, "먼 문서", { x: ox + 1.7, y: oy - 0.74, w: 0.9, h: 0.3, color: C.sub, fontSize: 14 });
}

function drawHybridMini(s, dx, dy) {
  box(s, "BM25 점수", { x: dx + 0.1, y: dy + 0.2, w: 1.4, h: 0.55, fill: C.white, line: C.navy, fontSize: 15 });
  box(s, "Vector 점수", { x: dx + 0.1, y: dy + 1.15, w: 1.4, h: 0.55, fill: C.white, line: C.navy, fontSize: 15 });
  box(s, "합친 점수", { x: dx + 1.95, y: dy + 0.67, w: 1.18, h: 0.6, fill: C.blue, color: C.white, fontSize: 15 });
  arrow(s, dx + 1.5, dy + 0.48, dx + 1.93, dy + 0.85, { color: C.blue, width: 2 });
  arrow(s, dx + 1.5, dy + 1.42, dx + 1.93, dy + 1.1, { color: C.blue, width: 2 });
}

function drawGraphMini(s, dx, dy) {
  const d = 0.78;
  const nodes = [
    { t: "회원", x: dx + 0.15, y: dy + 1.0 },
    { t: "카드", x: dx + 1.2, y: dy + 0.15 },
    { t: "혜택", x: dx + 2.25, y: dy + 1.0 },
  ];
  arrow(s, nodes[0].x + d / 2, nodes[0].y + d / 2, nodes[1].x + d / 2, nodes[1].y + d / 2, { color: C.dark, width: 2, head: false });
  arrow(s, nodes[1].x + d / 2, nodes[1].y + d / 2, nodes[2].x + d / 2, nodes[2].y + d / 2, { color: C.dark, width: 2, head: false });
  nodes.forEach((n, k) => box(s, n.t, {
    shape: pptx.shapes.OVAL, x: n.x, y: n.y, w: d, h: d, fill: k === 1 ? C.dark : C.white, line: C.dark,
    color: k === 1 ? C.white : C.dark, fontSize: 15, lw: 1.5,
  }));
  text(s, "보유", { x: dx + 0.2, y: dy + 0.42, w: 0.8, h: 0.3, color: C.sub, fontSize: 14, align: "center" });
  text(s, "제공", { x: dx + 2.2, y: dy + 0.42, w: 0.8, h: 0.3, color: C.sub, fontSize: 14, align: "center" });
}

// ---------- 슬라이드 2: Sparse BM25 ----------
async function createSlide02() {
  const s = pptx.addSlide({ masterName: "MASTER" });
  pageHeader(s, {
    crumb: "RAG › 4.2 Retrieval › 4.2.1 Sparse",
    title: "Sparse Retrieval — BM25",
    lead: "BM25는 \"질문 낱말이 이 문서에 얼마나 자주, 전체 문서에서 얼마나 드물게 나오나\"로 점수를 매김",
  });

  // ① 한국어 토큰화 흐름
  const fy = 2.3, fh = 1.15, gap = 0.42;
  const ws = [3.0, 2.7, 2.3, 3.1, 2.12];
  const xs = [];
  let cx = 0.55;
  ws.forEach((w) => { xs.push(cx); cx += w + gap; });
  box(s, [
    { text: "질문\n", options: { fontSize: fsMin(14), color: C.sub, bold: false } },
    { text: "“연회비 면제 조건은?”", options: { fontSize: fsMin(17) } },
  ], { x: xs[0], y: fy, w: ws[0], h: fh, fill: C.white, line: C.navy, lw: 1.5 });
  box(s, [
    { text: "① 정규화\n", options: { fontSize: fsMin(17) } },
    { text: "NFKC · 소문자 · 숫자 쉼표", options: { fontSize: fsMin(14), bold: false, color: C.slate } },
  ], { x: xs[1], y: fy, w: ws[1], h: fh, line: C.border });
  box(s, [
    { text: "② Kiwi\n", options: { fontSize: fsMin(17) } },
    { text: "형태소 분석", options: { fontSize: fsMin(14), bold: false, color: C.slate } },
  ], { x: xs[2], y: fy, w: ws[2], h: fh, line: C.border });
  rect(s, { x: xs[3], y: fy, w: ws[3], h: fh, round: true, r: 0.15, fill: C.tint, line: C.border });
  text(s, "③ 남은 낱말 (조사 탈락)", { x: xs[3], y: fy + 0.08, w: ws[3], h: 0.35, color: C.navy, bold: true, fontSize: 15, align: "center" });
  const tw = [0.82, 0.68, 0.68, 0.6];
  let tx = xs[3] + 0.1;
  ["연회비", "면제", "조건", "은?"].forEach((t, k) => {
    chip(s, t, { x: tx, y: fy + 0.55, w: tw[k], h: 0.42, on: k < 3, strike: k === 3, fontSize: 14 });
    tx += tw[k] + 0.06;
  });
  box(s, [
    { text: "④ BM25S\n", options: { fontSize: fsMin(17) } },
    { text: "점수 계산", options: { fontSize: fsMin(14), bold: false } },
  ], { x: xs[4], y: fy, w: ws[4], h: fh, fill: C.blue, color: C.white });
  for (let k = 0; k < 4; k++) stepArrow(s, xs[k] + ws[k] + 0.05, fy + fh / 2);
  callout(s, "색인할 때와 질문할 때 같은 토크나이저를 씀 — 서명이 다르면 검색 자체를 거부함", { x: 0.55, y: 3.6, w: 14.9 });

  // ② 점수를 만드는 세 요소
  const py = 4.3, ph = 3.25, pw = (14.9 - 2 * 0.25) / 3;
  const titles = ["TF — 많이 나올수록 ↑", "IDF — 드문 낱말일수록 ↑", "b — 긴 문서는 깎음"];
  const px = [0, 1, 2].map((k) => 0.55 + k * (pw + 0.25));
  px.forEach((x, k) => {
    card(s, { x, y: py, w: pw, h: ph });
    numBadge(s, { x: x + 0.2, y: py + 0.2, n: k + 1, color: C.navy });
    text(s, titles[k], { x: x + 0.78, y: py + 0.2, w: pw - 0.9, h: 0.45, color: C.navy, bold: true, fontSize: 20 });
  });

  // ①-TF 포화: BM25 TF 항 tf×(k1+1)/(tf+k1), k1=1.5, 문서 길이 = 평균
  {
    const x = px[0], base = py + 2.2, sc = 0.46;
    const tfs = [1, 2, 3, 5, 10];
    arrow(s, x + 0.45, base - 2.5 * sc, x + 4.55, base - 2.5 * sc, { color: C.sub, width: 1.5, head: false, dash: "dash" });
    text(s, "한계 2.5", { x: x + 0.45, y: base - 2.5 * sc - 0.3, w: 1.0, h: 0.27, color: C.sub, fontSize: 14 });
    rect(s, { x: x + 0.4, y: base, w: 4.2, h: 0.02, fill: C.sub });
    tfs.forEach((tf, k) => {
      const v = (tf * 2.5) / (tf + 1.5);
      const bx = x + 0.6 + k * 0.82, bh = v * sc;
      rect(s, { x: bx, y: base - bh, w: 0.5, h: bh, fill: k === 4 ? C.navy : C.blue });
      text(s, v.toFixed(2), { x: bx - 0.15, y: base - bh + 0.04, w: 0.8, h: 0.27, color: C.white, bold: true, fontSize: 14, align: "center" });
      text(s, `${tf}회`, { x: bx - 0.15, y: base + 0.03, w: 0.8, h: 0.27, color: C.slate, fontSize: 14, align: "center" });
    });
    text(s, "10번 나와도 1번의 10배가 아님 (k1 = 1.5)", {
      x: x + 0.2, y: py + 2.62, w: pw - 0.4, h: 0.5, color: C.slate, fontSize: 15, align: "center",
    });
  }

  // ②-IDF: 등장 문서 수와 가중치 (예시)
  {
    const x = px[1];
    text(s, "등장한 문서 (예시)", { x: x + 1.15, y: py + 0.72, w: 2.0, h: 0.27, color: C.sub, fontSize: 14 });
    text(s, "가중치", { x: x + 3.3, y: py + 0.72, w: 1.2, h: 0.27, color: C.sub, fontSize: 14 });
    [["카드", 5, 0.35, "약"], ["연회비", 1, 1.2, "강"]].forEach(([word, n, bw, lbl], r) => {
      const ry = py + 1.1 + r * 0.72;
      box(s, word, { x: x + 0.2, y: ry, w: 0.85, h: 0.42, r: 0.5, fill: C.white, line: C.navy, fontSize: 14 });
      for (let d = 0; d < 5; d++) {
        rect(s, { x: x + 1.2 + d * 0.4, y: ry, w: 0.3, h: 0.42, fill: d < n ? C.navy : C.white, line: d < n ? C.navy : C.pill });
      }
      rect(s, { x: x + 3.3, y: ry + 0.06, w: bw, h: 0.3, fill: C.blue });
      text(s, lbl, { x: x + 3.3 + bw + 0.08, y: ry, w: 0.4, h: 0.42, color: C.blue, bold: true, fontSize: 15 });
    });
    text(s, "흔한 말은 약하게, 드문 말은 강하게 쳐줌", {
      x: x + 0.2, y: py + 2.62, w: pw - 0.4, h: 0.5, color: C.slate, fontSize: 15, align: "center",
    });
  }

  // ③-길이 보정: tf=2, k1=1.5, b=0.75 → 짧은(평균×0.5)=1.70, 긴(평균×2)=1.08
  {
    const x = px[2], base = py + 2.25;
    const docs = [{ lx: 0.35, h: 0.75, lines: 2, t: "짧은 문서" }, { lx: 1.45, h: 1.4, lines: 6, t: "긴 문서" }];
    docs.forEach((d) => {
      rect(s, { x: x + d.lx, y: base - d.h, w: 0.9, h: d.h, fill: C.white, line: C.navy, lw: 1.5 });
      for (let l = 0; l < d.lines; l++) rect(s, { x: x + d.lx + 0.15, y: base - d.h + 0.18 + l * 0.2, w: 0.6, h: 0.06, fill: C.border });
      text(s, d.t, { x: x + d.lx - 0.15, y: base + 0.03, w: 1.2, h: 0.27, color: C.slate, fontSize: 14, align: "center" });
    });
    text(s, "같은 2회의 TF 점수", { x: x + 2.55, y: py + 0.72, w: 2.1, h: 0.27, color: C.sub, fontSize: 14, align: "center" });
    rect(s, { x: x + 2.6, y: base, w: 2.0, h: 0.02, fill: C.sub });
    [[1.70, "짧은", C.blue], [1.08, "긴", C.navy]].forEach(([v, lbl, col], k) => {
      const bx = x + 2.85 + k * 0.85, bh = v * 0.5;
      rect(s, { x: bx, y: base - bh, w: 0.55, h: bh, fill: col });
      text(s, v.toFixed(2), { x: bx - 0.15, y: base - bh - 0.29, w: 0.85, h: 0.27, color: C.ink, fontSize: 14, align: "center" });
      text(s, lbl, { x: bx - 0.15, y: base + 0.03, w: 0.85, h: 0.27, color: C.slate, fontSize: 14, align: "center" });
    });
    text(s, "긴 문서가 거저 얻는 점수를 덜어냄 (b = 0.75)", {
      x: x + 0.2, y: py + 2.62, w: pw - 0.4, h: 0.5, color: C.slate, fontSize: 15, align: "center",
    });
  }

  // 프로젝트 설정
  box(s, "프로젝트 설정", { x: 0.55, y: 7.7, w: 2.1, h: 0.45, r: 0.15, fill: C.dark, color: C.white, fontSize: 15 });
  ["k1 = 1.5", "b = 0.75", "BM25S · lucene 방식", "Kiwi + 카드명 사용자 사전"].forEach((t, k) => {
    const w = [1.5, 1.5, 2.9, 3.6][k];
    const x = 2.85 + [0, 1.65, 3.3, 6.35][k];
    box(s, t, { x, y: 7.7, w, h: 0.45, r: 0.5, fill: C.white, line: C.pill, fontSize: 15 });
  });

  footer(s, "출처: 교재 10.RAG.md §4.2.1 · Robertson & Zaragoza(2009) BM25 and Beyond · github.com/bab2min/Kiwi · " +
    "github.com/xhluca/bm25s · indexer lexical_index.py · retriever korean_tokenizer.py · 막대 값은 BM25 TF 항으로 계산", 2);
  s.addNotes(
    "한국어는 '연회비는/연회비가/연회비를'이 서로 다른 글자라 그대로 비교하면 같은 말을 못 알아봄. 그래서 Kiwi로 조사를 떼고 뜻 있는 낱말만 남김.\n" +
    "토큰 예시는 프로젝트 가상환경에서 실제로 실행한 결과임. 토크나이저 서명(SHA-256)이 색인과 다르면 검색을 거부함.\n" +
    "막대 값: TF 항 = tf×(k1+1)/(tf+k1×(1−b+b×문서길이/평균길이)), k1=1.5, b=0.75. IDF 그림의 문서 수는 설명용 예시임."
  );
}

// ---------- 슬라이드 3: Dense ----------
async function createSlide03() {
  const s = pptx.addSlide({ masterName: "MASTER" });
  pageHeader(s, {
    crumb: "RAG › 4.2 Retrieval › 4.2.2 Dense",
    title: "Dense Retrieval — 임베딩과 코사인 유사도",
    lead: "문장을 숫자 목록(벡터)으로 바꾼 뒤, 질문과 \"방향\"이 가장 비슷한 문서를 고름",
  });

  // ① 흐름
  const fy = 2.3, fh = 1.15, gap = 0.42;
  const ws = [3.4, 2.3, 3.3, 2.3, 1.92];
  const xs = [];
  let cx = 0.55;
  ws.forEach((w) => { xs.push(cx); cx += w + gap; });
  box(s, [
    { text: "질문\n", options: { fontSize: fsMin(14), color: C.sub, bold: false } },
    { text: "“연회비 안 내도 되는 경우”", options: { fontSize: fsMin(17) } },
  ], { x: xs[0], y: fy, w: ws[0], h: fh, fill: C.white, line: C.navy, lw: 1.5 });
  box(s, [
    { text: "KURE-v2\n", options: { fontSize: fsMin(17) } },
    { text: "임베딩 모델", options: { fontSize: fsMin(14), bold: false } },
  ], { x: xs[1], y: fy, w: ws[1], h: fh, fill: C.navy, color: C.white });
  rect(s, { x: xs[2], y: fy, w: ws[2], h: fh, round: true, r: 0.15, fill: C.tint, line: C.border });
  const vw = [0.66, 0.74, 0.66, 0.66];
  let vx = xs[2] + 0.17;
  ["0.12", "-0.34", "0.56", "…"].forEach((t, k) => {
    box(s, t, { x: vx, y: fy + 0.14, w: vw[k], h: 0.42, r: 0.1, fill: C.white, line: C.blue, fontSize: 14 });
    vx += vw[k] + 0.06;
  });
  text(s, "숫자 768개 (벡터)", { x: xs[2], y: fy + 0.66, w: ws[2], h: 0.38, color: C.navy, bold: true, fontSize: 15, align: "center" });
  box(s, [
    { text: "ChromaDB\n", options: { fontSize: fsMin(17) } },
    { text: "코사인 비교", options: { fontSize: fsMin(14), bold: false, color: C.slate } },
  ], { x: xs[3], y: fy, w: ws[3], h: fh, line: C.border });
  box(s, [
    { text: "Top-K\n", options: { fontSize: fsMin(17) } },
    { text: "후보 ×4 수집", options: { fontSize: fsMin(14), bold: false } },
  ], { x: xs[4], y: fy, w: ws[4], h: fh, fill: C.blue, color: C.white });
  for (let k = 0; k < 4; k++) stepArrow(s, xs[k] + ws[k] + 0.05, fy + fh / 2);

  // ② 벡터 공간 (예시)
  const lx = 0.55, ly = 3.7, lw = 7.6, lh = 4.45;
  card(s, { x: lx, y: ly, w: lw, h: lh });
  text(s, "벡터 공간에서 보기 (예시)", { x: lx + 0.25, y: ly + 0.15, w: 4.5, h: 0.4, color: C.navy, bold: true, fontSize: 18 });
  const ox = lx + 0.7, oy = ly + 3.85;
  arrow(s, ox, oy, ox + 5.6, oy, { color: C.border, width: 1.5, head: false });
  arrow(s, ox, oy, ox, oy - 3.2, { color: C.border, width: 1.5, head: false });
  arrow(s, ox, oy, ox + 4.6, oy - 0.7, { color: C.sub, width: 2.5 });
  arrow(s, ox, oy, ox + 0.9, oy - 2.7, { color: C.sub, width: 2.5 });
  arrow(s, ox, oy, ox + 3.0, oy - 2.7, { color: C.navy, width: 3 });
  arrow(s, ox, oy, ox + 4.2, oy - 2.6, { color: C.blue, width: 4.5 });
  oval(s, { x: ox - 0.08, y: oy - 0.08, d: 0.16, fill: C.ink });
  text(s, "질문", { x: ox + 4.27, y: oy - 2.82, w: 0.9, h: 0.34, color: C.blue, bold: true, fontSize: 17 });
  text(s, "“연회비 면제 조건” ✓", { x: ox + 2.3, y: oy - 3.17, w: 2.5, h: 0.34, color: C.navy, bold: true, fontSize: 16, align: "center" });
  text(s, "“해외 결제”", { x: ox + 0.15, y: oy - 3.1, w: 1.5, h: 0.3, color: C.sub, fontSize: 15 });
  text(s, "“포인트 적립”", { x: ox + 4.0, y: oy - 0.48, w: 1.7, h: 0.3, color: C.sub, fontSize: 15 });
  text(s, "각도가 작을수록 유사 · 화살표 길이는 무시 · 점수 = 1 − 거리", {
    x: lx + 0.25, y: ly + 3.95, w: lw - 0.5, h: 0.4, color: C.slate, fontSize: 15, align: "center",
  });

  // ③ MMR
  const rx = 8.4, ry = 3.7, rw = 7.05, rh = 4.45;
  card(s, { x: rx, y: ry, w: rw, h: rh });
  headerBar(s, { x: rx, y: ry, w: rw, t: "MMR — 비슷한 결과 쏠림 줄이기 (선택 옵션)", accent: true, fontSize: 20 });
  const topicColor = { A: C.navy, B: C.blue, C: C.dark, D: C.sub };
  [["similarity (기본)", ["A", "A", "A", "A", "B"], "같은 내용이 반복됨"],
    ["mmr", ["A", "B", "C", "A", "D"], "관련성 + 다양성을 함께 봄"]].forEach(([label, blocks, note], r) => {
    const by = ry + 0.85 + r * 1.1;
    text(s, label, { x: rx + 0.25, y: by, w: 2.4, h: 0.55, color: C.navy, bold: true, fontSize: 17 });
    blocks.forEach((b, k) => box(s, b, {
      x: rx + 2.7 + k * 0.72, y: by, w: 0.6, h: 0.55, r: 0.12, fill: topicColor[b], color: C.white, fontSize: 16,
    }));
    text(s, note, { x: rx + 2.7, y: by + 0.58, w: 3.6, h: 0.3, color: C.slate, fontSize: 14 });
  });
  // λ 눈금
  const tx0 = rx + 0.6, tw = 5.85, ty = ry + 3.4;
  text(s, "λ = 0.5 (MMR_LAMBDA_MULT)", { x: tx0 + tw / 2 - 1.6, y: ty - 0.42, w: 3.2, h: 0.3, color: C.blue, bold: true, fontSize: 15, align: "center" });
  rect(s, { x: tx0, y: ty, w: tw, h: 0.1, round: true, r: 0.5, fill: C.border });
  oval(s, { x: tx0 + tw / 2 - 0.15, y: ty - 0.1, d: 0.3, fill: C.blue });
  text(s, "0 · 다양성 우선", { x: tx0 - 0.3, y: ty + 0.18, w: 2.2, h: 0.3, color: C.sub, fontSize: 14 });
  text(s, "1 · 관련성 우선", { x: tx0 + tw - 1.9, y: ty + 0.18, w: 2.2, h: 0.3, color: C.sub, fontSize: 14, align: "right" });
  text(s, "기본값은 꺼짐 · MMR을 써도 결과 점수는 원래 코사인 값", {
    x: rx + 0.25, y: ry + 3.95, w: rw - 0.5, h: 0.4, color: C.slate, fontSize: 15, align: "center",
  });

  footer(s, "출처: 교재 10.RAG.md §4.2.2 · Carbonell & Goldstein(1998) MMR · huggingface.co/nlpai-lab/KURE-v2 · " +
    "vector-retriever settings.py, chroma_store.py · 768차원은 프로젝트 색인 /health 실측값", 3);
  s.addNotes(
    "Dense의 장점은 문서에 없는 표현('안 내도 되는')으로 물어도 '면제 조건' 문서를 찾는다는 점임.\n" +
    "약점은 'D1 제10조' 같은 딱 떨어지는 코드·조항을 흐릿하게 본다는 점이며, 그래서 다음 장의 Hybrid가 필요함.\n" +
    "벡터 공간 그림은 설명용 예시임. MMR은 결과 5개가 사실상 같은 내용일 때 켜는 옵션이며 프로젝트 기본값은 similarity임.\n" +
    "KURE-v2 모델 페이지 설명은 바뀌었으므로 768차원은 프로젝트 색인에서 직접 읽은 값을 근거로 함."
  );
}

// ---------- 슬라이드 4: Hybrid ----------
async function createSlide04() {
  const s = pptx.addSlide({ masterName: "MASTER" });
  pageHeader(s, {
    crumb: "RAG › 4.2 Retrieval › 4.2.3 Hybrid",
    title: "Hybrid Search — 두 점수를 합치는 두 가지 방법",
    lead: "BM25 점수와 코사인 점수는 단위가 달라 그냥 더할 수 없음 — 교재는 \"순위\"로, 프로젝트는 \"0 ~ 1 점수\"로 합침",
  });

  // ① 좌: RRF
  const lx = 0.55, ly = 2.3, lw = 7.3, lh = 4.05;
  card(s, { x: lx, y: ly, w: lw, h: lh });
  headerBar(s, { x: lx, y: ly, w: lw, t: "교재 — RRF (순위로 합치기)", fontSize: 20 });
  text(s, "점수 = Σ 1 ÷ (60 + 순위)", { x: lx, y: ly + 0.65, w: lw, h: 0.42, color: C.navy, bold: true, fontSize: 18, align: "center" });
  const rows = [
    { d: "A", r1: "BM25 1위", r2: "Dense 3위", calc: "1/61 + 1/63", v: 0.0323 },
    { d: "B", r1: "BM25 5위", r2: "Dense 1위", calc: "1/65 + 1/61", v: 0.0318 },
  ];
  rows.forEach((row, k) => {
    const ry = ly + 1.2 + k * 1.0;
    box(s, row.d, { shape: pptx.shapes.OVAL, x: lx + 0.25, y: ry, w: 0.55, h: 0.55, fill: C.dark, color: C.white, fontSize: 18 });
    box(s, row.r1, { x: lx + 1.0, y: ry + 0.06, w: 1.4, h: 0.42, r: 0.5, fill: C.navy, color: C.white, fontSize: 14 });
    box(s, row.r2, { x: lx + 2.5, y: ry + 0.06, w: 1.4, h: 0.42, r: 0.5, fill: C.blue, color: C.white, fontSize: 14 });
    text(s, row.calc, { x: lx + 4.1, y: ry + 0.06, w: 1.9, h: 0.42, color: C.slate, fontSize: 16 });
    const bw = 4.6 * (row.v / 0.0323);
    rect(s, { x: lx + 1.0, y: ry + 0.58, w: bw, h: 0.3, fill: k === 0 ? C.navy : C.sub });
    text(s, row.v.toFixed(4), { x: lx + 1.0 + bw + 0.1, y: ry + 0.56, w: 1.0, h: 0.34, color: C.ink, bold: true, fontSize: 15 });
  });
  callout(s, "A가 근소하게 위 — 몇 점인지 버리고 몇 등인지만 봄", { x: lx + 0.25, y: ly + 3.35, w: lw - 0.5, fontSize: 16 });

  // ② 우: 정규화 가중합
  const rx = 8.15, ry = 2.3, rw = 7.3, rh = 4.05;
  card(s, { x: rx, y: ry, w: rw, h: rh });
  headerBar(s, { x: rx, y: ry, w: rw, t: "이 프로젝트 — 정규화 가중합", accent: true, fontSize: 20 });
  text(s, "① 0 ~ 1로 다시 펴기 (최소-최대 정규화)", { x: rx + 0.25, y: ry + 0.65, w: 6.5, h: 0.4, color: C.navy, bold: true, fontSize: 16 });
  const base = ry + 2.4;
  [[2, 5, 8], [0, 0.5, 1.0]].forEach((vals, g) => {
    const gx = rx + (g === 0 ? 0.45 : 3.3);
    const sc = g === 0 ? 0.12 : 0.96;
    rect(s, { x: gx - 0.1, y: base, w: 2.15, h: 0.02, fill: C.sub });
    vals.forEach((v, k) => {
      const bh = Math.max(v * sc, 0.03), bx = gx + k * 0.68;
      rect(s, { x: bx, y: base - bh, w: 0.45, h: bh, fill: g === 0 ? C.sub : C.blue });
      text(s, g === 0 ? String(v) : v.toFixed(1), { x: bx - 0.15, y: base - bh - 0.29, w: 0.75, h: 0.27, color: C.ink, fontSize: 14, align: "center" });
    });
    text(s, g === 0 ? "원점수" : "정규화 점수", { x: gx - 0.1, y: base + 0.04, w: 2.15, h: 0.28, color: C.slate, fontSize: 14, align: "center" });
  });
  stepArrow(s, rx + 2.65, base - 0.6);
  text(s, "(점수 − 최소)\n÷ (최대 − 최소)", { x: rx + 5.45, y: base - 1.1, w: 1.75, h: 0.8, color: C.slate, fontSize: 14, align: "center" });
  text(s, "② 6 : 4로 더하기 — 점수 차 크기까지 반영", { x: rx + 0.25, y: ry + 2.85, w: 6.8, h: 0.4, color: C.navy, bold: true, fontSize: 16 });
  const sw = rw - 0.5;
  box(s, "Vector × 0.6", { x: rx + 0.25, y: ry + 3.33, w: sw * 0.6, h: 0.5, r: 0.1, fill: C.blue, color: C.white, fontSize: 16 });
  box(s, "BM25 × 0.4", { x: rx + 0.25 + sw * 0.6, y: ry + 3.33, w: sw * 0.4, h: 0.5, r: 0.1, fill: C.navy, color: C.white, fontSize: 16 });

  // ③ 하단: 실측
  rect(s, { x: 0.55, y: 6.55, w: 14.9, h: 1.62, round: true, r: 0.08, fill: C.tint, line: C.border });
  box(s, "실측", { x: 0.75, y: 6.68, w: 0.85, h: 0.36, r: 0.15, fill: C.dark, color: C.white, fontSize: 14 });
  text(s, "2026-09-20 · 질문 10건 · Top-5 · 질문 변환 off   (● 정답 문서 찾음  ○ 놓침)", {
    x: 1.75, y: 6.68, w: 6.8, h: 0.36, color: C.slate, fontSize: 14,
  });
  [["vector", [3, 9], "8 / 10"], ["hybrid", [9], "9 / 10"]].forEach(([mode, miss, score], r) => {
    const dy = 7.15 + r * 0.5;
    text(s, mode, { x: 0.8, y: dy, w: 1.2, h: 0.36, color: C.navy, bold: true, fontSize: 16 });
    for (let k = 0; k < 10; k++) {
      const hit = !miss.includes(k);
      oval(s, { x: 2.05 + k * 0.44, y: dy + 0.03, d: 0.3, fill: hit ? (r === 1 ? C.blue : C.navy) : C.white, line: hit ? undefined : C.sub });
    }
    text(s, score, { x: 6.55, y: dy, w: 1.3, h: 0.36, color: C.navy, bold: true, fontSize: 18 });
  });
  rect(s, { x: 8.35, y: 6.75, w: 0.02, h: 1.25, fill: C.border });
  text(s, "응답 시간 중앙값 — 거의 같음", { x: 8.6, y: 6.68, w: 6.5, h: 0.36, color: C.slate, fontSize: 14 });
  [["vector", 186.4, C.navy], ["hybrid", 195.4, C.blue]].forEach(([mode, ms, col], r) => {
    const dy = 7.15 + r * 0.5;
    text(s, mode, { x: 8.6, y: dy, w: 1.2, h: 0.36, color: C.navy, bold: true, fontSize: 16 });
    const bw = (ms / 200) * 3.6;
    rect(s, { x: 9.9, y: dy + 0.04, w: bw, h: 0.3, fill: col });
    text(s, `${Math.round(ms)}ms`, { x: 9.9 + bw + 0.1, y: dy, w: 1.0, h: 0.36, color: C.ink, bold: true, fontSize: 15 });
  });

  footer(s, "출처: 교재 10.RAG.md §4.2.3 (RRF 예시) · Cormack et al.(2009, SIGIR) RRF · vector-retriever scoring.py, settings.py · " +
    "data/retriever_10q_4mode_results.json", 4);
  s.addNotes(
    "RRF는 '몇 점인지'는 잊고 '몇 등인지'만 보는 방식이라 단위가 다른 검색기를 섞을 때 안전함. 예시 수치는 교재 §4.2.3 그대로임.\n" +
    "프로젝트는 두 점수를 각각 최소 0·최대 1로 다시 펴서 6:4로 더함(scoring.py fuse). 1등의 점수 차를 살리는 대신, 후보 집합이 바뀌면 정규화 결과도 바뀜.\n" +
    "실측 응답 시간은 평균이 아니라 중앙값임. 평균은 각 모드 첫 질문의 모델 적재 시간이 섞여 부풀려져 있음."
  );
}

async function main() {
  pptx = new pptxgen();
  pptx.defineLayout({ name: "CUSTOM", width: 16, height: 9 });
  pptx.layout = "CUSTOM";
  pptx.title = "검색 테크닉";
  pptx.defineSlideMaster({ title: "MASTER", background: { color: "FFFFFF" } });

  for (const fn of [createSlide01, createSlide02, createSlide03, createSlide04]) {
    await fn();
  }

  const out = path.resolve(__dirname, "..", "retrieval_techniques.pptx");
  await pptx.writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
