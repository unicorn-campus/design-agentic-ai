const K = require("./common");
const { newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow, table, callout, codeBox, codePanel,
  cards, C, X0, CW, XR } = K;

const CODE_W = 9.5, RX = X0 + CODE_W + 0.25, RW = XR - RX; // 표준 배치: 왼쪽 발췌 · 오른쪽 해설
const TOP = 1.95, H = 5.95;

// 1 한눈에 보기
function p01() {
  const s = newSlide({
    title: "품질평가 프로그램 한눈에 보기",
    lead: "계획 파일 하나로 재색인 → 검색 · 코드 채점 → 되돌리기 → RAGAS → 검토표 → 비교표를 돌리는 계층형 CLI 앱",
    notes: "대상 소스: hybrid-ai-lab/ragas(품질평가 프로그램)와 retriever/vector-retriever/evaluate_retriever.py(추가한 인자 5개).\n" +
      "숫자 출처: 시험 수는 pytest --collect-only, 실측은 README 7장(2026-10-04).",
  });
  const steps = [["평가셋 준비", "build_eval_set.py\nmd → json · 검증 5검사", C.navy], ["F0 준비", "검사 · 잠금 · 포인터 백업", C.navy],
    ["F1 ~ F6 버전마다", "설정 → 색인 → 검색 → 되돌리기\n→ RAGAS → 검토표", C.blue], ["F7 비교표", "compare.md · .csv", C.navy],
    ["종료", "포인터 재확인 · 잠금 해제", C.dark]];
  const w = 2.75, gap = 0.29;
  steps.forEach(([t, d, f], i) => {
    const x = X0 + i * (w + gap);
    card(s, t, { x, y: 2.0, w, h: 0.6, fill: f, line: null, color: C.white, size: 17, bold: true });
    rr(s, { x, y: 2.68, w, h: 1.2, fill: C.altRow });
    text(s, d, { x: x + 0.08, y: 2.7, w: w - 0.16, h: 1.16, size: 14, color: C.body, align: "center" });
    if (i < steps.length - 1) arrow(s, { x1: x + w, y1: 2.3, x2: x + w + gap, y2: 2.3, color: C.blue, width: 2 });
  });
  const tiles = [["5종", "실행 스크립트", "build · verify · ragas · review · run"], ["5 + 4", "코드 지표 + RAGAS 지표", "Hit·Recall·MRR·Precision·nDCG / 위·정·출·관"],
    ["9개", "포트(Protocol)", "파일 · 색인 · 평가자 · 하위 프로세스 · 포인터 …"], ["48건", "시험 통과", "live 2건 포함 · 리트리버 192건"]];
  const tw = (CW - 0.25 * 3) / 4;
  tiles.forEach(([big, label, sub], i) => {
    const x = X0 + i * (tw + 0.25);
    rr(s, { x, y: 4.25, w: tw, h: 2.2, fill: C.tint });
    text(s, big, { x, y: 4.35, w: tw, h: 0.85, size: 34, bold: true, color: C.blue, align: "center" });
    text(s, label, { x, y: 5.2, w: tw, h: 0.45, size: 17, bold: true, color: C.navy, align: "center" });
    text(s, sub, { x: x + 0.1, y: 5.65, w: tw - 0.2, h: 0.7, size: 13, color: C.slate, align: "center", valign: "top" });
  });
  callout(s, "원칙 3가지 — 같은 조건(평가셋 지문 · 평가자 고정) · 되돌리기(포인터 백업 → 복원) · 이어 하기(state.json · --resume)",
    { y: 6.8, h: 0.6 });
}

// 2 목차
function p02() {
  const s = newSlide({ title: "목차" });
  const parts = [["Ⅰ", "구조", ["디렉토리", "Layered Architecture", "DIP ① 포트 · ② 조립 · ③ 시험"]],
    ["Ⅱ", "공통 뼈대", ["진입 — CLI 하위 명령", "설정 읽기", "파일 어댑터"]],
    ["Ⅲ", "평가셋 준비", ["md → json 변환", "검증 5검사"]],
    ["Ⅳ", "버전 실험 실행기", ["계획 파일 검사", "실행 흐름 run", "F1 설정 적용 · F2 색인 · F4 되돌리기", "하위 프로세스 · 이어 하기"]],
    ["Ⅴ", "채점 · 비교", ["코드 채점 @k · @5", "RAGAS 입력 · 루프 · 평가자 · Claude 어댑터", "사람 검토표 일치도 · 비교표"]],
    ["Ⅵ", "설정 · 결과", ["계획 파일 · 설정", "설계서와 달라진 점", "실측과 시험 · 정리"]]];
  const w = 4.8, h = 2.85, gx = 0.25, gy = 0.25;
  parts.forEach(([n, t, items], i) => {
    const x = X0 + (i % 3) * (w + gx), y = 1.4 + Math.floor(i / 3) * (h + gy);
    rr(s, { x, y, w, h, fill: i % 2 ? C.altRow : C.tint });
    numBadge(s, n, { x: x + 0.2, y: y + 0.2, size: 0.55, fill: C.blue, fsz: 18 });
    text(s, t, { x: x + 0.9, y: y + 0.2, w: w - 1.0, h: 0.55, size: 21, bold: true, color: C.navy });
    text(s, items.map((v) => "· " + v).join("\n"), { x: x + 0.3, y: y + 0.95, w: w - 0.45, h: h - 1.05, size: 15,
      color: C.body, valign: "top" });
  });
}

// 3 디렉토리
function p03() {
  const s = newSlide({ title: "Ⅰ-1 디렉토리 구조", lead: "hybrid-ai-lab/ragas/ — 실행 스크립트 5개는 cli.py에 하위 명령 이름만 붙여 넘김" });
  codeBox(s, [
    "ragas/",
    "├─ build_eval_set.py · verify_eval_set.py      평가셋",
    "├─ evaluate_ragas.py · human_review.py         채점",
    "├─ run_experiments.py                          버전 실험",
    "├─ eval-set.md · eval-set.json                 평가셋 원본 · 기계용",
    "├─ plans/  chunk_size.yaml · top_k.yaml",
    "├─ experiments/  {하이퍼 파라미터}/{버전}/ · compare.md",
    "├─ app/",
    "│  ├─ domain/  text · eval_set · verification · plan · scoring · comparison",
    "│  ├─ application/  models · ports · eval_set_service · ragas_service",
    "│  │               review_service · compare_service · runner_service",
    "│  ├─ infrastructure/  settings · files · processes · ragas_judge",
    "│  │                  anthropic_llm",
    "│  ├─ presentation/cli.py",
    "│  └─ bootstrap.py",
    "├─ tests/  fakes · test_domain · test_services · test_runner · test_adapters",
    "└─ requirements*.txt · pytest.ini · .env.example · README.md",
  ], { x: X0, y: TOP, w: CODE_W, h: H, size: 14, title: "hybrid-ai-lab/ragas/ (캐시 · 가상환경 제외)" });
  table(s, [
    ["폴더", "한 줄 책임"],
    ["domain", "순수 규칙 — md 변환 · 검증 · 계획 검사 · 채점 집계 · 판정"],
    ["application", "DTO · 포트 · 서비스 5개(평가셋 · RAGAS · 검토표 · 비교표 · 실행기)"],
    ["infrastructure", "파일 · 포인터 · 잠금 · 말뭉치 · 하위 프로세스 · 평가자 LLM"],
    ["presentation", "명령행 하위 명령 → 서비스 호출 · 종료 코드"],
    ["bootstrap.py", "설정을 읽어 어댑터를 만들고 서비스에 끼움"],
    ["tests", "가짜 포트 주입 시험 + live 2건"],
  ], { x: RX, y: TOP, w: RW, colW: [1.75, RW - 1.75], rowH: 0.78, size: 14 });
}

// 4 계층
function p04() {
  const s = newSlide({ title: "Ⅰ-2 Layered Architecture",
    lead: "바깥(입구 · 기술)에서 안쪽(업무 규칙)으로만 import — 외부 기술은 infrastructure에만 있음" });
  const layers = [
    ["presentation", "cli.py — argparse 하위 명령 · 종료 코드", C.dark],
    ["application", "ports.py(포트 9개) · models.py · *_service.py 5개", C.blue],
    ["domain", "eval_set · verification · plan · scoring · comparison · text — 표준 라이브러리만", C.navy],
  ];
  layers.forEach(([n, d, f], i) => {
    const y = 2.0 + i * 1.55;
    card(s, n, { x: X0, y, w: 2.6, h: 1.25, fill: f, line: null, color: C.white, size: 18, bold: true });
    rr(s, { x: X0 + 2.75, y, w: 6.6, h: 1.25, fill: C.altRow });
    text(s, d, { x: X0 + 2.9, y, w: 6.3, h: 1.25, size: 15, color: C.body });
    if (i < 2) arrow(s, { x1: X0 + 1.3, y1: y + 1.25, x2: X0 + 1.3, y2: y + 1.55, color: C.blue, width: 2.5 });
  });
  const ix = X0 + 9.65, iw = XR - ix;
  card(s, "infrastructure", { x: ix, y: 2.0, w: iw, h: 0.6, fill: C.blue, line: null, color: C.white, size: 17, bold: true });
  rr(s, { x: ix, y: 2.7, w: iw, h: 2.65, fill: C.tint });
  text(s, "files · processes · ragas_judge\nanthropic_llm · settings\n\nragas · openai · anthropic · yaml ·\nsubprocess는 여기서만 import",
    { x: ix + 0.15, y: 2.75, w: iw - 0.3, h: 2.55, size: 14, color: C.body, valign: "top" });
  arrow(s, { x1: ix, y1: 3.8, x2: X0 + 9.35, y2: 3.6, color: C.blue, width: 2, dash: "dash" });
  text(s, "포트를 상속해 구현 →  application의 ports.py", { x: ix, y: 5.5, w: iw, h: 0.4, size: 13, color: C.blue, bold: true });
  card(s, "bootstrap.py — 어댑터 생성 · 주입은 여기 한 곳", { x: X0, y: 6.75, w: CW, h: 0.6, fill: C.white, size: 16,
    bold: true, color: C.navy });
  text(s, "시험이 계층 규칙을 강제함: domain · application에 외부 기술 import 없음, presentation은 infrastructure를 import하지 않음(test_adapters)",
    { x: X0, y: 7.45, w: CW, h: 0.45, size: 13, color: C.sub });
}

// 5 DIP ① 포트
function p05() {
  const s = newSlide({ title: "Ⅰ-3 DIP ① 응용 계층이 포트를 소유",
    lead: "ports.py가 '무엇이 필요한가'를 Protocol + @abstractmethod로 선언 — docstring이 입력 전제 · 반환 · 예외 · 부수효과 계약" });
  codePanel(s, "ports", { x: X0, y: TOP, w: CODE_W, h: H });
  table(s, [
    ["포트", "구현(infrastructure)"],
    ["ArtifactStorePort", "LocalArtifactStore"],
    ["CorpusPort", "ActiveCorpusReader"],
    ["JudgePort", "RagasJudge"],
    ["IndexerPort", "IndexerProcess"],
    ["RetrieverEvalPort", "RetrieverEvalProcess"],
    ["PointerPort", "ActivePointer"],
    ["LockPort", "RunnerLock"],
    ["ServerProbePort", "HttpServerProbe"],
    ["EnvironmentPort", "LocalEnvironment"],
  ], { x: RX, y: TOP, w: RW, colW: [2.55, RW - 2.55], rowH: 0.55, size: 14 });
  text(s, "어댑터는 포트를 명시적으로 상속 — 빠진 메서드는 객체를 만들 때 TypeError", { x: RX, y: 7.55, w: RW, h: 0.4,
    size: 13, color: C.sub });
}

// 6 DIP ② bootstrap
function p06() {
  const s = newSlide({ title: "Ⅰ-3 DIP ② 조립 지점 bootstrap",
    lead: "구현체 생성 · 주입은 create_services 한 곳에서만 — 서비스는 어떤 기술이 끼워졌는지 모름" });
  codePanel(s, "bootstrap", { x: X0, y: TOP, w: CODE_W, h: H });
  cards(s, [
    ["설정 읽기", "load_settings — 환경변수 > ragas/.env > hybrid-ai-lab/.env"],
    ["저장소 · 채점 서비스", "LocalArtifactStore 하나를 RAGAS · 검토표 · 비교표가 함께 씀"],
    ["평가자 공장", "create_judge_factory — 평가자 이름으로 RagasJudge를 만들 함수"],
    ["실행기", "포인터 · 잠금 · 인덱서 · 리트리버 · 서버 확인 어댑터를 RunnerService에 끼움"],
    ["늦게 올림", "평가자 LLM · KURE-v2는 첫 채점 때 만듦(도움말만 볼 때 빠름)"],
  ], { x: RX, y: TOP, w: RW, h: H, title: "조립 순서" });
}

// 7 DIP ③ 시험
function p07() {
  const s = newSlide({ title: "Ⅰ-3 DIP ③ 가짜 포트로 시험",
    lead: "포트 모양만 맞추면 끼울 수 있음 — 실행기 시험은 색인 · LLM 없이 '게시가 포인터를 바꾸는 것'까지 흉내 냄" });
  codePanel(s, "fake_indexer", { x: X0, y: TOP, w: 7.35, h: H });
  codePanel(s, "test_restore", { x: X0 + 7.55, y: TOP, w: CW - 7.55, h: 4.3 });
  rr(s, { x: X0 + 7.55, y: 6.4, w: CW - 7.55, h: 1.5, fill: C.tint });
  text(s, "base_seen이 [\"gen-base\", \"gen-base\"] → 두 번째 색인도 기준 세대에서 시작함\n= 버전마다 포인터를 되돌렸다는 증거(되돌리지 않으면 실제 인덱서는 게시를 거부함)",
    { x: X0 + 7.7, y: 6.45, w: CW - 7.85, h: 1.4, size: 14, color: C.body });
}

// 8 진입
function p08() {
  const s = newSlide({ title: "Ⅱ-1 진입 — CLI 하위 명령",
    lead: "실행 스크립트는 run_with([\"run\"])처럼 하위 명령만 붙여 main으로 넘김 — main은 서비스 호출과 종료 코드 변환만 함" });
  codePanel(s, "cli_main", { x: X0, y: TOP, w: CODE_W, h: H });
  table(s, [
    ["실행 스크립트", "하위 명령 → 서비스"],
    ["build_eval_set.py", "build → EvalSetService.build"],
    ["verify_eval_set.py", "verify → verify_file"],
    ["evaluate_ragas.py", "ragas → RagasService.score_file"],
    ["human_review.py", "review export · agree"],
    ["run_experiments.py", "run → RunnerService.run"],
    ["(-m app.presentation.cli)", "compare → rebuild_compare"],
  ], { x: RX, y: TOP, w: RW, colW: [2.45, RW - 2.45], rowH: 0.56, size: 13 });
  const codes = [["0", "정상"], ["1", "실행 오류"], ["2", "검사 거부"], ["130", "중단"]];
  const cw = (RW - 0.3) / 4;
  codes.forEach(([c, d], i) => {
    const x = RX + i * (cw + 0.1);
    card(s, c, { x, y: 6.25, w: cw, h: 0.6, fill: C.navy, line: null, color: C.white, size: 18, bold: true });
    text(s, d, { x, y: 6.9, w: cw, h: 0.4, size: 13, color: C.slate, align: "center" });
  });
  text(s, "종료 코드", { x: RX, y: 7.4, w: RW, h: 0.4, size: 13, color: C.sub });
}

// 9 설정
function p09() {
  const s = newSlide({ title: "Ⅱ-2 설정 읽기 — load_settings",
    lead: "dict를 뒤에서 덮어써 우선순위를 만듦 — 인자 > 환경변수 > ragas/.env > hybrid-ai-lab/.env > 기본값" });
  codePanel(s, "settings", { x: X0, y: TOP, w: CODE_W, h: 4.3 });
  const order = ["overrides(인자)", "os.environ", "ragas/.env", "hybrid-ai-lab/.env", "기본값"];
  const ow = (CODE_W - 0.2 * 4) / 5;
  order.forEach((t, i) => {
    const x = X0 + i * (ow + 0.2);
    card(s, t, { x, y: 6.55, w: ow, h: 0.75, fill: i === 0 ? C.blue : C.white, line: i === 0 ? null : C.border,
      color: i === 0 ? C.white : C.navy, size: 14, bold: true });
    if (i < 4) arrow(s, { x1: x + ow, y1: 6.92, x2: x + ow + 0.2, y2: 6.92 });
  });
  text(s, "← 앞이 이김", { x: X0, y: 7.4, w: 3, h: 0.4, size: 13, color: C.sub });
  table(s, [
    ["키", "기본값"],
    ["OLLAMA_BASE_URL", "http://localhost:11434/v1"],
    ["JUDGE_LOCAL_MODEL", "Qwen3.5-9B(GGUF Q4_K_M)"],
    ["JUDGE_ANTHROPIC_MODEL", "claude-opus-5-5"],
    ["JUDGE_GROQ_MODEL", "openai/gpt-oss-120b"],
    ["EMBED_MODEL · DEVICE", "nlpai-lab/KURE-v2 · auto"],
    ["RAGAS_CONCURRENCY", "4"],
    ["RETRIEVER_API_URLS", "http://127.0.0.1:8020"],
    ["PROCESS_TIMEOUT_SECONDS", "없음(결정 필요)"],
    ["비밀키", "CLAUDE_API_KEY · GROQ_API_KEY"],
  ], { x: RX, y: TOP, w: RW, colW: [2.55, RW - 2.55], rowH: 0.56, size: 13 });
}

// 10 파일 어댑터
function p10() {
  const s = newSlide({ title: "Ⅱ-3 파일 어댑터 — 원자적 쓰기와 잠금",
    lead: "모든 쓰기는 임시 파일 → fsync → 바꿔치기 — 끊겨도 반쯤 쓴 파일이 남지 않음. 포인터는 인덱서와 같은 게시 잠금을 잡고 바꿈" });
  codePanel(s, "atomic", { x: X0, y: TOP, w: CODE_W, h: H });
  cards(s, [
    ["LocalArtifactStore", "JSON · YAML · CSV 읽기 쓰기. CSV는 BOM을 붙여 엑셀 한글이 안 깨짐"],
    ["ActivePointer", "active_generation.json 읽기 · 원자적 교체 · SHA-256"],
    ["RunnerLock", "experiments/.runner.lock — 기다리지 않고 거부(실행기는 한 번에 하나)"],
    ["ActiveCorpusReader", "사용 중 세대의 corpus.jsonl → 검증용 Chunk 목록"],
  ], { x: RX, y: TOP, w: RW, h: H, title: "infrastructure/files.py" });
}

// 11 md → json
function p11() {
  const s = newSlide({ title: "Ⅲ-1 평가셋 변환 — md를 줄 단위로 읽음",
    lead: "정규식으로 줄 종류를 가르고 mode로 '들여쓴 불릿이 무엇인지' 기억함 — 순수 함수라 파일 · 색인 없이 시험 가능" });
  codePanel(s, "parse_md", { x: X0, y: TOP, w: CODE_W, h: H });
  const rows = [["### Q01. 질문", "id · question"], ["- **정답**: …", "ground_truth · answerable"], ["- **근거**: `파일` · 위치", "relevance[] 단위 1개"],
    ["  - 「원문 조각」", "그 단위의 any_of[]"], ["- **filters**: `[…]`", "filters(그대로)"], ["  - 낱말 + 낱말", "no_answer_terms[][]"]];
  headerBar(s, "md 줄 → json 칸", { x: RX, y: TOP, w: RW, h: 0.42, size: 15 });
  rows.forEach(([a, b], i) => {
    const y = TOP + 0.55 + i * 0.86;
    card(s, a, { x: RX, y, w: 2.5, h: 0.7, fill: C.white, size: 13, color: C.ink, align: "left" });
    arrow(s, { x1: RX + 2.5, y1: y + 0.35, x2: RX + 2.8, y2: y + 0.35, color: C.blue, width: 2 });
    card(s, b, { x: RX + 2.8, y, w: RW - 2.8, h: 0.7, fill: C.tint, size: 13, color: C.navy, bold: true });
  });
  text(s, "정답이 「확인 필요」로 시작하면 answerable=False · 근거를 비움", { x: RX, y: 7.5, w: RW, h: 0.4, size: 13, color: C.sub });
}

// 12 검증
function p12() {
  const s = newSlide({ title: "Ⅲ-2 평가셋 검증 — 색인 조각과 대조",
    lead: "검사가 하나라도 실패하면 eval-set.json을 쓰지 않음 — 리트리버 채점과 같은 정규화(NFKC · 공백 제거)로 비교" });
  codePanel(s, "check_index", { x: X0, y: TOP, w: CODE_W, h: H });
  cards(s, [
    ["① 글자 대조", "원문 조각이 지정 출처 조각에 그대로 있나"],
    ["② 카드 블록", "조각 앞쪽의 마지막 D2-Cxxx-Byy가 위치와 같은가"],
    ["③ 숫자 대조", "정답의 숫자가 근거를 담은 색인 조각에 있나"],
    ["④ 답 없음", "낱말 묶음을 모두 담은 조각이 없어야 함"],
    ["⑤ 구조", "check_structure — id 중복 · 필수 칸 · 위치 꼴"],
  ], { x: RX, y: TOP, w: RW, h: 5.2, size: 13 });
  card(s, "실측: 20문항 실패 0 · 지문 253f89d84905", { x: RX, y: 7.3, w: RW, h: 0.6, fill: C.blue, line: null,
    color: C.white, size: 15, bold: true });
}

// 13 계획 검사
function p13() {
  const s = newSlide({ title: "Ⅳ-1 계획 파일 검사 — check_plan",
    lead: "실행 전에 (거부 사유, 미지원 사유)를 돌려줌 — 범위 밖 값은 재색인 전에 거부해야 포인터가 덮어써지지 않음" });
  codePanel(s, "check_plan", { x: X0, y: TOP, w: CODE_W, h: H });
  headerBar(s, "거부 → 종료 코드 2", { x: RX, y: TOP, w: RW, h: 0.42, size: 15 });
  rr(s, { x: RX, y: TOP + 0.5, w: RW, h: 2.4, fill: C.tint });
  text(s, "V1 이름 없음 · V2 기준 값 없음\nV3 id 겹침 · V4 apply · 대상 꼴\nV10 · V11 범위 밖(청크 ≤ 800, top_k 1 ~ 10)",
    { x: RX + 0.15, y: TOP + 0.55, w: RW - 0.3, h: 2.3, size: 14, color: C.body, valign: "top" });
  headerBar(s, "미지원 → 그 계획만 건너뜀", { x: RX, y: 4.95, w: RW, h: 0.42, size: 15, accent: true });
  rr(s, { x: RX, y: 5.45, w: RW, h: 2.45, fill: C.white });
  text(s, "V7-1 defaults가 아닌 설정 키\nV9 code: 표기(아직 못 꺼낸 코드 값)\n\nV5 · V6 평가셋 · V8 · V9 도구 지원 · V14 서버는\n파일 · 프로세스를 봐야 해서 서비스가 검사",
    { x: RX + 0.15, y: 5.5, w: RW - 0.3, h: 2.35, size: 14, color: C.body, valign: "top" });
}

// 14 run
function p14() {
  const s = newSlide({ title: "Ⅳ-2 실행 흐름 — run",
    lead: "잠금 · 백업 뒤 기준 버전부터 _run_version을 돌림 — finally가 성공 · 실패 · 중단 어디서든 포인터를 재확인하고 잠금을 놓음" });
  codePanel(s, "run", { x: X0, y: TOP, w: CODE_W, h: H });
  const flow = [["F0", "검사 · 잠금 · 백업"], ["F1", "설정 적용"], ["F2", "색인(재색인만)"], ["F3", "검색 · 코드 채점"],
    ["F4", "되돌리기"], ["F5", "RAGAS"], ["F6", "검토표"], ["F7", "비교표"]];
  flow.forEach(([n, t], i) => {
    const y = TOP + i * 0.67;
    const loop = i >= 1 && i <= 6;
    numBadge(s, n, { x: RX, y, size: 0.55, fill: i === 4 ? C.blue : (loop ? C.navy : C.dark), fsz: 14 });
    card(s, t, { x: RX + 0.68, y, w: RW - 0.68, h: 0.55, fill: loop ? C.tint : C.white, size: 15, color: C.navy,
      bold: i === 4, align: "left" });
  });
  text(s, "F1 ~ F6 = 버전마다(_run_version) · 자동 재시도 0회", { x: RX, y: 7.45, w: RW, h: 0.4, size: 13, color: C.sub });
}

// 15 F1
function p15() {
  const s = newSlide({ title: "Ⅳ-3 F1 설정 적용 — _apply",
    lead: "바꾸는 종류별로 '하위 프로세스에 줄 값'만 만듦 — 원본 .env · config/는 열지 않거나 읽기만 함" });
  codePanel(s, "apply", { x: X0, y: TOP, w: CODE_W, h: H });
  cards(s, [
    ["config(설정 파일)", "원본을 읽어 대상 키만 바꾼 복사본을 버전 폴더에 씀 → POLICIES_PATH로 절대 경로 전달. 2곳 이상 다르면 E-CFG"],
    ["env(환경변수)", "인덱서 또는 리트리버 환경변수 묶음에 키 = 값을 얹음"],
    ["code_arg(인자)", "retriever_args에 ['--top-k', '3']처럼 더함"],
    ["기본으로 주는 값", "DATA_ROOT(인덱서 data) · AUDIT_LOG_PATH(버전 폴더 logs/)"],
  ], { x: RX, y: TOP, w: RW, h: H, size: 13 });
}

module.exports = [p01, p02, p03, p04, p05, p06, p07, p08, p09, p10, p11, p12, p13, p14, p15];
