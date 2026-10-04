// 소스설명서 공통 — 설계서 헬퍼(lib.js)에 발췌 상자 · 카드 목록을 더함
const path = require("path");
const fs = require("fs");
const L = require("../quality-eval-design/lib");

const SNIPPETS = JSON.parse(fs.readFileSync(path.join(__dirname, "snippets.json"), "utf-8"));
const CODE = 13; // 코드 글자 크기(사용자 허용 하한 13pt)

// 소스 발췌 상자 — snippets.json의 글자를 그대로 씀(손으로 옮기지 않음)
function codePanel(s, key, { x, y, w, h, size = CODE }) {
  const item = SNIPPETS[key];
  if (!item) throw new Error(`발췌 없음: ${key}`);
  L.rr(s, { x, y, w, h, fill: L.C.altRow, line: L.C.border, r: 0.06 });
  L.text(s, item.header, { x: x + 0.12, y: y + 0.05, w: w - 0.24, h: 0.32, size: 13, color: L.C.blue, bold: true });
  s.addText(item.lines.join("\n"), { x: x + 0.12, y: y + 0.38, w: w - 0.24, h: h - 0.44, fontFace: L.FONT,
    fontSize: L.fs(size), color: L.C.ink, valign: "top", margin: 0.02, isTextBox: true, paraSpaceAfter: 0,
    lineSpacingMultiple: 0.95 });
}

// 번호 카드 목록 — [제목, 설명] 배열을 세로로 쌓음
function cards(s, items, { x, y, w, h, title, size = 14, gap = 0.12 }) {
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
    L.text(s, head, { x: x + 0.55, y: yy + 0.04, w: w - 0.65, h: 0.4, size: 15, bold: true, color: L.C.navy });
    if (body) L.text(s, body, { x: x + 0.55, y: yy + 0.42, w: w - 0.65, h: each - 0.46, size, color: L.C.body,
      valign: "top" });
  });
}

module.exports = { ...L, SNIPPETS, codePanel, cards, CODE };
