import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const SKILL_DIR = "C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const workspaceDir = "C:/Users/hiond/class/design-agentic-ai";
const TMP_DIR = path.join(workspaceDir, ".codex-build/s04-scenario");
const FINAL_PPTX = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-S-04-시나리오-구체화-1장.pptx");
const sourcePath = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-4단계-커맨드-완료예시-표형식-v4.pptx");
const RUNTIME_PYTHON = "C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const FONT = "Pretendard";
const C = {
  navy: "#1E2A5C", blue: "#2E74C6", ink: "#2B3242", slate: "#4A5364",
  sub: "#7C8598", tint: "#EEF3FA", alt: "#F5F8FC", head: "#E2EEF9",
  dark: "#404155", border: "#D9E0EC", line: "#EDF0F6", white: "#FFFFFF",
};

const headers = ["슬라이스 ID", "시나리오", "Given", "When", "Then"];
const rows = [
  [
    "S-04",
    "질문과 관련된 문단을 검색",
    "질문 Q-1001은 ‘M카드의 공항 라운지 혜택은?’이고, 회원 M-1001의 접근 범위는 상담사임. 벡터 색인 BENEFIT-2026.09, 관련도 기준 0.75, 최대 결과 수 3개가 준비되어 있음",
    "질문 Q-1001과 접근 범위로 C-4 질문 관련 문단 검색을 요청함",
    "E-4가 발생함. DOC-203 v2026.08 14쪽 3번째 문단이 rank=1, similarity=0.87로 기록되고 원문 위치와 색인 버전이 포함됨",
  ],
  [
    "S-04",
    "관련도 기준을 충족하는 문단이 없음",
    "질문 Q-1002는 ‘해외 렌터카 보험 혜택은?’이고, BENEFIT-2026.09 색인의 최고 유사도는 0.62이며 관련도 기준은 0.75임",
    "질문 Q-1002와 최대 결과 수 3개로 C-4 질문 관련 문단 검색을 요청함",
    "E-4가 발생함. 결과 목록은 비어 있고 resultCount=0, maxSimilarity=0.62, threshold=0.75, 색인 버전 BENEFIT-2026.09가 기록됨",
  ],
  [
    "S-04",
    "벡터 색인을 사용할 수 없어 검색 보류",
    "벡터 색인 BENEFIT-2026.09가 unavailable 상태이고 검색 제한시간은 3초, 최대 재시도 횟수는 2회임",
    "질문 Q-1003으로 C-4 질문 관련 문단 검색을 요청함",
    "E-4는 발생하지 않음. ‘질문 관련 문단 검색이 보류되었음’이 발생하고 reasonCode=VECTOR_INDEX_UNAVAILABLE, 시도 횟수 2, 재시도 가능 시각이 기록됨",
  ],
];

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
try { await fs.access(FINAL_PPTX); throw new Error(`Output already exists: ${FINAL_PPTX}`); } catch (e) { if (e.code !== "ENOENT") throw e; }

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const slide = presentation.slides.add();
slide.background.fill = C.white;

function addShape({ geometry = "rect", name, left, top, width, height, fill = "none", lineFill = "none", lineWidth = 0, radius = 0 }) {
  return slide.shapes.add({ geometry, name, position: { left, top, width, height }, fill, line: { style: "solid", fill: lineFill, width: lineWidth }, ...(radius ? { borderRadius: radius } : {}) });
}
function addText({ name, text, left, top, width, height, fontSize = 16, bold = false, color = C.ink, align = "left", valign = "middle", fill = "none", lineFill = "none", lineWidth = 0, radius = 0, insets = { left: 4, right: 4, top: 2, bottom: 2 } }) {
  const box = addShape({ geometry: "textbox", name, left, top, width, height, fill, lineFill, lineWidth, radius });
  box.text = text;
  box.text.style = { typeface: FONT, fontSize, bold, color, alignment: align, verticalAlignment: valign, autoFit: "shrinkText", wrap: "square", insets };
  return box;
}
function addLine(name, x1, y1, x2, y2, color = C.border, width = 1) {
  return slide.shapes.add({ geometry: "line", name, position: { left: x1, top: y1, width: x2 - x1, height: y2 - y1 }, fill: "none", line: { style: "solid", fill: color, width } });
}

addText({ name: "crumb", text: "Event Modeling  ›  7단계 시나리오 구체화", left: 34, top: 18, width: 800, height: 22, fontSize: 17, color: C.sub, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
addText({ name: "title", text: "S-04 질문 관련 문단 검색", left: 34, top: 43, width: 1180, height: 56, fontSize: 42, bold: true, color: C.navy, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
addShape({ name: "title-rule", left: 34, top: 112, width: 1180, height: 3, fill: C.border });
addShape({ name: "title-accent", left: 34, top: 112, width: 170, height: 4, fill: C.blue });

addText({ name: "story-label", text: "유저스토리", left: 34, top: 126, width: 135, height: 64, fontSize: 18, bold: true, color: C.white, align: "center", fill: C.navy, radius: 6, insets: { left: 4, right: 4, top: 2, bottom: 2 } });
addText({ name: "story", text: "상담사로서 고객 질문과 의미상 관련된 문단과 원문 위치를 확인하고 싶음. 이를 통해 상담 제안에 사용할 근거를 신속하게 확보할 수 있음.", left: 177, top: 126, width: 1037, height: 64, fontSize: 18, bold: true, color: C.navy, fill: C.tint, lineFill: C.border, lineWidth: 1, radius: 6, insets: { left: 14, right: 14, top: 6, bottom: 6 } });

const values = [headers, ...rows];
const table = slide.tables.add({ rows: 4, columns: 5, left: 34, top: 204, width: 1180, height: 462, columnWidths: [95, 215, 315, 240, 315], values });
table.rows[0].height = 46;
for (let r = 1; r < 4; r++) table.rows[r].height = 138;
table.borders.assign({ style: "solid", fill: C.line, width: 1 });
table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 5 }).assign({
  fill: C.head,
  textStyle: { typeface: FONT, fontSize: 16, bold: true, color: C.navy, alignment: "center", verticalAlignment: "middle" },
  margins: { left: 7, right: 7, top: 5, bottom: 5 }, anchor: "middle",
});
for (let r = 1; r < 4; r++) {
  table.cells.block({ row: r, column: 0, rowCount: 1, columnCount: 5 }).assign({
    fill: r % 2 === 1 ? C.white : C.alt,
    textStyle: { typeface: FONT, fontSize: 14, color: C.ink, alignment: "left", verticalAlignment: "middle" },
    margins: { left: 8, right: 8, top: 6, bottom: 6 }, anchor: "middle",
  });
  table.getCell(r, 0).fill = C.tint;
  table.getCell(r, 0).text.style = { typeface: FONT, fontSize: 16, bold: true, color: C.blue, alignment: "center", verticalAlignment: "middle" };
  table.getCell(r, 1).text.style = { typeface: FONT, fontSize: 14, bold: true, color: C.navy, alignment: "left", verticalAlignment: "middle" };
  table.getCell(r, 3).fill = "#F7FAFE";
}

addLine("footer-rule", 34, 686, 1214, 686, C.line, 1);
addText({ name: "footer-left", text: "이탈 위험 방지 · Event Modeling 작성 예시", left: 36, top: 691, width: 640, height: 18, fontSize: 15, color: C.sub, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
addText({ name: "footer-page", text: "1 / 1", left: 1125, top: 691, width: 86, height: 18, fontSize: 15, color: C.sub, align: "right", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
slide.speakerNotes.textFrame.setText("S-04 질문 관련 문단 검색 Slice를 유저스토리와 구체적인 Specification by Example 시나리오로 정리함. 예시 ID와 값은 교육용 합성 데이터임.");

const preview = await slide.export({ format: "png", scale: 1.5 });
await fs.writeFile(path.join(TMP_DIR, "draft-slide-1.png"), new Uint8Array(await preview.arrayBuffer()));
const layout = await slide.export({ format: "layout" });
await fs.writeFile(path.join(TMP_DIR, "draft-slide-1.layout.json"), await layout.text());

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "s04-scenario-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const sourceBytes = await fs.readFile(sourcePath);
const referenceSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");
const result = await finalizePresentation({
  explicitTotalSlideCount: 1,
  requiredNativeTableOwnerSlides: [1],
  requiredNativeChartOwnerSlides: [],
  sourceTemplatePath: sourcePath,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit", "--require-native-table-slide", "1"],
  fontPolicy: { basis: "reference", families: [FONT], referencePath: sourcePath, referenceSha256 },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
});
console.log(JSON.stringify({ final: FINAL_PPTX, result }, null, 2));
