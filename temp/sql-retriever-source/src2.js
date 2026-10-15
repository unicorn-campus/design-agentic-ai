// 14 ~ 28쪽: Ⅲ 단계별 소스, Ⅳ 시험과 정리
const K = require("./common");
const { newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow, table, callout, codePanel,
  cards, elbow, C, X0, CW, XR, TOP } = K;

const GAP = 0.25;
const right = (cw) => ({ rx: X0 + cw + GAP, rw: XR - (X0 + cw + GAP) });

// 14 S-R1 ①
async function createSlide14() {
  const s = newSlide({ title: "Ⅲ-1 S-R1 ① 형식 검사와 식별자 가림",
    lead: "요청을 받자마자 형식을 검사하고, 외부 LLM으로 나가기 전에 질문 속 개인 식별자를 [가림]으로 바꿈" });
  const cw = 9.3;
  const h = codePanel(s, "r1_check", { x: X0, y: TOP, w: cw });
  codePanel(s, "masking", { x: X0, y: TOP + h + 0.15, w: cw });
  const { rx, rw } = right(cw);
  cards(s, [["시간 예산 먼저", "started_at을 기록하고 차감 5초로 예산을 잼(발췌 앞 130 ~ 133행). 미달이면 TIME_BUDGET_EXCEEDED"],
    ["형식 검사 4가지", "request_id 비어 있지 않음, 질문 1 ~ 500자, 회원ID M- + 숫자 4자리, 기준일 YYYY-MM-DD. 하나라도 틀리면 INVALID_REQUEST"],
    ["식별자 가림 순서", "카드번호 → 주민등록번호 → 전화번호 → 이메일 → 회원ID. 긴 카드번호를 먼저 가려야 그 일부가 전화번호로 잘못 잡히지 않음"]],
  { x: rx, y: TOP, w: rw, h: 4.75, size: 14 });
  callout(s, "이름처럼 정규식으로 못 잡는 식별자는 남을 수 있음(위험 항목 R-04)", { x: rx, y: 6.95, w: rw, h: 0.95, size: 15 });
}

// 15 S-R1 ②
async function createSlide15() {
  const s = newSlide({ title: "Ⅲ-2 S-R1 ② 회원 확인과 세션 변수",
    lead: "읽기 전용 트랜잭션 하나에서 데이터 기준일과 거래 제공 시작일을 읽고, 세션 변수 3개를 건 뒤 회원 가입일을 확인함" });
  const cw = 10.3;
  codePanel(s, "r1_member", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  rr(s, { x: rx, y: TOP, w: rw, h: 1.95, fill: C.tint, line: C.pill });
  text(s, "세션 변수 3개\napp.member_id\napp.base_date\napp.coverage_start", { x: rx + 0.15, y: TOP + 0.05, w: rw - 0.3,
    h: 1.15, size: 15, color: C.navy, bold: true, valign: "top" });
  text(s, "set_config(이름, 값, true): 이 트랜잭션 안에서만 유효", { x: rx + 0.15, y: TOP + 1.25, w: rw - 0.3, h: 0.65,
    size: 14, color: C.body, valign: "top" });
  cards(s, [["DB 실패", "접속 또는 조회 실패(시간 초과 포함) → DB_ERROR(500)"],
    ["기준일 오류", "요청 기준일 > 데이터 기준일 → INVALID_REQUEST(400)"],
    ["회원 없음", "가입일 없음 또는 가입일 > 기준일 → MEMBER_NOT_FOUND(404)"]],
  { x: rx, y: 4.05, w: rw, h: 3.85, title: "step_r1의 판정(156 ~ 163행)", size: 14 });
}

// 16 S-R2 ①
async function createSlide16() {
  const s = newSlide({ title: "Ⅲ-3 S-R2 ① LLM 계획과 대체 경로",
    lead: "LLM(C-01)으로 계획을 만들고, 예산이 모자라거나 LLM 호출이 실패하면 재시도 없이 키워드 규칙으로 정형쿼리를 고름" });
  const cw = 9.0;
  codePanel(s, "r2", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  pill(s, "attempt를 여기서 1 늘림. 회원ID는 PlanRequest에 없음", { x: rx, y: TOP, w: rw, h: 0.45, size: 14 });
  cards(s, [["예산 미달", "LLM을 부르지 않고 키워드 규칙. 맞는 정형쿼리가 없으면 TIME_BUDGET_EXCEEDED"],
    ["LLM 성공", "응답 JSON을 그대로 plan으로 씀. plan_source = LLM"],
    ["LLM 거절(refusal)", "route UNANSWERABLE 계획을 만들어 S-R3에 넘김"],
    ["LLM 호출 실패", "키워드 규칙에 맞으면 FIXED 계획(plan_source = KEYWORD_RULE), 없으면 LLM_UNAVAILABLE(503)"]],
  { x: rx, y: TOP + 0.6, w: rw, h: 5.4, size: 14 });
}

// 17 S-R2 ② C-01 커넥터
async function createSlide17() {
  const s = newSlide({ title: "Ⅲ-4 S-R2 ② C-01 커넥터 GroqPlanner",
    lead: "LangChain ChatOpenAI로 Groq의 OpenAI 호환 주소를 부르고, 프롬프트 | 구조화 출력 모델을 LCEL 체인 하나로 묶음",
    notes: "값 출처: app/infrastructure/groq_planner.py 상수, app/infrastructure/settings.py GROQ_BASE_URL. 설계서 24장 표와 같음." });
  const cw = 8.6;
  codePanel(s, "groq", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  darkBadge(s, "하이퍼파라미터 (설계서 24장)", { x: rx, y: TOP, w: rw, h: 0.42 });
  table(s, [["항목", "값"],
    ["base_url", "https://api.groq.com/openai/v1"], ["temperature", "0.2"], ["reasoning_effort", "low"],
    ["max_completion_tokens", "4096"], ["seed", "42"], ["timeout", "5초 (SDK 기본 60초)"],
    ["max_retries", "0 (SDK 기본 2회)"], ["include_reasoning", "false (extra_body)"],
    ["출력 형식", "json_schema, strict"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [2.6, rw - 2.6], rowH: 0.45, size: 14 });
  callout(s, "재시도는 반복 구간 L-1이 맡음. 연동 재시도까지 두면 최악값이 15초 예산을 넘음(설계서 20장)",
    { x: rx, y: 7.0, w: rw, h: 0.9, size: 14 });
}

// 18 S-R2 ③ 프롬프트와 응답 구조
async function createSlide18() {
  const s = newSlide({ title: "Ⅲ-5 S-R2 ③ 프롬프트와 응답 구조",
    lead: "유저 프롬프트는 XML 태그로 값을 감싸고, 응답은 strict JSON Schema로 6개 필드를 강제함(설계서 26장)" });
  const cw = 8.9;
  codePanel(s, "schema", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  const h = codePanel(s, "user_prompt", { x: rx, y: TOP, w: rw });
  cards(s, [["회원ID 없음", "유저 프롬프트 변수는 6개뿐. 회원 범위는 DB 세션 변수가 거름"],
    ["꺾쇠 바꾸기", "질문 속 & < >를 &amp; &lt; &gt;로 바꿔 </question> 같은 태그 끼워 넣기를 막음(_escape)"],
    ["시스템 프롬프트 고정", "prompts/c01_system_prompt.md 전문(8섹션)을 SystemMessage로 넣어 JSON 예시의 중괄호가 틀 변수로 읽히지 않게 함"]],
  { x: rx, y: TOP + h + 0.2, w: rw, h: 6.0 - h - 0.2, size: 14 });
}

// 19 S-R2 ④ 실패 분류와 키워드 규칙
async function createSlide19() {
  const s = newSlide({ title: "Ⅲ-6 S-R2 ④ 실패 분류와 키워드 규칙",
    lead: "LLM 호출 실패는 6종으로 나눠 기록만 하고, 모두 같은 대체 경로(키워드 규칙으로 정형쿼리 고르기)로 보냄",
    notes: "키워드 표 출처: app/domain/fixed_queries.py KEYWORD_RULES(설계서 30장)." });
  const cw = 9.0;
  codePanel(s, "groq_fail", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  darkBadge(s, "키워드 규칙 (fixed_queries.KEYWORD_RULES)", { x: rx, y: TOP, w: rw, h: 0.42 });
  table(s, [["정형쿼리", "질문에 이 말이 있으면"],
    ["FQ-01", "가입일, 연령"], ["FQ-02", "보유카드, 카드목록, 연회비"], ["FQ-03", "카드별 + (월 또는 사용)"],
    ["FQ-04", "월별, 월사용, 지난달, 이번달"], ["FQ-05", "업종, 가맹점, 어디서"], ["FQ-06", "연체 + 이력 표현 없음"],
    ["FQ-07", "연체 + (이력, 내역, 12개월 중 하나)"], ["FQ-08", "일별, 날짜별, 90일"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [1.2, rw - 1.2], rowH: 0.48, size: 14 });
  callout(s, "띄어쓰기를 지우고 비교함. 위에서부터 차례로 맞춰 처음 맞는 1개를 씀. 429의 retry-after는 기록만 하고 기다리지 않음",
    { x: rx, y: 6.9, w: rw, h: 1.0, size: 14 });
}

// 20 S-R3 ① 계획 판정
async function createSlide20() {
  const s = newSlide({ title: "Ⅲ-7 S-R3 ① 계획 판정 _judge",
    lead: "계획이 실제로 실행할 수 있는지 규칙으로 판정함. 정형쿼리는 등록된 SQL을 꺼내고, NL2SQL은 SQL과 대상 뷰를 확인" });
  const cw = 9.0;
  codePanel(s, "judge", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  const verdicts = [["FIT", "S-R4로 감. candidate_sql에 실행할 SQL", C.blue],
    ["UNFIT", "S-R2로 되돌아가 재계획(L-1). 이미 두 번째 계획이거나 시간이 모자라 재시도를 꺼 두었으면 UNANSWERABLE로 바꿈", C.navy],
    ["UNANSWERABLE", "S-R6으로 감. 오류가 아니라 '답할 수 없음' 정상 응답", C.dark]];
  verdicts.forEach(([v, d, f], i) => {
    const y = TOP + i * 1.2;
    card(s, v, { x: rx, y, w: 1.9, h: 1.05, fill: f, line: null, color: C.white, size: 15, bold: true });
    rr(s, { x: rx + 2.0, y, w: rw - 2.0, h: 1.05, fill: C.altRow });
    text(s, d, { x: rx + 2.1, y, w: rw - 2.2, h: 1.05, size: 14 });
  });
  darkBadge(s, "UNFIT 사유 코드 6종 → retry_reason", { x: rx, y: 5.65, w: rw, h: 0.42 });
  const codes = ["PLAN_FIELD_MISSING", "UNKNOWN_QUERY_ID", "EMPTY_SQL", "VIEW_NOT_ALLOWED", "INVALID_ROUTE", "INVALID_PERIOD"];
  const pw = (rw - 0.12) / 2;
  codes.forEach((c, i) => pill(s, c, { x: rx + (i % 2) * (pw + 0.12), y: 6.2 + Math.floor(i / 2) * 0.5, w: pw, h: 0.4, size: 14 }));
}

// 21 S-R3 ② 데이터 제공 기간
async function createSlide21() {
  const s = newSlide({ title: "Ⅲ-8 S-R3 ② 데이터 제공 기간",
    lead: "질문 기간(requested_period)이 대상 뷰의 제공 기간 안이고 기준일 이전인지 판정함. 기간 계산식은 뷰 정의 SQL에서 옮김" });
  const cw = 8.4;
  codePanel(s, "period", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  darkBadge(s, "예: 기준일 2026-08-31, 거래 제공 시작일 2025-08-01", { x: rx, y: TOP, w: rw, h: 0.42, size: 14 });
  table(s, [["뷰", "제공 기간"],
    ["monthly_usage", "2026-03-01 ~ 2026-08-31"], ["merchant_usage", "2026-03-01 ~ 2026-08-31"],
    ["customer_daily_usage", "2026-06-03 ~ 2026-08-31"], ["customer_delinquency_history", "2025-09-01 ~ 2026-08-31"],
    ["그 밖 3개 뷰", "기간 제한 없음(None)"]],
  { x: rx, y: TOP + 0.52, w: rw, colW: [3.15, rw - 3.15], rowH: 0.52, size: 14 });
  cards(s, [["기간 밖", "UNANSWERABLE(데이터 제공 기간 밖). 다시 계획해도 바뀌지 않아 재시도하지 않음"],
    ["재시도 소진", "UNFIT인데 attempt 2이거나 재시도를 껐으면 '다시 계획해도 실행할 수 있는 계획을 만들지 못함'"]],
  { x: rx, y: 5.7, w: rw, h: 2.2, size: 14 });
}

// 22 S-R4 ① SQL 검증 순서
async function createSlide22() {
  const s = newSlide({ title: "Ⅲ-9 S-R4 ① SQL 검증 순서",
    lead: "문자열 비교가 아니라 sqlglot 문법 트리로 검사함. 허용 목록에 있는 것만 통과시키는 기본 거부 방식(설계서 31장)" });
  const cw = 8.2;
  codePanel(s, "validate", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  table(s, [["순서", "검사", "실패 사유 코드"],
    ["1", "빈 SQL", "EMPTY_SQL"],
    ["2", "주석(토큰 단계)", "COMMENT_NOT_ALLOWED"],
    ["3", "세미콜론, 여러 문장", "MULTIPLE_STATEMENTS"],
    ["4", "쓰기와 구조 변경(하위 질의 포함)", "WRITE_NOT_ALLOWED"],
    ["5", "SELECT(WITH 포함)가 아님", "NOT_SELECT"],
    ["6", "UNION, 윈도 함수 등 목록 밖 구문", "SYNTAX_NOT_ALLOWED"],
    ["7", "FOR UPDATE 또는 SHARE, SELECT INTO", "FOR_UPDATE_NOT_ALLOWED, SELECT_INTO_NOT_ALLOWED"],
    ["8", "함수(허용 13개와 형변환만)", "FORBIDDEN_FUNCTION, FUNCTION_NOT_ALLOWED"],
    ["9", "스키마, 뷰, 컬럼", "SCHEMA_NOT_ALLOWED, VIEW_NOT_ALLOWED, COLUMN_NOT_ALLOWED"],
    ["통과", "LIMIT 200 맞춤", "ok = True"],
    ["공통", "토큰화 또는 파싱 실패", "PARSE_ERROR"]],
  { x: rx, y: TOP, w: rw, colW: [0.75, 2.4, rw - 3.15], rowH: 0.44, size: 14 });
}

// 23 S-R4 ② 뷰, 컬럼 검사와 LIMIT
async function createSlide23() {
  const s = newSlide({ title: "Ⅲ-10 S-R4 ② 뷰, 컬럼 검사와 LIMIT",
    lead: "WITH로 직접 만든 이름을 빼면 모든 표가 'app.'을 붙인 허용 뷰 7개 중 하나여야 하고, 컬럼은 그 뷰의 컬럼 목록 안이어야 함" });
  const cw = 10.0;
  codePanel(s, "tables", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  pill(s, "정형쿼리도 같은 검사를 거침(이중 안전장치)", { x: rx, y: TOP, w: rw, h: 0.45, size: 14 });
  cards(s, [["통과", "validated_sql(LIMIT 맞춘 SQL)과 row_limit 200 → S-R5"],
    ["정형쿼리 실패", "등록 오류로 보고 SQL_VALIDATION_FAILED + 운영 알림"],
    ["NL2SQL 실패, 재시도 남음", "retry_reason과 previous_sql을 담아 S-R2로(L-1)"],
    ["NL2SQL 실패, 재시도 없음", "이미 두 번째 계획이거나 시간이 모자라 재시도를 꺼 두었으면 SQL_VALIDATION_FAILED(422)"]],
  { x: rx, y: TOP + 0.6, w: rw, h: 5.4, title: "step_r4의 갈래", size: 14, headH: 0.62 });
}

// 24 S-R5 ① 읽기 전용 트랜잭션
async function createSlide24() {
  const s = newSlide({ title: "Ⅲ-11 S-R5 ① 읽기 전용 트랜잭션",
    lead: "모든 조회는 BEGIN READ ONLY로 시작해 ROLLBACK으로 끝냄. 세션 변수도 트랜잭션과 함께 지워짐" });
  const cw = 8.8;
  codePanel(s, "tx", { x: X0, y: TOP, w: cw });
  const { rx, rw } = right(cw);
  cards(s, [["접속 받기", "커넥션 풀(최소 1, 최대 4)에서 기다리는 시간도 남은 시간 예산 이하"],
    ["BEGIN READ ONLY", "쓰기를 DB가 막는 읽기 전용 트랜잭션"],
    ["statement_timeout", "남은 예산(ms)만큼 줌. 0은 '제한 없음'이라 최소 1ms"],
    ["본문", "세션 변수 지정 → SQL 실행 → 결과 받기"],
    ["ROLLBACK", "세션 변수까지 지우고 접속을 풀에 돌려줌"]],
  { x: rx, y: TOP, w: rw, h: 4.95, title: "_ReadOnlyTransaction 순서", size: 14 });
  callout(s, "예외 바꾸기: QueryCanceled → DatabaseTimeout, PoolTimeout과 그 밖 psycopg 오류 → DatabaseFailure",
    { x: rx, y: 7.05, w: rw, h: 0.85, size: 14 });
}

// 25 S-R5 ② 실행과 결과
async function createSlide25() {
  const s = newSlide({ title: "Ⅲ-12 S-R5 ② 실행과 결과",
    lead: "검증된 SQL을 회원 세션 변수를 건 트랜잭션에서 실행하고 최대 200행만 받음. 결과 0행은 오류가 아님" });
  const cw = 9.6;
  const h = codePanel(s, "execute", { x: X0, y: TOP, w: cw });
  codePanel(s, "r5", { x: X0, y: TOP + h + 0.15, w: cw });
  const { rx, rw } = right(cw);
  cards(s, [["세션 변수 다시 지정", "트랜잭션마다 새로 걸어야 행 수준 보안(RLS)이 그 회원 행만 보여 줌"],
    ["최대 200행", "fetchmany(row_limit). truncated = row_count ≥ row_limit"],
    ["JSON 값으로", "날짜는 ISO 문자열, 정수 Decimal은 int(_to_json_value)"],
    ["0행", "오류 아님. 잦으면 세션 변수 지정 누락을 먼저 의심(로그 zero rows)"]],
  { x: rx, y: TOP, w: rw, h: 4.85, size: 14 });
  callout(s, "실행 제한 시간 초과 → DB_TIMEOUT(504), 그 밖 DB 오류 → DB_ERROR(500)", { x: rx, y: 7.0, w: rw, h: 0.9,
    size: 14 });
}

// 26 S-R6 응답과 감사 로그
async function createSlide26() {
  const s = newSlide({ title: "Ⅲ-13 S-R6 응답과 감사 로그",
    lead: "결과와 '답할 수 없음'을 같은 응답 형식으로 만들고 감사 로그를 남김. 예산과 상관없이 항상 실행" });
  const cw = 8.6;
  const h = codePanel(s, "r6", { x: X0, y: TOP, w: cw });
  const h2 = codePanel(s, "message", { x: X0, y: TOP + h + 0.15, w: cw });
  const yb = TOP + h + h2 + 0.3;
  callout(s, "답할 수 없음 사유에 app.monthly_usage 같은 내부 뷰 이름이 있으면 지우고 씀(unanswerable_message)",
    { x: X0, y: yb, w: cw, h: 7.9 - yb, size: 14 });
  const { rx, rw } = right(cw);
  darkBadge(s, "응답 13개 필드 (SearchResponse)", { x: rx, y: TOP, w: rw, h: 0.42 });
  const fields = ["request_id", "status", "route", "query_id", "plan_source", "columns", "rows", "row_count", "truncated",
    "base_date", "coverage_start", "message", "elapsed_ms"];
  const pw = (rw - 0.24) / 3;
  fields.forEach((f, i) => pill(s, f, { x: rx + (i % 3) * (pw + 0.12), y: TOP + 0.55 + Math.floor(i / 3) * 0.48, w: pw,
    h: 0.38, size: 14 }));
  darkBadge(s, "감사 로그 1건 (logs/audit.jsonl)", { x: rx, y: 4.95, w: rw, h: 0.42 });
  rr(s, { x: rx, y: 5.45, w: rw, h: 2.45, fill: C.altRow });
  text(s, "- request_id, route, query_id, plan_source, attempt, elapsed_ms, row_count, status\n" +
    "- 질문은 가린 문장만, 회원ID는 SHA-256 해시만\n- 기록 실패해도 응답은 그대로 돌려주고 운영 알림만 남김",
  { x: rx + 0.15, y: 5.5, w: rw - 0.3, h: 2.35, size: 14, valign: "top" });
}

// 27 시험과 실측
async function createSlide27() {
  const s = newSlide({ title: "Ⅳ-1 시험과 실측",
    lead: "단위 시험은 가짜 객체로 261개, 통합 시험은 실제 DB와 Groq LLM으로 26개 통과(work/test_report.md, 2026-10-15)",
    notes: "단위 261건은 이 설명서 작성 중(2026-10-15) .venv에서 pytest -q로 다시 돌려 '261 passed'를 확인함. " +
      "통합 26건과 실측값은 work/test_report.md 기록을 옮김." });
  const lw = 8.4;
  darkBadge(s, "단위 시험 파일별 개수", { x: X0, y: TOP, w: lw, h: 0.42 });
  const rows = [["test_sql_validator", 58], ["test_domain_rules", 32], ["test_request_rules", 22], ["test_time_budget", 18],
    ["test_presentation", 17], ["test_steps_r3", 16], ["test_masking", 15], ["test_steps_r1", 15],
    ["test_settings_and_layers", 14], ["test_steps_r2", 13], ["test_groq_planner", 13], ["test_graph_flow", 11],
    ["test_steps_r5_r6", 11], ["test_steps_r4", 6]];
  const lab = 3.0, bmax = lw - lab - 0.75, rh = 0.395;
  rows.forEach(([name, n], i) => {
    const y = TOP + 0.52 + i * rh;
    text(s, name, { x: X0, y, w: lab, h: rh, size: 14, color: C.ink, align: "right" });
    box(s, { x: X0 + lab + 0.1, y: y + 0.07, w: (bmax * n) / 58, h: rh - 0.14, fill: i === 0 ? C.blue : C.pill, line: null });
    text(s, String(n), { x: X0 + lab + 0.15 + (bmax * n) / 58, y, w: 0.6, h: rh, size: 14, bold: true, color: C.navy });
  });
  const rx = X0 + lw + GAP, rw = XR - rx;
  const tiles = [["0.45 ~ 0.97초", "LLM 응답(통합 시험 8회)"], ["5ms", "회원 확인"], ["1 ~ 7ms", "정형쿼리(FQ-08만 302ms)"],
    ["15초", "전체 시간 예산(설계)"]];
  const tw = (rw - 0.2) / 2;
  tiles.forEach(([big, label], i) => {
    const x = rx + (i % 2) * (tw + 0.2), y = TOP + Math.floor(i / 2) * 1.3;
    rr(s, { x, y, w: tw, h: 1.15, fill: C.tint });
    text(s, big, { x, y: y + 0.05, w: tw, h: 0.6, size: 24, bold: true, color: C.blue, align: "center" });
    text(s, label, { x, y: y + 0.65, w: tw, h: 0.42, size: 14, color: C.navy, align: "center" });
  });
  cards(s, [["행 수준 보안", "같은 FQ-02가 M-1001은 1행, M-5001은 4행"],
    ["금지 SQL 차단", "금지 SQL만 내는 가짜 LLM + 실제 DB: 2회 모두 S-R4가 막아 422, DB 실행 0회"],
    ["실제 LLM 유도 질문", "app_internal 조회, set_config, DELETE 요구 3건 모두 UNANSWERABLE"]],
  { x: rx, y: 4.5, w: rw, h: 3.42, title: "통합 시험에서 확인한 것", size: 14, gap: 0.1, headH: 0.36 });
}

// 28 정리
async function createSlide28() {
  const s = newSlide({ title: "Ⅳ-2 정리 — 요청 한 건의 여정",
    lead: "단계마다 '검사 → 다음 단계'이며, 응답 어디에도 SQL 문장과 회원ID가 나가지 않음" });
  const steps = [["진입", "cli.py, api.py\nservices.py", "payload"], ["S-R1", "request_rules, masking\npostgres_repository", "가린 질문, 기준일"],
    ["S-R2", "groq_planner\nfixed_queries", "plan"], ["S-R3", "steps._judge\nperiods, catalog", "verdict, candidate_sql"],
    ["S-R4", "sql_validator\ncatalog", "validated_sql"], ["S-R5", "postgres_repository", "columns, rows"],
    ["S-R6", "messages, audit_log", "응답 13필드"], ["응답", "HTTP 200 또는\n오류 응답 5필드", "JSON"]];
  const w = (CW - 3 * 0.45) / 4, h = 2.35;
  steps.forEach(([t, files, out], i) => {
    const row = Math.floor(i / 4), col = i % 4;
    const x = X0 + col * (w + 0.45), y = TOP + row * (h + 0.55);
    const edge = i === 0 || i === 7;
    rr(s, { x, y, w, h, fill: C.white, line: edge ? C.navy : C.border, lw: edge ? 2 : 1 });
    card(s, t, { x, y, w, h: 0.48, fill: edge ? C.navy : i === 2 ? C.blue : C.tableHead, line: null,
      color: edge || i === 2 ? C.white : C.navy, size: 17, bold: true });
    text(s, files, { x: x + 0.1, y: y + 0.55, w: w - 0.2, h: 1.05, size: 14, color: C.body, align: "center" });
    pill(s, out, { x: x + 0.2, y: y + 1.75, w: w - 0.4, h: 0.42, size: 14 });
    if (col < 3) arrow(s, { x1: x + w, y1: y + h / 2, x2: x + w + 0.45, y2: y + h / 2, color: C.blue, width: 2 });
  });
  elbow(s, [[X0 + 3 * (w + 0.45) + w / 2, TOP + h], [X0 + 3 * (w + 0.45) + w / 2, TOP + h + 0.27], [X0 + w / 2, TOP + h + 0.27],
    [X0 + w / 2, TOP + h + 0.55]], { color: C.blue, width: 2 });
  callout(s, "LLM이 정하는 것은 계획(plan)뿐. 실행 여부는 S-R3 판정과 S-R4 검증이, 볼 수 있는 행은 DB 세션 변수와 RLS가 정함",
    { y: 7.35, h: 0.55 });
}

module.exports = [createSlide14, createSlide15, createSlide16, createSlide17, createSlide18, createSlide19, createSlide20,
  createSlide21, createSlide22, createSlide23, createSlide24, createSlide25, createSlide26, createSlide27, createSlide28];
