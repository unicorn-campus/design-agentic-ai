// node build.js — KG 예시로 보는 '노드 탐색'과 '탐색된 노드의 제목' 한 장 빌드 (script.md v3 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const GW = 10.05;                    // 왼편(KG 예시) 폭
const RX = X0 + GW + 0.2;            // 오른편(설명) 시작 x
const RW = X0 + CW - RX;             // 오른편 폭
const GREY = { fill: "EEF0F4", line: C.border, edge: C.sub, text: C.sub };   // 들르지 않는 노드

// 열 x 좌표 — 정형 DB 상자 · 그래프 상자(업종 · 혜택 · 상품 ID · 상품 이름표)
const SQX = 0.75, SQW = 2.35;
const GX = 3.45, GXR = X0 + GW - 0.1;
const CAT = { x: 3.65, w: 1.15 }, BEN = { x: 5.25, w: 1.95 };
const PID = { x: 7.6, w: 1.0 }, PNM = { x: 8.72, w: 1.7 };

// 선 이름표: 선 위에 흰 바탕 글자를 얹음
function edgeLabel(s, t, { cx, cy, w = 0.7 }) {
  L.card(s, t, { x: cx - w / 2, y: cy - 0.16, w, h: 0.32, fill: C.white, line: null, color: C.slate, size: 14, r: 0.05 });
}

// 한 줄(혜택 → 상품): 혜택 노드는 제목으로, 상품 노드는 ID 상자 + 제목 표로 그림
function benefitRow(s, { y, h, ben, pid, pname, on }) {
  L.card(s, ben, { x: BEN.x, y, w: BEN.w, h, size: 14, bold: on, r: 0.1, lw: on ? 2 : 1,
    fill: C.white, line: on ? C.blue : GREY.line, color: on ? C.navy : GREY.text });
  L.card(s, pid, { x: PID.x, y, w: PID.w, h, size: 14, bold: true, r: 0.08, lw: on ? 2 : 1,
    fill: C.white, line: on ? C.blue : GREY.line, color: on ? C.navy : GREY.text });
  L.hline(s, { x: PID.x + PID.w, y: y + h / 2, w: PNM.x - PID.x - PID.w, color: on ? C.blue : GREY.line, width: on ? 2 : 1 });
  L.card(s, pname, { x: PNM.x, y, w: PNM.w, h, size: 14, bold: on, r: h / 2,
    fill: on ? C.blue : GREY.fill, line: null, color: on ? C.white : GREY.text });
}

// 단계 카드: 번호 · 단계명 / 뜻 / 쓰는 것
function stepCard(s, { y, h, n, name, mean, use, useLabel = "쓰는 것" }) {
  L.rr(s, { x: RX, y, w: RW, h, fill: C.white, line: C.border, r: 0.08 });
  L.numBadge(s, n, { x: RX + 0.15, y: y + 0.13, size: 0.4 });
  L.text(s, name, { x: RX + 0.65, y: y + 0.1, w: RW - 0.75, h: 0.46, size: 17, bold: true, color: C.navy });
  s.addText([
    { text: mean, options: { color: C.ink, breakLine: true } },
    { text: `${useLabel}  `, options: { bold: true, color: C.blue } },
    { text: use, options: { color: C.ink } },
  ], { x: RX + 0.15, y: y + 0.6, w: RW - 0.3, h: h - 0.66, fontFace: FONT, fontSize: fs(14), valign: "top",
    margin: 2, isTextBox: true, paraSpaceAfter: 3 });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "KG 예시로 보는 '노드 탐색'과 '탐색된 노드의 제목'",
    lead: "자주 바뀌는 비중은 SQL로 계산해 출발 노드만 정하고, 그래프에서는 노드를 탐색하고 제목을 읽음",
    notes: "소비 비중은 매달 바뀌는 집계값이라 그래프에 넣지 않음. 600명 × 8업종 관계(4,694개)를 매달 다시 맞출 필요가 없어짐. "
      + "노드 탐색: 그래프 안에서는 '업종명=식비'로 출발 노드를 찾고, '대상'·'제공' 관계만 거꾸로 따라감. "
      + "관계는 '혜택 -대상→ 업종', '상품 -제공→ 혜택' 방향으로 저장되지만, 그래프DB는 거꾸로 따라가도 비용이 같음. "
      + "비중은 2025-08 ~ 2026-08 승인 거래 기준임. "
      + "쇼핑·주유 쪽 혜택은 출발 노드가 아니라 들르지 않음."
      + "탐색된 노드의 제목: 도착한 상품·혜택 노드에는 ID(D2-C005, D2-C005-B01)와 함께 "
      + "사람이 읽는 제목(상품명·혜택명)이 있어 그대로 답에 씀. Neo4j 도구에서는 이를 표시 이름(caption)이라고 부름. "
      + "회원-업종 관계는 '소비 패턴이 비슷한 회원 찾기'처럼 회원끼리 비교하는 질문을 쓸 때만 월 1회 배치로 만듦. "
      + "'대상' 관계는 혜택 문서에서 뽑아야 하며, 이 장의 관계는 설명용 예시임.",
  });

  // ① 왼쪽 — KG 예시
  const top = 1.9;
  L.headerBar(s, "KG 예시: 질문 하나를 SQL + 그래프로 풀기", { x: X0, y: top, w: GW, h: 0.42, size: 17, accent: true });
  L.pill(s, "질문", { x: X0, y: 2.44, w: 0.8, h: 0.36 });
  L.text(s, "\"M-6001 회원이 많이 쓰는 업종에 혜택을 주는 카드는?\"", { x: X0 + 0.92, y: 2.42, w: GW - 0.92, h: 0.4,
    size: 17, bold: true, color: C.ink });

  // 단계 표시 줄
  const my = 2.98;
  [[1, "출발 노드 정하기", SQX, C.navy], [2, "노드 탐색", CAT.x, C.blue], [3, "탐색된 노드의 제목", PID.x, C.blue]]
    .forEach(([n, t, x, col]) => {
      L.numBadge(s, n, { x, y: my, size: 0.38, fsz: 16, fill: col });
      L.text(s, t, { x: x + 0.45, y: my - 0.02, w: 2.6, h: 0.42, size: 15, bold: true, color: col });
    });

  // 정형 DB 상자 — 비중은 여기서 계산함(그래프에 없음)
  const by = 3.5, bh = 4.05;
  L.rr(s, { x: SQX, y: by, w: SQW, h: bh, fill: C.white, line: C.border, r: 0.08 });
  L.card(s, "정형 DB (SQL)", { x: SQX, y: by, w: SQW, h: 0.42, fill: C.navy, line: null, color: C.white, size: 15,
    bold: true, r: 0.08 });
  L.text(s, "M-6001 업종별 소비 비중", { x: SQX + 0.08, y: by + 0.48, w: SQW - 0.16, h: 0.36, size: 14, color: C.slate });
  const hi = { color: C.blue, bold: true };
  L.table(s, [
    ["업종", "비중"],
    [{ text: "식비", options: hi }, { text: "63.7%", options: { ...hi, align: "right" } }],
    ["쇼핑", { text: "20.8%", options: { align: "right" } }],
    ["생활", { text: "10.6%", options: { align: "right" } }],
    ["주유", { text: "1.1%", options: { align: "right" } }],
    [{ text: "그 외 4개", options: { bold: false, color: C.sub } }, { text: "3.9%", options: { align: "right", color: C.sub } }],
  ], { x: SQX + 0.12, y: by + 0.9, w: SQW - 0.24, colW: [1.1, SQW - 0.24 - 1.1], rowH: 0.36, size: 14 });
  L.card(s, "1위 업종 = 식비", { x: SQX + 0.12, y: by + bh - 0.66, w: SQW - 0.24, h: 0.5, fill: C.tint, line: null,
    color: C.navy, size: 16, bold: true, r: 0.06 });

  // 그래프 상자
  L.rr(s, { x: GX, y: by, w: GXR - GX, h: bh, fill: C.altRow, line: C.border, r: 0.08 });
  L.card(s, "그래프 (Neo4j)", { x: GX, y: by, w: GXR - GX, h: 0.42, fill: C.blue, line: null, color: C.white, size: 15,
    bold: true, r: 0.08 });

  const rh = 0.54;
  const rows = [
    { y: 4.32, ben: "시간대 할인", pid: "D2-C005", pname: "한빛 하루절약", cat: 0, on: true },
    { y: 4.98, ben: "배달앱 할인", pid: "D2-C033", pname: "한빛 한끼친구", cat: 0, on: true },
    { y: 5.64, ben: "주말 외식 적립", pid: "D2-C035", pname: "한빛 일상포인트", cat: 0, on: true },
    { y: 6.36, ben: "생활쇼핑 할인", pid: "D2-C058", pname: "한빛 반려동행", cat: 1, on: false },
    { y: 6.96, ben: "선택 주유소 할인", pid: "D2-C007", pname: "한빛 주유동행", cat: 2, on: false },
  ];
  const cats = [
    { name: "식비", y: 4.98, on: true },
    { name: "쇼핑", y: 6.36, on: false },
    { name: "주유", y: 6.96, on: false },
  ].map((c) => ({ ...c, cy: c.y + rh / 2 }));

  // 선(대상 · 제공)을 먼저 그리고 노드를 위에 얹음
  rows.forEach((r) => {
    const cy = r.y + rh / 2, c = cats[r.cat];
    const col = r.on ? C.blue : GREY.edge, width = r.on ? 2 : 1.25, dash = r.on ? undefined : "dash";
    // 화살표는 찾아가는 방향(업종 → 혜택 → 상품). 저장 방향(혜택 -대상→ 업종)과 반대여도 그래프는 거꾸로 따라갈 수 있음
    L.arrow(s, { x1: CAT.x + CAT.w, y1: c.cy, x2: BEN.x, y2: cy, color: col, width, dash });
    L.arrow(s, { x1: BEN.x + BEN.w, y1: cy, x2: PID.x, y2: cy, color: col, width, dash });
  });
  cats.forEach((c) => L.card(s, c.name, { x: CAT.x, y: c.y, w: CAT.w, h: rh, size: 17, bold: true, r: 0.1,
    fill: c.on ? C.blue : GREY.fill, line: c.on ? null : GREY.line, color: c.on ? C.white : GREY.text }));
  rows.forEach((r) => benefitRow(s, { ...r, h: rh }));
  edgeLabel(s, "해당 혜택", { cx: (CAT.x + CAT.w + BEN.x) / 2, cy: 4.12, w: 1.0 });
  edgeLabel(s, "제공 상품", { cx: (BEN.x + BEN.w + PID.x) / 2, cy: 4.12, w: 1.0 });
  L.text(s, "업종", { x: CAT.x, y: 3.95, w: CAT.w, h: 0.34, size: 14, bold: true, color: C.slate, align: "center" });
  L.text(s, "혜택", { x: BEN.x, y: 3.95, w: BEN.w, h: 0.34, size: 14, bold: true, color: C.slate, align: "center" });
  L.text(s, "상품 (ID · 제목)", { x: PID.x, y: 3.95, w: PID.w + PNM.w + 0.12, h: 0.34, size: 14, bold: true,
    color: C.slate, align: "center" });

  // SQL 결과로 그래프 출발 노드를 정함
  L.arrow(s, { x1: SQX + SQW, y1: cats[0].cy, x2: CAT.x, y2: cats[0].cy, color: C.navy, width: 2.5 });

  L.text(s, "※ 화살표 = 찾아가는 방향. 저장은 '혜택 →대상→ 업종'·'상품 →제공→ 혜택'이며 거꾸로 따라감",
    { x: SQX, y: 7.6, w: GW - 0.3, h: 0.34, size: 14, color: C.sub });

  // ② 오른쪽 — 세 단계가 뜻하는 것
  L.headerBar(s, "세 단계가 뜻하는 것", { x: RX, y: top, w: RW, h: 0.42, size: 17 });
  stepCard(s, { y: 2.42, h: 1.45, n: 1, name: "출발 노드 정하기 · SQL", mean: "매달 바뀌는 소비 비중은 SQL로 계산",
    use: "식비", useLabel: "결과" });
  stepCard(s, { y: 3.97, h: 1.45, n: 2, name: "노드 탐색 · 그래프", mean: "업종명으로 출발 노드를 찾고, 관계로 갈 길을 거름",
    use: "업종명, 관계(대상·제공)" });
  stepCard(s, { y: 5.52, h: 1.45, n: 3, name: "탐색된 노드의 제목 · 그래프", mean: "도착한 노드의 ID 대신 사람이 읽는 제목을 씀",
    use: "상품명, 혜택명" });

  L.rr(s, { x: RX, y: 7.07, w: RW, h: 0.88, fill: C.tint, line: null, r: 0.08 });
  s.addText([
    { text: "답  ", options: { fontSize: fs(15), bold: true, color: C.blue } },
    { text: "하루절약 · 한끼친구 · 일상포인트", options: { fontSize: fs(15), bold: true, color: C.navy, breakLine: true } },
    { text: "연회비·혜택률은 상품 ID로 따로 가져옴", options: { fontSize: fs(14), color: C.slate } },
  ], { x: RX + 0.15, y: 7.07, w: RW - 0.3, h: 0.88, fontFace: FONT, valign: "middle", margin: 2, isTextBox: true,
    paraSpaceAfter: 2 });
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  const out = process.argv[2] || path.join(__dirname, "KG길고르기이름붙이기.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
