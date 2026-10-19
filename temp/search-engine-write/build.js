// 검색 갈래 ③ 검색 엔진에 쓰기 장표 2장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "검색엔진쓰기.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 14,
  titleSize = 16, align = "center", r = 0.08, dash }) {
  L.rr(s, { x, y, w, h, fill, line, r, dash });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i === 0, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign: "middle", margin: 0.06, isTextBox: true,
    paraSpaceAfter: 2 });
}

// 청크 칸 한 줄. kind: plain(흰 칸), edited(고친 청크, 블루), orphan(고아, 점선 회색)
const SQ = 0.46, SG = 0.07;
function chunkRow(s, cells, { x, y }) {
  cells.forEach(([label, kind], i) => {
    const cx = x + i * (SQ + SG);
    const style = {
      plain: { fill: C.white, line: C.border, color: C.ink, bold: false },
      edited: { fill: C.blue, line: null, color: C.white, bold: true },
      orphan: { fill: C.altRow, line: C.sub, color: C.sub, bold: true, dash: "dash" },
    }[kind];
    L.card(s, label, { x: cx, y, w: SQ, h: SQ, fill: style.fill, line: style.line, color: style.color,
      size: 14, bold: style.bold, dash: style.dash, r: 0.05 });
  });
  return x + cells.length * (SQ + SG) - SG;
}

const nums = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => [String(from + i), "plain"]);

async function createSlide01() {
  const s = L.newSlide({
    title: "검색 갈래 ③ 검색 엔진에 쓰기",
    lead: "문서 하나를 통째로 지우고 다시 넣어, 고친 문서의 옛 청크가 남지 않게 함",
    notes: "검색 엔진에 쓸 때는 청크 하나를 엔진 문서 하나로 넣습니다. 문제는 문서를 고쳤을 때입니다. 청크 ID에는 본문 "
      + "해시가 들어 있어서 본문이 바뀌면 ID도 바뀝니다. 그래서 청크 ID로 덮어쓰기만 하면 옛 ID의 청크와 빠진 청크가 지울 "
      + "주인 없이 남습니다. 이렇게 남은 고아 청크는 이미 고친 옛 내용을 검색 결과에 섞어 냅니다.\n"
      + "그래서 문서 키로 그 문서의 청크를 먼저 모두 지우고 새 청크를 넣습니다. 문서 키는 청크 ID의 앞 칸이라 본문이 "
      + "바뀌어도 변하지 않습니다.",
  });

  // 맨 위 줄: 고친 문서
  const TY = 1.98;
  L.darkBadge(s, "고친 문서", { x: X0, y: TY, w: 1.45, h: SQ, size: 16 });
  const bx = 2.2;
  const bEnd = chunkRow(s, nums(1, 10), { x: bx, y: TY });
  L.text(s, "고치기 전 약관 문서 청크 10개", { x: bx, y: TY + 0.5, w: 5.3, h: 0.34, size: 14, color: C.sub,
    align: "center" });
  const ax = 10.75;
  L.arrow(s, { x1: bEnd + 0.15, y1: TY + SQ / 2, x2: ax - 0.15, y2: TY + SQ / 2, color: C.navy, width: 2 });
  L.text(s, "1번 본문 수정(ID 바뀜)\n10번 삭제", { x: bEnd + 0.1, y: TY + 0.5, w: ax - bEnd - 0.2, h: 0.5,
    size: 14, color: C.navy, bold: true, align: "center" });
  chunkRow(s, [["1′", "edited"], ...nums(2, 9)], { x: ax, y: TY });
  L.text(s, "고친 뒤 9개", { x: ax, y: TY + 0.5, w: 4.7, h: 0.34, size: 14, color: C.sub, align: "center" });

  // 가운데 두 칸
  const PY = 3.08, PW = (CW - 0.3) / 2, RX = X0 + PW + 0.3;
  L.card(s, "청크 단위로 교체하는 방식 (chunk_id 기준)", { x: X0, y: PY, w: PW, h: 0.45, fill: C.dark, line: null,
    color: C.white, size: 17, bold: true, r: 0.06 });
  L.card(s, "문서 단위로 교체하는 방식 (doc_id 기준)", { x: RX, y: PY, w: PW, h: 0.45, fill: C.blue, line: null,
    color: C.white, size: 17, bold: true, r: 0.06 });
  L.rr(s, { x: X0, y: PY + 0.52, w: PW, h: 1.72, fill: C.white, line: C.border });
  L.rr(s, { x: RX, y: PY + 0.52, w: PW, h: 1.72, fill: C.white, line: C.border });

  // 왼쪽: 같은 ID는 덮어써지지만 옛 1번과 빠진 10번은 남음
  L.text(s, "chunk_id로 덮어쓴 뒤 인덱스에 남은 청크", { x: X0 + 0.2, y: PY + 0.58, w: PW - 0.4, h: 0.4, size: 15,
    color: C.slate });
  const lCells = [["옛1", "orphan"], ["1′", "edited"], ...nums(2, 9), ["10", "orphan"]];
  const lw = lCells.length * (SQ + SG) - SG;
  chunkRow(s, lCells, { x: X0 + (PW - lw) / 2, y: PY + 1.02 });
  richCard(s, ["11개 남음", "옛 1번과 빠진 10번(고아)이 검색에 섞여 나옴"], { x: X0 + 0.2, y: PY + 1.56, w: PW - 0.4,
    h: 0.6, fill: C.dark, line: null, color: C.white, size: 15, titleSize: 16 });

  // 오른쪽: 문서 키로 지운 뒤 9개를 넣음
  const fw = (PW - 0.4 - 0.45) / 2;
  L.card(s, "doc_id가 같은 청크 10개 지움", { x: RX + 0.2, y: PY + 0.6, w: fw, h: 0.38, fill: C.tint, line: C.border,
    color: C.navy, size: 15, bold: true });
  L.arrow(s, { x1: RX + 0.2 + fw + 0.05, y1: PY + 0.79, x2: RX + 0.2 + fw + 0.4, y2: PY + 0.79 });
  L.card(s, "새 청크 9개 넣음", { x: RX + 0.2 + fw + 0.45, y: PY + 0.6, w: fw, h: 0.38, fill: C.tint, line: C.border,
    color: C.navy, size: 15, bold: true });
  const rCells = [["1′", "edited"], ...nums(2, 9)];
  const rw = rCells.length * (SQ + SG) - SG;
  chunkRow(s, rCells, { x: RX + (PW - rw) / 2, y: PY + 1.02 });
  richCard(s, ["9개만 남음", "고친 내용만 검색되고 고아 청크 없음"], { x: RX + 0.2, y: PY + 1.56, w: PW - 0.4, h: 0.6,
    fill: C.blue, line: null, color: C.white, size: 15, titleSize: 16 });

  // 아래: 엔진 문서 하나 = 청크 하나
  const BY = 5.5;
  L.headerBar(s, "검색 엔진에 넣는 한 건 = 청크 하나", { x: X0, y: BY, w: CW, h: 0.45, size: 18 });
  const fields = [
    { lines: ["_id = chunk_id", "같은 청크는 덮어씀"], fill: C.navy, color: C.white },
    { lines: ["doc_id", "지울 때 쓰는 원천 문서 키"], fill: C.blue, color: C.white },
    { lines: ["text_hash", "벡터 재사용 판단"] },
    { lines: ["text", "보여 주기용, 색인 안 함"] },
    { lines: ["text_tokens", "토큰화된 낱말"] },
    { lines: ["embedding", "색인용 본문을 벡터화"] },
    { lines: ["메타데이터", "카드명, 회원 키 등 필터"] },
  ];
  const FG = 0.12, FW = (CW - 6 * FG) / 7;
  fields.forEach((f, i) => {
    richCard(s, f.lines, { x: X0 + i * (FW + FG), y: BY + 0.55, w: FW, h: 0.95, fill: f.fill || C.altRow,
      line: f.fill ? null : C.border, color: f.color || C.ink, size: 14, titleSize: 16 });
  });

  const DY = 7.15;
  L.darkBadge(s, "doc_id 만드는 법", { x: X0, y: DY, w: 2.1, h: 0.75, size: 16 });
  const parts = [
    { lines: ["D1_27223010abe31291", "문서 키"], w: 3.1, fill: C.blue, color: C.white },
    { lines: ["_112f1e4abea05436", "본문 해시"], w: 2.8 },
    { lines: ["_0000", "청크 순번"], w: 1.2 },
  ];
  let px = X0 + 2.25;
  parts.forEach((pt) => {
    richCard(s, pt.lines, { x: px, y: DY, w: pt.w, h: 0.75, fill: pt.fill || C.white,
      line: pt.fill ? null : C.border, color: pt.color || C.ink, size: 14, titleSize: 15, r: 0.04 });
    px += pt.w + 0.04;
  });
  L.arrow(s, { x1: px + 0.1, y1: DY + 0.375, x2: px + 0.55, y2: DY + 0.375, color: C.navy, width: 2 });
  L.text(s, "chunk_id의 앞 칸만 남기면 doc_id.\n본문이 바뀌어도 문서 키는 그대로", { x: px + 0.65, y: DY, w: XR - px - 0.65, h: 0.75,
    size: 15, color: C.navy, bold: true });
}

async function createSlide02() {
  const s = L.newSlide({
    title: "③ 검색 엔진에 쓰기 코드",
    lead: "문서별로 묶고, 옛 청크를 지우고, 새 청크를 한꺼번에 넣은 뒤 바로 보이게 함",
    notes: "코드는 네 덩어리입니다. 먼저 들어온 청크를 문서 키로 묶습니다. 다음으로 문서마다 delete_by_query로 그 문서의 "
      + "옛 청크를 모두 지웁니다. refresh를 켜 두어야 지운 결과가 바로 반영됩니다. 그다음 bulk로 새 청크를 한꺼번에 넣는데, "
      + "이때 _id를 청크 ID로 고정해 두면 같은 입력을 두 번 넣어도 건수가 늘지 않습니다. 마지막으로 refresh를 불러 다음 "
      + "검색부터 보이게 합니다.\n시험에서는 고친 문서를 다시 쓸 때 옛 청크 9개를 지우고 10개를 넣었고, 남은 고아 청크는 "
      + "없었습니다. 지금 쓰는 인덱스에 바로 쓰면 지우기와 넣기 사이에 그 문서가 잠깐 보이지 않으므로, 전체 재색인은 새 "
      + "세대에 쓰고 별칭을 바꿉니다.\n별칭은 1-a의 활성 세대 파일(active_generation.json)과 같은 역할입니다. 둘 다 검색이 "
      + "보는 이름표이고, 새 세대를 다 만든 뒤 이름표만 바꿉니다. 차이는 반영 방식입니다. 1-a는 리트리버가 파일을 읽고 새 "
      + "세대를 메모리에 다시 올려야 하고, 1-b는 이름표가 검색 엔진 안에 있어 바꾸는 즉시 모든 검색에 적용됩니다.",
  });

  const code = [
    "def step3_write_documents(client, index, documents):",
    "    # ① 문서(doc_id)별로 묶음",
    "    grouped = {}",
    "    for document in documents:",
    "        grouped.setdefault(document[\"doc_id\"], []).append(document)",
    "    # ② 문서마다 옛 청크를 통째로 지움",
    "    deleted = 0",
    "    for doc_id in grouped:",
    "        response = client.delete_by_query(",
    "            index=index,",
    "            body={\"query\": {\"term\": {\"doc_id\": doc_id}}},",
    "            refresh=True, conflicts=\"proceed\")",
    "        deleted += response.get(\"deleted\", 0)",
    "    # ③ 새 청크를 한꺼번에 넣음 (_id = chunk_id)",
    "    actions = [{\"_index\": index, \"_id\": d[\"chunk_id\"], \"_source\": d}",
    "               for docs in grouped.values() for d in docs]",
    "    helpers.bulk(client, actions, max_retries=3)",
    "    # ④ 바로 검색되게 반영",
    "    client.indices.refresh(index=index)",
    "    return WriteReport(deleted, len(actions), tuple(grouped))",
  ];
  const CWID = 7.9;
  L.codeBox(s, code, { x: X0, y: 1.9, w: CWID, h: 6.05, size: 14,
    title: "search_branch.py 발췌 (타입 표기와 설명 주석은 줄임)" });

  // 오른쪽: 단계별 설명
  const RX = X0 + CWID + 0.3, RW = XR - RX;
  const steps = [
    { h: 0.78, title: "문서별로 묶음", body: "여러 문서가 한꺼번에 들어와도 문서마다 따로 지움" },
    { h: 1.2, title: "옛 청크 지우기",
      body: "term doc_id로 그 문서 청크를 모두 지움. refresh=True라 바로 반영되고, conflicts=\"proceed\"는 충돌이 나도 멈추지 않음" },
    { h: 0.98, title: "한꺼번에 넣기",
      body: "_id를 chunk_id로 고정해 같은 입력을 두 번 넣어도 건수가 그대로임. 일부가 실패하면 BulkIndexError" },
    { h: 0.72, title: "반영", body: "넣은 청크가 다음 검색부터 보임" },
  ];
  let y = 1.9;
  steps.forEach((st, i) => {
    L.rr(s, { x: RX, y, w: RW, h: st.h, fill: i === 1 || i === 2 ? C.tint : C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: RX + 0.15, y: y + 0.1, size: 0.38, fill: C.blue, fsz: 16 });
    L.text(s, st.title, { x: RX + 0.65, y: y + 0.06, w: RW - 0.8, h: 0.38, size: 16, color: C.navy, bold: true });
    L.text(s, st.body, { x: RX + 0.65, y: y + 0.42, w: RW - 0.8, h: st.h - 0.46, size: 14, color: C.body,
      valign: "top" });
    y += st.h + 0.08;
  });

  L.card(s, "시험 결과: 옛 청크 9개 지움 → 10개 넣음, 고아 0개", { x: RX, y: 5.9, w: RW, h: 0.42, fill: C.blue,
    line: null, color: C.white, size: 15, bold: true });

  // 세대 전환 이름표: 1-a의 활성 세대 파일과 1-b의 별칭은 같은 역할, 반영 방식만 다름
  L.callout(s, "운영 중인 인덱스에 바로 쓰면 ②와 ③ 사이에 그 문서가 잠깐 안 보임.\n"
    + "그래서 전체 재색인은 새 세대에 쓰고 검색이 보는 이름표만 바꿈", { x: RX, y: 6.4, w: RW, h: 0.6, size: 14 });
  const NW = (RW - 0.15) / 2;
  const tags = [
    { lines: ["벡터DB 인덱싱의 활성 세대 파일", "active_generation.json 교체", "리트리버가 새 세대를 다시 읽어 올림"],
      fill: C.altRow, line: C.border, color: C.ink },
    { lines: ["검색엔진 별칭", "card_chunks를 새 인덱스로 옮김", "엔진 안 이름표라 모든 검색에 바로 적용"],
      fill: C.tint, line: C.blue, color: C.navy },
  ];
  tags.forEach((t, i) => {
    const x = RX + i * (NW + 0.15);
    L.rr(s, { x, y: 7.08, w: NW, h: 0.87, fill: t.fill, line: t.line });
    s.addText(t.lines.map((v, j) => ({ text: v, options: { bold: j === 0, fontSize: fs(j === 0 ? 15 : 14),
      color: t.color, breakLine: j < t.lines.length - 1 } })),
    { x, y: 7.08, w: NW, h: 0.87, fontFace: FONT, align: "center", valign: "middle", margin: 0.04, isTextBox: true });
  });
}

async function createSlide03() {
  const s = L.newSlide({
    title: "벡터 색인과 키워드 색인을 한 번에 구축",
    lead: "검색 엔진 인덱스 하나가 벡터 검색과 키워드 검색을 모두 맡아, 청크 한 건에 담아 한 번에 넣음",
    notes: "검색 엔진 방식에서는 따로 된 벡터DB가 없습니다. 검색 엔진 인덱스 하나에 벡터 필드와 키워드 필드가 함께 있어서, "
      + "청크 한 건을 넣으면 벡터 색인과 키워드 역색인이 같은 순간에 갱신됩니다. 다만 벡터를 만드는 임베딩과 낱말을 만드는 "
      + "키워드 분석은 그 전에 파이썬에서 따로 합니다.\n벡터DB 인덱싱은 벡터를 Chroma에, 점수표를 파일에 따로 만든 뒤 활성 "
      + "세대 파일 하나로 함께 바꿉니다. 어느 쪽이든 벡터 검색과 키워드 검색은 늘 같은 세대를 봅니다.",
  });

  // 위쪽 흐름도: 청크 → 재료 두 가지(파이썬) → 한 건 → bulk 한 번 → 인덱스 하나 안의 두 색인
  const CY = 2.55, CH = 1.3;
  richCard(s, ["청크", "색인용 본문"], { x: X0, y: CY, w: 1.5, h: CH, fill: C.tint, size: 14, titleSize: 17 });
  const BX = 2.45, BW2 = 2.75;
  richCard(s, ["① 임베딩", "→ 벡터 768차원"], { x: BX, y: 2.0, w: BW2, h: 1.0, size: 15, titleSize: 16 });
  richCard(s, ["② 키워드 분석", "→ text_tokens 낱말"], { x: BX, y: 3.4, w: BW2, h: 1.0, size: 15, titleSize: 16 });
  L.text(s, "파이썬에서 따로 만듦", { x: BX, y: 4.43, w: BW2, h: 0.32, size: 14, color: C.sub, align: "center" });
  L.arrow(s, { x1: X0 + 1.55, y1: CY + 0.35, x2: BX - 0.05, y2: 2.5 });
  L.arrow(s, { x1: X0 + 1.55, y1: CY + CH - 0.35, x2: BX - 0.05, y2: 3.9 });

  const MX = 5.6, MW = 2.3;
  richCard(s, ["엔진 문서 한 건", "벡터 + text_tokens", "+ 메타데이터"], { x: MX, y: CY, w: MW, h: CH, fill: C.navy,
    line: null, color: C.white, size: 15, titleSize: 17 });
  L.arrow(s, { x1: BX + BW2 + 0.05, y1: 2.5, x2: MX - 0.05, y2: CY + 0.35 });
  L.arrow(s, { x1: BX + BW2 + 0.05, y1: 3.9, x2: MX - 0.05, y2: CY + CH - 0.35 });

  const EX = 9.6, EW = XR - EX;
  L.arrow(s, { x1: MX + MW + 0.05, y1: CY + CH / 2, x2: EX - 0.05, y2: CY + CH / 2, color: C.navy, width: 2.5 });
  L.text(s, "③ bulk 한 번", { x: MX + MW, y: CY + CH / 2 - 0.42, w: EX - MX - MW, h: 0.36, size: 15, color: C.navy,
    bold: true, align: "center" });

  L.rr(s, { x: EX, y: 1.95, w: EW, h: 2.8, fill: C.white, line: C.blue, lw: 1.5 });
  L.text(s, "검색 엔진 인덱스 하나 (card_chunks-gen-…)", { x: EX + 0.15, y: 2.0, w: EW - 0.3, h: 0.4, size: 16,
    color: C.navy, bold: true });
  richCard(s, ["embedding 필드 → 벡터 색인", "HNSW 그래프, kNN 검색에 씀"], { x: EX + 0.2, y: 2.45, w: EW - 0.4, h: 0.82,
    fill: C.tint, line: C.border, color: C.navy, size: 14, titleSize: 16 });
  richCard(s, ["text_tokens 필드 → 키워드 역색인", "낱말 → 청크 목록, BM25 점수에 씀"], { x: EX + 0.2, y: 3.35,
    w: EW - 0.4, h: 0.82, fill: C.tint, line: C.border, color: C.navy, size: 14, titleSize: 16 });
  L.card(s, "refresh → 둘이 함께 검색 가능", { x: EX + 0.2, y: 4.25, w: EW - 0.4, h: 0.4, fill: C.blue, line: null,
    color: C.white, size: 15, bold: true });

  // 아래: 벡터DB 인덱싱과 비교
  L.table(s, [
    ["항목", "벡터DB 인덱싱", "검색 엔진"],
    ["저장소", "벡터는 Chroma, 키워드는 bm25s 파일 (두 군데)", "검색 엔진 인덱스 한 군데"],
    ["구축 순서", "벡터를 Chroma에 먼저 넣고, BM25 점수표 파일을 따로 만듦", "bulk 한 번에 둘 다"],
    ["어긋나지 않게", "둘 다 만든 뒤 활성 세대 파일 하나로 함께 게시", "같은 한 건에 들어 있어 어긋날 수 없음"],
    ["지우기", "저장소마다 따로 처리", "delete_by_query 한 번에 둘 다"],
  ], { y: 5.0, colW: [2.0, 6.7, 6.2], rowH: 0.45, size: 15 });
  L.callout(s, "벡터DB 인덱싱은 따로 만들고 마지막에 함께 바꾸고, 검색 엔진은 처음부터 함께 넣음",
    { y: 7.42, h: 0.5, size: 16 });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlide01, createSlide02, createSlide03]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
