import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const workspaceDir = "C:/Users/hiond/class/design-agentic-ai";
const TMP_DIR = path.join(workspaceDir, ".codex-build/swimlane-matrix");
const sourcePath = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-4단계-커맨드-완료예시-표형식-v4.pptx");
const FINAL_PPTX = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-작성예시-스윔레인매트릭스-v1.pptx");
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

const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));

// Existing deck page counts: 1/7 ... 7/7 -> 1/8 ... 7/8.
const pageHits = await presentation.inspect({ kind: "textbox", search: "/ 7", maxChars: 8000 });
for (const line of pageHits.ndjson.split(/\r?\n/).filter(Boolean)) {
  const rec = JSON.parse(line);
  if (rec.kind === "textbox" && rec.id && rec.text) {
    const box = presentation.resolve(rec.id);
    box.text.replace("/ 7", "/ 8");
  }
}

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
addText({ name: "lead", text: "행은 업무 책임, 열은 워크플로우 단계이며 셀에는 Command와 Event만 배치함", left: 34, top: 121, width: 1180, height: 28, fontSize: 18, color: C.slate, valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });

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
  { name: "지식 검색", h: 96 },
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

function addItem(row, col, offset, type, id, title, compact = false) {
  const x = gridX + laneW + col * colW + 4;
  const baseY = rowTops[row] + offset;
  const h = compact ? 20 : 25;
  const badgeW = compact ? 33 : 37;
  const color = type === "C" ? C.navy : C.dark;
  addText({ name: `${id}-badge`, text: id, left: x, top: baseY, width: badgeW, height: h, fontSize: compact ? 13 : 14, bold: true, color: C.white, align: "center", fill: color, radius: 4, insets: { left: 1, right: 1, top: 0, bottom: 0 } });
  addText({ name: `${id}-title`, text: title, left: x + badgeW + 3, top: baseY, width: colW - badgeW - 11, height: h, fontSize: compact ? 13 : 14, bold: true, color: C.ink, align: "left", fill: C.white, lineFill: C.border, lineWidth: 0.7, radius: 3, insets: { left: 4, right: 2, top: 0, bottom: 0 } });
}
function addPair(row, col, command, event, topOffset = 10, compact = false) {
  const gap = compact ? 22 : 29;
  addItem(row, col, topOffset, "C", command.id, command.title, compact);
  addItem(row, col, topOffset + gap, "E", event.id, event.title, compact);
}

addPair(0, 0, { id: "C-1", title: "문의 접수" }, { id: "E-1", title: "문의 접수됨" }, 9);
addPair(0, 5, { id: "C-9", title: "제안 데이터 제공" }, { id: "E-9", title: "제안 데이터 반환됨" }, 9);
addPair(0, 6, { id: "C-10", title: "제안 확인 기록" }, { id: "E-10", title: "제안 확인 기록됨" }, 9);
addPair(1, 1, { id: "C-2", title: "실행 경로 결정" }, { id: "E-2", title: "실행 경로 결정됨" }, 5);
addPair(2, 2, { id: "C-3", title: "고객 현황 확보" }, { id: "E-3", title: "고객 현황 확보됨" }, 5);
addPair(3, 2, { id: "C-4", title: "관련 문단 검색" }, { id: "E-4", title: "관련 문단 확보됨" }, 5, true);
addPair(3, 2, { id: "C-5", title: "카드 근거 조회" }, { id: "E-5", title: "카드 근거 확보됨" }, 49, true);
addPair(4, 2, { id: "C-6", title: "이탈 위험 예측" }, { id: "E-6", title: "이탈 위험 예측됨" }, 5);
addPair(5, 3, { id: "C-7", title: "제안 정보 선별" }, { id: "E-7", title: "제안 정보 구성됨" }, 11);
addPair(5, 4, { id: "C-8", title: "상담 제안 작성" }, { id: "E-8", title: "상담 제안 작성됨" }, 11);

// Parallel/conditional marker for the information acquisition stage.
const infoX = gridX + laneW + 2 * colW;
addText({ name: "parallel-marker", text: "조건에 따라 병렬", left: infoX + 12, top: gridY + headerH - 5, width: colW - 24, height: 18, fontSize: 13, bold: true, color: C.blueDark, align: "center", fill: "#FFFFFF", lineFill: C.blue, lineWidth: 0.8, radius: 8, insets: { left: 2, right: 2, top: 0, bottom: 0 } });

// Legend and footer.
const legendY = 652;
addText({ name: "legend-command", text: "Command", left: 300, top: legendY, width: 95, height: 25, fontSize: 14, bold: true, color: C.white, align: "center", fill: C.navy, radius: 5, insets: { left: 2, right: 2, top: 0, bottom: 0 } });
addText({ name: "legend-event", text: "Event", left: 405, top: legendY, width: 85, height: 25, fontSize: 14, bold: true, color: C.white, align: "center", fill: C.dark, radius: 5, insets: { left: 2, right: 2, top: 0, bottom: 0 } });
addText({ name: "legend-note", text: "화면·Trigger·Read Model은 Slice 상세표에서 확인", left: 505, top: legendY, width: 465, height: 25, fontSize: 14, color: C.slate, align: "center", fill: C.greenTint, lineFill: C.green, lineWidth: 0.8, radius: 6, insets: { left: 4, right: 4, top: 0, bottom: 0 } });
addLine("footer-rule", 34, 686, 1214, 686, C.line, 1);
addText({ name: "footer-left", text: "이탈 위험 방지 · Event Modeling 작성 예시", left: 36, top: 691, width: 640, height: 18, fontSize: 15, color: C.sub, valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
addText({ name: "footer-page", text: "8 / 8", left: 1125, top: 691, width: 86, height: 18, fontSize: 15, color: C.sub, align: "right", valign: "middle", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
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
const candidatePath = path.join(stagingDir, "swimlane-matrix-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const sourceBytes = await fs.readFile(sourcePath);
const referenceSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");
const requirements = {
  explicitTotalSlideCount: 8,
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
