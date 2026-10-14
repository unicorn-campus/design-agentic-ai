// node build.js — 그래프DB 인덱싱 과정을 벡터DB 인덱싱과 비교한 한 장 빌드 (script.md 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

// 세로 칸 격자 — 그래프DB 줄의 단계 9칸을 기준으로 벡터DB 줄 상자를 같은 칸에 맞춰 대응 관계를 보여 줌
const LBL_W = 1.25;                       // 왼쪽 줄 이름 폭
const XS = X0 + LBL_W + 0.15;             // 첫 칸 시작 x
const GAP = 0.28;                         // 칸 사이(화살표 자리)
const UNIT = (X0 + CW - XS - GAP * 8) / 9;
const col = (i) => XS + i * (UNIT + GAP);
const span = (i0, i1) => ({ x: col(i0), w: col(i1) + UNIT - col(i0) });

// 구간 3개: 앞뒤는 벡터DB와 똑같고, 가운데만 그래프DB에 끼어드는 단계
const GROUPS = [
  { i0: 0, i1: 2, tag: "똑같음", fill: C.sub },
  { i0: 3, i1: 6, tag: "그래프DB에만 있음: 글 → 노드와 관계", fill: C.blue },
  { i0: 7, i1: 8, tag: "똑같음", fill: C.sub },
];

const Y = { tag: 1.9, vec: 2.42, vecH: 1.0, kg: 3.62, kgH: 1.4, who: 5.1, whoH: 0.38, out: 5.56, outH: 0.82,
  cmp: 6.5, cmpH: 1.45 };

// 누가 하나 표시 — LLM이 드는 단계를 색으로 바로 구분하게 함
const WHO = {
  "코드": { fill: C.white, line: C.pill, color: C.slate },
  "LLM": { fill: C.blue, line: null, color: C.white },
  "코드 + LLM": { fill: C.tint, line: C.blue, color: C.blue },
  "임베딩 모델": { fill: C.navy, line: null, color: C.white },
};

// 벡터DB 단계 상자: 흰 바탕 + 굵은 이름 / 하는 일
function vecStep(s, { x, w, title, sub }) {
  L.rr(s, { x, y: Y.vec, w, h: Y.vecH, fill: C.white, line: C.navy, lw: 1.25, r: 0.08 });
  s.addText([
    { text: title, options: { fontSize: fs(17), bold: true, color: C.navy, breakLine: true } },
    { text: sub, options: { fontSize: fs(14), color: C.slate } },
  ], { x, y: Y.vec, w, h: Y.vecH, fontFace: FONT, align: "center", valign: "middle", margin: 0.04, isTextBox: true,
    paraSpaceAfter: 2 });
}

// 그래프DB 단계 상자: 왼쪽 위 번호(또는 '보강'·'선택' 표시) + 가운데 이름
function kgStep(s, { x, w, n, mark, title, sub, dashed = false }) {
  L.rr(s, { x, y: Y.kg, w, h: Y.kgH, fill: dashed ? C.white : C.tint, line: C.blue, lw: 1.5, r: 0.08,
    dash: dashed ? "dash" : undefined });
  if (n) L.numBadge(s, n, { x: x + 0.1, y: Y.kg + 0.1, size: 0.38, fsz: 16 });
  if (mark) L.card(s, mark, { x: x + 0.1, y: Y.kg + 0.1, w: 0.64, h: 0.34, fill: C.white, line: C.blue,
    color: C.blue, size: 14, bold: true, r: 0.17 });
  const runs = [{ text: title, options: { fontSize: fs(17), bold: true, color: C.navy, breakLine: !!sub } }];
  if (sub) runs.push({ text: sub, options: { fontSize: fs(14), color: C.slate } });
  s.addText(runs, { x, y: Y.kg + 0.46, w, h: Y.kgH - 0.52, fontFace: FONT, align: "center", valign: "middle",
    margin: 0.03, isTextBox: true, paraSpaceAfter: 2 });
}

// 같은 줄 안에서 앞 상자 오른쪽 끝 → 다음 상자 왼쪽 끝 화살표
function flow(s, xr, xl, cy) {
  L.arrow(s, { x1: xr + 0.03, y1: cy, x2: xl - 0.03, y2: cy, color: C.slate, width: 1.75 });
}

// 비교 카드: 질문 + 벡터DB 줄 + 그래프DB 줄
function compareCard(s, { x, w, n, ask, vec, kg }) {
  const y = Y.cmp, h = Y.cmpH;
  L.rr(s, { x, y, w, h, fill: C.white, line: C.border, r: 0.08 });
  L.numBadge(s, n, { x: x + 0.15, y: y + 0.14, size: 0.38, fsz: 16 });
  L.text(s, ask, { x: x + 0.62, y: y + 0.12, w: w - 0.75, h: 0.42, size: 17, bold: true, color: C.navy });
  [["벡터DB", vec, false], ["그래프DB", kg, true]].forEach(([tag, t, strong], i) => {
    const ry = y + 0.6 + i * 0.44;
    L.card(s, tag, { x: x + 0.15, y: ry, w: 1.08, h: 0.36, size: 14, bold: true, r: 0.18,
      fill: strong ? C.blue : C.tint, line: strong ? null : C.pill, color: strong ? C.white : C.navy });
    L.text(s, t, { x: x + 1.33, y: ry - 0.02, w: w - 1.43, h: 0.42, size: 15, color: strong ? C.ink : C.body,
      bold: strong });
  });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "그래프DB 인덱싱 과정: 벡터DB와 비교",
    lead: "벡터DB 인덱싱 가운데에 'LLM이 글을 노드와 관계로 바꿔 그래프로 저장하는 단계'가 끼어든 것임",
    notes: "그래프DB 인덱싱은 벡터DB 인덱싱과 앞뒤가 똑같음. 앞의 로드·정제·청킹, 뒤의 임베딩·적재는 그대로임. "
      + "다른 점은 청킹과 임베딩 사이에 끼어드는 네 단계임. LLM이 청크마다 글을 읽고 사람·회사 같은 노드(엔티티)와 "
      + "'근무한다' 같은 관계를 한 번의 호출로 함께 뽑음. 같은 노드가 여러 청크에서 나오면 이름·종류가 같은 것을 "
      + "코드로 하나로 합치고, 청크마다 따로 붙은 설명은 LLM이 한 줄로 요약함. 지식 그래프 구축은 합친 노드·관계를 "
      + "그래프로 엮는 일이라 코드가 함. 사전요약은 Leiden 같은 알고리즘이 노드를 주제별로 묶고, 묶음마다 LLM이 "
      + "요약을 씀. '전체 경향' 질문을 위한 선택 단계임. 임베딩은 그래프DB에서도 LLM이 아니라 벡터DB와 같은 "
      + "임베딩 모델이 맡음. 즉 LLM은 추출과 요약(병합 설명·커뮤니티 요약)에만 씀. '삼성'과 '삼성전자'처럼 이름이 "
      + "다른 같은 대상을 합치는 일(엔티티 해소)은 기본 병합으로는 안 되며 따로 붙이는 작업임. 임베딩 대상은 청크와 노드 설명(사전요약을 했으면 커뮤니티 요약도)이고, 관계 연결 자체는 "
      + "임베딩하지 않고 그래프 그대로 둠. 마지막 적재에서 KG와 벡터를 함께 그래프DB에 저장함 "
      + "(Neo4j는 벡터를 노드 속성으로 두고 벡터 인덱스를 검). 검색할 때는 벡터로 비슷한 노드·청크를 먼저 찾고 "
      + "KG의 관계를 따라 넓혀 감. 정제 단계에서 이름·연락처 같은 개인정보를 가명으로 바꿔 두어야 "
      + "LLM 추출과 그래프 노드에 실명이 남지 않음.",
  });

  // ① 구간 바탕 + 머리표 — 같은 세로 칸이 서로 대응하는 단계임을 보여 줌
  GROUPS.forEach((g) => {
    const { x, w } = span(g.i0, g.i1);
    L.rr(s, { x: x - 0.07, y: Y.tag - 0.06, w: w + 0.14, h: Y.out + Y.outH - Y.tag + 0.12, fill: C.altRow,
      line: null, r: 0.1 });
    L.card(s, g.tag, { x, y: Y.tag, w, h: 0.4, fill: g.fill, line: null, color: C.white, size: 15, bold: true,
      r: 0.06 });
  });

  // ② 왼쪽 줄 이름
  L.card(s, "벡터DB\n인덱싱", { x: X0, y: Y.vec, w: LBL_W, h: Y.vecH, fill: C.navy, line: null, color: C.white,
    size: 16, bold: true, r: 0.08 });
  L.card(s, "그래프DB\n인덱싱", { x: X0, y: Y.kg, w: LBL_W, h: Y.kgH, fill: C.blue, line: null, color: C.white,
    size: 16, bold: true, r: 0.08 });
  L.card(s, "나오는 것", { x: X0, y: Y.out, w: LBL_W, h: Y.outH, fill: C.white, line: C.pill, color: C.navy,
    size: 15, bold: true, r: 0.08 });

  // ③ 벡터DB 줄 — 로드 → 정제 → 청킹 ──(그래프 단계 없이)──→ 임베딩 → 적재
  const vecCy = Y.vec + Y.vecH / 2;
  const vecBoxes = [
    { ...span(0, 0), title: "로드", sub: "원본 읽기" },
    { ...span(1, 1), title: "정제·\n가명처리", sub: "실명 → 가명" },
    { ...span(2, 2), title: "청킹", sub: "글 자르기" },
    { ...span(7, 7), title: "임베딩", sub: "청크 → 벡터" },
    { ...span(8, 8), title: "적재", sub: "벡터DB로" },
  ];
  vecBoxes.forEach((b, i) => {
    vecStep(s, b);
    if (i > 0) flow(s, vecBoxes[i - 1].x + vecBoxes[i - 1].w, b.x, vecCy);
  });
  // 빈 가운데 구간 위 긴 화살표에 이름표를 얹어 '벡터DB는 이 단계를 건너뜀'을 보여 줌
  const mid = span(3, 6);
  L.card(s, "그래프 단계 없이 바로 임베딩", { x: mid.x + mid.w / 2 - 1.6, y: vecCy - 0.2, w: 3.2, h: 0.4,
    fill: C.white, line: C.pill, color: C.slate, size: 14, r: 0.2 });

  // ④ 그래프DB 줄 — 로드 → 정제 → 청킹 → 엔티티·관계 추출 → 병합(보강) → 그래프 구축 → 사전요약(선택) → 임베딩 → 적재
  const kgCy = Y.kg + Y.kgH / 2;
  const kgBoxes = [
    { ...span(0, 0), n: 1, title: "로드", sub: "원본 읽기", who: "코드" },
    { ...span(1, 1), n: 2, title: "정제·\n가명처리", sub: "실명 → 가명", who: "코드" },
    { ...span(2, 2), n: 3, title: "청킹", sub: "글 자르기", who: "코드" },
    { ...span(3, 3), n: 4, title: "엔티티·관계\n추출", who: "LLM" },
    { ...span(4, 4), mark: "보강", title: "같은 이름\n병합", dashed: true, who: "코드 + LLM" },
    { ...span(5, 5), n: 5, title: "지식 그래프\n구축", who: "코드" },
    { ...span(6, 6), mark: "선택", title: "사전요약", sub: "커뮤니티 요약", who: "코드 + LLM" },
    { ...span(7, 7), n: 6, title: "임베딩", sub: "청크 +\n노드 설명", who: "임베딩 모델" },
    { ...span(8, 8), n: 7, title: "적재", sub: "KG + 벡터", who: "코드" },
  ];
  kgBoxes.forEach((b, i) => {
    kgStep(s, b);
    if (i > 0) flow(s, kgBoxes[i - 1].x + kgBoxes[i - 1].w, b.x, kgCy);
  });

  // ⑤ 누가 하나 — 단계마다 담당(코드 · LLM · 임베딩 모델) 표시
  L.card(s, "누가 하나", { x: X0, y: Y.who, w: LBL_W, h: Y.whoH, fill: C.white, line: C.pill, color: C.navy,
    size: 15, bold: true, r: 0.08 });
  kgBoxes.forEach((b) => {
    const st = WHO[b.who];
    L.card(s, b.who, { x: b.x, y: Y.who, w: b.w, h: Y.whoH, ...st, size: 14, bold: true, r: Y.whoH / 2 });
  });

  // ⑥ 나오는 것 — 두 칸씩(첫 구간은 세 칸) 한 상자
  const outs = [
    [0, 2, "청크(글 조각) — 벡터DB와 같음\n이름·연락처 같은 개인정보는 가명으로"],
    [3, 4, "(A사) ─출시→ (B카드)\n같은 이름 합침, 설명은 LLM 요약"],
    [5, 6, "노드·관계 연결망(KG) 완성\n묶기는 알고리즘, 요약은 LLM"],
    [7, 8, "임베딩: 청크 + 노드 설명\n(관계 연결은 임베딩 안 함)\n적재: KG + 벡터 함께 저장"],
  ];
  outs.forEach(([i0, i1, t]) => {
    const { x, w } = span(i0, i1);
    L.card(s, t, { x, y: Y.out, w, h: Y.outH, fill: C.white, line: C.border, color: C.ink, size: 14, r: 0.06 });
  });

  // ⑦ 맨 아래 — 한눈에 비교
  const cg = 0.2, cw = (CW - cg * 2) / 3;
  const cards = [
    { ask: "글을 무엇으로 바꾸나", vec: "숫자 벡터 → 뜻이 비슷한 글 찾기", kg: "노드·관계 → 누가 누구와 이어지나" },
    { ask: "누가 바꾸나", vec: "임베딩 모델 → 빠르고 쌈", kg: "LLM(추출·요약)까지 → 느리고 비쌈" },
    { ask: "무엇에 강한가", vec: "한 문단으로 끝나는 질문", kg: "여러 단계 연결 · 전체 경향" },
  ];
  cards.forEach((c, i) => compareCard(s, { x: X0 + i * (cw + cg), w: cw, n: i + 1, ...c }));
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  const out = process.argv[2] || path.join(__dirname, "그래프DB인덱싱.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
