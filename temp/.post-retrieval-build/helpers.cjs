// 공용 도형 헬퍼 — references/pptx-guide.md 6절 규칙(팔레트 상수·14pt 하한·pptx.shapes 참조)을 코드로 강제
const FONT = "Pretendard";
const C = {
  navy: "1E2A5C", blue: "2E74C6", ink: "2B3242", slate: "4A5364", sub: "7C8598",
  tint: "EEF3FA", alt: "F5F8FC", tableHead: "E2EEF9", dark: "404155",
  border: "D9E0EC", line: "EDF0F6", foot: "E9ECF3", pill: "C3CEE0", white: "FFFFFF",
};
const MIN_FONT = 14;
const fsMin = (n) => {
  if (n < MIN_FONT) throw new Error(`fontSize ${n} < ${MIN_FONT}pt 금지! 슬라이드를 분리할 것`);
  return n;
};

function make(pptx) {
  const S = pptx.shapes;

  function text(s, value, x, y, w, h, o = {}) {
    const { size = 18, color = C.ink, bold = false, align = "left", valign = "middle", ...rest } = o;
    s.addText(value, { x, y, w, h, fontFace: FONT, fontSize: fsMin(size), color, bold, align, valign, margin: 0, ...rest });
  }
  function box(s, x, y, w, h, o = {}) {
    const { fill = C.white, line = C.border, lw = 1, round = true, r = 0.08, dash } = o;
    s.addShape(round ? S.ROUNDED_RECTANGLE : S.RECTANGLE, {
      x, y, w, h, rectRadius: r, fill: { color: fill },
      line: line ? { color: line, width: lw, ...(dash ? { dashType: dash } : {}) } : { type: "none" },
    });
  }
  // 도형 + 가운데 텍스트를 한 덩어리로 — PowerPoint에서 도형 텍스트로 바로 수정 가능
  function card(s, x, y, w, h, value, o = {}) {
    const { fill = C.white, line = C.border, lw = 1, size = 16, color = C.ink, bold = false, align = "center", r = 0.08, round = true, dash } = o;
    s.addText(value, {
      shape: round ? S.ROUNDED_RECTANGLE : S.RECTANGLE, x, y, w, h, rectRadius: r,
      fill: { color: fill }, line: line ? { color: line, width: lw, ...(dash ? { dashType: dash } : {}) } : { type: "none" },
      fontFace: FONT, fontSize: fsMin(size), color, bold, align, valign: "middle", margin: 4,
    });
  }
  function arrow(s, x1, y1, x2, y2, o = {}) {
    const { color = C.blue, width = 2, dash, head = true } = o;
    const flipH = x2 < x1, flipV = y2 < y1;
    s.addShape(S.LINE, {
      x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH, flipV,
      line: { color, width, ...(dash ? { dashType: dash } : {}), ...(head ? { endArrowType: "triangle" } : {}) },
    });
  }
  function badge(s, x, y, n, o = {}) {
    const { color = C.blue, size = 0.42, fs = 16 } = o;
    s.addText(String(n), {
      shape: S.ROUNDED_RECTANGLE, x, y, w: size, h: size, rectRadius: 0.05, fill: { color }, line: { type: "none" },
      fontFace: FONT, fontSize: fsMin(fs), color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
    });
  }
  function pill(s, x, y, w, h, value, o = {}) {
    const { size = 14, fill = C.tint, line = C.pill, color = C.navy } = o;
    s.addText(value, {
      shape: S.ROUNDED_RECTANGLE, x, y, w, h, rectRadius: h / 2, fill: { color: fill }, line: { color: line, width: 1 },
      fontFace: FONT, fontSize: fsMin(size), color, bold: true, align: "center", valign: "middle", margin: 0,
    });
  }
  function headerBar(s, x, y, w, value, accent = false, h = 0.5) {
    s.addText(value, {
      shape: S.ROUNDED_RECTANGLE, x, y, w, h, rectRadius: 0.06,
      fill: { color: accent ? C.blue : C.navy }, line: { type: "none" },
      fontFace: FONT, fontSize: fsMin(20), color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
    });
  }
  // 문서 아이콘 — 접힌 모서리 도형(편집 가능)
  function doc(s, x, y, o = {}) {
    const { w = 0.38, h = 0.48, fill = C.white, line = C.blue, label } = o;
    s.addShape(S.FOLDED_CORNER || S.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: line, width: 1.25 } });
    if (label) text(s, label, x, y, w, h, { size: 14, bold: true, color: line === C.white ? C.navy : line, align: "center" });
  }
  function pageHeader(s, { crumb, title, lead, no, sources }) {
    s.background = { color: C.white };
    text(s, crumb, 0.55, 0.32, 12, 0.3, { size: 15, color: C.sub });
    text(s, title, 0.55, 0.6, 14.9, 0.82, { size: 48, color: C.navy, bold: true });
    s.addShape(S.RECTANGLE, { x: 0.55, y: 1.47, w: 14.9, h: 0.04, fill: { color: C.border }, line: { type: "none" } });
    s.addShape(S.RECTANGLE, { x: 0.55, y: 1.47, w: 2.1, h: 0.04, fill: { color: C.blue }, line: { type: "none" } });
    if (lead) text(s, lead, 0.55, 1.6, 14.9, 0.42, { size: 18, color: C.slate });
    // 하단 출처(작게) + 푸터
    s.addShape(S.LINE, { x: 0.55, y: 8.42, w: 14.9, h: 0, line: { color: C.foot, width: 1 } });
    text(s, "출처: " + sources, 0.55, 8.48, 13.9, 0.42, { size: 14, color: C.sub, valign: "top" });
    text(s, String(no).padStart(2, "0"), 14.75, 8.48, 0.7, 0.3, { size: 14, color: C.navy, bold: true, align: "right", valign: "top" });
  }
  return { text, box, card, arrow, badge, pill, headerBar, doc, pageHeader };
}

module.exports = { FONT, C, fsMin, make };
