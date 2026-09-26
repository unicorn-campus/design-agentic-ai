import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/Users/hiond/class/design-agentic-ai";
const SKILL_DIR = "C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const TMP_DIR = path.join(workspaceDir, ".codex-build/deployment-decision-ppt");
const FINAL_PPTX = path.join(workspaceDir, "output/pptx/배포단위-결정-및-통신방식-v3.pptx");
const RUNTIME_PYTHON = "C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";

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

function sectionBar(slide, { x, y, w, text, accent = false }) {
  const bar = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: 42 },
    fill: accent ? C.blue : C.navy,
    line: { fill: "none", width: 0 },
    borderRadius: 6,
  });
  bar.text = text;
  bar.text.style = {
    typeface: FONT,
    fontSize: fsPt(18),
    bold: true,
    color: C.white,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    insets: { top: 2, right: 5, bottom: 2, left: 5 },
  };
  return bar;
}

function addDeployNode(slide, { x, y, w, h, id, title, body, fill, stroke, color }) {
  const node = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: stroke, width: 2 },
    borderRadius: 10,
    shadow: "shadow-sm",
  });
  node.text = [
    [{ run: id, textStyle: { bold: true, color, fontSize: "18pt", typeface: FONT } }],
    [{ run: title, textStyle: { bold: true, color, fontSize: "16pt", typeface: FONT } }],
    [{ run: body, textStyle: { color, fontSize: "14pt", typeface: FONT } }],
  ];
  node.text.style = {
    typeface: FONT,
    fontSize: fsPt(14),
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: { top: 5, right: 8, bottom: 5, left: 8 },
  };
  return node;
}

function addLabel(slide, { x, y, w, h, text, color = C.slate, fill = C.white }) {
  const label = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: C.border, width: 1 },
    borderRadius: 5,
  });
  label.text = text;
  label.text.style = {
    typeface: FONT,
    fontSize: fsPt(14),
    bold: true,
    color,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: { top: 3, right: 4, bottom: 3, left: 4 },
  };
  return label;
}

function connect(slide, source, target, { fromSide, toSide, dashed = false, bidirectional = false, color = C.sub }) {
  return slide.shapes.connect(source, target, {
    kind: "straight",
    fromSide,
    toSide,
    line: { style: dashed ? "dashed" : "solid", fill: color, width: 2 },
    head: { type: "triangle", width: "sm", length: "sm" },
    ...(bidirectional ? { tail: { type: "triangle", width: "sm", length: "sm" } } : {}),
  });
}

function styleDecisionTable(table) {
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 5, columnCount: 6 }).assign({
    textStyle: {
      typeface: FONT,
      fontSize: fsPt(14),
      color: C.slate,
      alignment: "center",
      verticalAlignment: "middle",
      autoFit: "none",
      wrap: "square",
    },
    margins: { top: 4, right: 5, bottom: 4, left: 5 },
    anchor: "middle",
  });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 6 }).assign({
    fill: C.tableHead,
    textStyle: {
      typeface: FONT,
      fontSize: fsPt(14),
      bold: true,
      color: C.navy,
      alignment: "center",
      verticalAlignment: "middle",
    },
  });
  table.cells.block({ row: 1, column: 0, rowCount: 1, columnCount: 6 }).fill = C.white;
  table.cells.block({ row: 2, column: 0, rowCount: 1, columnCount: 6 }).fill = C.altRow;
  table.cells.block({ row: 3, column: 0, rowCount: 1, columnCount: 6 }).fill = C.white;
  table.cells.block({ row: 4, column: 0, rowCount: 1, columnCount: 6 }).fill = C.altRow;
  table.cells.block({ row: 1, column: 0, rowCount: 4, columnCount: 1 }).textStyle.alignment = "left";
  table.cells.block({ row: 1, column: 5, rowCount: 4, columnCount: 1 }).textStyle.bold = true;
  table.cells.block({ row: 1, column: 5, rowCount: 4, columnCount: 1 }).textStyle.color = C.blue;
  for (let row = 1; row <= 4; row += 1) {
    table.rows[row].height = 66;
  }
  table.rows[0].height = 46;
}

async function createSlide01(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = C.white;

  addText(slide, "② 논리 아키텍처 › 프로세스 분리 판정", { left: 40, top: 18, width: 760, height: 24 }, 14, {
    bold: true,
    color: C.sub,
  });
  addText(slide, "내부 서비스 배포 단위 결정과 통신 방식", { left: 40, top: 42, width: 1180, height: 52 }, 31, {
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
    "세 개의 배포 단위로 분리하고, 상담 흐름은 동기 통신으로 연결하며 문서 색인은 MQ 비동기로 격리함",
    { left: 40, top: 108, width: 1200, height: 28 },
    16,
    { color: C.slate },
  );

  sectionBar(slide, { x: 40, y: 150, w: 710, text: "4개 질문 기준 배포 판단" });
  sectionBar(slide, { x: 775, y: 150, w: 465, text: "배포 단위 간 통신", accent: true });

  const table = slide.tables.add({
    rows: 5,
    columns: 6,
    left: 40,
    top: 200,
    width: 710,
    height: 310,
    columnWidths: [225, 82, 82, 82, 82, 157],
    values: [
      ["비교 후보", "독립 배포", "독립 확장", "장애 격리", "트리거 상이", "결정"],
      ["문서 색인 ↔ 상담 요청 처리", "근거 미확정", "예", "예", "예", "P-3 분리"],
      ["상담 핵심 ↔ 조회·분석", "근거 미확정", "예", "예", "아니오", "P-1·P-2 분리"],
      ["상담 진행 ↔ 제안 작성", "아니오", "아니오", "아니오", "아니오", "P-1로 합침"],
      ["고객 현황 ↔ 지식 검색 ↔ 이탈 예측", "아니오", "조건부", "조건부", "아니오", "P-2로 합침"],
    ],
  });
  styleDecisionTable(table);

  const decision = slide.shapes.add({
    geometry: "roundRect",
    position: { left: 40, top: 535, width: 710, height: 112 },
    fill: C.tint,
    line: { style: "solid", fill: C.border, width: 1 },
    borderRadius: 8,
  });
  decision.text = [
    [{ run: "최종 배포 단위", textStyle: { bold: true, color: C.navy, fontSize: "17pt", typeface: FONT } }],
    [{ run: "P-1 상담 오케스트레이션  상담 진행 관리·상담 제안 작성", textStyle: { color: C.slate, fontSize: "14pt", typeface: FONT } }],
    [{ run: "P-2 조회·분석  고객 현황 조회·지식 검색·이탈 위험 예측", textStyle: { color: C.slate, fontSize: "14pt", typeface: FONT } }],
    [{ run: "P-3 문서 색인 Worker  문서 색인", textStyle: { color: C.slate, fontSize: "14pt", typeface: FONT } }],
  ];
  decision.text.style = {
    typeface: FONT,
    fontSize: fsPt(14),
    alignment: "left",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: { top: 7, right: 12, bottom: 7, left: 14 },
  };

  const p1 = addDeployNode(slide, {
    x: 795,
    y: 215,
    w: 175,
    h: 135,
    id: "P-1",
    title: "상담 오케스트레이션",
    body: "상담 진행 관리\n상담 제안 작성",
    fill: C.navy,
    stroke: C.navy,
    color: C.white,
  });
  const p2 = addDeployNode(slide, {
    x: 1050,
    y: 215,
    w: 175,
    h: 135,
    id: "P-2",
    title: "조회·분석",
    body: "고객 현황·지식 검색\n이탈 위험 예측\n인덱스 읽기",
    fill: C.tint,
    stroke: C.blue,
    color: C.navy,
  });
  const mq = addDeployNode(slide, {
    x: 795,
    y: 500,
    w: 175,
    h: 100,
    id: "MQ",
    title: "색인 작업 메시지",
    body: "요청·완료·실패 이벤트",
    fill: C.altRow,
    stroke: C.sub,
    color: C.ink,
  });
  const p3 = addDeployNode(slide, {
    x: 1050,
    y: 500,
    w: 175,
    h: 100,
    id: "P-3",
    title: "문서 색인 Worker",
    body: "문서 색인\n인덱스 쓰기",
    fill: C.dark,
    stroke: C.dark,
    color: C.white,
  });

  connect(slide, p1, p2, { fromSide: "right", toSide: "left", bidirectional: true, color: C.blue });

  connect(slide, p1, mq, { fromSide: "bottom", toSide: "top", dashed: true, bidirectional: true, color: C.sub });

  connect(slide, mq, p3, { fromSide: "right", toSide: "left", dashed: true, bidirectional: true, color: C.sub });

  addLabel(slide, { x: 995, y: 355, w: 230, h: 52, text: "P-1 ↔ P-2  동기 REST/gRPC" });
  addLabel(slide, {
    x: 995,
    y: 420,
    w: 230,
    h: 52,
    text: "P-1 ↔ P-3  MQ 비동기",
    color: C.dark,
    fill: C.altRow,
  });
  addLabel(slide, {
    x: 795,
    y: 615,
    w: 430,
    h: 42,
    text: "공유 문서·벡터 인덱스: P-3 쓰기 · P-2 읽기",
    color: C.slate,
    fill: C.white,
  });

  addText(slide, "실선  동기 통신    점선  MQ 비동기 통신", { left: 790, top: 660, width: 440, height: 24 }, 14, {
    color: C.sub,
    alignment: "center",
  });

  slide.shapes.add({
    geometry: "line",
    position: { left: 40, top: 691, width: 1200, height: 0 },
    fill: "none",
    line: { style: "solid", fill: C.line, width: 1 },
  });
  addText(slide, "Agentic AI Architecture", { left: 40, top: 693, width: 280, height: 20 }, 14, { color: C.sub });
  addText(slide, "1", { left: 1190, top: 693, width: 50, height: 20 }, 14, { color: C.sub, alignment: "right" });

  slide.speakerNotes.textFrame.setText(
    "설계 판단: 상담 오케스트레이션과 조회·분석은 동기 REST/gRPC로 연결함. 문서 색인은 Message Queue 비동기로 분리함. P-2 장애 시 P-1은 상담사 이관 또는 제한된 제안으로 전환해야 장애 격리 효과가 생김.",
  );
}

async function main() {
  await fs.mkdir(TMP_DIR, { recursive: true });
  await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
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
    requiredNativeTableOwnerSlides: [1],
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
      "--require-native-table-slide",
      "1",
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
