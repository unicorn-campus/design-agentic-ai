// 오케스트레이터 ① 세대 ID 발급과 ② 공통 단계 장표 1장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "오케스트레이터1-2단계.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 14,
  titleSize = 15, align = "center", r = 0.08, dash }) {
  L.rr(s, { x, y, w, h, fill, line, r, dash });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i === 0, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign: "middle", margin: 0.05, isTextBox: true,
    paraSpaceAfter: 1 });
}

// 이어 붙인 칸(값 + 설명): ID 모양을 칸으로 나눠 보여 줌
function segments(s, parts, { x, y, h }) {
  let cx = x;
  parts.forEach((p) => {
    richCard(s, [p.value, p.label], { x: cx, y, w: p.w, h, fill: p.fill || C.white, line: p.fill ? null : C.border,
      color: p.color || C.ink, size: 14, titleSize: 15, r: 0.04 });
    cx += p.w + 0.04;
  });
  return cx;
}

async function createSlide01() {
  const s = L.newSlide({
    title: "오케스트레이터 ① 세대 ID 발급, ② 공통 단계",
    lead: "실행마다 세대 ID를 정하고, 원문을 개인정보 처리된 청크 파일 하나로 만들어 두 서브 워크플로우에 넘김",
    notes: "오케스트레이터의 첫 단계는 이번 실행의 세대 ID를 정하는 일입니다. 세대 ID는 실행 이름과 그 해시로 만들어서, 실행이 "
      + "중간에 멈춰도 같은 이름으로 다시 돌리면 같은 세대로 이어서 만듭니다. 이 세대 ID가 검색엔진 인덱스 이름과 Neo4j 세대 "
      + "값의 공통 열쇠가 됩니다. 본격적으로 일하기 전에 원천 파일의 지문을 모아 활성 세대 기록과 비교합니다. 원천, 처리 정책, "
      + "문서 프로필, 토큰화, 임베딩 설정이 모두 같으면 할 일이 없으므로 여기서 끝냅니다.\n두 번째 단계는 원문을 청크 파일 "
      + "하나로 만드는 일입니다. 원문을 읽으면서 회원 정보를 가명 키로 바꾸고, 정제하고, 문서별 규칙으로 청크를 나눕니다. "
      + "원문은 메모리에서만 다루고 개인정보 처리가 끝난 청크만 저장합니다. 바뀌지 않은 문서는 이전 세대의 처리된 청크를 그대로 "
      + "씁니다. 청크 ID는 문서 키와 본문 해시로 만들어서 본문이 같으면 ID도 같습니다. 이 파일 하나를 두 서브 워크플로우가 함께 "
      + "읽기 때문에 KG와 검색엔진 인덱스의 chunk_id가 어긋나지 않습니다.",
  });

  // ───── 왼쪽: ① 세대 ID 발급과 사전 검사
  const LW = 6.9, RX = X0 + LW + 0.3, RW = XR - RX;
  L.headerBar(s, "① 세대 ID 발급과 사전 검사", { x: X0, y: 1.9, w: LW, h: 0.45, size: 18 });

  L.text(s, "세대 ID 모양", { x: X0, y: 2.45, w: LW, h: 0.32, size: 15, color: C.slate, bold: true });
  segments(s, [
    { value: "gen-", label: "접두어", w: 0.95 },
    { value: "birthfix-20261018b", label: "실행 이름", w: 3.05, fill: C.blue, color: C.white },
    { value: "-efeb65bd", label: "실행 이름 해시 8자리", w: 2.82 },
  ], { x: X0, y: 2.8, h: 0.72 });

  const HW = (LW - 0.2) / 2;
  richCard(s, ["같은 실행 이름 = 같은 세대 ID", "중단돼도 같은 세대로 이어서 만듦"], { x: X0, y: 3.65, w: HW, h: 0.8,
    fill: C.tint, line: C.border, color: C.navy });
  richCard(s, ["두 서브 워크플로우의 공통 열쇠", "card_chunks-gen-X, Neo4j gen-X"], { x: X0 + HW + 0.2, y: 3.65, w: HW,
    h: 0.8, fill: C.tint, line: C.border, color: C.navy });

  L.text(s, "사전 검사: 할 일이 있는지 먼저 확인", { x: X0, y: 4.65, w: LW, h: 0.32, size: 15, color: C.slate,
    bold: true });
  const PY = 5.05, c1w = 1.85, c2w = 2.45, ow = LW - c1w - c2w - 0.6;
  richCard(s, ["원천 지문 수집", "파일 SHA-256"], { x: X0, y: PY + 0.35, w: c1w, h: 0.95 });
  L.arrow(s, { x1: X0 + c1w + 0.03, y1: PY + 0.82, x2: X0 + c1w + 0.27, y2: PY + 0.82 });
  const c2x = X0 + c1w + 0.3;
  richCard(s, ["활성 세대 기록과 비교", "원천, 처리 정책, 문서 프로필, 토큰화, 임베딩 설정"], { x: c2x, y: PY + 0.2,
    w: c2w, h: 1.25, fill: C.tint, line: C.blue, color: C.navy });
  const ox = c2x + c2w + 0.3;
  richCard(s, ["모두 같음", "실행 종료 (할 일 없음)"], { x: ox, y: PY, w: ow, h: 0.78, fill: C.dark, line: null,
    color: C.white });
  richCard(s, ["하나라도 다름", "② 공통 단계로"], { x: ox, y: PY + 0.88, w: ow, h: 0.78, fill: C.blue, line: null,
    color: C.white });
  L.arrow(s, { x1: c2x + c2w + 0.03, y1: PY + 0.6, x2: ox - 0.03, y2: PY + 0.39 });
  L.arrow(s, { x1: c2x + c2w + 0.03, y1: PY + 1.05, x2: ox - 0.03, y2: PY + 1.27 });
  L.text(s, "전체 재색인을 요청하면 사전 검사를 건너뛰고 ②로 감", { x: X0, y: 6.85, w: LW, h: 0.36, size: 14,
    color: C.sub });

  // ───── 오른쪽: ② 공통 단계
  L.headerBar(s, "② 공통 단계: 원문 → 청크 파일", { x: RX, y: 1.9, w: RW, h: 0.45, size: 18, accent: true });
  const FG = 0.25, FW = (RW - 3 * FG) / 4, FY = 2.5, FH = 0.98;
  const flow = [
    { lines: ["원천 문서", "약관과 혜택 PDF", "상담 이력 TXT"], fill: C.altRow },
    { lines: ["로드와 가명처리", "회원 정보를", "가명 키로 바꿈"], fill: C.tint, line: C.blue, color: C.navy },
    { lines: ["정제", "표기 정리", "메타데이터 검증"] },
    { lines: ["청킹", "문서별 분할 정책", "카드 경계, 머리말"] },
  ];
  flow.forEach((f, i) => {
    const x = RX + i * (FW + FG);
    richCard(s, f.lines, { x, y: FY, w: FW, h: FH, fill: f.fill || C.white, line: f.line || C.border,
      color: f.color || C.ink });
    if (i < flow.length - 1) L.arrow(s, { x1: x + FW + 0.03, y1: FY + FH / 2, x2: x + FW + FG - 0.03, y2: FY + FH / 2 });
  });
  richCard(s, ["prepared-chunks.json + SHA-256", "개인정보 처리된 청크만 저장 → K1, S1이 함께 읽음"], { x: RX, y: 3.62,
    w: RW, h: 0.72, fill: C.navy, line: null, color: C.white, titleSize: 16 });

  const rules = [
    ["원문은 남기지 않음", "가명처리 전 원문은 메모리에서만 다루고 처리된 청크만 저장"],
    ["바뀌지 않은 문서는 재사용", "원천 해시와 처리 정책이 같으면 이전 세대의 처리된 청크를 씀"],
    ["실행 중 원천이 바뀌면 중단", "지문이 달라지면 같은 실행으로 이어 가지 않음"],
  ];
  const KG = 0.15, KW = (RW - 2 * KG) / 3;
  rules.forEach(([t, b], i) => {
    const x = RX + i * (KW + KG);
    L.rr(s, { x, y: 4.48, w: KW, h: 1.3, fill: C.altRow, line: C.border });
    L.text(s, t, { x: x + 0.1, y: 4.53, w: KW - 0.2, h: 0.38, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.1, y: 4.92, w: KW - 0.2, h: 0.8, size: 14, color: C.body, valign: "top" });
  });

  L.text(s, "chunk_id 만드는 법: 본문이 같으면 ID도 같음", { x: RX, y: 5.92, w: RW, h: 0.32, size: 15, color: C.slate,
    bold: true });
  segments(s, [
    { value: "D1_27223010abe31291", label: "문서 키", w: 2.9, fill: C.blue, color: C.white },
    { value: "_112f1e4abea05436", label: "본문 해시 16자리", w: 2.7 },
    { value: "_0000", label: "같은 본문 반복 번호", w: RW - 5.68 },
  ], { x: RX, y: 6.27, h: 0.72 });
  L.text(s, "청크 한 건: chunk_id, text, index_text(머리말 포함), metadata(가명 키 포함), text_hash, token_count",
    { x: RX, y: 7.12, w: RW, h: 0.62, size: 14, color: C.body });
}

async function main() {
  L.createDeck();
  await createSlide01();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
