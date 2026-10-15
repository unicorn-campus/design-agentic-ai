// SQL 검색기 소스설명서 공통 — 설계서 헬퍼(lib.js)에 발췌 상자, 카드 목록, 꺾인 화살표를 더함
const path = require("path");
const fs = require("fs");
const L = require("../quality-eval-design/lib");

const SNIPPETS = JSON.parse(fs.readFileSync(path.join(__dirname, "snippets.json"), "utf-8"));
const CODE = 13; // 코드 글자 크기(사용자 허용 하한 13pt, 2026-10-15)
const LINE_H = 0.21; // 13pt 코드 한 줄 높이(인치)
const TOP = 1.95, BOTTOM = 7.95;

// 발췌 상자 높이 — 머리말 0.44 + 줄 수 × 줄 높이
function codeH(key) {
  const item = SNIPPETS[key];
  if (!item) throw new Error(`발췌 없음: ${key}`);
  return 0.5 + item.lines.length * LINE_H;
}

// 소스 발췌 상자 — snippets.json의 글자를 그대로 씀(손으로 옮기지 않음). h를 안 주면 줄 수로 정함
function codePanel(s, key, { x, y, w, h, size = CODE }) {
  const item = SNIPPETS[key];
  if (!item) throw new Error(`발췌 없음: ${key}`);
  const hh = h || codeH(key);
  if (y + hh > BOTTOM + 0.001) throw new Error(`발췌 상자가 본문 아래 끝을 넘음: ${key} (${(y + hh).toFixed(2)})`);
  L.rr(s, { x, y, w, h: hh, fill: L.C.altRow, line: L.C.border, r: 0.06 });
  L.text(s, item.header, { x: x + 0.12, y: y + 0.05, w: w - 0.24, h: 0.32, size: 13, color: L.C.blue, bold: true });
  s.addText(item.lines.join("\n"), { x: x + 0.12, y: y + 0.4, w: w - 0.24, h: hh - 0.44, fontFace: L.FONT,
    fontSize: L.fs(size), color: L.C.ink, valign: "top", margin: 0.02, isTextBox: true, paraSpaceAfter: 0,
    lineSpacingMultiple: 0.95 });
  return hh;
}

// 번호 카드 목록 — [제목, 설명] 배열을 세로로 쌓음
function cards(s, items, { x, y, w, h, title, size = 14, gap = 0.12, headH = 0.4 }) {
  let top = y;
  if (title) {
    L.headerBar(s, title, { x, y, w, h: 0.42, size: 15 });
    top += 0.52;
  }
  const each = (y + h - top - gap * (items.length - 1)) / items.length;
  items.forEach(([head, body], i) => {
    const yy = top + i * (each + gap);
    L.rr(s, { x, y: yy, w, h: each, fill: i % 2 ? L.C.white : L.C.tint });
    L.numBadge(s, i + 1, { x: x + 0.1, y: yy + 0.1, size: 0.36, fsz: 14 });
    L.text(s, head, { x: x + 0.55, y: yy + 0.04, w: w - 0.65, h: headH, size: 15, bold: true, color: L.C.navy });
    if (body) L.text(s, body, { x: x + 0.55, y: yy + headH + 0.02, w: w - 0.65, h: each - headH - 0.06, size,
      color: L.C.body, valign: "top" });
  });
}

// 꺾인 화살표 — 점 목록을 선분으로 잇고 마지막 선분에만 화살촉을 붙임
function elbow(s, pts, { color = L.C.slate, width = 1.5, dash } = {}) {
  for (let i = 0; i < pts.length - 1; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
    L.arrow(s, { x1, y1, x2, y2, color, width, dash, head: i === pts.length - 2 ? "triangle" : "none" });
  }
}

module.exports = { ...L, SNIPPETS, codePanel, codeH, cards, elbow, CODE, TOP, BOTTOM };
