// KG 구축 K4 적재 장표 2장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "K4적재.pptx");

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
    title: "KG 구축 K4 적재",
    lead: "보관해 둔 추출 결과를 Neo4j에 쓰고, 검색용 청크와 같은 ID의 청크 노드로 이음",
    notes: "K4는 K2와 K3에서 파일로 보관해 둔 추출 결과를 Neo4j에 쓰는 단계입니다. 쓰기 전에 세 가지를 덧붙입니다. 첫째, "
      + "검색용 청크마다 라벨이 Chunk인 청크 노드를 하나 만듭니다. 청크 노드의 chunk_id는 검색엔진의 chunk_id와 "
      + "같습니다. 추출 단위는 추출할 때만 쓰고 노드로 남기지 않습니다. 둘째, 모든 노드에 세대와 실행 표시를 붙입니다. 셋째, "
      + "뽑힌 엔티티마다 그 단위가 나온 청크 노드로 FROM_CHUNK 관계를 만듭니다. 조항이 두 청크에 걸치면 관계도 두 개입니다."
      + "\n그래서 검색엔진이 청크 하나를 찾으면, 같은 chunk_id의 청크 노드를 바로 찾고, FROM_CHUNK를 거꾸로 따라가 그 청크에서 나온 엔티티를 모두 얻습니다.\nK4는 쓰기만 합니다. 여러 단위에서 같은 약관 "
      + "문서 노드가 나와도 그대로 여러 개 쓰고, 합치는 일은 다음 단계 K5가 합니다.",
  });

  const TOP = 2.4, END = 6.15;  // 위 구간 세로 범위(머리 띠 아래부터)

  // 왼쪽: 입력
  const IW = 3.3;
  L.darkBadge(s, "입력 (kg_prepared.json)", { x: X0, y: 1.9, w: IW, h: 0.4, size: 16 });
  const inputs = [
    ["unit_id", "D3_C-20260501-003_…_0000"],
    ["doc_id, doc_type", "D3_C-20260501-003, consult_log"],
    ["chunk_ids", "이 단위가 나온 검색용 청크 ID"],
    ["text", "추출 단위 본문"],
    ["graph", "K2와 K3 결과 (노드 6, 관계 5)"],
  ];
  const IP = (END - TOP + 0.08) / inputs.length, IH = IP - 0.08;
  inputs.forEach((lines, i) => {
    richCard(s, lines, { x: X0, y: TOP + i * IP, w: IW, h: IH, fill: i === 4 ? C.tint : C.altRow,
      line: i === 4 ? C.blue : C.border, color: i === 4 ? C.navy : C.ink, align: "left", titleSize: 15, size: 14 });
  });

  // 가운데: K4가 하는 일
  const MX = X0 + IW + 0.3, MW = 3.6;
  L.arrow(s, { x1: X0 + IW + 0.03, y1: (TOP + END) / 2, x2: MX - 0.03, y2: (TOP + END) / 2, color: C.navy, width: 2.5 });
  L.darkBadge(s, "K4가 하는 일", { x: MX, y: 1.9, w: MW, h: 0.4, size: 16, fill: C.navy });
  const steps = [
    ["청크 노드 만들기", "라벨 Chunk. 검색용 청크마다 1개"],
    ["모든 노드에 세대 표시", "generation, run_id 속성"],
    ["FROM_CHUNK로 잇기", "엔티티마다 단위가 나온 청크로 관계"],
  ];
  const SH = 0.86, SP = 0.96;
  steps.forEach(([t, b], i) => {
    const y = TOP + i * SP;
    L.rr(s, { x: MX, y, w: MW, h: SH, fill: C.white, line: C.border });
    L.numBadge(s, i + 1, { x: MX + 0.12, y: y + 0.13, size: 0.36, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: MX + 0.55, y: y + 0.07, w: MW - 0.65, h: 0.42, size: 16, color: C.navy, bold: true });
    L.text(s, b, { x: MX + 0.15, y: y + 0.48, w: MW - 0.3, h: 0.34, size: 14, color: C.body });
  });
  const WY = TOP + 3 * SP;
  richCard(s, ["Neo4jWriter로 한 번에 쓰기", "노드는 새로 만듦 (합치지 않음)"], { x: MX, y: WY, w: MW, h: END - WY,
    fill: C.navy, line: null, color: C.white, titleSize: 16, size: 14 });

  // 오른쪽: Neo4j에 남는 모양
  const GX = MX + MW + 0.3, GW = XR - GX;
  L.arrow(s, { x1: MX + MW + 0.03, y1: (TOP + END) / 2, x2: GX - 0.03, y2: (TOP + END) / 2, color: C.navy, width: 2.5 });
  L.headerBar(s, "Neo4j에 남는 모양 (상담 C-20260501-003)", { x: GX, y: 1.9, w: GW, h: 0.4, size: 16, accent: true });

  // 엔티티 3개와 추출 관계
  const EG = 0.3, EW = (GW - 2 * EG) / 3, EY = 2.85, EH = 0.8;
  const ents = [["Consultation", "C-20260501-003"], ["Proposal", "주문 내역 화면 대조"],
    ["ReconsiderCondition", "다음 명세서 나올 때"]];
  const ex = (i) => GX + i * (EW + EG);
  ents.forEach((lines, i) => richCard(s, lines, { x: ex(i), y: EY, w: EW, h: EH, fill: C.white, line: C.border,
    color: C.ink, titleSize: 15, size: 14 }));
  ["HAS_PROPOSAL", "RECONSIDER_WHEN"].forEach((rel, i) => {
    const gx = ex(i) + EW;
    L.arrow(s, { x1: gx + 0.02, y1: EY + EH / 2, x2: gx + EG - 0.02, y2: EY + EH / 2, color: C.slate, width: 1.5 });
    L.text(s, rel, { x: gx + EG / 2 - 1.1, y: EY - 0.42, w: 2.2, h: 0.36, size: 14, color: C.slate, bold: true,
      align: "center" });
  });

  // 청크 노드와 FROM_CHUNK
  const KW = 5.6, KX = GX + (GW - KW) / 2, KY = 4.25, KH = 0.95;
  ents.forEach((_, i) => {
    const cx = ex(i) + EW / 2, tx = KX + KW / 2 + (i - 1) * 1.6;
    L.arrow(s, { x1: cx, y1: EY + EH + 0.03, x2: tx, y2: KY - 0.03, color: C.blue, width: 1.75 });
  });
  L.text(s, "FROM_CHUNK", { x: KX + KW / 2 + 0.1, y: 3.82, w: 1.6, h: 0.36, size: 14, color: C.blue, bold: true });
  richCard(s, ["청크 노드 (라벨 Chunk)", "chunk_id: D3_C-20260501-003_…_0000",
    "검색용 청크와 1대1, 추출 단위는 남기지 않음"], { x: KX, y: KY, w: KW, h: KH, fill: C.tint, line: C.blue,
    color: C.navy, titleSize: 15, size: 14 });

  // 검색엔진 문서와 점선 연결
  const DY = END - 0.5;
  L.arrow(s, { x1: KX + KW / 2, y1: KY + KH + 0.03, x2: KX + KW / 2, y2: DY - 0.03, color: C.slate, width: 1.5,
    dash: "dash", head: "none" });
  L.text(s, "chunk_id가 같음", { x: KX + KW / 2 + 0.12, y: KY + KH + 0.02, w: 3.6,
    h: DY - KY - KH - 0.04, size: 14, color: C.slate });
  L.card(s, "검색엔진 문서 (chunk_id: D3_C-20260501-003_…_0000)", { x: KX, y: DY, w: KW, h: 0.5, fill: C.altRow,
    line: C.border, color: C.ink, size: 14, dash: "dash" });

  // 아래: 규칙 카드 4개
  const rules = [
    ["쓰기만 하고 합치지 않음", "같은 값의 노드가 여러 개여도 그대로 씀. 합치기는 K5"],
    ["세대마다 따로", "모든 노드에 generation. 세대끼리 섞이지 않음"],
    ["조항이 겹치면 청크 2개로 이음", "약관 제16조 엔티티는 두 청크 노드에 FROM_CHUNK"],
    ["증분 색인 때 옛 노드는 잠시 남김", "새 노드를 먼저 쓰고, 옛 청크 노드는 S3 뒤 K7에서 지움"],
  ];
  const RG = 0.2, RCW = (CW - 3 * RG) / 4, RY = END + 0.25, RCH = L.BODY_BOTTOM - RY;
  rules.forEach(([t, b], i) => {
    const x = X0 + i * (RCW + RG);
    L.rr(s, { x, y: RY, w: RCW, h: RCH, fill: C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.12, y: RY + 0.15, size: 0.36, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: x + 0.55, y: RY + 0.06, w: RCW - 0.65, h: 0.55, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.15, y: RY + 0.64, w: RCW - 0.3, h: RCH - 0.7, size: 14, color: C.body, valign: "top" });
  });
}

// kg_build.py apply() 원문 발췌 — 줄 나눔만 장표 폭에 맞게 바꾸고, 생략은 …, 끝의 # 주석 일부는 장표용. §…§은 굵게
const CODE_APPLY = String.raw`nodes, rels, merge_keys = [], [], set()
chunk_node = lambda cid: f"{generation}|{cid}|{run_id}"
for c in prepared["chunks"]:                 # 검색용 청크마다 1개
    nodes.append(Neo4jNode(id=§chunk_node(c["chunk_id"])§, label="Chunk",
        properties={"generation": generation, "run_id": run_id,
        "chunk_id": c["chunk_id"], "doc_id": c["doc_id"],
        "doc_type": c["doc_type"], "text": c["text"]}))
for u in prepared["units"]:
    if "graph" not in u:                     # 추출 실패 단위는 건너뜀
        continue
    graph = Neo4jGraph.model_validate(u["graph"])
    for n in graph.nodes:
        n.properties = {**(n.properties or {}),
                        "generation": generation, "run_id": run_id}
        nodes.append(n)
        for cid in dict.fromkeys(u["chunk_ids"]):  # 조항이 겹치면 청크 2개
            §rels.append(Neo4jRelationship(type="FROM_CHUNK",§
                §start_node_id=n.id, end_node_id=chunk_node(cid)))§
        …                                    # K5에서 합칠 값 모으기
    rels.extend(graph.relationships)          # LLM이 뽑은 관계를 추가함
asyncio.run(Neo4jWriter(driver).run(
    Neo4jGraph(nodes=nodes, relationships=rels)))`.split("\n");

const CODE_NODE = String.raw`(:Chunk {
  chunk_id: "D3_C-20260501-003_3415…_0000",
  doc_id: "D3_C-20260501-003", doc_type: "consult_log",
  generation: "gen-sample-005-dbe57d45",
  run_id: "sample-005@20261023135905",
  text: "…"})`.split("\n");

const CODE_QUERY = String.raw`MATCH (c:Chunk {generation: $g, chunk_id: $chunk_id})
MATCH (e)-[:FROM_CHUNK]->(c)
RETURN e
// 결과: Consultation 2, Proposal 2, Complaint 1,
//       ReconsiderCondition 1`.split("\n");

async function createSlide02() {
  const s = L.newSlide({
    title: "K4 적재 코드 (kg_build.py)",
    lead: "검색용 청크마다 청크 노드를 만들고 엔티티를 단위가 나온 청크에 FROM_CHUNK로 이은 뒤, Neo4jWriter로 한 번에 씀",
    notes: "코드는 먼저 검색용 청크마다 청크 노드를 하나씩 만듭니다. 그다음 단위를 하나씩 돌며 노드와 관계를 목록에 "
      + "모읍니다. 추출 실패로 그래프가 없는 단위는 건너뜁니다. 엔티티마다 세대와 실행 표시를 붙인 뒤, 그 단위가 나온 "
      + "청크 노드로 FROM_CHUNK 관계를 더합니다. LLM이 뽑은 관계도 그대로 "
      + "더합니다. 다 모으면 Neo4jWriter를 한 번 불러 씁니다.\n오른쪽 가운데 질의가 검색 때 그래프로 넘어가는 길입니다. "
      + "검색엔진이 돌려준 chunk_id로 청크 노드를 바로 찾습니다. 예시 상담의 chunk_id로 조회하면 상담 노드 2개, 제안 2개, "
      + "불만 1개, 재검토 조건 1개가 나옵니다. v0 표본 전체 재색인에서는 추출 단위 24개에서 엔티티 110개가 나왔고, "
      + "청크 노드 10개와 함께 노드 120개, 관계 212개를 한 번에 썼습니다.",
  });

  const LW = 8.05, RX = X0 + LW + 0.3, RW = XR - RX;
  codeBoxBold(s, CODE_APPLY, { x: X0, y: 1.9, w: LW, h: 6.05, size: 14, title: "apply()의 K4 부분 (kg_build.py 발췌)" });
  L.codeBox(s, CODE_NODE, { x: RX, y: 1.9, w: RW, h: 2.75, size: 14, title: "적재된 청크 노드 (Neo4j 조회, 일부)" });
  L.codeBox(s, CODE_QUERY, { x: RX, y: 4.75, w: RW, h: 1.85, size: 14,
    title: "검색이 찾은 chunk_id로 엔티티 찾기 (조회 예시)" });
  richCard(s, ["v0 표본 전체 재색인 K4", "추출 단위 24개 → 노드 120 (청크 노드 10)", "관계 212 (FROM_CHUNK 120, 추출 92)"],
    { x: RX, y: 6.7, w: RW, h: 1.25, fill: C.blue, line: null, color: C.white, titleSize: 16, size: 15 });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlide01, createSlide02]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
