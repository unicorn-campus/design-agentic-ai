// node build.js — 노드 타입과 관계 먼저 정하기(그래프 스키마 도출) 7장 빌드 (script.md 슬라이드 1 ~ 7)
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

// ------------------------------------------------------------------ 슬라이드 4(v8 추가: 프롬프트로 도출)
async function createSlidePrompt() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 프롬프트로 정형 테이블의 스키마 도출",
    lead: "변환 규칙을 프롬프트에 담아 바이브 코딩 도구에 맡김 — AI는 읽고 판정하고 그리며, 사람은 세 번 답하고 승인함",
    notes: "앞 장의 변환 규칙은 대부분 기계적으로 적용할 수 있어서, 규칙을 프롬프트에 적어 바이브 코딩 도구에 맡김. "
      + "규칙 ②③④와 검증, 그림, 저장은 AI가 하고, 업무 판단이 필요한 규칙 ①과 이름, 최종 승인은 사람이 함. "
      + "DB 카탈로그는 DB가 원래 갖고 있는 구조 설명 테이블이라 따로 만들 필요가 없음(PostgreSQL은 pg_catalog). "
      + "FK 개수는 열이 아니라 제약 수로 셈: card의 product_id와 brand는 열 2개지만 FK 제약 1개임. "
      + "라벨은 Neo4j 이름 규칙에 따라 영문(Card, HAS_CARD)으로 두고, 한글 이름은 description에 넣어 그림과 LLM 안내에 씀. "
      + "한글 라벨도 동작은 하지만(실행 확인), 영문 속성 이름과 섞이지 않게 하려고 영문으로 정함. "
      + "8단계에서 수정을 요청하면 5단계부터 다시 하며, 5회가 넘으면 남은 쟁점을 정리해 멈춤. "
      + "최종 파일은 GraphSchema.save()로 저장한 뒤 from_file()로 다시 읽어 개수가 같은지 확인하고, 승인 기록을 함께 남김.",
  });

  // 맨 위: 사람 줄과 AI 줄에 9단계 카드를 같은 격자로 놓음(사람 단계 1, 4, 8)
  const laneW = 1.7, gx0 = X0 + laneW + 0.15, gap = 0.2, n = 9;
  const cw = (X0 + CW - gx0 - gap * (n - 1)) / n;
  const gx = (i) => gx0 + i * (cw + gap);
  const yH = 1.92, yA = 2.92, h = 0.7;
  [[yH, "사람", C.blue], [yA, "AI\n(바이브 코딩 도구)", C.navy]].forEach(([y, t, fill]) => {
    L.rr(s, { x: gx0 - 0.08, y: y - 0.06, w: X0 + CW - gx0 + 0.08, h: h + 0.12, fill: C.altRow, line: null, r: 0.06 });
    L.card(s, t, { x: X0, y: y - 0.06, w: laneW, h: h + 0.12, fill, line: null, color: C.white, size: 14, bold: true, r: 0.06 });
  });
  const steps = [
    ["1. 입력 받기", "H"], ["2. DB\n카탈로그 읽기", "A"], ["3. 규칙 판정\n(②③④)", "A"], ["4. 규칙 ①과\n이름 답", "H"],
    ["5. 스키마\n초안", "A"], ["6. 기계 검증", "A"], ["7. Mermaid\n그림", "A"], ["8. 검증과\n승인", "H"],
    ["9. 저장과\n다시 읽기", "A"],
  ];
  const yOf = (lane) => (lane === "H" ? yH : yA);
  steps.forEach(([t, lane], i) => {
    const human = lane === "H";
    L.card(s, t, { x: gx(i), y: yOf(lane), w: cw, h, fill: human ? C.blue : C.white, line: human ? null : C.slate,
      color: human ? C.white : C.ink, size: 14, bold: true, r: 0.08, lw: 1.25 });
    if (i === n - 1) return;
    const next = steps[i + 1][1];
    const x1 = gx(i) + cw + 0.03, x2 = gx(i + 1) - 0.03;
    if (next === lane) {
      L.arrow(s, { x1, y1: yOf(lane) + h / 2, x2, y2: yOf(lane) + h / 2, color: C.slate, width: 1.75 });
    } else {
      // 줄이 바뀌면 카드 모서리끼리 비스듬히 이음
      const down = lane === "H";
      L.arrow(s, { x1, y1: down ? yH + h - 0.05 : yA + 0.05, x2, y2: down ? yA + 0.05 : yH + h - 0.05, color: C.slate,
        width: 1.75 });
    }
  });
  // 8 → 5 되돌림(점선): 8 아래로 내려가 AI 줄 밑을 지나 5로 올라감(AI 줄의 7열 칸은 비어 있음)
  const x8 = gx(7) + cw / 2, x5 = gx(4) + cw / 2, yLoop = yA + h + 0.2;
  L.arrow(s, { x1: x8, y1: yH + h + 0.02, x2: x8, y2: yLoop, color: C.blue, width: 1.5, dash: "dash", head: "none" });
  L.hline(s, { x: x5, y: yLoop, w: x8 - x5, color: C.blue, width: 1.5, dash: "dash" });
  L.arrow(s, { x1: x5, y1: yLoop, x2: x5, y2: yA + h + 0.02, color: C.blue, width: 1.5, dash: "dash" });
  L.text(s, "수정 요청 시 5단계부터 다시(최대 5회)", { x: x5 + 0.1, y: yLoop + 0.02, w: x8 - x5 - 0.2, h: 0.3, size: 14,
    bold: true, color: C.blue, align: "center", margin: 0 });

  // 아래 3칸
  // 왼쪽 상자 3개(0.64 + 0.88 + 0.64 + 간격)가 아래 띠(7.12) 위에서 끝나게 맞춘 높이
  const top = 4.22, bodyY = top + 0.48, bodyB = 7.0;
  const wA = 4.75, wB = 5.0, g3 = 0.25, wC = CW - wA - wB - g3 * 2;
  const xA = X0, xB = xA + wA + g3, xC = xB + wB + g3;

  // A: 사람이 답하는 곳 3번
  sectionLabel(s, "사람이 답하는 곳 3번", { x: xA, y: top, w: wA, fill: C.blue });
  const asks = [
    ["1", "출력 폴더와 DB 접속 정보\n비밀번호는 .env에 직접 등록", 0.64],
    ["4", "규칙 ① 후보(FK 2개 + 업무 열)를 노드 타입\n또는 관계 + 관계 속성으로 정함\n뺄 테이블, 이름 후보 승인", 0.88],
    ["8", "Mermaid 그림과 판정표를 보고 승인\n(승인자와 일시를 기록)", 0.64],
  ];
  let ay = bodyY;
  asks.forEach(([num, t, hh]) => {
    L.rr(s, { x: xA, y: ay, w: wA, h: hh, fill: C.tint, line: C.blue, r: 0.06 });
    L.numBadge(s, num, { x: xA + 0.1, y: ay + (hh - 0.38) / 2, size: 0.38, fsz: 16, fill: C.blue });
    L.text(s, t, { x: xA + 0.6, y: ay, w: wA - 0.7, h: hh, size: 14, color: C.navy, bold: true, margin: 0 });
    ay += hh + 0.07;
  });

  // B: AI가 지키는 규칙
  sectionLabel(s, "AI가 지키는 규칙", { x: xB, y: top, w: wB });
  L.rr(s, { x: xB, y: bodyY, w: wB, h: bodyB - bodyY, fill: C.white, line: C.border, r: 0.08 });
  // 줄 사이를 띄워 상자 높이를 고르게 채움
  s.addText("• FK 개수는 열 수가 아니라 제약 수로 셈\n"
    + "• DB는 읽기 전용, 비밀번호는 .env에만 둠\n"
    + "• 라벨은 영문, 한글 이름은 description에 넣음\n"
    + "• 그림은 Mermaid만 씀\n"
    + "• 규칙 ① 판정과 이름은 추측해 확정하지 않음\n"
    + "• 후보 표시가 남으면 스키마 파일을 만들지 않음",
  { x: xB + 0.2, y: bodyY + 0.06, w: wB - 0.3, h: bodyB - bodyY - 0.12, fontFace: FONT, fontSize: fs(14), color: C.ink,
    valign: "middle", margin: 0, isTextBox: true, paraSpaceAfter: 7 });

  // C: 승인 화면 예(Mermaid 그림을 도형으로 옮김)
  sectionLabel(s, "승인 화면 예 (Mermaid 그림)", { x: xC, y: top, w: wC, fill: C.dark });
  L.rr(s, { x: xC, y: bodyY, w: wC, h: bodyB - bodyY, fill: C.white, line: C.border, r: 0.08 });
  const nbW = 1.55, nbH = 1.45, nbY = bodyY + 0.2, nb1 = xC + 0.15, nb2 = xC + wC - 0.15 - nbW;
  [[nb1, "Member", "회원", "member_id (키)\nage_band"], [nb2, "Card", "카드", "card_id (키)\nstatus"]].forEach(
    ([x, label, ko, props]) => {
      L.rr(s, { x, y: nbY, w: nbW, h: nbH, fill: C.tint, line: C.navy, lw: 1.5, r: 0.08 });
      L.card(s, `:${label}`, { x: x + 0.08, y: nbY + 0.08, w: nbW - 0.16, h: 0.36, ...LOOK.navy, size: 14, bold: true,
        r: 0.05 });
      L.text(s, `(${ko})\n${props}`, { x: x + 0.08, y: nbY + 0.48, w: nbW - 0.16, h: nbH - 0.54, size: 14, color: C.ink,
        align: "center", margin: 0, valign: "top" });
    });
  const my = nbY + nbH / 2;
  L.arrow(s, { x1: nb1 + nbW + 0.04, y1: my, x2: nb2 - 0.04, y2: my, color: C.navy, width: 2 });
  L.text(s, "HAS_CARD", { x: nb1 + nbW, y: my - 0.36, w: nb2 - nb1 - nbW, h: 0.3, size: 14, bold: true, color: C.blue,
    align: "center", margin: 0 });
  L.text(s, "(보유함)", { x: nb1 + nbW, y: my + 0.06, w: nb2 - nb1 - nbW, h: 0.3, size: 14, color: C.ink, align: "center",
    margin: 0 });
  L.text(s, "영문 라벨 아래에 한글 이름을 함께 적어\n검토하는 사람이 바로 읽게 함", { x: xC + 0.15, y: nbY + nbH + 0.1,
    w: wC - 0.3, h: bodyB - nbY - nbH - 0.16, size: 14, color: C.slate, align: "center", margin: 0 });

  band(s, "결과: graph_schema.json(승인본)과 approval.json(승인자, 승인 일시, 입력 파일 SHA-256). 인덱싱은 이 파일을 읽기만 함\n"
    + "GraphSchema 검증, 저장, 다시 읽기는 Neo4j 서버 없이 됨(실행 확인)",
  { y: 7.12, h: 0.76, size: 15 });
  // 사용자 직접 수정(10-14 18:07 저장본) 그대로: 띠 아래 ※ 안내 한 줄(테마 색 대신 팔레트 ink)
  L.text(s, "※ DB 카탈로그를 읽을 스키마는 원본 테이블이 있는 스키마로 지정하고, 서비스용 뷰(View)가 정의된 스키마(예: app)는 쓰지 않음",
    { x: 0.515, y: 8.029, w: 14.792, h: 0.37, size: 16, color: C.ink, margin: 0 });
  return s;
}

// ------------------------------------------------------------------ 슬라이드 12(v11 추가: 소스 문서 프롬프트 수행)
async function createSlideDocPrompt() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 프롬프트로 소스 문서의 스키마 도출",
    lead: "앞의 다섯 단계를 프롬프트에 담아 바이브 코딩 도구에 맡김 — AI는 초안을 내고 시험하며, 사람은 여섯 번 확정함",
    notes: "정형 테이블은 규칙만으로 대부분 판정할 수 있어 사람이 세 번 답했지만, 문서는 테이블 구조가 없어 LLM이 후보와 초안을 내고 "
      + "사람이 역량 질문 기준으로 확정해야 함. 그래서 승인 단계가 1, 2, 3, 5, 7, 8 여섯 곳임. "
      + "1단계에서 AI는 청크 위치 파일(예: 인덱서의 활성 세대 기록)을 받아 실제 청크 파일을 찾고, 본문 칸과 문서 종류를 제안하고, "
      + "개인정보 꼴이 남았는지 셈. 3단계에서 청크 하나에 조항이 여러 개 들었으면 표본으로 뽑힌 청크만 제목 줄로 나눔. 원본이 많아도 "
      + "다시 청킹하지 않으며, 인덱싱도 추출 직전에 같은 규칙으로 나눔. 4단계는 역량 질문만 examples로 넘겨 후보를 넓게 뽑고, "
      + "5단계에서 AI가 병합, 제거, 추가를 질문 번호와 함께 추천하면 사람이 제약까지 확정함. 7단계 기대 답은 정답표가 있으면 그것을 씀. "
      + "8단계는 후보에 쓰지 않은 표본으로 시험해 질문마다 지표를 보고, 미달이면 설명(description)을 고쳐 5단계부터 다시 함. "
      + "자동 승인으로 돌려 본 실행에서 혜택과 상담은 통과해 파일을 만들었고, 약관은 조항 단위로 바꾼 뒤에도 기대 답 검토가 먼저 필요해 멈춤.",
  });

  // 맨 위: AI 줄에 9단계, 사람 줄에는 승인 단계 위에만 카드(4쪽과 같은 격자)
  const laneW = 1.7, gx0 = X0 + laneW + 0.15, gap = 0.2, n = 9;
  const cw = (X0 + CW - gx0 - gap * (n - 1)) / n;
  const gx = (i) => gx0 + i * (cw + gap);
  const yH = 1.92, yA = 2.92, h = 0.7;
  [[yH, "사람", C.blue], [yA, "AI\n(바이브 코딩 도구)", C.navy]].forEach(([y, t, fill]) => {
    L.rr(s, { x: gx0 - 0.08, y: y - 0.06, w: X0 + CW - gx0 + 0.08, h: h + 0.12, fill: C.altRow, line: null, r: 0.06 });
    L.card(s, t, { x: X0, y: y - 0.06, w: laneW, h: h + 0.12, fill, line: null, color: C.white, size: 14, bold: true, r: 0.06 });
  });
  const steps = ["1. 입력 받기", "2. 역량 질문\n초안", "3. 추출 단위,\n표본 계획", "4. 후보\n넓게 뽑기", "5. 스키마\n초안 추천",
    "6. 기계 검증", "7. 기대 답\n초안", "8. 채우기\n시험", "9. 저장과\n다시 읽기"];
  const approve = { 0: "입력값\n확인", 1: "질문\n확정", 2: "단위, 표본\n승인", 4: "초안, 제약\n확정", 6: "기대 답,\n기준 확정",
    7: "통과\n판정" };
  steps.forEach((t, i) => {
    L.card(s, t, { x: gx(i), y: yA, w: cw, h, fill: C.white, line: C.slate, color: C.ink, size: 14, bold: true, r: 0.08,
      lw: 1.25 });
    if (approve[i]) {
      L.card(s, approve[i], { x: gx(i), y: yH, w: cw, h, fill: C.blue, line: null, color: C.white, size: 14, bold: true,
        r: 0.08 });
      // AI가 낸 초안을 사람이 받아 확정함(아래에서 위로)
      L.arrow(s, { x1: gx(i) + cw / 2, y1: yA - 0.02, x2: gx(i) + cw / 2, y2: yH + h + 0.02, color: C.blue, width: 1.5 });
    }
    if (i < n - 1) {
      L.arrow(s, { x1: gx(i) + cw + 0.03, y1: yA + h / 2, x2: gx(i + 1) - 0.03, y2: yA + h / 2, color: C.slate, width: 1.75 });
    }
  });
  // 8 → 5 되돌림(점선): AI 줄 밑으로 지나감
  const x8 = gx(7) + cw / 2, x5 = gx(4) + cw / 2, yLoop = yA + h + 0.2;
  L.arrow(s, { x1: x8, y1: yA + h + 0.02, x2: x8, y2: yLoop, color: C.blue, width: 1.5, dash: "dash", head: "none" });
  L.hline(s, { x: x5, y: yLoop, w: x8 - x5, color: C.blue, width: 1.5, dash: "dash" });
  L.arrow(s, { x1: x5, y1: yLoop, x2: x5, y2: yA + h + 0.02, color: C.blue, width: 1.5, dash: "dash" });
  L.text(s, "설명 고치기 시 5단계부터 다시(최대 5회)", { x: x5 + 0.1, y: yLoop + 0.02, w: x8 - x5 - 0.2, h: 0.3, size: 14,
    bold: true, color: C.blue, align: "center", margin: 0 });

  // 아래 3칸(4쪽과 같은 폭)
  const top = 4.22, bodyY = top + 0.48, bodyB = 7.0;
  const wA = 4.75, wB = 5.0, g3 = 0.25, wC = CW - wA - wB - g3 * 2;
  const xA = X0, xB = xA + wA + g3, xC = xB + wB + g3;

  // A: 사람이 확정하는 곳 6번(단계 번호 배지 + 한 줄)
  sectionLabel(s, "사람이 확정하는 곳 6번", { x: xA, y: top, w: wA, fill: C.blue });
  const asks = [
    ["1", "입력값 확인(AI가 추천값 제시)"], ["2", "역량 질문 확정(사용자 질문에서 초안)"], ["3", "추출 단위, 묶음, 표본 수 승인"],
    ["5", "스키마 초안과 제약 확정"], ["7", "기대 답과 합격 기준 확정"], ["8", "통과 판정, 미달이면 설명 고치기"],
  ];
  const ah = 0.33, ag = (bodyB - bodyY - ah * asks.length) / (asks.length - 1);
  asks.forEach(([num, t], i) => {
    const y = bodyY + i * (ah + ag);
    L.rr(s, { x: xA, y, w: wA, h: ah, fill: C.tint, line: C.blue, r: 0.05 });
    L.numBadge(s, num, { x: xA + 0.06, y: y + 0.025, size: 0.28, fsz: 14, fill: C.blue });
    L.text(s, t, { x: xA + 0.45, y, w: wA - 0.5, h: ah, size: 14, color: C.navy, bold: true, margin: 0 });
  });

  // B: AI가 지키는 규칙
  sectionLabel(s, "AI가 지키는 규칙", { x: xB, y: top, w: wB });
  L.rr(s, { x: xB, y: bodyY, w: wB, h: bodyB - bodyY, fill: C.white, line: C.border, r: 0.08 });
  s.addText("• 후보 뽑기에는 역량 질문만 넘김(이름 재사용 안내 없음)\n"
    + "• 판단은 빈도가 아니라 역량 질문 기준\n"
    + "• 시험은 후보에 안 쓴 표본, 답 없는 문서 포함\n"
    + "• 조항 여러 개 든 청크는 표본만 나눔\n"
    + "• 키는 .env에서 읽기만 함, AI가 쓰지 않음\n"
    + "• 쓰는 Neo4j 판이 지원하는 제약만 씀",
  { x: xB + 0.2, y: bodyY + 0.06, w: wB - 0.3, h: bodyB - bodyY - 0.12, fontFace: FONT, fontSize: fs(14), color: C.ink,
    valign: "middle", margin: 0, isTextBox: true, paraSpaceAfter: 7 });

  // C: 승인 화면 예(실행 결과의 상담 초안 일부를 도형으로 옮김)
  sectionLabel(s, "승인 화면 예 (Mermaid 그림)", { x: xC, y: top, w: wC, fill: C.dark });
  L.rr(s, { x: xC, y: bodyY, w: wC, h: bodyB - bodyY, fill: C.white, line: C.border, r: 0.08 });
  // 관계 이름(HAS_PROPOSAL)이 상자에 붙지 않게 상자 폭을 4쪽보다 조금 줄이고 속성은 줄마다 하나씩 씀
  const nbW = 1.55, nbH = 1.62, nbY = bodyY + 0.16, nb1 = xC + 0.12, nb2 = xC + wC - 0.12 - nbW;
  [[nb1, "Consultation", "상담", "record_id (키)\nconsult_date"], [nb2, "Proposal", "상담 제안", "content\ndecision\nreason"]]
    .forEach(([x, label, ko, props]) => {
      L.rr(s, { x, y: nbY, w: nbW, h: nbH, fill: C.tint, line: C.navy, lw: 1.5, r: 0.08 });
      L.card(s, `:${label}`, { x: x + 0.06, y: nbY + 0.08, w: nbW - 0.12, h: 0.36, ...LOOK.navy, size: 14, bold: true,
        r: 0.05 });
      L.text(s, `(${ko})\n${props}`, { x: x + 0.06, y: nbY + 0.48, w: nbW - 0.12, h: nbH - 0.54, size: 14, color: C.ink,
        align: "center", margin: 0, valign: "top" });
    });
  const my = nbY + nbH / 2;
  L.arrow(s, { x1: nb1 + nbW + 0.04, y1: my, x2: nb2 - 0.04, y2: my, color: C.navy, width: 2 });
  L.text(s, "HAS_\nPROPOSAL", { x: nb1 + nbW, y: my - 0.62, w: nb2 - nb1 - nbW, h: 0.56, size: 14, bold: true, color: C.blue,
    align: "center", margin: 0, valign: "bottom" });
  L.text(s, "(제안함)", { x: nb1 + nbW, y: my + 0.06, w: nb2 - nb1 - nbW, h: 0.3, size: 14, color: C.ink, align: "center",
    margin: 0 });
  L.text(s, "추천표와 함께 보고 고치거나 승인함", { x: xC + 0.15, y: nbY + nbH + 0.1,
    w: wC - 0.3, h: bodyB - nbY - nbH - 0.16, size: 14, color: C.slate, align: "center", margin: 0 });

  band(s, "결과: 문서 종류마다 graph_schema.json과 approval.json(승인자, 일시, 입력 SHA-256, 마지막 시험 지표, 추출 단위)\n"
    + "시험 보고서 fill_report.md는 질문마다 뽑음, 잘못 뽑음, 값 같음과 합격 판정을 보여 줌. 인덱싱은 승인 파일을 읽기만 함",
  { y: 7.12, h: 0.76, size: 15 });
  L.text(s, "※ 기대 답을 LLM이 쓰면 시험하는 모델과 같아 점수가 후해질 수 있음 → 7단계에서 사람이 반드시 검토함",
    { x: 0.515, y: 8.029, w: 14.792, h: 0.37, size: 16, color: C.ink, margin: 0 });
  return s;
}

// ------------------------------------------------------------------ 별도 장표(검색 저장소 구성 4가지 안 비교)
async function createSlideStoreCompare() {
  const s = L.newSlide({
    title: "그래프DB 구축: 검색 저장소 구성 4가지 안 비교",
    lead: "벡터, 키워드, 그래프를 어디에 두느냐로 갈림 — 한국어 키워드 품질과 운영 부담이 선택을 가름",
    notes: "검색에 쓰는 것은 벡터 색인(의미 검색), 키워드 색인(BM25), 지식 그래프 세 가지이고, 네 안은 이 셋을 어느 저장소에 두느냐로 나뉨. "
      + "일반적인 비교이며, 우리 프로젝트의 지금 구성(Chroma, Kiwi와 bm25s로 만든 BM25 파일, Neo4j)은 1-a의 한 예임. "
      + "한국어 실무에서는 1-b처럼 한국어 형태소 분석기가 있는 검색 엔진(Elasticsearch 또는 OpenSearch의 공식 nori 플러그인, 사용자 사전 지원)에 "
      + "벡터와 키워드를 함께 두고 그래프 DB를 따로 두는 구성이 흔함. Neo4j 전문 검색에는 한국어 분석기가 없어, 3번은 형태소 분석기로 미리 "
      + "나눈 낱말을 넣거나 Java 분석기 플러그인을 직접 만들어야 함. 미리 나눠 넣은 우리 실측에서 키워드 상위 10 겹침이 0.952였고, "
      + "Neo4j는 BM25의 k1 값을 바꿀 수 없었음. neo4j-graphrag의 하이브리드 검색기는 필터를 받지 않아 회원별 검색 같은 조건은 직접 Cypher로 짜야 함. "
      + "증분 색인: Lucene 계열 키워드 색인(Elasticsearch, OpenSearch, Neo4j 전문 검색)은 문서를 넣고 고치고 지우는 대로 따로 갱신되므로 "
      + "어느 안이든 전체를 다시 만들 필요가 없음. 그래서 차이는 '바뀐 문서 하나를 몇 곳에 써야 하고, 그 곳들이 서로 어긋나지 않게 맞춰야 하느냐'임. "
      + "다만 bm25s처럼 추가와 삭제 기능이 없는 정적 라이브러리로 키워드 색인을 만들면 바뀔 때마다 전체를 다시 만들어야 하며, 지금 우리 구성이 이 경우임. "
      + "Neo4j Community 판에는 온라인 백업과 클러스터가 없고 Enterprise 판에는 있음. "
      + "바뀐 청크만 LLM으로 다시 추출하고 엔티티를 병합하는 그래프 쪽 일은 네 안 모두 같음.",
  });

  const labW = 1.6, gx0 = X0 + labW + 0.15, g = 0.15;
  const cw = (X0 + CW - gx0 - g * 3) / 4;
  const cx = (i) => gx0 + i * (cw + g);
  const CHIP = { 벡터: C.blue, 키워드: C.navy, 그래프: C.dark };
  const plans = [
    { name: "1-a 분리형(저장소 따로)", stores: [["벡터 DB", ["벡터"]], ["키워드 색인", ["키워드"]], ["Neo4j", ["그래프"]]] },
    { name: "1-b 분리형(검색 엔진)", stores: [["검색 엔진(nori)", ["벡터", "키워드"]], ["Neo4j", ["그래프"]]], pick: true },
    { name: "2 벡터 통합형", stores: [["Neo4j", ["벡터", "그래프"]], ["키워드 색인", ["키워드"]]], pick: true },
    { name: "3 전부 통합형", stores: [["Neo4j", ["벡터", "키워드", "그래프"]]] },
  ];
  const yHead = 1.86, hHead = 0.42, yStore = yHead + hHead + 0.08, hStore = 0.86;
  // 증분 색인 줄만 세 줄(지원 여부 + 맞춤 부담)이라 높게 두고 나머지 줄을 조금 줄여 전체 높이를 지킴
  const yRow0 = yStore + hStore + 0.14, rhBase = 0.58, rhTall = 0.98, rg = 0.06;
  const rows = [
    ["한국어 키워드\n품질", [["좋음", "형태소 분석기를\n골라 씀(예: Kiwi)"], ["좋음", "nori 공식 플러그인과\n사용자 사전"],
      ["좋음", "형태소 분석기를\n골라 씀"], ["주의", "한국어 분석기 없음,\n미리 나누거나 직접 개발"]]],
    ["운영:\n저장소와 장애", [["보통", "3곳 운영,\n한 곳 멈춰도 나머지 검색"], ["좋음", "2곳, 검색 엔진\n복제로 장애 대비"],
      ["보통", "2곳, Neo4j 멈추면\n벡터와 그래프 함께 멈춤"], ["주의", "1곳으로 단순,\n멈추면 검색 전부 멈춤"]]],
    ["운영:\n규모와 백업", [["보통", "저장소마다 확장과\n백업을 따로 함"], ["좋음", "대규모, 필터,\n백업 기능 갖춤"],
      ["보통", "Community는 온라인\n백업과 클러스터 없음"], ["주의", "같은 제약에 키워드\n색인까지 몰림"]]],
    // 바뀐 문서 하나를 몇 곳에 쓰고 맞춰야 하나(Lucene 계열 색인은 모두 문서 단위로 갱신됨). 그래프 재추출은 네 안 모두 같아 뺌
    // 첫 줄은 증분 색인 지원 여부(굵게), 둘째 줄부터 저장소 사이 맞춤 부담
    ["운영:\n증분 색인", [["주의", "지원: 벡터와 그래프\n키워드는 도구 따라 다름\n3곳에 따로 쓰고 맞춤"],
      ["보통", "지원: 모두\n2곳, 검색 엔진은 벡터와\n키워드를 한 문서로 갱신"],
      ["보통", "지원: 벡터와 그래프\n키워드는 도구 따라 다름\n2곳, Neo4j와 키워드 맞춤"],
      ["좋음", "지원: 모두\n1곳, 한 트랜잭션에서\n벡터와 키워드 함께 갱신"]]],
    ["그래프 연결", [["보통", "저장소 사이를\nID로 이어 조회"], ["보통", "같음(검색 결과 ID로\nNeo4j 조회)"],
      ["좋음", "관계 선 하나,\n쿼리 한 번"], ["좋음", "관계 선 하나,\n쿼리 한 번"]]],
  ];
  const chipFill = { 좋음: C.blue, 기준: C.blue, 실측: C.blue, 보통: C.slate, 미측정: C.slate, "채점 중": C.slate, 주의: C.dark };
  const rhOf = (r) => (rows[r][0].includes("증분") ? rhTall : rhBase);
  const yOfRow = (r) => yRow0 + rows.slice(0, r).reduce((a, _, k) => a + rhOf(k) + rg, 0);
  const yEnd = yOfRow(rows.length - 1) + rhOf(rows.length - 1);

  // 열 바탕: 권고 안(1-b, 2)은 파란 테두리로 표시
  plans.forEach((p, i) => {
    L.rr(s, { x: cx(i) - 0.05, y: yHead - 0.05, w: cw + 0.1, h: yEnd - yHead + 0.1, fill: C.altRow,
      line: p.pick ? C.blue : null, lw: 1.5, r: 0.08 });
    L.card(s, p.name, { x: cx(i), y: yHead, w: cw, h: hHead, fill: p.pick ? C.blue : C.navy, line: null, color: C.white,
      size: 15, bold: true, r: 0.06 });
    // 저장소 상자: 상자 폭은 그 안에 든 칩 수에 비례
    const units = p.stores.reduce((a, st) => a + Math.max(st[1].length, 1), 0);
    const sg = 0.08, unitW = (cw - sg * (p.stores.length - 1)) / units;
    let x = cx(i);
    p.stores.forEach(([name, chips]) => {
      const w = unitW * chips.length + (chips.length - 1) * 0;
      L.rr(s, { x, y: yStore, w, h: hStore, fill: C.white, line: C.slate, lw: 1, r: 0.06 });
      L.text(s, name, { x, y: yStore + 0.04, w, h: 0.34, size: 14, bold: true, color: C.ink, align: "center", margin: 0 });
      const chW = (w - 0.12 - 0.06 * (chips.length - 1)) / chips.length;
      chips.forEach((c, k) => L.card(s, c, { x: x + 0.06 + k * (chW + 0.06), y: yStore + 0.44, w: chW, h: 0.34, fill: CHIP[c],
        line: null, color: C.white, size: 14, bold: true, r: 0.05 }));
      x += w + sg;
    });
  });

  // 비교 줄: 왼쪽 줄 이름 + 칸마다 판정 칩과 한두 줄 설명
  rows.forEach(([label, cells], r) => {
    const y = yOfRow(r), rh = rhOf(r);
    const ops = label.startsWith("운영") || label.startsWith("한국어");
    L.card(s, label, { x: X0, y, w: labW, h: rh, fill: ops ? C.blue : C.tint, line: ops ? null : C.blue,
      color: ops ? C.white : C.navy, size: 14, bold: true, r: 0.06 });
    cells.forEach(([v, t], i) => {
      L.rr(s, { x: cx(i), y, w: cw, h: rh, fill: C.white, line: C.border, r: 0.05 });
      const chipW = v.length >= 3 ? 0.86 : 0.62;
      L.card(s, v, { x: cx(i) + 0.07, y: y + (rh - 0.32) / 2, w: chipW, h: 0.32, fill: chipFill[v], line: null,
        color: C.white, size: 14, bold: true, r: 0.05 });
      const tx = { x: cx(i) + chipW + 0.14, y, w: cw - chipW - 0.18, h: rh };
      if (t.startsWith("지원:")) {
        // 지원 여부 줄은 굵은 남색으로 먼저 보이게 함
        const [head, ...rest] = t.split("\n");
        s.addText([{ text: head, options: { bold: true, color: C.navy, breakLine: true } },
          { text: rest.join("\n"), options: { color: C.ink } }],
        { ...tx, fontFace: FONT, fontSize: fs(14), margin: 0, valign: "middle", isTextBox: true });
      } else {
        L.text(s, t, { ...tx, size: 14, color: C.ink, margin: 0 });
      }
    });
  });

  band(s, "권고: 한국어 실서비스는 1-b 분리형(검색 엔진)이 정석, 그래프 비중이 크고 규모가 작으면 2 벡터 통합형\n"
    + "3 전부 통합형은 증분 색인이 가장 단순하지만 한국어 분석기와 필터를 Neo4j에서 직접 만들어야 해 한국어에서는 마지막 선택지",
  { y: 7.12, h: 0.76, size: 15 });
  L.text(s, "※ 키워드 색인을 추가와 삭제가 없는 정적 라이브러리(예: bm25s)로 만들면 바뀔 때마다 전체를 다시 만들어야 함(지금 우리 구성)",
    { x: 0.515, y: 8.029, w: 14.792, h: 0.37, size: 16, color: C.ink, margin: 0 });
  return s;
}

// ------------------------------------------------------------------ 별도 장표 2쪽(1-b 분리형의 인덱싱 파이프라인)
async function createSlidePipeline1b() {
  const s = L.newSlide({
    title: "그래프DB 구축: 1-b 분리형(검색 엔진)의 인덱싱 파이프라인",
    lead: "청킹까지 함께 쓰고 두 갈래로 나눔 — 검색 갈래는 검색 엔진에 문서 단위로 쓰고, KG 갈래는 지금과 같음",
    notes: "1-b에서 바뀌는 곳은 ③ 청킹 뒤의 검색 갈래뿐임. 지금은 Chroma에 벡터를, bm25s로 BM25 파일을 따로 만들지만, 1-b는 검색 엔진 한 문서에 "
      + "본문, 벡터, 메타데이터를 함께 넣고 문서 단위로 넣고 고치고 지움. 키워드 분석은 nori와 사용자 사전으로 옮기거나, Kiwi로 미리 나눈 낱말을 "
      + "공백 분석기로 넣는 두 길이 있음. nori로 옮기면 Kiwi와 결과가 같지 않아 순위 비교 시험이 필요함. "
      + "KG 갈래는 그대로임. 청크 하나에 제목 단위가 여럿 든 문서는 추출 직전에 청크를 추출 단위(예: 규정은 조항, 매뉴얼은 절)로 나누고, "
      + "제목 단위가 하나뿐인 문서는 청크를 그대로 씀. 추출 단위 노드와 추출 노드는 Neo4jWriter 한 묶음으로 저장함. "
      + "세대는 새 인덱스를 만든 뒤 검색 엔진 별칭과 Neo4j 세대를 같은 순간에 바꿔야 하며, 한쪽만 바뀌면 검색 결과의 chunk_id가 그래프에 없게 됨. "
      + "노드 설명 임베딩을 Neo4j에 둘지 검색 엔진에 둘지는 따로 정할 일임. "
      + "라이선스: Elasticsearch는 2021년부터 SSPL과 Elastic License 2.0이었고 2024년 8월 말 AGPL v3를 선택지로 더해 다시 오픈소스로 인정됨. "
      + "OpenSearch는 Elasticsearch 7.10.2에서 갈라진 Apache 2.0 프로젝트이며 2024년 9월부터 리눅스 재단 산하 OpenSearch Software Foundation이 관리함. "
      + "회사 서비스에 넣을 때는 사내 법무 또는 오픈소스 담당의 확인을 받음.",
  });

  // 9칸 격자, 네 줄(설계 시, 인덱싱 공통, KG 갈래, 검색 갈래)
  const laneW = 1.7, gx0 = X0 + laneW + 0.15, gap = 0.15, n = 9;
  const cw = (X0 + CW - gx0 - gap * (n - 1)) / n;
  const gx = (i) => gx0 + i * (cw + gap);
  const span = (k) => k * cw + (k - 1) * gap;
  // 맨 아래 "추출 단위" 예시 띠를 넣으려고 줄 높이를 조금 줄임
  const lanes = [
    { y: 1.86, h: 0.56, t: "설계 시\n(사전 1회)", fill: C.dark },
    { y: 2.56, h: 0.56, t: "인덱싱 공통\n(매 실행)", fill: C.navy },
    { y: 3.26, h: 0.62, t: "KG 갈래\n(그대로)", fill: C.navy },
    { y: 4.02, h: 0.62, t: "검색 갈래\n(1-b에서 바뀜)", fill: C.blue },
  ];
  lanes.forEach((ln) => {
    L.rr(s, { x: gx0 - 0.08, y: ln.y - 0.06, w: X0 + CW - gx0 + 0.08, h: ln.h + 0.12, fill: C.altRow, line: null, r: 0.06 });
    L.card(s, ln.t, { x: X0, y: ln.y - 0.06, w: laneW, h: ln.h + 0.12, fill: ln.fill, line: null, color: C.white, size: 14,
      bold: true, r: 0.06 });
  });
  const LOOKS = {
    plain: { fill: C.white, line: C.slate, color: C.ink },
    key: { fill: C.navy, line: null, color: C.white },
    changed: { fill: C.blue, line: null, color: C.white },
    schema: { fill: C.tint, line: C.blue, color: C.navy },
  };
  const box = (lane, i, k, t, look = "plain") => {
    const ln = lanes[lane], st = LOOKS[look];
    L.card(s, t, { x: gx(i), y: ln.y, w: span(k), h: ln.h, fill: st.fill, line: st.line, color: st.color, size: 14, bold: true,
      r: 0.08, lw: 1.25 });
  };
  const flow = (lane, items) => {
    items.forEach(([i, k, t, look]) => box(lane, i, k, t, look));
    const ym = lanes[lane].y + lanes[lane].h / 2;
    items.slice(0, -1).forEach(([i, k], j) => {
      const x1 = gx(i) + span(k) + 0.03, x2 = gx(items[j + 1][0]) - 0.03;
      L.arrow(s, { x1, y1: ym, x2, y2: ym, color: C.slate, width: 1.75 });
    });
  };
  flow(0, [[0, 1, "원천 분석"], [1, 1, "후보 도출"], [2, 1, "3단계 확정\n(사람)"], [4, 2, "GraphSchema 파일\n(버전 관리)", "schema"]]);
  flow(1, [[0, 1, "로드"], [1, 1, "정제와\n가명처리"], [2, 1, "③ 청킹"]]);
  flow(2, [[3, 1, "④-1 추출 단위\n나누기"], [4, 1, "④-2 추출", "key"], [5, 1, "가지치기\n(Pruning)", "key"], [6, 1, "KG 저장"],
    [7, 1, "병합"], [8, 1, "임베딩\n(노드 설명)"]]);
  flow(3, [[3, 1, "청크 임베딩\n(바뀐 것만)", "changed"], [4, 2, "키워드 분석\n(nori 또는 Kiwi 낱말)", "changed"],
    [6, 2, "검색 엔진에 쓰기\n(문서 단위로 넣고 지움)", "changed"], [8, 1, "별칭 전환\n(세대)", "changed"]]);

  // GraphSchema 파일 → 추출, 가지치기(점선, 읽어 씀). 인덱싱 공통 줄의 5, 6번째 칸은 비어 있어 선이 상자를 지나지 않음
  [4, 5].forEach((i) => L.arrow(s, { x1: gx(i) + cw / 2, y1: lanes[0].y + lanes[0].h + 0.02, x2: gx(i) + cw / 2,
    y2: lanes[2].y - 0.02, color: C.blue, width: 1.5, dash: "dash" }));
  L.text(s, "읽어 씀", { x: gx(4) + cw / 2 + 0.06, y: lanes[1].y + 0.12, w: 0.9, h: 0.3, size: 14, bold: true, color: C.blue,
    margin: 0 });
  L.text(s, "인덱싱은 읽기만 함\n바뀌면 새 세대로 재인덱싱", { x: gx(6) + 0.1, y: lanes[0].y, w: span(3) - 0.1, h: lanes[0].h, size: 14,
    bold: true, color: C.blue, margin: 0 });
  L.text(s, "청크는 검색용 크기 그대로\n두 갈래가 함께 씀", { x: gx(6) + 0.1, y: lanes[1].y, w: span(3) - 0.1, h: lanes[1].h, size: 14,
    color: C.slate, margin: 0 });

  // ③ 청킹에서 두 갈래로: 청킹 오른쪽 → 3번째와 4번째 칸 사이 세로선 → 각 갈래 첫 상자
  const xs = gx(2) + cw + 0.03, xm = gx(3) - gap / 2 - 0.02;
  const y2 = lanes[1].y + lanes[1].h / 2, y3 = lanes[2].y + lanes[2].h / 2, y4 = lanes[3].y + lanes[3].h / 2;
  L.hline(s, { x: xs, y: y2, w: xm - xs, color: C.slate, width: 1.75 });
  L.arrow(s, { x1: xm, y1: y2, x2: xm, y2: y4, color: C.slate, width: 1.75, head: "none" });
  [y3, y4].forEach((y) => L.arrow(s, { x1: xm, y1: y, x2: gx(3) - 0.03, y2: y, color: C.slate, width: 1.75 }));

  // 아래: 세대 전환, 검색 때 연결, 라이선스
  const top = 4.92, bodyY = top + 0.48, bodyB = 7.12;
  const wL = 4.15, g3 = 0.25, wR = CW - wL * 2 - g3 * 2;
  const xA = X0, xB = xA + wL + g3, xC = xB + wL + g3;
  sectionLabel(s, "세대 전환을 함께", { x: xA, y: top, w: wL });
  L.rr(s, { x: xA, y: bodyY, w: wL, h: bodyB - bodyY, fill: C.white, line: C.border, r: 0.08 });
  bullets(s, ["새 세대 인덱스를 다 만든 뒤 검색 엔진 별칭과 Neo4j 세대를 같은 순간에 바꿈",
    "한쪽만 바뀌면 검색 결과의 chunk_id가 그래프에 없게 됨",
    "증분 색인은 바뀐 문서만 두 곳에 쓰고 맞춤"], { x: xA + 0.18, y: bodyY + 0.14, w: wL - 0.3, h: bodyB - bodyY - 0.24, gap: 8 });
  sectionLabel(s, "검색 때 그래프로 건너감", { x: xB, y: top, w: wL });
  L.rr(s, { x: xB, y: bodyY, w: wL, h: bodyB - bodyY, fill: C.white, line: C.border, r: 0.08 });
  bullets(s, ["검색 엔진이 하이브리드로 청크를 찾음(BM25와 벡터, 회원 필터)",
    "돌려받은 chunk_id로 Neo4j 추출 단위 노드의 parent_chunk_ids를 찾음",
    "관계를 따라 질문에 필요한 근거 노드를 얻음"], { x: xB + 0.18, y: bodyY + 0.14, w: wL - 0.3, h: bodyB - bodyY - 0.24,
    gap: 8 });
  sectionLabel(s, "검색 엔진 라이선스(2026-10 기준, 둘 다 nori 지원)", { x: xC, y: top, w: wR, fill: C.dark });
  // 칸마다 세 줄로 줄여 상자 안에 들어가게 함(렌더링에서 넘침 확인 후 고침)
  const lic = [
    ["Elasticsearch", "AGPL v3, SSPL, ELv2 중 선택\n2024-08 AGPL 추가로 다시 오픈소스\nAGPL로 고쳐서 서비스하면 소스 공개"],
    ["OpenSearch", "Apache 2.0(7.10.2에서 갈라짐)\n2024-09부터 리눅스 재단 산하 재단 관리\n고쳐 써도 소스 공개 의무 없음"],
  ];
  const lh = 0.8, lg = 0.06;
  lic.forEach(([name, t], k) => {
    const y = bodyY + k * (lh + lg);
    L.rr(s, { x: xC, y, w: wR, h: lh, fill: C.white, line: C.border, r: 0.06 });
    L.card(s, name, { x: xC + 0.08, y: y + (lh - 0.36) / 2, w: 1.55, h: 0.36, fill: C.navy, line: null, color: C.white, size: 14,
      bold: true, r: 0.05 });
    L.text(s, t, { x: xC + 1.72, y, w: wR - 1.8, h: lh, size: 14, color: C.ink, margin: 0 });
  });
  // 맨 아래 띠: 추출 단위의 뜻과 예(나누는 경우, 그대로 쓰는 경우)를 도형으로 보여 줌
  const yE = 7.26, hE = 0.64, mid = yE + hE / 2;
  L.rr(s, { x: X0, y: yE - 0.04, w: CW, h: hE + 0.08, fill: C.altRow, line: null, r: 0.06 });
  s.addText([{ text: "추출 단위", options: { bold: true, color: C.navy, breakLine: true } },
    { text: "LLM에 한 번에 넣는 글 조각", options: { color: C.ink } }],
  { x: X0 + 0.12, y: yE, w: 2.55, h: hE, fontFace: FONT, fontSize: fs(14), margin: 0, valign: "middle", isTextBox: true });
  const chip = (t, x, w, look) => L.card(s, t, { x, y: yE + 0.1, w, h: hE - 0.2, ...LOOKS[look], size: 14, bold: true,
    r: 0.05, lw: 1.25 });
  const arr = (x1, x2) => L.arrow(s, { x1, y1: mid, x2, y2: mid, color: C.slate, width: 1.75 });
  // 예 1: 청크 하나에 제목 단위가 여럿 → 나눠서 여러 번 추출
  let ex = X0 + 2.75;
  chip("예 1) 약관 청크 A\n조항 3개가 함께 듦", ex, 2.05, "plain");
  arr(ex + 2.08, ex + 2.3);
  ex += 2.33;
  ["제33조", "제34조", "제34조의2"].forEach((t, k) => chip(t, ex + k * 1.06, 1.0, "schema"));
  arr(ex + 3.15, ex + 3.37);
  chip("LLM 3번 추출", ex + 3.4, 1.35, "key");
  // 예 2: 청크 하나가 한 건 → 그대로 한 번 추출
  ex += 3.4 + 1.35 + 0.25;
  chip("예 2) 상담 청크 B\n상담 1건", ex, 1.8, "plain");
  arr(ex + 1.83, ex + 2.05);
  chip("그대로", ex + 2.08, 0.8, "schema");
  arr(ex + 2.91, ex + 3.13);
  chip("LLM 1번 추출", ex + 3.16, X0 + CW - (ex + 3.16) - 0.1, "key");
  return s;
}

// 출처 줄: 구분선 + 한 줄(가이드 3절 ⑤⑥). 링크가 있으면 글자에 하이퍼링크를 붙임
function sourceLine(s, prefix, links = []) {
  L.hline(s, { x: X0, y: 8.08, w: CW, color: C.footLine, width: 1 });
  const runs = [{ text: prefix, options: { color: C.sub } }];
  links.forEach(([label, url], i) => {
    if (i > 0) runs.push({ text: ", ", options: { color: C.sub } });
    runs.push({ text: label, options: { color: C.blue, underline: { style: "sng" }, hyperlink: { url, tooltip: url } } });
  });
  s.addText(runs, { x: X0, y: 8.14, w: CW, h: 0.32, fontFace: FONT, fontSize: fs(14), margin: 0, valign: "middle",
    isTextBox: true });
}

// 글머리 여러 줄(줄 사이 간격을 둠)
function bullets(s, lines, { x, y, w, h, size = 14, color = C.ink, gap = 5, valign = "top" }) {
  s.addText(lines.map((t, i) => ({ text: t, options: { bullet: { indent: 12 }, breakLine: i < lines.length - 1 } })),
    { x, y, w, h, fontFace: FONT, fontSize: fs(size), color, valign, margin: 0, isTextBox: true, paraSpaceAfter: gap });
}

// ------------------------------------------------------------------ 슬라이드 5(v9 다시 씀: 일반 권고 절차)
async function createSlideGuide() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 소스 문서 → 노드 타입과 관계: 권고 절차(Neo4j)",
    lead: "LLM은 넓게 후보만 뽑고, 사람이 역량 질문 기준으로 뼈대를 확정한 뒤, 뼈대로 실제 추출해 검증하고 GraphSchema로 고정함",
    notes: "문서 종류와 상관없이 쓰는 절차임. ① 역량 질문은 이 스키마로 만든 그래프가 답해야 할 질문 목록이며, Ontology 101에서 "
      + "범위를 정하고 나중에 충분한지 시험하는 기준으로 씀. 답이 될 타입 이름은 적지 않고 질문으로만 씀. "
      + "② neo4j-graphrag의 SchemaFromTextExtractor는 글을 받아 스키마 후보를 내고, examples 자리에 역량 질문을 넣음. 표본은 비율이 아니라 "
      + "건수로 정함(드문 타입을 95% 확률로 보려면 등장률 10%면 29건). 앞서 나온 이름을 다시 쓰라는 안내를 넣으면 이름은 모이지만 "
      + "새 개념이 막혀서 이 단계에서는 넣지 않음. ③ 사람이 합치기, 빼기, 보태기로 뼈대를 정함. 드문 이름을 빈도로 거르면 핵심 개념이 "
      + "버려지므로 질문 기준으로 살림. 타입 설명(description)이 추출 품질을 크게 좌우하므로 무엇이 아닌지까지 좁게 씀. "
      + "LLM이 제안하는 제약은 자주 충돌하므로 사람이 정함. ④ LLMEntityRelationExtractor에 뼈대를 schema로 주고 GraphPruning으로 정리한 뒤, "
      + "정답표나 역량 질문의 답이 채워지는지 셈. 잘못 뽑기가 많으면 설명을 고쳐 다시 함. ⑤ GraphSchema.save()로 파일을 고정하고 "
      + "인덱싱은 그 파일만 읽음. 화면으로 하려면 Neo4j LLM Graph Builder의 Get Schema From Text가 ②에 해당함.",
  });

  const n = 5, gap = 0.3, cw = (CW - gap * (n - 1)) / n, y = 1.9, h = 0.62;
  const cx = (i) => X0 + i * (cw + gap);
  const steps = [
    ["① 역량 질문 정하기", "사람", "blue"], ["② 넓게 뽑기", "LLM", "tint"], ["③ 뼈대 확정", "사람", "blue"],
    ["④ 채우기 시험", "LLM + 사람", "tint"], ["⑤ 고정", "코드", "navy"],
  ];
  steps.forEach(([t, who, st], i) => {
    L.card(s, `${t}\n${who}`, { x: cx(i), y, w: cw, h, ...LOOK[st], size: 15, bold: true, r: 0.08, lw: st === "tint" ? 1.5 : 1 });
    if (i < n - 1) {
      L.arrow(s, { x1: cx(i) + cw + 0.03, y1: y + h / 2, x2: cx(i + 1) - 0.03, y2: y + h / 2, color: C.slate, width: 1.75 });
    }
  });
  // ④ → ③ 되돌림(설명을 고쳐 다시)
  const yb = y + h + 0.28, x3 = cx(2) + cw / 2, x4 = cx(3) + cw / 2;
  L.arrow(s, { x1: x4, y1: y + h + 0.02, x2: x4, y2: yb, color: C.blue, width: 1.5, dash: "dash", head: "none" });
  L.hline(s, { x: x3, y: yb, w: x4 - x3, color: C.blue, width: 1.5, dash: "dash" });
  L.arrow(s, { x1: x3, y1: yb, x2: x3, y2: y + h + 0.02, color: C.blue, width: 1.5, dash: "dash" });
  L.text(s, "설명 고쳐 다시", { x: x3 + 0.1, y: y + h + 0.02, w: x4 - x3 - 0.2, h: 0.24, size: 14, bold: true, color: C.blue,
    align: "center", margin: 0 });

  const dy = 2.95, dh = 2.45;  // 15pt 글머리가 들어가고 아래 주의 칸을 키울 수 있게 맞춘 높이
  const details = [
    ["문서 종류마다 답해야 할 질문 5개 안팎", "타입 이름은 쓰지 않고 질문으로만 씀", "질문이 범위이자 나중의 합격 기준"],
    ["층별 표본: 시작 10건, 상한 30건(비율이 아니라 건수)", "SchemaFromTextExtractor에 질문을 examples로 넣음",
      "앞서 나온 이름을 다시 쓰라는 안내는 넣지 않음"],
    ["합치기, 빼기, 보태기", "빈도가 아니라 질문 기준(드문 이름도 살림)", "타입마다 description을 좁게(무엇이 아닌지까지)",
      "제약은 사람이 정함"],
    ["뼈대를 schema로 주고 추출한 뒤 GraphPruning으로 정리", "정답표나 질문의 답이 채워지는지 셈",
      "잘못 뽑기가 많으면 설명을 고쳐 ③으로"],
    ["GraphSchema.save(), additional_* = false", "인덱싱은 이 파일을 읽기만 함", "바뀌면 새 세대로 다시 인덱싱"],
  ];
  details.forEach((lines, i) => {
    const human = steps[i][2] === "blue";
    L.rr(s, { x: cx(i), y: dy, w: cw, h: dh, fill: human ? C.tint : C.white, line: human ? C.blue : C.border, r: 0.08 });
    // 15pt는 SchemaFromTextExtractor 같은 긴 이름이 중간에서 끊겨 14pt로 둠
    bullets(s, lines, { x: cx(i) + 0.14, y: dy + 0.14, w: cw - 0.24, h: dh - 0.24, gap: 10 });
  });

  L.text(s, "주의", { x: X0, y: 5.6, w: 2.0, h: 0.32, size: 16, bold: true, color: C.navy, margin: 0 });
  const tips = [
    "앞서 나온 이름을 다시 쓰라는 안내는 이름을 모으지만 새 개념을 막음 → ④에서만",
    "대화 속 행위나 조항 규칙 같은 구조는 LLM이 잘 못 뽑음 → 사람이 보탬",
    "여러 문서에 걸친 관계(카드 비교 등)는 청크 단위 추출로 나오지 않음",
    "멈춤: 2건 이상 나온 새 이름이 연속 3건 없으면 그 층은 멈춤",
  ];
  const tg = 0.15, tw = (CW - tg * 3) / 4, ty = 5.98, th = 1.25;
  tips.forEach((t, i) => {
    const x = X0 + i * (tw + tg);
    L.rr(s, { x, y: ty, w: tw, h: th, fill: C.altRow, line: C.border, r: 0.08 });
    L.numBadge(s, "!", { x: x + 0.1, y: ty + (th - 0.4) / 2, size: 0.4, fsz: 16, fill: C.dark });
    L.text(s, t, { x: x + 0.6, y: ty, w: tw - 0.68, h: th, size: 15, color: C.ink, margin: 0 });
  });

  sourceLine(s, "출처: ", [
    ["Neo4j GraphRAG Python 사용자 안내", "https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html"],
    ["Neo4j LLM Graph Builder 기능", "https://neo4j.com/labs/genai-ecosystem/llm-graph-builder-features/"],
    ["Noy와 McGuinness, Ontology 101(역량 질문)", "https://protege.stanford.edu/publications/ontology_development/ontology101-noy-mcguinness.html"],
    ["Guest 외(2020) 포화 기준", "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0232076"]]);
  return s;
}

// ------------------------------------------------------------------ v10: 5쪽 단계별 예시(우리 예제의 실제 데이터)
// 출처 줄은 한 줄을 넘으면 고정 문구와 겹쳐 짧게 둠
const MEASURED = "실측: 2026-10-18, Groq openai/gpt-oss-120b, neo4j-graphrag 1.22.0, 합성 상담 이력 v3";

// 작은 글자 배지(묶음 이름, 유형 기호 등)
function tag(s, t, { x, y, w = 0.36, h = 0.32, fill = C.blue, color = C.white, size = 14 }) {
  L.card(s, t, { x, y, w, h, fill, line: null, color, size, bold: true, r: Math.min(0.08, h / 2) });
}

// 판정 배지: 맞음(파랑) 또는 틀림(어두운 회색)
function verdict(s, ok, { x, y }) {
  tag(s, ok ? "맞음" : "틀림", { x, y, w: 0.72, h: 0.34, fill: ok ? C.blue : C.dark });
}

// 단계 ① 역량 질문 정하기
async function createStep1() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 단계 ① 역량 질문 정하기(예시: 상담 이력)",
    lead: "실제 사용자 질문을 모아 값을 빈칸으로 바꾸고 유형으로 묶은 뒤, 유형마다 역량 질문을 씀",
    notes: "역량 질문은 문서만 보고 지어내지 않고 사용자가 실제로 묻는 질문에서 출발함. 상담 이력의 출처는 D3 안내문의 검색 평가 질문과 "
      + "RAGAS 평가셋 문항임. 회원 번호 같은 값을 빈칸으로 바꾸면 같은 틀의 질문이 하나로 묶이고, 묶음마다 역량 질문을 1개 이상 씀. "
      + "제안과 응답처럼 한 유형에 두 질문이 필요하면 나눠 씀. 질문에는 Complaint 같은 답이 될 이름을 쓰지 않음. 이 예의 초안은 "
      + "LLM(클로니)이 사용자 질문을 보고 작성했고 사람이 검토함. 약관과 혜택도 같은 방법으로 5개씩 정했음.",
  });
  const c1 = { x: X0, w: 5.0 }, c2 = { x: X0 + 5.35, w: 3.85 }, c3 = { x: X0 + 9.55, w: CW - 9.55 };
  sectionLabel(s, "실제 사용자 질문(출처)", { x: c1.x, y: 1.9, w: c1.w, fill: C.dark });
  sectionLabel(s, "값을 빈칸으로 → 질문 유형", { x: c2.x, y: 1.9, w: c2.w, fill: C.dark });
  sectionLabel(s, "역량 질문(상담 이력 5개)", { x: c3.x, y: 1.9, w: c3.w });
  [[c1, c2], [c2, c3]].forEach(([a, b]) => L.arrow(s, { x1: a.x + a.w + 0.04, y1: 2.1, x2: b.x - 0.04, y2: 2.1, color: C.slate,
    width: 2 }));

  const srcs = [
    ["D3 안내문 검색 평가", "이 고객의 최근 불편은 무엇이고 이전 상담과 무엇이 달라졌는가?", "A D"],
    ["D3 안내문 검색 평가", "어떤 제안을 받아들이거나 거절했으며 고객이 밝힌 이유는 무엇인가?", "B"],
    ["평가셋 Q15", "M-1042 회원은 생활비를 이 카드로 옮기는 것을 왜 원하지 않았나요?", "B"],
    ["평가셋 Q16", "M-3001 회원은 … 어떤 조건이면 옮기겠다고 했나요?", "C"],
  ];
  const types = [
    ["A", "{회원}의 최근 불편과 그 원인은?"], ["B", "{회원}이 받은 제안과 수용 또는 거절, 이유는?"],
    ["C", "{회원}은 어떤 조건이면 다시 보나?"], ["D", "{회원}의 이 상담은 어느 상담과 이어지나?"],
  ];
  const ry = 2.42, rh = 0.84, rg = 0.08;
  srcs.forEach(([src, q, tg], i) => {
    const y = ry + i * (rh + rg);
    L.rr(s, { x: c1.x, y, w: c1.w, h: rh, fill: C.white, line: C.border, r: 0.06 });
    s.addText([
      { text: src, options: { fontSize: fs(14), bold: true, color: C.slate, breakLine: true } },
      { text: q, options: { fontSize: fs(14), color: C.ink } },
    ], { x: c1.x + 0.12, y, w: c1.w - 1.1, h: rh, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true });
    // 배지는 오른쪽 끝에 붙여 글과 겹치지 않게 함
    const tgs = tg.split(" ");
    tgs.forEach((t, k) => tag(s, t, { x: c1.x + c1.w - 0.1 - (tgs.length - k) * 0.4, y: y + (rh - 0.32) / 2 }));
  });
  types.forEach(([t, q], i) => {
    const y = ry + i * (rh + rg);
    L.rr(s, { x: c2.x, y, w: c2.w, h: rh, fill: C.tint, line: C.blue, r: 0.06 });
    tag(s, t, { x: c2.x + 0.1, y: y + (rh - 0.32) / 2 });
    L.text(s, q, { x: c2.x + 0.55, y, w: c2.w - 0.65, h: rh, size: 14, bold: true, color: C.navy, margin: 0 });
  });
  const cqs = [
    ["A", "고객이 말한 불만 원인은 무엇인가?"], ["B", "상담사가 어떤 제안을 했는가?"],
    ["B", "고객은 그 제안을 수용했는가, 거절했는가, 보류했는가? 그 이유는?"],
    ["C", "고객은 어떤 조건이 되면 다시 검토하겠다고 했는가?"], ["D", "이 상담은 같은 고객의 어떤 이전 상담과 이어지는가?"],
  ];
  const qh = 0.62, qg = 0.07;
  cqs.forEach(([t, q], i) => {
    const y = ry + i * (qh + qg);
    L.rr(s, { x: c3.x, y, w: c3.w, h: qh, fill: C.white, line: C.blue, r: 0.06 });
    tag(s, t, { x: c3.x + 0.1, y: y + (qh - 0.32) / 2 });
    L.text(s, `${i + 1}. ${q}`, { x: c3.x + 0.55, y, w: c3.w - 0.65, h: qh, size: 14, color: C.ink, margin: 0 });
  });

  const by = 6.08, bh = 0.92;
  L.rr(s, { x: X0, y: by, w: 7.3, h: bh, fill: C.altRow, line: C.border, r: 0.08 });
  s.addText([
    { text: "답이 될 이름은 쓰지 않음", options: { fontSize: fs(14), bold: true, color: C.navy, breakLine: true } },
    { text: "피함: \"Complaint 노드의 cause는?\"   권함: \"고객이 말한 불만 원인은?\"", options: { fontSize: fs(14), color: C.ink } },
  ], { x: X0 + 0.15, y: by, w: 7.0, h: bh, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true });
  L.rr(s, { x: X0 + 7.6, y: by, w: CW - 7.6, h: bh, fill: C.altRow, line: C.border, r: 0.08 });
  s.addText([
    { text: "다른 문서도 같은 방법(각 5개)", options: { fontSize: fs(14), bold: true, color: C.navy, breakLine: true } },
    { text: "약관: 어떤 조건을 채우면 어떤 면제나 혜택을 받는가?", options: { fontSize: fs(14), color: C.ink, breakLine: true } },
    { text: "혜택: 혜택의 한도와 제외 대상은 무엇인가?", options: { fontSize: fs(14), color: C.ink } },
  ], { x: X0 + 7.75, y: by, w: CW - 7.9, h: bh, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true });
  band(s, "초안은 LLM이 사용자 질문을 보고 작성하고 사람이 검토해 확정함. 개수는 정해 두지 않고 질문 유형마다 1개 이상",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, "근거: D3 상담 이력 안내문(검색 평가 질문), RAGAS 평가셋 Q15와 Q16, 역량 질문은 스키마 후보 실험에 쓴 문장 그대로");
  return s;
}

// 단계 ② 스키마 후보 넓게 뽑기
async function createStep2() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 단계 ② 스키마 후보 넓게 뽑기(예시: 상담 이력)",
    lead: "묶음별 표본을 1건씩 SchemaFromTextExtractor에 넣고(역량 질문만 examples로), 나온 이름을 모두 모음",
    notes: "문서를 성격이 비슷한 묶음으로 나눠 묶음마다 표본을 뽑음. 상담은 고객 세그먼트 6개, 혜택은 청크 성격 4개로 나눴음. 1건씩 넣는 "
      + "이유는 새 이름이 몇 개 늘었는지 세어 멈출 때를 정하려는 것임. 가운데는 실제 1건(C-20260701-016)에 대한 추출기 출력임. Proposal과 "
      + "Condition은 업무 개념이고, Customer의 email과 birthdate 속성은 가명처리 대상이라 ③에서 버릴 후보임. 30건을 모으면 이름이 53개로 "
      + "흩어지고 업무 개념 이름은 2 ~ 5건씩만 나옴. 같은 30건에 앞 결과 이름을 넘기면 10개로 모이지만 업무 개념은 불만 하나만 나왔음.",
  });
  const c1 = { x: X0, w: 4.6 }, c2 = { x: X0 + 4.9, w: 5.3 }, c3 = { x: X0 + 10.5, w: CW - 10.5 };
  sectionLabel(s, "묶음과 표본 수", { x: c1.x, y: 1.9, w: c1.w, fill: C.dark });
  const groups = [
    ["약관", "10청크 → 묶음 1개", "10건 전부 봄"],
    ["상담", "48건 → 고객 세그먼트 묶음 6개", "시작 12건(묶음마다 2건), 상한 30건"],
    ["혜택", "160청크 → 묶음 4개(공통 안내 4, 참고 카드 7, 카드 개요 64, 혜택 상세 85)", "시작 4, 7, 10, 10건, 묶음마다 상한 30건"],
  ];
  const gy = 2.42, gh = 1.2, gg = 0.1;
  groups.forEach(([n, a, b], i) => {
    const y = gy + i * (gh + gg);
    L.rr(s, { x: c1.x, y, w: c1.w, h: gh, fill: C.white, line: C.border, r: 0.06 });
    L.card(s, n, { x: c1.x + 0.1, y: y + 0.1, w: 0.8, h: gh - 0.2, fill: C.navy, line: null, color: C.white, size: 15, bold: true,
      r: 0.06 });
    s.addText([
      { text: a, options: { fontSize: fs(14), color: C.ink, breakLine: true } },
      { text: b, options: { fontSize: fs(14), bold: true, color: C.blue } },
    ], { x: c1.x + 1.02, y, w: c1.w - 1.12, h: gh, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true, paraSpaceAfter: 3 });
  });
  L.text(s, "1건씩 넣는 이유: 새 이름이 몇 개 늘었는지 세어 멈출 때를 정함", { x: c1.x, y: 6.35, w: c1.w, h: 0.6, size: 14,
    color: C.slate, margin: 0, valign: "top" });

  sectionLabel(s, "실제 1건: C-20260701-016(타사 관리 절차 비교)", { x: c2.x, y: 1.9, w: c2.w });
  L.rr(s, { x: c2.x, y: 2.42, w: c2.w, h: 1.78, fill: C.altRow, line: C.border, r: 0.06 });
  L.text(s, "고객: 전환 신청은 아직 안 했어요. 매달 신청을 반복해야 하는 게 불만의 원인이에요.\n"
    + "상담사: 지금 카드를 유지하시면 자주 쓰시는 곳 할인을 늘릴 수 있는지 확인해 볼까요?\n"
    + "고객: 그건 다음 결제일이 지나고 다시 볼게요. …\n"
    + "고객: 2026-06-26 상담 C-20260626-011과 이어지는 기록으로 남겨 주세요.",
  { x: c2.x + 0.12, y: 2.46, w: c2.w - 0.24, h: 1.7, size: 14, color: C.ink, margin: 0, valign: "middle" });
  L.arrow(s, { x1: c2.x + 0.25, y1: 4.22, x2: c2.x + 0.25, y2: 4.52, color: C.navy, width: 2 });
  L.text(s, "SchemaFromTextExtractor(examples = 역량 질문)", { x: c2.x + 0.42, y: 4.22, w: c2.w - 0.42, h: 0.3,
    size: 14, bold: true, color: C.navy, margin: 0 });
  L.rr(s, { x: c2.x, y: 4.56, w: c2.w, h: 2.42, fill: C.white, line: C.blue, r: 0.06 });
  L.text(s, "나온 노드 타입 6개", { x: c2.x + 0.12, y: 4.62, w: 3, h: 0.3, size: 14, bold: true, color: C.navy, margin: 0 });
  const pills = [["Customer", false], ["Transaction", false], ["Request", false], ["Record", false], ["Proposal", true],
    ["Condition", true]];
  let px = c2.x + 0.12, py = 4.98;
  pills.forEach(([t, biz]) => {
    const w = 0.22 + t.length * 0.105;
    if (px + w > c2.x + c2.w - 0.1) { px = c2.x + 0.12; py += 0.42; }
    tag(s, t, { x: px, y: py, w, h: 0.34, fill: biz ? C.blue : C.altRow, color: biz ? C.white : C.navy });
    px += w + 0.1;
  });
  L.text(s, "관계 7개: MAKES_REQUEST, PROVIDES_PROPOSAL, HAS_CONDITION, CONTINUES_WITH 등\n"
    + "파랑 = 업무 개념. Customer 속성으로 email, birthdate까지 제안 → 가명처리 대상이라 ③에서 버림",
  { x: c2.x + 0.12, y: 5.85, w: c2.w - 0.24, h: 1.08, size: 14, color: C.ink, margin: 0, valign: "top" });

  sectionLabel(s, "30건을 모은 결과", { x: c3.x, y: 1.9, w: c3.w });
  L.rr(s, { x: c3.x, y: 2.42, w: c3.w, h: 0.9, fill: C.tint, line: C.blue, r: 0.06 });
  L.text(s, "노드 타입 53개, 관계 106개", { x: c3.x, y: 2.42, w: c3.w, h: 0.9, size: 18, bold: true, color: C.navy, align: "center",
    margin: 0 });
  s.addText([
    { text: "많이 나온 이름", options: { fontSize: fs(14), bold: true, color: C.navy, breakLine: true } },
    { text: "Customer 29, Request 20, Transaction 18, Consultation 12, TransactionSummary 10", options: { fontSize: fs(14),
      color: C.ink, breakLine: true } },
    { text: "드물게 나온 업무 개념", options: { fontSize: fs(14), bold: true, color: C.blue, breakLine: true } },
    { text: "Issue 5, Complaint 2, Proposal 2, Condition 2, REJECTS_CHANGE 1", options: { fontSize: fs(14), color: C.ink } },
  ], { x: c3.x + 0.05, y: 3.42, w: c3.w - 0.1, h: 1.9, fontFace: FONT, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 4 });
  L.rr(s, { x: c3.x, y: 5.4, w: c3.w, h: 1.58, fill: C.altRow, line: C.border, r: 0.06 });
  s.addText([
    { text: "같은 30건, 앞 결과 이름을 넘기면", options: { fontSize: fs(14), bold: true, color: C.slate, breakLine: true } },
    { text: "10개로 모이지만 업무 개념 1 / 4", options: { fontSize: fs(14), color: C.ink, breakLine: true } },
    { text: "넘기지 않으면(권고)", options: { fontSize: fs(14), bold: true, color: C.blue, breakLine: true } },
    { text: "53개로 흩어지지만 업무 개념 4 / 4", options: { fontSize: fs(14), color: C.ink } },
  ], { x: c3.x + 0.12, y: 5.4, w: c3.w - 0.24, h: 1.58, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true });
  band(s, "드물게 나온 이름이 핵심일 수 있음 — 빈도로 거르지 말고 ③에서 역량 질문을 기준으로 판단",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, MEASURED + ", 상담 30건(세그먼트 균형 순서), 업무 개념 = 불만, 제안, 응답, 재검토 조건");
  return s;
}

// 스키마 초안 그림(③과 ⑤에서 같이 씀)
function drawDraft(s, { rx, rw, top }) {
  const nodeBox = (label, props, { x, y, w, h, dark = false, dash = false }) => {
    L.rr(s, { x, y, w, h, fill: dark ? C.navy : C.tint, line: dash ? C.sub : C.navy, lw: 1.5, r: 0.08, dash: dash ? "dash" : undefined });
    L.text(s, label, { x: x + 0.08, y: y + 0.03, w: w - 0.16, h: 0.3, size: 14, bold: true, color: dark ? C.white : C.navy,
      align: "center", margin: 0 });
    if (props) {
      L.text(s, props, { x: x + 0.08, y: y + 0.32, w: w - 0.16, h: h - 0.34, size: 14, color: dark ? "D9E3F5" : C.ink,
        align: "center", margin: 0, valign: "top" });
    }
  };
  const ax = rx + 0.1, aw = 2.0, bw = 2.5, bx = rx + rw - 0.1 - bw, t = top;
  nodeBox(":Consultation", "record_id (키)", { x: ax, y: t + 0.95, w: aw, h: 0.72, dark: true });
  nodeBox(":Consultation", "앞선 상담", { x: ax, y: t + 2.05, w: aw, h: 0.62, dash: true });
  nodeBox(":Complaint", "cause, category", { x: bx, y: t, w: bw, h: 0.68 });
  nodeBox(":Proposal", "content, decision,\ndecision_reason", { x: bx, y: t + 0.95, w: bw, h: 0.9 });
  nodeBox(":ReconsiderCondition", "description", { x: bx, y: t + 2.12, w: bw, h: 0.62 });
  L.arrow(s, { x1: ax + aw + 0.03, y1: t + 1.05, x2: bx - 0.03, y2: t + 0.4, color: C.navy, width: 1.5 });
  L.text(s, "HAS_COMPLAINT", { x: ax + aw + 0.05, y: t + 0.32, w: 1.7, h: 0.26, size: 14, bold: true, color: C.navy, margin: 0 });
  L.arrow(s, { x1: ax + aw + 0.03, y1: t + 1.4, x2: bx - 0.03, y2: t + 1.4, color: C.navy, width: 1.5 });
  L.text(s, "HAS_PROPOSAL", { x: ax + aw + 0.05, y: t + 1.1, w: bx - ax - aw - 0.1, h: 0.26, size: 14, bold: true, color: C.navy,
    align: "center", margin: 0 });
  L.arrow(s, { x1: bx + bw / 2, y1: t + 0.93, x2: bx + bw / 2, y2: t + 0.7, color: C.blue, width: 1.5 });
  L.text(s, "ADDRESSES", { x: bx + bw / 2 + 0.06, y: t + 0.68, w: 1.2, h: 0.24, size: 14, bold: true, color: C.blue, margin: 0 });
  L.arrow(s, { x1: bx + bw / 2, y1: t + 1.87, x2: bx + bw / 2, y2: t + 2.1, color: C.blue, width: 1.5 });
  L.text(s, "RECONSIDER_WHEN", { x: bx + bw / 2 - 2.15, y: t + 1.86, w: 2.08, h: 0.26, size: 14, bold: true, color: C.blue,
    align: "right", margin: 0 });
  L.arrow(s, { x1: ax + aw / 2, y1: t + 1.69, x2: ax + aw / 2, y2: t + 2.03, color: C.navy, width: 1.5 });
  L.text(s, "FOLLOWS", { x: ax + aw / 2 + 0.06, y: t + 1.72, w: 1.1, h: 0.26, size: 14, bold: true, color: C.navy, margin: 0 });
}

// 단계 ③ 스키마 후보 확정(LLM 추천 + 사람 확정)
async function createStep3() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 단계 ③ 스키마 후보 확정(LLM 추천 + 사람 확정)",
    lead: "후보 목록과 역량 질문을 LLM에 주면 병합, 제거, 추가 초안과 근거를 추천하고, 사람이 검토해 스키마 초안을 확정함",
    notes: "② 결과(이름 53개와 나온 건수)와 역량 질문 5개를 LLM에 주고 초안을 추천받았음(이 예에서는 클로니가 추천). 추천에는 항목마다 근거가 "
      + "된 질문 번호를 붙임. 병합은 같은 뜻의 이름을 하나로 합치는 것, 제거는 질문에 안 쓰이거나 다른 원천(RDB)에 있거나 가명처리 대상인 것을 "
      + "빼는 것, 추가는 후보에 없거나 거의 없던 개념을 넣는 것임. 고객 응답(수용, 거절)은 후보에 1건뿐이었지만 질문 3에 필요해 추가함. "
      + "사람은 데이터 사정으로 판단함: 응답을 노드로 둘지 속성으로 둘지, 제약은 Community 판에서 되는 UNIQUENESS만. 오른쪽 아래 설명은 "
      + "④ 시험을 거쳐 좁힌 최종 판이며, 처음부터 해당과 비해당을 함께 쓰는 것이 좋음.",
  });
  const lw = 7.5, rx = X0 + lw + 0.3, rw = CW - lw - 0.3;
  sectionLabel(s, "LLM 추천(괄호 = 근거가 된 역량 질문 번호)", { x: X0, y: 1.9, w: lw, fill: C.dark });
  const groups = [
    ["병합", C.navy, ["Issue, Complaint → Complaint (1)", "Proposal, SUGGESTS, MAKES_PROPOSAL → Proposal (2)",
      "Condition → ReconsiderCondition (4)", "Consultation, Conversation, Session, Record → Consultation (5)",
      "FOLLOWS, CONTINUES_FROM, PREVIOUS_SESSION → FOLLOWS (5)"]],
    ["제거", C.dark, ["Request, Menu, Address, Order: 어느 질문에도 안 쓰임", "Transaction, TransactionSummary: RDB에 이미 있는 집계",
      "Customer의 name, email, birthdate: 가명처리 대상", "Agent, Counselor: 메타데이터(상담사 가명ID)로 충분"]],
    ["추가", C.blue, ["Proposal.decision, decision_reason (3): 후보는 REJECTS_CHANGE 1건뿐",
      "ADDRESSES: 제안이 어느 불만을 겨냥했나 (1, 2)", "RECONSIDER_WHEN: 보류한 제안의 재검토 조건 (4)"]],
  ];
  let y = 2.42;
  groups.forEach(([name, fill, lines]) => {
    const h = 0.14 + lines.length * 0.3;
    L.rr(s, { x: X0, y, w: lw, h, fill: C.white, line: C.border, r: 0.06 });
    L.card(s, name, { x: X0 + 0.1, y: y + 0.08, w: 0.8, h: h - 0.16, fill, line: null, color: C.white, size: 15, bold: true, r: 0.06 });
    L.text(s, lines.join("\n"), { x: X0 + 1.02, y, w: lw - 1.1, h, size: 14, color: C.ink, margin: 0 });
    y += h + 0.1;
  });

  sectionLabel(s, "사람이 검토해 정한 것", { x: rx, y: 1.9, w: rw });
  L.rr(s, { x: rx, y: 2.42, w: rw, h: 1.06, fill: C.tint, line: C.blue, r: 0.06 });
  L.text(s, "• 고객 응답은 노드 대신 Proposal 속성(decision, decision_reason)으로\n"
    + "• 상담 주제(Request)는 노드 대신 Consultation.topic 속성으로\n"
    + "• 제약은 Consultation.record_id UNIQUENESS 하나(Community 판)",
  { x: rx + 0.12, y: 2.42, w: rw - 0.2, h: 1.06, size: 14, color: C.navy, bold: true, margin: 0 });
  drawDraft(s, { rx, rw, top: 3.62 });
  L.rr(s, { x: rx, y: 6.42, w: rw, h: 0.6, fill: C.altRow, line: C.border, r: 0.06 });
  L.text(s, "Complaint 설명: 불만이나 불편을 분명히 말한 경우만. 문의 목적, 개인 사정은 아님",
    { x: rx + 0.12, y: 6.42, w: rw - 0.2, h: 0.6, size: 14, color: C.ink, margin: 0 });
  band(s, "결과: 스키마 초안 = 노드 타입 4, 관계 5, 패턴 5, 제약 1. 사람은 질문과 데이터 사정(RDB, 가명처리, Neo4j 판)으로 판단",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, "근거: 단계 ② 결과(이름 53개와 건수)와 역량 질문 5개, 초안 파일 skeleton_consult_v2.json(GraphSchema 검증 통과)");
  return s;
}

// 단계 ④-1 채우기 시험: 실제 1건씩 보기
async function createStep4a() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 단계 ④ 채우기 시험(1) 실제 1건씩 대조",
    lead: "스키마 초안을 schema로 주고 상담 48건 전체를 실제 추출해, 강사용 정답표와 한 건씩 맞춰 봄",
    notes: "LLMEntityRelationExtractor에 스키마 초안을 schema로 주고 GraphPruning으로 초안 밖 노드를 지운 뒤 정답표와 비교함. 왼쪽은 불만이 "
      + "있는 상담 1건으로, 불만 원인, 재검토 조건, 이전 상담 연결은 맞았지만 제안은 상담사가 한 다른 안내(자동납부 재등록 절차 비교)를 골라 "
      + "응답도 수용으로 적었음. 정답은 할인을 늘리는 제안과 보류임. 오른쪽은 불만이 없는 주소 변경 문의로, 답이 없어야 하는 문서임. v1 설명에서는 "
      + "'이사'를 불만으로, 절차 안내를 제안으로 뽑았고, 설명을 좁힌 v2에서는 둘 다 사라지고 제안 1개와 이유가 정답과 같아졌음.",
  });
  const lw = 7.3, rx = X0 + lw + 0.3, rw = CW - lw - 0.3;
  sectionLabel(s, "C-20260701-016, 불만이 있는 상담(v2 설명)", { x: X0, y: 1.9, w: lw, fill: C.dark });
  L.text(s, "항목", { x: X0 + 0.1, y: 2.36, w: 1.4, h: 0.28, size: 14, bold: true, color: C.slate, margin: 0 });
  L.text(s, "정답(대조표)", { x: X0 + 1.55, y: 2.36, w: 2.4, h: 0.28, size: 14, bold: true, color: C.slate, margin: 0 });
  L.text(s, "추출 결과", { x: X0 + 4.0, y: 2.36, w: 2.4, h: 0.28, size: 14, bold: true, color: C.slate, margin: 0 });
  const rows = [
    ["불만 원인", "매달 신청을 반복해야 하는 게 불만의 원인", "같음", true],
    ["재검토 조건", "다음 결제일이 지나고 다시 볼게요", "같음", true],
    ["이전 상담", "C-20260626-011", "같음(FOLLOWS 관계)", true],
    ["제안과 응답", "할인을 늘릴 수 있는지 확인, 보류", "자동납부 재등록 절차 비교, 수용", false],
  ];
  const ry = 2.7, rh = 0.8, rg = 0.08;
  rows.forEach(([k, gt, got, ok], i) => {
    const y = ry + i * (rh + rg);
    L.rr(s, { x: X0, y, w: lw, h: rh, fill: ok ? C.white : C.altRow, line: ok ? C.border : C.dark, r: 0.06 });
    L.text(s, k, { x: X0 + 0.1, y, w: 1.4, h: rh, size: 14, bold: true, color: C.navy, margin: 0 });
    L.text(s, gt, { x: X0 + 1.55, y, w: 2.4, h: rh, size: 14, color: C.ink, margin: 0 });
    L.text(s, got, { x: X0 + 4.0, y, w: 2.4, h: rh, size: 14, color: C.ink, margin: 0 });
    verdict(s, ok, { x: X0 + lw - 0.84, y: y + (rh - 0.34) / 2 });
  });
  L.text(s, "제안이 둘 이상인 상담에서 다른 안내를 고르는 실수가 남음(응답 엄격 일치 37 / 48의 이유)",
    { x: X0, y: 6.28, w: lw, h: 0.7, size: 14, color: C.slate, margin: 0, valign: "top" });

  sectionLabel(s, "C-20260310-018, 불만이 없는 주소 변경 문의", { x: rx, y: 1.9, w: rw });
  L.text(s, "답이 없어야 하는 문서: 불만이 나오면 잘못 뽑은 것", { x: rx, y: 2.36, w: rw, h: 0.28, size: 14, bold: true,
    color: C.slate, margin: 0 });
  const cases = [
    ["v1 설명", [["Complaint {cause: \"이사\"}", false], ["Proposal 2개: 수령지 직접 변경 방법(수용), 후속 안내를 영업점 방식으로(수용)", false]]],
    ["v2 설명(좁힘)", [["Complaint 없음", true], ["Proposal 1개: 앱에서 본인 인증하고 수령지를 직접 바꾸는 방법, 수용, "
      + "이유 \"집에서 바로 할 수 있는 쪽이 편해서요\"", true]]],
  ];
  let cy = 2.7;
  cases.forEach(([name, items]) => {
    const h = 1.62;
    L.rr(s, { x: rx, y: cy, w: rw, h, fill: name.startsWith("v2") ? C.tint : C.white, line: name.startsWith("v2") ? C.blue : C.border,
      r: 0.06 });
    tag(s, name, { x: rx + 0.1, y: cy + 0.1, w: 1.6, h: 0.32, fill: name.startsWith("v2") ? C.blue : C.slate });
    items.forEach(([t, ok], k) => {
      const iy = cy + 0.5 + k * 0.54;
      L.text(s, t, { x: rx + 0.15, y: iy, w: rw - 1.15, h: 0.52, size: 14, color: C.ink, margin: 0 });
      verdict(s, ok, { x: rx + rw - 0.86, y: iy + 0.08 });
    });
    cy += h + 0.12;
  });
  L.text(s, "v1의 두 번째 제안은 절차 안내라 틀림. 정답표 제안은 1개", { x: rx, y: 6.18, w: rw, h: 0.8, size: 14, color: C.slate,
    margin: 0, valign: "top" });
  band(s, "한 건씩 맞춰 보면 어떤 설명이 넓은지 보임. 답이 없어야 하는 문서가 있어야 잘못 뽑기를 찾음",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, MEASURED + ", LLMEntityRelationExtractor와 GraphPruning, 정답: 강사용 상담근거 대조표(v3)");
  return s;
}

// 단계 ④-2 채우기 시험: 전체 지표와 설명 고치기
async function createStep4b() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 단계 ④ 채우기 시험(2) 전체 지표와 설명 고치기",
    lead: "48건 지표로 보고 잘못 뽑기가 많은 타입의 설명을 고쳐 ③으로 돌아감 — 한 번 고치자 불만 오탐이 22건에서 4건으로",
    notes: "v1은 처음 쓴 설명, v2는 시험 결과를 보고 좁힌 설명임. 불만 오탐은 불만이 없는 상담 24건 중 Complaint를 만든 수, 제안 노드 수는 "
      + "48건에서 만든 Proposal 합계, 응답 일치는 뽑은 응답이 정답 하나뿐인 기록 수임. 설명 몇 줄을 바꾸자 오탐과 작은 안내를 제안으로 뽑는 "
      + "일이 크게 줄었음. 남은 문제는 응답 엄격 일치 37 / 48과 불만 오탐 4건이며, 오탐 4건은 '종이 영수증이 없어 불편'처럼 고객이 실제로 "
      + "불편을 말한 경우라 정답 기준을 다시 볼 대상임.",
  });
  const lw = 7.3, rx = X0 + lw + 0.3, rw = CW - lw - 0.3;
  sectionLabel(s, "상담 48건, 정답표와 비교", { x: X0, y: 1.9, w: lw, fill: C.dark });
  L.box(s, { x: X0 + 3.0, y: 2.44, w: 0.3, h: 0.18, fill: C.pill, line: null });
  L.text(s, "v1 설명", { x: X0 + 3.38, y: 2.36, w: 1.0, h: 0.32, size: 14, color: C.slate, margin: 0 });
  L.box(s, { x: X0 + 4.4, y: 2.44, w: 0.3, h: 0.18, fill: C.blue, line: null });
  L.text(s, "v2 설명(좁힘)", { x: X0 + 4.78, y: 2.36, w: 1.6, h: 0.32, size: 14, color: C.slate, margin: 0 });
  const mets = [
    ["불만을 잘못 뽑음", "불만 없는 24건 중, 낮을수록 좋음", 22, 4, 24],
    ["제안 노드 수", "48건 합계, 낮을수록 좋음", 87, 56, 87],
    ["응답이 정답과 같음", "48건 중, 높을수록 좋음", 31, 37, 48],
    ["재검토 조건을 잘못 뽑음", "조건 없는 29건 중, 낮을수록 좋음", 6, 0, 29],
    ["이전 상담 연결을 뽑음", "연결 있는 36건 중, 높을수록 좋음", 34, 36, 36],
  ];
  const my0 = 2.78, mh = 0.74, mg = 0.08, bx = X0 + 3.0, bmax = 3.4;
  mets.forEach(([name, sub, v1, v2, max], i) => {
    const y = my0 + i * (mh + mg);
    L.rr(s, { x: X0, y, w: lw, h: mh, fill: C.white, line: C.border, r: 0.06 });
    L.text(s, name, { x: X0 + 0.12, y: y + 0.06, w: 2.85, h: 0.3, size: 14, bold: true, color: C.navy, margin: 0 });
    L.text(s, sub, { x: X0 + 0.12, y: y + 0.38, w: 2.85, h: 0.3, size: 14, color: C.slate, margin: 0 });
    [[v1, C.pill, 0.14], [v2, C.blue, 0.42]].forEach(([v, col, off]) => {
      const w = Math.max(0.05, (bmax * v) / max);
      L.box(s, { x: bx, y: y + off, w, h: 0.2, fill: col, line: null });
      L.text(s, String(v), { x: bx + w + 0.06, y: y + off - 0.06, w: 0.6, h: 0.3, size: 14, bold: col === C.blue, color: C.ink,
        margin: 0 });
    });
  });

  sectionLabel(s, "고친 설명(description)", { x: rx, y: 1.9, w: rw });
  const pairs = [
    ["Complaint", "고객이 말한 불만과 그 원인", "불만이나 불편을 분명히 말한 경우만. 단순 문의 목적, 개인 사정(이사, 지출 감소), 궁금증은 아님"],
    ["Proposal", "상담사가 한 제안과 고객의 응답", "고객이 받아들이거나 거절할 수 있는 구체적 대안만. '확인해 드릴게요' 같은 절차 안내는 아님, 보통 1개"],
  ];
  let py = 2.42;
  pairs.forEach(([name, v1, v2]) => {
    const h = 1.5;
    L.rr(s, { x: rx, y: py, w: rw, h, fill: C.white, line: C.border, r: 0.06 });
    tag(s, name, { x: rx + 0.1, y: py + 0.1, w: 1.4, h: 0.32, fill: C.navy });
    s.addText([
      { text: `v1: ${v1}`, options: { fontSize: fs(14), color: C.slate, breakLine: true } },
      { text: `v2: ${v2}`, options: { fontSize: fs(14), bold: true, color: C.navy } },
    ], { x: rx + 0.15, y: py + 0.48, w: rw - 0.3, h: h - 0.54, fontFace: FONT, valign: "top", margin: 0, isTextBox: true,
      paraSpaceAfter: 4 });
    py += h + 0.12;
  });
  L.rr(s, { x: rx, y: 5.66, w: rw, h: 1.32, fill: C.altRow, line: C.border, r: 0.06 });
  s.addText([
    { text: "남은 문제", options: { fontSize: fs(14), bold: true, color: C.navy, breakLine: true } },
    { text: "응답 엄격 일치 37 / 48: 제안이 여럿이면 다른 안내를 고름", options: { fontSize: fs(14), color: C.ink, breakLine: true } },
    { text: "불만 오탐 4건: '종이 영수증이 없어 불편'처럼 실제 불편 발화 → 정답 기준을 다시 볼 대상",
      options: { fontSize: fs(14), color: C.ink } },
  ], { x: rx + 0.15, y: 5.66, w: rw - 0.3, h: 1.32, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true });
  band(s, "결론: 이름보다 설명이 추출 품질을 좌우함. 지표가 기준에 닿을 때까지 ③과 ④를 되풀이",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, MEASURED + ", LLMEntityRelationExtractor와 GraphPruning, 정답: 강사용 상담근거 대조표(v3)");
  return s;
}

// 단계 ⑤ 고정과 그 뒤
async function createStep5() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 단계 ⑤ 고정과 그 뒤",
    lead: "시험을 통과한 스키마 초안을 GraphSchema.save()로 파일에 고정하고, 인덱싱은 그 파일만 읽음",
    notes: "상담 스키마 초안 v2로 저장과 다시 읽기를 해 보았음(사람의 최종 승인 전이라 프로젝트에는 저장하지 않고 작업 폴더에서 시연). 다시 읽은 "
      + "스키마는 저장 전과 같았고, Neo4j 서버 없이 됨. additional_* 세 값이 False라 인덱싱 때 목록 밖 노드 타입과 관계는 가지치기가 지움. "
      + "스키마나 원천이 바뀌면 새 세대로 다시 인덱싱하며, 상담 원문을 v3로 고쳤을 때 새 세대를 만들어 상담 48청크만 새로 임베딩하고 나머지 170청크는 "
      + "재사용했음. 혜택과 약관은 ②까지 했음. 혜택은 질문을 넣자 제외 대상(Exclusion)이 핵심이 되어 후보가 거의 초안이 되고, 약관은 이름이 "
      + "흩어져 조항 구조 초안을 사람이 먼저 그리는 쪽이 맞아 보임.",
  });
  const c1 = { x: X0, w: 5.6 }, c2 = { x: X0 + 5.9, w: 4.75 }, c3 = { x: X0 + 10.95, w: CW - 10.95 };
  sectionLabel(s, "저장과 다시 읽기(실측)", { x: c1.x, y: 1.9, w: c1.w, fill: C.dark });
  L.codeBox(s, [
    "schema = GraphSchema.model_validate(초안)",
    "schema.save(\"graph_schema_consult.json\")",
    "again = GraphSchema.from_file(",
    "    \"graph_schema_consult.json\")",
    "again == schema        # True",
  ], { x: c1.x, y: 2.42, w: c1.w, h: 1.86, size: 14 });
  const res = ["노드 타입 4", "관계 5", "패턴 5", "제약 1", "additional_* 3개 모두 False"];
  let rx0 = c1.x, ry0 = 4.42;
  res.forEach((t) => {
    const w = 0.3 + t.length * 0.13;
    if (rx0 + w > c1.x + c1.w) { rx0 = c1.x; ry0 += 0.44; }
    tag(s, t, { x: rx0, y: ry0, w, h: 0.36, fill: C.tint, color: C.navy });
    rx0 += w + 0.1;
  });
  L.text(s, "Neo4j 서버 없이 됨. 상담 초안은 사람의 최종 승인 전이라 작업 폴더에서 시연함",
    { x: c1.x, y: 5.38, w: c1.w, h: 0.62, size: 14, color: C.slate, margin: 0, valign: "top" });

  sectionLabel(s, "고정의 뜻", { x: c2.x, y: 1.9, w: c2.w });
  L.rr(s, { x: c2.x, y: 2.42, w: c2.w, h: 2.95, fill: C.white, line: C.border, r: 0.06 });
  bullets(s, [
    "목록 밖 노드 타입과 관계는 가지치기가 지움(additional_* False)",
    "스키마나 원천이 바뀌면 새 세대로 다시 인덱싱",
    "실제 예: 상담 원문 v3를 반영할 때 새 세대 gen-d3v3-20261018을 만들고 상담 48청크만 새로 임베딩, 170청크는 재사용",
  ], { x: c2.x + 0.15, y: 2.56, w: c2.w - 0.3, h: 2.7, gap: 12 });
  // 인덱싱이 이 파일을 읽는 자리(1쪽 인덱싱 줄과 같은 순서)
  L.text(s, "인덱싱이 이 파일을 읽는 곳", { x: c2.x, y: 5.5, w: c2.w, h: 0.3, size: 14, bold: true, color: C.navy, margin: 0 });
  chipFlow(s, [{ t: "GraphSchema\n파일", style: "tint" }, { t: "④ 추출", style: "navy" }, { t: "가지치기", style: "navy" }],
    { x: c2.x, y: 5.86, w: c2.w, h: 0.72, gap: 0.3, size: 14 });
  L.text(s, "추출 프롬프트의 허용 목록과 가지치기 기준으로 함께 씀", { x: c2.x, y: 6.62, w: c2.w, h: 0.36, size: 14, color: C.slate,
    margin: 0 });

  sectionLabel(s, "문서 종류별 진행", { x: c3.x, y: 1.9, w: c3.w });
  const docs = [
    ["상담", "① ~ ④ 완료, ⑤는 사람의 최종 승인 남음"],
    ["혜택", "②까지. 질문을 넣자 Exclusion 3 → 25건, 후보가 거의 그대로 초안"],
    ["약관", "②까지. 이름 76%가 1건에서만 나옴 → 조항 구조 초안을 사람이 먼저"],
  ];
  const dh = 1.44, dg = 0.12;
  docs.forEach(([n, t], i) => {
    const y = 2.42 + i * (dh + dg);
    L.rr(s, { x: c3.x, y, w: c3.w, h: dh, fill: i === 0 ? C.tint : C.white, line: i === 0 ? C.blue : C.border, r: 0.06 });
    tag(s, n, { x: c3.x + 0.1, y: y + 0.1, w: 0.8, h: 0.32, fill: C.navy });
    L.text(s, t, { x: c3.x + 0.12, y: y + 0.48, w: c3.w - 0.24, h: dh - 0.54, size: 14, color: C.ink, margin: 0, valign: "top" });
  });
  band(s, "결론: 다섯 단계는 문서와 상관없이 같고, 문서 성격에 따라 LLM 후보를 그대로 쓰는 비중과 사람 판단의 비중이 달라짐",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, MEASURED + ", 인덱서 세대 gen-d3v3-20261018(청크 218개 중 48개 새 임베딩)");
  return s;
}

async function main() {
  L.createDeck();
  // ONLY=schema: 7가지 장표만 한 장짜리 덱으로 만듦(사용자가 직접 고친 덱을 덮어쓰지 않고 붙여 넣게 하려는 용도)
  if (process.env.ONLY === "schema") {
    await createSlideSchema();
  } else if (process.env.ONLY === "storecompare") {
    // 그래프DB 구축 저장소 구성 비교(별도 파일): 1쪽 4가지 안 비교, 2쪽 1-b 인덱싱 파이프라인
    await createSlideStoreCompare();
    await createSlidePipeline1b();
  } else if (process.env.ONLY === "docprompt") {
    // v11: 사용자가 덱을 직접 고치는 중이라 소스 문서 프롬프트 장표 1장만 따로 만들어 끝에 붙임
    await createSlideDocPrompt();
  } else if (process.env.ONLY === "steps") {
    // v10: 사용자가 덱을 직접 고치는 중이라 단계별 예시 6장만 따로 만들어 붙여 넣게 함
    for (const f of [createStep1, createStep2, createStep3, createStep4a, createStep4b, createStep5]) await f();  // v10: 단계별 예시
  } else {
    await createSlide01();
    await createSlideSchema();
    await createSlide02();
    await createSlidePrompt();  // v8: 3쪽(변환 규칙) 바로 뒤
    await createSlideGuide();  // v9: 5쪽 권고 절차(옛 createSlide03 대체)
    for (const f of [createStep1, createStep2, createStep3, createStep4a, createStep4b, createStep5]) await f();  // v10: 단계별 예시
  }
  const out = process.argv[2] || path.join(__dirname, "그래프스키마도출.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
