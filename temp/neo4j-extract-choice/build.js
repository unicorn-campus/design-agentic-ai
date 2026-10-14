// node build.js — ④ 엔티티·관계 추출 도구(LangChain + Neo4j vs Native Neo4j) 비교 한 장 빌드 (script.md 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const GAP = 0.3;
const COL_W = (CW - GAP) / 2;
const Y = { head: 1.9, headH: 0.6, scope: 2.6, chipH: 0.42, code: 3.42, codeH: 0.9, pc: 4.42, pcH: 0.95, pcGap: 0.06,
  band: 6.49, bandH: 1.46 };

// 맡는 범위 칩 — 채움(맡음) · 옅은 채움(일부만) · 점선(없음: 다른 부품·직접 코드)
// 가명처리 칸을 넣어 두 도구 모두 앞단 정제·가명처리가 없다는 점을 보여 줌(사용자 지적 반영)
const STEPS = ["로드", "가명처리", "청킹", "④ 추출", "병합", "KG 저장", "임베딩"];
const CHIP = {
  own: (accent) => ({ fill: accent, line: null, color: C.white, dash: undefined }),
  part: (accent) => ({ fill: C.tint, line: accent, color: accent, dash: undefined }),
  none: () => ({ fill: C.white, line: C.sub, color: C.sub, dash: "dash" }),
};

const SIDES = [
  {
    tag: "A", name: "LangChain + Neo4j", sub: "langchain-neo4j · LLMGraphTransformer", accent: C.blue,
    scope: ["none", "none", "none", "own", "part", "own", "none"],
    scopeNote: "병합은 같은 이름만 · 임베딩 연결·유사 이름 병합은 직접 조립",
    code: [
      "t = LLMGraphTransformer(llm=llm, allowed_nodes=[...])",
      "docs = t.convert_to_graph_documents(chunks)",
      "graph.add_graph_documents(docs, include_source=True)",
    ],
    pros: ["코드 3줄로 첫 그래프 — 배우기·시연이 빠름", "LLM 교체 쉬움 — ChatOpenAI·ChatOllama 객체만 바꿈",
      "LangChain·LangGraph 흐름에 그대로 끼움"],
    cons: ["추출만 맡음 — 임베딩 연결(Neo4jVector)은 따로 조립", "유사 이름('A사'·'A사(주)') 병합은 직접 작성",
      "옛 예제의 langchain_experimental 경로는 종료"],
  },
  {
    tag: "B", name: "Native Neo4j", sub: "neo4j-graphrag · 추출기·저장기·병합기 부품", accent: C.navy,
    scope: ["own", "none", "own", "own", "own", "own", "part"],
    scopeNote: "정제·가명처리 없음 · 임베딩은 청크만(노드 설명은 직접)",
    code: [
      "ext = LLMEntityRelationExtractor(llm=llm)",
      "graph = await ext.run(chunks=TextChunks(chunks=my_chunks))",
      "await Neo4jWriter(driver).run(graph)   # 이어서 병합기 실행",
    ],
    pros: ["벡터DB와 같은 청크를 추출기에 바로 넣음(부품 조립)", "같은 이름 병합 기본, 유사 이름 병합기 선택",
      "문서 – 청크 – 엔티티 연결을 자동으로 만듦"],
    cons: ["개념(컴포넌트·파이프라인)이 많아 첫 장벽 높음", "Neo4j 전용 — 다른 그래프DB로 옮기기 어려움",
      "정제·가명처리 없음 — 원문 그대로면 실명이 LLM·그래프로"],
  },
];

// 머리 바: 왼쪽 A/B 배지 + 이름(굵게) + 패키지·클래스(옅게)
function sideHeader(s, x, side) {
  L.rr(s, { x, y: Y.head, w: COL_W, h: Y.headH, fill: side.accent, line: null, r: 0.06 });
  L.card(s, side.tag, { x: x + 0.12, y: Y.head + 0.11, w: 0.4, h: 0.4, fill: C.white, line: null,
    color: side.accent, size: 18, bold: true, r: 0.05 });
  s.addText([
    { text: side.name, options: { fontSize: fs(21), bold: true, color: C.white } },
    { text: "  " + side.sub, options: { fontSize: fs(14), color: "D9E3F5" } },
  ], { x: x + 0.62, y: Y.head, w: COL_W - 0.7, h: Y.headH, fontFace: FONT, valign: "middle", margin: 0.02,
    isTextBox: true });
}

function scopeRow(s, x, side) {
  L.text(s, "범위", { x, y: Y.scope, w: 0.55, h: Y.chipH, size: 15, bold: true, color: C.navy, margin: 0 });
  const n = STEPS.length, cx0 = x + 0.55, cg = 0.06, cw = (COL_W - 0.55 - cg * (n - 1)) / n;
  STEPS.forEach((t, i) => {
    const st = CHIP[side.scope[i]](side.accent);
    L.card(s, t, { x: cx0 + i * (cw + cg), y: Y.scope, w: cw, h: Y.chipH, ...st, size: 14, bold: true,
      r: Y.chipH / 2, lw: 1.25 });
  });
  L.text(s, side.scopeNote, { x: cx0, y: Y.scope + Y.chipH + 0.04, w: COL_W - 0.55, h: 0.36, size: 14,
    color: C.slate, margin: 0 });
}

function codeRow(s, x, side) {
  L.rr(s, { x, y: Y.code, w: COL_W, h: Y.codeH, fill: C.altRow, line: C.border, r: 0.06 });
  s.addText(side.code.join("\n"), { x: x + 0.15, y: Y.code + 0.05, w: COL_W - 0.3, h: Y.codeH - 0.1,
    fontFace: FONT, fontSize: fs(15), color: C.ink, valign: "middle", margin: 0.02, isTextBox: true,
    paraSpaceAfter: 0, lineSpacingMultiple: 1.05 });
}

// 장점(틴트) · 단점(흰 바탕) 위아래 상자 — 왼쪽 세로 배지 + 항목 3줄(한 줄씩 들어가게 전폭 사용)
function prosCons(s, x, side) {
  [["장점", side.pros, "+", C.tint, side.accent], ["단점", side.cons, "−", C.white, C.dark]].forEach(
    ([label, items, mark, fill, badge], k) => {
      const by = Y.pc + k * (Y.pcH + Y.pcGap);
      L.rr(s, { x, y: by, w: COL_W, h: Y.pcH, fill, line: C.border, r: 0.08 });
      L.darkBadge(s, label, { x: x + 0.1, y: by + 0.1, w: 0.72, h: Y.pcH - 0.2, size: 15, fill: badge });
      items.forEach((t, i) => {
        const iy = by + 0.06 + i * 0.295;
        L.text(s, mark, { x: x + 0.9, y: iy, w: 0.26, h: 0.29, size: 15, bold: true, color: badge, margin: 0,
          align: "center" });
        L.text(s, t, { x: x + 1.16, y: iy, w: COL_W - 1.24, h: 0.29, size: 15, color: C.ink, margin: 0 });
      });
    });
}

// 막대 비교 패널: 지표 이름 + A·B 막대(값에 비례) + 값
function barPanel(s, { x, w, title, a, b, fmt }) {
  const y = Y.band, h = Y.bandH;
  L.rr(s, { x, y, w, h, fill: C.white, line: C.border, r: 0.08 });
  L.text(s, title, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.36, size: 15, bold: true, color: C.navy, margin: 0 });
  const max = Math.max(a, b), bx = x + 0.55, bwMax = w - 0.55 - 1.1;
  [["A", a, C.blue], ["B", b, C.navy]].forEach(([tag, v, color], i) => {
    const ry = y + 0.56 + i * 0.4;
    L.text(s, tag, { x: x + 0.15, y: ry, w: 0.35, h: 0.32, size: 15, bold: true, color, margin: 0, align: "center" });
    L.box(s, { x: bx, y: ry + 0.04, w: Math.max(0.08, bwMax * v / max), h: 0.24, fill: color, line: null });
    L.text(s, fmt(v), { x: bx + bwMax * v / max + 0.08, y: ry, w: 1.1, h: 0.32, size: 15, bold: true,
      color: C.ink, margin: 0 });
  });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "엔티티·관계 추출 도구 선택: LangChain + Neo4j vs Native Neo4j",
    lead: "둘 다 정제·가명처리는 없음 → 앞단은 벡터DB와 함께 쓰고, 추출부터 Native 부품으로 잇는 구성이 실무에 맞음",
    notes: "A는 청크를 노드·관계로 바꾸는 ④ 한 단계 부품이고, B는 추출기·저장기·병합기 같은 부품을 이어 붙이는 "
      + "파이프라인임. B의 SimpleKGPipeline은 PDF 로드 → 분할 → 청크 임베딩 → 추출 → 가지치기 → 저장 → 병합으로 "
      + "구성되며 정제·가명처리 단계가 없음. 원문을 그대로 넣으면 실명이 LLM에 전달되고 그래프에 저장됨. "
      + "그래서 로드·정제·가명처리·청킹은 벡터DB 인덱싱과 같은 코드로 한 번만 하고, 그 청크를 TextChunks로 바꿔 "
      + "B의 추출기에 바로 넣음. 이렇게 하면 두 DB가 같은 청크를 씀. "
      + "둘 다 허용 노드·관계 목록과 (출발, 관계, 도착) 묶음으로 스키마를 제한할 수 있어 스키마 통제는 차이가 아님. "
      + "병합 차이: A도 저장할 때 MERGE로 이름이 완전히 같은 노드는 합침. 'A사'와 'A사(주)'처럼 조금 다른 이름은 "
      + "A는 직접 짜야 하고, B는 Fuzzy·spaCy 병합기를 붙이면 됨. 노드 설명 임베딩과 사전요약(커뮤니티 요약)은 "
      + "어느 쪽에도 없어 직접 만들어야 함. "
      + "사용도: 다운로드·개발 활동 모두 B가 큼. 단 Neo4j 공식 데모 도구(LLM Knowledge Graph Builder)는 A로 추출하고, "
      + "A를 깔면 B도 같이 깔려 B 다운로드에 A 몫이 일부 섞임. 학습용 예제는 A가 많음. 추출 품질 우열을 비교한 공개 "
      + "벤치마크는 없음. 수치는 2026-10-13 조회값(PyPI 최근 1개월 다운로드, GitHub 최근 90일 커밋).",
  });

  SIDES.forEach((side, i) => {
    const x = X0 + i * (COL_W + GAP);
    sideHeader(s, x, side);
    scopeRow(s, x, side);
    codeRow(s, x, side);
    prosCons(s, x, side);
  });
  // 가운데 세로 구분선 — 두 카드를 확실히 나눔
  L.box(s, { x: X0 + COL_W + GAP / 2 - 0.01, y: Y.head, w: 0.02, h: Y.pc + Y.pcH - Y.head, fill: C.border, line: null });

  // 아래 띠 — 실무 사용도
  L.rr(s, { x: X0, y: Y.band, w: 1.25, h: Y.bandH, fill: C.dark, line: null, r: 0.06 });
  s.addText([
    { text: "실무\n사용도", options: { fontSize: fs(18), bold: true, color: C.white, breakLine: true } },
    { text: "2026-10-13\n기준", options: { fontSize: fs(14), color: "D9E3F5" } },
  ], { x: X0, y: Y.band, w: 1.25, h: Y.bandH, fontFace: FONT, align: "center", valign: "middle", margin: 0.04,
    isTextBox: true, paraSpaceAfter: 6 });
  const bx0 = X0 + 1.4, pw = 2.7, pg = 0.15;
  barPanel(s, { x: bx0, w: pw, title: "월 다운로드(PyPI)", a: 143552, b: 296514,
    fmt: (v) => `약 ${(v / 10000).toFixed(1)}만` });
  barPanel(s, { x: bx0 + pw + pg, w: pw, title: "최근 90일 커밋", a: 15, b: 89, fmt: (v) => `${v}건` });

  // 판정 카드 — 권장 구성을 칩 흐름으로: 앞 3칸은 벡터DB 인덱싱과 공유, 뒤 3칸은 Native 부품
  const vx = bx0 + (pw + pg) * 2, vw = X0 + CW - vx;
  L.rr(s, { x: vx, y: Y.band, w: vw, h: Y.bandH, fill: C.tint, line: C.blue, lw: 1.5, r: 0.08 });
  L.text(s, "판정: 운영은 Native(B) — 앞단은 벡터DB 인덱싱과 함께", { x: vx + 0.15, y: Y.band + 0.08, w: vw - 0.3,
    h: 0.36, size: 17, bold: true, color: C.navy, margin: 0 });
  const flowSteps = [["로드", 0], ["가명처리", 0], ["청킹", 0], ["④ 추출", 1], ["KG 저장", 1], ["병합", 1]];
  const fa = 0.22, fcw = (vw - 0.3 - fa * 5) / 6, fy = Y.band + 0.48, fh = 0.38;
  flowSteps.forEach(([t, native], i) => {
    const cx = vx + 0.15 + i * (fcw + fa);
    L.card(s, t, { x: cx, y: fy, w: fcw, h: fh, size: 14, bold: true, r: fh / 2,
      fill: native ? C.navy : C.white, line: native ? null : C.slate, color: native ? C.white : C.slate });
    if (i < flowSteps.length - 1) {
      L.arrow(s, { x1: cx + fcw + 0.02, y1: fy + fh / 2, x2: cx + fcw + fa - 0.02, y2: fy + fh / 2,
        color: C.slate, width: 1.5 });
    }
  });
  const half = fcw * 3 + fa * 2;
  L.text(s, "벡터DB와 같은 코드 · 같은 청크", { x: vx + 0.15, y: fy + fh + 0.02, w: half, h: 0.28, size: 14,
    color: C.slate, align: "center", margin: 0 });
  L.text(s, "Native 부품으로 조립", { x: vx + 0.15 + half + fa, y: fy + fh + 0.02, w: half, h: 0.28, size: 14,
    color: C.navy, bold: true, align: "center", margin: 0 });
  L.text(s, "※ 노드 설명 임베딩·사전요약은 어느 쪽이든 직접 · 다운로드는 설치 횟수(B에 A 몫 포함)",
    { x: vx + 0.15, y: Y.band + Y.bandH - 0.31, w: vw - 0.3, h: 0.28, size: 14, color: C.slate, margin: 0 });
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  const out = process.argv[2] || path.join(__dirname, "Neo4j추출도구선택.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
