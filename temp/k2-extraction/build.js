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
    lead: "추출 단위 하나와 그 문서 유형의 그래프 스키마를 LLM에 넣어, 스키마 모양대로 노드와 관계를 JSON으로 받음",
    notes: "K2는 추출 단위 하나를 LLM에 넣어 노드와 관계를 받는 단계입니다. LLM에는 네 가지가 들어갑니다. 그 문서 유형의 "
      + "graph_schema.json, 메타데이터 머리줄, 추출 단위 본문, 그리고 라이브러리의 기본 추출 지시입니다. 머리줄은 상담 번호나 "
      + "날짜처럼 본문에 잘 드러나지 않는 키 속성을 채우려고 붙입니다.\n예시 상담에서 LLM은 상담사가 권한 두 방법을 제안 "
      + "노드로, 고객이 말한 다시 문의할 조건을 재검토 조건 노드로 뽑고, 본문에 적힌 앞 상담 번호로 이전 상담과 이었습니다. "
      + "다만 같은 원문을 한 번 더 넣었더니 재검토 조건이 제안의 이유 속성으로 들어갔습니다. LLM은 부를 때마다 결과가 조금씩 "
      + "다릅니다. 그래서 본문과 스키마가 그대로인 단위는 다시 묻지 않고 앞 결과를 씁니다.\n노드 ID 앞에 붙는 단위 ID는 "
      + "단위끼리 ID가 겹치지 않게 하는 임시 표시입니다. 검색용 청크와 잇는 일은 K4에서 추출 단위 노드와 FROM_CHUNK 관계가 "
      + "맡습니다.",
  });

  // 왼쪽: LLM에 넣는 것
  const IW = 4.55;
  L.darkBadge(s, "LLM에 넣는 것", { x: X0, y: 1.9, w: IW, h: 0.4, size: 16 });
  const inputs = [
    ["① 문서 유형별 graph_schema.json", "상담 기록: 노드 4, 관계 4와 해당, 비해당 설명"],
    ["② 머리줄 (메타데이터 5칸)", "record_id, 상담일, 채널, 주제, 가명 회원 키"],
    ["③ 추출 단위 본문 (K1 결과)", "상담은 검색용 청크 1개가 곧 단위 1개"],
    ["④ 추출 지시 (라이브러리 기본)", "JSON으로, 주어진 타입만, 관계 방향 지킴"],
  ];
  inputs.forEach((lines, i) => {
    richCard(s, lines, { x: X0, y: 2.4 + i * 0.72, w: IW, h: 0.64, fill: i === 0 ? C.tint : C.altRow,
      line: i === 0 ? C.blue : C.border, color: i === 0 ? C.navy : C.ink, align: "left" });
  });

  // 가운데: LLM
  const MX = X0 + IW + 0.35, MW = 1.75;
  richCard(s, ["LLM", "gpt-oss-120b", "(Groq)", "단위 하나에 1번", "동시 4건"], { x: MX, y: 2.6, w: MW, h: 2.3, fill: C.navy,
    line: null, color: C.white, titleSize: 20 });
  L.arrow(s, { x1: X0 + IW + 0.04, y1: 3.75, x2: MX - 0.04, y2: 3.75, color: C.navy, width: 2.5 });

  // 오른쪽: 나온 그래프(실제 결과)
  const GX = MX + MW + 0.35, GW = XR - GX;
  L.arrow(s, { x1: MX + MW + 0.04, y1: 3.75, x2: GX - 0.04, y2: 3.75, color: C.navy, width: 2.5 });
  L.headerBar(s, "나온 그래프 (v0 표본 실행, 상담 C-20260501-003)", { x: GX, y: 1.9, w: GW, h: 0.4, size: 16, accent: true });
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
    ["같은 본문은 다시 묻지 않음", "본문 해시와 스키마 지문이 같으면 앞 결과를 씀"],
    ["형식 오류는 다시", "같은 입력으로 2번까지 다시 물음"],
    ["실패는 기록하고 계속", "failed_units에 남기고 나머지 단위는 진행"],
    ["노드 ID 앞 단위 ID는 임시", "단위끼리 ID가 겹치지 않게 함. K4 적재 중에만 씀"],
  ];
  const RG = 0.2, RCW = (CW - 3 * RG) / 4, RY = 5.4;
  rules.forEach(([t, b], i) => {
    const x = X0 + i * (RCW + RG);
    L.rr(s, { x, y: RY, w: RCW, h: 1.2, fill: C.altRow, line: C.border });
    L.numBadge(s, i + 1, { x: x + 0.12, y: RY + 0.12, size: 0.36, fill: C.blue, fsz: 15 });
    L.text(s, t, { x: x + 0.55, y: RY + 0.08, w: RCW - 0.65, h: 0.44, size: 15, color: C.navy, bold: true });
    L.text(s, b, { x: x + 0.15, y: RY + 0.54, w: RCW - 0.3, h: 0.6, size: 14, color: C.body, valign: "top" });
  });

  // 맨 아래: v0 표본 실행 결과
  richCard(s, ["v0 표본: 전체 재색인 단위 24개, LLM 24번, 실패 0, 토큰 76,401 / 증분 색인 LLM 1번, 3개 재사용",
    "결과는 K3까지 마친 뒤 kg_prepared.json에 보관만 함. Neo4j에는 K4 반영 때 씀"], { x: X0, y: 6.75, w: CW, h: 0.95,
    fill: C.navy, line: null, color: C.white, size: 15, titleSize: 16 });
}

// kg_build.py 원문 발췌 — 줄 나눔만 장표 폭에 맞게 바꾸고, 생략은 …, 끝의 # 주석 일부는 장표용
const CODE_EXTRACT = String.raw`# prepare() 안: 추출기와 가지치기는 한 번만 만듦
llm = make_llm()                                  # Groq openai/gpt-oss-120b
extractor = LLMEntityRelationExtractor(llm=llm,
    create_lexical_graph=False, on_error=OnError.RAISE)
pruner, sem = GraphPruning(), asyncio.Semaphore(config.LLM_CONCURRENCY)

async def _k2_k3_one(sem, extractor, pruner, unit, spec):
    async with sem:                               # 동시 4건
        text = _head_line(unit["metadata"], spec["header"]) + unit["text"]
        for attempt in range(config.LLM_RETRIES + 1):    # 2번까지 다시
            try:
                graph = await extractor.run(chunks=TextChunks(chunks=[
                    TextChunk(text=text, index=0, uid=unit["unit_id"])]),
                    schema=spec["schema"])
                break
            except Exception as e:
                if attempt == config.LLM_RETRIES:   # 실패는 기록용으로 돌려줌
                    return {"error": f"{type(e).__name__}: {str(e)[:200]}"}
        pruned = (await pruner.run(graph, spec["schema"])).graph   # K3
        return {"graph": pruned.model_dump(), …}`.split("\n");

const CODE_SAVED = String.raw`{"unit_id": "D3_C-20260501-003_c797…_0000",
 "text_hash": "…", "schema_signature": "…",
 "graph": {"nodes": [ …,
   {"id": "D3_C-20260501-003_c797…_0000:p1",
    "label": "Proposal",
    "properties": {"content": "그러면 주문 내역 화면으로 …",
                   "decision": "수용"}}, … ],
  "relationships": [ …,
   {"type": "RECONSIDER_WHEN",
    "start_node_id": "…_0000:p1", "end_node_id": "…_0000:r0"}]}}`.split("\n");

const CODE_REUSE = String.raw`hit = cache.get((u["doc_type"], u["text_hash"], u["schema_signature"]))
if hit:
    u.update(graph=hit["graph"], reused=True)   # LLM을 부르지 않음
else:
    todo.append(u)`.split("\n");

async function createSlide02() {
  const s = L.newSlide({
    title: "K2 추출 코드 (kg_build.py)",
    lead: "추출기는 한 번 만들고, 단위마다 머리줄을 붙여 부르며, K3 가지치기까지 마친 결과를 파일로 보관함",
    notes: "추출기는 한 번만 만듭니다. 검색용 청크 노드는 만들지 않고, 오류가 나면 예외로 올리게 설정합니다. 단위마다 "
      + "머리줄을 붙인 글을 TextChunk 하나로 감싸 넣는데, uid에 단위 ID를 줍니다. 그래서 돌려받은 노드 ID 앞에 단위 ID가 "
      + "붙습니다.\n형식 오류는 같은 입력으로 두 번까지 다시 묻고, 그래도 안 되면 오류를 돌려줘 실패 목록에 남깁니다. 받은 "
      + "그래프는 같은 함수에서 바로 가지치기를 하고, 결과를 kg_prepared.json에 보관합니다. 다음 실행에서는 본문 해시와 "
      + "스키마 지문이 같으면 이 보관 결과를 그대로 씁니다.",
  });

  const LW = 8.05, RX = X0 + LW + 0.3, RW = XR - RX;
  L.codeBox(s, CODE_EXTRACT, { x: X0, y: 1.9, w: LW, h: 6.05, size: 14,
    title: "추출기 만들기와 _k2_k3_one (kg_build.py 발췌)" });
  L.codeBox(s, CODE_SAVED, { x: RX, y: 1.9, w: RW, h: 3.15, size: 14, title: "kg_prepared.json에 보관한 결과 (일부)" });
  L.codeBox(s, CODE_REUSE, { x: RX, y: 5.15, w: RW, h: 1.85, size: 14, title: "앞 세대 결과 재사용 (prepare 발췌)" });
  richCard(s, ["응답 다듬기 (GroqLLM._clean)", "정해진 칸 밖 키 제거, id는 글자로, 빈 속성 제거"], { x: RX, y: 7.1, w: RW,
    h: 0.85, fill: C.altRow, line: C.border, color: C.ink });
}

async function main() {
  L.createDeck();
  for (const fn of [createSlide01, createSlide02]) await fn();
  await L.getPptx().writeFile({ fileName: OUT });
  console.log("✅ PPT 생성 완료:", OUT);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
