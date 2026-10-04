// 품질평가 설계서 빌드 공통 헬퍼 — references/pptx-guide.md 6절 규칙을 코드로 강제함
const pptxgen = require("pptxgenjs");

const FONT = "Pretendard";
const FONT_SB = "Pretendard SemiBold";
const LAYOUT = "내용_단쪽";
const X0 = 0.557, CW = 14.9, XR = X0 + CW;
const BODY_TOP = 1.9, BODY_BOTTOM = 7.95;

const C = {
  title: "2C2926", lead: "000000",
  navy: "1E2A5C", blue: "2E74C6", ink: "2B3242",
  slate: "4A5364", sub: "7C8598", body: "3B4557",
  tint: "EEF3FA", altRow: "F5F8FC", tableHead: "E2EEF9",
  dark: "404155", border: "D9E0EC", line: "EDF0F6", pill: "C3CEE0",
  titleLine: "E2E8F0", footLine: "E9ECF3", pageNum: "6B6B7B", white: "FFFFFF",
};

const MIN_FONT = 14;
const fs = (size) => {
  if (size < MIN_FONT) throw new Error(`fontSize ${size} < ${MIN_FONT}pt 금지 — 슬라이드를 나눌 것`);
  return size;
};

let pptx;

function createDeck() {
  pptx = new pptxgen();
  pptx.defineLayout({ name: "CUSTOM", width: 16, height: 9 });
  pptx.layout = "CUSTOM";
  pptx.defineSlideMaster({
    title: LAYOUT,
    background: { color: "FFFFFF" },
    objects: [
      { line: { x: 0.556, y: 0.95, w: 14.888, h: 0, line: { color: C.titleLine, width: 1.5 } } },
      { text: { text: "무단전재 및 배포 금지",
          options: { x: 0.4875, y: 8.517, w: 1.675, h: 0.27, fontFace: FONT, fontSize: 12, color: "A6A6A6", margin: 0 } } },
      { placeholder: { options: { name: "title", type: "title", x: X0, y: 0.109, w: 15.025, h: 0.906,
          fontFace: FONT, fontSize: 32, bold: true, color: C.title, margin: 0, align: "left", valign: "middle" }, text: "" } },
    ],
    slideNumber: { x: 11.913, y: 8.517, w: 3.6, h: 0.25, fontFace: FONT, fontSize: 16, color: C.pageNum, align: "right" },
  });
  return pptx;
}

function newSlide({ title, lead, notes }) {
  const s = pptx.addSlide({ masterName: LAYOUT });
  s.addText(title, { placeholder: "title" });
  if (lead) {
    s.addText(lead, { x: X0, y: 1.259, w: CW, h: 0.42, margin: 0, isTextBox: true,
      fontFace: FONT_SB, fontSize: fs(18), color: C.lead, valign: "middle" });
  }
  if (notes) s.addNotes(notes);
  return s;
}

// 둥근 사각형 — 둥글기는 짧은 변의 절반을 넘지 않게 제한(pptxgenjs 4 adj 범위 초과 손상 방지)
function rr(s, { x, y, w, h, fill = C.white, line = C.border, lw = 1, r = 0.08, dash }) {
  s.addShape(pptx.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: Math.min(r, 0.5 * Math.min(w, h) * 0.9),
    fill: { color: fill }, line: line ? { color: line, width: lw, dashType: dash || "solid" } : { type: "none" },
  });
}

function box(s, { x, y, w, h, fill = C.white, line = C.border, lw = 1, dash }) {
  s.addShape(pptx.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill },
    line: line ? { color: line, width: lw, dashType: dash || "solid" } : { type: "none" } });
}

function text(s, t, { x, y, w, h, size = 16, color = C.body, bold = false, align = "left", valign = "middle",
  face = FONT, italic = false, margin = 0.06 }) {
  s.addText(t, { x, y, w, h, fontFace: face, fontSize: fs(size), color, bold, align, valign, italic, margin,
    isTextBox: true, paraSpaceAfter: 0 });
}

// 라벨 박스: 둥근 사각형 + 가운데 글자
function card(s, t, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 16, bold = false,
  align = "center", valign = "middle", dash, r = 0.08, lw = 1 }) {
  rr(s, { x, y, w, h, fill, line, dash, r, lw });
  s.addText(t, { x, y, w, h, fontFace: FONT, fontSize: fs(size), color, bold, align, valign, margin: 0.08,
    isTextBox: true });
}

function headerBar(s, t, { x, y, w, h = 0.5, accent = false, size = 20 }) {
  card(s, t, { x, y, w, h, fill: accent ? C.blue : C.navy, line: null, color: C.white, size, bold: true, r: 0.06 });
}

function darkBadge(s, t, { x, y, w, h = 0.4, size = 16, fill = C.dark }) {
  card(s, t, { x, y, w, h, fill, line: null, color: C.white, size, bold: true, r: 0.05 });
}

function numBadge(s, n, { x, y, size = 0.42, fill = C.blue, fsz = 18 }) {
  card(s, String(n), { x, y, w: size, h: size, fill, line: null, color: C.white, size: fsz, bold: true, r: 0.05 });
}

function pill(s, t, { x, y, w, h = 0.36, size = 14 }) {
  card(s, t, { x, y, w, h, fill: C.tint, line: C.pill, color: C.navy, size, bold: true, r: h / 2 });
}

function arrow(s, { x1, y1, x2, y2, color = C.slate, width = 1.5, dash, head = "triangle" }) {
  const x = Math.min(x1, x2), y = Math.min(y1, y2);
  const w = Math.abs(x2 - x1), h = Math.abs(y2 - y1);
  s.addShape(pptx.shapes.LINE, { x, y, w, h, flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width, endArrowType: head, dashType: dash || "solid" } });
}

function hline(s, { x, y, w, color = C.border, width = 1, dash }) {
  s.addShape(pptx.shapes.LINE, { x, y, w, h: 0, line: { color, width, dashType: dash || "solid" } });
}

// 표: 첫 행은 머리 행. rows는 문자열 또는 {text, options} 셀
function table(s, rows, { x = X0, y, w = CW, colW, rowH = 0.46, size = 15, firstColBold = true, valign = "middle",
  autoPage = false }) {
  const data = rows.map((row, i) => row.map((cell, j) => {
    const base = typeof cell === "object" && cell !== null && "text" in cell ? cell : { text: String(cell) };
    const opt = { ...(base.options || {}) };
    if (i === 0) Object.assign(opt, { fill: { color: C.tableHead }, color: C.navy, bold: true, align: opt.align || "center" });
    else {
      if (opt.fill === undefined) opt.fill = { color: i % 2 === 0 ? C.altRow : C.white };
      if (opt.color === undefined) opt.color = C.body;
      if (j === 0 && firstColBold && opt.bold === undefined) opt.bold = true;
    }
    return { text: base.text, options: opt };
  }));
  s.addTable(data, { x, y, w, colW, rowH, fontSize: fs(size), fontFace: FONT, valign, margin: [0.03, 0.08, 0.03, 0.08],
    border: { type: "solid", color: C.line, pt: 1 }, autoPage });
}

// 인용 콜아웃: 왼쪽 파란 막대 + 굵은 글
function callout(s, t, { x = X0, y, w = CW, h = 0.5, size = 16 }) {
  box(s, { x, y, w: 0.07, h, fill: C.blue, line: null });
  text(s, t, { x: x + 0.18, y, w: w - 0.18, h, size, color: C.navy, bold: true });
}

// 코드 박스(고정폭 대신 Pretendard 유지 — 가이드 6-10)
function codeBox(s, lines, { x, y, w, h, size = 14, title }) {
  rr(s, { x, y, w, h, fill: C.altRow, line: C.border, r: 0.06 });
  let top = y + 0.08;
  if (title) {
    text(s, title, { x: x + 0.12, y: top, w: w - 0.24, h: 0.34, size: 14, color: C.sub, bold: true });
    top += 0.36;
  }
  s.addText(lines.join("\n"), { x: x + 0.12, y: top, w: w - 0.24, h: y + h - top - 0.06, fontFace: FONT,
    fontSize: fs(size), color: C.ink, valign: "top", margin: 0.02, isTextBox: true, paraSpaceAfter: 0,
    lineSpacingMultiple: 1.05 });
}

module.exports = { pptxgen, createDeck, newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow,
  hline, table, callout, codeBox, C, FONT, FONT_SB, X0, CW, XR, BODY_TOP, BODY_BOTTOM, fs, getPptx: () => pptx };
