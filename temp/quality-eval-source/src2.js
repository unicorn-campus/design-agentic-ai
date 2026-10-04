const K = require("./common");
const { newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow, table, callout, codeBox, codePanel,
  cards, C, X0, CW, XR } = K;

const CODE_W = 9.5, RX = X0 + CODE_W + 0.25, RW = XR - RX;
const TOP = 1.95, H = 5.95;

// 16 F2 · F4
function p16() {
  const s = newSlide({ title: "Ⅳ-4 F2 색인 · F4 되돌리기 — _run_version",
    lead: "게시가 포인터를 새 세대로 바꾼 것을 확인하고 그 포인터를 버전 폴더에 저장 — F4는 finally 안이라 실패해도 반드시 지남" });
  codePanel(s, "run_version", { x: X0, y: TOP, w: CODE_W, h: H });
  cards(s, [
    ["게시 확인", "인덱서가 돌려준 세대 = 포인터의 세대여야 함(아니면 E-OUT)"],
    ["버전 포인터 저장", "active_generation.version.json — 이어 하기 때 F3 직전에 이 세대로 다시 돌려놓음"],
    ["F4 되돌리기", "검색 직후 기준 세대로 복원 — RAGAS · 검토표는 로그만 읽어 포인터가 필요 없음"],
    ["왜 바로 되돌리나", "게시는 '사용 중 세대 = 그 세대의 기준 세대'일 때만 통과 → 다음 버전 색인이 거부되지 않게"],
  ], { x: RX, y: TOP, w: RW, h: H, size: 13 });
}

// 17 하위 프로세스
function p17() {
  const s = newSlide({ title: "Ⅳ-5 하위 프로세스 호출 — _run",
    lead: "각 도구를 자기 가상환경 python으로 부르고 출력은 로그 파일로 남김 — 종료 코드를 실패 분류(StepError)로 바꿈" });
  codePanel(s, "subprocess", { x: X0, y: TOP, w: CODE_W, h: H });
  table(s, [
    ["분류", "언제", "실행기 동작"],
    ["E-CFG", "설정 검사 실패", "프로세스를 띄우지 않음"],
    ["E-EXIT", "종료 코드 ≠ 0", "그 단계 실패 → F4"],
    ["E-OUT", "결과 파일 · JSON 없음", "종료 코드 0이어도 실패"],
    ["E-INT", "종료 코드 130", "되돌린 뒤 종료"],
    ["E-TIME", "시간 상한 초과", "상한 기본 없음(결정 필요)"],
    ["E-API", "평가자 호출 실패", "그 버전 F5 실패"],
  ], { x: RX, y: TOP, w: RW, colW: [1.15, 1.95, RW - 3.1], rowH: 0.66, size: 13 });
  text(s, "환경변수는 지금 환경을 물려받고 바꿀 값만 얹음 — Windows에서 PATH · CUDA 변수를 빼면 python · torch가 뜨지 않음",
    { x: RX, y: 6.75, w: RW, h: 1.1, size: 13, color: C.sub, valign: "top" });
}

// 18 되돌리기 · 이어 하기
function p18() {
  const s = newSlide({ title: "Ⅳ-6 되돌리기 · 이어 하기 — _restore · _done",
    lead: "포인터가 백업과 다르면 되돌리고 다시 읽어 확인 — 이어 하기는 '성공이고 산출 파일이 실제로 있는' 단계만 건너뜀" });
  codePanel(s, "restore", { x: X0, y: TOP, w: CODE_W, h: 4.3 });
  rr(s, { x: X0, y: 6.4, w: CODE_W, h: 1.5, fill: C.tint });
  text(s, "백업은 처음 한 번만 씀 — 이어 하기에서 덮어쓰면 실험 세대를 '원래 값'으로 착각함\n실측: 두 계획 실행 전후 active_generation.json 내용이 같음",
    { x: X0 + 0.15, y: 6.45, w: CODE_W - 0.3, h: 1.4, size: 14, color: C.body });
  table(s, [
    ["state.json 상태", "--resume에서"],
    ["대기", "실행"],
    ["실행 중", "끊긴 것 — 그 단계부터 다시"],
    ["성공", "산출 파일이 있으면 건너뜀"],
    ["실패", "그 단계부터 다시"],
    ["미지원", "다시 검사"],
    ["건너뜀", "그대로(재색인 아닌 F2 등)"],
  ], { x: RX, y: TOP, w: RW, colW: [1.9, RW - 1.9], rowH: 0.62, size: 14 });
  text(s, "계획 파일이 바뀐 채 --resume하면 거부(계획 SHA-256 대조)", { x: RX, y: 6.5, w: RW, h: 0.8, size: 13, color: C.sub,
    valign: "top" });
}

// 19 코드 채점
function p19() {
  const s = newSlide({ title: "Ⅴ-1 코드 채점 — score_hits의 k",
    lead: "검색 리트리버 evaluate_retriever.py — k가 자르는 개수이자 Precision 분모. 인자를 안 주면 k = 5로 예전과 같음" });
  codePanel(s, "score_hits", { x: X0, y: TOP, w: CODE_W, h: 4.6 });
  table(s, [
    ["추가 인자", "기본값", "하는 일"],
    ["--top-k", "5", "첫 검색 · 워크플로우 요청의 top_k"],
    ["--metric-k / --fixed-k", "top_k / 5", "search 층 @k / 비교용 @5(search_fixed)"],
    ["--version-label · --config-snapshot", "없음", "버전 이름 · 적용 설정을 결과 머리에"],
  ], { x: X0, y: 6.7, w: CODE_W, colW: [3.4, 1.4, CODE_W - 4.8], rowH: 0.3, size: 13 });
  headerBar(s, "k를 키우면", { x: RX, y: TOP, w: RW, h: 0.42, size: 15, accent: true });
  [["k = 3", 3], ["k = 5", 5], ["k = 10", 10]].forEach(([lab, k], i) => {
    const y = TOP + 0.6 + i * 0.55;
    text(s, lab, { x: RX, y, w: 0.9, h: 0.42, size: 13, bold: true, color: C.navy });
    for (let j = 0; j < k; j++) box(s, { x: RX + 0.95 + j * 0.42, y: y + 0.05, w: 0.34, h: 0.34,
      fill: j === 1 || j === 6 ? C.blue : C.white, line: C.border });
  });
  rr(s, { x: RX, y: 4.35, w: RW, h: 3.55, fill: C.tint });
  text(s, "■ 정답 근거(2위 · 7위)\n\nPrecision@k = 1/3 → 1/5 → 2/10\n분모 탓에 내려감\n\n→ 버전 비교의 Δ는 @5(search_fixed)로만 계산, @k는 참고",
    { x: RX + 0.15, y: 4.4, w: RW - 0.3, h: 3.45, size: 14, color: C.body, valign: "top" });
}

// 20 RAGAS 입력
function p20() {
  const s = newSlide({ title: "Ⅴ-2 RAGAS 입력 · 제외 규칙",
    lead: "핵심 4지표가 읽는 칸을 표로 정해 두고, 채점할 수 없는 행은 사유 하나만 남기고 뺌 — 평균의 분모 = 채점한 행 수" });
  codePanel(s, "split_rows", { x: X0, y: TOP, w: CODE_W, h: H });
  const metrics = [["위", "context_precision", [1, 1, 1, 0]], ["정", "context_recall", [1, 1, 1, 0]],
    ["출", "faithfulness", [1, 0, 1, 1]], ["관", "answer_relevancy", [1, 0, 0, 1]]];
  const heads = ["질문", "정답", "근거", "답변"];
  const gx = RX + 2.4, cw = (RW - 2.4) / 4;
  heads.forEach((h, j) => text(s, h, { x: gx + j * cw, y: TOP, w: cw, h: 0.4, size: 13, bold: true, color: C.navy, align: "center" }));
  metrics.forEach(([b, m, reads], i) => {
    const y = TOP + 0.45 + i * 0.62;
    rr(s, { x: RX, y, w: RW, h: 0.54, fill: i < 2 ? C.altRow : C.tint, line: null });
    numBadge(s, b, { x: RX + 0.06, y: y + 0.08, size: 0.38, fill: i < 2 ? C.navy : C.blue, fsz: 13 });
    text(s, m, { x: RX + 0.5, y, w: 1.9, h: 0.54, size: 13, bold: true, color: C.ink });
    reads.forEach((r, j) => r && K.getPptx() && rr(s, { x: gx + j * cw + cw / 2 - 0.12, y: y + 0.15, w: 0.24, h: 0.24,
      fill: i < 2 ? C.navy : C.blue, line: null, r: 0.12 }));
  });
  table(s, [
    ["제외 사유(먼저 걸린 것 하나)", "조건"],
    ["no_answer_question", "답 없음 문항"],
    ["status_not_answered", "answered · retrieved가 아님"],
    ["empty_evidence", "근거 본문이 없음"],
    ["empty_response", "답변이 없음"],
  ], { x: RX, y: 4.9, w: RW, colW: [2.75, RW - 2.75], rowH: 0.56, size: 13 });
}

// 21 RAGAS 루프
function p21() {
  const s = newSlide({ title: "Ⅴ-3 RAGAS 채점 루프 — score_rows",
    lead: "(행 · 지표 · 회차)를 한꺼번에 띄우고 세마포어로 동시 호출 수만 묶음 — 칸 하나가 실패해도 전체를 멈추지 않음" });
  codePanel(s, "score_rows", { x: X0, y: TOP, w: CODE_W, h: H });
  headerBar(s, "호출 수 = 행 × 지표 × 반복", { x: RX, y: TOP, w: RW, h: 0.42, size: 15 });
  rr(s, { x: RX, y: TOP + 0.5, w: RW, h: 1.35, fill: C.tint });
  text(s, "예) 채점 행 11 × 4지표 × 3회 = 132칸\n동시 4개(RAGAS_CONCURRENCY)", { x: RX + 0.15, y: TOP + 0.55, w: RW - 0.3,
    h: 1.25, size: 14, color: C.body });
  cards(s, [
    ["문항별", "values · reasons와 평균 · 표준편차 · 최소 · 최대"],
    ["repeat_means", "회차마다 문항 평균 → 그 평균들의 최대 − 최소 = 흔들림 폭"],
    ["failed_scores", "실패 칸은 평균에서 빼고 {id, metric, repeat_index, error}로 남김"],
  ], { x: RX, y: 4.05, w: RW, h: 3.85, size: 13 });
}

// 22 평가자
function p22() {
  const s = newSlide({ title: "Ⅴ-4 평가자 연결 — build_llm",
    lead: "ragas 0.4.3 지표 묶음은 Instructor 형식 LLM만 받음 — 로컬 · Groq는 llm_factory, Claude만 전용 어댑터" });
  codePanel(s, "judge", { x: X0, y: TOP, w: CODE_W, h: H });
  table(s, [
    ["평가자", "연결", "특이점"],
    ["local", "Ollama OpenAI 호환 /v1", "reasoning_effort=\"none\"으로 사고를 끔(켜면 빈 답)"],
    ["groq", "OpenAI 호환 주소", "temperature 0"],
    ["anthropic", "AnthropicParseLLM", "다음 장 — 발췌에서 뺀 81 ~ 95행"],
  ], { x: RX, y: TOP, w: RW, colW: [1.05, 1.75, RW - 2.8], rowH: 0.8, size: 13 });
  rr(s, { x: RX, y: 5.35, w: RW, h: 2.55, fill: C.tint });
  text(s, "임베딩(AnswerRelevancy)은 평가자와 상관없이 KURE-v2 — HuggingFaceEmbeddings(revision 고정, 로컬 캐시만)\n\n지표 객체는 첫 채점 때 한 번 만듦",
    { x: RX + 0.15, y: 5.4, w: RW - 0.3, h: 2.45, size: 14, color: C.body, valign: "top" });
}

// 23 Claude 어댑터
function p23() {
  const s = newSlide({ title: "Ⅴ-5 Claude 평가자 어댑터 — AnthropicParseLLM",
    lead: "ragas가 요구하는 agenerate(prompt, 응답 모델)를 Anthropic SDK의 구조화 출력(messages.parse)으로 직접 구현" });
  codePanel(s, "anthropic", { x: X0, y: TOP, w: CODE_W, h: H });
  cards(s, [
    ["왜 따로 만들었나", "llm_factory의 Anthropic 경로는 temperature와 특정 도구 강제 호출을 보내는데 Claude Opus 5.5는 둘 다 400(실측)"],
    ["output_format", "응답 모델(pydantic)을 그대로 넘겨 검증된 parsed_output을 받음"],
    ["fallbacks=\"default\"", "안전 분류가 거절하면 서버가 대체 모델로 다시 돌림 — 끝내 거절이면 예외 → failed_scores"],
    ["effort medium", "판정 흔들림은 temperature 대신 effort와 반복 채점으로 다룸"],
  ], { x: RX, y: TOP, w: RW, h: H, size: 13 });
}

// 24 kappa
function p24() {
  const s = newSlide({ title: "Ⅴ-6 사람 검토표 일치도 — Agreement",
    lead: "사람 종합 판정(pass · fail)과 지표별 LLM 판정(점수 ≥ 0.5)을 2×2 표로 세고 F1 · kappa를 계산" });
  codePanel(s, "kappa", { x: X0, y: TOP, w: CODE_W, h: H });
  const gx = RX + 1.25, cw = (RW - 1.25) / 2, ch = 0.8;
  text(s, "사람 합격", { x: gx, y: TOP, w: cw, h: 0.4, size: 13, bold: true, color: C.navy, align: "center" });
  text(s, "사람 불합격", { x: gx + cw, y: TOP, w: cw, h: 0.4, size: 13, bold: true, color: C.navy, align: "center" });
  text(s, "LLM 합격", { x: RX, y: TOP + 0.45, w: 1.2, h: ch, size: 13, bold: true, color: C.navy });
  text(s, "LLM 불합격", { x: RX, y: TOP + 0.45 + ch, w: 1.2, h: ch, size: 13, bold: true, color: C.navy });
  [["TP 12", C.blue, C.white], ["FP 4", C.altRow, C.ink], ["FN 1", C.altRow, C.ink], ["TN 3", C.blue, C.white]]
    .forEach(([t, f, c], i) => card(s, t, { x: gx + (i % 2) * cw, y: TOP + 0.45 + Math.floor(i / 2) * ch, w: cw, h: ch,
      fill: f, line: C.white, color: c, size: 16, bold: true, r: 0.02 }));
  rr(s, { x: RX, y: 4.25, w: RW, h: 2.2, fill: C.tint });
  text(s, "교재 예시를 시험으로 고정(test_domain)\n일치율 0.75 · F1 0.83 · kappa 0.39\n\nchance ≥ 1(한쪽이 전부 같은 판정)이면 kappa = None",
    { x: RX + 0.15, y: 4.3, w: RW - 0.3, h: 2.1, size: 14, color: C.body, valign: "top" });
  text(s, "판정이 60건 미만이면 confidence = '참고값'. 지금 사람 판정은 0건", { x: RX, y: 6.6, w: RW, h: 0.8, size: 13,
    color: C.sub, valign: "top" });
}

// 25 비교표
function p25() {
  const s = newSlide({ title: "Ⅴ-7 비교표 판정 — CompareService.build",
    lead: "코드 지표는 @5 Δ의 부호로, RAGAS는 기준 버전 흔들림 폭과 비교해 판정 — 채점 행 수가 3 이상 다르면 ⚠" });
  codePanel(s, "compare", { x: X0, y: TOP, w: CODE_W, h: H });
  table(s, [
    ["지표", "조건", "판정"],
    ["코드(@5)", "Δ ≠ 0", "부호대로 개선 / 악화"],
    ["RAGAS", "|Δ| > 흔들림 폭", "개선 / 악화"],
    ["RAGAS", "|Δ| ≤ 흔들림 폭", "차이 없음"],
    ["두 채점 반대", "코드 ↑ · RAGAS ↓", "원인 확인"],
    ["평가셋 지문 다름", "—", "Δ 계산 안 함"],
  ], { x: RX, y: TOP, w: RW, colW: [1.7, 1.9, RW - 3.6], rowH: 0.66, size: 13 });
  rr(s, { x: RX, y: 6.2, w: RW, h: 1.7, fill: C.tint });
  text(s, "판정 함수는 domain/comparison.py(judge_code · judge_ragas · direction_match)\n흔들림 폭은 평가자 반복만 반영 — 리트리버 답변 생성의 흔들림은 들어 있지 않음",
    { x: RX + 0.12, y: 6.25, w: RW - 0.24, h: 1.6, size: 13, color: C.body, valign: "top" });
}

// 26 계획 파일 · 설정
function p26() {
  const s = newSlide({ title: "Ⅵ-1 계획 파일과 실행 명령",
    lead: "계획 파일 하나 = 하이퍼 파라미터 하나 — 평가셋 지문 · 평가자 · 반복 수를 함께 고정해 '같은 조건'을 지킴" });
  codePanel(s, "plan_yaml", { x: X0, y: TOP, w: CODE_W, h: H, size: 13 });
  codeBox(s, [
    "# 평가셋 준비",
    "python build_eval_set.py",
    "# 실행 전 검사만",
    "python run_experiments.py --plan plans/top_k.yaml --check-only",
    "# 기준 5 + 3만",
    "python run_experiments.py --plan plans/top_k.yaml --versions 3",
    "# 실패 · 끊긴 단계부터",
    "python run_experiments.py --plan plans/top_k.yaml --resume",
  ], { x: RX, y: TOP, w: RW, h: 4.0, size: 13, title: "실행 명령(가상환경 python)" });
  rr(s, { x: RX, y: 6.1, w: RW, h: 1.8, fill: C.tint });
  text(s, "실험 중에는 같은 data 폴더를 보는 검색 API 서버를 내림 — 떠 있으면 V14로 거부(종료 코드 2)",
    { x: RX + 0.15, y: 6.15, w: RW - 0.3, h: 1.7, size: 14, color: C.body });
}

// 27 설계서 대비
function p27() {
  const s = newSlide({ title: "Ⅵ-2 설계서와 달라진 점",
    lead: "소스는 품질평가 설계서를 따르되 실측 · 사용자 결정으로 바꾼 곳이 있음 — 이유는 README 8장에 기록" });
  table(s, [
    ["#", "설계서", "소스", "이유"],
    ["①", "실행기 eval-runner/ · 전용 .venv", "ragas/ 하나에 합침", "사용자 결정 — 실행기는 하위 프로세스만 불러 충돌 없음"],
    ["②", "RAGAS · 검토표도 하위 프로세스", "같은 가상환경 서비스로 직접 호출", "같은 .venv라 나눌 이유 없음"],
    ["③", "하위 프로세스에 필요한 키만", "환경을 물려받고 바꿀 값만 얹음", "Windows에서 PATH · CUDA가 빠지면 실행 불가"],
    ["④", "검증 ③은 평가셋만", "근거를 담은 색인 조각에서 숫자 대조", "원문 조각은 핵심 문장만이라 한도 숫자가 옆 칸에 있음"],
    ["⑤", "LangChain 사용(프롬프트)", "ragas llm_factory", "사용자 결정 — 지표 묶음이 LangChain 래퍼를 거부"],
    ["⑥", "retriever.json 머리에 세대", "config.json에 세대 · 복원 확인", "평가 스크립트를 더 고치지 않음"],
    ["⑦", "평가자 3종 llm_factory", "Claude만 AnthropicParseLLM", "Opus 5.5가 temperature · 강제 도구 호출을 거부"],
    ["⑧", "RAGAS 6지표", "핵심 4지표(위 · 정 · 출 · 관)", "사용자 결정 — 코드 채점 5지표는 그대로"],
  ], { y: TOP, colW: [0.5, 3.6, 4.2, 6.6], rowH: 0.64, size: 13 });
}

// 28 실측
function p28() {
  const s = newSlide({ title: "Ⅵ-3 실측과 시험",
    lead: "2026-10-04 — 평가셋 20/20 통과, 두 계획 모든 단계 성공, 실행 전후 포인터 같음 · 시험 48건 통과" });
  headerBar(s, "시험 파일별 건수(합계 48)", { x: X0, y: TOP, w: 7.3, h: 0.42, size: 15 });
  const bars = [["test_domain", 20], ["test_runner", 11], ["test_adapters", 10], ["test_services", 7]];
  bars.forEach(([n, v], i) => {
    const y = TOP + 0.65 + i * 0.7;
    text(s, n, { x: X0, y, w: 1.9, h: 0.5, size: 14, bold: true, color: C.ink });
    box(s, { x: X0 + 2.0, y: y + 0.05, w: 4.4 * v / 20, h: 0.4, fill: C.blue, line: null });
    text(s, String(v), { x: X0 + 2.05 + 4.4 * v / 20, y, w: 0.6, h: 0.5, size: 14, bold: true, color: C.navy });
  });
  text(s, "live 2건(실제 말뭉치 · 로컬 평가자) 포함 · 리트리버 192건 통과 · 새 가상환경 설치 후 45건 통과",
    { x: X0, y: 5.55, w: 7.3, h: 0.7, size: 13, color: C.sub, valign: "top" });
  const tiles = [["40분 43초", "청크 800 · 600", "재색인 38 · 42초"], ["36분 49초", "Top-k 5 · 3", "재색인 없음"],
    ["14 ~ 22분", "버전당 RAGAS", "당시 6지표 × 3회"], ["0.941", "기준 Hit@5", "Recall@5 0.912"]];
  const tx = X0 + 7.6, tw = (XR - tx - 0.2) / 2, th = 1.75;
  tiles.forEach(([big, label, sub], i) => {
    const x = tx + (i % 2) * (tw + 0.2), y = TOP + Math.floor(i / 2) * (th + 0.2);
    rr(s, { x, y, w: tw, h: th, fill: C.tint });
    text(s, big, { x, y: y + 0.12, w: tw, h: 0.7, size: 26, bold: true, color: C.blue, align: "center" });
    text(s, label, { x, y: y + 0.85, w: tw, h: 0.42, size: 15, bold: true, color: C.navy, align: "center" });
    text(s, sub, { x, y: y + 1.27, w: tw, h: 0.4, size: 13, color: C.slate, align: "center" });
  });
  callout(s, "같은 설정의 두 기준이 근거를 들고 끝난 문항 11 대 10 — 리트리버 답변 생성이 흔들림. 작은 RAGAS Δ는 다시 돌려 확인",
    { x: X0, y: 6.4, w: CW, h: 0.6, size: 14 });
  text(s, "로컬 평가자는 3회 반복이 모두 같은 값(흔들림 0) · 사람 판정은 아직 0건",
    { x: X0, y: 7.15, w: CW, h: 0.45, size: 13, color: C.sub });
}

// 29 정리
function p29() {
  const s = newSlide({ title: "정리 — 단계별 산출물",
    lead: "모든 단계가 '검사 → 파일로 남김 → 다음 단계'이고, 포인터는 어떤 길로 끝나도 원래 값으로 돌아옴" });
  const steps = [["평가셋", "eval-set.json", "build_eval_set.py"], ["F0", "_backup · state.json", "run"],
    ["F1", "config.json · 설정 복사본", "_apply"], ["F2", "새 세대 · version 포인터", "IndexerProcess"],
    ["F3", "retriever.json", "RetrieverEvalProcess"], ["F4", "pointer_restored", "_restore"],
    ["F5", "ragas.json", "RagasService"], ["F6", "review.csv", "ReviewService"], ["F7", "compare.md · .csv", "CompareService"]];
  const w = 1.5, gap = 0.18;
  steps.forEach(([n, out, who], i) => {
    const x = X0 + i * (w + gap);
    card(s, n, { x, y: 2.1, w, h: 0.6, fill: i === 5 ? C.blue : C.navy, line: null, color: C.white, size: 16, bold: true });
    rr(s, { x, y: 2.8, w, h: 1.6, fill: C.altRow });
    text(s, out, { x: x + 0.05, y: 2.85, w: w - 0.1, h: 1.5, size: 13, color: C.ink, bold: true, align: "center" });
    text(s, who, { x, y: 4.5, w, h: 0.7, size: 13, color: C.slate, align: "center", valign: "top" });
    if (i < steps.length - 1) arrow(s, { x1: x + w, y1: 2.4, x2: x + w + gap, y2: 2.4, color: C.blue, width: 1.5 });
  });
  cards(s, [
    ["같은 조건", "평가셋 지문 · 평가자 · 반복 수를 계획 파일에 고정, 다르면 거부하거나 Δ를 계산하지 않음"],
    ["되돌리기", "버전마다 검색 직후 · 종료 때 포인터 복원 확인"],
    ["이어 하기", "state.json + --resume, 색인은 같은 thread-id로 체크포인트 재개"],
  ], { x: X0, y: 5.45, w: CW, h: 2.45, size: 13, gap: 0.08 });
}

module.exports = [p16, p17, p18, p19, p20, p21, p22, p23, p24, p25, p26, p27, p28, p29];
