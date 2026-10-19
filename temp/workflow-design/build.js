// 인덱싱 워크플로우 구성안 장표 1장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "워크플로우구성.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 14,
  titleSize = 15, align = "center", r = 0.08, dash, boldLines = 1 }) {
  L.rr(s, { x, y, w, h, fill, line, r, dash });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i < boldLines, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign: "middle", margin: 0.05, isTextBox: true,
    paraSpaceAfter: 1 });
}

// 가로로 같은 폭 칩을 늘어놓고 사이를 화살표로 이음
function chipFlow(s, items, { x, y, w, h, gap = 0.3, styles = [] }) {
  const cw = (w - gap * (items.length - 1)) / items.length;
  items.forEach((lines, i) => {
    const cx = x + i * (cw + gap);
    const st = styles[i] || {};
    richCard(s, lines, { x: cx, y, w: cw, h, fill: st.fill || C.white, line: st.line === undefined ? C.border : st.line,
      color: st.color || C.ink, size: 14, titleSize: 15 });
    if (i < items.length - 1) L.arrow(s, { x1: cx + cw + 0.03, y1: y + h / 2, x2: cx + cw + gap - 0.03, y2: y + h / 2 });
  });
}

const NAVY = { fill: C.navy, line: null, color: C.white };
const BLUE = { fill: C.blue, line: null, color: C.white };
const TINT = { fill: C.tint, line: C.blue, color: C.navy };

async function createSlide01() {
  const s = L.newSlide({
    title: "인덱싱 워크플로우 구성안",
    lead: "서브 워크플로우는 준비, 반영, 정리를 따로 제공하고, 언제 부를지와 게시는 오케스트레이터가 정함",
    notes: "인덱싱은 오케스트레이터, KG 구축, 검색엔진 인덱싱 세 워크플로우로 나눕니다. 서브 워크플로우 두 개는 준비, 반영, "
      + "정리를 따로 부를 수 있게 만들고, 언제 무엇을 부를지는 오케스트레이터가 모드에 따라 정합니다. 서브 워크플로우는 "
      + "활성 세대 파일을 바꾸지 않습니다.\n준비는 아무 데도 쓰지 않고 계산만 해서 결과를 보관합니다. 반영은 Neo4j나 "
      + "검색엔진에 씁니다. 정리는 KG에서 옛 청크와 근거를 잃은 엔티티를 지웁니다.\n전체 재색인은 둘 다 새 세대에 쓰므로 "
      + "게시 전까지 아무에게도 보이지 않습니다. 그래서 두 서브 워크플로우를 처음부터 끝까지 병렬로 돌리고, chunk_id 목록을 "
      + "검증한 뒤 활성 세대 파일을 바꿉니다.\n증분 색인은 지금 쓰는 세대에 바로 쓰므로 쓰는 순간 보입니다. 그래서 준비만 "
      + "병렬로 하고, 반영은 KG에 새 청크 넣기, 검색엔진 문서 교체, KG 옛 청크 지우기 순서로 합니다. 그래프는 먼저 넣고 "
      + "나중에 지워서, 바뀌는 동안에도 검색이 찾은 chunk_id가 그래프에 있게 합니다.\n준비 결과를 보관하므로 반영에서 "
      + "실패해도 오래 걸리는 계산을 다시 하지 않습니다. 되돌리기와 옛 세대 정리는 이 흐름과 따로 처리합니다. 세 워크플로우 "
      + "모두 순서가 정해진 처리라 에이전트가 필요 없고, LLM은 K2 추출의 도구로만 씁니다.",
  });

  // 1) 오케스트레이터 단계 띠
  const SY = 1.9, SH = 0.72, BW0 = 2.0;
  L.darkBadge(s, "오케스트레이터", { x: X0, y: SY, w: BW0, h: SH, size: 16, fill: C.navy });
  const steps = [
    ["① 세대 ID 발급", "gen-X"], ["② 공통 단계", "청킹 결과 파일 생성"], ["③ 인덱스 구축", "서브 워크플로우 호출"],
    ["④ 검증", "chunk_id 목록 비교"], ["⑤ 게시", "활성 세대 파일 교체"],
  ];
  const SX = X0 + BW0 + 0.15, SG = 0.3, SW = (XR - SX - SG * 4) / 5;
  chipFlow(s, steps, { x: SX, y: SY, w: XR - SX, h: SH, gap: SG,
    styles: [TINT, TINT, { fill: C.white, line: C.blue, color: C.navy }, TINT, NAVY] });
  const x3 = SX + 2 * (SW + SG) + SW / 2, x4 = SX + 3 * (SW + SG) + SW / 2;

  // 2) ③ 인덱스 구축: 서브 워크플로우 두 개를 준비, 반영, 정리 구간으로 나눔
  const BY = 2.78, BH = 1.92;
  L.rr(s, { x: X0, y: BY, w: CW, h: BH, fill: C.white, line: C.blue, lw: 1.5 });
  L.arrow(s, { x1: x3, y1: SY + SH + 0.02, x2: x3, y2: BY - 0.02, color: C.blue, width: 2 });
  L.arrow(s, { x1: x4, y1: BY - 0.02, x2: x4, y2: SY + SH + 0.02, color: C.blue, width: 2 });
  L.text(s, "준비 보고를 ④로", { x: x4 + 0.1, y: BY + 0.03, w: 2.2, h: 0.32, size: 14, color: C.blue, bold: true });
  L.text(s, "③ 서브 워크플로우 (활성 세대 파일은 안 바꿈)", { x: X0 + 0.15, y: BY + 0.03, w: 6.5, h: 0.32, size: 15,
    color: C.navy, bold: true });

  const RX0 = X0 + 0.15, LBW = 2.0, PL = 0.62, PG = 0.22, CG = 0.08;
  const AX = RX0 + LBW + 0.15, AW = XR - 0.15 - AX;
  const kg = [
    ["준비", [["K1 추출 단위", "나누기"], ["K2 엔티티와", "관계 추출"], ["K3 가지치기", "결과 보관"]]],
    ["반영", [["K4 Neo4j 저장", "새 청크 넣기"], ["K5 병합", "관련 엔티티만"], ["K6 노드 설명", "임베딩"]]],
    ["정리", [["K7 옛 청크 지움", "고아 엔티티 정리"]]],
  ];
  // K7은 설명이 길어 다른 칩보다 1.6배 넓게 잡음
  const weight = (lines) => (lines[0].startsWith("K7") ? 1.6 : 1);
  const chipCount = kg.reduce((n, [, c]) => n + c.reduce((m, lines) => m + weight(lines), 0), 0);
  const gapsInside = kg.reduce((n, [, c]) => n + (c.length - 1) * CG, 0);
  const ckw = (AW - kg.length * (PL + CG) - (kg.length - 1) * PG - gapsInside) / chipCount;
  // 구간마다 시작 x와 칩 영역 폭을 기록해 검색엔진 줄도 같은 구간에 맞춰 그림
  const phaseX = [];
  let px = AX;
  kg.forEach(([, chips]) => {
    const areaW = chips.reduce((m, lines) => m + weight(lines) * ckw, 0) + (chips.length - 1) * CG;
    phaseX.push({ x: px, chipX: px + PL + CG, areaW });
    px += PL + CG + areaW + PG;
  });

  const rows = [
    { y: BY + 0.42, label: ["KG 구축", "워크플로우"], phases: kg },
    { y: BY + 1.17, label: ["검색엔진 인덱싱", "워크플로우"], phases: [
      ["준비", [["S1 임베딩", "바뀐 것만"], ["S2 키워드 분석", "사전과 별칭, 결과 보관"]]],
      ["반영", [["S3 검색엔진에 쓰기", "card_chunks-gen-X"]]],
      ["정리", []],
    ] },
  ];
  const RH = 0.68;
  rows.forEach((row) => {
    richCard(s, row.label, { x: RX0, y: row.y, w: LBW, h: RH, fill: C.navy, line: null, color: C.white, size: 14,
      titleSize: 15 });
    row.phases.forEach(([name, chips], i) => {
      const ph = phaseX[i];
      const apply = name === "반영";
      L.card(s, name, { x: ph.x, y: row.y, w: PL, h: RH, fill: apply ? C.blue : C.dark, line: null,
        color: C.white, size: 14, bold: true, r: 0.05 });
      if (!chips.length) {
        L.card(s, "없음", { x: ph.chipX, y: row.y, w: ph.areaW, h: RH, fill: C.white, line: C.border, color: C.sub,
          size: 14, dash: "dash" });
        return;
      }
      const cw = (ph.areaW - (chips.length - 1) * CG) / chips.length;
      chips.forEach((lines, j) => {
        richCard(s, lines, { x: ph.chipX + j * (cw + CG), y: row.y, w: cw, h: RH, fill: apply ? C.tint : C.altRow,
          line: C.border, color: apply ? C.navy : C.ink, size: 14, titleSize: 14 });
      });
    });
  });

  // 3) 모드별 호출 순서
  const MY1 = 4.86, MY2 = 5.66, MH = 0.7, MBW = 1.9, MX = X0 + MBW + 0.15, MW = XR - MX;
  richCard(s, ["전체 재색인", "순서 불필요"], { x: X0, y: MY1, w: MBW, h: MH, fill: C.dark, line: null,
    color: C.white, size: 14, titleSize: 16 });
  chipFlow(s, [["K1 ~ K7 와 S1 ~ S3 병렬", "둘 다 새 세대에 씀"], ["④ 검증", "chunk_id 목록 비교"],
    ["⑤ 게시", "활성 세대 파일 교체"]], { x: MX, y: MY1, w: MW, h: MH, gap: 0.35, styles: [TINT, TINT, NAVY] });
  richCard(s, ["증분 색인", "순서 필요"], { x: X0, y: MY2, w: MBW, h: MH, fill: C.blue, line: null,
    color: C.white, size: 14, titleSize: 16 });
  chipFlow(s, [["준비 (병렬)", "K1 ~ K3, S1 ~ S2"], ["반영 K4 ~ K6", "KG에 새 청크 넣기"],
    ["반영 S3", "검색엔진 문서 교체"], ["정리 K7", "KG 옛 청크 지우기"], ["기록 갱신", "입력 지문 갱신"]],
  { x: MX, y: MY2, w: MW, h: MH, gap: 0.3, styles: [TINT, BLUE, BLUE, BLUE, TINT] });

  // 4) 약속 카드 4개
  const rules = [
    // 1번 제목은 사용자가 PowerPoint에서 고친 글(2026-10-19)
    ["서브 워크플로우는 인덱스 구축만 함", "준비, 반영, 정리만 제공. 활성 세대 파일은 안 바꿈"],
    ["활성 세대 파일은 하나", "검색기는 요청마다 한 번 읽고 같은 세대로 두 곳을 조회"],
    ["실패하면 게시 안 함", "준비 결과를 보관해 반영만 다시 실행"],
    ["별도 처리", "되돌리기와 옛 세대 정리는 흐름 밖에서 함"],
  ];
  const RG = 0.2, RCW = (CW - 3 * RG) / 4, RY = 6.52, RCH = 1.4;
  rules.forEach(([title, body], i) => {
    const x = X0 + i * (RCW + RG);
    L.rr(s, { x, y: RY, w: RCW, h: RCH, fill: C.tint, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.15, y: RY + 0.13, size: 0.38, fill: i === 1 ? C.navy : C.blue, fsz: 16 });
    // 제목이 두 줄이 되어도 설명과 겹치지 않게 제목 칸을 두 줄 높이로 잡음
    L.text(s, title, { x: x + 0.62, y: RY + 0.08, w: RCW - 0.75, h: 0.62, size: 16, color: C.navy, bold: true });
    L.text(s, body, { x: x + 0.15, y: RY + 0.74, w: RCW - 0.3, h: RCH - 0.8, size: 14, color: C.body, valign: "top" });
  });
}

async function main() {
  L.createDeck();
  await createSlide01();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
