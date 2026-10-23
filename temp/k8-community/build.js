// KG 구축 K8 커뮤니티 요약 장표 5장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
// 코드는 hybrid-ai-lab/indexer/graphrag/v0/community.py 발췌, 실측값은 data.json(make_data.py가 활성 세대에서 뽑음)
const fs0 = require("fs");
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "K8커뮤니티요약.pptx");
const D = JSON.parse(fs0.readFileSync(path.join(__dirname, "data.json"), "utf-8"));
const n = (v) => Number(v).toLocaleString("en-US");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스(K6, K7 장표와 같은 모양)
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 14,
  titleSize = 15, align = "center", r = 0.08, dash, valign = "middle" }) {
  L.rr(s, { x, y, w, h, fill, line, r, dash });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i === 0, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  // 왼쪽 정렬일 때는 글자가 테두리에 붙지 않게 안쪽 여백을 넓힘(pptxgenjs 여백 단위는 포인트)
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign, margin: align === "left" ? [10, 10, 4, 4] : 0.05,
    isTextBox: true, paraSpaceAfter: 1 });
}

// 코드 상자: §…§ 구간만 굵게(K6, K7 장표와 같은 모양)
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

// 작은 그래프 그림용 점(원)
function dot(s, cx, cy, { fill = C.tint, line = C.blue, r = 0.17, label = "" } = {}) {
  s.addText(label, { shape: L.getPptx().shapes.OVAL, x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { color: fill },
    line: { color: line, width: 1.25 }, fontFace: FONT, fontSize: fs(14), bold: true, color: C.white,
    align: "center", valign: "middle", margin: 0, isTextBox: false });
}
function edge(s, a, b, { color = C.slate, width = 1.25, dash } = {}) {
  L.arrow(s, { x1: a[0], y1: a[1], x2: b[0], y2: b[1], color, width, dash, head: "none" });
}

// 1장: K8이 하는 일
async function slideWhat() {
  const s = L.newSlide({
    title: "2. 인덱싱: KG 구축 – K8. 커뮤니티 요약 (선택)",
    lead: "서로 촘촘히 이어진 엔티티를 Leiden으로 묶고, 묶음마다 LLM이 요약 보고서를 써서 거시 질문에 답할 재료를 만듦",
    notes: "K8은 선택 단계입니다. 지금까지의 그래프는 사실 하나를 찾는 질문에 강합니다. 할부로 산 물건을 며칠 안에 "
      + "철회하는지 물으면 기한 엔티티 하나로 답할 수 있습니다. 그런데 고객군별로 불만을 주제별로 나눠 달라는 질문은 "
      + "여러 상담을 한꺼번에 훑어 묶어야 답할 수 있습니다. 이런 질문을 거시 질문이라고 합니다.\n"
      + "K8은 거시 질문에 답할 재료를 미리 만들어 둡니다. 엔티티 그래프에서 서로 촘촘히 이어진 엔티티 묶음, 즉 커뮤니티를 "
      + "Leiden 알고리즘으로 찾고, 묶음마다 LLM이 제목, 요약, 핵심 사실을 담은 보고서를 씁니다. 보고서는 임베딩해 두어 "
      + "질문과 가까운 보고서를 찾을 수 있게 합니다. Microsoft GraphRAG의 커뮤니티 보고서와 같은 생각입니다.\n"
      + "묶는 대상은 엔티티와 그 사이 관계뿐입니다. 청크 노드를 넣으면 같은 청크에서 나온 엔티티끼리만 뭉쳐 문서 요약과 "
      + "다를 바가 없어지기 때문입니다. 엔티티가 3개 이상인 묶음만 요약하고, 구성원이 그대로인 묶음은 지난 보고서를 다시 "
      + "씁니다. 전체 재색인에서는 K6 다음, 증분 색인에서는 K7 다음에 돌립니다.",
  });

  // 위: 사실 질문과 거시 질문
  const QY = 1.9, QH = 1.25, QW = (CW - 0.3) / 2;
  richCard(s, ["사실 질문: 엔티티 하나로 답함", "「할부로 산 물건은 며칠 안에 철회하나요?」",
    "→ 기한 엔티티 「7일 이내 철회」"], { x: X0, y: QY, w: QW, h: QH, fill: C.white, line: C.border,
    align: "left", titleSize: 15, size: 14 });
  richCard(s, ["거시 질문: 여러 문서를 훑어 묶어야 답함", "「고객군별로 고객 불만을 주제별로 나눠 주세요」",
    "→ 미리 만들어 둔 커뮤니티 보고서로 답함 (K8)"], { x: X0 + QW + 0.3, y: QY, w: QW, h: QH, fill: C.tint,
    line: C.blue, color: C.navy, align: "left", titleSize: 15, size: 14 });

  // 가운데: 5단계 흐름
  const FY = QY + QH + 0.3, FG = 0.22, FW = (CW - 4 * FG) / 5, FB = FY + 0.48, FH = 1.0;
  const flow = [
    ["① 그래프 읽기", ["엔티티와 관계만", "청크 노드는 뺌"]],
    ["② Leiden 묶기", ["GDS가 촘촘한", "묶음을 찾음"]],
    ["③ 보고서 쓰기", ["LLM이 제목, 요약,", "핵심 사실을 씀"]],
    ["④ 임베딩", ["보고서를 KURE-v2로", "벡터로 바꿈"]],
    ["⑤ 적재", ["Community 노드와", "IN_COMMUNITY 관계"]],
  ];
  flow.forEach(([head, lines], i) => {
    const x = X0 + i * (FW + FG);
    const key = i === 1 || i === 2;
    L.darkBadge(s, head, { x, y: FY, w: FW, h: 0.42, size: 15, fill: key ? C.blue : C.navy });
    richCard(s, lines, { x, y: FB, w: FW, h: FH, fill: key ? C.tint : C.white, line: key ? C.blue : C.border,
      color: key ? C.navy : C.ink, titleSize: 14, size: 14 });
    if (i < 4) {
      L.arrow(s, { x1: x + FW + 0.03, y1: FB + FH / 2, x2: x + FW + FG - 0.03, y2: FB + FH / 2, color: C.navy,
        width: 2.25 });
    }
  });

  // 아래: 규칙 4개
  const rules = [
    ["엔티티만 묶음", "청크 노드를 넣으면 청크 단위로만 뭉침"],
    ["3개 이상만 요약", "엔티티 1 ~ 2개 묶음은 보고서를 쓰지 않음"],
    ["같으면 재사용", "구성원 지문이 같으면 LLM을 부르지 않음"],
    ["실행 위치", "전체 재색인은 K6 다음, 증분 색인은 K7 다음"],
  ];
  const RG = 0.2, RW = (CW - 3 * RG) / 4, RY = FB + FH + 0.3, RH = 1.2;
  rules.forEach(([t, b], i) => {
    const x = X0 + i * (RW + RG);
    L.rr(s, { x, y: RY, w: RW, h: RH, fill: C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.12, y: RY + 0.12, size: 0.34, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: x + 0.55, y: RY + 0.08, w: RW - 0.65, h: 0.42, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.15, y: RY + 0.55, w: RW - 0.3, h: RH - 0.6, size: 14, color: C.body, valign: "top" });
  });
  const BY = RY + RH + 0.2;
  richCard(s, ["선택 단계: 실행할 때 --communities 옵션으로 켬",
    "Microsoft GraphRAG의 커뮤니티 보고서와 같은 생각. 거시 질문이 없으면 꺼 둠"],
  { x: X0, y: BY, w: CW, h: L.BODY_BOTTOM - BY, fill: C.navy, line: null, color: C.white, titleSize: 15, size: 14 });
}

// 2장: Leiden 원리
async function slideLeiden() {
  const s = L.newSlide({
    title: "2. 인덱싱: KG 구축 – K8. Leiden으로 커뮤니티 찾기 (원리)",
    lead: "묶음 안 연결은 많고 묶음 사이 연결은 적게 나누는 것이 목표. 옮기기, 다듬기, 합치기를 점수가 더 오르지 않을 때까지 반복",
    notes: "좋은 나누기의 기준은 모듈성입니다. 묶음 안의 연결이 우연히 이어질 때보다 얼마나 더 많은지를 잰 점수입니다. 묶음 "
      + "안은 촘촘하고 묶음 사이는 성길수록 점수가 높습니다.\n"
      + "Leiden은 세 단계를 반복합니다. 첫째 옮기기입니다. 점 하나씩 이웃 묶음으로 옮겨 보고, 점수가 오르면 옮깁니다. 둘째 "
      + "다듬기입니다. 묶음 안을 다시 살펴, 안에서 서로 끊어진 조각이 있으면 떼어 냅니다. 이 단계가 이전 방법인 Louvain에 "
      + "없던 부분이라, Leiden은 묶음 안이 끊어진 채로 남지 않습니다. 셋째 합치기입니다. 묶음 하나를 점 하나로 보고 묶음 "
      + "사이 연결을 굵은 선 하나로 합친 뒤, 첫째 단계부터 다시 합니다. 점수가 더 오르지 않으면 끝납니다.\n"
      + "Leiden은 옮겨 보는 순서에 따라 결과가 조금 달라질 수 있습니다. 그래서 씨앗을 고정하고 병렬 처리를 하나로 두어, 같은 "
      + "그래프에서는 늘 같은 묶음이 나오게 했습니다.",
  });

  L.text(s, "좋은 나누기의 기준: 모듈성", { x: X0, y: 1.85, w: CW, h: 0.36, size: 16, color: C.navy, bold: true });
  L.text(s, "묶음 안 연결이 우연히 이어질 때보다 얼마나 더 많은가. 묶음 안은 촘촘하고 묶음 사이는 성길수록 높음",
    { x: X0, y: 2.2, w: CW, h: 0.34, size: 14, color: C.body });

  // 세 그림 패널
  const PY = 2.7, PH = 3.95, PG = 0.3, PW = (CW - 2 * PG) / 3;
  const panels = [
    ["① 옮기기", "점 하나씩 이웃 묶음으로 옮겨 보고, 점수가 오르면 옮김"],
    ["② 다듬기", "묶음 안에서 끊어진 조각은 떼어 냄 (Louvain에 없던 단계)"],
    ["③ 합치기", "묶음을 점 하나로 보고 ①부터 다시. 점수가 그대로면 끝"],
  ];
  panels.forEach(([t, b], i) => {
    const x = X0 + i * (PW + PG);
    L.rr(s, { x, y: PY, w: PW, h: PH, fill: C.white, line: C.border });
    L.darkBadge(s, t, { x: x + 0.15, y: PY + 0.15, w: 1.55, h: 0.4, size: 15, fill: i === 1 ? C.blue : C.navy });
    L.text(s, b, { x: x + 0.15, y: PY + PH - 0.78, w: PW - 0.3, h: 0.66, size: 14, color: C.body, valign: "top" });
    if (i < 2) {
      L.arrow(s, { x1: x + PW + 0.03, y1: PY + PH / 2, x2: x + PW + PG - 0.03, y2: PY + PH / 2, color: C.navy,
        width: 2.25 });
    }
  });
  const A = C.blue, B = "E8833A", G = C.sub;
  // ① 옮기기: 왼쪽 네 점은 파랑, 오른쪽 네 점은 주황으로 정해지고, 가운데 한 점이 파랑으로 옮겨 감
  {
    const x = X0, cx = x + PW / 2, cy = PY + 1.6;
    const P = [[cx - 1.2, cy - 0.55], [cx - 0.55, cy - 0.85], [cx - 0.9, cy + 0.15], [cx - 0.25, cy - 0.1],
      [cx + 0.45, cy - 0.7], [cx + 1.15, cy - 0.45], [cx + 0.7, cy + 0.2], [cx + 1.25, cy + 0.45]];
    [[0, 1], [0, 2], [1, 3], [2, 3], [0, 3], [4, 5], [4, 6], [5, 7], [6, 7], [5, 6], [3, 4]].forEach(([a, b]) =>
      edge(s, P[a], P[b]));
    P.forEach((p, k) => dot(s, p[0], p[1], { fill: k < 4 ? A : B, line: k < 4 ? A : B }));
    L.arrow(s, { x1: cx + 0.15, y1: cy + 0.55, x2: cx - 0.2, y2: cy + 0.15, color: A, width: 1.75, dash: "dash" });
    L.text(s, "이웃이 많은 쪽으로", { x: cx - 0.2, y: cy + 0.55, w: 1.9, h: 0.3, size: 14, color: A });
  }
  // ② 다듬기: 파랑 묶음 안에 끊어진 두 점이 있어 떼어 냄
  {
    // ①에서 한 묶음(점선)으로 정해졌지만 안에서 서로 이어지지 않은 두 조각 → 회색 조각을 떼어 냄
    const x = X0 + PW + PG, cx = x + PW / 2, cy = PY + 1.85;
    const P = [[cx - 1.15, cy - 0.45], [cx - 0.5, cy - 0.7], [cx - 0.8, cy + 0.15], [cx + 0.4, cy - 0.25],
      [cx + 1.0, cy - 0.55], [cx + 0.9, cy + 0.3]];
    L.rr(s, { x: cx - 1.5, y: cy - 1.05, w: 3.0, h: 1.6, fill: C.white, line: A, dash: "dash", r: 0.3 });
    [[0, 1], [0, 2], [1, 2], [3, 4], [3, 5], [4, 5]].forEach(([a, b]) => edge(s, P[a], P[b]));
    P.forEach((p, k) => dot(s, p[0], p[1], { fill: k < 3 ? A : G, line: k < 3 ? A : G }));
    L.text(s, "점선: ①에서 정한 한 묶음. 안이 끊어져 회색 조각을 따로 묶음", { x: x + 0.15, y: cy + 0.68,
      w: PW - 0.3, h: 0.55, size: 14, color: C.sub, valign: "top" });
  }
  // ③ 합치기: 묶음을 큰 점 하나로
  {
    const x = X0 + 2 * (PW + PG), cx = x + PW / 2, cy = PY + 1.55;
    const P = [[cx - 1.0, cy - 0.35], [cx + 0.1, cy + 0.35], [cx + 1.05, cy - 0.45]];
    edge(s, P[0], P[1], { width: 4 });
    edge(s, P[1], P[2], { width: 2 });
    [[A, "4"], [G, "3"], [B, "4"]].forEach(([c, t], k) => dot(s, P[k][0], P[k][1], { fill: c, line: c, r: 0.32,
      label: t }));
    L.text(s, "점 안 숫자: 합쳐진 엔티티 수, 선 굵기: 묶음 사이 연결 수", { x: x + 0.15, y: cy + 0.7, w: PW - 0.3,
      h: 0.32, size: 14, color: C.sub });
  }

  // 아래: 결정성
  richCard(s, ["같은 그래프면 늘 같은 묶음",
    "옮겨 보는 순서에 따라 결과가 달라질 수 있어 씨앗(randomSeed)을 고정하고 병렬 처리를 하나로 둠"],
  { x: X0, y: PY + PH + 0.2, w: CW, h: L.BODY_BOTTOM - (PY + PH + 0.2), fill: C.navy, line: null, color: C.white,
    titleSize: 15, size: 14 });
}

// community.py detect() 발췌 — 긴 질의 문자열만 장표 폭에 맞게 이어 붙는 조각으로 나눔. 주석은 장표용
const CODE_DETECT = [
  "# ① 투영: 엔티티를 키 순서로 넣고 엔티티 사이 관계만 이음(청크 노드는 없음)",
  "driver.execute_query(",
  "    \"UNWIND $rows AS row MATCH (s) WHERE elementId(s) = $ids[row.s] \"",
  "    \"OPTIONAL MATCH (t) WHERE row.t IS NOT NULL AND elementId(t) = $ids[row.t] \"",
  "    §\"WITH gds.graph.project($name, s, t, {}, \"§",
  "    §\"{undirectedRelationshipTypes: ['*']}) AS g \"§",
  "    \"RETURN g.nodeCount AS n\", rows=rows, ids=ids, name=name)",
  "# ② Leiden: 씨앗 고정, 병렬 1 → 같은 그래프면 같은 묶음",
  "records, _, _ = driver.execute_query(",
  "    §\"CALL gds.leiden.stream($name, {randomSeed: $seed, concurrency: 1}) \"§",
  "    \"YIELD nodeId, communityId \"",
  "    \"RETURN elementId(gds.util.asNode(nodeId)) AS id, communityId AS c\",",
  "    name=name, seed=config.COMMUNITY_SEED)",
  "# ③ 투영 그래프는 메모리에만 있으므로 끝나면 반드시 지움",
  "driver.execute_query(§\"CALL gds.graph.drop($name, false) YIELD graphName \"§ ...)",
];

// 3장: GDS 코드
async function slideGds() {
  const F = D.full;
  const s = L.newSlide({
    title: "2. 인덱싱: KG 구축 – K8. GDS로 커뮤니티 찾기 (코드)",
    lead: "Neo4j 안에서 엔티티 그래프를 메모리에 투영하고, gds.leiden.stream으로 묶음 번호를 받은 뒤 투영을 지움",
    notes: "실제 코드는 community.py의 detect 함수입니다. GDS 알고리즘은 저장된 그래프를 바로 쓰지 않고, 필요한 노드와 "
      + "관계만 메모리에 복사한 투영 그래프에서 돕니다. 첫째 줄 묶음이 투영입니다. 엔티티만 넣고, 엔티티 사이 관계만 "
      + "잇습니다. 관계 방향은 묶음에 상관없으므로 무방향으로 투영합니다.\n"
      + "둘째 줄 묶음이 Leiden입니다. stream 방식은 그래프를 고치지 않고 엔티티마다 묶음 번호만 돌려줍니다. 씨앗을 고정하고 "
      + "병렬 처리를 하나로 두어 결과가 매번 같게 했습니다. 마지막으로 투영 그래프는 메모리를 차지하므로 반드시 지웁니다.\n"
      + `v0 전체 재색인에서는 엔티티 ${n(F.entities)}개, 관계 ${n(F.relations)}개를 투영했고, 묶음 ${n(F.groups)}개가 `
      + `나왔습니다. 그중 엔티티가 3개 이상인 ${n(F.summarized)}개를 요약했습니다. GDS는 Community Edition으로도 무료로 `
      + "쓸 수 있고, 병렬 처리는 4코어까지입니다.",
  });
  const LW = 9.05, RX = X0 + LW + 0.3, RW = XR - RX, TOP = 1.9, END = 7.0;
  codeBoxBold(s, CODE_DETECT, { x: X0, y: TOP, w: LW, h: END - TOP, size: 14, title: "detect (community.py 발췌)" });
  const notes = [
    ["투영 그래프", "필요한 노드와 관계만 메모리에 복사한 그래프. GDS 알고리즘은 이 위에서 돎"],
    ["무방향", "관계 방향은 묶음과 상관없어 양쪽으로 봄"],
    ["stream 방식", "그래프를 고치지 않고 엔티티마다 묶음 번호만 돌려줌"],
    ["Community Edition", "GDS도 무료. 모든 알고리즘을 쓰고 병렬은 4코어까지"],
  ];
  const NG = 0.15, NH = (END - TOP - 3 * NG) / 4;
  notes.forEach(([t, b], i) => richCard(s, [t, b], { x: RX, y: TOP + i * (NH + NG), w: RW, h: NH,
    fill: i === 0 ? C.tint : C.white, line: i === 0 ? C.blue : C.border, color: C.ink, align: "left", titleSize: 15,
    size: 14 }));
  richCard(s, [`v0 전체 재색인: 엔티티 ${n(F.entities)}개, 관계 ${n(F.relations)}개 → 묶음 ${n(F.groups)}개`,
    `엔티티 3개 이상 ${n(F.summarized)}개 요약. 가장 큰 묶음 ${F.size_top.join(", ")}개. 문서 종류가 섞인 묶음 ${F.mixed}개`],
  { x: X0, y: END + 0.15, w: CW, h: L.BODY_BOTTOM - END - 0.15, fill: C.navy, line: null, color: C.white,
    titleSize: 15, size: 14 });
}

// community.py 프롬프트와 적재 발췌
// 입력 줄은 실제 보고서 예와 같은 묶음의 실제 입력 글 앞부분(make_data.py가 community._report_prompt로 만듦)
const CODE_PROMPT = [
  "엔티티:", ...D.prompt_entities, "관계:", ...D.prompt_relations, "",
  "출력(JSON): {\"title\": \"묶음 주제 한 줄\", \"summary\": \"3 ~ 5문장\",",
  "  \"findings\": [{\"text\": \"핵심 사실\", \"entities\": [\"e1\"]}]}",
];
const CODE_WRITE = [
  "§CREATE (c:Community {community_id, title, summary,§",
  "§  findings, member_hash, size, generation, run_id})§",
  "CALL db.create.setNodeVectorProperty(c, 'embedding', row.vec)",
  "§CREATE (e)-[:IN_COMMUNITY]->(c)§      // 묶음의 엔티티마다",
  "CREATE VECTOR INDEX kg_community_embedding …",
];

// 4장: 보고서 만들기
async function slideReport() {
  const E = D.example;
  const s = L.newSlide({
    title: "2. 인덱싱: KG 구축 – K8. 묶음마다 보고서 쓰기 (원리와 코드)",
    lead: "묶음의 엔티티 설명과 관계를 LLM에 주고, 근거 엔티티를 단 제목, 요약, 핵심 사실을 받아 임베딩해 저장함",
    notes: "보고서 입력은 묶음 안 엔티티의 설명 글과 그 사이 관계입니다. 엔티티마다 e1, e2 같은 번호를 붙여 넣고, LLM에게는 "
      + "제목, 요약, 핵심 사실을 JSON으로 쓰게 합니다. 핵심 사실마다 근거 엔티티 번호를 적게 해서, 보고서가 그래프에 없는 "
      + "사실을 지어내지 않았는지 되짚을 수 있게 했습니다. 번호는 저장할 때 엔티티 이름으로 바꾸고, 본문에 남은 번호는 "
      + "지웁니다.\n"
      + "큰 묶음은 관계가 많은 엔티티부터 120개까지만 넣습니다. 묶음 지문은 보고서 판, 구성원, 묶음 안 관계로 만들고, 지문이 "
      + "지난번과 같으면 LLM을 부르지 않고 지난 보고서를 다시 씁니다.\n"
      + "보고서는 제목, 요약, 핵심 사실을 이어 KURE-v2로 임베딩하고, Community 노드로 저장합니다. 묶음의 엔티티마다 "
      + "IN_COMMUNITY 관계를 잇고, 보고서 벡터 인덱스를 따로 만듭니다. Community 노드는 엔티티가 아니라서 엔티티 라벨을 "
      + "붙이지 않습니다.",
  });
  const LW = 7.0, RX = X0 + LW + 0.3, RW = XR - RX, TOP = 1.9;
  codeBoxBold(s, CODE_PROMPT, { x: X0, y: TOP, w: LW, h: 2.85, size: 14, title: "LLM 입력과 출력 (프롬프트 요지)" });
  codeBoxBold(s, CODE_WRITE, { x: X0, y: TOP + 3.0, w: LW, h: 2.1, size: 14, title: "⑤ 적재 (community.py 발췌)" });

  // 오른쪽: 실제 보고서 예
  L.text(s, `실제 보고서 예 (v0 전체 재색인, 엔티티 ${E.size}개 묶음)`, { x: RX, y: TOP, w: RW, h: 0.36, size: 15,
    color: C.navy, bold: true });
  richCard(s, [E.title, E.summary], { x: RX, y: TOP + 0.42, w: RW, h: 1.75, fill: C.tint, line: C.blue,
    color: C.navy, align: "left", titleSize: 15, size: 14, valign: "top" });
  const FY = TOP + 2.3;
  L.text(s, "핵심 사실과 근거 엔티티", { x: RX, y: FY, w: RW, h: 0.34, size: 15, color: C.navy, bold: true });
  const fh = (TOP + 5.1 - FY - 0.4 - 0.1 * (E.findings.length - 1)) / E.findings.length;
  E.findings.forEach((f, i) => {  // 핵심 사실은 보통 굵기로(richCard는 첫 줄을 굵게 씀)
    const y = FY + 0.4 + i * (fh + 0.1);
    L.rr(s, { x: RX, y, w: RW, h: fh, fill: C.white, line: C.border });
    L.text(s, f, { x: RX + 0.08, y, w: RW - 0.16, h: fh, size: 14, color: C.ink, margin: 0.06 });
  });

  const rules = [
    ["근거를 단다", "핵심 사실마다 근거 엔티티를 적어 지어낸 내용을 되짚음"],
    ["지문으로 재사용", "보고서 판, 구성원, 관계가 같으면 LLM을 부르지 않음"],
    ["엔티티가 아님", "Community 노드에는 엔티티 라벨을 붙이지 않음"],
  ];
  const RG = 0.2, RCW = (CW - 2 * RG) / 3, RY = TOP + 5.25, RH = L.BODY_BOTTOM - RY;
  rules.forEach(([t, b], i) => {
    const x = X0 + i * (RCW + RG);
    L.rr(s, { x, y: RY, w: RCW, h: RH, fill: C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.12, y: RY + 0.1, size: 0.34, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: x + 0.55, y: RY + 0.06, w: RCW - 0.65, h: 0.42, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.15, y: RY + 0.46, w: RCW - 0.3, h: RH - 0.5, size: 14, color: C.body, valign: "top" });
  });
}

// 5장: 거시 검색
async function slideSearch() {
  const M = D.macro, Q = M.Q23;
  const s = L.newSlide({
    title: "2. 인덱싱: KG 구축 – K8. 커뮤니티 보고서로 거시 검색하기",
    lead: "질문과 가까운 보고서를 벡터로 찾고, 그 보고서들만 근거로 LLM이 답을 씀 (Microsoft GraphRAG의 Global Search 방식)",
    notes: "거시 검색은 엔티티 하나가 아니라 보고서 여러 개에서 답을 모읍니다. 먼저 질문을 KURE-v2로 임베딩해 커뮤니티 보고서 "
      + "벡터 인덱스에서 가까운 보고서 다섯 개를 찾습니다. 그다음 그 보고서들만 근거로 LLM이 답을 씁니다. 보고서에 없는 "
      + "내용은 지어내지 말고 없다고 쓰게 합니다. Microsoft GraphRAG의 Global Search와 같은 생각이고, 원래는 보고서마다 "
      + "부분 답을 낸 뒤 합치는 두 단계로 합니다.\n"
      + "평가셋의 거시 질문 세 개로 v0 전체 재색인 결과를 쟀습니다. 표의 세 숫자는 정답 요점이 보고서 전체 어딘가에 있는 수, "
      + "질문으로 찾은 상위 다섯 보고서에 있는 수, LLM 답에 들어간 수입니다. 보고서 전체에는 있는데 상위 다섯에 없으면 "
      + "찾기 문제이고, 보고서 전체에도 없으면 묶음이나 요약 문제입니다.\n"
      + "v0 검색기에는 아직 이 거시 검색 단계가 없습니다. 여기 결과는 시험 스크립트로 잰 것입니다. 요점 판정은 낱말로 "
      + "자동으로 했고, 같은 질문을 두 번 물었을 때 Q24 답은 4개 중 2개와 0개로 달랐습니다. 그래서 답 칸은 대략의 경향으로만 "
      + "봐야 합니다.",
  });
  const TOP = 1.9;
  // 위: Q23으로 따라가는 흐름
  L.text(s, `질문 예: 「${Q.question}」`, { x: X0, y: TOP, w: CW, h: 0.36, size: 15, color: C.navy, bold: true });
  const FY = TOP + 0.45, FG = 0.22, FW = (CW - 3 * FG) / 4, FH = 1.75;
  const flow = [
    ["① 질문 임베딩", ["KURE-v2로", "질문을 벡터로 바꿈"]],
    ["② 보고서 찾기", ["kg_community_embedding", "가까운 보고서 상위 5개"]],
    ["③ 보고서로 답 쓰기", ["LLM이 보고서만 근거로", "없는 내용은 없다고 씀"]],
    ["④ 답", [`정답 요점 ${Q.score.in_answer} / ${Q.of}`, `상위 5에 있던 요점 ${Q.score.in_top_reports} / ${Q.of}`]],
  ];
  flow.forEach(([head, lines], i) => {
    const x = X0 + i * (FW + FG);
    const key = i === 1 || i === 2;
    L.darkBadge(s, head, { x, y: FY, w: FW, h: 0.42, size: 15, fill: key ? C.blue : C.navy });
    richCard(s, lines, { x, y: FY + 0.48, w: FW, h: FH - 0.48, fill: key ? C.tint : C.white,
      line: key ? C.blue : C.border, color: key ? C.navy : C.ink, titleSize: 15, size: 14 });
    if (i < 3) {
      L.arrow(s, { x1: x + FW + 0.03, y1: FY + 0.48 + (FH - 0.48) / 2, x2: x + FW + FG - 0.03,
        y2: FY + 0.48 + (FH - 0.48) / 2, color: C.navy, width: 2.25 });
    }
  });
  // 가운데: Q23 상위 보고서 제목
  const TY = FY + FH + 0.2;
  L.text(s, "Q23으로 찾은 상위 보고서", { x: X0, y: TY, w: 6.6, h: 0.34, size: 15, color: C.navy, bold: true });
  const cut = (t, k) => (t.length <= k ? t : t.slice(0, k - 1) + "…");  // 한 줄에 들어가게 긴 제목은 줄임
  Q.top.slice(0, 5).forEach((t, i) => {
    const y = TY + 0.42 + i * 0.5;
    L.rr(s, { x: X0, y, w: 6.6, h: 0.42, fill: i % 2 ? C.white : C.altRow, line: C.border });
    L.text(s, `${i + 1}. ${cut(t.title, 27)}`, { x: X0 + 0.1, y, w: 5.2, h: 0.42, size: 14, color: C.ink });
    L.text(s, t.doc_types.join("+"), { x: X0 + 5.2, y, w: 1.3, h: 0.42, size: 14, color: C.sub, align: "right" });
  });
  // 오른쪽: 세 질문 결과 표
  const RX = X0 + 6.9, RW = XR - RX;
  L.text(s, "거시 질문 3개 결과 (정답 요점 수)", { x: RX, y: TY, w: RW, h: 0.34, size: 15, color: C.navy, bold: true });
  const rows = [["질문", "보고서 전체", "상위 5", "답"]];
  ["Q23", "Q24", "Q25"].forEach((q) => {
    const r = M[q];
    rows.push([`${q} ${r.label}`, `${r.score.in_any_report} / ${r.of}`, `${r.score.in_top_reports} / ${r.of}`,
      `${r.score.in_answer} / ${r.of}`]);
  });
  L.table(s, rows, { x: RX, y: TY + 0.42, w: RW, colW: [RW - 3.6, 1.3, 1.1, 1.2], rowH: 0.45, size: 14 });
  const FT = TY + 0.42 + 4 * 0.45 + 0.15;
  richCard(s, ["찾기는 되지만 답이 약함", D.finding], { x: RX, y: FT, w: RW, h: L.BODY_BOTTOM - FT, fill: C.tint,
    line: C.blue, color: C.navy, align: "left", titleSize: 15, size: 14, valign: "top" });
}

async function main() {
  L.createDeck();
  for (const fn of [slideWhat, slideLeiden, slideGds, slideReport, slideSearch]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
