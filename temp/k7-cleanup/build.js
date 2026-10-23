// KG 구축 K7 청크 정리 장표 1장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
// 코드는 hybrid-ai-lab/indexer/graphrag/v0/kg_build.py cleanup() 발췌, 수치는 v0 README 증분 색인 sample-006 실행 기록
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "K7청크정리.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스(K6 장표와 같은 모양)
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

// 코드 상자: §…§ 구간만 굵게(K6 장표와 같은 모양)
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

// kg_build.py cleanup() 원문 발췌 — 긴 질의 문자열만 장표 폭에 맞게 이어 붙는 조각으로 나눔. 주석은 장표용
const CODE_K7 = [
  "def cleanup(driver, generation, run_id, doc_ids):      # 증분 색인, S3 다음",
  "    records, _, _ = driver.execute_query(",
  "        \"MATCH (c:Chunk {generation: $g}) \"",
  "        §\"WHERE c.doc_id IN $docs AND c.run_id <> $run \"§",
  "        §\"DETACH DELETE c\"§ \" RETURN count(*) AS n\",",
  "        g=generation, docs=doc_ids, run=run_id)",
  "    chunks = records[0][\"n\"]                          # 옛 청크 노드 수",
  "    records, _, _ = driver.execute_query(",
  "        \"MATCH (e:__Entity__ {generation: $g}) \"",
  "        §\"WHERE NOT (e)-[:FROM_CHUNK]->(:Chunk) \"§",
  "        §\"DETACH DELETE e\"§ \" RETURN count(*) AS n\", g=generation)",
  "    orphans = records[0][\"n\"]                         # 고아 엔티티 수",
];  // 마지막 return(지운 개수를 돌려줌)은 장표 폭 때문에 뺌

async function createSlide01() {
  const s = L.newSlide({
    title: "2. 인덱싱: KG 구축 – K7. 청크 정리",
    lead: "증분 색인에서 바뀐 문서의 옛 청크 노드를 지우고, 근거 청크를 모두 잃은 고아 엔티티를 지움",
    notes: "K7은 증분 색인에서만 부르는 정리 단계입니다. 문서가 바뀌면 K4가 그 문서의 청크 노드를 새로 만들어 넣습니다. 그래서 "
      + "그래프에는 이번에 넣은 새 청크 노드와 지난 실행에서 넣은 옛 청크 노드가 함께 남아 있습니다. K7은 바뀌었거나 사라진 문서의 "
      + "청크 노드 가운데 이번 실행이 만들지 않은 것, 즉 run_id가 다른 것만 지웁니다. 증분 색인은 바뀐 청크가 아니라 "
      + "바뀐 문서를 단위로 다시 넣습니다. 그래서 내용이 그대로인 청크까지 그 문서의 청크는 모두 새로 들어가고, K7 전까지는 "
      + "같은 chunk_id의 청크 노드가 잠시 두 벌이 됩니다. 이번 K4가 넣은 새 청크 노드를 지우지 않도록 run_id로 가릅니다.\n"
      + "청크 노드를 지우면 그 청크에만 이어져 있던 엔티티는 근거를 잃습니다. FROM_CHUNK가 하나도 남지 않은 엔티티를 고아 "
      + "엔티티라고 부르고, 두 번째 질의로 지웁니다. 겹친 조항처럼 다른 청크에도 이어진 엔티티는 근거가 남아 있어 지우지 "
      + "않습니다.\n"
      + "K7은 검색엔진 문서 교체, 즉 S3 다음에 합니다. 그래프에는 먼저 넣고 나중에 지우기 때문에, 바뀌는 동안에도 검색엔진이 "
      + "돌려준 chunk_id의 청크 노드가 그래프에 늘 있습니다. 순서를 거꾸로 하면 검색엔진은 아직 옛 chunk_id를 돌려주는데 "
      + "그래프에는 그 청크 노드가 없는 순간이 생깁니다.\n"
      + "v0 표본 증분 색인에서는 상담 1건의 본문을 고치고 혜택 청크 1개를 뺐습니다. K7은 옛 청크 노드 5개와 고아 엔티티 "
      + "33개를 지웠고, 그 뒤 검증에서 검색엔진 청크 9개와 청크 노드 9개가 맞았습니다. 전체 재색인은 새 세대에 처음부터 쓰므로 "
      + "지울 옛 청크가 없어 K7을 부르지 않습니다.",
  });

  // 위: 4단계 흐름(K6 장표와 같은 배치)
  const FG = 0.35, FW = (CW - 3 * FG) / 4, FY = 1.9, FB = 2.42, FH = 0.85;
  const flow = [
    ["① 바뀐 문서", ["증분 색인이 찾은 문서", "본문이 바뀐 문서, 빠진 문서"]],
    ["② 옛 청크 노드 지우기", ["그 문서의 옛 청크 노드", "이번 K4가 넣지 않은 것"]],
    ["③ 고아 엔티티 지우기", ["FROM_CHUNK가 하나도", "남지 않은 엔티티"]],
    ["④ 결과 (v0 표본)", ["옛 청크 노드 5개", "고아 엔티티 33개 지움"]],
  ];
  flow.forEach(([head, lines], i) => {
    const x = X0 + i * (FW + FG);
    const key = i === 1 || i === 2;
    L.darkBadge(s, head, { x, y: FY, w: FW, h: 0.42, size: 16, fill: key ? C.blue : C.navy });
    richCard(s, lines, { x, y: FB, w: FW, h: FH, fill: key ? C.tint : C.white, line: key ? C.blue : C.border,
      color: key ? C.navy : C.ink, titleSize: 15, size: 15 });
    if (i < 3) {
      L.arrow(s, { x1: x + FW + 0.04, y1: FB + FH / 2, x2: x + FW + FG - 0.04, y2: FB + FH / 2, color: C.navy,
        width: 2.5 });
    }
  });

  // 왼쪽 아래: 실제 코드
  const BY = FB + FH + 0.2, LW = 8.15, END = 6.95;
  codeBoxBold(s, CODE_K7, { x: X0, y: BY, w: LW, h: END - BY, size: 14, title: "cleanup (kg_build.py 발췌)" });

  // 오른쪽 아래: 왜 S3 다음에 지우나(증분 색인 반영 순서)
  const QX = X0 + LW + 0.3, QW = XR - QX;
  L.text(s, "왜 S3 다음에 지우나: 증분 색인 반영 순서", { x: QX, y: BY, w: QW, h: 0.38, size: 15, color: C.navy,
    bold: true });
  const steps = [
    ["K4 ~ K6", "그래프에 새 청크 노드를 먼저 넣음", C.white, C.border, C.ink],
    ["S3", "검색엔진 문서를 새 청크로 바꿈", C.white, C.border, C.ink],
    ["K7", "그다음 옛 청크 노드를 지움", C.tint, C.blue, C.navy],
  ];
  const SH = 0.5, SG = 0.2;
  steps.forEach(([tag, txt, fill, line, color], i) => {
    const y = BY + 0.48 + i * (SH + SG);
    L.rr(s, { x: QX, y, w: QW, h: SH, fill, line });
    L.card(s, tag, { x: QX + 0.1, y: y + 0.08, w: 1.05, h: SH - 0.16, fill: i === 2 ? C.blue : C.navy, line: null,
      color: C.white, size: 14, bold: true, r: 0.06 });
    L.text(s, txt, { x: QX + 1.3, y, w: QW - 1.4, h: SH, size: 14, color, bold: i === 2 });
    if (i < steps.length - 1) {
      L.arrow(s, { x1: QX + 0.62, y1: y + SH + 0.02, x2: QX + 0.62, y2: y + SH + SG - 0.02, color: C.navy, width: 2 });
    }
  });
  const NY = BY + 0.48 + 3 * (SH + SG) - SG + 0.15;
  richCard(s, ["바뀌는 동안에도 검색 결과의 chunk_id가 그래프에 있음",
    "순서를 거꾸로 하면 옛 chunk_id의 청크 노드가 없는 순간이 생김"],
  { x: QX, y: NY, w: QW, h: END - NY, fill: C.navy, line: null, color: C.white, titleSize: 15, size: 14 });

  // 아래: 규칙 카드 3개
  const rules = [
    ["증분 색인에서만", "전체 재색인은 새 세대에 처음부터 써서 지울 것이 없음"],
    ["새로 넣은 청크 노드는 남김", "바뀐 문서는 잠시 두 벌, 이번 K4 것은 유지(run_id)"],
    ["근거가 남으면 유지", "겹친 조항처럼 다른 청크에 이어진 엔티티는 지우지 않음"],
  ];
  const RG = 0.2, RCW = (CW - (rules.length - 1) * RG) / rules.length, RY = END + 0.13, RCH = L.BODY_BOTTOM - RY;
  rules.forEach(([t, b], i) => {
    const x = X0 + i * (RCW + RG);
    L.rr(s, { x, y: RY, w: RCW, h: RCH, fill: C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.12, y: RY + 0.1, size: 0.34, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: x + 0.55, y: RY + 0.06, w: RCW - 0.65, h: 0.42, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.15, y: RY + 0.46, w: RCW - 0.3, h: RCH - 0.5, size: 14, color: C.body, valign: "top" });
  });
}

async function main() {
  L.createDeck();
  await createSlide01();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
