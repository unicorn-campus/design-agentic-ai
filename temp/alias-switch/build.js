// 검색 갈래 ④ 별칭 전환 장표 1장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "별칭전환.pptx");

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

// 세대 인덱스 상자 모양: live(사용 중), building(채우는 중), checked(건수 확인), kept(남겨 둠)
const GEN = {
  live: { fill: C.navy, line: null, color: C.white },
  building: { fill: C.white, line: C.sub, color: C.slate, dash: "dash" },
  checked: { fill: C.tint, line: C.blue, color: C.navy },
  kept: { fill: C.altRow, line: C.border, color: C.sub },
};

async function createSlide01() {
  const s = L.newSlide({
    title: "검색 갈래 ④ 별칭 전환",
    lead: "새 세대 인덱스를 다 채우고 건수를 확인한 뒤, 검색이 보는 이름표(별칭)만 한 번에 옮김",
    notes: "검색은 실제 인덱스 이름을 모르고 card_chunks라는 별칭에만 질의합니다. 전체 재색인 때는 새 세대 인덱스를 따로 "
      + "다 채우고, refresh 뒤 건수가 기대와 같은지 확인합니다. 건수가 다르면 덜 만들어진 세대이므로 전환하지 않습니다.\n"
      + "확인이 끝나면 별칭을 새 세대로 옮기는데, 이때 옛 세대에서 빼는 일과 새 세대에 붙이는 일을 update_aliases 한 요청에 "
      + "함께 넣습니다. 두 번에 나눠 부르면 그 사이에 별칭이 아무것도 가리키지 않아 검색 결과가 비는 순간이 생깁니다.\n"
      + "옛 세대 인덱스는 지우지 않고 남겨 두므로, 문제가 생기면 같은 함수에 옛 인덱스를 넘겨 바로 되돌릴 수 있습니다. "
      + "그래프 쪽 Neo4j 세대도 같은 순간에 맞춰 바꿔야 검색 결과의 chunk_id가 그래프에서 끊기지 않습니다. 예제는 검색 엔진 "
      + "쪽만 구현했습니다.",
  });

  // 위쪽 세 칸: 전환 전, 건수 확인, 전환 후
  const PG = 0.45, PW = (CW - 2 * PG) / 3, PY = 1.9;
  const panels = [
    { head: "전환 전", fill: C.dark, target: 0,
      gens: [["1세대 인덱스", "사용 중", "live"], ["2세대 인덱스", "채우는 중", "building"]] },
    { head: "건수 확인", fill: C.dark, target: 0, note: "refresh 뒤 건수 확인.\n다르면 전환 중단",
      gens: [["1세대 인덱스", "사용 중", "live"], ["2세대 인덱스", "건수 23 = 입력 23", "checked"]] },
    { head: "전환 후", fill: C.blue, target: 1,
      gens: [["1세대 인덱스", "남겨 둠 (되돌리기용)", "kept"], ["2세대 인덱스", "사용 중", "live"]] },
  ];
  panels.forEach((p, i) => {
    const x = X0 + i * (PW + PG);
    L.card(s, p.head, { x, y: PY, w: PW, h: 0.42, fill: p.fill, line: null, color: C.white, size: 17, bold: true,
      r: 0.06 });
    L.rr(s, { x, y: PY + 0.5, w: PW, h: 1.95, fill: C.white, line: C.border });
    const pillX = p.note ? x + 0.2 : x + (PW - 2.3) / 2;
    L.pill(s, "별칭 card_chunks", { x: pillX, y: PY + 0.65, w: 2.3, h: 0.4, size: 15 });
    if (p.note) {
      L.text(s, p.note, { x: x + 2.6, y: PY + 0.57, w: PW - 2.7, h: 0.6, size: 14, color: C.blue, bold: true });
    }
    const GW = (PW - 0.6) / 2;
    p.gens.forEach(([name, state, kind], j) => {
      const gx = x + 0.2 + j * (GW + 0.2);
      const st = GEN[kind];
      richCard(s, [name, state], { x: gx, y: PY + 1.5, w: GW, h: 0.82, fill: st.fill, line: st.line,
        color: st.color, dash: st.dash, size: 14, titleSize: 15 });
    });
    // 별칭이 가리키는 세대로 화살표
    const tx = x + 0.2 + p.target * (GW + 0.2) + GW / 2;
    L.arrow(s, { x1: pillX + 1.15, y1: PY + 1.07, x2: tx, y2: PY + 1.47, color: C.navy, width: 2 });
    if (i < panels.length - 1) {
      L.arrow(s, { x1: x + PW + 0.06, y1: PY + 1.45, x2: x + PW + PG - 0.06, y2: PY + 1.45, color: C.slate, width: 2 });
    }
  });

  // 가운데: 왜 한 요청인가
  const MY = 4.55, HW = (CW - 0.3) / 2, RX2 = X0 + HW + 0.3;
  L.darkBadge(s, "두 번 나눠 부르면", { x: X0, y: MY, w: 2.4, h: 0.38, size: 15 });
  L.card(s, "update_aliases 한 요청", { x: RX2, y: MY, w: 2.9, h: 0.38, fill: C.blue, line: null, color: C.white,
    size: 15, bold: true, r: 0.05 });
  const BY = MY + 0.48, BH = 0.85;
  const left = [
    { lines: ["remove", "1세대에서 뺌"], fill: C.white },
    { lines: ["별칭이 비어 있음", "이 사이 검색 0건"], fill: C.dark, color: C.white, line: null },
    { lines: ["add", "2세대에 붙임"], fill: C.white },
  ];
  const LW3 = (HW - 2 * 0.35) / 3;
  left.forEach((b, i) => {
    const bx = X0 + i * (LW3 + 0.35);
    richCard(s, b.lines, { x: bx, y: BY, w: LW3, h: BH, fill: b.fill, line: b.line === undefined ? C.border : b.line,
      color: b.color || C.ink, size: 14, titleSize: 15 });
    if (i < left.length - 1) L.arrow(s, { x1: bx + LW3 + 0.04, y1: BY + BH / 2, x2: bx + LW3 + 0.31, y2: BY + BH / 2 });
  });
  const RW1 = HW * 0.58, RW2 = HW - RW1 - 0.35;
  richCard(s, ["remove 1세대 + add 2세대", "한 요청에 함께 넣음"], { x: RX2, y: BY, w: RW1, h: BH, fill: C.tint,
    line: C.blue, color: C.navy, size: 14, titleSize: 15 });
  L.arrow(s, { x1: RX2 + RW1 + 0.04, y1: BY + BH / 2, x2: RX2 + RW1 + 0.31, y2: BY + BH / 2 });
  richCard(s, ["빈 순간 없음", "검색은 늘 한 세대를 봄"], { x: RX2 + RW1 + 0.35, y: BY, w: RW2, h: BH, fill: C.blue,
    line: null, color: C.white, size: 14, titleSize: 15 });

  // 아래 왼쪽: 코드 발췌
  const CY = 6.1, CWID = 8.2;
  L.codeBox(s, [
    "previous = resolve_alias(client, alias)   # 지금 별칭이 가리키는 세대",
    "actions = [{\"remove\": {\"index\": name, \"alias\": alias}}",
    "           for name in previous]",
    "actions.append({\"add\": {\"index\": new_index, \"alias\": alias}})",
    "client.indices.update_aliases(body={\"actions\": actions})  # 한 요청",
  ], { x: X0, y: CY, w: CWID, h: 1.85, size: 14, title: "search_branch.py step4_switch_alias 발췌" });

  // 아래 오른쪽: 되돌리기, 시험 결과, 주의
  const RX = X0 + CWID + 0.3, RW = XR - RX;
  L.card(s, "되돌리기: 같은 함수에 1세대 인덱스를 넘김", { x: RX, y: CY, w: RW, h: 0.45, fill: C.blue, line: null,
    color: C.white, size: 15, bold: true });
  richCard(s, ["시험: 전환 세 번 모두 통과", "없음 → 1세대, 1세대 → 2세대, 2세대 → 1세대(되돌리기)",
    "되돌린 뒤 건수 23, 검색 동작"], { x: RX, y: CY + 0.53, w: RW, h: 0.82, fill: C.tint, line: C.border,
    color: C.navy, size: 14, titleSize: 15 });
  L.callout(s, "그래프(Neo4j) 세대도 같은 순간에 바꿔야 함. 예제는 검색 엔진 쪽만 구현",
    { x: RX, y: CY + 1.43, w: RW, h: 0.42, size: 14 });
}

async function main() {
  L.createDeck();
  await createSlide01();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
