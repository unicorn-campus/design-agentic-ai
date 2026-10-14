// node build.js — ④ 엔티티·관계 추출 상세(LangChain LLMGraphTransformer) 한 장 빌드 (script.md 슬라이드 1)
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, fs } = L;

const Y = { flow: 1.9, flowH: 1.72, ex: 3.84, exH: 2.46, tip: 6.5, tipH: 1.45 };

// 누가 하나 표시 — 앞 장표 「그래프DB 인덱싱 과정」과 같은 색 규칙
const WHO = {
  "코드": { fill: C.white, line: C.pill, color: C.slate },
  "LLM": { fill: C.blue, line: null, color: C.white },
};

const FLOW = [
  { tag: "입력", title: "청크 1개", desc: "Document\n(청크 글 + 메타데이터)", io: true },
  { tag: "4-1", who: "코드", title: "프롬프트 조립", desc: "기본 지시문\n+ 허용 목록\n+ 추가 지시" },
  { tag: "4-2", who: "LLM", title: "LLM 호출", desc: "청크당 1번 호출\n도구 호출로 정해진 틀에 답\n미지원 모델은 JSON 복구" },
  { tag: "4-3", who: "코드", title: "이름 정리", desc: "관계 → LAUNCHED 꼴\n종류 → Company 꼴\n영문 iPhone → Iphone" },
  { tag: "4-4", who: "코드", title: "허용 목록 필터", desc: "strict_mode=True(기본)\n목록 밖 종류·관계는\n말없이 버림" },
  { tag: "출력", title: "GraphDocument", desc: "노드 · 관계 · 원본 청크\n→ 다음: 같은 이름 병합", io: true },
];

const TIPS = [
  { title: "목록은 안내, 강제는 필터", body: "허용 목록은 프롬프트로 알려 줄 뿐\n(답을 강제하는 건 OpenAI 모델만)\n→ 뒤에서 strict_mode가 거름" },
  { title: "속성은 도구 호출 모델만", body: "node_properties ·\nrelationship_properties는\n도구 호출 못 하는 모델에서 오류" },
  { title: "청크 수 = LLM 호출 수", body: "aconvert_to_graph_documents로\n동시 호출 가능\n호출 한도(속도 제한) 주의" },
  { title: "청크끼리는 못 합침", body: "한 청크 안의 '이 카드'만 맞춰 줌\n→ 청크 사이 같은 대상은\n다음 단계 병합에서" },
];

function flowBox(s, { x, w }, st) {
  const y = Y.flow, h = Y.flowH;
  L.rr(s, { x, y, w, h, fill: st.io ? C.white : C.tint, line: st.io ? C.navy : C.blue, lw: 1.5, r: 0.08 });
  if (st.io) L.darkBadge(s, st.tag, { x: x + 0.1, y: y + 0.1, w: 0.62, h: 0.34, size: 14, fill: C.navy });
  else {
    // 정사각 번호 배지는 '4-1'이 들어가기 좁아 폭을 늘린 배지를 씀
    L.card(s, st.tag, { x: x + 0.1, y: y + 0.1, w: 0.62, h: 0.34, fill: C.blue, line: null, color: C.white, size: 14,
      bold: true, r: 0.05 });
    const ws = WHO[st.who];
    L.card(s, st.who, { x: x + w - 0.82, y: y + 0.1, w: 0.72, h: 0.34, ...ws, size: 14, bold: true, r: 0.17 });
  }
  L.text(s, st.title, { x, y: y + 0.5, w, h: 0.4, size: 17, bold: true, color: C.navy, align: "center" });
  L.text(s, st.desc, { x: x + 0.04, y: y + 0.9, w: w - 0.08, h: h - 0.96, size: 14, color: C.ink, align: "center",
    valign: "top", margin: 0.02 });
}

// 예시 칸 머리: 다크 배지
function exPanel(s, { x, w, label, bw }) {
  L.rr(s, { x, y: Y.ex, w, h: Y.exH, fill: C.white, line: C.border, r: 0.08 });
  L.darkBadge(s, label, { x: x + 0.12, y: Y.ex + 0.12, w: bw, h: 0.36,
    size: 15 });
}

// 그래프 노드: 이름(굵게) + 종류(옅게). 버려진 노드는 회색 점선
function gNode(s, { x, y, w = 1.2, h = 0.62, name, type, dropped = false }) {
  L.rr(s, { x, y, w, h, fill: dropped ? C.white : C.tint, line: dropped ? C.sub : C.navy, lw: 1.5, r: 0.12,
    dash: dropped ? "dash" : undefined });
  s.addText([
    { text: name, options: { fontSize: fs(15), bold: true, color: dropped ? C.sub : C.navy, breakLine: true } },
    { text: type, options: { fontSize: fs(14), color: dropped ? C.sub : C.slate } },
  ], { x, y, w, h, fontFace: FONT, align: "center", valign: "middle", margin: 0.02, isTextBox: true, paraSpaceAfter: 0 });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "④ 엔티티·관계 추출 상세: LangChain LLMGraphTransformer",
    lead: "청크 하나마다 LLM을 한 번 불러 노드·관계를 뽑고, 허용 목록 밖은 걸러 GraphDocument로 넘김",
    notes: "LLMGraphTransformer는 청크(Document) 하나를 받아 LLM을 한 번 부르고, 노드·관계 묶음(GraphDocument)을 돌려줌. "
      + "4-1: 기본 지시문에 '사람은 person처럼 기본 종류로', '관계는 일반적인 이름으로', '같은 대상은 가장 완전한 이름 하나로'가 "
      + "들어 있음. 허용 목록과 additional_instructions가 여기에 붙음. "
      + "4-2: 모델이 도구 호출(구조화 출력)을 지원하면 정해진 틀로 답을 받음. 지원하지 않거나 ignore_tool_usage=True면 JSON 글을 "
      + "받아 json_repair로 고쳐 읽음. 이 경우 속성 추출은 못 씀. "
      + "4-3: 이름을 .title()로 바꿔 영문은 단어 첫 글자만 대문자가 됨(iPhone → Iphone). 한글은 그대로. 관계는 LAUNCHED처럼 "
      + "대문자 + 밑줄. "
      + "4-4: strict_mode가 기본으로 켜져 있어 허용 목록 밖 결과를 버림. 몇 개를 버렸는지 알려 주지 않으므로 처음엔 "
      + "strict_mode=False로 한 번 돌려 무엇이 버려지는지 보는 것을 권장. "
      + "다음 단계 예고: add_graph_documents가 이름(id)으로 MERGE해 이름이 완전히 같은 노드는 합쳐짐. baseEntityLabel=True면 "
      + "종류가 달라도 이름만 같으면 한 노드가 됨. 'A사'와 'A사(주)'처럼 조금 다른 이름은 따로 처리해야 함.",
  });

  // ① 흐름 6칸
  const fg = 0.3, fw = (CW - fg * 5) / 6;
  FLOW.forEach((st, i) => {
    const x = X0 + i * (fw + fg);
    flowBox(s, { x, w: fw }, st);
    if (i < FLOW.length - 1) {
      L.arrow(s, { x1: x + fw + 0.03, y1: Y.flow + Y.flowH / 2, x2: x + fw + fg - 0.03, y2: Y.flow + Y.flowH / 2,
        color: C.slate, width: 1.75 });
    }
  });

  // ② 예시 3칸: 입력 청크 → 설정 → 결과 그래프
  const eg = 0.25, w1 = 3.5, w2 = 4.9, w3 = CW - w1 - w2 - eg * 2;
  const x1 = X0, x2 = x1 + w1 + eg, x3 = x2 + w2 + eg;
  const midY = Y.ex + Y.exH / 2;

  exPanel(s, { x: x1, w: w1, label: "예시 입력 청크", bw: 1.9 });
  L.text(s, "A사는 2025년 B카드를 출시했다.\n이 카드는 C은행과 제휴했다.", { x: x1 + 0.15, y: Y.ex + 0.6, w: w1 - 0.3,
    h: 1.0, size: 17, color: C.ink, valign: "top" });
  L.text(s, "(가명처리를 거친 글)", { x: x1 + 0.15, y: Y.ex + Y.exH - 0.46, w: w1 - 0.3, h: 0.34, size: 14,
    color: C.sub });

  exPanel(s, { x: x2, w: w2, label: "설정", bw: 0.8 });
  s.addText([
    "t = LLMGraphTransformer(llm=llm,",
    "  allowed_nodes=[\"Company\", \"Product\"],",
    "  allowed_relationships=[",
    "    (\"Company\", \"LAUNCHED\", \"Product\"),",
    "    (\"Product\", \"PARTNERED_WITH\", \"Company\")])",
    "docs = t.convert_to_graph_documents(chunks)",
  ].join("\n"), { x: x2 + 0.15, y: Y.ex + 0.56, w: w2 - 0.3, h: Y.exH - 0.64, fontFace: FONT, fontSize: fs(14),
    color: C.ink, valign: "top", margin: 0.02, isTextBox: true, paraSpaceAfter: 0, lineSpacingMultiple: 1.0 });

  exPanel(s, { x: x3, w: w3, label: "결과 GraphDocument", bw: 2.4 });
  const nW = 1.2, nY = Y.ex + 0.9, nH = 0.62, cy = nY + nH / 2;
  const ax = x3 + 0.15, bx = x3 + (w3 - nW) / 2, cx = x3 + w3 - 0.15 - nW;
  gNode(s, { x: ax, y: nY, name: "A사", type: "Company" });
  gNode(s, { x: bx, y: nY, name: "B카드", type: "Product" });
  gNode(s, { x: cx, y: nY, name: "C은행", type: "Company" });
  L.arrow(s, { x1: ax + nW + 0.03, y1: cy, x2: bx - 0.03, y2: cy, color: C.navy, width: 2 });
  L.arrow(s, { x1: bx + nW + 0.03, y1: cy, x2: cx - 0.03, y2: cy, color: C.navy, width: 2 });
  const lab = (t, xa, xb) => L.text(s, t, { x: (xa + xb) / 2 - 1.0, y: nY - 0.34, w: 2.0, h: 0.3, size: 14, bold: true,
    color: C.blue, align: "center", margin: 0 });
  lab("LAUNCHED", ax + nW, bx);
  lab("PARTNERED_WITH", bx + nW, cx);
  // 버려진 노드 — 허용 목록 밖(Year)
  const dY = nY + nH + 0.2, dH = 0.55;
  gNode(s, { x: ax, y: dY, h: dH, name: "2025", type: "Year", dropped: true });
  L.arrow(s, { x1: ax + 0.2, y1: nY + nH + 0.02, x2: ax + 0.2, y2: dY - 0.02, color: C.sub, width: 1.5, dash: "dash" });
  L.text(s, "✕ RELEASED_IN\nYear는 목록 밖 → 버림", { x: ax + nW + 0.1, y: dY - 0.05, w: 2.3, h: dH + 0.1,
    size: 14, color: C.sub, margin: 0 });
  L.text(s, "'이 카드' →\nB카드로 맞춤", { x: cx - 0.45, y: dY - 0.05, w: nW + 0.45, h: dH + 0.1, size: 14, color: C.blue,
    bold: true, align: "right", margin: 0 });

  [[x1 + w1, x2], [x2 + w2, x3]].forEach(([xa, xb]) => L.arrow(s, { x1: xa + 0.02, y1: midY, x2: xb - 0.02, y2: midY,
    color: C.slate, width: 1.75 }));

  // ③ 실무 포인트 4개
  const tg = 0.15, tw = (CW - tg * 3) / 4;
  TIPS.forEach((t, i) => {
    const x = X0 + i * (tw + tg);
    L.rr(s, { x, y: Y.tip, w: tw, h: Y.tipH, fill: C.altRow, line: C.border, r: 0.08 });
    L.numBadge(s, i + 1, { x: x + 0.12, y: Y.tip + 0.12, size: 0.38, fsz: 16, fill: C.navy });
    L.text(s, t.title, { x: x + 0.58, y: Y.tip + 0.1, w: tw - 0.66, h: 0.42, size: 16, bold: true, color: C.navy,
      margin: 0 });
    L.text(s, t.body, { x: x + 0.15, y: Y.tip + 0.58, w: tw - 0.25, h: Y.tipH - 0.66, size: 14, color: C.ink,
      valign: "top", margin: 0 });
  });
  return s;
}

async function main() {
  L.createDeck();
  await createSlide01();
  const out = process.argv[2] || path.join(__dirname, "엔티티관계추출상세.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
