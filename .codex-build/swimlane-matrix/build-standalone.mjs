import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const workspaceDir = "C:/Users/hiond/class/design-agentic-ai";
const TMP_DIR = path.join(workspaceDir, ".codex-build/swimlane-matrix");
const sourcePath = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-4단계-커맨드-완료예시-표형식-v4.pptx");
const FINAL_PPTX = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-스윔레인매트릭스-1장.pptx");
const RUNTIME_PYTHON = "C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const FONT = "Pretendard";
const C = {
  navy: "#1E2A5C",
  blue: "#2E74C6",
  blueDark: "#255E9F",
  ink: "#2B3242",
  slate: "#4A5364",
  sub: "#7C8598",
  tint: "#EEF3FA",
  alt: "#F5F8FC",
  head: "#E2EEF9",
  dark: "#404155",
  border: "#D9E0EC",
  line: "#EDF0F6",
  white: "#FFFFFF",
  green: "#258A72",
  greenTint: "#EAF7F2",
};

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
try { await fs.access(FINAL_PPTX); throw new Error(`Output already exists: ${FINAL_PPTX}`); } catch (e) { if (e.code !== "ENOENT") throw e; }

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const slide = presentation.slides.add();
slide.background.fill = C.white;

function addShape({ geometry = "rect", name, left, top, width, height, fill = "none", lineFill = "none", lineWidth = 0, radius = 0 }) {
  return slide.shapes.add({
    geometry,
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
    ...(radius ? { borderRadius: radius } : {}),
  });
}
function addText({ name, text, left, top, width, height, fontSize = 16, bold = false, color = C.ink, align = "left", valign = "middle", fill = "none", lineFill = "none", lineWidth = 0, radius = 0, insets = { left: 6, right: 6, top: 2, bottom: 2 } }) {
  const box = addShape({ geometry: "textbox", name, left, top, width, height, fill, lineFill, lineWidth, radius });
  box.text = text;
  box.text.style = {
    typeface: FONT,
    fontSize,
    bold,
    color,
    alignment: align,
    verticalAlignment: valign,
    autoFit: "shrinkText",
    wrap: "square",
    insets,
  };
  return box;
}
function addLine(name, x1, y1, x2, y2, color = C.border, width = 1) {
  return slide.shapes.add({
    geometry: "line",
    name,
    position: { left: x1, top: y1, width: x2 - x1, height: y2 - y1 },
    fill: "none",
    line: { style: "solid", fill: color, width },
  });
}

// Page header matching the source deck.
addText({ name: "breadcrumb", text: "Event Modeling  ›  6단계 Swimlane", left: 34, top: 18, width: 800, height: 22, fontSize: 17, color: C.sub, valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
addText({ name: "title", text: "스윔레인 매트릭스", left: 34, top: 43, width: 1180, height: 56, fontSize: 42, bold: true, color: C.navy, valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
addShape({ name: "title-rule", left: 34, top: 112, width: 1180, height: 3, fill: C.border });
addShape({ name: "title-rule-accent", left: 34, top: 112, width: 170, height: 4, fill: C.blue });
addText({ name: "lead", text: "행은 업무 책임, 열은 워크플로우 단계이며 셀에는 Slice ID와 업무명을 배치함", left: 34, top: 121, width: 1180, height: 28, fontSize: 18, color: C.slate, valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });

const gridX = 34;
const gridY = 158;
const gridW = 1180;
const laneW = 170;
const colW = (gridW - laneW) / 7;
const headerH = 52;
const lanes = [
  { name: "상담 진행 관리", h: 72 },
  { name: "실행 경로 관리", h: 64 },
  { name: "고객 현황 조회", h: 64 },
  { name: "지식 검색", h: 104 },
  { name: "이탈 위험 예측", h: 64 },
  { name: "상담 제안", h: 76 },
];
const stages = [
  "문의 접수",
  "실행 경로\n결정",
  "상담 정보\n확보",
  "제안 정보\n구성",
  "상담 제안\n작성",
  "상담 제안\n제공",
  "상담 제안\n확인",
];

// Top-left matrix label.
addText({ name: "corner-header", text: "Swimlane", left: gridX, top: gridY, width: laneW, height: headerH, fontSize: 18, bold: true, color: C.white, align: "center", fill: C.navy, lineFill: C.white, lineWidth: 1, insets: { left: 4, right: 4, top: 2, bottom: 2 } });

for (let c = 0; c < stages.length; c++) {
  const x = gridX + laneW + c * colW;
  addShape({ name: `stage-${c+1}-bg`, left: x, top: gridY, width: colW, height: headerH, fill: c === 2 ? "#D7E9FA" : C.head, lineFill: C.white, lineWidth: 1 });
  addText({ name: `stage-${c+1}-num`, text: String(c + 1), left: x + 7, top: gridY + 10, width: 26, height: 30, fontSize: 16, bold: true, color: C.white, align: "center", fill: C.blue, radius: 5, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addText({ name: `stage-${c+1}-label`, text: stages[c], left: x + 36, top: gridY + 4, width: colW - 40, height: 44, fontSize: 16, bold: true, color: C.navy, align: "center", insets: { left: 1, right: 1, top: 0, bottom: 0 } });
}

let y = gridY + headerH;
const rowTops = [];
for (let r = 0; r < lanes.length; r++) {
  const lane = lanes[r];
  rowTops.push(y);
  const rowFill = r % 2 === 0 ? C.white : C.alt;
  addText({ name: `lane-${r+1}`, text: lane.name, left: gridX, top: y, width: laneW, height: lane.h, fontSize: 17, bold: true, color: C.navy, align: "center", fill: r === 0 || r === 5 ? C.tint : C.head, lineFill: C.white, lineWidth: 1, insets: { left: 8, right: 8, top: 3, bottom: 3 } });
  for (let c = 0; c < 7; c++) {
    addShape({ name: `cell-${r+1}-${c+1}`, left: gridX + laneW + c * colW, top: y, width: colW, height: lane.h, fill: c === 2 ? (r % 2 === 0 ? "#F2F8FE" : "#EAF3FC") : rowFill, lineFill: C.line, lineWidth: 1 });
  }
  y += lane.h;
}

function addSlice(row, col, offset, sliceId, title, commandId, eventId, compact = false) {
  const x = gridX + laneW + col * colW + 5;
  const baseY = rowTops[row] + offset;
  const cardW = colW - 10;
  const titleH = compact ? 30 : 31;
  const metaH = compact ? 18 : 20;
  const badgeW = 43;
  addText({ name: `${sliceId}-badge`, text: sliceId, left: x, top: baseY, width: badgeW, height: titleH, fontSize: 14, bold: true, color: C.white, align: "center", fill: C.blue, radius: 5, insets: { left: 1, right: 1, top: 0, bottom: 0 } });
  addText({ name: `${sliceId}-title`, text: title, left: x + badgeW + 3, top: baseY, width: cardW - badgeW - 3, height: titleH, fontSize: 14, bold: true, color: C.navy, align: "left", fill: C.white, lineFill: C.blue, lineWidth: 0.8, radius: 4, insets: { left: 4, right: 2, top: 0, bottom: 0 } });
  addText({ name: `${sliceId}-links`, text: `${commandId} · ${eventId}`, left: x, top: baseY + titleH + 2, width: cardW, height: metaH, fontSize: 14, bold: true, color: C.slate, align: "center", fill: C.tint, lineFill: C.border, lineWidth: 0.7, radius: 4, insets: { left: 2, right: 2, top: 0, bottom: 0 } });
}

addSlice(0, 0, 9, "S-01", "문의 접수", "C-1", "E-1");
addSlice(0, 5, 9, "S-09", "상담 제안 제공", "C-9", "E-9");
addSlice(0, 6, 9, "S-10", "상담 제안 확인", "C-10", "E-10");
addSlice(1, 1, 5, "S-02", "실행 경로 결정", "C-2", "E-2");
addSlice(2, 2, 5, "S-03", "고객 현황 확보", "C-3", "E-3");
addSlice(3, 2, 2, "S-04", "질문 관련 문단 검색", "C-4", "E-4", true);
addSlice(3, 2, 52, "S-05", "보유 카드 관련 근거 조회", "C-5", "E-5", true);
addSlice(4, 2, 5, "S-06", "이탈 위험 예측", "C-6", "E-6");
addSlice(5, 3, 11, "S-07", "상담 제안용 정보 구성", "C-7", "E-7");
addSlice(5, 4, 11, "S-08", "상담 제안 작성", "C-8", "E-8");

// Parallel/conditional marker for the information acquisition stage.
const infoX = gridX + laneW + 2 * colW;
addText({ name: "parallel-marker", text: "조건에 따라 병렬", left: infoX + 12, top: gridY + headerH - 5, width: colW - 24, height: 20, fontSize: 14, bold: true, color: C.blueDark, align: "center", fill: "#FFFFFF", lineFill: C.blue, lineWidth: 0.8, radius: 8, insets: { left: 2, right: 2, top: 0, bottom: 0 } });

// Legend and footer.
const legendY = 658;
addText({ name: "legend-command", text: "S · Slice", left: 270, top: legendY, width: 110, height: 25, fontSize: 14, bold: true, color: C.white, align: "center", fill: C.blue, radius: 5, insets: { left: 2, right: 2, top: 0, bottom: 0 } });
addText({ name: "legend-event", text: "C/E · 연결 ID", left: 390, top: legendY, width: 135, height: 25, fontSize: 14, bold: true, color: C.white, align: "center", fill: C.dark, radius: 5, insets: { left: 2, right: 2, top: 0, bottom: 0 } });
addText({ name: "legend-note", text: "화면·Trigger·Read Model은 Slice 상세표에서 확인", left: 540, top: legendY, width: 465, height: 25, fontSize: 14, color: C.slate, align: "center", fill: C.greenTint, lineFill: C.green, lineWidth: 0.8, radius: 6, insets: { left: 4, right: 4, top: 0, bottom: 0 } });
addLine("footer-rule", 34, 686, 1214, 686, C.line, 1);
addText({ name: "footer-left", text: "이탈 위험 방지 · Event Modeling 작성 예시", left: 36, top: 691, width: 640, height: 18, fontSize: 15, color: C.sub, valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
addText({ name: "footer-page", text: "1 / 1", left: 1125, top: 691, width: 86, height: 18, fontSize: 15, color: C.sub, align: "right", valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
slide.speakerNotes.textFrame.setText("사용자 제공 Event 목록과 Slice 정의를 바탕으로 구성함. C-7/E-7은 첨부 표의 중복 ID를 전체 흐름에 맞게 바로잡아 표기함.");

// Save draft and previews.
const preview = await slide.export({ format: "png", scale: 2 });
await fs.writeFile(path.join(TMP_DIR, "matrix-slide-draft.png"), new Uint8Array(await preview.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(path.join(TMP_DIR, "matrix-slide-draft.layout.json"), await layout.text());
const montage = await presentation.export({ format: "png", montage: { format: "png", columns: 2, slideWidth: 800, padding: 20, gap: 20, background: "#E9ECF3" } });
await fs.writeFile(path.join(TMP_DIR, "draft-montage.png"), new Uint8Array(await montage.arrayBuffer()));

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "swimlane-matrix-standalone-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const sourceBytes = await fs.readFile(sourcePath);
const referenceSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");
const requirements = {
  explicitTotalSlideCount: 1,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  sourceTemplatePath: sourcePath,
};
const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
  requiredNativeTableOwnerSlides: [],
  fontPolicy: { basis: "reference", families: [FONT], referencePath: sourcePath, referenceSha256 },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
});
console.log(JSON.stringify({ final: FINAL_PPTX, result }, null, 2));
