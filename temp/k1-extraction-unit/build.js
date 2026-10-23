// KG 구축 K1 추출 단위 나누기 장표 2장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "K1추출단위.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 14,
  titleSize = 15, align = "center", r = 0.08 }) {
  L.rr(s, { x, y, w, h, fill, line, r });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i === 0, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign: "middle", margin: 0.05, isTextBox: true,
    paraSpaceAfter: 1 });
}

// 화살표 위에 작은 라벨을 얹음
function labeledArrow(s, label, { x1, x2, y }) {
  L.arrow(s, { x1, y1: y, x2, y2: y, color: C.navy, width: 2 });
  L.text(s, label, { x: x1 - 0.05, y: y - 0.38, w: x2 - x1 + 0.1, h: 0.32, size: 14, color: C.navy, bold: true,
    align: "center", margin: 0 });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "KG 구축 K1 추출 단위 나누기",
    lead: "LLM에 한 번에 넣는 글 조각을 뜻 단위(조항)로 맞춤. 검색용 청크는 그대로 두고 추출 직전에만 나눔",
    notes: "추출 단위는 LLM에 한 번에 넣는 글 조각입니다. 검색용 청크는 800토큰 크기라 약관 청크 하나에 조항이 아홉 개씩 "
      + "들어 있습니다. 이걸 통째로 넣으면 모델에 따라 조항 안의 조건이나 기한을 놓칩니다. gpt-oss-120b는 청크째로는 조항과 "
      + "문서 노드만 뽑았고, Opus 5.5는 청크째로도 조건, 기한, 처리를 뽑았지만 같은 청크에서 조건 노드가 청크째 1개, 조항 단위 "
      + "4개였습니다. 실무 관행도 같은 방향입니다. GraphRAG 논문은 600토큰 청크에서 2400토큰보다 엔티티를 약 2배 뽑았다고 "
      + "보고했고, Microsoft GraphRAG와 LightRAG는 놓친 것을 한 번 더 묻는 추출을 기본으로 둡니다. 엔티티가 나온 청크 ID를 "
      + "여러 개 기록하는 것도 LightRAG와 Neo4j의 방식입니다.\n나누는 방법은 단순합니다. 조항 제목 줄을 찾되 바로 다음 줄이 ①로 "
      + "시작할 때만 조항의 시작으로 봅니다. 그래야 제목만 이어지는 차례가 단위가 되지 않습니다. 다음 제목 전까지를 한 단위로 "
      + "자르고, 청크가 겹쳐서 같은 조항이 두 번 나오면 하나만 남기되 나온 청크 ID를 모두 기억합니다. 추출 단위는 추출할 때만 "
      + "쓰는 임시 조각이라 그래프에 노드로 남기지 않습니다. 그래프의 청크 노드는 검색용 청크와 하나씩 맞고, 조항에서 뽑힌 "
      + "엔티티는 그 조항이 나온 청크마다 FROM_CHUNK로 이어집니다. 그래서 검색 결과의 chunk_id로 청크 노드를 바로 찾습니다.\n혜택 안내와 상담 기록은 청크가 이미 카드 하나, 상담 한 건이라 그대로 "
      + "씁니다.",
  });

  const PW = (CW - 0.3) / 2, RX = X0 + PW + 0.3;

  // ── 왼쪽 위: 왜 나누나
  L.headerBar(s, "왜 나누나", { x: X0, y: 1.9, w: PW, h: 0.45, size: 18 });
  const rows = [
    { y: 2.55, badge: "청크 그대로", bfill: C.dark, src: ["약관 청크 1개", "1,449자, 조항 9개"], srcFill: C.altRow,
      llm: "LLM 1번", out: ["조항, 문서 노드만", "조항 안 내용은 놓침"], outFill: C.dark },
    { y: 3.6, badge: "조항 단위", bfill: C.blue, src: ["조항 9개로 나눔", "제16조 ~ 제21조"],
      srcFill: C.tint, llm: "LLM 9번", out: ["조건, 기한, 처리", "노드가 나오기 시작"], outFill: C.blue },
  ];
  rows.forEach((r) => {
    L.card(s, r.badge, { x: X0, y: r.y, w: 1.45, h: 0.85, fill: r.bfill, line: null, color: C.white, size: 15,
      bold: true, r: 0.06 });
    richCard(s, r.src, { x: X0 + 1.6, y: r.y, w: 2.25, h: 0.85, fill: r.srcFill, line: C.border, color: C.ink });
    labeledArrow(s, r.llm, { x1: X0 + 3.92, x2: X0 + 4.83, y: r.y + 0.5 });
    richCard(s, r.out, { x: X0 + 4.9, y: r.y, w: PW - 4.9, h: 0.85, fill: r.outFill, line: null, color: C.white });
  });
  L.text(s, "약관 스키마 실험 결과. 조항 단위도 합격 기준은 아직 못 넘어 스키마 설명을 다듬는 중", { x: X0, y: 4.52,
    w: PW, h: 0.36, size: 14, color: C.sub });

  // ── 오른쪽 위: 어떻게 나누나
  L.headerBar(s, "어떻게 나누나 (약관)", { x: RX, y: 1.9, w: PW, h: 0.45, size: 18, accent: true });
  const how = [
    "조항 제목 줄 찾기: 「제16조(할부 거래)」 꼴",
    "다음 줄이 ①로 시작할 때만 시작점 (차례 줄은 건너뜀)",
    "다음 제목 전까지가 한 단위 (장 제목 줄은 버림)",
    "겹친 조항은 하나로 합치고, 나온 청크 ID를 모두 기억",
  ];
  how.forEach((t, i) => {
    const y = 2.47 + i * 0.6;
    L.rr(s, { x: RX, y, w: PW, h: 0.52, fill: i === 3 ? C.tint : C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: RX + 0.1, y: y + 0.07, size: 0.38, fill: i === 3 ? C.navy : C.blue, fsz: 16 });
    L.text(s, t, { x: RX + 0.6, y, w: PW - 0.7, h: 0.52, size: 15, color: i === 3 ? C.navy : C.ink, bold: i === 3 });
  });

  // ── 왼쪽 아래: 문서 종류별 추출 단위
  L.darkBadge(s, "문서 종류별 추출 단위", { x: X0, y: 5.05, w: 2.8, h: 0.38, size: 15 });
  L.table(s, [
    ["문서 종류", "추출 단위", "청크 → 단위"],
    ["약관", "조항 제목 줄로 나눔", "10 → 51"],
    ["혜택 안내", "청크 그대로 (카드 경계로 이미 나뉨)", "160 → 160"],
    ["상담 기록", "청크 그대로 (상담 1건)", "48 → 48"],
  ], { x: X0, y: 5.5, w: PW, colW: [1.55, 4.1, 1.65], rowH: 0.36, size: 15 });
  L.text(s, "약관 단위 길이 97 ~ 632자(중앙 147자). 차례뿐인 청크는 단위가 0개", { x: X0, y: 7.0, w: PW, h: 0.36,
    size: 14, color: C.sub });

  // ── 왼쪽 맨 아래: 실무 관행(사용자 요청으로 이 쪽만 짧은 출처 표기를 넣음. 원문 주소는 script.md 근거 표)
  const PY = 7.55, PH = 0.92;
  L.card(s, "실무 관행", { x: X0, y: PY, w: 1.25, h: PH, fill: C.dark, line: null, color: C.white, size: 15,
    bold: true, r: 0.13 });
  L.box(s, { x: X0 + 1.32, y: PY, w: PW - 1.32, h: PH, fill: C.altRow, line: null });
  const practice = [
    ["작게 나눌수록 더 뽑음 (600토큰 청크가 2400토큰의 약 2배)", "GraphRAG 논문 2024"],
    ["놓친 것 다시 묻기(gleaning) 1회가 기본값", "Microsoft GraphRAG, LightRAG"],
    ["엔티티는 나온 청크 ID를 여러 개 기록", "LightRAG, Neo4j GraphRAG"],
    ["법률 문서는 조, 항 같은 구조 단위로 나눔", "PROPOR 2026 논문"],
  ];
  const pruns = [];
  practice.forEach(([t, src], i) => {
    pruns.push({ text: t + "  ", options: { fontSize: fs(12), color: C.body, bullet: true } });
    pruns.push({ text: src, options: { fontSize: fs(10), color: C.sub, breakLine: i < practice.length - 1 } });
  });
  // pptxgenjs 여백은 포인트 단위이고 배열 순서는 [왼쪽, 오른쪽, 아래, 위]
  s.addText(pruns, { x: X0 + 1.32, y: PY, w: PW - 1.32, h: PH, fontFace: FONT, align: "left", valign: "middle",
    margin: [7, 7, 2, 2], isTextBox: true });

  // ── 오른쪽 아래: 검색 청크와 잇기
  L.darkBadge(s, "검색 청크와 잇기", { x: RX, y: 5.05, w: 2.3, h: 0.38, size: 15 });
  const FG = 0.3, FW = (PW - 2 * FG) / 3;
  const flow = [
    { lines: ["검색엔진이 찾은", "chunk_id"], fill: C.altRow },
    { lines: ["같은 chunk_id의", "청크 노드에서 엔티티"], fill: C.navy, color: C.white, line: null },
    { lines: ["질문에 필요한", "근거 노드"], fill: C.tint, line: C.blue, color: C.navy },
  ];
  flow.forEach((f, i) => {
    const x = RX + i * (FW + FG);
    richCard(s, f.lines, { x, y: 5.55, w: FW, h: 0.9, fill: f.fill, line: f.line === undefined ? C.border : f.line,
      color: f.color || C.ink });
    if (i < flow.length - 1) L.arrow(s, { x1: x + FW + 0.03, y1: 6.0, x2: x + FW + FG - 0.03, y2: 6.0 });
  });
  L.callout(s, "규칙은 스키마 승인 기록에서 가져옴.\n스키마 설계, 시험, 인덱싱이 모두 같은 단위를 씀",
    { x: RX, y: 6.65, w: PW, h: 0.75, size: 15 });
}

const CODE_SPLIT = String.raw`RULE = {"heading": r"^(제\d+조(?:의\d+)?)\(([^)]*)\)\s*$",  # 조항 제목 줄
        "body_start": "①",                     # 본문 시작 표시
        "drop_lines": r"^제\d+장\s"}           # 버릴 줄(장 제목)

def _split_by_heading(chunk, rule):
    heading = re.compile(rule["heading"])
    drop = (re.compile(rule["drop_lines"])
            if rule.get("drop_lines") else None)
    lines = chunk["text"].split("\n")
    nxt = lambda i: next((l.strip() for l in lines[i + 1:] if l.strip()), "")
    # 제목 줄이면서 다음 줄이 ①로 시작하는 줄만 시작점(차례 제외)
    starts = [i for i, l in enumerate(lines) if heading.match(l.strip())
              and nxt(i).startswith(rule["body_start"])]
    units = []
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        body = [l for l in lines[i:end]
                if not (drop and drop.match(l.strip()))]
        no = heading.match(lines[i].strip()).group(1)   # 제16조의2
        units.append({"text": "\n".join(body).strip(), "key": no,
                      "section_label": lines[i].strip()})
    return units`.split("\n");

// v0 kg_build.py k1_split_units 발췌. 앞부분(base, rule 준비와 규칙 없는 문서 처리)은 생략
const CODE_MERGE = String.raw`def k1_split_units(chunks, schemas):
    units, empty = {}, []
    for c in chunks:   # … 혜택, 상담은 청크 하나가 단위 하나
        for p in _split_by_heading(c, rule):
            uid = f"{base['doc_id']}#{p['key']}"
            old = units.get(uid)
            if old is None:
                units[uid] = {**base, "unit_id": uid, "text": p["text"],
                              "chunk_ids": [c["chunk_id"]]}
            elif c["chunk_id"] not in old["chunk_ids"]:  # 겹친 조항
                keep = max(old["text"], p["text"], key=len)
                old.update(text=keep, chunk_ids=
                    old["chunk_ids"] + [c["chunk_id"]])
    return list(units.values()), empty`.split("\n");

const CODE_RESULT = String.raw`{"unit_id": "D1_27223010abe31291#제16조의2",
 "text": "제16조의2(할부 거래의 철회 요청)\n① …",
 "chunk_ids": ["D1_…_112f1e4abea05436_0000",
               "D1_…_a4fd4ae81ec3f063_0000"]}`.split("\n");

async function createSlide02() {
  const s = L.newSlide({
    title: "K1 추출 단위 나누기 코드",
    lead: "제목 줄과 본문 시작 표시로 조항을 자르고, 겹친 조항은 합치면서 나온 청크 ID를 모음",
    notes: "규칙은 세 가지 값입니다. 조항 제목 꼴의 정규식, 본문 시작 표시 ①, 버릴 줄(장 제목)입니다. _split_by_heading은 "
      + "제목 줄 가운데 다음 줄이 ①로 시작하는 줄만 시작점으로 삼고, 다음 시작점 전까지를 한 단위로 자릅니다. 단위 ID는 "
      + "문서 ID와 조항 번호로 만들어서, 같은 조항이 겹침 구간 때문에 두 청크에 나오면 같은 ID가 됩니다.\nk1_split_units는 "
      + "같은 ID를 만나면 글이 더 긴 쪽을 남기고 두 청크의 ID를 chunk_ids에 모읍니다. 이 목록은 K4에서 뽑힌 엔티티를 어느 "
      + "청크 노드에 이을지 정하는 데만 쓰고, 추출 단위 자체는 그래프에 남기지 않습니다. 약관 청크 10개에서 단위 51개가 "
      + "나왔고, 그중 13개는 두 청크에 걸쳐 있었습니다.",
  });

  const LW = 8.15, RX = X0 + LW + 0.3, RW = XR - RX;
  L.codeBox(s, CODE_SPLIT, { x: X0, y: 1.9, w: LW, h: 6.05, size: 14,
    title: "조항 나누기 코드 예제" });
  L.codeBox(s, CODE_MERGE, { x: RX, y: 1.9, w: RW, h: 4.0, size: 14, title: "k1_split_units: 겹친 조항 합치기" });
  L.codeBox(s, CODE_RESULT, { x: RX, y: 6.0, w: RW, h: 1.43, size: 14, title: "결과 예 (약관 청크 10개 → 단위 51개)" });
  L.card(s, "각 추출 단위는 여러 개의 청크에 소속될 수 있음", { x: RX, y: 7.5,
    w: RW, h: 0.45, fill: C.blue, line: null, color: C.white, size: 14, bold: true });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlide01, createSlide02]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
