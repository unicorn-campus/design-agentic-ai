// 검색 갈래 ② 키워드 분석 장표 2장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

// OUT 환경변수로 다른 파일에 빌드할 수 있음(사람이 고친 덱을 덮어쓰지 않고 대조할 때 씀)
const OUT = process.env.OUT || path.join(__dirname, "키워드분석.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 15,
  titleSize = 17, align = "center", r = 0.08 }) {
  L.rr(s, { x, y, w, h, fill, line, r });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i === 0, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign: "middle", margin: 0.08, isTextBox: true,
    paraSpaceAfter: 2 });
}

// 낱말 칩: 겹친 낱말은 블루 채움, 안 겹친 낱말은 흰 바탕 회색 글자
function chip(s, t, { x, y, hit }) {
  const w = 0.32 + 0.21 * [...t].length;
  L.card(s, t, { x, y, w, h: 0.42, fill: hit ? C.blue : C.white, line: hit ? null : C.border,
    color: hit ? C.white : C.sub, size: 16, bold: hit, r: 0.21 });
  return w;
}

function chipRow(s, label, chips, { x, y, note }) {
  L.text(s, label, { x, y, w: 0.7, h: 0.42, size: 15, color: C.slate, bold: true });
  let cx = x + 0.75;
  for (const [t, hit] of chips) cx += chip(s, t, { x: cx, y, hit }) + 0.1;
  if (note) L.text(s, note, { x: cx, y, w: 2.2, h: 0.42, size: 14, color: C.sub });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "검색 갈래 ② 키워드 분석",
    lead: "파이썬에서 Kiwi로 낱말을 잘라 넣고, BM25 점수는 검색 엔진이 검색할 때 계산함",
    notes: "키워드 분석 단계는 한국어 문장을 BM25가 셀 수 있는 낱말로 바꾸는 일입니다. 1-b에서는 이 일을 검색 엔진에 "
      + "맡기지 않고 파이썬에서 Kiwi로 미리 자릅니다. 자른 낱말을 공백으로 이어 text_tokens 필드에 넣으면, 검색 엔진은 "
      + "공백으로만 잘라 역색인을 만듭니다. 예를 들어 '한빛 가족돌봄 카드로 30,000원 이상 결제하면 KB-PAY 할인을 "
      + "받습니다.'는 '한빛가족돌봄 카드 30000 원 이상 결제 kb pay 할인 받 30000원 kb-pay'로 들어갑니다.\n"
      + "검색할 때는 질문을 같은 토크나이저로 잘라 넣고, BM25 점수는 그때 검색 엔진이 계산합니다. "
      + "1-a와 가장 큰 차이는 점수표를 미리 만들어 두지 않는다는 점입니다. 그래서 문서 하나만 지우고 다시 넣는 "
      + "증분 색인이 가능해집니다.",
  });

  // 두 줄 흐름도: 다섯 칸 격자
  const LX = 1.75, GAP = 0.35, BW = (XR - LX - 4 * GAP) / 5;
  const col = (i) => LX + i * (BW + GAP);
  const R1 = { y: 1.95, h: 1.35 }, R2 = { y: 4.0, h: 1.0 };

  L.darkBadge(s, "색인 때", { x: X0, y: R1.y, w: 1.0, h: R1.h, size: 17 });
  L.darkBadge(s, "검색 때", { x: X0, y: R2.y, w: 1.0, h: R2.h, size: 17 });

  const row1 = [
    { lines: ["청크 색인용 본문", "(머리말 포함)"] },
    { lines: ["Kiwi 토크나이저", "표기 통일", "카드명 사전과 별칭 사전", "조사와 어미 빼고 원형 보충"], navy: true },
    { lines: ["text_tokens 필드", "낱말을 공백으로 이음", "예) 한빛가족돌봄 카드 30000원 …"] },
    { lines: ["whitespace 분석기", "공백으로만 자름"] },
    { lines: ["역색인", "낱말 → 청크 목록"] },
  ];
  const row2 = [
    { lines: ["질문"] },
    { lines: ["Kiwi 토크나이저", "(색인 때와 같은 것)"], navy: true },
    { lines: ["match 질의", "text_tokens 필드"] },
    { lines: ["BM25 점수 계산", "k1 1.5, b 0.75 (인덱스 설정)"], blue: true },
    { lines: ["상위 청크", "chunk_id 목록"] },
  ];
  for (const [row, R] of [[row1, R1], [row2, R2]]) {
    row.forEach((b, i) => {
      const fill = b.navy ? C.navy : b.blue ? C.blue : (i === 0 ? C.tint : C.white);
      const color = b.navy || b.blue ? C.white : C.ink;
      richCard(s, b.lines, { x: col(i), y: R.y, w: BW, h: R.h, fill, line: b.navy || b.blue ? null : C.border,
        color, size: 15, titleSize: 17 });
      if (i < row.length - 1) {
        L.arrow(s, { x1: col(i) + BW + 0.04, y1: R.y + R.h / 2, x2: col(i + 1) - 0.04, y2: R.y + R.h / 2 });
      }
    });
  }

  // 두 줄의 토크나이저는 같은 것
  const tx = col(1) + BW / 2;
  L.arrow(s, { x1: tx, y1: R1.y + R1.h + 0.03, x2: tx, y2: R2.y - 0.03, color: C.navy, dash: "dash", head: "none" });
  L.text(s, "같은 사전, 같은 규칙", { x: tx + 0.1, y: 3.43, w: 2.6, h: 0.42, size: 15, color: C.navy, bold: true });

  // 역색인 통계를 검색 때 읽음: 역색인 아래 → 점수 계산 위로 꺾은 점선
  const ix = col(4) + BW / 2, sx = col(3) + BW / 2, my = 3.62;
  L.arrow(s, { x1: ix, y1: R1.y + R1.h + 0.03, x2: ix, y2: my, color: C.blue, dash: "dash", head: "none" });
  L.arrow(s, { x1: ix, y1: my, x2: sx, y2: my, color: C.blue, dash: "dash", head: "none" });
  L.arrow(s, { x1: sx, y1: my, x2: sx, y2: R2.y - 0.03, color: C.blue, dash: "dash" });
  L.text(s, "검색할 때 통계를 읽음", { x: col(3) - 0.3, y: 3.2, w: 2.6, h: 0.36, size: 14, color: C.blue, bold: true,
    align: "right" });

  // 아래 왼쪽: 1-a BM25 색인과 다른 점
  const BY = 5.25, LW = 9.4;
  L.headerBar(s, "벡터DB 인덱싱(1-a)의 BM25 색인과 다른 점", { x: X0, y: BY, w: LW, h: 0.45, size: 18 });
  const KW = 1.7, VW = (LW - KW - 0.2) / 2, VX1 = X0 + KW + 0.1, VX2 = VX1 + VW + 0.1;
  L.card(s, "벡터DB 인덱싱 (bm25s)", { x: VX1, y: BY + 0.53, w: VW, h: 0.36, fill: C.tableHead, line: null,
    color: C.navy, size: 15, bold: true });
  L.card(s, "검색 엔진 (1-b)", { x: VX2, y: BY + 0.53, w: VW, h: 0.36, fill: C.blue, line: null,
    color: C.white, size: 15, bold: true });
  const rows = [
    ["점수 계산", "색인 때 점수표를 미리 만들어 저장", "검색할 때 역색인 통계로 계산"],
    ["갱신", "하나만 바뀌어도 점수표를 다시 만듦\n(항상 전체 재색인)", "바뀐 문서만 지우고 넣음 (증분 색인)"],
    ["전체 재색인", "임시 폴더에서 만든 뒤 폴더 교체", "새 세대 인덱스를 채운 뒤 별칭 전환"],
  ];
  rows.forEach(([k, a, b], i) => {
    const y = BY + 0.97 + i * 0.62;
    L.darkBadge(s, k, { x: X0, y, w: KW, h: 0.56, size: 15 });
    L.card(s, a, { x: VX1, y, w: VW, h: 0.56, fill: C.altRow, color: C.slate, size: 15 });
    L.card(s, b, { x: VX2, y, w: VW, h: 0.56, fill: C.tint, line: C.blue, color: C.navy, size: 15, bold: true });
  });

  // 아래 오른쪽: nori 대신 Kiwi
  const RX = X0 + LW + 0.3, RW = XR - RX;
  L.headerBar(s, "nori 대신 Kiwi를 쓰는 이유", { x: RX, y: BY, w: RW, h: 0.45, accent: true, size: 18 });
  L.rr(s, { x: RX, y: BY + 0.53, w: RW, h: 2.14, fill: C.tint, line: C.border });
  const reasons = [
    ["1-a의 토큰화 규칙과 사전을 그대로 씀", false],
    ["검색 엔진에 형태소 플러그인을 깔지 않음", false],
    ["대신 질문도 반드시 같은 토크나이저로 잘라야 함", true],
  ];
  reasons.forEach(([t, strong], i) => {
    const y = BY + 0.68 + i * 0.64;
    L.numBadge(s, i + 1, { x: RX + 0.18, y: y + 0.06, size: 0.4, fill: strong ? C.navy : C.blue, fsz: 16 });
    L.text(s, t, { x: RX + 0.7, y, w: RW - 0.85, h: 0.52, size: 15, color: strong ? C.navy : C.body, bold: strong });
  });

  // BM25 점수 계산의 뜻과 k1, b의 역할(사람 검토로 추가한 각주)
  L.text(s, "※ 점수 계산: 낱말마다 청크 안 빈도, 전체 청크 중 희소성, 청크 길이 보정을 합쳐 계산 "
    + "(k1은 빈도, b는 길이 보정의 세기)", { x: X0, y: 8.16, w: CW, h: 0.34, size: 14, color: C.sub, margin: 0 });
}

async function createSlide02() {
  const s = L.newSlide({
    title: "카드명 사전과 별칭 사전은 한 쌍",
    lead: "카드명 사전만 넣으면 줄여 부른 카드명 질문이 문서의 카드명 낱말과 겹치지 않음",
    notes: "카드명 사전은 '한빛 가족돌봄'을 한 단어로 묶어 줍니다. 그런데 사전만 넣으면 문서에는 한빛가족돌봄 한 단어만 "
      + "남고, '가족돌봄'이라고만 묻는 질문은 가족, 돌봄, 가족돌봄으로 잘려 카드명과 하나도 겹치지 않습니다. 사전이 "
      + "없을 때보다 오히려 나빠지는 셈입니다. 별칭 사전은 줄여 부른 이름을 정식 카드명 단어로 바꿔 줘서 이 틈을 "
      + "메웁니다.\n별칭은 규칙으로 자동으로 만들되, 장보기처럼 일반 명사와 같은 별칭은 빼야 합니다. 그대로 두면 "
      + "'장보기 할인'이라는 일반 질문이 특정 카드명으로 바뀌어 버립니다.",
  });

  // 예문
  L.pill(s, "문서", { x: X0, y: 1.9, w: 0.9, h: 0.38, size: 15 });
  L.text(s, "한빛 가족돌봄 카드로 30,000원 이상 결제하면 KB-PAY 할인을 받습니다.",
    { x: X0 + 1.0, y: 1.88, w: 12, h: 0.42, size: 17, color: C.ink });
  L.pill(s, "질문", { x: X0, y: 2.36, w: 0.9, h: 0.38, size: 15 });
  L.text(s, "가족돌봄 카드 할인 조건이 뭐예요?", { x: X0 + 1.0, y: 2.34, w: 12, h: 0.42, size: 17, color: C.ink,
    bold: true });

  // 세 칸 비교
  const GW = 0.3, W3 = (CW - 2 * GW) / 3, TOP = 2.95;
  const cases = [
    { head: "사전 없음", fill: C.navy,
      doc: [["한빛", false], ["가족", true], ["돌봄", true], ["가족돌봄", true]],
      q: [["가족", true], ["돌봄", true], ["가족돌봄", true]],
      verdict: ["겹치지만 카드 구분이 약함", "'한빛'은 카드 64종 모두에,", "'가족'은 한빛 가족통신에도 나옴"],
      vfill: C.altRow, vcolor: C.ink },
    { head: "카드명 사전만", fill: C.dark,
      doc: [["한빛가족돌봄", false]],
      q: [["가족", false], ["돌봄", false], ["가족돌봄", false]],
      verdict: ["카드명이 하나도 안 겹침", "줄여 부르면 그 카드를 못 찾음"],
      vfill: C.dark, vcolor: C.white },
    { head: "카드명 사전 + 별칭", fill: C.blue,
      doc: [["한빛가족돌봄", true]],
      q: [["한빛가족돌봄", true]], qnote: "← 별칭이 바꿈",
      verdict: ["그 카드 한 단어로 정확히 겹침", "줄여 불러도 정식 카드명으로 찾음"],
      vfill: C.blue, vcolor: C.white },
  ];
  cases.forEach((c, i) => {
    const x = X0 + i * (W3 + GW);
    L.card(s, c.head, { x, y: TOP, w: W3, h: 0.48, fill: c.fill, line: null, color: C.white, size: 18, bold: true,
      r: 0.06 });
    L.rr(s, { x, y: TOP + 0.55, w: W3, h: 2.3, fill: C.white, line: C.border });
    chipRow(s, "문서", c.doc, { x: x + 0.15, y: TOP + 0.68 });
    chipRow(s, "질문", c.q, { x: x + 0.15, y: TOP + 1.2, note: c.qnote });
    richCard(s, c.verdict, { x: x + 0.15, y: TOP + 1.75, w: W3 - 0.3, h: 0.98, fill: c.vfill,
      line: c.vfill === C.altRow ? C.border : null, color: c.vcolor, size: 15, titleSize: 17 });
  });
  L.text(s, "파란 칩이 문서와 질문에서 겹친 낱말. 카드, 할인 같은 다른 낱말은 세 경우 모두 겹침",
    { x: X0, y: TOP + 2.91, w: CW, h: 0.34, size: 14, color: C.sub });

  // 별칭 사전 만드는 법
  const FY = 6.82;
  L.darkBadge(s, "별칭 사전 만드는 법", { x: X0, y: FY - 0.5, w: 2.6, h: 0.4, size: 16 });
  L.text(s, "사전이나 별칭이 바뀌면 문서 낱말도 바뀜 → 새 세대로 BM25 필드를 다시 만듦 (벡터는 재사용)",
    { x: X0 + 2.75, y: FY - 0.5, w: CW - 2.75, h: 0.4, size: 15, color: C.navy, bold: true });
  const FG = 0.3, FW = (CW - 4 * FG) / 5, FH = 1.08;
  const steps = [
    { lines: ["정식 카드명 64개", "예) 한빛 가족돌봄"], fill: C.tint },
    { lines: ["규칙으로 자동 생성", "'한빛', '카드'를 떼고", "3글자 이상만"] },
    { lines: ["별칭 189개", "가족돌봄 → 한빛가족돌봄"], fill: C.blue, color: C.white },
    { lines: ["일반 명사 자동 제외 3개", "대중교통, 장보기, 출퇴근"] },
    { lines: ["사람 검수", "추가 목록과 제외 목록"] },
  ];
  steps.forEach((st, i) => {
    const x = X0 + i * (FW + FG);
    richCard(s, st.lines, { x, y: FY, w: FW, h: FH, fill: st.fill || C.white,
      line: st.fill === C.blue ? null : C.border, color: st.color || C.ink, size: 15, titleSize: 17 });
    if (i < steps.length - 1) {
      L.arrow(s, { x1: x + FW + 0.03, y1: FY + FH / 2, x2: x + FW + FG - 0.03, y2: FY + FH / 2 });
    }
  });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlide01, createSlide02]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
