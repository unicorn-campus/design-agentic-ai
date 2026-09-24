import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const workspaceDir = "C:/Users/hiond/class/design-agentic-ai";
const TMP_DIR = path.join(workspaceDir, ".codex-build/scenario-spec");
const FINAL_PPTX = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-7단계-시나리오-구체화.pptx");
const sourcePath = path.join(workspaceDir, "docs/plan/think/em/Event-Modeling-4단계-커맨드-완료예시-표형식-v4.pptx");
const RUNTIME_PYTHON = "C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const FONT = "Pretendard";
const C = {
  navy: "#1E2A5C", blue: "#2E74C6", ink: "#2B3242", slate: "#4A5364",
  sub: "#7C8598", tint: "#EEF3FA", alt: "#F5F8FC", head: "#E2EEF9",
  dark: "#404155", border: "#D9E0EC", line: "#EDF0F6", white: "#FFFFFF",
};

const groups = [
  {
    title: "S-03·S-04 시나리오",
    range: "고객 현황 확보와 질문 관련 문단 검색",
    rows: [
      ["S-03", "고객 현황이 정상적으로 확보됨", "E-2가 발생하고 회원 ID와 조회 기준일이 유효하며 고객정보계와 카드이용계가 정상 상태임", "C-3 고객 현황 확보를 요청함", "카드 ID, 상품 ID, 승인 사용액, 출처, 기준시점이 포함된 E-3가 발생함"],
      ["S-03", "고객 정보 시스템이 응답하지 않음", "고객 현황 조회 경로가 선택되었지만 고객정보계 또는 카드이용계가 제한 시간 안에 응답하지 않음", "C-3 고객 현황 확보를 요청함", "고객 현황 확보가 보류되고 응답하지 않은 시스템, 실패 원인과 재시도 가능 여부가 기록됨"],
      ["S-04", "질문과 관련된 문단이 검색됨", "문서 검색 경로가 선택되고 질문, 회원 ID, 접근 범위와 벡터 색인이 준비됨", "C-4 질문 관련 문단 검색을 요청함", "문서 ID, 관련 문단, 유사도, 원문 위치와 버전이 포함된 E-4가 발생함"],
      ["S-04", "관련도 기준을 충족하는 문단이 없음", "벡터 색인은 정상이나 관련도 기준 이상의 문단이 존재하지 않음", "C-4 질문 관련 문단 검색을 요청함", "빈 검색 결과와 검색 조건, 관련도 기준, 색인 버전이 포함된 E-4가 발생함"],
    ],
  },
  {
    title: "S-05·S-06 시나리오",
    range: "보유 카드 관련 근거 조회와 이탈 위험 예측",
    rows: [
      ["S-05", "보유 카드와 연결된 근거가 조회됨", "회원의 카드 보유 관계가 확인되고 카드와 상품, 문서, 상담 이력의 관계 데이터가 존재함", "C-5 보유 카드 관련 근거 조회를 요청함", "카드–상품–문서 연결 관계, 관련 문단, 상담 근거와 출처가 포함된 E-5가 발생함"],
      ["S-05", "보유 카드와 연결된 근거가 없음", "회원의 카드 보유 관계는 확인되었지만 연결된 문서 또는 상담 근거가 존재하지 않음", "C-5 보유 카드 관련 근거 조회를 요청함", "빈 근거 목록과 확인한 관계 경로, 근거가 없는 이유가 포함된 E-5가 발생함"],
      ["S-06", "이탈 위험이 정상적으로 예측됨", "회원 ID, 고객 현황, 예측 기간과 필요한 예측 입력 변수가 준비됨", "C-6 이탈 위험 예측을 요청함", "이탈 확률, 위험 등급, 판단 신호, 모델 버전과 입력 데이터 기준시점이 포함된 E-6가 발생함"],
      ["S-06", "필수 예측 입력 변수가 누락됨", "고객 현황은 확보되었지만 예측에 필요한 필수 입력 변수의 일부가 누락됨", "C-6 이탈 위험 예측을 요청함", "예측이 보류되고 누락된 입력 변수, 보류 사유와 재시도 조건이 기록됨"],
    ],
  },
  {
    title: "S-07·S-08 시나리오",
    range: "상담 제안용 정보 구성과 상담 제안 작성",
    rows: [
      ["S-07", "상담 제안에 사용할 정보가 구성됨", "E-3, E-4, E-5가 완료되고 E-6이 완료되거나 보류 상태로 결정됨", "C-7 상담 제안용 정보 구성을 요청함", "선택한 고객 현황, 검색 근거, 예측 결과와 선택·제외 이유가 포함된 E-7이 발생함"],
      ["S-07", "상담 제안에 사용할 근거가 부족함", "검색과 예측이 완료되었지만 신뢰할 수 있는 문서·상담 근거가 없거나 필수 정보가 누락됨", "C-7 상담 제안용 정보 구성을 요청함", "정보 구성이 보류되고 부족한 정보, 제외한 결과, 보류 이유와 사람의 검토 필요 여부가 기록됨"],
      ["S-08", "근거가 포함된 상담 제안이 작성됨", "E-7이 발생하고 선택된 정보의 출처와 사용 권한이 유효함", "C-8 상담 제안 작성을 요청함", "상담 제안 ID, 제안 내용, 참조 근거와 주의사항이 포함된 E-8이 발생함"],
      ["S-08", "상담 제안의 근거 검증을 통과하지 못함", "상담 제안은 생성되었지만 내용과 참조 근거가 일치하지 않거나 금지된 표현이 발견됨", "C-8 상담 제안 작성을 요청함", "상담 제안 작성이 보류되고 검증 실패 항목, 사용하지 않은 생성 결과와 사람의 검토 필요 여부가 기록됨"],
    ],
  },
];

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
try { await fs.access(FINAL_PPTX); throw new Error(`Output already exists: ${FINAL_PPTX}`); } catch (e) { if (e.code !== "ENOENT") throw e; }

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function addShape(slide, { geometry = "rect", name, left, top, width, height, fill = "none", lineFill = "none", lineWidth = 0, radius = 0 }) {
  return slide.shapes.add({ geometry, name, position: { left, top, width, height }, fill, line: { style: "solid", fill: lineFill, width: lineWidth }, ...(radius ? { borderRadius: radius } : {}) });
}
function addText(slide, { name, text, left, top, width, height, fontSize = 16, bold = false, color = C.ink, align = "left", valign = "middle", fill = "none", lineFill = "none", lineWidth = 0, radius = 0, insets = { left: 4, right: 4, top: 2, bottom: 2 } }) {
  const box = addShape(slide, { geometry: "textbox", name, left, top, width, height, fill, lineFill, lineWidth, radius });
  box.text = text;
  box.text.style = { typeface: FONT, fontSize, bold, color, alignment: align, verticalAlignment: valign, autoFit: "shrinkText", wrap: "square", insets };
  return box;
}
function addLine(slide, name, x1, y1, x2, y2, color = C.border, width = 1) {
  return slide.shapes.add({ geometry: "line", name, position: { left: x1, top: y1, width: x2 - x1, height: y2 - y1 }, fill: "none", line: { style: "solid", fill: color, width } });
}
function buildSlide(group, index) {
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  addText(slide, { name: `crumb-${index}`, text: "Event Modeling  ›  7단계 시나리오 구체화", left: 34, top: 18, width: 800, height: 22, fontSize: 17, color: C.sub, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addText(slide, { name: `title-${index}`, text: group.title, left: 34, top: 43, width: 1180, height: 56, fontSize: 42, bold: true, color: C.navy, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addShape(slide, { name: `title-rule-${index}`, left: 34, top: 112, width: 1180, height: 3, fill: C.border });
  addShape(slide, { name: `title-accent-${index}`, left: 34, top: 112, width: 170, height: 4, fill: C.blue });
  addText(slide, { name: `lead-${index}`, text: `${group.range}의 정상 흐름과 예외 조건을 Given–When–Then으로 구체화함`, left: 34, top: 121, width: 1180, height: 28, fontSize: 18, color: C.slate, insets: { left: 0, right: 0, top: 0, bottom: 0 } });

  const headers = ["슬라이스 ID", "시나리오", "Given", "When", "Then"];
  const values = [headers, ...group.rows];
  const table = slide.tables.add({ rows: values.length, columns: 5, left: 34, top: 158, width: 1180, height: 508, columnWidths: [100, 220, 300, 230, 330], values });
  table.rows[0].height = 48;
  for (let r = 1; r < values.length; r++) table.rows[r].height = 115;
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 5 }).assign({
    fill: C.head,
    textStyle: { typeface: FONT, fontSize: 16, bold: true, color: C.navy, alignment: "center", verticalAlignment: "middle" },
    margins: { left: 7, right: 7, top: 5, bottom: 5 },
    anchor: "middle",
  });
  for (let r = 1; r < values.length; r++) {
    const rowFill = r % 2 === 1 ? C.white : C.alt;
    table.cells.block({ row: r, column: 0, rowCount: 1, columnCount: 5 }).assign({
      fill: rowFill,
      textStyle: { typeface: FONT, fontSize: 14, color: C.ink, alignment: "left", verticalAlignment: "middle" },
      margins: { left: 8, right: 8, top: 6, bottom: 6 },
      anchor: "middle",
    });
    table.getCell(r, 0).fill = C.tint;
    table.getCell(r, 0).text.style = { typeface: FONT, fontSize: 16, bold: true, color: C.blue, alignment: "center", verticalAlignment: "middle" };
    table.getCell(r, 1).text.style = { typeface: FONT, fontSize: 14, bold: true, color: C.navy, alignment: "left", verticalAlignment: "middle" };
    table.getCell(r, 3).fill = "#F7FAFE";
  }

  addLine(slide, `footer-rule-${index}`, 34, 686, 1214, 686, C.line, 1);
  addText(slide, { name: `footer-left-${index}`, text: "이탈 위험 방지 · Event Modeling 작성 예시", left: 36, top: 691, width: 640, height: 18, fontSize: 15, color: C.sub, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addText(slide, { name: `footer-page-${index}`, text: `${index} / ${groups.length}`, left: 1125, top: 691, width: 86, height: 18, fontSize: 15, color: C.sub, align: "right", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  slide.speakerNotes.textFrame.setText("사용자와 협의한 S-03부터 S-08까지의 Given–When–Then 시나리오를 표로 정리함.");
}

groups.forEach((group, i) => buildSlide(group, i + 1));

for (let i = 0; i < presentation.slides.items.length; i++) {
  const preview = await presentation.slides.getItem(i).export({ format: "png", scale: 1.5 });
  await fs.writeFile(path.join(TMP_DIR, `draft-slide-${i + 1}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const montage = await presentation.export({ format: "png", montage: { format: "png", columns: 2, slideWidth: 800, padding: 20, gap: 20, background: "#E9ECF3" } });
await fs.writeFile(path.join(TMP_DIR, "draft-montage.png"), new Uint8Array(await montage.arrayBuffer()));

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "scenario-spec-candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const sourceBytes = await fs.readFile(sourcePath);
const referenceSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");
const requirements = {
  explicitTotalSlideCount: 3,
  requiredNativeTableOwnerSlides: [1, 2, 3],
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
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit", "--require-native-table-slide", "1", "--require-native-table-slide", "2", "--require-native-table-slide", "3"],
  requiredNativeTableOwnerSlides: [1, 2, 3],
  fontPolicy: { basis: "reference", families: [FONT], referencePath: sourcePath, referenceSha256 },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
});
console.log(JSON.stringify({ final: FINAL_PPTX, result }, null, 2));
