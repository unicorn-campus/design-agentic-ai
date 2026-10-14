// node build.js — RDB에 연결해 스키마를 설계하는 도구 2종(Aura Import, apoc.model.jdbc) 한 장 빌드 (script.md 슬라이드 1)
// v2(사용자 결정): RDB 테이블을 직접 분석하는 두 도구만 남김. 가운뎃점(·)은 쓰지 않음(pptx 가이드 5절)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const LOOK = {
  plain: { fill: C.white, line: C.slate, color: C.ink },
  navy: { fill: C.navy, line: null, color: C.white },
  blue: { fill: C.blue, line: null, color: C.white },
  tint: { fill: C.tint, line: C.blue, color: C.navy },
  off: { fill: C.white, line: C.sub, color: C.sub, dash: "dash" },
};

const TOOLS = [
  {
    name: "Aura Import", kind: "Aura 콘솔의 가져오기 서비스", tags: [["LLM 있음", "tint"], ["로컬 CE 불가", "off"]],
    steps: [["데이터 원천\n연결", "plain"], ["모델 생성\n(자동 또는 AI)", "blue"], ["사람이\n검토, 수정", "tint"],
      ["매핑, 인덱스\n와 제약", "plain"], ["가져오기\n실행", "plain"]],
    rows: [
      ["분석 방법", "테이블의 PK와 FK로 관계를 추론해 모델 자동 생성\n키가 없으면 'Generate with AI'가 키를 추정해 모델 생성"],
      ["결과물", "후보 그래프 모델(노드, 관계) → 화면에서 고친 뒤 바로 적재"],
      ["연결 대상", "PostgreSQL, MySQL, SQL Server, Oracle, Snowflake 등 12종과 CSV"],
      ["로컬 Neo4j", "못 씀 — 적재 대상이 Aura 인스턴스(클라우드)"],
      ["주의", "AI가 만든 모델은 의도와 맞는지 반드시 검토(Neo4j 안내)"],
      ["상태", "운영 중. AI 모델 생성은 2025-03 공식 블로그 기준(현행 문서엔 언급 없음)"],
    ],
    links: [["Aura Import 문서", "https://neo4j.com/docs/aura/import/introduction/"],
      ["공식 블로그(모델 자동 생성)", "https://neo4j.com/blog/auradb/auradb-direct-import/"]],
  },
  {
    name: "apoc.model.jdbc", kind: "APOC Extended", tags: [["LLM 없음", "plain"], ["로컬 CE 가능", "blue"]],
    steps: [["JDBC로\nRDB 연결", "plain"], ["테이블, 열,\nFK 읽기", "blue"], ["nodes,\nrelationships", "plain"],
      ["변환 규칙\n①~④ 적용", "tint"], ["사람이\n확정", "tint"]],
    rows: [
      ["분석 방법", "JDBC 메타데이터로 테이블, 열, FK 구조를 읽어 그래프로 돌려줌\nfilters의 정규식으로 테이블, 뷰, 열을 뺄 수 있음"],
      ["결과물", "원본 구조(최종 모델 아님) → 규칙 적용과 이름 짓기는 직접\nwrite: true면 그 구조를 Neo4j에 저장"],
      ["연결 대상", "JDBC를 지원하는 RDB(드라이버를 plugins 폴더에 넣음)"],
      ["로컬 Neo4j", "됨 — APOC Extended를 따로 설치(기본 이미지에는 APOC Core만)"],
      ["상태", "유지 중(APOC 2026 문서, Apache-2.0). 결과 모양은 실행으로 확인 필요"],
    ],
    code: [
      "CALL apoc.model.jdbc('jdbc:postgresql://localhost:5432/app',",
      "  {schema: 'public', credentials: {user: $user, password: $pw},",
      "   filters: {tables: ['^tmp_.*']}}) YIELD nodes, relationships",
    ],
    links: [["APOC 문서(Database Modeling)", "https://neo4j.com/apoc/2026/database-integration/database-modeling/"],
      ["GitHub neo4j-apoc-procedures", "https://github.com/neo4j-contrib/neo4j-apoc-procedures"]],
  },
];

function toolCard(s, t, { x, y, w, h }) {
  L.rr(s, { x, y, w, h, fill: C.white, line: C.border, r: 0.08 });
  L.rr(s, { x, y, w, h: 0.5, fill: C.navy, line: null, r: 0.06 });
  s.addText([
    { text: t.name, options: { fontSize: fs(19), bold: true, color: C.white } },
    { text: "  " + t.kind, options: { fontSize: fs(14), color: "D9E3F5" } },
  ], { x: x + 0.15, y, w: w - 3.3, h: 0.5, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true });
  t.tags.forEach(([label, style], i) => {
    L.card(s, label, { x: x + w - 3.1 + i * 1.55, y: y + 0.09, w: 1.45, h: 0.32, ...LOOK[style], size: 14, bold: true,
      r: 0.16 });
  });

  // 단계 흐름
  const sy = y + 0.62, sh = 0.56, sg = 0.18, sw = (w - 0.3 - sg * 4) / 5;
  t.steps.forEach(([label, style], i) => {
    const sx = x + 0.15 + i * (sw + sg);
    L.card(s, label, { x: sx, y: sy, w: sw, h: sh, ...LOOK[style], size: 14, bold: true, r: 0.08 });
    if (i < t.steps.length - 1) {
      L.arrow(s, { x1: sx + sw + 0.02, y1: sy + sh / 2, x2: sx + sw + sg - 0.02, y2: sy + sh / 2, color: C.slate, width: 1.5 });
    }
  });

  // 항목 줄
  let ry = sy + sh + 0.16;
  const lx = x + 0.15, tx = x + 1.3, tw = w - 1.4;
  t.rows.forEach(([label, body]) => {
    const rh = body.includes("\n") ? 0.52 : 0.3;
    L.text(s, label, { x: lx, y: ry, w: 1.1, h: rh, size: 14, bold: true, color: C.navy, margin: 0, valign: "top" });
    L.text(s, body, { x: tx, y: ry, w: tw, h: rh, size: 14, color: C.ink, margin: 0, valign: "top" });
    ry += rh + 0.08;
  });
  if (t.code) {
    L.codeBox(s, t.code, { x: lx, y: ry, w: w - 0.3, h: 0.86, size: 14 });
    ry += 1.16;
  }
  // 출처(누르면 열리는 링크)
  const fy = y + h - 0.42;
  L.text(s, "출처", { x: lx, y: fy, w: 1.1, h: 0.3, size: 14, bold: true, color: C.navy, margin: 0, valign: "top" });
  const runs = [];
  t.links.forEach(([label, url], i) => {
    if (i > 0) runs.push({ text: ",  ", options: { color: C.slate } });
    runs.push({ text: label, options: { color: C.blue, underline: { style: "sng" }, hyperlink: { url, tooltip: url } } });
  });
  s.addText(runs, { x: tx, y: fy, w: tw, h: 0.3, fontFace: FONT, fontSize: fs(14), margin: 0, valign: "top", isTextBox: true });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "1. 스키마 도출: RDB에 연결해 스키마를 설계하는 도구 2종",
    lead: "RDB 테이블을 직접 분석하는 도구는 둘뿐 — Aura Import는 후보 모델까지, apoc.model.jdbc는 원본 구조까지 만들어 줌",
    notes: "Neo4j 도구 중 RDB에 직접 연결해 테이블 구조를 분석하는 것은 Aura Import와 apoc.model.jdbc 두 가지임(2026-10-14 기준, "
      + "같은 일을 하던 Neo4j ETL Tool은 2022-11 이후 멈춤). Data Importer는 CSV 머리글만 읽고, Arrows.app은 그림 도구, "
      + "Data Modeling MCP는 DB에 붙지 않음. Aura Import는 테이블의 PK와 FK로 관계를 추론해 후보 모델을 만들고, 키 정의가 없으면 "
      + "Generate with AI로 키를 추정함. AI 모델은 의도와 맞는지 검토하라고 Neo4j가 안내함. 다만 적재 대상이 Aura 클라우드라 "
      + "로컬 Community에서는 쓸 수 없음. apoc.model.jdbc는 JDBC 메타데이터로 테이블, 열, FK를 읽어 nodes와 relationships로 "
      + "돌려주는 원본 구조이며, 조회 대상 판정과 조인 테이블 흡수 같은 변환 규칙 ①~④는 직접 적용해야 함. APOC Extended라 "
      + "기본 Neo4j 이미지의 APOC Core에는 없고, JDBC 드라이버도 plugins 폴더에 넣어야 함. 결과 모양(라벨, 관계 이름)은 문서에 "
      + "그림으로만 있어 실제 실행으로 확인이 필요함.",
  });

  const gap = 0.25, cw = (CW - gap) / 2, ch = 5.1;
  TOOLS.forEach((t, i) => toolCard(s, t, { x: X0 + i * (cw + gap), y: 1.9, w: cw, h: ch }));

  // 아래 띠: 우리 환경(Neo4j CE 로컬)
  const by = 7.12, bh = 0.8;
  L.rr(s, { x: X0, y: by, w: CW, h: bh, fill: C.tint, line: C.blue, lw: 1.5, r: 0.08 });
  L.text(s, "우리 환경\n(CE 로컬)", { x: X0 + 0.15, y: by, w: 1.4, h: bh, size: 15, bold: true, color: C.navy, margin: 0 });
  const steps = [["Aura Import는\n쓸 수 없음", "off"], ["apoc.model.jdbc로\n구조 읽기", "navy"],
    ["변환 규칙 ①~④\n스크립트로 초안", "plain"], ["사람이 확정\n(조회 대상, 이름)", "blue"], ["GraphSchema\n파일로 고정", "navy"]];
  const fx = X0 + 1.6, fw = CW - 1.75, g = 0.26, w = (fw - g * 4) / 5;
  steps.forEach(([t, st], i) => {
    const x = fx + i * (w + g);
    L.card(s, t, { x, y: by + 0.12, w, h: bh - 0.24, ...LOOK[st], size: 14, bold: true, r: 0.08 });
    if (i > 0 && i < steps.length - 1) {
      L.arrow(s, { x1: x + w + 0.03, y1: by + bh / 2, x2: x + w + g - 0.03, y2: by + bh / 2, color: C.slate, width: 1.75 });
    }
  });
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  const out = process.argv[2] || path.join(__dirname, "스키마도출도구.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
