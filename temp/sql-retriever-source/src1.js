// 2 ~ 13쪽: 개요, 목차, Ⅰ 구조, Ⅱ 공통 뼈대
const K = require("./common");
const { newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow, table, callout, codeBox, codePanel,
  codeH, cards, elbow, C, X0, CW, XR, TOP } = K;

const GAP = 0.25;
// 표준 배치: 왼쪽 발췌, 오른쪽 해설. 발췌 폭(cw)에 따라 오른쪽 시작점과 폭을 계산
const right = (cw) => ({ rx: X0 + cw + GAP, rw: XR - (X0 + cw + GAP) });

// 2 한눈에 보기
async function createSlide02() {
  const s = newSlide({
    title: "SQL 검색기 한눈에 보기",
    lead: "상담사 질문 1건을 정형쿼리 또는 NL2SQL 계획으로 바꿔, 회원 범위 안에서 읽기 전용으로 조회하는 LangGraph 6단계 앱",
    notes: "대상 소스: ~/workspace/crc/sql-retriever(W-1). 설계 근거: sql_retriever_워크플로우설계서.pptx 5 ~ 7장.\n" +
      "숫자 출처: 단계와 간선은 app/infrastructure/graph.py, 정형쿼리는 app/domain/fixed_queries.py, 허용 뷰는 app/domain/catalog.py, " +
      "시험 수는 work/test_report.md(단위 261은 2026-10-15 pytest 재실행으로 확인).",
  });
  const stages = [["S-R1", "요청 접수와 검증"], ["S-R2", "정형쿼리 또는\nNL2SQL 판단"], ["S-R3", "계획 적합성 판정"],
    ["S-R4", "SQL 검증"], ["S-R5", "SQL 실행"], ["S-R6", "응답 구성과 반환"]];
  const endW = 1.0, w = 1.85, gap = (CW - 2 * endW - 6 * w) / 7, y = 2.45, h = 1.15;
  const xs = stages.map((_, i) => X0 + endW + gap + i * (w + gap));
  card(s, "요청", { x: X0, y: y + 0.3, w: endW, h: 0.55, fill: C.navy, line: null, color: C.white, size: 16, bold: true });
  card(s, "응답", { x: XR - endW, y: y + 0.3, w: endW, h: 0.55, fill: C.navy, line: null, color: C.white, size: 16,
    bold: true });
  stages.forEach(([id, name], i) => {
    const x = xs[i];
    const llm = id === "S-R2";
    rr(s, { x, y, w, h, fill: C.white, line: llm ? C.blue : C.border, lw: llm ? 2 : 1 });
    card(s, id, { x, y, w, h: 0.42, fill: llm ? C.blue : C.tableHead, line: null, color: llm ? C.white : C.navy,
      size: 16, bold: true });
    text(s, name, { x: x + 0.05, y: y + 0.44, w: w - 0.1, h: h - 0.48, size: 14, color: C.body, align: "center" });
    if (i < stages.length - 1) arrow(s, { x1: x + w, y1: y + 0.58, x2: x + w + gap, y2: y + 0.58, color: C.blue, width: 2 });
  });
  arrow(s, { x1: X0 + endW, y1: y + 0.58, x2: xs[0], y2: y + 0.58, color: C.blue, width: 2 });
  arrow(s, { x1: xs[5] + w, y1: y + 0.58, x2: XR - endW, y2: y + 0.58, color: C.blue, width: 2 });
  // 위쪽: S-R3 → S-R6 답할 수 없음 합류
  const c = (i) => xs[i] + w / 2;
  elbow(s, [[c(2), y], [c(2), 2.02], [c(5), 2.02], [c(5), y]], { color: C.slate, dash: "dash" });
  text(s, "답할 수 없음(재시도 소진 또는 제공 기간 밖) → S-R6 합류", { x: c(2) + 0.2, y: 2.07, w: 6.6, h: 0.32, size: 14,
    color: C.slate });
  // 아래쪽: L-1 되돌림
  elbow(s, [[c(2) - 0.3, y + h], [c(2) - 0.3, 3.95], [c(1) + 0.3, 3.95], [c(1) + 0.3, y + h]], { color: C.blue });
  elbow(s, [[c(3), y + h], [c(3), 4.15], [c(1) - 0.3, 4.15], [c(1) - 0.3, y + h]], { color: C.blue });
  text(s, "L-1 재계획: 부적합 또는 검증 실패면 S-R2로 1번 되돌아감", { x: c(3) + 0.15, y: 3.95, w: 6.4, h: 0.3,
    size: 14, color: C.blue, bold: true });
  // 오류 종료
  rr(s, { x: X0, y: 4.45, w: CW, h: 0.62, fill: C.altRow, line: C.border, dash: "dash" });
  text(s, "오류 종료(HTTP 4xx, 5xx)  S-R1: INVALID_REQUEST, MEMBER_NOT_FOUND, DB_ERROR   S-R2: LLM_UNAVAILABLE   " +
    "S-R4: SQL_VALIDATION_FAILED   S-R5: DB_TIMEOUT, DB_ERROR   S-R6: INTERNAL_ERROR   S-R1 ~ S-R5: TIME_BUDGET_EXCEEDED",
  { x: X0 + 0.15, y: 4.45, w: CW - 0.3, h: 0.62, size: 14, color: C.ink });
  const tiles = [["6개", "노드(S-R1 ~ S-R6)", "조건 간선 2개(S-R3 뒤, S-R4 뒤)"], ["8개", "정형쿼리 FQ-01 ~ FQ-08", "LLM 실패 시 키워드 규칙으로도 고름"],
    ["7개", "허용 뷰(app 스키마)", "SQL 검증기는 이 뷰와 컬럼만 통과"], ["261 + 26", "시험 통과", "단위(가짜 객체) + 통합(실제 DB, LLM)"]];
  const tw = (CW - 0.25 * 3) / 4;
  tiles.forEach(([big, label, sub], i) => {
    const x = X0 + i * (tw + 0.25);
    rr(s, { x, y: 5.3, w: tw, h: 1.75, fill: C.tint });
    text(s, big, { x, y: 5.37, w: tw, h: 0.72, size: 32, bold: true, color: C.blue, align: "center" });
    text(s, label, { x, y: 6.09, w: tw, h: 0.42, size: 16, bold: true, color: C.navy, align: "center" });
    text(s, sub, { x: x + 0.1, y: 6.5, w: tw - 0.2, h: 0.45, size: 14, color: C.slate, align: "center" });
  });
  callout(s, "원칙 3가지: LLM에는 가린 질문만 보냄. 검증을 통과한 SQL만 실행함. 요청 한 건에 15초를 주고 단계를 시작할 때마다 남은 시간을 잼",
    { y: 7.3, h: 0.55 });
}

// 3 목차
async function createSlide03() {
  const s = newSlide({ title: "목차" });
  const parts = [["Ⅰ", "구조", ["디렉토리 구조", "Layered Architecture", "DIP ① 포트 6개", "DIP ② 조립 지점 bootstrap"]],
    ["Ⅱ", "공통 뼈대", ["진입 CLI와 API", "서비스와 오류 응답", "LangGraph 흐름 조립", "상태 WorkflowState",
      "남은 시간 예산", "설정 읽기"]],
    ["Ⅲ", "단계별 소스", ["S-R1 형식 검사, 식별자 가림, 회원 확인", "S-R2 LLM 계획, C-01 커넥터, 키워드 규칙",
      "S-R3 계획 판정, 데이터 제공 기간", "S-R4 SQL 검증", "S-R5 읽기 전용 실행", "S-R6 응답과 감사 로그"]],
    ["Ⅳ", "시험과 정리", ["시험과 실측", "정리: 요청 한 건의 여정"]]];
  const w = (CW - 0.25) / 2, h = 3.05;
  parts.forEach(([n, t, items], i) => {
    const x = X0 + (i % 2) * (w + 0.25), y = 1.4 + Math.floor(i / 2) * (h + 0.25);
    rr(s, { x, y, w, h, fill: i === 1 || i === 2 ? C.altRow : C.tint });
    numBadge(s, n, { x: x + 0.2, y: y + 0.2, size: 0.55, fill: C.blue, fsz: 18 });
    text(s, t, { x: x + 0.9, y: y + 0.2, w: w - 1.0, h: 0.55, size: 21, bold: true, color: C.navy });
    text(s, items.map((v) => "- " + v).join("\n"), { x: x + 0.35, y: y + 0.9, w: w - 0.5, h: h - 1.0, size: 16,
      color: C.body, valign: "top" });
  });
}

// 4 디렉토리
async function createSlide04() {
  const s = newSlide({ title: "Ⅰ-1 디렉토리 구조",
    lead: "업무 규칙은 domain, 업무 순서와 포트는 application, 외부 기술은 infrastructure. 조립은 bootstrap.py 한 곳" });
  const lw = 8.75;
  // 비례 글꼴(Pretendard)이라 공백으로 열을 맞출 수 없음 → 이름 열과 설명 열을 따로 그려 줄을 맞춤
  const tree = [
    ["sql-retriever/", ""],
    ["├─ run_cli.py", "CLI 실행 스크립트"],
    ["├─ serve_api.py", "API 서버 실행 스크립트"],
    ["├─ app/", ""],
    ["│   ├─ bootstrap.py", "조립 지점(구현체 생성은 여기서만)"],
    ["│   ├─ domain/", "catalog, fixed_queries, masking, messages,"],
    ["│   │", "periods, request_rules, time_budget"],
    ["│   ├─ application/", "models, ports, steps, services"],
    ["│   ├─ infrastructure/", "graph, groq_planner, postgres_repository,"],
    ["│   │   │", "sql_validator, audit_log, settings"],
    ["│   │   └─ prompts/", "c01_system_prompt.md, c01_user_prompt.md"],
    ["│   └─ presentation/", "cli, api"],
    ["├─ tests/", "단위 시험 14개 파일, 통합 시험 2개 파일"],
    ["├─ work/", "설계 대조표, 개발 계획, 시험 결과, 실행 로그"],
    ["├─ logs/audit.jsonl", "감사 로그(실행할 때 생김)"],
    ["└─ 그 밖 파일", "pytest.ini, requirements.txt, README.md"],
  ];
  rr(s, { x: X0, y: TOP, w: lw, h: 6.0, fill: C.altRow, line: C.border, r: 0.06 });
  text(s, "~/workspace/crc/sql-retriever/ (.py 확장자 생략)", { x: X0 + 0.12, y: TOP + 0.08, w: lw - 0.24, h: 0.34,
    size: 14, color: C.sub, bold: true });
  const treeOpt = { y: TOP + 0.5, h: 5.4, fontFace: K.FONT, fontSize: K.fs(15), color: C.ink, valign: "top", margin: 0.02,
    isTextBox: true, paraSpaceAfter: 0, lineSpacingMultiple: 1.05 };
  s.addText(tree.map((r) => r[0]).join("\n"), { ...treeOpt, x: X0 + 0.15, w: 3.1 });
  s.addText(tree.map((r) => r[1] || " ").join("\n"), { ...treeOpt, x: X0 + 3.3, w: lw - 3.4, color: C.slate });
  const { rx, rw } = right(lw);
  darkBadge(s, "계층별 책임", { x: rx, y: TOP, w: rw, h: 0.42 });
  table(s, [["계층", "담는 것"],
    ["domain", "외부 기술 없는 업무 규칙: 시간 예산, 요청 검사, 식별자 가림, 허용 뷰, 정형쿼리, 기간, 안내 문장"],
    ["application", "요청, 응답, 상태, 오류 구조와 포트 6개, S-R1 ~ S-R6 단계 함수, 서비스"],
    ["infrastructure", "포트 구현: Groq LLM, PostgreSQL, sqlglot 검사기, LangGraph 흐름, 감사 로그, 설정"],
    ["presentation", "CLI와 FastAPI 진입점"],
    ["bootstrap", "설정 읽기 → 구현체 생성 → 서비스 조립"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [1.75, rw - 1.75], rowH: 0.62, size: 14, valign: "middle" });
  callout(s, "DB, LLM, SQL 파서, LangGraph import는 infrastructure에만 둠. test_settings_and_layers.py가 domain과 application에 이런 import가 없는지 자동 점검",
    { x: rx, y: 6.95, w: rw, h: 0.95, size: 15 });
}

// 5 Layered Architecture
async function createSlide05() {
  const s = newSlide({ title: "Ⅰ-2 Layered Architecture",
    lead: "바깥(입출력)에서 안쪽(업무 규칙)으로만 import하고, 외부 기술은 포트 모양에 맞춘 어댑터로 옆에서 끼움" });
  const lw = 8.9, bh = 1.45, gy = 0.42;
  const layers = [["Presentation", "app/presentation", ["cli.py", "api.py"], "요청을 받아 service.search(payload) 한 줄만 부름"],
    ["Application", "app/application", ["services.py", "steps.py", "ports.py", "models.py"], "S-R1 ~ S-R6 업무 순서. 포트만 알고 구현체는 모름"],
    ["Domain", "app/domain", ["time_budget", "request_rules", "masking", "catalog", "fixed_queries", "periods", "messages"],
      "외부 기술 없는 순수 규칙과 상수"]];
  layers.forEach(([name, dir, files, desc], i) => {
    const y = TOP + i * (bh + gy);
    rr(s, { x: X0, y, w: lw, h: bh, fill: i === 2 ? C.tint : C.white });
    darkBadge(s, name, { x: X0 + 0.15, y: y + 0.15, w: 2.0, h: 0.42, fill: i === 2 ? C.blue : C.navy });
    text(s, dir, { x: X0 + 0.15, y: y + 0.65, w: 2.1, h: 0.35, size: 14, color: C.sub });
    let px = X0 + 2.4, py = y + 0.15;
    files.forEach((f) => {
      const pw = 0.25 + f.length * 0.105;
      if (px + pw > X0 + lw - 0.15) { px = X0 + 2.4; py += 0.45; } // 줄이 넘치면 다음 줄로
      pill(s, f, { x: px, y: py, w: pw, h: 0.36, size: 14 });
      px += pw + 0.12;
    });
    text(s, desc, { x: X0 + 2.4, y: py + 0.42, w: lw - 2.55, h: y + bh - py - 0.45, size: 15, color: C.body });
    if (i < 2) arrow(s, { x1: X0 + lw / 2, y1: y + bh, x2: X0 + lw / 2, y2: y + bh + gy, color: C.blue, width: 2 });
  });
  text(s, "import 방향", { x: X0 + lw / 2 + 0.12, y: TOP + bh, w: 1.6, h: gy, size: 14, color: C.blue, bold: true });
  const { rx, rw } = right(lw);
  const ih = 3 * bh + 2 * gy;
  rr(s, { x: rx, y: TOP, w: rw, h: ih, fill: C.altRow });
  darkBadge(s, "Infrastructure  (app/infrastructure)", { x: rx + 0.15, y: TOP + 0.15, w: rw - 0.3, h: 0.42 });
  const adapters = [["graph.py", "LangGraphRunner", "WorkflowRunnerPort"], ["groq_planner.py", "GroqPlanner", "PlannerPort"],
    ["postgres_repository.py", "PostgresRepository", "MemberRepositoryPort, SqlExecutorPort"],
    ["sql_validator.py", "SqlglotValidator", "SqlValidatorPort"], ["audit_log.py", "JsonlAuditLog", "AuditLogPort"],
    ["settings.py", "load_settings", "(포트 아님, bootstrap이 씀)"]];
  adapters.forEach(([f, cls, port], i) => {
    const y = TOP + 0.75 + i * 0.73;
    rr(s, { x: rx + 0.15, y, w: rw - 0.3, h: 0.63, fill: C.white });
    text(s, `${f}  →  ${cls}`, { x: rx + 0.25, y, w: rw - 0.5, h: 0.32, size: 14, bold: true, color: C.navy });
    text(s, port, { x: rx + 0.25, y: y + 0.3, w: rw - 0.5, h: 0.32, size: 14, color: C.slate });
  });
  arrow(s, { x1: rx, y1: TOP + bh + gy + bh / 2, x2: X0 + lw, y2: TOP + bh + gy + bh / 2, color: C.blue, width: 2 });
  text(s, "포트 상속", { x: X0 + lw - 1.25, y: TOP + bh + gy + bh / 2 - 0.38, w: 1.2, h: 0.32, size: 14, color: C.blue,
    bold: true, align: "right" });
  const by = TOP + ih + 0.25;
  rr(s, { x: X0, y: by, w: CW, h: 7.9 - by, fill: C.tint, line: C.pill });
  text(s, "bootstrap.py — 설정을 읽고 구현체를 만들어 서비스에 끼우는 유일한 곳. CLI와 API는 서비스를 받지 못했을 때만 지연 import로 부름",
    { x: X0 + 0.2, y: by, w: CW - 0.4, h: 7.9 - by, size: 16, bold: true, color: C.navy });
}

// 6 DIP ① 포트
async function createSlide06() {
  const s = newSlide({ title: "Ⅰ-3 DIP ① 응용 계층이 포트를 소유",
    lead: "application이 '무엇이 필요한가'를 포트(Protocol + @abstractmethod)로 정하고, 어댑터가 그 포트를 상속해 구현함",
    notes: "포트 docstring에는 입력 전제, 반환값, 예외, 부수효과가 적혀 있음(references/dev-comment-guide.md 규칙)." });
  const cw = 9.0;
  codePanel(s, "ports", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  darkBadge(s, "포트 6개와 구현체", { x: rx, y: TOP, w: rw, h: 0.42 });
  table(s, [["포트", "구현체", "단계"],
    ["PlannerPort", "GroqPlanner", "S-R2"],
    ["MemberRepositoryPort", "PostgresRepository", "S-R1"],
    ["SqlExecutorPort", "PostgresRepository", "S-R5"],
    ["SqlValidatorPort", "SqlglotValidator", "S-R4"],
    ["AuditLogPort", "JsonlAuditLog", "S-R6"],
    ["WorkflowRunnerPort", "LangGraphRunner", "흐름"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [2.45, 2.25, rw - 4.7], rowH: 0.5, size: 14 });
  cards(s, [["명시적 상속", "class GroqPlanner(PlannerPort)처럼 포트를 상속. 추상 메서드를 빠뜨리면 객체를 만들 때 오류"],
    ["가짜 객체로 시험", "단위 시험은 FakePlanner, FakeRepository를 포트 자리에 끼워 DB와 LLM 없이 실행"]],
  { x: rx, y: 6.1, w: rw, h: 1.8, size: 14, gap: 0.1, headH: 0.36 });
}

// 7 DIP ② bootstrap
async function createSlide07() {
  const s = newSlide({ title: "Ⅰ-4 DIP ② 조립 지점 bootstrap",
    lead: "구현체 생성과 주입은 create_service 한 곳에서만. 단계 코드(WorkflowSteps)는 포트만 받고 구현체를 만들지 않음" });
  const cw = 9.6;
  codePanel(s, "bootstrap", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  cards(s, [["설정 읽기", "load_settings: secrets/.env와 환경변수"],
    ["DB 구현체 1개", "PostgresRepository 하나를 회원 확인 포트와 SQL 실행 포트에 함께 넣음"],
    ["LLM 고르기", "create_planner: 제공자가 groq면 GroqPlanner, 그 밖은 SettingsError"],
    ["단계에 주입", "WorkflowSteps에 포트 5개와 시계(utc_now)를 넣음. 시험에서는 가짜 시계"],
    ["흐름으로 감싸기", "LangGraphRunner(steps)를 SqlRetrieverService에 넘겨 완성"]],
  { x: rx, y: TOP, w: rw, h: 6.0, title: "조립 순서", size: 14 });
}

// 8 진입 CLI와 API
async function createSlide08() {
  const s = newSlide({ title: "Ⅱ-1 진입 CLI와 API",
    lead: "두 진입점 모두 요청 본문(payload)을 만들어 service.search 하나만 부름. 흐름 판단은 표현 계층에 두지 않음" });
  const cw = 9.0;
  const h1 = codePanel(s, "cli", { x: X0, y: TOP, w: cw });
  codePanel(s, "api", { x: X0, y: TOP + h1 + 0.15, w: cw });
  const { rx, rw } = right(cw);
  const box2 = (y, h, head, rows) => {
    headerBar(s, head, { x: rx, y, w: rw, h: 0.45, size: 16 });
    rr(s, { x: rx, y: y + 0.52, w: rw, h: h - 0.52, fill: C.altRow });
    text(s, rows.map((r) => "- " + r).join("\n"), { x: rx + 0.15, y: y + 0.6, w: rw - 0.3, h: h - 0.66, size: 14,
      valign: "top" });
  };
  box2(TOP, 2.75, "CLI  run_cli.py", ["--member-id와 --question은 필수, --base-date와 --request-id는 선택",
    "request_id를 안 주면 cli- + 12자리로 만듦", "응답 JSON을 UTF-8로 출력. 종료 코드는 HTTP 200이면 0, 아니면 1"]);
  box2(TOP + 2.95, 3.05, "API  serve_api.py", ["POST /v1/sql-retriever/search (기본 127.0.0.1:8000)",
    "본문 형식 오류도 FastAPI 기본 422가 아니라 INVALID_REQUEST(400)로 바꿈",
    "서비스는 첫 요청 때 한 번만 조립(get_service)", "상태 코드는 서비스 결과(http_status)를 그대로 씀"]);
}

// 9 서비스와 오류 응답
async function createSlide09() {
  const s = newSlide({ title: "Ⅱ-2 서비스와 오류 응답",
    lead: "단계가 던진 RetrieverError를 오류 코드표로 HTTP 상태와 안내 문구로 바꿈. 예상 밖 실패는 INTERNAL_ERROR(500)",
    notes: "오류 코드표 출처: app/application/models.py ERROR_CATALOG(설계서 33장과 같음)." });
  const cw = 9.0;
  codePanel(s, "service", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  darkBadge(s, "오류 코드 8종 (models.ERROR_CATALOG)", { x: rx, y: TOP, w: rw, h: 0.42 });
  table(s, [["오류 코드", "HTTP", "다시 시도"],
    ["INVALID_REQUEST", "400", "아니요"], ["MEMBER_NOT_FOUND", "404", "아니요"], ["LLM_UNAVAILABLE", "503", "예"],
    ["SQL_VALIDATION_FAILED", "422", "아니요"], ["DB_TIMEOUT", "504", "예"], ["DB_ERROR", "500", "예"],
    ["TIME_BUDGET_EXCEEDED", "504", "예"], ["INTERNAL_ERROR", "500", "예"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [rw - 2.25, 1.0, 1.25], rowH: 0.47, size: 14 });
  callout(s, "응답에는 오류 코드와 한국어 안내만. 내부 사유(detail)는 로그에만 남기고 SQL, 뷰 이름, 접속 정보는 넣지 않음",
    { x: rx, y: 6.8, w: rw, h: 1.1, size: 15 });
}

// 10 LangGraph 흐름
async function createSlide10() {
  const s = newSlide({ title: "Ⅱ-3 LangGraph 흐름 조립",
    lead: "노드 6개(단계 함수)와 조건 간선 2개. 오류 종료는 단계 함수가 RetrieverError를 던져 그래프를 멈추는 방식" });
  const cw = 9.0;
  const h = codePanel(s, "graph", { x: X0, y: TOP, w: cw });
  text(s, "recursion_limit 12: 정상이면 노드를 최대 9번 지남(S-R1, S-R2 ~ S-R4 두 바퀴, S-R5, S-R6). 12는 그 위의 안전망. 체크포인트는 두지 않음",
    { x: X0, y: TOP + h + 0.05, w: cw, h: 7.95 - TOP - h - 0.05, size: 14, color: C.slate });
  const { rx, rw } = right(cw);
  const nodes = ["START", "S-R1", "S-R2", "S-R3", "S-R4", "S-R5", "S-R6", "END"];
  const nw = 1.7, nh = 0.5, ng = 0.21, nx = rx + 0.2;
  const ny = (i) => TOP + i * (nh + ng);
  nodes.forEach((n, i) => {
    const edge = i === 0 || i === 7;
    const cond = n === "S-R3" || n === "S-R4";
    card(s, n, { x: nx, y: ny(i), w: nw, h: nh, fill: edge ? C.navy : cond ? C.tint : C.white,
      line: edge ? null : cond ? C.blue : C.border, color: edge ? C.white : C.navy, size: 15, bold: true });
    if (i < 7) arrow(s, { x1: nx + nw / 2, y1: ny(i) + nh, x2: nx + nw / 2, y2: ny(i + 1), color: C.slate });
  });
  const mid = (i) => ny(i) + nh / 2;
  elbow(s, [[nx + nw, mid(3)], [nx + nw + 0.45, mid(3)], [nx + nw + 0.45, mid(2)], [nx + nw, mid(2)]], { color: C.blue });
  elbow(s, [[nx + nw, mid(4) - 0.08], [nx + nw + 0.85, mid(4) - 0.08], [nx + nw + 0.85, mid(2) - 0.12], [nx + nw, mid(2) - 0.12]],
    { color: C.blue });
  elbow(s, [[nx, mid(3)], [nx - 0.15, mid(3)], [nx - 0.15, mid(6)], [nx, mid(6)]], { color: C.slate, dash: "dash" });
  const tx = nx + nw + 1.0;
  text(s, "next_after_r3\nFIT → S-R4\nUNFIT → S-R2\nUNANSWERABLE → S-R6(점선)", { x: tx, y: ny(2) - 0.1, w: XR - tx, h: 1.4, size: 14,
    color: C.ink, valign: "top" });
  text(s, "next_after_r4\nvalidated_sql 있음 → S-R5\n없음 → S-R2(재생성)", { x: tx, y: ny(4) + 0.35, w: XR - tx, h: 1.1,
    size: 14, color: C.ink, valign: "top" });
}

// 11 상태
async function createSlide11() {
  const s = newSlide({ title: "Ⅱ-4 상태 WorkflowState",
    lead: "단계 사이에 오가는 필드를 TypedDict 하나로 정함. 이름과 뜻은 설계서 32장 필드 영문명과 같음" });
  const cw = 7.0;
  const h = codePanel(s, "state", { x: X0, y: TOP, w: cw });
  callout(s, "단계 함수는 자기 출력 필드만 dict로 돌려줌. 값을 합치는 규칙(reducer)을 따로 두지 않아, 같은 이름이면 나중에 돌려준 값이 앞 값을 덮어씀",
    { x: X0, y: TOP + h + 0.25, w: cw, h: 7.9 - TOP - h - 0.25, size: 15 });
  const { rx, rw } = right(cw);
  darkBadge(s, "단계별 출력 필드 (발췌 생략 부분 포함)", { x: rx, y: TOP, w: rw, h: 0.42 });
  table(s, [["단계", "출력 필드"],
    ["S-R1", "masked_question, masked_count, base_date(date로 확정), coverage_start, started_at, attempt = 0"],
    ["S-R2", "plan, plan_source, attempt(+1)"],
    ["S-R3", "verdict, candidate_sql, sql_source, query_id, retry_reason, unanswerable_reason"],
    ["S-R4", "validated_sql, row_limit, previous_sql (+ retry_reason)"],
    ["S-R5", "columns, rows, row_count, truncated, db_elapsed_ms"],
    ["S-R6", "response (호출자에게 돌려줄 응답 본문)"],
    ["내부", "retry_disabled: 시간 예산 착지로 재시도를 껐는지. 응답에는 안 나감"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [1.1, rw - 1.1], rowH: 0.68, size: 14 });
}

// 12 남은 시간 예산
async function createSlide12() {
  const s = newSlide({ title: "Ⅱ-5 남은 시간 예산",
    lead: "단계를 시작하기 전마다 실제로 흐른 시간을 재서, 남은 시간 예산이 0.75초 이상일 때만 시작함(설계서 27 ~ 28장)" });
  const cw = 8.6;
  codePanel(s, "budget", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  rr(s, { x: rx, y: TOP, w: rw, h: 1.45, fill: C.tint, line: C.pill });
  text(s, "남은 시간 = 15 - 흐른 시간 - 1(종료 처리)\n남은 시간 예산 = 남은 시간 - 차감값\n시작 조건: 남은 시간 예산 ≥ 0.75초(15 × 5%)",
    { x: rx + 0.15, y: TOP + 0.05, w: rw - 0.3, h: 1.35, size: 15, color: C.navy, bold: true });
  table(s, [["시작 전", "차감값", "미달이면(착지)"],
    ["S-R1", "5초", "TIME_BUDGET_EXCEEDED"],
    ["S-R2", "5초", "LLM 없이 키워드 규칙. 맞는 정형쿼리가 없으면 TIME_BUDGET_EXCEEDED"],
    ["S-R3, S-R4", "attempt 1이면 5초, 그 밖 0초", "재시도를 끄고 차감 0초로 다시 계산. 그래도 미달이면 TIME_BUDGET_EXCEEDED"],
    ["S-R5", "0초", "TIME_BUDGET_EXCEEDED"],
    ["S-R6", "측정 안 함", "항상 실행(종료 처리 1초를 미리 떼어 둠)"]],
  { x: rx, y: TOP + 1.6, w: rw, colW: [1.2, 1.5, rw - 2.7], rowH: 0.55, size: 14 });
  callout(s, "예: 흐른 시간 9.6초, 차감 5초 → 남은 시간 4.4초, 예산 -0.6초 → 시작 불가(check_budget 예시)",
    { x: rx, y: 7.1, w: rw, h: 0.8, size: 14 });
}

// 13 설정 읽기
async function createSlide13() {
  const s = newSlide({ title: "Ⅱ-6 설정 읽기",
    lead: "secrets/.env와 환경변수를 합쳐 Settings를 만듦. 같은 이름이면 환경변수가 이기고, 필수 4개가 비면 SettingsError" });
  const cw = 9.0;
  codePanel(s, "settings", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  darkBadge(s, "읽는 이름 (값은 문서에 적지 않음)", { x: rx, y: TOP, w: rw, h: 0.42 });
  table(s, [["이름", "기본값"],
    ["SQL_RETRIEVER_LLM_PROVIDER", "필수(groq)"], ["SQL_RETRIEVER_LLM_MODEL", "필수"], ["GROQ_API_KEY", "필수"],
    ["RDB_PASSWORD", "필수"], ["RDB_HOST", "localhost"], ["RDB_PORT", "5432"], ["RDB_NAME", "cardlab"],
    ["SQL_RETRIEVER_AUDIT_LOG", "logs/audit.jsonl"], ["SQL_RETRIEVER_ENV_FILE", "../secrets/.env"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [3.35, rw - 3.35], rowH: 0.45, size: 14 });
  callout(s, "DB 계정은 sql_retriever_user로 고정(설정 이름을 열어 두지 않음). 키와 비밀번호는 repr에 안 나오게 숨김",
    { x: rx, y: 7.0, w: rw, h: 0.9, size: 14 });
}

module.exports = [createSlide02, createSlide03, createSlide04, createSlide05, createSlide06, createSlide07, createSlide08,
  createSlide09, createSlide10, createSlide11, createSlide12, createSlide13];
