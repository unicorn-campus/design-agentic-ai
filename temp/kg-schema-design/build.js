// node build.js — 노드 타입 · 관계 먼저 정하기(그래프 스키마 도출) 3장 빌드 (script.md 슬라이드 1 ~ 3)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const LOOK = {
  plain: { fill: C.white, line: C.slate, color: C.ink },
  navy: { fill: C.navy, line: null, color: C.white },
  blue: { fill: C.blue, line: null, color: C.white },
  tint: { fill: C.tint, line: C.blue, color: C.navy },
  dash: { fill: C.white, line: C.sub, color: C.sub, dash: "dash" },
};

// 칩 흐름: 칩 사이 화살표
function chipFlow(s, items, { x, y, w, h, gap = 0.3, size = 15 }) {
  const cw = (w - gap * (items.length - 1)) / items.length;
  items.forEach((it, i) => {
    const cx = x + i * (cw + gap);
    L.card(s, it.t, { x: cx, y, w: cw, h, ...LOOK[it.style || "plain"], size, bold: true, r: 0.08,
      lw: it.style === "blue" ? 2 : 1.25 });
    if (i < items.length - 1) {
      L.arrow(s, { x1: cx + cw + 0.03, y1: y + h / 2, x2: cx + cw + gap - 0.03, y2: y + h / 2, color: C.slate, width: 1.75 });
    }
  });
}

function sectionLabel(s, t, { x, y, w, fill = C.navy }) {
  L.darkBadge(s, t, { x, y, w, h: 0.4, size: 16, fill });
}

function pill(s, t, { x, y, w, h = 0.36, style = "plain", size = 14 }) {
  L.card(s, t, { x, y, w, h, ...LOOK[style], size, bold: true, r: h / 2 });
}

// 작은 그래프 노드(라벨 이름)
function node(s, t, { x, y, w = 1.1, h = 0.42, style = "tint" }) {
  L.card(s, t, { x, y, w, h, ...LOOK[style], size: 14, bold: true, r: 0.12 });
}

// 두 노드 사이 화살표 + 위쪽 관계 이름
function edge(s, label, { x1, x2, y, color = C.navy }) {
  L.arrow(s, { x1: x1 + 0.03, y1: y, x2: x2 - 0.03, y2: y, color, width: 1.75 });
  L.text(s, label, { x: x1 - 0.1, y: y - 0.33, w: x2 - x1 + 0.2, h: 0.28, size: 14, bold: true, color: C.blue,
    align: "center", margin: 0 });
}

function band(s, t, { y = 7.1, h = 0.8, size = 16 }) {
  L.rr(s, { x: X0, y, w: CW, h, fill: C.tint, line: C.blue, lw: 1.5, r: 0.08 });
  L.box(s, { x: X0, y, w: 0.09, h, fill: C.blue, line: null });
  L.text(s, t, { x: X0 + 0.25, y, w: CW - 0.4, h, size, bold: true, color: C.navy, margin: 0 });
}

// ------------------------------------------------------------------ 슬라이드 1
async function createSlide01() {
  // 사용자 직접 수정(14:04 저장본) 반영: 제목 앞 '1. 스키마 도출:', 칩 '가지치기 (Pruning)'
  const s = L.newSlide({
    title: "1. 스키마 도출: 노드 타입과 관계는 추출 전에 먼저 정함",
    lead: "스키마는 추출 결과가 아니라 추출기에 주는 허용 목록 — 먼저 정하지 않으면 같은 개념이 여러 라벨로 쪼개짐",
    notes: "스키마 도출은 인덱싱 파이프라인의 단계가 아니라 설계 단계의 일임. 사람이 후보를 줄이고 이름을 정해 확정하므로 "
      + "매 실행 자동으로 돌리지 않음. 확정한 GraphSchema를 파일로 두고 버전을 관리하며, 인덱싱은 그 파일을 읽어 ④ 추출의 "
      + "프롬프트 안내와 가지치기에 씀. 스키마가 바뀌면 새 세대로 다시 인덱싱함. "
      + "인덱싱 줄의 KG 저장과 병합은 다른 단계임: Native는 저장기(Neo4jWriter)가 먼저 쓰고 병합기(resolver)가 DB 안에서 "
      + "같은 이름 노드를 합침(SimpleKGPipeline 연결 순서 writer → resolver). 임베딩은 합쳐진 노드 설명을 벡터로 바꾸는 단계라 "
      + "병합 다음에 둠. 청크 벡터는 기존 벡터DB 인덱싱의 벡터를 KG 저장 때 함께 넣어 다시 만들지 않음. "
      + "같은 카드가 어떤 청크에선 Brand, 어떤 청크에선 CardProduct로 뽑히면 병합 단계에서도 못 합침(라벨이 달라서). "
      + "실측: 로컬 gemma-4 12B로 스키마 없이 청크 2개를 추출했더니 라벨이 11종 나왔고, 카드는 Brand와 CardProduct, 요금은 "
      + "Fee와 AnnualFee로 갈렸음. Native neo4j-graphrag는 스키마를 안 주면 SimpleKGPipeline이 매번 입력 글에서 스키마를 "
      + "자동으로 뽑아 쓰므로(사람 검토 없음) 실행마다 달라질 수 있음 — 그래서 설계 단계에서 고정함.",
  });

  // 맨 위 두 줄: 설계 시(사전 1회) / 인덱싱 시(매 실행). 같은 8칸 격자를 써서 스키마 파일이 ④ 추출 · 가지치기 바로 위에 오게 함
  // 인덱싱 순서는 Native 연결 순서를 따름: writer(KG 저장) → resolver(병합) — 병합기는 저장된 __Entity__를 대상으로 함.
  // 임베딩(노드 설명)은 합쳐진 뒤의 설명을 써야 하므로 병합 다음. 청크 벡터는 기존 것을 KG 저장 때 함께 넣음
  const laneW = 1.95, gx0 = X0 + laneW + 0.12, gap = 0.22;
  const cw = (X0 + CW - gx0 - gap * 7) / 8;
  const gx = (i) => gx0 + i * (cw + gap);
  const yA = 1.86, yB = 2.66, h = 0.5;
  [[yA, "설계 시(사전 1회)", C.blue], [yB, "인덱싱 시(매 실행)", C.navy]].forEach(([y, t, fill]) => {
    L.card(s, t, { x: X0, y, w: laneW, h, fill, line: null, color: C.white, size: 14, bold: true, r: 0.06 });
  });
  const design = [["원천 분석", "plain"], ["후보 도출", "plain"], ["3단계 확정\n(사람)", "blue"]];
  design.forEach(([t, st], i) => {
    L.card(s, t, { x: gx(i), y: yA, w: cw, h, ...LOOK[st], size: 14, bold: true, r: 0.08 });
    L.arrow(s, { x1: gx(i) + cw + 0.03, y1: yA + h / 2, x2: gx(i + 1) - 0.03, y2: yA + h / 2, color: C.slate, width: 1.75 });
  });
  const fileW = cw * 2 + gap;
  L.card(s, "GraphSchema 파일\n(버전 관리)", { x: gx(3), y: yA, w: fileW, h, ...LOOK.tint, size: 14, bold: true, r: 0.08,
    lw: 2 });
  L.text(s, "인덱싱은 읽기만 함\n바뀌면 새 세대로 재인덱싱", { x: gx(5) + 0.1, y: yA - 0.04, w: X0 + CW - gx(5) - 0.1,
    h: h + 0.08, size: 14, bold: true, color: C.blue, margin: 0 });
  const run = [["로드", "plain"], ["정제와\n가명처리", "plain"], ["③ 청킹", "plain"], ["④ 추출", "navy"],
    ["가지치기\n(Pruning)", "navy"], ["KG 저장", "plain"], ["병합", "plain"], ["임베딩\n(노드 설명)", "plain"]];
  run.forEach(([t, st], i) => {
    L.card(s, t, { x: gx(i), y: yB, w: cw, h, ...LOOK[st], size: 14, bold: true, r: 0.08 });
    if (i < run.length - 1) {
      L.arrow(s, { x1: gx(i) + cw + 0.03, y1: yB + h / 2, x2: gx(i + 1) - 0.03, y2: yB + h / 2, color: C.slate,
        width: 1.75 });
    }
  });
  // 스키마 파일 → ④ 추출 · 가지치기: 읽어 씀(점선)
  [3, 4].forEach((i) => L.arrow(s, { x1: gx(i) + cw / 2, y1: yA + h + 0.02, x2: gx(i) + cw / 2, y2: yB - 0.02,
    color: C.blue, width: 1.75, dash: "dash" }));
  L.text(s, "읽어 씀", { x: gx(3) + cw / 2 + 0.08, y: yA + h + 0.01, w: 1.0, h: 0.28, size: 14, bold: true, color: C.blue,
    margin: 0 });

  // 왼쪽: 스키마 없이 추출하면(실측)
  const lw = 7.2, rx = X0 + lw + 0.25, rw = CW - lw - 0.25;
  const P = 3.3, B = 3.76;  // 구역 머리 · 상자 시작
  sectionLabel(s, "스키마 없이 추출하면 (실측)", { x: X0, y: P, w: lw, fill: C.dark });
  L.rr(s, { x: X0, y: B, w: lw, h: 3.36, fill: C.white, line: C.border, r: 0.08 });
  L.text(s, "로컬 gemma-4 12B로 청크 2개를 스키마 없이 추출 → 라벨 11종", { x: X0 + 0.2, y: B + 0.08, w: lw - 0.4, h: 0.34,
    size: 15, bold: true, color: C.navy, margin: 0 });
  const px = X0 + 0.2;
  [[["Brand", "CardProduct"], "= 카드 하나가 라벨 2개로"], [["Fee", "AnnualFee"], "= 요금도 라벨 2개로"]].forEach(
    ([pair, note], i) => {
      const y = B + 0.5 + i * 0.44;
      pill(s, pair[0], { x: px, y, w: 1.25, style: "blue" });
      pill(s, pair[1], { x: px + 1.35, y, w: 1.65, style: "blue" });
      L.text(s, note, { x: px + 3.15, y, w: 3.6, h: 0.36, size: 15, bold: true, color: C.blue, margin: 0 });
    });
  const rest = ["Channel", "Benefit", "Guardian", "Grade", "Date", "Store", "PerformanceCondition"];
  const widths = [1.25, 1.2, 1.25, 1.0, 0.9, 0.95, 2.45];
  let cx = px, cy = B + 1.4;
  rest.forEach((t, i) => {
    if (cx + widths[i] > X0 + lw - 0.2) { cx = px; cy += 0.42; }
    pill(s, t, { x: cx, y: cy, w: widths[i], style: "plain" });
    cx += widths[i] + 0.1;
  });
  L.hline(s, { x: px, y: B + 2.28, w: lw - 0.4, color: C.border });
  L.text(s, "GraphRAG 도구 기본 노드 타입/관계가 없거나 너무 일반적임", { x: px, y: B + 2.33, w: lw - 0.4, h: 0.32,
    size: 15, bold: true, color: C.navy, margin: 0 });
  L.text(s, "• Neo4j: 스키마를 안 주면 매번 입력 글에서 자동 추출(사람 검토 없음)\n"
    + "• MS GraphRAG 기본 타입: organization, person, geo, event\n"
    + "• LangChain+Neo4j: 허용 목록이 비면 아무 타입이나 만듦",
  { x: px, y: B + 2.64, w: lw - 0.4, h: 0.7, size: 14, color: C.ink, margin: 0, valign: "top" });

  // 오른쪽: 스키마를 주면(Native GraphSchema)
  sectionLabel(s, "스키마를 주면 (Native GraphSchema)", { x: rx, y: P, w: rw });
  L.codeBox(s, [
    "schema = GraphSchema.model_validate({",
    "    \"node_types\": [\"Card\", \"Benefit\", \"Fee\"],",
    "    \"relationship_types\": [\"HAS_BENEFIT\", \"HAS_FEE\"],",
    "    \"patterns\": [(\"Card\", \"HAS_BENEFIT\", \"Benefit\"),",
    "                 (\"Card\", \"HAS_FEE\", \"Fee\")]})",
    "graph = await extractor.run(chunks=chunks, schema=schema)",
    "result = await GraphPruning().run(graph, schema)",
  ], { x: rx, y: B, w: rw, h: 1.86, size: 14 });
  const cw2 = (rw - 0.2) / 2;
  [["① 추출 안내", "허용 목록이 추출 프롬프트에\n들어가 LLM이 그 안에서 고름"],
    ["② 가지치기", "목록 밖 노드와 관계를 지우고\n지운 개수를 통계로 남김"]].forEach(([t, b], i) => {
    const x = rx + i * (cw2 + 0.2);
    L.rr(s, { x, y: B + 1.98, w: cw2, h: 1.0, fill: C.tint, line: C.blue, r: 0.08 });
    L.text(s, t, { x: x + 0.15, y: B + 2.02, w: cw2 - 0.3, h: 0.34, size: 16, bold: true, color: C.navy, margin: 0 });
    L.text(s, b, { x: x + 0.15, y: B + 2.38, w: cw2 - 0.3, h: 0.56, size: 14, color: C.ink, margin: 0, valign: "top" });
  });
  L.text(s, "실행 확인: 노드 타입을 주면 목록 밖 타입은 기본 불허", { x: rx, y: B + 3.04, w: rw, h: 0.3, size: 14,
    color: C.slate, margin: 0 });

  // 사용자 직접 수정(14:39 저장본) 그대로: 두 줄 · 16pt
  band(s, "결론: 스키마는 인덱싱 전 설계 단계에서 확정해 파일로 고정, 인덱싱은 읽어 쓰기만 함.\n"
    + "정형 테이블은 변환 규칙으로, 문서는 표본 → 후보 → 사람 확정으로 스키마 설계",
  { y: 7.22, h: 0.68, size: 16 });
  return s;
}

// ------------------------------------------------------------------ 슬라이드 2(스키마 7가지)
async function createSlideSchema() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 스키마에 정의하는 7가지",
    lead: "노드 타입과 관계, 각각의 속성, 연결 패턴이 뼈대 — 제약과 허용 범위로 무엇을 지킬지 정함",
    notes: "①~⑤가 뼈대임: 노드 타입, 노드 속성, 관계, 관계 속성, 그리고 어느 노드에서 어느 노드로 그 관계가 갈 수 있는지를 정하는 "
      + "연결 패턴. ⑥ 제약은 고유키와 필수 속성이며 UNIQUENESS, EXISTENCE, KEY 세 종류가 있음. KEY는 필수이면서 고유함. "
      + "⑦ 허용 범위는 목록 밖의 타입, 패턴, 속성을 지울지 통과시킬지이며, 목록을 주면 기본은 지움. "
      + "실행 확인(neo4j-graphrag 1.22.0): 이 코드로 만든 스키마로 가지치기를 돌리니 name이 없는 Card 노드가 "
      + "MISSING_REQUIRED_PROPERTY로 지워졌음. 타입과 속성마다 description을 적으면 추출 프롬프트에 들어가 LLM이 고르는 기준이 됨. "
      + "속성의 type(STRING, INTEGER 등)은 적을 수 있지만 지금 버전의 가지치기는 값 형식을 검사하지 않으므로 금액과 날짜는 저장 전에 따로 변환함. "
      + "최대 홉 수, 결과 상한, 상충 관계 쌍은 검색과 검수에 쓰는 규칙이라 추출용 스키마에는 넣지 않음.",
  });

  // 왼쪽: 7가지 목록
  const lw = 7.3, rx = X0 + lw + 0.25, rw = CW - lw - 0.25;
  const rows = [
    ["노드 타입", "node_types[].label", "Card, Benefit"],
    ["노드 속성", "node_types[]\n.properties", "Card {name, annual_fee}"],
    ["관계", "relationship_types[]\n.label", "HAS_BENEFIT"],
    ["관계 속성", "relationship_types[]\n.properties", "HAS_BENEFIT {valid_until}"],
    ["연결 패턴", "patterns\n(출발, 관계, 도착)", "(Card, HAS_BENEFIT,\nBenefit)"],
    // 사용자 직접 수정(14:04 저장본) 반영: ⑥ 예 한 줄, ⑦ 칸 이름 셋을 풀어 씀(사용자는 12pt였으나 14pt 하한이라 세 줄로)
    ["제약", "constraints\nUNIQUENESS, EXISTENCE, KEY", "Card.name = KEY"],
    ["허용 범위", "additional_node_types,\nadditional_relationship_types,\nadditional_patterns",
      "①~⑤에 지정된 목록 밖을 허용할지 여부"],
  ];
  L.text(s, "뼈대 ① ~ ⑤", { x: X0, y: 1.86, w: 2.0, h: 0.3, size: 14, bold: true, color: C.navy, margin: 0 });
  L.text(s, "왼쪽부터 정의할 것, GraphSchema 칸, 카드 예", { x: X0 + 2.0, y: 1.86, w: lw - 2.0, h: 0.3, size: 14, color: C.slate,
    align: "right", margin: 0 });
  // 줄 7개 + '지킬 규칙' 머리 자리(0.3)가 아래 띠(7.1) 위에 들어가게 줄 높이를 잡음. ⑦은 칸 이름 셋이라 세 줄 높이
  const rh = 0.58, rg = 0.05, ruleGap = 0.3, lastH = 0.74;
  const rowY = (i) => 2.2 + i * (rh + rg) + (i >= 5 ? ruleGap : 0);
  rows.forEach(([name, field, ex], i) => {
    const y = rowY(i), hh = i === 6 ? lastH : rh;
    const rule = i >= 5;
    L.rr(s, { x: X0, y, w: lw, h: hh, fill: rule ? C.tint : C.white, line: rule ? C.blue : C.border, r: 0.06 });
    L.numBadge(s, ["①", "②", "③", "④", "⑤", "⑥", "⑦"][i], { x: X0 + 0.1, y: y + (hh - 0.38) / 2, size: 0.38, fsz: 16,
      fill: rule ? C.blue : C.navy });
    L.text(s, name, { x: X0 + 0.58, y, w: 1.25, h: hh, size: 16, bold: true, color: C.navy, margin: 0 });
    L.text(s, field, { x: X0 + 1.85, y, w: 3.05, h: hh, size: 14, color: C.slate, margin: 0 });
    L.text(s, ex, { x: X0 + 4.95, y, w: lw - 5.05, h: hh, size: 14, color: C.ink, bold: true, margin: 0 });
  });
  L.text(s, "지킬 규칙 ⑥ ⑦", { x: X0, y: rowY(5) - 0.3, w: 2.5, h: 0.28, size: 14, bold: true, color: C.blue,
    margin: 0 });

  // 오른쪽 위: 카드 예 그림(번호를 붙여 왼쪽 목록과 짝지음)
  const gy = 1.9, gh = 1.5;
  L.rr(s, { x: rx, y: gy, w: rw, h: gh, fill: C.white, line: C.border, r: 0.08 });
  const bw = 2.35, by = gy + 0.16, bh = gh - 0.32, b1 = rx + 0.2, b2 = rx + rw - 0.2 - bw;
  [[b1, "Card", ["name (키)", "annual_fee"]], [b2, "Benefit", ["name", "rate"]]].forEach(([x, label, props]) => {
    L.rr(s, { x, y: by, w: bw, h: bh, fill: C.tint, line: C.navy, lw: 1.5, r: 0.08 });
    L.card(s, `:${label}`, { x: x + 0.1, y: by + 0.08, w: bw - 0.2, h: 0.36, ...LOOK.navy, size: 15, bold: true, r: 0.05 });
    L.text(s, props.join("\n"), { x: x + 0.15, y: by + 0.48, w: bw - 0.3, h: bh - 0.54, size: 14, color: C.ink, margin: 0,
      valign: "top" });
  });
  const ay = by + bh / 2;
  L.arrow(s, { x1: b1 + bw + 0.04, y1: ay, x2: b2 - 0.04, y2: ay, color: C.navy, width: 2 });
  L.text(s, ":HAS_BENEFIT", { x: b1 + bw, y: ay - 0.38, w: b2 - b1 - bw, h: 0.32, size: 15, bold: true, color: C.blue,
    align: "center", margin: 0 });
  L.text(s, "{valid_until}", { x: b1 + bw, y: ay + 0.06, w: b2 - b1 - bw, h: 0.3, size: 14, color: C.ink,
    align: "center", margin: 0 });
  const tag = (t, x, y, fill = C.navy) => L.card(s, t, { x, y, w: 0.34, h: 0.34, fill, line: null, color: C.white,
    size: 14, bold: true, r: 0.17 });
  tag("①", b1 + bw - 0.3, by - 0.1);
  tag("②", b1 + bw - 0.45, by + 0.78);
  tag("⑥", b1 + 1.3, by + 0.47, C.blue);
  tag("③", (b1 + bw + b2) / 2 - 0.17, ay - 0.72);
  tag("④", (b1 + bw + b2) / 2 + 0.75, ay + 0.04);
  tag("⑤", (b1 + bw + b2) / 2 - 0.17, ay + 0.36);

  // 오른쪽 아래: 7칸을 채운 GraphSchema 코드
  L.codeBox(s, [
    "schema = GraphSchema.model_validate({",
    "  \"node_types\": [                              # ① ②",
    "    {\"label\": \"Card\", \"properties\": [",
    "        {\"name\": \"name\", \"type\": \"STRING\"},",
    "        {\"name\": \"annual_fee\", \"type\": \"INTEGER\"}]},",
    "    {\"label\": \"Benefit\", \"properties\": [...]}],",
    "  \"relationship_types\": [{\"label\": \"HAS_BENEFIT\",   # ③ ④",
    "      \"properties\": [{\"name\": \"valid_until\", \"type\": \"DATE\"}]}],",
    "  \"patterns\": [(\"Card\", \"HAS_BENEFIT\", \"Benefit\")],   # ⑤",
    "  \"constraints\": [{\"type\": \"KEY\", \"node_type\": \"Card\",  # ⑥",
    "                   \"property_names\": [\"name\"]}],",
    "  \"additional_node_types\": False})                # ⑦",
  ], { x: rx, y: 3.82, w: rw, h: 3.18, size: 14 });
  L.text(s, "7칸을 채운 Native GraphSchema — 실행 확인: name 없는 Card는 가지치기가 지움", { x: rx, y: 3.48, w: rw,
    h: 0.3, size: 14, bold: true, color: C.slate, margin: 0 });

  // 사용자 직접 수정(14:04 저장본) 그대로: 둘째 줄을 제약 3종 설명으로 바꿈
  band(s, "※ 최소한 = ①, ③, ⑤ + ⑥ 고유키. 속성은 질문에 쓰는 것만 정의하고, 타입마다 description을 적으면 LLM이 고르는 기준이 됨\n"
    + "※ 제약: 지정한 속성에 대해 UNIQUENESS는 고유 강제, EXISTENCE는 존재 강제, KEY는 고유 + 존재를 강제함. "
    + "UNIQUENESS는 지정한 속성이 비어 있어도 허용하나 KEY는 불허함",
  { size: 14 });
  return s;
}

// ------------------------------------------------------------------ 슬라이드 2
async function createSlide02() {
  // 사용자 직접 수정(14:39 저장본) 반영: 제목 앞 '1. 스키마 도출:', ③ 상자 '조인 테이블: 2개 + 업무 속성'
  // v5: 판정 결과 4개에 ①~④ 번호를 붙이고 예시를 같은 번호 순으로 놓음. 예시 ②는 사용자 첨부 표의 '사용자 역할 테이블'로 바꿈
  const s = L.newSlide({
    title: "1. 스키마 도출: 정형 테이블 → 노드 타입과 관계: 변환 규칙",
    lead: "모델 없이 규칙으로 바꿈 — 단, FK를 세기 전에 '그 표 자체가 조회 대상인가'부터 물음",
    notes: "Neo4j 공식 관계형 → 그래프 변환 규칙과 같음: 테이블은 라벨, 행은 노드, 열은 속성, FK는 관계로 바꾸고 FK 열은 지움, "
      + "조인 테이블은 관계로 바꾸고 그 열은 관계 속성. 관계는 양 끝이 둘뿐이라 셋 이상을 묶으면 중간 노드로 풂. "
      + "판정 결과는 4가지이고 오른쪽 예시가 같은 번호임. ① 조회 대상이면 노드 타입: 이체는 FK가 2개지만 이체 자체를 찾으므로 노드. "
      + "② FK가 2개이고 업무 열이 없으면 관계로 흡수: 사용자역할 테이블은 사용자와 역할을 잇기만 하므로 노드를 만들지 않음. "
      + "③ FK 2개 + 업무 속성이면 관계 속성: 주문상품의 수량과 단가는 '포함' 관계의 속성. 상품별 판매 집계처럼 그 속성을 "
      + "조회하거나 집계하면 노드로 둠. ④ FK 3개 이상이면 중간 노드: 수강신청은 학생, 과목, 학기를 함께 묶어 관계 하나로 못 담음. "
      + "조회 대상 질문을 먼저 하는 이유는 ① 이체 예: FK 개수만 보면 관계로 흡수되어 이체 자체를 찾을 수 없게 됨. "
      + "정형에서 나온 타입은 LLM 추출이 필요 없어 비용이 들지 않으므로 정형을 먼저 훑는 것이 이득임.",
  });

  // 규칙 번호표: 왼쪽 판정 결과와 오른쪽 예시를 같은 번호로 짝지음
  const ruleTag = (n, x, y, onDark = false) => L.card(s, n, { x, y, w: 0.36, h: 0.36,
    fill: onDark ? C.white : C.blue, line: null, color: onDark ? C.navy : C.white, size: 15, bold: true, r: 0.18 });

  // 왼쪽: 판정 흐름
  const lw = 6.6, lx = X0;
  L.card(s, "테이블 1개", { x: lx + lw / 2 - 1.1, y: 1.92, w: 2.2, h: 0.42, ...LOOK.navy, size: 15, bold: true, r: 0.08 });
  L.arrow(s, { x1: lx + lw / 2, y1: 2.36, x2: lx + lw / 2, y2: 2.56, color: C.slate, width: 1.75 });
  L.card(s, "Q1. 그 표 자체가 조회 대상인 엔티티인가?", { x: lx, y: 2.58, w: lw, h: 0.55, ...LOOK.tint, size: 16, bold: true,
    r: 0.08, lw: 1.5 });
  const leftW = 2.9, rX = lx + 3.2, rW = lw - 3.2;
  L.arrow(s, { x1: lx + leftW / 2, y1: 3.15, x2: lx + leftW / 2, y2: 3.5, color: C.navy, width: 1.75 });
  L.text(s, "예", { x: lx + leftW / 2 + 0.08, y: 3.16, w: 0.5, h: 0.3, size: 15, bold: true, color: C.navy, margin: 0 });
  L.arrow(s, { x1: rX + rW / 2, y1: 3.15, x2: rX + rW / 2, y2: 3.5, color: C.slate, width: 1.75 });
  L.text(s, "아니오", { x: rX + rW / 2 + 0.08, y: 3.16, w: 0.8, h: 0.3, size: 15, bold: true, color: C.slate, margin: 0 });

  L.rr(s, { x: lx, y: 3.52, w: leftW, h: 1.55, fill: C.navy, line: null, r: 0.08 });
  ruleTag("①", lx + 0.12, 3.62, true);
  s.addText([
    { text: "노드 타입", options: { fontSize: fs(18), bold: true, color: C.white, breakLine: true } },
    { text: "열 = 노드 속성\nFK = 관계\nFK 열은 바꾼 뒤 지움", options: { fontSize: fs(14), color: "D9E3F5" } },
  ], { x: lx + 0.6, y: 3.52, w: leftW - 0.7, h: 1.55, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true,
    paraSpaceAfter: 4 });
  L.text(s, "FK가 0개 또는 1개인\n보통 테이블은 대부분 여기로 옴", { x: lx, y: 5.15, w: leftW, h: 0.6, size: 14, color: C.slate,
    align: "center", margin: 0 });

  L.card(s, "Q2. FK 몇 개?", { x: rX, y: 3.52, w: rW, h: 0.46, ...LOOK.tint, size: 15, bold: true, r: 0.08 });
  const outs = [
    ["②", "조인 테이블: 2개이고 업무 열 없음", "관계 1개로 흡수", "plain"],  // 사용자 직접 수정(15:17 저장본)
    ["③", "조인 테이블: 2개 + 업무 속성", "관계 + 관계 속성\n(조회하거나 집계하면 노드)", "plain"],
    ["④", "3개 이상", "노드 타입(중간 노드)", "navy"],
  ];
  const outH = [0.58, 0.82, 0.58];
  let oy = 4.08;
  outs.forEach(([n, cond, result, style], i) => {
    const y = oy, h = outH[i];
    oy += h + 0.08;
    const dark = style === "navy";
    L.rr(s, { x: rX, y, w: rW, h, fill: dark ? C.navy : C.white, line: dark ? null : C.border, r: 0.06 });
    ruleTag(n, rX + 0.08, y + (h - 0.36) / 2, dark);
    s.addText([
      { text: cond, options: { fontSize: fs(14), bold: true, color: dark ? C.white : C.navy, breakLine: true } },
      { text: result, options: { fontSize: fs(14), color: dark ? "D9E3F5" : C.ink } },
    ], { x: rX + 0.52, y, w: rW - 0.58, h, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true,
      paraSpaceAfter: 0 });
  });
  // 순서가 중요한 이유
  L.rr(s, { x: lx, y: 6.34, w: lw, h: 0.64, fill: C.tint, line: C.blue, r: 0.08 });
  L.text(s, "왜 Q1이 먼저? FK 수만 보면 이체 기록(FK 2개)이 관계로 흡수돼 이체 자체를 찾을 수 없음 (예 ①)",
    { x: lx + 0.15, y: 6.34, w: lw - 0.3, h: 0.64, size: 14, bold: true, color: C.navy, margin: 0 });

  // 오른쪽: 예시 4개 — 왼쪽 판정 결과와 같은 번호 순
  const ex = X0 + lw + 0.3, ew = CW - lw - 0.3;
  const rows = [
    { n: "①", tbl: "이체(출금계좌FK, 입금계좌FK,\n금액, 일시)", nodes: ["계좌", "이체", "계좌"], rels: ["출금", "입금"],
      memo: "조회 대상 → 노드 타입(FK가 2개여도)" },
    { n: "②", tbl: "사용자, 역할,\n사용자역할(사용자FK, 역할FK)", nodes: ["사용자", "역할"], rels: ["맡음"],
      memo: "업무 열 없음 → 관계로 흡수(사용자역할 노드 없음)" },
    { n: "③", tbl: "주문상품(주문FK, 상품FK,\n수량, 단가)", nodes: ["주문", "상품"], rels: ["포함 {수량, 단가}"],
      memo: "업무 속성 → 관계 속성(판매 집계가 잦으면 노드)" },
    { n: "④", tbl: "수강신청(학생FK, 과목FK,\n학기FK)", nodes: ["학생", "수강신청", "과목"], rels: ["신청", "대상"],
      memo: "FK 3개 → 중간 노드(학기도 같은 방식), 홉 +1" },
  ];
  const rh = 1.18, rg = 0.08;
  rows.forEach((r, i) => {
    const y = 1.92 + i * (rh + rg);
    L.rr(s, { x: ex, y, w: ew, h: rh, fill: C.white, line: C.border, r: 0.08 });
    ruleTag(r.n, ex + 0.1, y + 0.1);
    L.rr(s, { x: ex + 0.55, y: y + 0.12, w: 2.55, h: rh - 0.24, fill: C.altRow, line: C.border, r: 0.06 });
    L.text(s, r.tbl, { x: ex + 0.6, y: y + 0.12, w: 2.45, h: rh - 0.24, size: 14, color: C.ink, margin: 0.04 });
    L.arrow(s, { x1: ex + 3.15, y1: y + rh / 2, x2: ex + 3.4, y2: y + rh / 2, color: C.slate, width: 1.75 });
    const gx = ex + 3.5, gw = ew - 3.6, ny = y + 0.36, nh = 0.42, cyy = ny + nh / 2;
    if (r.nodes.length === 2) {
      const nw = 1.0;
      node(s, `:${r.nodes[0]}`, { x: gx, y: ny, w: nw });
      node(s, `:${r.nodes[1]}`, { x: gx + gw - nw, y: ny, w: nw });
      edge(s, `:${r.rels[0]}`, { x1: gx + nw, x2: gx + gw - nw, y: cyy });
    } else {
      const nw = 1.05, step = (gw - nw) / 2;
      r.nodes.forEach((n, k) => node(s, `:${n}`, { x: gx + k * step, y: ny, w: nw, style: k === 1 ? "navy" : "tint" }));
      r.rels.forEach((rel, k) => edge(s, `:${rel}`, { x1: gx + k * step + nw, x2: gx + (k + 1) * step, y: cyy }));
    }
    L.text(s, r.memo, { x: gx - 0.05, y: y + 0.8, w: gw + 0.1, h: 0.32, size: 14, color: C.slate, margin: 0 });
  });

  // 사용자 직접 수정(15:17 저장본) 그대로: 조인 테이블 → '관계 또는 관계 + 속성'
  band(s, "Neo4j 공식 변환 규칙과 같음: 테이블 → 라벨 , FK → 관계 , 조인 테이블 → 관계 또는 관계 + 속성,  셋 이상 → 중간 노드\n"
    + "이름에 공백 없음(Neo4j 권고: 라벨은 PascalCase, 관계는 대문자_밑줄). 정형에서 나온 타입은 LLM 추출 비용이 들지 않음",
  { size: 14 });
  return s;
}

// ------------------------------------------------------------------ 슬라이드 3
async function createSlide03() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 소스 문서 → 노드 타입과 관계: 표본 → 후보 → 사람 확정",
    lead: "LLM은 표본에서 후보만 뽑고 확정은 사람이 함 — 확정한 목록을 GraphSchema로 고정해 추출기에 넘김",
    notes: "자동 추출 결과는 표본에 있는 것만 담는 후보임. 사람이 3단계로 줄이고 이름을 정한 뒤 GraphSchema로 고정해야 "
      + "매 실행 결과가 같아짐. Native는 SchemaFromTextExtractor로 표본 글에서 후보 스키마를 받을 수 있고, 확정본을 schema로 넘기지 "
      + "않으면 SimpleKGPipeline이 매번 자동 추출함. Neo4j LLM Knowledge Graph Builder는 'Get Schema From Text'로 스키마를 제안하고, "
      + "MS GraphRAG는 graphrag prompt-tune의 --discover-entity-types(기본 켜짐)로 표본 청크에서 엔티티 타입을 만들어 프롬프트 파일로 "
      + "저장함. LangChain과 LlamaIndex는 자동 후보 단계 없이 사람이 허용 목록을 먼저 적음. 3단계 확정은 온톨로지 공학의 용어 정리, "
      + "역량 질문(답해야 할 질문이 범위를 정함)과 같은 생각이며, 3단계(원천 없는 타입 제외)는 적재를 전제한 가이드 고유 규칙임. "
      + "확정 뒤 역량 질문으로 되짚는 검증은 가이드에 없는 보완점임.",
  });

  chipFlow(s, [{ t: "문서 종류별 표본 N건" }, { t: "스키마 추출기 → 후보", style: "tint" }, { t: "정형 후보와 합침" },
    { t: "3단계 확정 (사람)", style: "blue" }, { t: "GraphSchema 고정 → 추출기", style: "navy" }],
  { x: X0, y: 1.9, w: CW, h: 0.62, gap: 0.3, size: 14 });

  // 왼쪽: 후보 뽑는 도구
  const lw = 6.9, rx = X0 + lw + 0.25, rw = CW - lw - 0.25;
  sectionLabel(s, "후보 뽑는 도구", { x: X0, y: 2.72, w: lw, fill: C.dark });
  const tools = [
    ["Native\nneo4j-graphrag", "후보: SchemaFromTextExtractor().run(text=표본)\n확정: 고친 스키마를 schema로 넘김(안 넘기면 매번 자동)", "navy"],
    ["Neo4j LLM\nKG Builder", "후보: 'Get Schema From Text'가 스키마 제안\n확정: 화면에서 사람이 고름", "dark"],
    ["MS GraphRAG", "후보: graphrag prompt-tune --discover-entity-types\n확정: 저장된 프롬프트 파일을 사람이 고침", "dark"],
    ["LangChain과\nLlamaIndex", "후보: 자동 후보 단계 없음\n확정: 사람이 허용 목록을 먼저 적음", "dark"],
  ];
  tools.forEach(([name, body, tone], i) => {
    const y = 3.2 + i * 0.95, h = 0.88;
    L.rr(s, { x: X0, y, w: lw, h, fill: i === 0 ? C.tint : C.white, line: i === 0 ? C.blue : C.border, r: 0.08 });
    L.card(s, name, { x: X0 + 0.1, y: y + 0.1, w: 1.75, h: h - 0.2, fill: tone === "navy" ? C.navy : C.dark, line: null,
      color: C.white, size: 14, bold: true, r: 0.06 });
    L.text(s, body, { x: X0 + 2.0, y, w: lw - 2.1, h, size: 14, color: C.ink, margin: 0 });
  });

  // 오른쪽: 3단계 확정
  sectionLabel(s, "3단계 확정 — 사람이 줄이고 이름을 정함", { x: rx, y: 2.72, w: rw });
  const steps = [
    ["같은 의미는 합치고 이름을 정함", "온톨로지: 용어 나열과 계층 정리", "예: Brand와 CardProduct → Card, Fee와 AnnualFee → Fee"],
    ["쓰는 워크플로우 단계가 없는 관계는 뺌", "온톨로지: 역량 질문(답해야 할 질문이 범위를 정함)",
      "예: 어느 단계도 따라가지 않는 관계 → 다음 회차 후보로 1줄"],
    ["적재 원천이 없는 노드 타입은 뺌", "가이드 고유 규칙(빈 노드 방지)", "예: 어느 원천도 채우지 않는 타입 → 정의하지 않음"],
  ];
  steps.forEach(([title, onto, ex], i) => {
    const y = 3.2 + i * 1.27, h = 1.18;
    L.rr(s, { x: rx, y, w: rw, h, fill: C.white, line: C.border, r: 0.08 });
    L.numBadge(s, i + 1, { x: rx + 0.12, y: y + 0.12, size: 0.4, fsz: 17, fill: C.blue });
    L.text(s, title, { x: rx + 0.65, y: y + 0.08, w: rw - 0.75, h: 0.42, size: 16, bold: true, color: C.navy, margin: 0 });
    L.text(s, onto, { x: rx + 0.65, y: y + 0.5, w: rw - 0.75, h: 0.3, size: 14, color: C.slate, margin: 0 });
    L.text(s, ex, { x: rx + 0.65, y: y + 0.8, w: rw - 0.75, h: 0.32, size: 14, color: C.blue, bold: true, margin: 0 });
  });

  // 아래: 주의 4개
  const tips = [
    "표본에 없던 타입은 안 나옴\n→ 문서 종류마다 표본, 표본 수 기록",
    "도구 기본값(organization,\nperson, geo, event) 그대로 금지",
    "빼면 그래프에 아예 없음\n(가리는 것은 접근 필터의 일)",
    "확정 뒤 역량 질문으로 되짚기\n(가이드에 없는 보완점)",
  ];
  const tg = 0.15, tw = (CW - tg * 3) / 4;
  tips.forEach((t, i) => {
    const x = X0 + i * (tw + tg);
    L.rr(s, { x, y: 7.1, w: tw, h: 0.82, fill: C.altRow, line: C.border, r: 0.08 });
    L.numBadge(s, "!", { x: x + 0.1, y: 7.1 + 0.21, size: 0.4, fsz: 16, fill: C.dark });
    L.text(s, t, { x: x + 0.6, y: 7.1, w: tw - 0.68, h: 0.82, size: 14, color: C.ink, margin: 0 });
  });
  return s;
}

async function main() {
  L.createDeck();
  // ONLY=schema: 7가지 장표만 한 장짜리 덱으로 만듦(사용자가 직접 고친 덱을 덮어쓰지 않고 붙여 넣게 하려는 용도)
  if (process.env.ONLY === "schema") {
    await createSlideSchema();
  } else {
    await createSlide01();
    await createSlideSchema();
    await createSlide02();
    await createSlide03();
  }
  const out = process.argv[2] || path.join(__dirname, "그래프스키마도출.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
