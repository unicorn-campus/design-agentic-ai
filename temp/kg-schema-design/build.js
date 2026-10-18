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

// ------------------------------------------------------------------ 슬라이드 6(v9 추가: 사례 ① 상담 이력)
async function createSlideCase1() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 사례 ① 상담 이력: 넓게 뽑기에서 뼈대 확정까지",
    lead: "같은 상담 30건에 방법만 바꿔 보니, 역량 질문만 넣었을 때 비로소 불만, 제안, 응답, 재검토 조건이 후보로 나옴",
    notes: "우리 시스템의 상담 이력(합성 48건) 사례임. 같은 표본 30건, 같은 순서로 방법만 바꿨음. 1건씩 따로 뽑으면 같은 뜻을 다른 이름으로 "
      + "계속 만들어 노드 타입 이름이 45개까지 흩어졌고, 앞서 나온 이름을 다시 쓰라고 하면 14개로 모였지만 업무 핵심 개념은 하나도 "
      + "나오지 않았음. 상담 원문에 불만 원인, 제안, 수용과 거절, 재검토 조건 문장을 넣는 것(원문 보강)만으로도 나오지 않았음. "
      + "역량 질문과 이름 다시 쓰기를 함께 쓰면 불만(Issue)만 26건 나왔고, 역량 질문만 넣으면 네 개념이 모두 나왔지만 각각 30건 중 "
      + "1 ~ 5건뿐이었음. 그래서 빈도로 거르면 모두 버려짐. 사람이 질문 기준으로 이름을 합치고(Issue와 Complaint), 원천이 따로 있는 것을 "
      + "빼고(거래 집계는 RDB, 고객 이름과 이메일은 가명처리 대상), 근거가 약한 응답 속성과 관계는 보태서 오른쪽 뼈대를 만들었음.",
  });
  const lw = 7.0, rx = X0 + lw + 0.3, rw = CW - lw - 0.3;

  // 왼쪽: 방법 5개
  sectionLabel(s, "같은 상담 30건, 방법만 바꿔 봄", { x: X0, y: 1.9, w: lw, fill: C.dark });
  L.text(s, "방법", { x: X0, y: 2.36, w: 2.9, h: 0.28, size: 14, bold: true, color: C.slate, margin: 0 });
  L.text(s, "노드 타입 이름 수", { x: X0 + 3.0, y: 2.36, w: 2.6, h: 0.28, size: 14, bold: true, color: C.slate, margin: 0 });
  L.text(s, "업무 개념 4개 중", { x: X0 + 5.6, y: 2.36, w: 1.4, h: 0.28, size: 14, bold: true, color: C.slate,
    align: "center", margin: 0 });
  const rows = [
    ["1건씩 따로 뽑기", 45, "0"],
    ["이름 다시 쓰기\n(앞서 나온 이름을 examples로)", 14, "0"],
    ["원문 보강\n+ 이름 다시 쓰기", 38, "0"],
    ["원문 보강 + 역량 질문\n+ 이름 다시 쓰기", 10, "1"],
    ["원문 보강 + 역량 질문만", 53, "4"],
  ];
  const ry0 = 2.68, rh = 0.6, rg = 0.05, barMax = 2.1;  // 아래 설명 3줄이 결론 띠 위에서 끝나게 맞춤
  rows.forEach(([name, cnt, got], i) => {
    const y = ry0 + i * (rh + rg), best = i === rows.length - 1;
    L.rr(s, { x: X0, y, w: lw, h: rh, fill: best ? C.tint : C.white, line: best ? C.blue : C.border, r: 0.06 });
    L.text(s, name, { x: X0 + 0.12, y, w: 2.8, h: rh, size: 14, bold: true, color: C.navy, margin: 0 });
    const bw = Math.max(0.08, (barMax * cnt) / 53);
    L.box(s, { x: X0 + 3.0, y: y + rh / 2 - 0.13, w: bw, h: 0.26, fill: best ? C.blue : C.slate, line: null });
    L.text(s, String(cnt), { x: X0 + 3.0 + bw + 0.08, y, w: 0.6, h: rh, size: 15, bold: true, color: C.ink, margin: 0 });
    L.card(s, `${got} / 4`, { x: X0 + 5.75, y: y + 0.12, w: 1.1, h: rh - 0.24, fill: got === "4" ? C.blue : got === "0" ? C.altRow : C.tint,
      line: got === "0" ? C.border : null, color: got === "4" ? C.white : C.navy, size: 15, bold: true, r: 0.08 });
  });
  L.text(s, "업무 개념: 불만 원인, 제안, 수용과 거절, 재검토 조건\n원문 보강: 상담 원문에 그 문장을 넣은 판(v3)\n"
    + "역량 질문만 넣으면 네 개념이 각각 30건 중 1 ~ 5건뿐이라 빈도로 거르면 버려짐",
  { x: X0, y: 6.02, w: lw, h: 0.98, size: 14, color: C.slate, margin: 0, valign: "top" });

  // 오른쪽: 확정한 뼈대
  sectionLabel(s, "확정한 뼈대(역량 질문 기준으로 사람이 정함)", { x: rx, y: 1.9, w: rw });
  const nodeBox = (label, props, { x, y, w, h, dark = false, dash = false }) => {
    L.rr(s, { x, y, w, h, fill: dark ? C.navy : C.tint, line: dash ? C.sub : C.navy, lw: 1.5, r: 0.08, dash: dash ? "dash" : undefined });
    L.text(s, label, { x: x + 0.1, y: y + 0.04, w: w - 0.2, h: 0.32, size: 15, bold: true, color: dark ? C.white : C.navy,
      align: "center", margin: 0 });
    if (props) {
      L.text(s, props, { x: x + 0.1, y: y + 0.36, w: w - 0.2, h: h - 0.4, size: 14, color: dark ? "D9E3F5" : C.ink,
        align: "center", margin: 0, valign: "top" });
    }
  };
  const ax = rx + 0.15, aw = 2.25, bx = rx + rw - 0.15 - 2.6, bw2 = 2.6;
  nodeBox(":Consultation", "record_id (키)\nconsult_date, topic", { x: ax, y: 3.4, w: aw, h: 1.05, dark: true });
  nodeBox(":Consultation", "앞선 상담", { x: ax, y: 4.75, w: aw, h: 0.7, dash: true });
  nodeBox(":Complaint", "cause, category", { x: bx, y: 2.4, w: bw2, h: 0.78 });
  nodeBox(":Proposal", "content\ndecision, decision_reason", { x: bx, y: 3.4, w: bw2, h: 1.05 });
  nodeBox(":ReconsiderCondition", "description", { x: bx, y: 4.75, w: bw2, h: 0.7 });
  // 관계: 이름이 화살표와 겹치거나 오른쪽 밖으로 나가지 않게 선의 왼쪽 위나 옆에 둠
  L.arrow(s, { x1: ax + aw + 0.03, y1: 3.5, x2: bx - 0.03, y2: 2.85, color: C.navy, width: 1.75 });
  L.text(s, "HAS_COMPLAINT", { x: ax + aw + 0.08, y: 2.78, w: 1.7, h: 0.28, size: 14, bold: true, color: C.navy, margin: 0 });
  L.arrow(s, { x1: ax + aw + 0.03, y1: 3.92, x2: bx - 0.03, y2: 3.92, color: C.navy, width: 1.75 });
  L.text(s, "HAS_PROPOSAL", { x: ax + aw + 0.1, y: 3.6, w: bx - ax - aw - 0.2, h: 0.28, size: 14, bold: true, color: C.navy,
    align: "center", margin: 0 });
  L.arrow(s, { x1: bx + bw2 / 2, y1: 3.38, x2: bx + bw2 / 2, y2: 3.2, color: C.blue, width: 1.75 });
  L.text(s, "ADDRESSES", { x: bx + bw2 / 2 + 0.08, y: 3.15, w: 1.3, h: 0.26, size: 14, bold: true, color: C.blue, margin: 0 });
  L.arrow(s, { x1: bx + bw2 / 2, y1: 4.47, x2: bx + bw2 / 2, y2: 4.73, color: C.blue, width: 1.75 });
  L.text(s, "RECONSIDER_WHEN", { x: bx + bw2 / 2 - 2.2, y: 4.46, w: 2.12, h: 0.28, size: 14, bold: true, color: C.blue,
    align: "right", margin: 0 });
  L.arrow(s, { x1: ax + aw / 2, y1: 4.47, x2: ax + aw / 2, y2: 4.73, color: C.navy, width: 1.75 });
  L.text(s, "FOLLOWS", { x: ax + aw / 2 + 0.08, y: 4.46, w: 1.2, h: 0.28, size: 14, bold: true, color: C.navy, margin: 0 });
  L.text(s, "네이비: LLM 후보를 합침, 파랑: 사람이 보탬(관계 2개와 decision 속성)",
    { x: rx, y: 5.58, w: rw, h: 0.3, size: 14, color: C.slate, margin: 0, valign: "top" });
  L.text(s, "합침: Issue와 Complaint → Complaint, Proposal과 SUGGESTS → Proposal, Conversation과 Session → Consultation\n"
    + "뺌: Transaction(RDB 집계), Customer의 이름과 이메일(가명처리 대상), Request와 Menu(질문에 안 쓰임)",
  { x: rx, y: 5.96, w: rw, h: 1.06, size: 14, color: C.ink, margin: 0, valign: "top" });

  band(s, "결론: 드문 핵심 개념은 역량 질문만으로 넓게 뽑아야 보이고, 무엇을 살릴지는 빈도가 아니라 질문을 기준으로 사람이 정함",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, "실측: 2026-10-18, LLM Groq openai/gpt-oss-120b, neo4j-graphrag 1.22.0 SchemaFromTextExtractor, 합성 상담 이력 30건(같은 순서)");
  return s;
}

// ------------------------------------------------------------------ 슬라이드 7(v9 추가: 사례 ② 채우기 시험과 문서 종류별 차이)
async function createSlideCase2() {
  const s = L.newSlide({
    title: "1. 스키마 도출: 사례 ② 뼈대 채우기 시험과 문서 종류별 차이",
    lead: "뼈대의 이름보다 설명(description)이 추출 품질을 좌우함 — 채우기 시험으로 설명을 고쳐 가며 확정",
    notes: "왼쪽은 확정한 상담 뼈대로 48건 전체를 LLMEntityRelationExtractor와 GraphPruning으로 실제 추출하고 강사용 정답표와 비교한 결과임. "
      + "v1은 Complaint 설명이 '고객이 말한 불만과 그 원인'이라 일반 문의 고객의 문의 목적이나 사정(이사, 영수증 필요)까지 불만으로 뽑아 "
      + "24건 중 22건이 잘못 뽑혔음. v2에서 '분명히 말한 불만이나 불편만, 문의 목적과 개인 사정은 아님'으로 좁히자 4건으로 줄었음. "
      + "Proposal도 '확인해 드릴게요' 같은 절차 안내를 빼라고 하자 제안 노드가 87개에서 56개로 줄고 응답 일치가 올랐음. "
      + "오른쪽은 같은 절차를 문서 종류별로 해 본 결과임. 혜택 안내는 이름이 빨리 모이고 역량 질문(제외 대상)으로 Exclusion이 핵심 타입이 "
      + "되어 넓게 뽑은 후보가 거의 뼈대가 됨. 상담은 사람이 보태야 하고, 약관은 청크마다 조항이 달라 이름이 흩어져 조항 구조를 사람이 먼저 그리는 쪽이 맞음. "
      + "절차는 같고 문서 성격에 따라 LLM 후보와 사람 설계의 비중이 다름.",
  });
  const lw = 7.3, rx = X0 + lw + 0.3, rw = CW - lw - 0.3;

  sectionLabel(s, "뼈대 채우기 시험(상담 48건, 정답표와 비교)", { x: X0, y: 1.9, w: lw, fill: C.dark });
  // 범례
  L.box(s, { x: X0 + 3.0, y: 2.44, w: 0.3, h: 0.18, fill: C.pill, line: null });
  L.text(s, "v1 설명", { x: X0 + 3.38, y: 2.36, w: 1.0, h: 0.32, size: 14, color: C.slate, margin: 0 });
  L.box(s, { x: X0 + 4.4, y: 2.44, w: 0.3, h: 0.18, fill: C.blue, line: null });
  L.text(s, "v2 설명(좁힘)", { x: X0 + 4.78, y: 2.36, w: 1.6, h: 0.32, size: 14, color: C.slate, margin: 0 });
  const mets = [
    ["불만을 잘못 뽑음", "24건 중, 낮을수록 좋음", 22, 4, 24],
    ["제안 노드 수", "48건 합계, 낮을수록 좋음", 87, 56, 87],
    ["응답이 정답과 같음", "48건 중, 높을수록 좋음", 31, 37, 48],
    ["재검토 조건을 잘못 뽑음", "29건 중, 낮을수록 좋음", 6, 0, 29],
    ["이전 상담 연결을 뽑음", "36건 중, 높을수록 좋음", 34, 36, 36],
  ];
  const my0 = 2.78, mh = 0.62, mg = 0.07, bx = X0 + 2.85, bmax = 3.55;
  mets.forEach(([name, sub, v1, v2, max], i) => {
    const y = my0 + i * (mh + mg);
    L.rr(s, { x: X0, y, w: lw, h: mh, fill: C.white, line: C.border, r: 0.06 });
    L.text(s, name, { x: X0 + 0.12, y: y + 0.04, w: 2.7, h: 0.3, size: 14, bold: true, color: C.navy, margin: 0 });
    L.text(s, sub, { x: X0 + 0.12, y: y + 0.32, w: 2.7, h: 0.26, size: 14, color: C.slate, margin: 0 });
    [[v1, C.pill, 0.1], [v2, C.blue, 0.34]].forEach(([v, col, off]) => {
      const w = Math.max(0.05, (bmax * v) / max);
      L.box(s, { x: bx, y: y + off, w, h: 0.18, fill: col, line: null });
      L.text(s, String(v), { x: bx + w + 0.06, y: y + off - 0.06, w: 0.6, h: 0.3, size: 14, bold: col === C.blue, color: C.ink,
        margin: 0 });
    });
  });
  L.rr(s, { x: X0, y: 6.28, w: lw, h: 0.74, fill: C.tint, line: C.blue, r: 0.08 });
  L.text(s, "Complaint 설명 v1: 고객이 말한 불만과 그 원인\n"
    + "v2: 불만이나 불편을 분명히 말한 경우만. 문의 목적과 개인 사정(이사, 지출 감소)은 아님",
  { x: X0 + 0.15, y: 6.28, w: lw - 0.3, h: 0.74, size: 14, bold: true, color: C.navy, margin: 0 });

  sectionLabel(s, "문서 종류에 따라 비중이 다름", { x: rx, y: 1.9, w: rw });
  const docs = [
    ["혜택 안내", "이름이 빨리 모임(핵심 6개). 역량 질문을 넣자 제외 대상 Exclusion이 3건에서 25건으로",
      "넓게 뽑은 후보가 거의 그대로 뼈대, 사람은 합치기 위주"],
    ["상담 이력", "대화 속 행위(불만, 제안, 응답)는 30건 중 1 ~ 5건만 나옴",
      "사람이 보태고, 채우기 시험으로 설명을 다듬음"],
    ["약관", "청크마다 조항이 달라 1건에서만 나온 이름이 76%. 기한과 의무 같은 규칙 구조는 거의 안 나옴",
      "조항 구조 뼈대를 사람이 먼저 그림"],
  ];
  const dy0 = 2.38, dh = 1.18, dg = 0.1;
  docs.forEach(([name, fact, way], i) => {
    const y = dy0 + i * (dh + dg);
    L.rr(s, { x: rx, y, w: rw, h: dh, fill: C.white, line: C.border, r: 0.08 });
    L.card(s, name, { x: rx + 0.1, y: y + 0.1, w: 1.35, h: dh - 0.2, fill: C.navy, line: null, color: C.white, size: 15, bold: true,
      r: 0.06 });
    s.addText([
      { text: fact, options: { fontSize: fs(14), color: C.ink, breakLine: true } },
      { text: `→ ${way}`, options: { fontSize: fs(14), color: C.blue, bold: true } },
    ], { x: rx + 1.6, y, w: rw - 1.7, h: dh, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true, paraSpaceAfter: 4 });
  });
  L.rr(s, { x: rx, y: 6.28, w: rw, h: 0.74, fill: C.altRow, line: C.border, r: 0.08 });
  L.text(s, "표본 수: 이름 다시 쓰기 시험에서 혜택 층은 10 ~ 14건, 상담은 13 ~ 20건에서 멈춤(상한 30건 전)",
    { x: rx + 0.15, y: 6.28, w: rw - 0.3, h: 0.74, size: 14, color: C.ink, margin: 0 });

  band(s, "결론: 절차 ①~⑤는 같음. 문서 성격에 따라 LLM 후보를 그대로 쓰는 비중과 사람이 설계하는 비중이 달라짐",
    { y: 7.12, h: 0.72, size: 16 });
  sourceLine(s, "실측: 2026-10-18, Groq openai/gpt-oss-120b, neo4j-graphrag 1.22.0 LLMEntityRelationExtractor와 GraphPruning, 정답: 강사용 상담근거 대조표(v3)");
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
    await createSlidePrompt();  // v8: 3쪽(변환 규칙) 바로 뒤
    await createSlideGuide();  // v9: 5쪽 권고 절차(옛 createSlide03 대체)
    await createSlideCase1();  // v9: 6쪽 사례 ①
    await createSlideCase2();  // v9: 7쪽 사례 ②
  }
  const out = process.argv[2] || path.join(__dirname, "그래프스키마도출.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
