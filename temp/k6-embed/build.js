// KG 구축 K6 노드 설명 임베딩 장표 3장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "K6임베딩.pptx");

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

// 활성 세대 노드 속성으로 K6 규칙대로 다시 만든 실제 설명 글(scratchpad k6_probe.py, 2026-10-19)
const DESCS = [
  "TermsDocument: effective_date=2027-01-15, supersedes=1.1, version=1.2",
  "Clause: clause_no=제13조, title=이용 원칙",
  "Requirement: description=카드는 회원 본인이 유효기간과 이용한도 안에서 사용합니다.",
  "Proposal: content=화면을 같이 보면서 그 기간이 적힌 자리를 짚어 드릴까요?, decision=수용, reason=…",
];

async function createSlide01() {
  const s = L.newSlide({
    title: "KG 구축 K6 노드 설명 임베딩",
    lead: "엔티티마다 「라벨: 속성=값」 설명 글을 만들어 임베딩하고, 벡터 인덱스로 질문과 뜻이 가까운 엔티티를 찾게 함",
    notes: "K6은 K5까지 마친 엔티티에 뜻을 담은 벡터를 붙이는 단계입니다. 엔티티에는 문장이 따로 없기 때문에, 라벨과 속성을 "
      + "「라벨: 속성=값」 꼴의 설명 글로 이어 붙여 만듭니다. 세대나 실행 표시 같은 관리용 속성은 뜻과 상관이 없어서 뺍니다. 이 "
      + "글을 검색엔진과 같은 KURE-v2 모델로 임베딩해 엔티티에 저장하고, 엔티티 전체에 벡터 인덱스를 만듭니다.\n이렇게 해 두면 "
      + "질문 하나로 뜻이 가까운 엔티티를 바로 찾을 수 있습니다. 「할부 수수료는 언제 알려 주나요?」로 찾으면 할부 조항의 충족 "
      + "조건 엔티티가 가장 먼저 나옵니다. 찾은 엔티티를 시작 엔티티로 삼아 관계를 따라가면 그래프 탐색이 시작됩니다. 이것이 엔티티 "
      + "직접 검색입니다.\n청크 노드는 임베딩하지 않습니다. 청크의 벡터는 검색엔진이 이미 갖고 있기 때문입니다. 그리고 임베딩은 합치기가 끝난 뒤에 하므로, 합쳐질 노드를 "
      + "여러 번 임베딩하지 않습니다.",
  });

  // 위: 4단계 흐름
  const FG = 0.35, FW = (CW - 3 * FG) / 4, FY = 1.9, FB = 2.42, FH = 1.35;
  const flow = [
    ["① 엔티티", ["Proposal", "content, decision, generation, run_id"]],
    ["② 설명 글 만들기", ["Proposal: content=그러면 주문", "내역 화면으로 …, decision=수용"]],
    ["③ KURE-v2 임베딩", ["768차원 벡터", "검색엔진 S1과 같은 모델"]],
    ["④ 저장과 벡터 인덱스", ["엔티티의 embedding 속성", "kg_entity_embedding (코사인)"]],
  ];
  flow.forEach(([head, lines], i) => {
    const x = X0 + i * (FW + FG);
    L.darkBadge(s, head, { x, y: FY, w: FW, h: 0.42, size: 16, fill: i === 1 ? C.blue : C.navy });
    richCard(s, lines, { x, y: FB, w: FW, h: FH, fill: i === 1 ? C.tint : C.white, line: i === 1 ? C.blue : C.border,
      color: i === 1 ? C.navy : C.ink, titleSize: 16, size: 15 });
    if (i < 3) {
      L.arrow(s, { x1: x + FW + 0.04, y1: FB + FH / 2, x2: x + FW + FG - 0.04, y2: FB + FH / 2, color: C.navy,
        width: 2.5 });
    }
  });

  // 왼쪽 아래: 실제 설명 글
  const BY = FB + FH + 0.25, LW = 7.3, END = 6.25;
  L.text(s, "실제 설명 글 (v0 표본)", { x: X0, y: BY, w: LW, h: 0.38, size: 15, color: C.navy, bold: true });
  L.codeBox(s, DESCS.slice(0, 3), { x: X0, y: BY + 0.42, w: LW, h: END - BY - 0.42, size: 15 });

  // 오른쪽 아래: 질문으로 노드 찾기
  const QX = X0 + LW + 0.35, QW = XR - QX;
  L.text(s, "어디에 쓰나: 엔티티 직접 검색 (조회 예시)", { x: QX, y: BY, w: QW, h: 0.38, size: 15, color: C.navy,
    bold: true });
  const QY = BY + 0.42;
  L.card(s, "질문: 할부 수수료는 언제 알려 주나요?", { x: QX, y: QY, w: QW, h: 0.46, fill: C.tint, line: C.blue,
    color: C.navy, size: 15, bold: true });
  L.arrow(s, { x1: QX + QW / 2, y1: QY + 0.48, x2: QX + QW / 2, y2: QY + 0.66, color: C.navy, width: 2 });
  const hits = [["Requirement 0.866", "할부 거래의 개월 수, 회차별 금액과 가상 수수료율은 …"],
    ["Clause 0.836", "할부 거래"]];
  hits.forEach(([t, b], i) => {
    const y = QY + 0.7 + i * 0.5;
    L.rr(s, { x: QX, y, w: QW, h: 0.44, fill: C.white, line: C.border });
    L.text(s, t, { x: QX + 0.1, y, w: 2.2, h: 0.44, size: 14, color: C.blue, bold: true });
    L.text(s, b, { x: QX + 2.3, y, w: QW - 2.4, h: 0.44, size: 14, color: C.ink });
  });
  L.text(s, "→ 찾은 엔티티를 시작 엔티티로 관계를 따라 그래프 탐색", { x: QX, y: QY + 1.72, w: QW, h: END - QY - 1.72, size: 14,
    color: C.slate });

  // 아래: 규칙 카드 3개
  const rules = [
    ["엔티티만 임베딩", "청크 노드는 뺌. 청크 벡터는 검색엔진에 이미 있음"],
    ["관리용 속성은 뺌", "generation, run_id는 설명 글에 넣지 않음. 속성은 이름순"],
    ["K5 병합 뒤에 임베딩", "합쳐져 사라질 엔티티는 임베딩하지 않고, 남은 엔티티의 속성과 벡터가 맞게 함"],
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

// kg_build.py 원문 발췌 — 줄 나눔만 장표 폭에 맞게 바꾸고(긴 질의 문자열은 이어 붙는 조각), 주석 일부는 장표용. §…§은 굵게
const CODE_K6 = String.raw`SYSTEM_PROPS = {"generation", "run_id", "embedding"}   # 설명에서 뺌
def k6_embed_descriptions(driver, generation):
    records, _, _ = driver.execute_query(
        "MATCH (n:__Entity__ {generation: $g}) WHERE n.embedding IS NULL "
        "RETURN elementId(n) AS id, "
        "[l IN labels(n) WHERE NOT l STARTS WITH '__'][0] AS label, "
        "properties(n) AS props", g=generation)
    rows = [dict(r) for r in records]
    §texts = [f"{r['label']}: " + ", ".join(§
        §f"{k}={v}" for k, v in sorted(r["props"].items())§
        §if k not in SYSTEM_PROPS) for r in rows]§
    §vectors = embed(texts)§                          # KURE-v2, 768차원
    driver.execute_query(
        "UNWIND $rows AS row MATCH (n) WHERE elementId(n) = row.id "
        §"CALL db.create.setNodeVectorProperty(n, 'embedding', row.vec)",§
        rows=[{"id": r["id"], "vec": v} for r, v in zip(rows, vectors)])
    driver.execute_query(
        §"CREATE VECTOR INDEX kg_entity_embedding IF NOT EXISTS "§
        §"FOR (n:__Entity__) ON n.embedding "§
        "OPTIONS {indexConfig: {\`vector.dimensions\`: $d, "
        "\`vector.similarity_function\`: 'cosine'}}", d=config.EMBED_DIMENSION)
    return len(rows)`.replace(/\\`/g, "`").split("\n");

async function createSlide02() {
  const s = L.newSlide({
    title: "K6 노드 설명 임베딩 코드 (kg_build.py)",
    lead: "임베딩이 없는 엔티티를 읽어 설명 글을 만들고, 한 번에 임베딩해 저장한 뒤 벡터 인덱스를 만듦",
    notes: "코드는 세 단계입니다. 먼저 임베딩이 없는 엔티티의 라벨과 속성을 읽고, 관리용 속성을 뺀 설명 글을 만듭니다. 다음으로 "
      + "글 전체를 한 번에 임베딩해 엔티티마다 embedding 속성으로 저장합니다. 마지막으로 벡터 인덱스를 만드는데, 이미 있으면 그대로 "
      + "둡니다.\nv0 표본 전체 재색인에서는 91개를 임베딩했습니다. 증분 색인 때는 임베딩이 없는 새 엔티티만 임베딩합니다. "
      + "청크 노드는 엔티티가 아니라서 임베딩하지 않습니다.",
  });

  const LW = 8.05, RX = X0 + LW + 0.3, RW = XR - RX;
  codeBoxBold(s, CODE_K6, { x: X0, y: 1.9, w: LW, h: 6.05, size: 14, title: "k6_embed_descriptions (kg_build.py 발췌)" });
  L.codeBox(s, DESCS, { x: RX, y: 1.9, w: RW, h: 2.3, size: 14, title: "만들어진 설명 글 (v0 표본)" });
  L.text(s, "벡터 인덱스 (SHOW VECTOR INDEXES)", { x: RX, y: 4.32, w: RW, h: 0.38, size: 15, color: C.navy, bold: true });
  L.table(s, [["항목", "값"], ["이름", "kg_entity_embedding"], ["대상", "__Entity__ 라벨의 embedding 속성"],
    ["설정", "768차원, COSINE, ONLINE"]], { x: RX, y: 4.74, w: RW, colW: [1.4, RW - 1.4], rowH: 0.42, size: 15 });
  richCard(s, ["v0 표본 결과", "전체 재색인 91개, 증분 색인은 새 엔티티만", "청크 노드는 0개 (엔티티가 아니라 임베딩 안 함)"],
    { x: RX, y: 6.55, w: RW, h: 1.4, fill: C.blue, line: null, color: C.white, titleSize: 16, size: 15 });
}

// 1장: K6이 왜 필요한가 — 그래프 탐색의 시작 엔티티를 찾는 두 방식(검색엔진 경유 검색, 엔티티 직접 검색)을 비교
// 수치는 verify/kg-entry-compare 재실행(2026-10-23, 세대 gen-sample-003-06e0ccea) 결과
async function createSlideWhy() {
  const s = L.newSlide({
    title: "KG 구축 K6이 필요한 이유",
    lead: "검색엔진 경유 검색과 엔티티 직접 검색은 놓치는 질문이 달라 함께 써야 하고, K6은 엔티티 직접 검색을 가능하게 함",
    notes: "K6을 설명하기 전에 왜 필요한지부터 보겠습니다. 그래프 탐색은 시작 엔티티를 정해야 시작할 수 있고, 시작 엔티티를 찾는 "
      + "방식은 두 가지입니다.\n첫째는 검색엔진 경유 검색입니다. 질문으로 검색엔진을 먼저 검색해 검색결과 청크를 얻고, 그 청크와 "
      + "chunk_id가 같은 청크 노드를 찾은 뒤, 그 청크 노드에 FROM_CHUNK로 이어진 엔티티를 시작 엔티티로 씁니다. 검색엔진 결과에 "
      + "기대므로 K6이 없어도 됩니다.\n둘째는 엔티티 직접 검색입니다. 검색엔진을 거치지 않고, 질문과 뜻이 가까운 엔티티를 엔티티 "
      + "설명 벡터로 바로 찾아 시작 엔티티로 씁니다. 검색엔진과 따로, 동시에 돌릴 수 있습니다. 이 벡터를 만드는 단계가 K6입니다. "
      + "그래서 검색엔진 경유 검색만 쓴다면 K6은 필요 없습니다.\n같은 질문 20개로 비교해 보니 두 방식은 놓치는 질문이 "
      + "달랐습니다. 할부 철회 기한을 구어체로 물으면 검색엔진이 말투가 비슷한 상담 청크를 1위로 올려 검색엔진 경유 검색이 "
      + "놓쳤지만, 엔티티 직접 검색은 철회 기한 엔티티를 1위로 찾았습니다. 반대로 오랫동안 카드를 안 쓰면 어떻게 되는지 물으면 "
      + "엔티티 직접 검색은 5위 안에 정답이 없었고, 검색엔진 경유 검색은 청크 2개 안에서 찾았습니다.\n두 방식을 함께 쓰고 "
      + "결과를 합치면 20개 중 18개에 닿아 가장 많았습니다. 다만 표본이 작은 실험이라 전체 데이터에서는 숫자가 달라질 수 "
      + "있습니다.",
  });

  // 위: 시작 엔티티를 찾는 두 방식
  const GAP = 0.3, EW = (CW - GAP) / 2, TOP = 1.9, EH = 2.75;
  const entries = [
    { head: "검색엔진 경유 검색", fill: C.navy,
      steps: ["질문", "검색결과 청크", "같은 chunk_id의 청크 노드", "FROM_CHUNK로 이어진 엔티티"],
      good: "청크 본문에 맥락이 있어 표현이 달라도 맞음. K6 없이 가능",
      bad: "후보가 많음(청크 1개에 평균 9.8개). 검색엔진이 다른 문서 청크를 1위로 올리면 함께 빗나감" },
    { head: "엔티티 직접 검색", fill: C.blue, steps: ["질문", "K6 엔티티 설명 벡터", "뜻이 가까운 엔티티"],
      good: "검색엔진과 따로 돌고, 사실 하나를 바로 짚음(후보 5개)",
      bad: "설명 글이 짧아 맥락이 빠지면 놓침. 인덱싱에 K6 단계를 더 해야 함" },
  ];
  entries.forEach((e, i) => {
    const x = X0 + i * (EW + GAP);
    L.rr(s, { x, y: TOP, w: EW, h: EH, fill: i === 1 ? C.tint : C.white, line: i === 1 ? C.blue : C.border });
    L.card(s, e.head, { x, y: TOP, w: EW, h: 0.44, fill: e.fill, line: null, color: C.white, size: 16, bold: true,
      r: 0.06 });
    // 흐름 알약: 칸 수에 맞춰 폭을 나눔. 두 줄 글이 들어가게 높이를 넉넉히 둠
    const PG = 0.26, PW = (EW - 0.3 - (e.steps.length - 1) * PG) / e.steps.length, PY = TOP + 0.6, PH = 0.66;
    e.steps.forEach((t, k) => {
      const px = x + 0.15 + k * (PW + PG);
      L.card(s, t, { x: px, y: PY, w: PW, h: PH, fill: C.white, line: C.pill, color: C.navy, size: 14, bold: true,
        r: 0.2 });
      if (k < e.steps.length - 1) {
        L.arrow(s, { x1: px + PW + 0.03, y1: PY + PH / 2, x2: px + PW + PG - 0.03, y2: PY + PH / 2, color: C.navy,
          width: 1.75 });
      }
    });
    [["강점", e.good, C.blue], ["약점", e.bad, C.slate]].forEach(([tag, txt, col], k) => {
      const y = TOP + 1.45 + k * 0.62;
      L.card(s, tag, { x: x + 0.15, y: y + 0.08, w: 0.8, h: 0.38, fill: col, line: null, color: C.white, size: 14,
        bold: true, r: 0.12 });
      L.text(s, txt, { x: x + 1.05, y, w: EW - 1.2, h: 0.54, size: 15, color: C.ink });
    });
  });

  // 왼쪽 아래: 비교 막대
  const BY = TOP + EH + 0.25, BW = 8.4;
  L.text(s, "같은 질문 20개로 비교 (v0 표본: 청크 9개, 엔티티 83개)", { x: X0, y: BY, w: BW, h: 0.38, size: 15,
    color: C.navy, bold: true });
  const bars = [["검색엔진 경유, 청크 1개", 9, "후보 9.8", C.pill], ["검색엔진 경유, 청크 2개", 16, "후보 20.5", C.pill],
    ["엔티티 직접, 5개", 16, "후보 5", C.blue], ["함께 (청크 2 + 엔티티 5)", 18, "후보 25.5 이하", C.navy]];
  const LBW = 2.75, MAXW = 3.1, RP = 0.66, RH = 0.48;
  bars.forEach(([label, n, cand, col], i) => {
    const y = BY + 0.5 + i * RP;
    L.text(s, label, { x: X0, y, w: LBW, h: RH, size: 15, color: C.ink, bold: i === 3 });
    L.box(s, { x: X0 + LBW, y: y + 0.06, w: MAXW, h: RH - 0.12, fill: C.line, line: null });
    L.box(s, { x: X0 + LBW, y: y + 0.06, w: MAXW * n / 20, h: RH - 0.12, fill: col, line: null });
    L.text(s, `${n} / 20  (${cand})`, { x: X0 + LBW + MAXW + 0.1, y, w: BW - LBW - MAXW - 0.1, h: RH, size: 15,
      color: i === 3 ? C.navy : C.body, bold: i === 3 });
  });

  // 오른쪽 아래: 서로 메운 예와 결론
  const RX = X0 + BW + 0.3, RW = XR - RX;
  L.text(s, "서로 메운 예", { x: RX, y: BY, w: RW, h: 0.38, size: 15, color: C.navy, bold: true });
  const fills = [
    ["「할부로 산 물건을 무르고 싶은데…」", "검색엔진 경유: 상담 청크가 1위라 놓침 → 엔티티 직접: 철회 기한 엔티티 1위"],
    ["「오랫동안 카드를 안 쓰면…」", "엔티티 직접: 5위 안에 정답 없음 → 검색엔진 경유: 청크 2개 안에 정답"],
  ];
  fills.forEach(([t, b], i) => richCard(s, [t, b], { x: RX, y: BY + 0.44 + i * 0.84, w: RW, h: 0.78, fill: C.altRow,
    line: C.border, color: C.ink, align: "left", titleSize: 15, size: 14 }));
  const CY = BY + 0.44 + 2 * 0.84;
  richCard(s, ["두 방식을 함께 쓰고 결과를 합침", "검색엔진 경유 검색만 쓰면 K6은 필요 없음"], { x: RX, y: CY, w: RW,
    h: L.BODY_BOTTOM - CY, fill: C.navy, line: null, color: C.white, titleSize: 16, size: 15 });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlideWhy, createSlide01, createSlide02]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });

