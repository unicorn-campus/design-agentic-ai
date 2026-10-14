// node build.js — 그래프에는 ID와 최소 속성만 넣음 한 장 빌드 (script.md v2 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const LEFT_W = 4.6;                  // 왼편(최소 속성 설명) 폭
const RX = X0 + LEFT_W + 0.2;        // 오른편(우리 시스템 예시) 시작 x
const RW = X0 + CW - RX;             // 오른편 폭

// 판정 카드: 질문 + 우리 예, 오른쪽에 넣음/뺌 필
function judgeCard(s, { y, h, n, ask, ex, verdict, keep }) {
  L.rr(s, { x: X0, y, w: LEFT_W, h, fill: C.white, line: C.border, r: 0.08 });
  L.numBadge(s, n, { x: X0 + 0.12, y: y + 0.14, size: 0.36, fsz: 16 });
  s.addText([
    { text: ask, options: { fontSize: fs(15), bold: true, color: C.navy, breakLine: true } },
    { text: ex, options: { fontSize: fs(14), color: C.slate } },
  ], { x: X0 + 0.55, y, w: LEFT_W - 1.75, h, fontFace: FONT, valign: "middle", margin: 2, isTextBox: true,
    paraSpaceAfter: 0 });
  L.card(s, verdict, { x: X0 + LEFT_W - 1.17, y: y + h / 2 - 0.19, w: 1.05, h: 0.38, size: 14, bold: true, r: 0.19,
    fill: keep ? C.tint : C.dark, line: keep ? C.pill : null, color: keep ? C.blue : C.white });
}

// 처리 단계 상자: 색 머리띠(번호·저장소) + 단계명 + 하는 일 + 넘기는 것
function stepBox(s, { x, y, w, h, head, color, name, body, out }) {
  L.rr(s, { x, y, w, h, fill: C.white, line: C.border, r: 0.08 });
  L.card(s, head, { x, y, w, h: 0.4, fill: color, line: null, color: C.white, size: 15, bold: true, r: 0.08 });
  s.addText([
    { text: name, options: { bold: true, color: C.navy, breakLine: true } },
    { text: body, options: { color: C.ink } },
  ], { x: x + 0.08, y: y + 0.44, w: w - 0.16, h: h - 0.86, fontFace: FONT, fontSize: fs(14), valign: "top",
    margin: 2, isTextBox: true, paraSpaceAfter: 0 });
  L.text(s, `넘김: ${out}`, { x: x + 0.08, y: y + h - 0.4, w: w - 0.16, h: 0.34, size: 14, bold: true, color: C.blue });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "그래프에는 ID와 최소 속성만 넣음",
    lead: "그래프는 노드 탐색과 제목만 맡고, 비중·금액·원문은 원래 저장소에서 ID로 가져옴",
    notes: "ID만 넣으면 노드 하나를 지날 때마다 정형 DB를 다시 불러야 해서 여러 단계 탐색이 느려짐. "
      + "그래서 노드 탐색에 쓰는 속성(업종명)과 탐색된 노드의 제목(상품명·혜택명)은 그래프에 복제함. "
      + "전부 넣으면 값이 두 곳에 생겨 맞춰 두기(동기화) 부담과 민감정보 노출 범위가 커짐. "
      + "그래서 자주 바뀌고 크고 민감한 값은 뺌. "
      + "업종 비중은 매달 바뀌는 집계값이라 그래프에 넣지 않고 SQL로 계산해 출발 노드만 정함. "
      + "회원-업종 관계는 '소비 패턴이 비슷한 회원 찾기'처럼 회원끼리 비교하는 질문을 쓸 때만 월 1회 배치로 만듦. "
      + "업종과 잇는 대상은 발급 카드가 아니라 상품(64종)이며, 사이에 혜택 노드를 둠.",
  });

  // ① 왼쪽 — 최소 속성이란?
  const top = 1.9;
  L.headerBar(s, "최소 속성이란?", { x: X0, y: top, w: LEFT_W, h: 0.42, size: 17 });
  L.rr(s, { x: X0, y: 2.42, w: LEFT_W, h: 0.95, fill: C.tint, line: null, r: 0.08 });
  s.addText([
    { text: "그래프 안에서 ", options: { color: C.ink } },
    { text: "① 노드 탐색", options: { color: C.navy, bold: true } },
    { text: "과", options: { color: C.ink, breakLine: true } },
    { text: "② 탐색된 노드의 제목", options: { color: C.navy, bold: true } },
    { text: "에", options: { color: C.ink, breakLine: true } },
    { text: "꼭 필요한 정보만 넣은 것", options: { color: C.ink } },
  ], { x: X0 + 0.12, y: 2.42, w: LEFT_W - 0.24, h: 0.95, fontFace: FONT, fontSize: fs(15), valign: "middle",
    margin: 2, isTextBox: true });

  L.rr(s, { x: X0, y: 3.47, w: LEFT_W, h: 1.05, fill: C.white, line: C.border, r: 0.08 });
  s.addText([
    { text: "비유: 지하철 노선도", options: { fontSize: fs(15), bold: true, color: C.navy, breakLine: true } },
    { text: "역 이름·노선·환승만 있어도 길은 찾음", options: { fontSize: fs(14), color: C.ink, breakLine: true } },
    { text: "시간표·역 안 상가는 역에 가서 봄", options: { fontSize: fs(14), color: C.slate } },
  ], { x: X0 + 0.12, y: 3.47, w: LEFT_W - 0.24, h: 1.05, fontFace: FONT, valign: "middle", margin: 2,
    isTextBox: true, paraSpaceAfter: 0 });

  L.darkBadge(s, "넣을지 정하는 질문 3가지", { x: X0, y: 4.67, w: LEFT_W, h: 0.4, size: 15 });
  const jh = 0.86, jg = 0.08, jy = 5.17;
  [
    { ask: "노드 탐색에 쓰나?", ex: "예) 업종명=식비, 관계(대상·제공)", verdict: "넣음", keep: true },
    { ask: "탐색된 노드의 제목인가?", ex: "예) 상품명, 혜택명", verdict: "넣음", keep: true },
    { ask: "자주 바뀌거나 크거나 민감한가?", ex: "예) 업종 비중, 카드 상태, 상담 원문", verdict: "빼고 ID만", keep: false },
  ].forEach((q, i) => judgeCard(s, { y: jy + i * (jh + jg), h: jh, n: i + 1, ...q }));

  // ② 오른쪽 위 — 우리 시스템 예시 표
  L.headerBar(s, "우리 시스템 예시: 무엇을 그래프에 넣나", { x: RX, y: top, w: RW, h: 0.42, size: 17, accent: true });
  const keepCell = (t) => ({ text: t, options: { color: C.navy, bold: true } });
  const noneCell = (t) => ({ text: t, options: { color: C.sub, bold: true } });
  L.table(s, [
    ["노드", "그래프에 넣는 것 (ID + 최소 속성)", "원래 자리에 두는 것"],
    ["회원", keepCell("회원 가명 ID, 고객군"), "가입일·연령대·연체 (정형 DB)"],
    ["카드", keepCell("카드 ID"), "카드 상태·발급일 (정형 DB)"],
    ["상품", keepCell("상품 ID, 상품명"), "연회비 (정형 DB)"],
    ["혜택", keepCell("혜택 ID, 혜택명"), "혜택률·한도·조건 문구 (벡터 DB)"],
    ["업종", keepCell("업종명 (식비·주유 등 8개)"), "없음"],
    ["거래", noneCell("넣지 않음 — 업종 비중은 SQL로 계산"), "거래 건별 금액 (정형 DB)"],
    ["상담", keepCell("상담 ID, 상담일, 불만 주제, 조각 ID"), "발언 원문 (벡터 DB)"],
  ], { x: RX, y: 2.42, w: RW, colW: [1.4, 4.5, 4.2], rowH: 0.36, size: 14 });

  // ③ 오른쪽 아래 — 질문 하나가 처리되는 순서
  const qy = 5.46;
  L.pill(s, "예시 질문", { x: RX, y: qy, w: 1.2, h: 0.36 });
  L.text(s, "\"M-6001 회원이 많이 쓰는 업종에 혜택을 주는 카드는?\"", { x: RX + 1.32, y: qy - 0.02, w: RW - 1.32,
    h: 0.4, size: 16, bold: true, color: C.ink });

  const sy = 5.92, sh = 1.42, ag = 0.3, sw = (RW - ag * 3) / 4;
  const steps = [
    { head: "① 정형 DB", color: C.navy, name: "출발 노드 정하기", body: "업종 비중 계산", out: "식비" },
    { head: "② 그래프", color: C.blue, name: "노드 탐색", body: "식비 → 혜택 → 상품", out: "ID·제목" },
    { head: "③ 정형 DB", color: C.navy, name: "정확한 값", body: "상품 ID로 연회비 조회", out: "연회비" },
    { head: "④ 벡터 DB", color: C.dark, name: "근거 문단", body: "혜택 ID로 문단 찾기", out: "혜택 문단" },
  ];
  steps.forEach((st, i) => {
    const x = RX + i * (sw + ag);
    stepBox(s, { x, y: sy, w: sw, h: sh, ...st });
    if (i < steps.length - 1) {
      L.arrow(s, { x1: x + sw + 0.04, y1: sy + sh / 2, x2: x + sw + ag - 0.04, y2: sy + sh / 2, color: C.slate, width: 2 });
    }
  });

  L.callout(s, "ID 하나로 세 저장소를 이음 → 값은 원래 자리에 한 번만 두고, 그래프는 노드 탐색과 제목만 맡음",
    { x: RX, y: 7.47, w: RW, h: 0.45, size: 16 });
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  const out = process.argv[2] || path.join(__dirname, "그래프최소속성.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
