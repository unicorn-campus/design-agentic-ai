// KG의 모양 장표 1장 (KG의 G가 그래프라 'KG 그래프'로 겹쳐 쓰지 않음) — script.md 기준, references/pptx-guide.md 6절 규칙 적용
// 값은 v0 활성 세대 gen-sample-005-dbe57d45의 kg_prepared.json(약관 청크 2개, 제15조 ~ 제17조)에서 가져옴
// v3: 가장 바깥에 KG 하나를 두고, 그 안을 엔티티 그래프(지식 층)와 Lexical Graph(원문 층)로 나눠 그림
// v4: 엔티티는 한 색의 원, 관계는 한 색의 실선으로 통일하고 범례 견본으로 구분. 청크 노드는 엔티티 아님을 표시
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "KG모양.pptx");

// 엔티티는 원, 청크 노드는 둥근 사각형으로 그려 "LLM이 뽑은 노드인지"를 모양으로 구분함
function node(s, lines, { cx, cy, w, h, fill, line = null, color = C.white, size = 14, lw = 1.25, rect = false }) {
  const runs = lines.map((t, i) => ({
    text: t, options: { bold: i === 0, fontSize: fs(size), color, breakLine: i < lines.length - 1 },
  }));
  const P = L.getPptx();
  s.addText(runs, {
    shape: rect ? P.shapes.ROUNDED_RECTANGLE : P.shapes.OVAL, x: cx - w / 2, y: cy - h / 2, w, h,
    ...(rect ? { rectRadius: 0.12 } : {}),
    fill: { color: fill }, line: line ? { color: line, width: lw } : { type: "none" },
    fontFace: FONT, align: "center", valign: "middle", margin: 0, isTextBox: false, paraSpaceAfter: 0,
  });
}

// 관계 이름표: 선 위에 흰 바탕 작은 상자로 얹어 "이 선이 관계"임을 바로 읽게 함
function relLabel(s, t, { cx, cy, w, color = C.slate }) {
  const h = 0.32;
  L.rr(s, { x: cx - w / 2, y: cy - h / 2, w, h, fill: C.white, line: color, lw: 0.75, r: 0.06 });
  s.addText(t, { x: cx - w / 2, y: cy - h / 2, w, h, fontFace: FONT, fontSize: fs(14), color, bold: true,
    align: "center", valign: "middle", margin: 0, isTextBox: true, paraSpaceAfter: 0 });
}


// 층 이름: 굵은 첫 줄 + 설명 줄
function layerTitle(s, title, desc, { x, y, w, h, align = "left", color = C.navy }) {
  s.addText([
    { text: title, options: { bold: true, color, breakLine: true } },
    { text: desc, options: { color: C.body } },
  ], { x, y, w, h, fontFace: FONT, fontSize: fs(14), margin: 0, valign: "top", align, isTextBox: true,
    paraSpaceAfter: 0 });
}

// 엔티티는 모두 같은 색의 원, 엔티티 사이 관계는 모두 같은 색의 실선(범례 견본과 같은 값)
const ENT_FILL = C.tint, ENT_LINE = C.blue, REL_C = C.slate;
const ENT_STYLE = { fill: ENT_FILL, line: ENT_LINE, color: C.ink };

async function createSlide01() {
  const s = L.newSlide({
    title: "2. 인덱싱: KG 구축 - KG의 모양",
    lead: "엔티티 그래프의 모든 엔티티는 Lexical Graph의 청크 노드에 FROM_CHUNK로 이어짐 (KG 하나 안의 두 층)",
    notes: "가장 바깥 틀이 KG입니다. Neo4j에 하나로 저장됩니다. 그 안을 논리적으로 두 층으로 나눠 볼 수 "
      + "있습니다. 위층은 엔티티 그래프입니다. LLM이 조항 단위로 읽고 뽑은 엔티티와 관계입니다. 원은 엔티티이고, "
      + "약관 문서, 조항, 조건, 기한, 처리가 모두 엔티티입니다. 이름표가 붙은 선이 관계입니다. 문서가 조항을 가지는 "
      + "HAS_CLAUSE, 조항이 조건, 기한, 처리를 정하는 SETS_REQUIREMENT, SETS_DEADLINE, DEFINES_HANDLING이 있습니다.\n"
      + "아래층은 Lexical Graph입니다. 검색엔진의 청크를 코드가 그대로 옮긴 청크 노드입니다. LLM이 뽑은 것이 아니고, "
      + "chunk_id가 검색엔진과 같습니다. 원문 본문도 함께 들어 있어 답의 근거를 보여 줄 때 씁니다. v0는 Document "
      + "노드와 NEXT_CHUNK는 만들지 않고 청크 노드만 둡니다.\n"
      + "두 층은 따로 저장되지 않고 같은 그래프 안에서 FROM_CHUNK로 이어집니다. 엔티티마다 자기 조항이 나온 청크로 "
      + "이어집니다. 제15조는 왼쪽 청크에만, 제17조는 오른쪽 청크에만 있습니다. 제16조와 제16조의2는 두 청크가 "
      + "겹치는 구간에 있어 두 청크 모두에 이어집니다. 약관 문서 노드도 두 청크 모두에 이어집니다. 그림이 복잡해지지 "
      + "않게 점선 묶음마다 선을 모아 그렸습니다. 점선 묶음은 설명용 표시이고, 추출 단위는 그래프에 남지 않습니다.\n"
      + "색과 모양 읽는 법입니다. 같은 색의 원은 모두 엔티티 노드이고, 같은 색의 실선은 엔티티 사이 관계입니다. 관계 "
      + "종류는 선 위 이름표로 구분합니다. 남색 사각형은 청크 노드로, 글에서 뽑은 개체가 아니라 엔티티가 아닙니다. "
      + "남색 점선이 FROM_CHUNK 관계이고, 엔티티 그래프의 모든 엔티티가 이 관계로 청크 노드에 이어집니다.",
  });

  // ── 관계 이름 범례(KG 틀 바깥 한 줄): 선 위 우리말 이름표와 실제 관계 이름을 짝지음
  s.addText([
    { text: "관계 이름  ", options: { bold: true, color: C.slate } },
    { text: "조항 가짐 = HAS_CLAUSE,  조건 둠 = SETS_REQUIREMENT,  기한 둠 = SETS_DEADLINE,  "
      + "처리 정함 = DEFINES_HANDLING", options: { color: C.body } },
  ], { x: X0, y: 1.74, w: XR - X0, h: 0.28, fontFace: FONT, fontSize: fs(14), margin: 0, valign: "middle",
    isTextBox: true, paraSpaceAfter: 0 });

  // ── 위치 상수
  const KG = { x: X0, y: 2.24, w: XR - X0, h: 6.14 };
  const ENT = { x: X0 + 0.12, y: 2.44, w: XR - X0 - 0.24, h: 4.5 };      // 엔티티 그래프 층
  const LEX = { x: X0 + 0.12, y: 7.16, w: XR - X0 - 0.24, h: 1.1 };      // Lexical Graph 층
  const DOC = { cx: 8.0, cy: 3.2, w: 2.9, h: 0.8 };
  const CHA = { cx: 4.3, cy: 7.74, w: 2.6, h: 0.74 }, CHB = { cx: 11.7, cy: 7.74, w: 2.6, h: 0.74 };
  const GY = 4.05, GH = 2.78, CLY = 4.6, R1 = 6.05;
  const EW = 1.4, EH = 0.85, PAD = 0.2, GAP = 0.1;

  // ── 바깥 KG 틀과 두 층(뒤에 깔림)
  L.rr(s, { x: KG.x, y: KG.y, w: KG.w, h: KG.h, fill: C.white, line: C.navy, lw: 2, r: 0.14 });
  L.rr(s, { x: ENT.x, y: ENT.y, w: ENT.w, h: ENT.h, fill: C.white, line: C.blue, lw: 1.25, r: 0.1 });
  L.rr(s, { x: LEX.x, y: LEX.y, w: LEX.w, h: LEX.h, fill: C.tableHead, line: C.navy, lw: 1.25, r: 0.1 });
  L.card(s, "KG  (Neo4j에 하나로 저장)", { x: KG.x + 0.25, y: KG.y - 0.17, w: 3.3, h: 0.36, fill: C.navy, line: null,
    color: C.white, size: 16, bold: true, r: 0.06 });
  L.text(s, "엔티티 그래프 (지식 층): LLM이 조항 단위로 추출", { x: ENT.x + 0.2, y: ENT.y + 0.1, w: 5.8, h: 0.3,
    size: 14, bold: true, color: C.blue, margin: 0 });
  // 범례 견본: 모양과 색으로 엔티티, 관계, FROM_CHUNK, 청크 노드를 구분
  const LX = ENT.x + 0.2, R2 = ENT.y + 0.62, R3 = ENT.y + 1.04;
  const swatchText = (t, x, y, w) => L.text(s, t, { x, y: y - 0.15, w, h: 0.3, size: 14, color: C.body, margin: 0 });
  const C2 = 2.75;  // 범례 둘째 열 시작(첫째 열 글과 붙지 않게)
  s.addShape(L.getPptx().shapes.OVAL, { x: LX, y: R2 - 0.17, w: 0.55, h: 0.34, fill: { color: ENT_FILL },
    line: { color: ENT_LINE, width: 1.25 } });
  swatchText("엔티티 노드", LX + 0.65, R2, 1.9);
  L.arrow(s, { x1: LX + C2, y1: R2, x2: LX + C2 + 0.6, y2: R2, color: REL_C, width: 1.25 });
  swatchText("관계 (이름표로 종류 표시)", LX + C2 + 0.7, R2, 2.7);
  L.arrow(s, { x1: LX, y1: R3, x2: LX + 0.55, y2: R3, color: C.navy, width: 2.25, dash: "dash" });
  swatchText("FROM_CHUNK 관계", LX + 0.65, R3, 1.9);
  L.rr(s, { x: LX + C2, y: R3 - 0.15, w: 0.6, h: 0.3, fill: C.navy, line: null, r: 0.06 });
  swatchText("청크 노드 (엔티티 아님)", LX + C2 + 0.7, R3, 2.7);
  s.addText([
    { text: "Lexical Graph (원문 층)", options: { bold: true, color: C.navy, breakLine: true } },
    { text: "코드가 검색 청크를 옮긴 청크 노드", options: { color: C.body, breakLine: true } },
    { text: "글에서 뽑은 개체가 아니므로 엔티티 아님", options: { color: C.body } },
  ], { x: 5.8, y: LEX.y + 0.12, w: 4.4, h: 0.82, fontFace: FONT, fontSize: fs(14), margin: 0, valign: "top",
    align: "center", isTextBox: true, paraSpaceAfter: 0 });

  // ── 조항 묶음 계산
  const spec = [
    { clause: ["제15조", "승인과 취소"], foot: "청크 a4fd…에만", A: true, B: false,
      ents: [["처리", "승인 시 기록"], ["처리", "결제 이월"]] },
    { clause: ["제16조", "할부 거래"], foot: "겹친 조항: 청크 2개", A: true, B: true,
      ents: [["조건", "승인 전 표시"], ["처리", "선납 재계산"]] },
    { clause: ["제16조의2", "철회 요청"], foot: "겹친 조항: 청크 2개 (처리 1개 더 있음)", A: true, B: true,
      ents: [["기한", "7일 내 철회"], ["조건", "철회 제한"], ["처리", "사유 안내"]] },
    { clause: ["제17조", "부가서비스 이용"], foot: "청크 112f…에만", A: false, B: true,
      ents: [["조건", "전월 실적"]] },
  ];
  const REL = { 조건: ["조건 둠", 0.8], 기한: ["기한 둠", 0.8], 처리: ["처리 정함", 0.95] };
  const widths = spec.map((g) => Math.max(g.ents.length * EW + (g.ents.length - 1) * GAP + 2 * PAD, 2.05));
  const total = widths.reduce((a, b) => a + b, 0) + 0.15 * (spec.length - 1);
  let gx = 8.0 - total / 2;
  const groups = spec.map((g, i) => {
    const w = widths[i], x = gx, cx = x + w / 2;
    gx += w + 0.15;
    const first = cx - ((g.ents.length - 1) * (EW + GAP)) / 2;
    return { ...g, x, w, cx, ents: g.ents.map((lines, k) => [lines, first + k * (EW + GAP) - cx, R1]),
      fromA: g.A ? (g.B ? cx - 0.5 : cx) : null, fromB: g.B ? (g.A ? cx + 0.5 : cx) : null };
  });

  // ── 점선 묶음
  groups.forEach((g) => {
    L.rr(s, { x: g.x, y: GY, w: g.w, h: GH, fill: C.altRow, line: C.pill, lw: 1.25, dash: "dash", r: 0.12 });
    L.text(s, g.foot, { x: g.x, y: GY + GH - 0.36, w: g.w, h: 0.32, size: 14, align: "center", margin: 0,
      color: g.A && g.B ? C.blue : C.sub, bold: !!(g.A && g.B) });
  });

  // ── FROM_CHUNK: 묶음 아래에서 층 경계를 건너 청크 노드 위로. 도착점은 청크 노드 윗변에 고르게 나눔
  const toA = groups.filter((g) => g.A), toB = groups.filter((g) => g.B);
  const land = (n, i, c) => c.cx + (n === 1 ? 0 : (i - (n - 1) / 2) * (c.w - 0.5) / (n - 1));
  toA.forEach((g, i) => L.arrow(s, { x1: g.fromA, y1: GY + GH, x2: land(toA.length, i, CHA), y2: CHA.cy - CHA.h / 2,
    color: C.navy, width: 2.25, dash: "dash" }));
  toB.forEach((g, i) => L.arrow(s, { x1: g.fromB, y1: GY + GH, x2: land(toB.length, i, CHB), y2: CHB.cy - CHB.h / 2,
    color: C.navy, width: 2.25, dash: "dash" }));
  // 문서 노드 → 청크 2개: 가장자리를 도는 긴 선은 틀처럼 보여 헷갈리므로, 문서 노드 옆 짧은 점선과 글로 표시함
  L.arrow(s, { x1: DOC.cx + DOC.w / 2, y1: DOC.cy, x2: DOC.cx + DOC.w / 2 + 0.5, y2: DOC.cy, color: C.navy,
    width: 2.25, dash: "dash" });

  // ── 문서 노드 → 조항(HAS_CLAUSE), 조항 → 엔티티
  groups.forEach((g) => L.arrow(s, { x1: DOC.cx, y1: DOC.cy + DOC.h / 2, x2: g.cx, y2: CLY - 0.4,
    color: REL_C, width: 1.25 }));
  groups.forEach((g) => g.ents.forEach(([, dx, ry]) => {
    const tx = g.cx + dx, sx = g.cx + Math.max(-0.45, Math.min(0.45, dx * 0.4));  // 조항 원 아래쪽에서 퍼져 나감
    L.arrow(s, { x1: sx, y1: CLY + 0.37, x2: tx, y2: ry - EH / 2, color: REL_C, width: 1.25 });
  }));

  // ── 관계 이름표
  groups.forEach((g) => {
    g.ents.forEach(([lines, dx, ry]) => {
      const sx = g.cx + Math.max(-0.45, Math.min(0.45, dx * 0.4)), tx = g.cx + dx, t = 0.72;
      const y1 = CLY + 0.37, y2 = ry - EH / 2;
      const [name, w] = REL[lines[0]];
      relLabel(s, name, { cx: sx + (tx - sx) * t, cy: y1 + (y2 - y1) * t, w });
    });
    relLabel(s, "조항 가짐", { cx: (DOC.cx + g.cx) / 2, cy: (DOC.cy + DOC.h / 2 + CLY - 0.4) / 2, w: 0.95 });
  });
  // 층 경계를 건너는 자리 가운데와 문서 노드 선 아래쪽에 FROM_CHUNK 이름표
  relLabel(s, "FROM_CHUNK: 엔티티 그래프의 모든 엔티티 → 나온 청크", { cx: 8.0, cy: (ENT.y + ENT.h + LEX.y) / 2, w: 5.4,
    color: C.navy });
  relLabel(s, "FROM_CHUNK: 청크 a4fd…, 112f… 둘 다", { cx: DOC.cx + DOC.w / 2 + 0.5 + 1.9, cy: DOC.cy, w: 3.8,
    color: C.navy });

  // ── 노드(선 위에 그림)
  node(s, ["약관 문서", "판 1.2, 시행 2027-01-15"], { ...DOC, ...ENT_STYLE });
  node(s, ["청크 노드 (Chunk)", "엔티티 아님, 검색 청크 a4fd…"], { ...CHA, fill: C.navy, rect: true });
  node(s, ["청크 노드 (Chunk)", "엔티티 아님, 검색 청크 112f…"], { ...CHB, fill: C.navy, rect: true });
  groups.forEach((g) => {
    node(s, g.clause, { cx: g.cx, cy: CLY, w: 1.85, h: 0.8, ...ENT_STYLE });
    g.ents.forEach(([lines, dx, ry]) => node(s, lines, { cx: g.cx + dx, cy: ry, w: EW, h: EH, ...ENT_STYLE }));
  });
}

async function main() {
  L.createDeck();
  await createSlide01();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
