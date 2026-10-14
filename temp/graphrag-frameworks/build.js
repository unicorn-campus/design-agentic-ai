// node build.js — GraphRAG 대표 프레임워크 3종 한 장 빌드 (script.md 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const GAP = 0.25;
const COL_W = (CW - GAP * 2) / 3;
const TOP = 1.9;
const LABEL_W = 0.9;                 // 행 왼쪽 필 라벨 폭

const STEPS = ["청킹", "추출", "KG 저장", "요약", "임베딩"];

// 순서는 사용자 지정(Neo4j → MS GraphRAG → LightRAG). 내용 근거 · 원문 대비 수정은 script.md 참조
const FW = [
  {
    name: "Neo4j", sub: "Neo4j GraphRAG · LangChain + Neo4j", color: C.navy,
    who: "그래프 DB에 담고 Cypher로 직접 묻기",
    summary: false,
    store: { merged: true, boxes: ["그래프", "벡터 인덱스"], outer: "Neo4j", note: "한 DB에 통합" },
    rows: [
      ["Local", "벡터로 진입점 → Cypher로 주변 탐색"],
      ["Global", "Cypher 조건 · 집계 + LLM 요약\n(선택) GDS 커뮤니티 + LLM 요약"],
      ["Hybrid", "'Hybrid' = 벡터 + 키워드 검색\nLocal + Global 결합은 직접 구성"],
      ["문서 갱신", "MERGE로 중복 없이 추가,\nCypher로 지우고 재삽입"],
    ],
    pick: "정형 데이터와 함께 쓰고\n조건 · 집계 질문이 많을 때",
  },
  {
    name: "MS GraphRAG", mark: "1)", sub: "Microsoft Research", color: C.blue,
    who: "미리 요약해 두어 전체 질문에 강함",
    summary: true,
    store: { merged: false, boxes: ["Parquet 파일\n(그래프)", "LanceDB\n(벡터)"], note: "그래프 DB 불필요" },
    rows: [
      ["Local", "엔티티 벡터 → 1홉 관계 · 원문 · 리포트"],
      ["Global", "커뮤니티 리포트 map-reduce"],
      ["Hybrid", "DRIFT: 요약 → 후속 질문 → Local"],
      ["문서 갱신", "update는 새 문서만 이어 붙임\n수정 · 삭제는 전체 재인덱싱이 안전"],
    ],
    pick: "전체 주제 요약 품질이 최우선일 때\n(인덱싱 비용 감수)",
  },
  {
    name: "LightRAG", sub: "HKUDS · 경량 GraphRAG", color: C.dark,
    who: "요약 없이 가볍게, 듀얼레벨 키워드로 찾기",
    summary: false,
    store: { merged: false, boxes: ["그래프\n(파일 · Neo4j 등)", "벡터\n(내장 · Milvus 등)"], note: "기본은 파일(테스트용)" },
    rows: [
      ["Local", "Low-level 키워드 → 엔티티 벡터"],
      ["Global", "High-level 키워드 → 관계 벡터"],
      ["Hybrid", "hybrid: Low + High 둘 다\n기본 mix는 원문 벡터까지 추가"],
      ["문서 갱신", "새 문서는 바로 병합,\n수정은 문서 삭제 후 재삽입"],
    ],
    pick: "비용 · 속도가 중요하고\n문서가 자주 늘 때",
  },
];

// 행 라벨 필 — 행 세로 가운데에 놓음
function rowLabel(s, t, { x, y, h }) {
  L.pill(s, t, { x, y: y + h / 2 - 0.17, w: LABEL_W - 0.08, h: 0.34, size: 14 });
}

// 인덱싱 단계 칩: 요약 칩만 프레임워크별로 채움(있음) / 회색 점선(없음)
function pipeline(s, fw, { x, y, w }) {
  const g = 0.05, cw = (w - g * (STEPS.length - 1)) / STEPS.length, h = 0.34;
  STEPS.forEach((t, i) => {
    const cx = x + i * (cw + g);
    if (t === "요약") {
      if (fw.summary) {
        L.card(s, t, { x: cx, y, w: cw, h, fill: fw.color, line: null, color: C.white, size: 14, bold: true, r: 0.05 });
      } else {
        L.card(s, t, { x: cx, y, w: cw, h, fill: C.white, line: C.pill, dash: "dash", color: C.pill, size: 14, r: 0.05 });
      }
      return;
    }
    L.card(s, t, { x: cx, y, w: cw, h, fill: C.tint, line: null, color: C.navy, size: 14, r: 0.05 });
  });
}

// 저장소 도식: 통합이면 바깥 상자 안에 두 상자, 분리면 두 상자를 나란히 + 아래 설명
function storage(s, fw, { x, y, w, h }) {
  const st = fw.store, noteH = 0.28, bh = h - noteH - 0.04;
  if (st.merged) {
    L.rr(s, { x, y, w, h: bh, fill: C.altRow, line: fw.color, lw: 1.5, r: 0.06 });
    L.text(s, st.outer, { x: x + 0.08, y, w: 0.9, h: bh, size: 15, bold: true, color: fw.color });
    const iw = (w - 1.0 - 0.15) / 2;
    st.boxes.forEach((t, i) => L.card(s, t, { x: x + 1.0 + i * (iw + 0.07), y: y + 0.08, w: iw, h: bh - 0.16,
      fill: C.white, line: C.border, color: C.ink, size: 14, bold: true, r: 0.05 }));
  } else {
    const iw = (w - 0.1) / 2;
    st.boxes.forEach((t, i) => L.card(s, t, { x: x + i * (iw + 0.1), y, w: iw, h: bh, fill: C.altRow, line: fw.color,
      lw: 1.25, color: C.ink, size: 14, bold: true, r: 0.06 }));
  }
  L.text(s, st.note, { x, y: y + bh + 0.02, w, h: noteH, size: 14, color: C.sub, align: "center" });
}

function fwCard(s, fw, x) {
  const H = 7.88 - TOP, ix = x + 0.15, iw = COL_W - 0.3;
  L.rr(s, { x, y: TOP, w: COL_W, h: H, fill: C.white, line: C.border, r: 0.08 });
  // 머리 바: 이름 + 부제
  L.rr(s, { x, y: TOP, w: COL_W, h: 0.55, fill: fw.color, line: null, r: 0.06 });
  s.addText([
    { text: fw.name, options: { fontSize: fs(20), bold: true, color: C.white } },
    // 각주 번호는 위첨자로 붙임(사용자가 PowerPoint에서 정한 표기)
    ...(fw.mark ? [{ text: fw.mark, options: { fontSize: fs(20), bold: true, color: C.white, superscript: true } }] : []),
    { text: `  ${fw.sub}`, options: { fontSize: fs(14), color: "D9E3F5" } },
  ], { x: x + 0.15, y: TOP, w: COL_W - 0.3, h: 0.55, fontFace: FONT, valign: "middle", margin: 0, isTextBox: true });
  // 한 줄 정체성
  L.card(s, fw.who, { x: ix, y: TOP + 0.65, w: iw, h: 0.48, fill: C.tint, line: null, color: fw.color === C.blue ? C.blue : C.navy,
    size: 16, bold: true, r: 0.06 });
  // 인덱싱
  let y = TOP + 1.25;
  rowLabel(s, "인덱싱", { x: ix, y, h: 0.34 });
  pipeline(s, fw, { x: ix + LABEL_W, y, w: iw - LABEL_W });
  // 저장소
  y += 0.46;
  rowLabel(s, "저장소", { x: ix, y, h: 0.66 });
  storage(s, fw, { x: ix + LABEL_W, y, w: iw - LABEL_W, h: 0.98 });
  // 검색 · 갱신 행
  y += 1.08;
  const rh = 0.6;
  fw.rows.forEach(([label, t], i) => {
    const ry = y + i * rh;
    L.hline(s, { x: ix, y: ry, w: iw, color: C.line });
    rowLabel(s, label, { x: ix, y: ry, h: rh });
    L.text(s, t, { x: ix + LABEL_W, y: ry, w: iw - LABEL_W, h: rh, size: 14, color: C.ink });
  });
  // 이럴 때 고름
  y += fw.rows.length * rh + 0.08;
  L.card(s, fw.pick, { x: ix, y, w: iw, h: TOP + H - 0.12 - y, fill: fw.color, line: null, color: C.white, size: 15,
    bold: true, r: 0.06 });
}

async function main() {
  L.createDeck();
  const s = L.newSlide({
    title: "GraphRAG 대표 프레임워크: Neo4j · MS GraphRAG · LightRAG",
    lead: "그래프를 어디에 담고, 전체를 묻는 질문을 어떻게 푸는지가 세 프레임워크의 가장 큰 차이",
    notes: "세 프레임워크 모두 엔티티 · 관계를 LLM으로 뽑아 그래프를 만들고, 벡터로 진입점을 찾는 점은 같음. "
      + "차이 ① 저장: Neo4j는 DB 하나에 다 담고, MS는 파일 + 벡터 DB, LightRAG는 기본 파일(운영은 외부 DB). "
      + "차이 ② 전체 질문: Neo4j는 Cypher로 조건 · 집계, MS는 미리 만든 커뮤니티 요약, LightRAG는 상위 키워드로 관계 검색. "
      + "차이 ③ 갱신: MS는 커뮤니티를 다시 계산해야 해 전체 재인덱싱이 안전하고, LightRAG는 문서 단위 추가 · 삭제가 쉬움.",
  });
  FW.forEach((fw, i) => fwCard(s, fw, X0 + i * (COL_W + GAP)));
  L.text(s, "※ 1) MS GraphRAG는 현재 유지보수 모드: 새 기능 추가 없이 버그 · 보안 수정만 이어 가는 상태 (2026-08 공지)",
    { x: X0, y: 7.94, w: CW, h: 0.34, size: 14, color: C.sub });
  const out = process.argv[2] || path.join(__dirname, "GraphRAG프레임워크.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
