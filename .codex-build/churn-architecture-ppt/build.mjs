import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/Users/hiond/class/design-agentic-ai";
const SKILL_DIR = "C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const TMP_DIR = path.join(workspaceDir, ".codex-build/churn-architecture-ppt");
const FINAL_PPTX = path.join(
  workspaceDir,
  "output/pptx/이탈위험-대응-상담-시스템-논리아키텍처-v2.pptx",
);
const RUNTIME_PYTHON =
  "C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";

const C = {
  navy: "#1E2A5C",
  blue: "#2E74C6",
  ink: "#2B3242",
  slate: "#4A5364",
  sub: "#7C8598",
  white: "#FFFFFF",
  tint: "#EEF3FA",
  altRow: "#F5F8FC",
  tableHead: "#E2EEF9",
  dark: "#404155",
  border: "#D9E0EC",
  line: "#EDF0F6",
};

const FONT = "Noto Sans KR";
const MIN_FONT_PT = 14;
const fsPt = (pt) => {
  if (pt < MIN_FONT_PT) throw new Error(`fontSize ${pt}pt < ${MIN_FONT_PT}pt`);
  return (pt * 96) / 72;
};

function addText(slide, text, position, fontSizePt, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: fsPt(fontSizePt),
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "middle",
    autoFit: "none",
    wrap: "square",
    insets: options.insets ?? { top: 2, right: 4, bottom: 2, left: 4 },
  };
  return shape;
}

function addBoundary(slide, { x, y, w, h, title, fill, stroke }) {
  const boundary = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "dashed", fill: stroke, width: 2 },
    borderRadius: 10,
  });
  boundary.sendToBack();
  addText(
    slide,
    title,
    { left: x + 12, top: y + 6, width: w - 24, height: 36 },
    15,
    { bold: true, color: stroke },
  );
  return boundary;
}

function addNode(slide, { x, y, w, h, text, fill = C.white, stroke = C.blue, color = C.navy, size = 16 }) {
  const node = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: stroke, width: 1.6 },
    borderRadius: 8,
    shadow: "shadow-sm",
  });
  node.text = text;
  node.text.style = {
    typeface: FONT,
    fontSize: fsPt(size),
    bold: true,
    color,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: { top: 5, right: 7, bottom: 5, left: 7 },
  };
  return node;
}

function addEdgeLabel(slide, { x, y, w, h, title, detail, accent = C.blue }) {
  const label = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill: C.white,
    line: { style: "solid", fill: C.border, width: 1 },
    borderRadius: 6,
  });
  label.text = [
    [
      { run: title, textStyle: { bold: true, color: accent, fontSize: "14pt", typeface: FONT } },
      { run: `\n${detail}`, textStyle: { color: C.slate, fontSize: "14pt", typeface: FONT } },
    ],
  ];
  label.text.style = {
    typeface: FONT,
    fontSize: fsPt(14),
    color: C.slate,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: { top: 3, right: 5, bottom: 3, left: 5 },
  };
  return label;
}

function connect(slide, source, target, { fromSide, toSide, bidirectional = false, color = C.sub }) {
  return slide.shapes.connect(source, target, {
    kind: "straight",
    fromSide,
    toSide,
    line: { style: "solid", fill: color, width: 1.5 },
    head: { type: "triangle", width: "sm", length: "sm" },
    ...(bidirectional ? { tail: { type: "triangle", width: "sm", length: "sm" } } : {}),
  });
}

async function createSlide01(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = C.white;

  addText(slide, "② 논리 아키텍처 › 전체관계도", { left: 40, top: 20, width: 700, height: 24 }, 14, {
    bold: true,
    color: C.sub,
  });
  addText(slide, "이탈위험 대응 상담 시스템 논리 아키텍처", { left: 40, top: 43, width: 1180, height: 52 }, 32, {
    bold: true,
    color: C.navy,
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 40, top: 100, width: 1200, height: 3 },
    fill: C.border,
    line: { fill: "none", width: 0 },
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 40, top: 100, width: 170, height: 3 },
    fill: C.blue,
    line: { fill: "none", width: 0 },
  });
  addText(
    slide,
    "사용자·사내 연계 시스템·외부 AI 사업자의 통제 경계를 분리하고, 경계마다 전달 데이터와 민감정보를 표시함",
    { left: 40, top: 108, width: 1200, height: 28 },
    16,
    { color: C.slate },
  );

  addBoundary(slide, { x: 30, y: 145, w: 270, h: 462, title: "TB-1  외부 사용자 경계", fill: C.altRow, stroke: C.blue });
  addBoundary(slide, { x: 455, y: 205, w: 350, h: 225, title: "TB-2  당사 통제 경계", fill: C.tint, stroke: C.navy });
  addBoundary(slide, { x: 1010, y: 145, w: 240, h: 225, title: "TB-3  사내 연계 시스템 경계", fill: C.altRow, stroke: C.sub });
  addBoundary(slide, { x: 1010, y: 390, w: 240, h: 217, title: "TB-4  외부 AI 사업자 경계", fill: C.tint, stroke: C.dark });

  const customer = addNode(slide, { x: 80, y: 190, w: 170, h: 54, text: "고객" });
  const counselor = addNode(slide, { x: 80, y: 300, w: 170, h: 62, text: "상담사" });
  const operator = addNode(slide, { x: 80, y: 475, w: 170, h: 62, text: "운영자" });
  const system = addNode(slide, {
    x: 500,
    y: 270,
    w: 260,
    h: 100,
    text: "이탈위험 대응 상담 시스템",
    fill: C.navy,
    stroke: C.navy,
    color: C.white,
    size: 20,
  });
  const customerInfo = addNode(slide, { x: 1030, y: 205, w: 200, h: 58, text: "고객정보계\n보유카드정보", stroke: C.sub });
  const cardUsage = addNode(slide, { x: 1030, y: 290, w: 200, h: 58, text: "카드이용계\n이용현황", stroke: C.sub });
  const predictAI = addNode(slide, { x: 1030, y: 445, w: 200, h: 58, text: "외부 예측 AI 서비스", stroke: C.dark });
  const llm = addNode(slide, { x: 1030, y: 530, w: 200, h: 58, text: "외부 LLM", stroke: C.dark });

  connect(slide, customer, counselor, { fromSide: "bottom", toSide: "top", bidirectional: true, color: C.border });
  connect(slide, counselor, system, { fromSide: "right", toSide: "left", bidirectional: true, color: C.blue });
  connect(slide, operator, system, { fromSide: "right", toSide: "left", bidirectional: true, color: C.blue });
  connect(slide, system, customerInfo, { fromSide: "right", toSide: "left", bidirectional: true, color: C.sub });
  connect(slide, system, cardUsage, { fromSide: "right", toSide: "left", bidirectional: true, color: C.sub });
  connect(slide, system, predictAI, { fromSide: "right", toSide: "left", bidirectional: true, color: C.dark });
  connect(slide, system, llm, { fromSide: "right", toSide: "left", bidirectional: true, color: C.dark });

  addText(slide, "상담질문·본인확인 정보\n상담 안내·확인 결과", { left: 60, top: 245, width: 210, height: 46 }, 14, {
    color: C.slate,
    alignment: "center",
  });
  addEdgeLabel(slide, {
    x: 305,
    y: 248,
    w: 145,
    h: 90,
    title: "TB-1 · SL-1·2·3·4",
    detail: "회원ID·질문·상담사ID\n제안내용·근거·주의사항",
  });
  addEdgeLabel(slide, {
    x: 305,
    y: 430,
    w: 145,
    h: 78,
    title: "TB-1 · SL-5",
    detail: "원본 문서 경로\n색인 완료 시각",
  });
  addEdgeLabel(slide, {
    x: 815,
    y: 178,
    w: 185,
    h: 78,
    title: "TB-3 · SL-1·3",
    detail: "회원ID·조회 기준일\n카드ID·상품ID",
    accent: C.sub,
  });
  addEdgeLabel(slide, {
    x: 815,
    y: 282,
    w: 185,
    h: 78,
    title: "TB-3 · SL-1·3",
    detail: "회원ID·카드ID\n승인 사용액·연체액",
    accent: C.sub,
  });
  addEdgeLabel(slide, {
    x: 815,
    y: 410,
    w: 185,
    h: 82,
    title: "TB-4 · SL-1·3·4",
    detail: "회원ID·고객 현황·예측 기간\n이탈 확률·위험 등급",
    accent: C.dark,
  });
  addEdgeLabel(slide, {
    x: 815,
    y: 510,
    w: 185,
    h: 82,
    title: "TB-4 · SL-2·5",
    detail: "비식별 질문·선별 근거\n질문 해석·상담 제안 초안",
    accent: C.dark,
  });

  const guard = slide.shapes.add({
    geometry: "roundRect",
    position: { left: 455, top: 460, width: 350, height: 118 },
    fill: C.white,
    line: { style: "solid", fill: C.blue, width: 2 },
    borderRadius: 8,
  });
  guard.text = [
    [{ run: "외부 LLM 미통과", textStyle: { bold: true, color: C.navy, fontSize: "16pt", typeface: FONT } }],
    [{ run: "회원ID·카드ID·상담사ID·상담ID·원문 문서 경로", textStyle: { color: C.slate, fontSize: "14pt", typeface: FONT } }],
    [{ run: "입력 전 제거하고 대체 ID를 사용함", textStyle: { bold: true, color: C.blue, fontSize: "14pt", typeface: FONT } }],
  ];
  guard.text.style = {
    typeface: FONT,
    fontSize: fsPt(14),
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: { top: 6, right: 10, bottom: 6, left: 10 },
  };

  const legend = slide.shapes.add({
    geometry: "roundRect",
    position: { left: 30, top: 625, width: 1220, height: 54 },
    fill: C.altRow,
    line: { style: "solid", fill: C.border, width: 1 },
    borderRadius: 8,
  });
  legend.text =
    "SL-1 개인정보  회원ID·상담사ID·상담ID     SL-2 상담정보  질문·발언·상담일     SL-3 금융정보  카드ID·상품ID·승인액·연체액\n" +
    "SL-4 추론정보  이탈확률·위험등급·판단신호     SL-5 내부업무정보  문서ID·문단·원문위치·버전";
  legend.text.style = {
    typeface: FONT,
    fontSize: fsPt(14),
    bold: false,
    color: C.slate,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: { top: 4, right: 8, bottom: 4, left: 8 },
  };

  slide.shapes.add({
    geometry: "line",
    position: { left: 40, top: 691, width: 1200, height: 0 },
    fill: "none",
    line: { style: "solid", fill: C.line, width: 1 },
  });
  addText(slide, "Agentic AI Architecture", { left: 40, top: 693, width: 280, height: 20 }, 14, { color: C.sub });
  addText(slide, "1", { left: 1190, top: 693, width: 50, height: 20 }, 14, { color: C.sub, alignment: "right" });

  slide.speakerNotes.textFrame.setText(
    "출처: 사용자가 제공한 문의 접수부터 상담 제안 확인까지의 이벤트 모델링 자료와 전체관계도 Mermaid 스크립트.",
  );
}

async function main() {
  await fs.mkdir(TMP_DIR, { recursive: true });
  await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

  const presentation = Presentation.create({
    slideSize: { width: 1280, height: 720 },
  });
  await createSlide01(presentation);

  const draftPath = path.join(TMP_DIR, "candidate.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(draftPath);

  const firstSlide = presentation.slides.getItem(0);
  const preview = await presentation.export({ slide: firstSlide, format: "png", scale: 1 });
  await fs.writeFile(path.join(TMP_DIR, "slide-1.png"), new Uint8Array(await preview.arrayBuffer()));
  const layout = await firstSlide.export({ format: "layout" });
  await fs.writeFile(path.join(TMP_DIR, "slide-1.layout.json"), await layout.text());

  const { finalizePresentation } = await import(
    pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
  );
  const stagingDir = path.join(workspaceDir, ".codex-finalizer");
  await fs.mkdir(stagingDir, { recursive: true });
  const result = await finalizePresentation({
    explicitTotalSlideCount: 1,
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [],
    workspaceDir,
    candidatePath: draftPath,
    finalPath: FINAL_PPTX,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
    layoutArgs: [
      "--expected-slide-size-emu",
      "12192000,6858000",
      "--validate-bullet-geometry",
      "--validate-heading-fit",
    ],
    fontPolicy: { basis: "design", families: [FONT] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
  });
  console.log(JSON.stringify({ finalPath: FINAL_PPTX, result }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
