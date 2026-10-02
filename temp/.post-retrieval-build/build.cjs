// Post-Retrieval(리랭킹 중점) 3장 덱 빌드 — 원본 스크립트: temp/post_retrieval_reranking_script.md
const fs = require("node:fs");
const path = require("node:path");
const pptxgen = require("C:/Users/hiond/.npm-global/node_modules/pptxgenjs");
const { FONT, C, fsMin, make } = require("./helpers.cjs");

const OUT = path.join(__dirname, "..", "post_retrieval_reranking.pptx");
const SCRIPT = path.join(__dirname, "..", "post_retrieval_reranking_script.md");

// 스크립트의 '### 강사 노트'를 슬라이드 노트로 그대로 옮김 — 노트 문구를 두 곳에서 따로 관리하지 않기 위함
function notesOf(n) {
  const md = fs.readFileSync(SCRIPT, "utf8");
  const sec = md.split(/^## 슬라이드 /m)[n];
  const m = sec.match(/### 강사 노트\s*\n([\s\S]*?)(\n---|\n## |$)/);
  return m ? m[1].replace(/ {2}\n/g, "\n").trim() : "";
}

// 여러 줄 텍스트(줄마다 크기·굵기 다름)를 한 도형 안에 넣기 위한 런 배열
const rt = (lines) =>
  lines.map(([t, size, o = {}], i) => ({
    text: t,
    options: { fontSize: fsMin(size), fontFace: FONT, breakLine: i < lines.length - 1, ...o },
  }));

let H;

// ───────────────────────── 슬라이드 1 ─────────────────────────
async function createSlide01(pptx) {
  const s = pptx.addSlide({ masterName: "MASTER" });
  H.pageHeader(s, {
    crumb: "RAG 검색 › Post-Retrieval",
    title: "검색 뒤 한 번 더 고르기",
    lead: "1차 검색 후보를 다시 평가해 LLM에 넘길 근거를 추림",
    no: 1,
    sources: "aistudy 교재 10.RAG.md §4.3 Post-Retrieval — github.com/cna-bootcamp/aistudy/blob/main/agentic-ai/textbook/10.RAG.md",
  });

  // ① 파이프라인 띠
  const y = 2.25, h = 1.05, cy = y + h / 2;
  H.card(s, 0.55, y, 1.9, h, "질문", { fill: C.navy, line: null, color: C.white, size: 20, bold: true });
  H.arrow(s, 2.55, cy, 3.3, cy, { color: C.sub });
  // 겹친 사각형 5장 = 후보 여러 건
  for (let i = 4; i >= 0; i--) {
    H.box(s, 3.45 + i * 0.12, y + 0.1 - i * 0.05 + 0.1, 2.0, h - 0.2, { fill: i === 0 ? C.white : C.alt, line: C.border, round: false });
  }
  s.addText(rt([["1차 검색", 18, { bold: true, color: C.navy }], ["후보 다수", 14, { color: C.slate }]]), {
    x: 3.45, y: y + 0.2, w: 2.0, h: h - 0.2, align: "center", valign: "middle", margin: 0,
  });
  H.arrow(s, 6.1, cy, 7.2, cy, { color: C.blue, width: 3 });
  H.card(s, 7.35, y, 4.6, h, rt([["Post-Retrieval", 22, { bold: true, color: C.navy }], ["오늘 다룰 구간", 14, { color: C.blue }]]),
    { fill: C.tint, line: C.blue, lw: 2, dash: "dash" });
  H.arrow(s, 12.05, cy, 13.15, cy, { color: C.blue });
  H.text(s, "추린 근거", 12.0, y - 0.32, 1.2, 0.3, { size: 14, color: C.blue, align: "center" });
  H.text(s, "후보 다수", 6.0, y - 0.32, 1.3, 0.3, { size: 14, color: C.blue, align: "center" });
  H.card(s, 13.25, y, 2.2, h, "LLM", { fill: C.navy, line: null, color: C.white, size: 20, bold: true });

  // ② 확대 표시: Post-Retrieval 상자 → 아래 4기법 컨테이너
  const top = 3.95;
  H.arrow(s, 7.35, y + h, 0.55, top, { color: C.blue, width: 1, dash: "dash", head: false });
  H.arrow(s, 11.95, y + h, 15.45, top, { color: C.blue, width: 1, dash: "dash", head: false });
  H.box(s, 0.55, top, 14.9, 4.3, { fill: C.white, line: C.blue, lw: 1.5, dash: "dash", r: 0.04 });

  const bw = 3.4, gap = 0.27, by = 4.3, bh = 3.65;
  const xs = [0, 1, 2, 3].map((i) => 0.85 + i * (bw + gap));
  const blocks = [
    { name: "재정렬 Re-ranking", goal: "관련 높은 문서를 위로", hi: true, note: "1차 검색 후보의\n순서를 다시 매김" },
    { name: "압축 Compression", goal: "토큰 절감 · 노이즈 제거", note: "질문 관련 문장만 추출\n또는 LLM으로 요약" },
    { name: "걸러내기 Filtering", goal: "관련 없는 문서 제거", note: "유사도 임계값 · 메타데이터\n· 중복 · 길이" },
    { name: "합치기 Fusion", goal: "여러 검색 결과 병합", note: "RRF = Σ 1 / (k + 순위)\nk는 보통 60" },
  ];
  blocks.forEach((b, i) => {
    const x = xs[i];
    H.box(s, x, by, bw, bh, { fill: b.hi ? C.tint : C.alt, line: b.hi ? C.blue : C.border, lw: b.hi ? 3 : 1 });
    H.text(s, b.name, x, by + 1.85, bw, 0.42, { size: 20, bold: true, color: C.navy, align: "center" });
    H.text(s, b.goal, x, by + 2.32, bw, 0.36, { size: 16, color: C.ink, align: "center" });
    if (b.note) H.text(s, b.note, x + 0.1, by + 2.82, bw - 0.2, 0.62, { size: 14, color: C.sub, align: "center" });
  });
  H.pill(s, xs[0] + 0.2, by - 0.2, 1.6, 0.4, "이번 장 중점", { fill: C.blue, line: C.blue, color: C.white });

  // 아이콘 영역 공통 y
  const iy = by + 0.3;
  // (1) 재정렬: 순서 섞인 3건 → 정렬된 3건 (진할수록 관련 높음)
  {
    const x = xs[0];
    const tone = { A: [C.blue, C.white], B: [C.white, C.blue], C: [C.white, C.sub] };
    const col = (cx, order) => order.forEach((k, j) =>
      H.card(s, cx, iy + j * 0.44, 1.0, 0.36, "문서 " + k, { fill: tone[k][0], line: k === "C" ? C.border : C.blue, color: tone[k][1], size: 14, bold: true, r: 0.05 }));
    col(x + 0.35, ["C", "A", "B"]);
    H.arrow(s, x + 1.45, iy + 0.62, x + 1.95, iy + 0.62, { color: C.blue, width: 2.5 });
    col(x + 2.05, ["A", "B", "C"]);
  }
  // (2) 압축: 긴 문서 → 필요한 줄만 남은 짧은 문서
  {
    const x = xs[1];
    H.box(s, x + 0.4, iy, 1.2, 1.3, { fill: C.white, line: C.navy, round: false });
    for (let j = 0; j < 5; j++) H.box(s, x + 0.55, iy + 0.18 + j * 0.22, j === 2 ? 0.9 : 0.75, 0.07, { fill: j === 2 ? C.blue : C.border, line: null, round: false });
    H.arrow(s, x + 1.7, iy + 0.65, x + 2.15, iy + 0.65, { color: C.navy, width: 2.5 });
    H.box(s, x + 2.25, iy + 0.35, 0.8, 0.6, { fill: C.white, line: C.navy, round: false });
    H.box(s, x + 2.35, iy + 0.62, 0.6, 0.07, { fill: C.blue, line: null, round: false });
  }
  // (3) 걸러내기: 3건 중 1건에 금지 표시
  {
    const x = xs[2];
    [0, 1, 2].forEach((j) => H.box(s, x + 0.45 + j * 0.9, iy + 0.25, 0.65, 0.85, { fill: C.white, line: j === 2 ? C.sub : C.blue, round: false, lw: 1.25 }));
    const ox = x + 2.18, oy = iy + 0.08;
    s.addShape(pptx.shapes.OVAL, { x: ox, y: oy, w: 1.2, h: 1.2, fill: { type: "none" }, line: { color: C.dark, width: 3 } });
    H.arrow(s, ox + 0.18, oy + 0.18, ox + 1.02, oy + 1.02, { color: C.dark, width: 3, head: false });
  }
  // (4) 합치기: 두 검색 결과가 한 목록으로
  {
    const x = xs[3];
    H.card(s, x + 0.25, iy + 0.05, 1.05, 0.42, "검색 A", { fill: C.white, line: C.navy, color: C.navy, size: 14, bold: true });
    H.card(s, x + 0.25, iy + 0.85, 1.05, 0.42, "검색 B", { fill: C.white, line: C.navy, color: C.navy, size: 14, bold: true });
    const mx = x + 1.85, my = iy + 0.66;
    H.arrow(s, x + 1.3, iy + 0.26, mx, my, { color: C.navy, width: 2, head: false });
    H.arrow(s, x + 1.3, iy + 1.06, mx, my, { color: C.navy, width: 2, head: false });
    H.arrow(s, mx, my, x + 2.15, my, { color: C.navy, width: 2.5 });
    H.card(s, x + 2.2, iy + 0.38, 1.0, 0.56, "통합 목록", { fill: C.navy, line: null, color: C.white, size: 14, bold: true });
  }
  s.addNotes(notesOf(1));
  return s;
}

// ───────────────────────── 슬라이드 2 ─────────────────────────
async function createSlide02(pptx) {
  const s = pptx.addSlide({ masterName: "MASTER" });
  H.pageHeader(s, {
    crumb: "RAG 검색 › Post-Retrieval › Re-ranking",
    title: "넓게 뽑고 정밀하게 다시 줄 세우기",
    lead: "빠른 모델로 후보를 모으고, 정확한 모델로 최종 순서를 정함",
    no: 2,
    sources: "aistudy 교재 10.RAG.md §4.3 · huggingface.co/BAAI/bge-reranker-v2-m3 · sbert.net Retrieve & Re-Rank",
  });

  const py = 2.2, ph = 3.1, pw = 7.2;
  // ① Bi-Encoder: 질문·문서를 따로 인코딩
  {
    const x = 0.55;
    H.headerBar(s, x, py, pw, "Bi-Encoder · 1차 검색");
    H.box(s, x, py + 0.55, pw, ph - 0.55, { fill: C.white, line: C.border });
    const r1 = py + 0.8, r2 = py + 1.85, bh = 0.6;
    [[r1, "질문"], [r2, "문서"]].forEach(([ry, label]) => {
      H.card(s, x + 0.3, ry, 1.3, bh, label, { fill: C.alt, line: C.border, size: 16, bold: true, color: C.navy });
      H.arrow(s, x + 1.65, ry + bh / 2, x + 2.05, ry + bh / 2, { color: C.sub });
      H.card(s, x + 2.1, ry, 1.3, bh, "인코더", { fill: C.dark, line: null, color: C.white, size: 16, bold: true, round: false });
      H.arrow(s, x + 3.45, ry + bh / 2, x + 3.85, ry + bh / 2, { color: C.sub });
      H.card(s, x + 3.9, ry, 1.5, bh, "벡터", { fill: C.blue, line: null, color: C.white, size: 16, bold: true });
    });
    // 두 벡터 사이 양방향 비교
    s.addShape(pptx.shapes.LINE, { x: x + 4.65, y: r1 + bh + 0.04, w: 0, h: r2 - r1 - bh - 0.08,
      line: { color: C.blue, width: 2.5, beginArrowType: "triangle", endArrowType: "triangle" } });
    H.text(s, "유사도 비교", x + 4.8, r1 + bh + 0.05, 1.4, 0.35, { size: 14, color: C.blue, bold: true });
    H.pill(s, x + 5.6, r2 + 0.1, 1.45, 0.4, "미리 계산", { size: 14 });
    H.text(s, "따로 계산 · 문서 벡터는 미리 저장  →  빠름, 대신 거침", x + 0.3, py + ph - 0.48, pw - 0.6, 0.36, { size: 15, color: C.slate });
  }
  // ② Cross-Encoder: 질문+문서를 한 번에 읽어 점수 1개
  {
    const x = 8.25;
    H.headerBar(s, x, py, pw, "Cross-Encoder · Re-ranking", true);
    H.box(s, x, py + 0.55, pw, ph - 0.55, { fill: C.white, line: C.border });
    const gy = py + 0.7;
    H.box(s, x + 0.3, gy, 1.9, 1.85, { fill: C.tint, line: C.blue, lw: 2 });
    H.text(s, "한 상자에 함께", x + 0.3, gy + 0.05, 1.9, 0.32, { size: 14, color: C.blue, bold: true, align: "center" });
    H.card(s, x + 0.5, gy + 0.45, 1.5, 0.55, "질문", { fill: C.white, line: C.border, size: 16, bold: true, color: C.navy });
    H.card(s, x + 0.5, gy + 1.1, 1.5, 0.55, "문서", { fill: C.white, line: C.border, size: 16, bold: true, color: C.navy });
    H.arrow(s, x + 2.25, gy + 0.92, x + 2.75, gy + 0.92, { color: C.blue, width: 2.5 });
    H.card(s, x + 2.8, gy + 0.3, 1.4, 1.25, "인코더", { fill: C.dark, line: null, color: C.white, size: 16, bold: true, round: false });
    H.arrow(s, x + 4.25, gy + 0.92, x + 4.75, gy + 0.92, { color: C.blue, width: 2.5 });
    s.addText("0.98", { shape: pptx.shapes.OVAL, x: x + 4.85, y: gy + 0.2, w: 1.45, h: 1.45, fill: { color: C.blue }, line: { type: "none" },
      fontFace: FONT, fontSize: fsMin(28), bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
    H.text(s, "관련성 점수(0 ~ 1) 예시", x + 4.3, gy + 1.68, 2.6, 0.32, { size: 14, color: C.blue, align: "center" });
    H.text(s, "쌍마다 새로 계산 · 낱말 간 상호작용 분석  →  느림, 대신 정확", x + 0.3, py + ph - 0.48, pw - 0.6, 0.36, { size: 15, color: C.slate });
  }
  // ③ 비유(이 장의 유일한 비유)
  H.pill(s, 4.5, py + ph + 0.12, 7.0, 0.42, "비유: 사진으로 집 고르기  ↔  직접 방문해 확인하기", { size: 16 });

  // ④ Retrieve More, Rerank Better 깔때기
  const fc = 6.75;
  H.card(s, 0.55, fc - 0.35, 1.2, 0.7, "질문", { fill: C.navy, line: null, color: C.white, size: 18, bold: true });
  H.arrow(s, 1.82, fc, 2.38, fc, { color: C.sub });
  H.card(s, 2.45, fc - 0.72, 2.75, 1.44, rt([["1차 검색", 18, { bold: true, color: C.navy }], ["Top 50 ~ 100", 16, { color: C.slate }]]), { fill: C.alt, line: C.border, round: false });
  H.arrow(s, 5.27, fc, 5.8, fc, { color: C.blue, width: 3 });
  H.card(s, 5.87, fc - 0.52, 2.4, 1.04, rt([["Re-ranking", 18, { bold: true }], ["Cross-Encoder", 15]]), { fill: C.blue, line: null, color: C.white, round: false });
  H.arrow(s, 8.34, fc, 8.87, fc, { color: C.blue, width: 3 });
  H.card(s, 8.94, fc - 0.38, 1.66, 0.76, rt([["Top 3 ~ 5", 17, { bold: true }], ["→ LLM", 15]]), { fill: C.navy, line: null, color: C.white, round: false });
  H.text(s, "INITIAL_K · 넓게", 2.45, fc + 0.75, 2.75, 0.32, { size: 14, color: C.sub, align: "center" });
  H.text(s, "RERANK_K · 좁게", 8.6, fc + 0.42, 2.3, 0.32, { size: 14, color: C.sub, align: "center" });
  // 인용 콜아웃
  s.addShape(pptx.shapes.RECTANGLE, { x: 0.55, y: 7.88, w: 0.07, h: 0.42, fill: { color: C.blue }, line: { type: "none" } });
  H.text(s, "INITIAL_K를 올려도 LLM에는 RERANK_K개만 전달  →  토큰 비용 그대로", 0.75, 7.88, 9.9, 0.42, { size: 16, color: C.navy, bold: true, italic: true });

  // ⑤ 모델 선택 미니 카드(교재 기준)
  const mx = 11.05, mw = 4.4;
  H.text(s, "모델 선택 예 (교재 기준)", mx, 5.95, mw, 0.36, { size: 16, color: C.navy, bold: true });
  [["다국어", "BAAI/bge-reranker-v2-m3"], ["한국어", "dragonkue/bge-reranker-v2-m3-ko"], ["API", "Cohere rerank · Jina reranker"]].forEach(([b, t], i) => {
    const yy = 6.38 + i * 0.66;
    H.box(s, mx, yy, mw, 0.56, { fill: C.alt, line: C.border });
    H.card(s, mx + 0.1, yy + 0.09, 0.9, 0.38, b, { fill: C.dark, line: null, color: C.white, size: 14, bold: true, r: 0.05 });
    H.text(s, t, mx + 1.1, yy, mw - 1.15, 0.56, { size: 14, color: C.ink });
  });
  s.addNotes(notesOf(2));
  return s;
}

// ───────────────────────── 슬라이드 3 ─────────────────────────
async function createSlide03(pptx) {
  const s = pptx.addSlide({ masterName: "MASTER" });
  H.pageHeader(s, {
    crumb: "RAG 검색 › Post-Retrieval › 프로젝트 적용",
    title: "우리 프로젝트의 리랭킹",
    lead: "hybrid-ai-lab vector-retriever · 기본 모드 hybrid_rerank의 후보 축소 단계와 실패 대비 경로 (최종 Top-K 5 기준)",
    no: 3,
    sources: "hybrid-ai-lab/retriever/vector-retriever — README.md · app/infrastructure/graph.py · reranker.py · settings.py · app/application/scoring.py",
  });

  // ① 후보 축소 깔때기 + 담당 부품
  const cy = 3.15;
  const bars = [
    { x: 0.55, w: 3.0, h: 1.5, n: "40건", l: "검색기별 원시 후보", fill: C.alt, line: C.border, color: C.navy, part: "Vector 검색 + BM25 검색" },
    { x: 3.95, w: 2.4, h: 1.15, n: "10건", l: "질문별 융합 후보", fill: C.tint, line: C.blue, color: C.navy, part: "가중 융합\nVector 0.6 + BM25 0.4" },
    { x: 6.75, w: 1.9, h: 0.88, n: "5건", l: "Rerank 결과", fill: C.blue, line: null, color: C.white, part: "CrossEncoder\nbge-reranker-v2-m3" },
  ];
  bars.forEach((b, i) => {
    H.card(s, b.x, cy - b.h / 2, b.w, b.h, rt([[b.n, i === 2 ? 26 : 30, { bold: true }], [b.l, 14]]), { fill: b.fill, line: b.line, color: b.color, round: false, lw: 1.5 });
    const pcx = b.x + b.w / 2, pw = Math.max(b.w, 2.3);
    s.addShape(pptx.shapes.LINE, { x: pcx, y: cy + b.h / 2, w: 0, h: 4.25 - (cy + b.h / 2), line: { color: C.border, width: 1.25 } });
    H.card(s, pcx - pw / 2, 4.25, pw, 0.72, b.part, { fill: C.white, line: C.border, size: 14, color: C.ink, bold: i === 2 });
    const nx = bars[i + 1] ? bars[i + 1].x : 9.05;
    H.arrow(s, b.x + b.w + 0.06, cy, nx - 0.06, cy, { color: C.blue, width: 2.5 });
  });
  H.card(s, 9.05, cy - 0.44, 1.9, 0.88, rt([["LLM", 20, { bold: true }], ["근거로 사용", 14]]), { fill: C.navy, line: null, color: C.white });

  // 비교 띠: rerank 유무에 따른 후보 수
  H.box(s, 0.55, 5.12, 10.4, 0.5, { fill: C.alt, line: C.border });
  H.pill(s, 0.7, 5.17, 1.8, 0.4, "hybrid_rerank", { fill: C.blue, line: C.blue, color: C.white });
  H.text(s, "40 → 10 → 5", 2.6, 5.12, 1.5, 0.5, { size: 15, bold: true, color: C.navy });
  H.pill(s, 4.15, 5.17, 1.15, 0.4, "hybrid", { fill: C.white, line: C.border });
  H.text(s, "20 → 5 → 5", 5.4, 5.12, 1.4, 0.5, { size: 15, bold: true, color: C.slate });
  H.text(s, "rerank 모드: 융합 = Top-K × 2, 원시 = 융합 × 4", 6.85, 5.12, 4.05, 0.5, { size: 14, color: C.sub });

  // ② 기본 설정값 카드(네이티브 표)
  const sx = 11.2, sw = 4.25;
  H.card(s, sx, 2.15, 1.7, 0.4, "기본 설정값", { fill: C.dark, line: null, color: C.white, size: 14, bold: true, r: 0.05 });
  const hd = (t) => ({ text: t, options: { fill: { color: C.tableHead }, color: C.navy, bold: true } });
  s.addTable(
    [
      [hd("설정"), hd("기본값")],
      ["RERANK_MODEL", "bge-reranker-v2-m3"],
      ["RERANK_MAX_LENGTH", "512 토큰"],
      ["TIMEOUT_RERANK", "60초"],
      ["TOP_K_DEFAULT", "5"],
      ["CANDIDATE_MULTIPLIER", "4"],
    ].map((row, ri) => (ri > 0 && ri % 2 === 0 ? row.map((c) => ({ text: c, options: { fill: { color: C.alt } } })) : row)),
    { x: sx, y: 2.62, w: sw, colW: [2.3, 1.95], rowH: 0.4, fontFace: FONT, fontSize: fsMin(14), color: C.ink,
      border: { type: "solid", color: C.line, pt: 1 }, valign: "middle", margin: 0.05 }
  );
  H.text(s, "최초 사용 시 모델 약 2.2GB 내려받기", sx, 5.12, sw, 0.5, { size: 14, color: C.sub });

  // ③ 리랭커 내부 동작
  const by = 5.85;
  H.headerBar(s, 0.55, by, 8.8, "리랭커 내부 동작 · 모델은 처음 쓸 때 적재", false, 0.45);
  H.box(s, 0.55, by + 0.5, 8.8, 1.95, { fill: C.white, line: C.border });
  const ry = by + 0.65;
  H.box(s, 0.75, ry, 2.05, 1.3, { fill: C.tint, line: C.blue, lw: 2 });
  H.text(s, "쌍으로 묶음", 0.75, ry + 0.03, 2.05, 0.3, { size: 14, color: C.blue, bold: true, align: "center" });
  H.card(s, 0.9, ry + 0.36, 1.75, 0.4, "질문", { fill: C.white, line: C.border, size: 14, bold: true, color: C.navy, r: 0.05 });
  H.card(s, 0.9, ry + 0.82, 1.75, 0.4, "청크 본문", { fill: C.white, line: C.border, size: 14, bold: true, color: C.navy, r: 0.05 });
  H.arrow(s, 2.87, ry + 0.65, 3.35, ry + 0.65, { color: C.blue, width: 2.5 });
  H.card(s, 3.42, ry + 0.15, 1.85, 1.0, rt([["CrossEncoder", 15, { bold: true }], ["predict", 14]]), { fill: C.dark, line: null, color: C.white, round: false });
  H.arrow(s, 5.34, ry + 0.65, 5.8, ry + 0.65, { color: C.blue, width: 2.5 });
  s.addText(rt([["Sigmoid", 14, { bold: true }], ["0 ~ 1", 14]]), { shape: pptx.shapes.OVAL, x: 5.87, y: ry + 0.1, w: 1.2, h: 1.1,
    fill: { color: C.blue }, line: { type: "none" }, color: C.white, align: "center", valign: "middle", margin: 0 });
  H.arrow(s, 7.13, ry + 0.65, 7.55, ry + 0.65, { color: C.blue, width: 2.5 });
  // 점수 순 정렬 막대 + 순위 배지
  [1.0, 0.72, 0.45].forEach((hh, i) => {
    const bx = 7.68 + i * 0.52;
    H.box(s, bx, ry + 1.0 - hh, 0.4, hh, { fill: C.blue, line: null, round: false });
    H.badge(s, bx + 0.02, ry + 1.06, i + 1, { color: C.navy, size: 0.36, fs: 14 });
  });
  H.text(s, "정렬: rerank_score 높은 순 → 같으면 원래 score → 그래도 같으면 chunk_id", 0.75, by + 2.0, 8.4, 0.38, { size: 14, color: C.slate });

  // ④ 실패 시 분기
  const fx = 9.65, fw = 5.8;
  H.headerBar(s, fx, by, fw, "리랭킹이 실패해도 검색은 실패가 아님", true, 0.45);
  H.box(s, fx, by + 0.5, fw, 1.95, { fill: C.white, line: C.border });
  const fcY = by + 1.47;
  H.card(s, fx + 0.2, fcY - 0.38, 1.35, 0.76, rt([["리랭킹", 15, { bold: true }], ["실패", 15, { bold: true }]]), { fill: C.dark, line: null, color: C.white });
  const jx = fx + 1.85;
  H.arrow(s, fx + 1.55, fcY, jx, fcY, { color: C.sub, width: 2, head: false });
  const upY = by + 0.95, dnY = by + 1.98;
  H.arrow(s, jx, fcY, fx + 3.1, upY, { color: C.sub, width: 2 });
  H.arrow(s, jx, fcY, fx + 3.1, dnY, { color: C.sub, width: 2 });
  H.text(s, "변환 질문 없음", fx + 1.55, by + 0.58, 1.6, 0.3, { size: 14, color: C.slate });
  H.text(s, "변환 질문 있음", fx + 1.75, by + 2.08, 1.6, 0.3, { size: 14, color: C.slate });
  H.card(s, fx + 3.15, upY - 0.32, 2.5, 0.64, "직전 결과 그대로 사용", { fill: C.alt, line: C.border, size: 14, bold: true, color: C.navy });
  H.card(s, fx + 3.15, dnY - 0.32, 2.5, 0.64, rt([["원 질문 · 변환 질문", 14, { bold: true }], ["RRF 병합", 14, { bold: true }]]), { fill: C.alt, line: C.border, color: C.navy });
  H.text(s, "warnings에\n기록", fx + 0.2, fcY + 0.42, 1.35, 0.5, { size: 14, color: C.sub, align: "center" });

  s.addNotes(notesOf(3));
  return s;
}

async function main() {
  const pptx = new pptxgen();
  pptx.defineLayout({ name: "CUSTOM", width: 16, height: 9 });
  pptx.layout = "CUSTOM";
  pptx.title = "Post-Retrieval Techniques — Re-ranking";
  pptx.defineSlideMaster({ title: "MASTER", background: { color: C.white } });
  H = make(pptx);
  for (const fn of [createSlide01, createSlide02, createSlide03]) await fn(pptx);
  await pptx.writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
