// KG 구축 K2 엔티티와 관계 추출 장표 2장 — script.md 기준, references/pptx-guide.md 6절 규칙 적용
const path = require("path");
const L = require("./lib");
const { C, FONT, X0, CW, XR, fs } = L;

const OUT = process.env.OUT || path.join(__dirname, "K2추출.pptx");

// 제목 줄(굵게)과 설명 줄을 한 박스에 담는 라벨 박스
function richCard(s, lines, { x, y, w, h, fill = C.white, line = C.border, color = C.ink, size = 14,
  titleSize = 15, align = "center", r = 0.08 }) {
  L.rr(s, { x, y, w, h, fill, line, r });
  const runs = lines.map((t, i) => ({
    text: t,
    options: { bold: i === 0, fontSize: fs(i === 0 ? titleSize : size), color, breakLine: i < lines.length - 1 },
  }));
  // 왼쪽 정렬일 때는 글자가 테두리에 붙지 않게 안쪽 여백을 넓힘
  s.addText(runs, { x, y, w, h, fontFace: FONT, align, valign: "middle", margin: align === "left" ? [10, 10, 3, 3] : 0.05, isTextBox: true,
    paraSpaceAfter: 1 });
}

async function createSlide01() {
  const s = L.newSlide({
    title: "KG 구축 K2 엔티티와 관계 추출",
    lead: "추출 단위 하나와 승인된 그래프 스키마를 LLM에 넣어, 스키마 모양대로 노드와 관계를 JSON으로 받음",
    notes: "K2는 추출 단위 하나를 LLM에 넣어 노드와 관계를 받는 단계입니다. LLM에는 네 가지가 들어갑니다. 승인된 그래프 "
      + "스키마, 메타데이터 머리줄, 추출 단위 본문, 그리고 라이브러리의 기본 추출 지시입니다. 스키마의 설명에는 해당하는 것과 "
      + "해당하지 않는 것을 함께 적어서 LLM이 경계를 판단하게 합니다. 머리줄은 상담 번호나 날짜처럼 본문에 잘 드러나지 않는 키 "
      + "속성을 채우려고 붙입니다.\n예시 상담에서 LLM은 상담사가 권한 두 가지 방법을 제안 노드로, 고객이 말한 다시 문의할 "
      + "조건을 재검토 조건 노드로 뽑고, 본문에 적힌 앞 상담 번호로 이전 상담과 이었습니다. 응답 형식이 깨지면 같은 입력으로 "
      + "두 번까지 다시 묻고, 그래도 안 되면 그 단위만 실패로 기록하고 나머지를 계속합니다. 노드 ID 앞에는 단위 ID가 붙어서 "
      + "K4에서 검색용 청크와 이을 수 있습니다.",
  });

  // 왼쪽: LLM에 넣는 것
  const IW = 4.55;
  L.darkBadge(s, "LLM에 넣는 것", { x: X0, y: 1.9, w: IW, h: 0.4, size: 16 });
  const inputs = [
    ["① 승인된 그래프 스키마", "노드 4, 관계 4, 패턴 4 + 해당과 비해당 설명"],
    ["② 머리줄 (메타데이터)", "record_id, 상담일, 채널, 주제, 가명 회원 키"],
    ["③ 추출 단위 본문", "상담 1건 698자 (연락처는 이미 [삭제])"],
    ["④ 추출 지시 (라이브러리 기본)", "JSON으로, 주어진 타입만, 관계 방향 지킴"],
  ];
  inputs.forEach((lines, i) => {
    richCard(s, lines, { x: X0, y: 2.4 + i * 0.72, w: IW, h: 0.64, fill: i === 0 ? C.tint : C.altRow,
      line: i === 0 ? C.blue : C.border, color: i === 0 ? C.navy : C.ink, align: "left" });
  });

  // 가운데: LLM
  const MX = X0 + IW + 0.35, MW = 1.75;
  richCard(s, ["LLM", "gpt-oss-120b", "(Groq)", "단위 하나에 1번"], { x: MX, y: 2.75, w: MW, h: 2.0, fill: C.navy,
    line: null, color: C.white, titleSize: 20 });
  L.arrow(s, { x1: X0 + IW + 0.04, y1: 3.75, x2: MX - 0.04, y2: 3.75, color: C.navy, width: 2.5 });

  // 오른쪽: 나온 그래프(실제 결과)
  const GX = MX + MW + 0.35, GW = XR - GX;
  L.arrow(s, { x1: MX + MW + 0.04, y1: 3.75, x2: GX - 0.04, y2: 3.75, color: C.navy, width: 2.5 });
  L.headerBar(s, "나온 그래프 (상담 C-20260501-003 실제 결과)", { x: GX, y: 1.9, w: GW, h: 0.4, size: 16, accent: true });
  const NW1 = 2.55, RW = 2.05, NW2 = GW - NW1 - RW - 0.3;
  const triples = [
    [["Consultation", "C-20260501-003, 콜센터"], "HAS_PROPOSAL", ["Proposal", "종이 영수증 대조 (거절)"]],
    [["Consultation", "C-20260501-003"], "HAS_PROPOSAL", ["Proposal", "주문 내역 화면 대조 (수용)"]],
    [["Proposal", "주문 내역 화면 대조"], "RECONSIDER_WHEN", ["ReconsiderCondition", "다음 명세서 나올 때 다시 문의"]],
    [["Consultation", "C-20260501-003"], "FOLLOWS", ["Consultation", "C-20260302-002 (앞 상담)"]],
  ];
  triples.forEach(([a, rel, b], i) => {
    const y = 2.4 + i * 0.72, h = 0.64;
    richCard(s, a, { x: GX, y, w: NW1, h, fill: C.white, line: C.border, color: C.ink, titleSize: 14 });
    L.arrow(s, { x1: GX + NW1 + 0.03, y1: y + h / 2, x2: GX + NW1 + 0.12, y2: y + h / 2 });
    L.card(s, rel, { x: GX + NW1 + 0.15, y: y + 0.12, w: RW, h: 0.4, fill: C.tint, line: C.pill, color: C.navy,
      size: 14, bold: true, r: 0.2 });
    L.arrow(s, { x1: GX + NW1 + 0.15 + RW + 0.02, y1: y + h / 2, x2: GX + NW1 + RW + 0.27, y2: y + h / 2 });
    richCard(s, b, { x: GX + NW1 + RW + 0.3, y, w: NW2, h, fill: C.tint, line: C.blue, color: C.navy, titleSize: 14 });
  });

  // 아래: 규칙 카드 4개
  const rules = [
    ["형식 오류는 다시", "같은 입력으로 2번까지 다시 물음"],
    ["한 건 실패는 기록하고 계속", "나머지 단위는 그대로 진행 (동시 4건)"],
    ["노드 ID에 단위 ID가 붙음", "K4에서 검색용 청크와 이을 때 씀"],
    ["스키마 밖은 K3에서 지움", "정해진 타입이 아닌 노드와 관계는 가지치기"],
  ];
  const RG = 0.2, RCW = (CW - 3 * RG) / 4, RY = 5.4;
  rules.forEach(([t, b], i) => {
    const x = X0 + i * (RCW + RG);
    L.rr(s, { x, y: RY, w: RCW, h: 1.05, fill: C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.12, y: RY + 0.12, size: 0.36, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: x + 0.55, y: RY + 0.08, w: RCW - 0.65, h: 0.44, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.15, y: RY + 0.54, w: RCW - 0.3, h: 0.46, size: 14, color: C.body });
  });

  // 맨 아래: 시험 결과
  richCard(s, ["상담 기록 시험 18건: 실패 0, 재시도 0, 건당 평균 4.8초, 역량 질문 5개 모두 통과",
    "약관은 조항 단위로 나눠도 아직 합격 기준 미달"], { x: X0, y: 6.62, w: CW, h: 0.9, fill: C.navy, line: null,
    color: C.white, size: 15, titleSize: 16 });
}

const CODE_EXTRACT = String.raw`llm = make_llm(graph_safe=True)                # Groq openai/gpt-oss-120b
extractor = LLMEntityRelationExtractor(
    llm=llm, create_lexical_graph=False, on_error=OnError.RAISE)
schema = GraphSchema.model_validate(graph_schema)  # 승인된 스키마

def head_line(md, fields):                      # 단위 본문 앞에 붙이는 머리줄
    return " | ".join(f"{f}: {md[f]}" for f in fields
                      if md.get(f) not in (None, "")) + "\n"

async def extract_one(sem, unit_id, text):
    async with sem:                             # 동시 4건
        for attempt in range(3):                # 형식 오류는 2번까지 다시
            try:
                graph = await extractor.run(
                    chunks=TextChunks(chunks=[
                        TextChunk(text=text, index=0, uid=unit_id)]),
                    schema=schema)
                break
            except Exception:
                if attempt == 2:
                    raise
        return graph                            # 다음: K3 가지치기`.split("\n");

const CODE_JSON = String.raw`{"nodes": [
  {"id": "0", "label": "Consultation",
   "properties": {"record_id": "C-20260501-003",
                  "channel": "콜센터", …}},
  {"id": "3", "label": "Proposal",
   "properties": {"content": "그러면 주문 내역 화면으로 …",
                  "decision": "수용"}},
  {"id": "4", "label": "ReconsiderCondition",
   "properties": {"condition": "다음 명세서 나올 때 …"}}],
 "relationships": [
  {"type": "HAS_PROPOSAL",
   "start_node_id": "0", "end_node_id": "3"},
  {"type": "RECONSIDER_WHEN",
   "start_node_id": "3", "end_node_id": "4"}]}`.split("\n");

async function createSlide02() {
  const s = L.newSlide({
    title: "K2 엔티티와 관계 추출 코드",
    lead: "추출기 하나를 만들고, 단위마다 머리줄을 붙여 호출하며, 형식 오류는 다시 시도함",
    notes: "추출기는 한 번만 만듭니다. LLM, 그리고 검색용 청크 노드는 만들지 않는다는 설정, 오류가 나면 예외로 올린다는 설정을 "
      + "줍니다. 단위마다 머리줄을 붙인 글을 TextChunk 하나로 감싸 넣는데, 이때 uid에 단위 ID를 줍니다. 그래서 돌려받은 노드 "
      + "ID 앞에 단위 ID가 붙습니다. 형식 오류는 같은 입력으로 두 번까지 다시 묻고, 받은 그래프는 다음 단계인 가지치기로 "
      + "넘깁니다.",
  });

  const LW = 8.05, RX = X0 + LW + 0.3, RW = XR - RX;
  L.codeBox(s, CODE_EXTRACT, { x: X0, y: 1.9, w: LW, h: 6.05, size: 14,
    title: "추출기 만들기와 extract_one (fill_test.py 발췌)" });
  L.codeBox(s, CODE_JSON, { x: RX, y: 1.9, w: RW, h: 4.2, size: 14, title: "LLM이 돌려준 JSON (다듬은 뒤, 일부)" });
  richCard(s, ["응답 다듬기 (GraphSafeLLM)", "정해진 칸 밖 키 제거, id는 글자로, 빈 속성 제거"], { x: RX, y: 6.2, w: RW,
    h: 0.8, fill: C.altRow, line: C.border, color: C.ink });
  richCard(s, ["노드 ID 앞에 단위 ID가 붙음", "\"3\" → D3_C-20260501-003_…_0000:3"], { x: RX, y: 7.1, w: RW, h: 0.85,
    fill: C.blue, line: null, color: C.white });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlide01, createSlide02]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
