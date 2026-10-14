// node build.js — 벡터검색을 Native Neo4j 벡터 인덱스로(인덱싱·검색 / 검색 세대 구성) 두 장 빌드 (script.md 슬라이드 1 · 2)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

// 칩 흐름: 칩 사이에 화살표(또는 '+')를 넣어 한 줄로 그림
function chipFlow(s, items, { x, y, w, h, gap = 0.3, joins = [], size = 14 }) {
  const cw = (w - gap * (items.length - 1)) / items.length;
  items.forEach((it, i) => {
    const cx = x + i * (cw + gap);
    const st = it.style || "plain";
    const look = {
      plain: { fill: C.white, line: C.slate, color: C.ink },
      navy: { fill: C.navy, line: null, color: C.white },
      blue: { fill: C.blue, line: null, color: C.white },
      tint: { fill: C.tint, line: C.blue, color: C.navy },
    }[st];
    L.card(s, it.t, { x: cx, y, w: cw, h, ...look, size, bold: true, r: 0.08 });
    if (i < items.length - 1) {
      if (joins[i] === "+") {
        L.text(s, "+", { x: cx + cw, y, w: gap, h, size: 20, bold: true, color: C.slate, align: "center", margin: 0 });
      } else {
        L.arrow(s, { x1: cx + cw + 0.03, y1: y + h / 2, x2: cx + cw + gap - 0.03, y2: y + h / 2, color: C.slate,
          width: 1.5 });
      }
    }
  });
}

// 구역 머리: 다크 배지 한 줄
function sectionLabel(s, t, { x, y, w }) {
  L.darkBadge(s, t, { x, y, w, h: 0.4, size: 16, fill: C.navy });
}

// 그래프 노드: 굵은 이름 + 옅은 라벨
function gNode(s, { x, y, w, h, name, label, fill = C.tint, line = C.navy }) {
  L.rr(s, { x, y, w, h, fill, line, lw: 1.5, r: 0.12 });
  s.addText([
    { text: name, options: { fontSize: fs(15), bold: true, color: C.navy, breakLine: !!label } },
    ...(label ? [{ text: label, options: { fontSize: fs(14), color: C.slate } }] : []),
  ], { x, y, w, h, fontFace: FONT, align: "center", valign: "middle", margin: 0.02, isTextBox: true, paraSpaceAfter: 0 });
}

function relLabel(s, t, { x, y, w }) {
  L.text(s, t, { x, y, w, h: 0.28, size: 14, bold: true, color: C.blue, align: "center", margin: 0 });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "벡터검색을 Native Neo4j 벡터 인덱스로",
    lead: "청크·벡터·그래프를 Neo4j 한 곳에 담고, 하이브리드 검색의 키워드 쪽은 기존 BM25 인덱스를 그대로 씀",
    notes: "기존 인덱서가 만든 청크를 그대로 TextChunk로 바꿔 Neo4j에 넣음. 정제·가명처리·청킹은 기존 코드가 함. "
      + "uid는 저장할 때만 쓰고 지워지므로, 검색 결과를 BM25와 맞추려면 chunk_id를 metadata에 넣어 속성으로 남겨야 함. "
      + "metadata에 embedding을 넣으면 벡터 속성으로 저장돼 다시 임베딩하지 않아도 됨. 질문 임베딩도 같은 KURE-v2를 써야 함. "
      + "member_scope는 상담 이력이 아니면 'all', 상담 이력이면 회원 가명임. Neo4j 2026.09 벡터 필터는 같음(=)과 범위만 받아 "
      + "'상담이 아니거나 그 회원'이라는 OR 조건을 넘길 수 없으므로, member_scope = 'all' 검색과 = 회원 검색을 따로 해 점수순으로 합침. "
      + "후보를 넉넉히 받아 앱에서 거르는 방식은 시험에서 20문항 중 3문항이 틀렸음. "
      + "기본 VectorRetriever는 이 버전 조합에서 걸러 낼 속성을 못 읽어 필터가 늘 전수 비교가 되므로 하위 클래스로 보완함. "
      + "인덱스 기본 압축(BINARY) 때문에 후보 배수를 4로 둬야 기존 Chroma와 60/60 같았음(배수 1은 40/60). "
      + "하이브리드: HybridRetriever는 Neo4j 전문 색인만 연결할 수 있어 쓰지 않고, 기존 BM25와 기존 가중합(0.6 : 0.4)으로 합침. "
      + "Neo4j 점수는 (1+cos)/2라 값은 다르지만 최소-최대 정규화 뒤 같아져 순위가 그대로임. "
      + "그래프 확장은 찾은 chunk_id에서 FROM_CHUNK를 거꾸로 따라가 엔티티와 관계를 모음. "
      + "검증: hybrid-ai-lab/verify/neo4j-vector-search 시험 24건 통과(2026-10-13).",
  });
  L.card(s, "실측 검증 60/60 일치", { x: X0 + CW - 2.3, y: 1.28, w: 2.3, h: 0.38, fill: C.blue, line: null,
    color: C.white, size: 15, bold: true, r: 0.19 });

  // ① 인덱싱(왼쪽 위)
  const lw = 7.4, rx = X0 + lw + 0.25, rw = CW - lw - 0.25;
  sectionLabel(s, "① 인덱싱 — 기존 청크를 Neo4j에 담기", { x: X0, y: 1.9, w: lw });
  chipFlow(s, [{ t: "청킹(기존 코드)" }, { t: "TextChunk 만들기", style: "tint" }, { t: "Neo4jWriter 저장", style: "navy" },
    { t: "벡터 인덱스 생성", style: "navy" }], { x: X0, y: 2.42, w: lw, h: 0.42, gap: 0.25 });
  L.codeBox(s, [
    "TextChunk(text=c.text, index=i, uid=c.chunk_id, metadata={",
    "    \"chunk_id\": c.chunk_id, \"generation\": gen, \"access_level\": c.level,",
    "    \"member_scope\": c.member or \"all\", \"embedding\": c.vector})",
    "create_vector_index(driver, \"chunk_vec\", label=\"Chunk\",",
    "    embedding_property=\"embedding\", dimensions=768, similarity_fn=\"cosine\",",
    "    filterable_properties=[\"generation\", \"access_level\", \"member_scope\"])",
  ], { x: X0, y: 2.95, w: lw, h: 1.66, size: 14 });
  L.text(s, "• uid는 임시 ID라 chunk_id는 metadata에 · 기존 벡터(768차원)를 넣어 재사용\n"
    + "• member_scope: 상담이 아니면 \"all\", 상담이면 회원 가명 → 회원 필터를 $eq로",
  { x: X0, y: 4.64, w: lw, h: 0.5, size: 14, color: C.slate, margin: 0, valign: "top" });

  // Neo4j에 담긴 모습(오른쪽 위) — 엔티티 줄 / 청크 줄 두 층, 관계 이름은 화살표 위·아래 빈칸에 둠
  sectionLabel(s, "Neo4j에 담긴 모습", { x: rx, y: 1.9, w: rw });
  L.rr(s, { x: rx, y: 2.36, w: rw, h: 2.78, fill: C.white, line: C.border, r: 0.08 });
  const nw = 1.3, eY = 2.62, eH = 0.5, cY = 3.68, cH = 0.5;
  const c1 = rx + 0.25, c2 = rx + 3.0, dX = rx + rw - 0.25 - 1.35;
  gNode(s, { x: c1, y: eY, w: nw, h: eH, name: "A사", fill: C.white, line: C.blue });
  gNode(s, { x: c2, y: eY, w: nw, h: eH, name: "B카드", fill: C.white, line: C.blue });
  gNode(s, { x: c1, y: cY, w: nw, h: cH, name: "Chunk 1" });
  gNode(s, { x: c2, y: cY, w: nw, h: cH, name: "Chunk 2" });
  gNode(s, { x: dX, y: cY, w: 1.35, h: cH, name: "Document", fill: C.altRow, line: C.slate });
  L.arrow(s, { x1: c1 + nw + 0.03, y1: eY + eH / 2, x2: c2 - 0.03, y2: eY + eH / 2, color: C.navy, width: 1.75 });
  relLabel(s, "LAUNCHED", { x: c1 + nw, y: eY - 0.06, w: c2 - c1 - nw });
  [c1, c2].forEach((cx) => L.arrow(s, { x1: cx + nw / 2, y1: eY + eH + 0.03, x2: cx + nw / 2, y2: cY - 0.03,
    color: C.navy, width: 1.5 }));
  relLabel(s, "FROM_CHUNK", { x: c1 + nw / 2 + 0.1, y: eY + eH + 0.14, w: 1.4 });
  L.arrow(s, { x1: c1 + nw + 0.03, y1: cY + cH / 2, x2: c2 - 0.03, y2: cY + cH / 2, color: C.slate, width: 1.5 });
  relLabel(s, "NEXT_CHUNK", { x: c1 + nw, y: cY + cH + 0.02, w: c2 - c1 - nw });
  L.arrow(s, { x1: c2 + nw + 0.03, y1: cY + cH / 2, x2: dX - 0.03, y2: cY + cH / 2, color: C.slate, width: 1.5 });
  relLabel(s, "FROM_DOCUMENT", { x: c2 + nw - 0.25, y: cY - 0.3, w: dX - c2 - nw + 0.5 });
  L.text(s, "Chunk 속성: chunk_id · text · embedding · generation · 등급 · member_scope",
    { x: rx + 0.15, y: 4.5, w: rw - 0.3, h: 0.27, size: 14, color: C.ink, margin: 0 });
  L.card(s, "벡터 인덱스 chunk_vec = Chunk.embedding", { x: rx + 0.15, y: 4.79, w: rw - 0.3, h: 0.3, fill: C.tint,
    line: C.blue, color: C.navy, size: 14, bold: true, r: 0.16 });

  // ② 검색 3가지(아래)
  sectionLabel(s, "② 검색 4가지", { x: X0, y: 5.24, w: CW });
  const rows = [
    { tag: "벡터", items: [{ t: "질문" }, { t: "VectorRetriever\n(속성 인식 보완)", style: "navy" }, { t: "chunk_id 목록" }],
      joins: [], desc: "세대 · 등급을 $eq로 인덱스 안에서 거름\n후보 배수 4(압축 보정)" },
    { tag: "회원 필터", items: [{ t: "member_scope\n= \"all\"", style: "navy" }, { t: "member_scope\n= 회원", style: "navy" },
      { t: "점수순 합침" }], joins: ["+"], desc: "$or · $ne는 전수 비교 · 서버 거부\n→ $eq 검색 2번" },
    { tag: "하이브리드", items: [{ t: "Neo4j 벡터 결과", style: "navy" }, { t: "기존 BM25 결과\n(bm25s · Kiwi)", style: "blue" },
      { t: "가중합 0.6 : 0.4\n(weighted_hybrid)", style: "tint" }], joins: ["+"],
    desc: "HybridRetriever 대신 기존 BM25 유지\n점수는 정규화돼 순위 그대로", strong: true },
    { tag: "그래프 확장", items: [{ t: "chunk_id" }, { t: "FROM_CHUNK로\n엔티티", style: "navy" }, { t: "관계 따라감" }],
      joins: [], desc: "VectorCypherRetriever\n또는 Cypher 직접 작성" },
  ];
  const tagW = 1.5, flowW = 7.7, dx = X0 + tagW + 0.2 + flowW + 0.25, dw = X0 + CW - dx;
  rows.forEach((r, i) => {
    const y = 5.66 + i * 0.575, h = 0.54;
    L.rr(s, { x: X0, y, w: CW, h, fill: r.strong ? C.tint : C.white, line: r.strong ? C.blue : C.border,
      lw: r.strong ? 1.5 : 1, r: 0.08 });
    L.card(s, r.tag, { x: X0 + 0.1, y: y + 0.07, w: tagW, h: h - 0.14, fill: r.strong ? C.blue : C.dark, line: null,
      color: C.white, size: 16, bold: true, r: 0.06 });
    chipFlow(s, r.items, { x: X0 + tagW + 0.2, y: y + 0.03, w: flowW, h: h - 0.06, joins: r.joins });
    L.text(s, r.desc, { x: dx, y: y + 0.02, w: dw - 0.1, h: h - 0.04, size: 14, color: r.strong ? C.navy : C.ink,
      bold: !!r.strong, margin: 0 });
  });
  return s;
}

async function createSlide02() {
  const s = L.newSlide({
    title: "검색 세대 구성: Neo4j와 BM25를 한 세대로",
    lead: "새 세대를 다 만든 뒤 포인터 하나만 바꿔, 검색기가 늘 같은 세대의 벡터·그래프·BM25를 보게 함",
    notes: "지금 인덱서는 Chroma와 BM25를 같은 세대 폴더에 만들고 active_generation.json을 한 번에 바꿈. 검색기는 포인터를 "
      + "한 번 읽고 같은 세대의 두 경로를 씀. Neo4j로 바꿔도 이 원칙은 그대로 둠. 차이는 Neo4j 쪽 세대를 폴더가 아니라 "
      + "노드의 generation 속성으로 구분한다는 점이며, 한 DB에 여러 세대가 같이 있음. 엔티티는 추출기가 만들 때 generation이 "
      + "붙지 않으므로, 저장 뒤 해당 세대 청크와 FROM_CHUNK로 이어진 엔티티에 표시함. 병합기를 그냥 돌리면 이전 세대 "
      + "엔티티와도 합쳐 세대가 섞이므로 filter_query로 새 세대만 대상으로 함. 검증을 통과해야 포인터를 바꿈. 되돌릴 때는 "
      + "포인터를 이전 세대로 바꾸면 Neo4j 값과 BM25 경로가 함께 돌아감. "
      + "검증(2026-10-13, hybrid-ai-lab/verify/neo4j-vector-search, Neo4j 2026.09.0 · neo4j-graphrag 1.22.0): 게시 · 전환 · "
      + "되돌리기, 검증 실패 시 게시 거부, 세대 범위 병합이 시험을 통과함. 같은 세대 재저장 시 청크 2배, 병합 범위를 안 좁히면 "
      + "두 세대 엔티티가 한 노드로 합쳐지는 현상도 재현함. 주의 1 · 2 · 3은 시험 중 드러나 설계를 고친 부분임. "
      + "한계: BM25 세대는 하나뿐이라 BM25 쪽 전환은 포인터 값 대조까지만 확인함.",
  });
  L.card(s, "검증 완료 · 시험 24건 통과", { x: X0 + CW - 3.0, y: 1.28, w: 3.0, h: 0.38, fill: C.blue, line: null,
    color: C.white, size: 15, bold: true, r: 0.19 });

  // 왼쪽: 포인터 → 세대 2개
  const lw = 8.6, rx = X0 + lw + 0.3, rw = CW - lw - 0.3;
  sectionLabel(s, "포인터 active_generation.json", { x: X0, y: 1.9, w: lw });
  L.rr(s, { x: X0, y: 2.36, w: lw, h: 1.32, fill: C.altRow, line: C.border, r: 0.06 });
  s.addText([
    { text: "{ \"generation\": \"gen-B\",", options: { color: C.ink, breakLine: true } },
    { text: "  \"neo4j\": { \"vector_index\": \"chunk_vec\", \"generation\": \"gen-B\" },",
      options: { color: C.blue, bold: true, breakLine: true } },
    { text: "  \"search_index_root\": \"generations/gen-B/search_indexes\",", options: { color: C.ink, breakLine: true } },
    { text: "  \"embedding_dimension\": 768 }", options: { color: C.ink } },
  ], { x: X0 + 0.15, y: 2.4, w: lw - 0.3, h: 1.0, fontFace: FONT, fontSize: fs(14), valign: "top", margin: 0.02,
    isTextBox: true, paraSpaceAfter: 0 });
  L.text(s, "바뀌는 점: chroma_path(폴더) 대신 neo4j.generation(값) — Neo4j는 세대를 노드 속성으로 구분",
    { x: X0 + 0.15, y: 3.36, w: lw - 0.3, h: 0.3, size: 14, color: C.blue, bold: true, margin: 0 });

  const gw = (lw - 0.3) / 2, gy = 4.0, gh = 2.25;
  const gens = [
    { x: X0, name: "gen-A · 이전(보관)", active: false, g: "gen-A" },
    { x: X0 + gw + 0.3, name: "gen-B · 활성", active: true, g: "gen-B" },
  ];
  gens.forEach((g) => {
    L.rr(s, { x: g.x, y: gy, w: gw, h: gh, fill: g.active ? C.tint : C.white, line: g.active ? C.blue : C.sub,
      lw: 1.5, r: 0.08, dash: g.active ? undefined : "dash" });
    L.text(s, g.name, { x: g.x + 0.15, y: gy + 0.08, w: gw - 0.3, h: 0.36, size: 16, bold: true,
      color: g.active ? C.navy : C.sub, margin: 0 });
    const bw = (gw - 0.4) / 2, by = gy + 0.55, bh = gh - 0.7;
    [["Neo4j", `generation = ${g.g}\n청크 · 엔티티\n노드`], ["BM25", `generations/\n${g.g}/\nsearch_indexes`]].forEach(
      ([tag, body], k) => {
        const bx = g.x + 0.15 + k * (bw + 0.1);
        L.rr(s, { x: bx, y: by, w: bw, h: bh, fill: C.white, line: g.active ? C.navy : C.border, r: 0.06 });
        L.card(s, tag, { x: bx + 0.1, y: by + 0.1, w: bw - 0.2, h: 0.34, fill: g.active ? (k ? C.blue : C.navy) : C.sub,
          line: null, color: C.white, size: 14, bold: true, r: 0.05 });
        L.text(s, body, { x: bx + 0.05, y: by + 0.5, w: bw - 0.1, h: bh - 0.56, size: 14,
          color: g.active ? C.ink : C.sub, align: "center", valign: "middle", margin: 0 });
      });
  });
  // 포인터 → 활성 세대(실선), 이전 세대(점선: 되돌릴 때)
  L.arrow(s, { x1: X0 + gw + 0.3 + gw / 2, y1: 3.7, x2: X0 + gw + 0.3 + gw / 2, y2: gy - 0.02, color: C.blue, width: 2 });
  L.text(s, "검색기가 한 번 읽음", { x: X0 + gw + 0.3 + gw / 2 + 0.1, y: 3.7, w: 2.2, h: 0.3, size: 14, bold: true,
    color: C.blue, margin: 0 });
  L.arrow(s, { x1: X0 + gw / 2, y1: 3.7, x2: X0 + gw / 2, y2: gy - 0.02, color: C.sub, width: 1.5, dash: "dash" });
  L.text(s, "되돌릴 때", { x: X0 + gw / 2 + 0.1, y: 3.7, w: 1.4, h: 0.3, size: 14, color: C.sub, margin: 0 });

  // 오른쪽: 게시 순서
  sectionLabel(s, "게시 순서", { x: rx, y: 1.9, w: rw });
  const steps = [
    "새 세대 ID를 정함(gen-B)",
    "Neo4j 저장 — 청크는 metadata(member_scope 포함),\n엔티티는 저장 뒤 Cypher로 generation 표시",
    "같은 세대 안에서만 병합(병합기 filter_query)",
    "BM25 색인 생성(generations/gen-B)",
    "검증 — 청크 수 · chunk_id 집합 일치,\n768차원, 벡터 인덱스 ONLINE",
    "포인터 교체(active_generation.json 원자적 교체)",
  ];
  steps.forEach((t, i) => {
    const y = 2.4 + i * 0.58;
    L.numBadge(s, i + 1, { x: rx, y: y + 0.08, size: 0.38, fsz: 16, fill: i === steps.length - 1 ? C.blue : C.navy });
    L.text(s, t, { x: rx + 0.5, y, w: rw - 0.5, h: 0.54, size: 14, color: C.ink, margin: 0,
      bold: i === steps.length - 1 });
    if (i < steps.length - 1) L.hline(s, { x: rx + 0.5, y: y + 0.565, w: rw - 0.5, color: C.line });
  });
  L.rr(s, { x: rx, y: 5.9, w: rw, h: 0.35, fill: C.altRow, line: C.border, r: 0.06 });
  L.text(s, "되돌리기: 포인터만 gen-A로 → Neo4j 값 · BM25 경로가 함께", { x: rx + 0.12, y: 5.9, w: rw - 0.24, h: 0.35,
    size: 14, bold: true, color: C.navy, margin: 0 });

  // 아래: 주의 카드 4개
  const tips = [
    { title: "라이브러리 불일치", body: "기본 VectorRetriever가 거를 속성을\n못 읽어 필터가 늘 전수 비교\n→ 하위 클래스로 보완" },
    { title: "회원 필터는 $eq 2번", body: "$or · $ne는 전수 비교 · 서버 거부\n앱에서 거르면 3/20 문항 누락\n→ member_scope로 2번 검색" },
    { title: "압축(BINARY) 보정", body: "기본 압축 + 후보 배수 1은\n순서 일치 40/60\n→ 후보 배수 4로 60/60" },
    { title: "CREATE · 병합 범위", body: "같은 세대 재저장 시 청크 중복\n→ 실패 세대는 지우고 처음부터\n병합기는 filter_query로 새 세대만" },
  ];
  const tg = 0.15, tw = (CW - tg * 3) / 4, ty = 6.45, th = 1.5;
  tips.forEach((t, i) => {
    const x = X0 + i * (tw + tg);
    L.rr(s, { x, y: ty, w: tw, h: th, fill: C.white, line: C.border, r: 0.08 });
    L.numBadge(s, "!", { x: x + 0.12, y: ty + 0.12, size: 0.36, fsz: 16, fill: C.dark });
    L.text(s, t.title, { x: x + 0.56, y: ty + 0.1, w: tw - 0.64, h: 0.4, size: 16, bold: true, color: C.navy, margin: 0 });
    L.text(s, t.body, { x: x + 0.15, y: ty + 0.6, w: tw - 0.25, h: th - 0.68, size: 14, color: C.ink, valign: "top",
      margin: 0 });
  });
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  await createSlide02();
  const out = process.argv[2] || path.join(__dirname, "Neo4j벡터검색.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
