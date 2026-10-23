// KG 구축 K5 병합 장표 2장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "K5병합.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 14,
  titleSize = 15, align = "center", r = 0.08, dash }) {
  L.rr(s, { x, y, w, h, fill, line, r, dash });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i === 0, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  // 왼쪽 정렬일 때는 글자가 테두리에 붙지 않게 안쪽 여백을 넓힘(pptxgenjs 여백 단위는 포인트)
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign: "middle", margin: align === "left" ? [10, 10, 3, 3] : 0.05,
    isTextBox: true, paraSpaceAfter: 1 });
}

// 코드 상자: lib.codeBox와 같은 모양에 §…§ 구간만 굵게(파이썬 ** 연산자와 겹치지 않게 § 사용)
function codeBoxBold(s, lines, { x, y, w, h, size = 14, title }) {
  L.rr(s, { x, y, w, h, fill: C.altRow, line: C.border, r: 0.06 });
  let top = y + 0.08;
  if (title) {
    L.text(s, title, { x: x + 0.12, y: top, w: w - 0.24, h: 0.34, size: 14, color: C.sub, bold: true });
    top += 0.36;
  }
  const runs = [];
  lines.forEach((line, li) => {
    const parts = line.split("§");
    parts.forEach((t, pi) => {
      const last = pi === parts.length - 1;
      if (t === "" && !last) return;
      runs.push({ text: t, options: { bold: pi % 2 === 1, breakLine: last && li < lines.length - 1 } });
    });
  });
  s.addText(runs, { x: x + 0.12, y: top, w: w - 0.24, h: y + h - top - 0.06, fontFace: FONT, fontSize: fs(size),
    color: C.ink, valign: "top", margin: 0.02, isTextBox: true, paraSpaceAfter: 0, lineSpacingMultiple: 1.05 });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "KG 구축 K5 병합",
    lead: "노드를 합칠 때 사용 하는 스키마의 고유 속성 값이 같은 노드를 하나로 합쳐, 여러 추출 단위에 흩어진 같은 대상을 한 노드로 모음",
    notes: "앞 장의 원리가 실제로 어떻게 나타나는지 봅니다. K4는 쓰기만 하기 때문에, 약관 조항 16개에서 각각 뽑힌 약관 문서 "
      + "노드 16개가 그대로 들어가 있습니다. K5는 버전 값이 같은 이 노드들을 하나로 합칩니다. 혜택 안내는 상품 ID, 상담 기록은 "
      + "상담 번호가 같은 노드를 합칩니다. 고유 속성이 없는 조항이나 제안 노드는 합치지 않습니다.\n합칠 때 관계도 남는 "
      + "노드로 옮깁니다. 그래서 합쳐진 약관 문서 노드는 조항 16개와 이어지고, 근거 청크 노드 2개와 이어집니다. 같은 청크로 가는 관계는 하나로 합쳐집니다. 상담 "
      + "예시에서는 다른 상담이 앞 상담을 가리키며 만든 번호만 있는 노드와, 그 상담 본문에서 뽑힌 노드가 하나로 합쳐져 이전 "
      + "상담과 다음 상담이 실제로 이어집니다.",
  });

  const END = 6.15;

  // 왼쪽: 합치는 기준
  const LW = 4.2;
  L.darkBadge(s, "합치는 기준: 스키마의 고유 속성", { x: X0, y: 1.9, w: LW, h: 0.4, size: 16 });
  const keys = [["약관", "TermsDocument.version"], ["혜택 안내", "ProductGuide.product_id"],
    ["상담 기록", "Consultation.record_id"]];
  keys.forEach((lines, i) => richCard(s, lines, { x: X0, y: 2.4 + i * 0.95, w: LW, h: 0.85, fill: C.tint,
    line: C.blue, color: C.navy, align: "left", titleSize: 16, size: 15 }));
  richCard(s, ["고유 속성이 없는 라벨은 합치지 않음", "Clause, Proposal 등"], { x: X0, y: 5.3, w: LW, h: END - 5.3,
    fill: C.white, line: C.slate, color: C.ink, align: "left", titleSize: 15, size: 14, dash: "dash" });

  // 오른쪽 공통 배치: 합치기 전 | mergeNodes 화살표 | 합친 뒤
  const RX0 = X0 + LW + 0.4, RW = XR - RX0, BW = 4.3, MWID = 1.6, AX = RX0 + BW + MWID, AW = XR - AX;
  const mergeArrow = (y) => {
    L.arrow(s, { x1: RX0 + BW + 0.12, y1: y, x2: AX - 0.12, y2: y, color: C.navy, width: 2.5 });
    L.text(s, "mergeNodes", { x: RX0 + BW, y: y - 0.42, w: MWID, h: 0.36, size: 14, color: C.navy, bold: true,
      align: "center" });
  };

  // 예 1. 약관 문서 노드
  L.headerBar(s, "예 1. 약관 문서 노드 (조항 16개에서 각각 뽑힘)", { x: RX0, y: 1.9, w: RW, h: 0.4, size: 16,
    accent: true });
  const R0 = 2.45, RP = 0.48, RH = 0.4, TDW = 1.95, CLW = 1.6;
  [1, 2, 3].forEach((k, i) => {
    const y = R0 + i * RP;
    L.card(s, "TermsDocument 1.2", { x: RX0, y, w: TDW, h: RH, fill: C.white, line: C.border, color: C.ink, size: 14 });
    L.arrow(s, { x1: RX0 + TDW + 0.03, y1: y + RH / 2, x2: RX0 + TDW + 0.4, y2: y + RH / 2 });
    L.card(s, `Clause (조항 ${k})`, { x: RX0 + TDW + 0.43, y, w: CLW, h: RH, fill: C.altRow, line: C.border,
      color: C.ink, size: 14 });
  });
  const CAP = R0 + 3 * RP - 0.02;
  L.text(s, "… 16쌍 (약관 문서 노드도 16개)", { x: RX0, y: CAP, w: BW, h: 0.34, size: 14, color: C.slate });
  const MID1 = R0 + (2 * RP + RH) / 2;
  mergeArrow(MID1);
  const ATDH = 0.6, ACX = AX + TDW + 0.75;
  richCard(s, ["TermsDocument", "1.2 (하나)"], { x: AX, y: MID1 - ATDH / 2, w: TDW, h: ATDH, fill: C.tint, line: C.blue,
    color: C.navy, titleSize: 15, size: 14 });
  [1, 2, 3].forEach((k, i) => {
    const y = R0 + i * RP;
    L.arrow(s, { x1: AX + TDW + 0.03, y1: MID1, x2: ACX - 0.03, y2: y + RH / 2, color: C.blue, width: 1.5 });
    L.card(s, `Clause (조항 ${k})`, { x: ACX, y, w: Math.min(CLW, XR - ACX), h: RH, fill: C.altRow, line: C.border,
      color: C.ink, size: 14 });
  });
  L.text(s, "… HAS_CLAUSE 16개, FROM_CHUNK 청크 2개", { x: AX, y: CAP, w: AW, h: 0.34, size: 14, color: C.blue,
    bold: true });

  // 예 2. 상담 노드
  const E2 = 4.3;
  L.headerBar(s, "예 2. 상담 노드 (앞 상담 참조와 본문)", { x: RX0, y: E2, w: RW, h: 0.4, size: 16, accent: true });
  const BH = 0.6, B1 = E2 + 0.52, B2 = B1 + BH + 0.08;
  richCard(s, ["Consultation C-20260302-002", "record_id만 (다른 상담의 FOLLOWS로 생김)"], { x: RX0, y: B1, w: BW, h: BH,
    fill: C.white, line: C.border, color: C.ink, titleSize: 15, size: 14 });
  richCard(s, ["Consultation C-20260302-002", "속성 5개 (그 상담 본문에서 뽑힘)"], { x: RX0, y: B2, w: BW, h: BH,
    fill: C.white, line: C.border, color: C.ink, titleSize: 15, size: 14 });
  const MID2 = (B1 + B2 + BH) / 2;
  mergeArrow(MID2);
  richCard(s, ["Consultation C-20260302-002", "속성 5개 (빈 속성이 채워짐)", "FOLLOWS 1, FROM_CHUNK 2 유지"],
    { x: AX, y: B1, w: AW, h: B2 + BH - B1, fill: C.tint, line: C.blue, color: C.navy, titleSize: 15, size: 14 });

  // 아래: 규칙 카드 2개(관계 옮김은 위 예시 그림이 보여 주고, 값 충돌 처리는 v0 한계라 README에만 둠)
  const rules = [
    ["이번에 들어온 값만", "K4가 모은 값만 검사. 관련 엔티티만 건드림"],
    ["같은 세대 안에서만", "generation이 같은 노드끼리 합침"],
  ];
  const RG = 0.2, RCW = (CW - (rules.length - 1) * RG) / rules.length, RY = END + 0.25, RCH = L.BODY_BOTTOM - RY;
  rules.forEach(([t, b], i) => {
    const x = X0 + i * (RCW + RG);
    L.rr(s, { x, y: RY, w: RCW, h: RCH, fill: C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.12, y: RY + 0.15, size: 0.36, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: x + 0.55, y: RY + 0.06, w: RCW - 0.65, h: 0.55, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.15, y: RY + 0.64, w: RCW - 0.3, h: RCH - 0.7, size: 14, color: C.body, valign: "top" });
  });
}

// kg_build.py 원문 발췌 — 줄 나눔만 장표 폭에 맞게 바꾸고(긴 if 조건은 괄호, 긴 질의 문자열은 이어 붙는 조각),
// 생략은 …, 주석 일부는 장표용. §…§은 굵게
const CODE_MERGE = String.raw`# apply() 안(K4): 합칠 값 모으기. 이번에 쓴 노드만
for c in schemas[u["doc_type"]]["schema"].constraints:
    if (c.node_type == n.label
            and n.properties.get(c.property_name) not in (None, "")):
        §merge_keys.add((n.label, c.property_name,§
                        §str(n.properties[c.property_name])))§

def k5_merge(driver, generation, keys):
    groups = 0
    for label, prop, value in sorted(keys):
        records, _, _ = driver.execute_query(
            f"MATCH (n:\`{label}\` {{generation: $g}}) "
            f"WHERE toString(n.\`{prop}\`) = $v "
            "WITH collect(n) AS ns WHERE size(ns) > 1 "
            §"CALL apoc.refactor.mergeNodes(ns, "§
            §"{properties: 'discard', mergeRels: true}) "§
            "YIELD node RETURN count(node) AS c",
            g=generation, v=value)
        groups += sum(r["c"] for r in records)
    return groups`.replace(/\\`/g, "`").split("\n");

const CODE_NODE = String.raw`(:TermsDocument {version: "1.2",
  effective_date: "2027-01-15", supersedes: "1.1"})
  -[:HAS_CLAUSE]-> 조항 노드 16개
  -[:FROM_CHUNK]-> 청크 노드 2개`.split("\n");

async function createSlide02() {
  const s = L.newSlide({
    title: "K5 병합 코드 (kg_build.py)",
    lead: "K4에서 모은 (라벨, 속성, 값)마다 같은 세대의 노드를 찾아, 2개 이상이면 APOC로 하나로 합침",
    notes: "합칠 값은 K4가 노드를 쓰면서 미리 모읍니다. 스키마의 고유 속성 제약을 보고, 이번에 쓴 노드 가운데 그 라벨이면서 "
      + "값이 있는 것만 모읍니다. k5_merge는 그 값마다 같은 세대에서 값이 같은 노드를 찾고, 두 개 이상이면 APOC의 "
      + "mergeNodes로 합칩니다.\nv0 표본 전체 재색인에서는 세 묶음이 합쳐져 엔티티가 110개에서 91개로 줄었습니다. 증분 "
      + "색인에서는 새로 쓴 엔티티 31개 가운데 5개가 이미 있던 노드와 합쳐졌습니다.",
  });

  const LW = 8.05, RX = X0 + LW + 0.3, RW = XR - RX;
  codeBoxBold(s, CODE_MERGE, { x: X0, y: 1.9, w: LW, h: 6.05, size: 14,
    title: "합칠 값 모으기(apply)와 k5_merge (kg_build.py 발췌)" });

  L.text(s, "v0 표본에서 합쳐진 묶음 (전체 재색인)", { x: RX, y: 1.9, w: RW, h: 0.38, size: 15, color: C.navy,
    bold: true });
  L.table(s, [["라벨", "고유 속성 값", "전 → 뒤"],
    ["TermsDocument", "version 1.2", { text: "16 → 1", options: { align: "center" } }],
    ["ProductGuide", "product_id D2-C021", { text: "4 → 1", options: { align: "center" } }],
    ["Consultation", "record_id C-20260302-002", { text: "2 → 1", options: { align: "center" } }]],
  { x: RX, y: 2.32, w: RW, colW: [2.0, 3.25, RW - 5.25], rowH: 0.46, size: 15 });

  L.codeBox(s, CODE_NODE, { x: RX, y: 4.35, w: RW, h: 1.75, size: 14, title: "합쳐진 약관 문서 노드 (Neo4j 조회)" });
  richCard(s, ["v0 표본 결과", "전체 재색인: 3묶음, 엔티티 110 → 91",
    "증분 색인: 3묶음, 새 엔티티 31개 중 5개가 기존 노드와 합쳐짐"], { x: RX, y: 6.25, w: RW, h: 1.7, fill: C.blue,
    line: null, color: C.white, titleSize: 16, size: 15 });
}

// 1장: 스키마 설계의 제약이 K4, K5에서 병합 기준이 되는 흐름
async function createSlidePrinciple() {
  const s = L.newSlide({
    title: "K5 병합의 원리",
    lead: "스키마 설계에서 정한 고유 속성 제약을 K4가 노드와 맞춰 보고 값을 모으면, K5가 그 값으로 같은 세대의 노드를 찾아 합침",
    notes: "병합 기준은 인덱싱이 새로 정하는 것이 아니라 스키마 설계에서 이미 정해져 넘어옵니다. 약관 스키마에는 약관 문서 "
      + "노드의 버전이 고유 속성이라는 제약이 하나 있습니다. 인덱싱은 이 제약을 읽어 두었다가, K4에서 노드를 쓸 때 노드마다 "
      + "라벨을 제약의 라벨과 비교합니다. 약관 제16조 단위에서 뽑힌 노드 네 개 가운데 라벨이 같은 것은 약관 문서 노드 "
      + "하나뿐이라, 그 노드의 버전 값만 합칠 값으로 모입니다. 조항 노드는 라벨이 달라 건너뜁니다.\nK5는 모인 값마다 같은 "
      + "세대에서 값이 같은 노드를 찾아 합칩니다. 제약은 LLM에게도 보이지만, LLM은 단위마다 따로 불려서 중복을 피할 수 "
      + "없습니다. Neo4j에도 제약을 걸지 않습니다. 걸어 두면 같은 값의 두 번째 노드를 쓰는 순간 실패하기 때문입니다. 그래서 "
      + "제약은 막는 데가 아니라 나중에 합치는 기준으로만 씁니다.",
  });

  // 위: 제약이 흘러가는 4단계
  const FG = 0.35, FW = (CW - 3 * FG) / 4, FY = 1.9, FB = 2.42, FH = 2.1;
  const flow = [
    ["① 스키마 설계 (정함)", "schema_spec.json에 정하고 graph_schema.json으로 확정",
      ['{"type": "UNIQUENESS",', ' "node_type": "TermsDocument",', ' "property_name": "version"}']],
    ["② 인덱싱 준비 (읽음)", "load_schemas()가 문서 유형별 graph_schema.json을 읽음",
      ["약관: TermsDocument.version", "혜택: ProductGuide.product_id", "상담: Consultation.record_id"]],
    ["③ K4 적재 (모음)", "노드 라벨이 제약 라벨과 같고 값이 있으면 (라벨, 속성, 값)을 모음",
      ["merge_keys = {", '  ("TermsDocument",', '   "version", "1.2")}']],
    ["④ K5 병합 (합침)", "값마다 같은 세대에서 값이 같은 노드를 찾아 2개 이상이면 mergeNodes",
      ["TermsDocument 1.2", "16개 → 1개"]],
  ];
  flow.forEach(([head, desc, code], i) => {
    const x = X0 + i * (FW + FG);
    L.darkBadge(s, head, { x, y: FY, w: FW, h: 0.42, size: 16, fill: i === 0 ? C.blue : C.navy });
    L.rr(s, { x, y: FB, w: FW, h: FH, fill: i === 0 ? C.tint : C.white, line: i === 0 ? C.blue : C.border });
    L.text(s, desc, { x: x + 0.12, y: FB + 0.06, w: FW - 0.24, h: 0.78, size: 15, color: C.ink, valign: "top" });
    L.codeBox(s, code, { x: x + 0.12, y: FB + 0.9, w: FW - 0.24, h: FH - 1.02, size: 14 });
    if (i < 3) {
      L.arrow(s, { x1: x + FW + 0.04, y1: FB + FH / 2, x2: x + FW + FG - 0.04, y2: FB + FH / 2, color: C.navy,
        width: 2.5 });
    }
  });

  // 왼쪽 아래: ③의 비교 표
  const BY = 4.8, TW = 8.2;
  L.text(s, "③의 비교: 약관 제16조 단위에서 뽑힌 노드 (제약의 node_type은 'TermsDocument')", { x: X0, y: BY, w: TW,
    h: 0.38, size: 15, color: C.navy, bold: true });
  const hit = (t) => ({ text: t, options: { color: C.blue, bold: true } });
  L.table(s, [["n.label", "c.node_type == n.label", "결과"],
    [hit("TermsDocument"), hit("참"), hit("모음 (version 1.2)")],
    ["Clause", "거짓", "건너뜀"],
    ["Requirement", "거짓", "건너뜀"],
    ["Handling", "거짓", "건너뜀"]],
  { x: X0, y: BY + 0.44, w: TW, colW: [2.2, 2.5, TW - 4.7], rowH: 0.44, size: 15 });
  L.text(s, "조항 16개 단위가 같은 키를 넣어도 set이라 키는 1개만 남음", { x: X0, y: BY + 0.44 + 5 * 0.44 + 0.12, w: TW,
    h: 0.38, size: 14, color: C.slate });

  // 오른쪽 아래: 제약을 쓰는 곳과 안 쓰는 곳
  const UX = X0 + TW + 0.35, UW = XR - UX;
  L.text(s, "제약을 쓰는 곳과 안 쓰는 곳", { x: UX, y: BY, w: UW, h: 0.38, size: 15, color: C.navy, bold: true });
  const uses = [
    ["K2 추출", "LLM에 보이지만 단위끼리 서로 몰라 중복이 생김", false],
    ["K3 가지치기", "필수 속성만 보고 고유 속성은 안 봄", false],
    ["Neo4j", "제약을 걸지 않음. 걸면 K4 쓰기가 실패함", false],
    ["K4와 K5", "실제로 쓰는 곳: 값을 모으고 합침", true],
  ];
  const UP = 0.66, UH = 0.58, PW = 1.55;
  uses.forEach(([stage, desc, on], i) => {
    const y = BY + 0.44 + i * UP;
    L.rr(s, { x: UX, y, w: UW, h: UH, fill: on ? C.tint : C.altRow, line: on ? C.blue : C.border });
    L.card(s, stage, { x: UX + 0.1, y: y + 0.1, w: PW, h: UH - 0.2, fill: on ? C.blue : C.white, line: on ? null : C.pill,
      color: on ? C.white : C.navy, size: 14, bold: true, r: 0.15 });
    L.text(s, desc, { x: UX + PW + 0.2, y, w: UW - PW - 0.3, h: UH, size: 14, color: on ? C.navy : C.body, bold: on });
  });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlidePrinciple, createSlide01, createSlide02]) await fn();  // 사용자가 원리 장표를 맨 앞으로 옮김
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
