// node build.js [출력 경로] — AGENTS.md 구성 한 장 요약 빌드 (script.md 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, fs } = L;

const LW = 1.3;                 // 왼쪽 층 라벨 폭
const CX = X0 + LW + 0.12;      // 층 내용 시작 x
const CR = X0 + L.CW;           // 내용 오른쪽 끝 x
const CWC = CR - CX;            // 층 내용 폭

// 두 줄 카드: 굵은 머리글 + 본문. 머리글에 runs 배열을 넘기면 한 줄에 여러 서식을 섞음
function card2(s, { x, y, w, h, head, body, fill = C.white, line = C.border, dash, headColor = C.navy,
  bodyColor = C.slate, headSize = 15, bodySize = 14, align = "center", margin = 7, textDx = 0 }) {
  L.rr(s, { x, y, w, h, fill, line, dash, r: 0.08 });
  const heads = Array.isArray(head) ? head : [{ text: head, size: headSize, color: headColor, bold: true }];
  const runs = heads.map((r, i) => ({ text: r.text, options: { fontSize: fs(r.size || headSize), color: r.color || headColor,
    bold: r.bold !== false, breakLine: i === heads.length - 1 } }));
  String(body).split("\n").forEach((t, i, arr) => runs.push({ text: t,
    options: { fontSize: fs(bodySize), color: bodyColor, bold: false, breakLine: i < arr.length - 1 } }));
  // textDx: 왼쪽 강조 막대가 있는 카드는 글 상자를 막대 오른쪽으로 비켜 놓음(margin은 포인트 단위)
  s.addText(runs, { x: x + textDx, y, w: w - textDx, h, fontFace: FONT, align, valign: "middle", margin, isTextBox: true, paraSpaceAfter: 0 });
}

// 층 라벨: 영문 키워드 + 한글 부제
function layerLabel(s, { y, h, key, sub, fill }) {
  L.rr(s, { x: X0, y, w: LW, h, fill, line: null, r: 0.08 });
  s.addText([
    { text: key, options: { fontSize: fs(20), bold: true, color: C.white, breakLine: true } },
    { text: sub, options: { fontSize: fs(14), color: C.white } },
  ], { x: X0, y, w: LW, h, fontFace: FONT, align: "center", valign: "middle", margin: 3, isTextBox: true });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "AGENTS.md 구성 한눈에 보기",
    lead: "목표·원칙(WHY) 아래 8명 팀(WHO)이 협업·작업 규칙(HOW)으로 움직이고, 품질 장치(CHECK)가 결과를 지킴",
    notes: "위에서 아래로 '왜 → 누가 → 어떻게 → 어떻게 지키나' 순서로 읽음. "
      + "팀원 위임은 .agents/agents/ 원본 정의를 Agent 도구로 실제 호출하는 방식이며, "
      + "협업 패턴은 접두어 없이 요청 신호로 자동 판정함(모호하면 계층형).",
  });

  // ① WHY — 목표 + M사상
  const y1 = 1.9, h1 = 0.95;
  layerLabel(s, { y: y1, h: h1, key: "WHY", sub: "목표·M사상", fill: C.navy });
  const goalW = CWC - 5.6 - 0.15;
  card2(s, { x: CX, y: y1, w: goalW, h: h1, fill: C.tint, align: "left", margin: 13, headSize: 18,
    head: "Agentic AI 아키텍처 설계",
    body: "멀티모달 · LangGraph · RAG/GraphRAG · NL2SQL · 온톨로지 · MCP/A2A · MAS 조합" });
  [["Value-Oriented", "WHY First"], ["Interactive", "Believe · Yes And"], ["Iterative", "Fast fail · Pivot"]]
    .forEach(([hd, bd], i) => card2(s, { x: CX + goalW + 0.15 + i * 1.9, y: y1, w: 1.8, h: h1, head: hd, body: bd }));

  // ② WHO — 오케스트레이터 → 팀원 7명 + 라우팅 규칙
  const y2 = 2.97, h2 = 2.1, orchW = 2.5;
  layerLabel(s, { y: y2, h: h2, key: "WHO", sub: "팀 8명", fill: C.blue });
  L.rr(s, { x: CX, y: y2, w: orchW, h: h2, fill: C.navy, line: null, r: 0.08 });
  s.addText([
    { text: "클로니", options: { fontSize: fs(22), bold: true, color: C.white, breakLine: true } },
    { text: "아키텍트 겸 오케스트레이터", options: { fontSize: fs(14), color: C.white, breakLine: true } },
    { text: " ", options: { fontSize: fs(14), breakLine: true } },
    { text: "단일/멀티 판정 · 패턴 선택", options: { fontSize: fs(14), color: C.tint, breakLine: true } },
    { text: "산출물 검수 · 통합", options: { fontSize: fs(14), color: C.tint } },
  ], { x: CX, y: y2, w: orchW, h: h2, fontFace: FONT, align: "center", valign: "middle", margin: 9, isTextBox: true });
  const mx = CX + orchW + 0.38, mw = 2.56, mg = (CR - mx - 4 * mw) / 3, mh = (h2 - 0.12) / 2;
  L.arrow(s, { x1: CX + orchW + 0.04, y1: y2 + h2 / 2, x2: mx - 0.04, y2: y2 + h2 / 2, color: C.blue, width: 2 });
  const members = [
    ["플로니", "오케스트레이션", "LangGraph · Harness"],
    ["지식니", "지식·데이터", "RAG·GraphRAG·NL2SQL"],
    ["커넥니", "도구 연동", "MCP · A2A · 인증·권한"],
    ["모달니", "멀티모달", "STT · TTS · VLM · 요약"],
    ["스택니", "API·UI", "FastAPI · SSE · React"],
    ["옵스니", "플랫폼·배포", "컨테이너 · 비밀값 · 롤백"],
    ["에듀니", "교육·문서", "코드 해설 · 용어사전"],
  ];
  members.forEach(([nick, role, area], i) => card2(s, {
    x: mx + (i % 4) * (mw + mg), y: y2 + Math.floor(i / 4) * (mh + 0.12), w: mw, h: mh, align: "left", margin: 8,
    head: [{ text: nick, size: 17 }, { text: `  ${role}`, size: 14, color: C.slate, bold: false }],
    body: area, bodyColor: C.ink }));
  card2(s, { x: mx + 3 * (mw + mg), y: y2 + mh + 0.12, w: mw, h: mh, fill: C.altRow, line: C.blue, dash: "dash",
    align: "left", margin: 10, headColor: C.blue, head: "라우팅 규칙", body: "키워드로 담당자 선정\n없으면 클로니 직접" });

  // ③ HOW — 협업 패턴 2×2 + 작업 규칙 3×2
  const y3 = 5.19, h3 = 1.75, ch = 0.62, cy = y3 + 0.43;
  layerLabel(s, { y: y3, h: h3, key: "HOW", sub: "협업·작업 규칙", fill: C.dark });
  const pw = 2.575, patW = 2 * pw + 0.15, rx = CX + patW + 0.25, rw = (CR - rx - 0.2) / 3;
  L.text(s, "협업 패턴 — 신호로 자동 선택, 모호하면 계층형", { x: CX, y: y3, w: patW, h: 0.35, size: 14, color: C.navy,
    bold: true, margin: 0 });
  L.text(s, "작업 규칙", { x: rx, y: y3, w: CR - rx, h: 0.35, size: 14, color: C.navy, bold: true, margin: 0 });
  [["계층형 (기본값)", "1명 위임 → 검수·통합"], ["파이프라인형", "앞 산출물 → 다음 입력"],
    ["토론형", "병렬 의견 → 교차검증"], ["협업형", "라운드마다 클로니 중개"]]
    .forEach(([hd, bd], i) => card2(s, { x: CX + (i % 2) * (pw + 0.15), y: cy + Math.floor(i / 2) * (ch + 0.08), w: pw,
      h: ch, fill: C.tint, head: hd, body: bd, margin: 4 }));
  [["대화 가이드", "존대 · q: 질문 · o: 최적안"], ["Git 연동", "pull · push · 한글 커밋"],
    ["문서·프롬프트", "명사체 · 8섹션 표준"], ["파이썬 개발", "DIP 계층 · 주석 가이드"],
    ["멀티 도구 호환", ".agents 원본 → 생성"], ["도구 사용", "URL curl · 플러그인 명령"]]
    .forEach(([hd, bd], i) => card2(s, { x: rx + (i % 3) * (rw + 0.1), y: cy + Math.floor(i / 3) * (ch + 0.08), w: rw,
      h: ch, head: hd, body: bd, margin: 4 }));

  // ④ CHECK — 품질 장치 3개(왼쪽 파란 막대로 강조)
  const y4 = 7.06, h4 = 0.85, kw = (CWC - 0.2) / 3;
  layerLabel(s, { y: y4, h: h4, key: "CHECK", sub: "품질 장치", fill: C.navy });
  [["정직한 보고", "증거(로그·응답·화면) 없으면 완료 아님"], ["Lessons Learned", "시행착오 기록 → 검증된 교훈만 승격"],
    ["Advisor 자문", "작업 전 · 중(최대 3회) · 후 호출"]]
    .forEach(([hd, bd], i) => {
      const x = CX + i * (kw + 0.1);
      card2(s, { x, y: y4, w: kw, h: h4, fill: C.tint, align: "left", margin: 7, textDx: 0.18, head: hd, body: bd,
        headSize: 16 });
      L.box(s, { x, y: y4 + 0.12, w: 0.07, h: h4 - 0.24, fill: C.blue, line: null });
    });
}

async function main() {
  const out = process.argv[2] || path.join(__dirname, "AGENTS구성.pptx");
  const pptx = L.createDeck();
  await createSlide01();
  await pptx.writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
