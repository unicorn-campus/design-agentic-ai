const L = require("./lib");
const { newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow, hline, table, callout, codeBox,
  C, X0, CW, XR } = L;

// S11 ② 설정 적용 — 적용기 3종
function s11() {
  const s = newSlide({
    title: "② 설정 적용 — 적용기 3종",
    lead: "원본(.env · config/ · 사용 중 세대)은 바꾸지 않음 — 바꾸는 값은 하위 프로세스에 준 값 또는 버전 폴더의 복사본뿐",
    notes: "소스 확인: 리트리버 settings는 환경변수가 .env보다 먼저(빈 문자열로 값을 지울 수는 없음). 인덱서 load_settings도 환경변수가 .env를 이김.\n" +
      "인덱서는 POLICIES_PATH · PROFILES_PATH · METADATA_SCHEMA_PATH · CARD_ALIAS_RULES_PATH · CARD_ALIAS_OVERRIDES_PATH로 설정 파일 경로를 바꿀 수 있음.\n" +
      "상대 경로는 인덱서 앱 루트 기준으로 풀리므로 복사본 경로는 절대 경로로 넘김. 교재 CHROMA_PATH 방식은 소스에 없어 env로 세대를 바꿀 수 없음.",
  });
  const cols = [
    { k: "env", t: "환경변수", when: "도구가 이미 환경변수로 읽는 값\n예) GRADE_* · HYBRID_* · GROQ_MODEL",
      how: "하위 프로세스에 넘길 환경변수 묶음에만 키 = 값을 얹음", guard: ".env 파일을 열지도 쓰지도 않음",
      re: "아니요 — 프로세스만 새로 띄움", ex: "(이번 버전안에는 없음)" },
    { k: "config", t: "설정 파일", when: "값이 인덱서 설정 파일 안에 있음\n예) document_policies.json",
      how: "원본을 버전 폴더에 복사 → 대상 키만 덮어씀 → POLICIES_PATH로 복사본 경로를 넘김", guard: "원본은 읽기만 · 쓰기는 버전 폴더 안에서만",
      re: "예 — 처리 규칙 지문이 바뀜", ex: "청크 크기 600 · 800" },
    { k: "code_arg", t: "코드 값 → 인자", when: "값이 코드에 박혀 있음\n예) evaluate_retriever.py top_k=5",
      how: "기존 도구에 인자를 추가해 꺼냄(--top-k). 기본값은 지금과 같게", guard: "인자를 안 주면 지금과 같은 결과",
      re: "아니요", ex: "Top-k 3 · 5 · 10" },
    { k: "미지원", t: "아직 못 꺼낸 값", when: "RRF k · 후보 배수 · BM25 k1 · b · 유형별 청크 크기",
      how: "적용하지 않고 상태 '미지원'으로 적은 뒤 건너뜀", guard: "—", re: "—", ex: "—" },
  ];
  const w = 3.55, gap = 0.233, y0 = 1.95;
  const rows = [["언제", "when", 1.05], ["어떻게", "how", 1.05], ["원본 보호", "guard", 0.8], ["재색인", "re", 0.6], ["이번 예", "ex", 0.6]];
  cols.forEach((c, i) => {
    const x = X0 + i * (w + gap), last = i === 3;
    card(s, c.k + "  ·  " + c.t, { x, y: y0, w, h: 0.55, fill: last ? C.dark : (i === 1 ? C.blue : C.navy), line: null,
      color: C.white, size: 17, bold: true, r: 0.06 });
    let y = y0 + 0.65;
    rows.forEach(([label, key, h]) => {
      rr(s, { x, y, w, h, fill: last ? C.white : (key === "ex" ? C.tint : C.altRow), dash: last ? "dash" : undefined });
      text(s, label, { x: x + 0.1, y: y + 0.02, w: 1.1, h: 0.34, size: 14, bold: true, color: C.sub, valign: "top" });
      text(s, c[key], { x: x + 0.1, y: y + 0.3, w: w - 0.2, h: h - 0.32, size: 14, color: key === "ex" ? C.navy : C.body,
        bold: key === "ex", valign: "top" });
      y += h + 0.1;
    });
  });
  // 아래 흐름
  const fy = 7.25, fh = 0.62;
  const flow = ["계획 파일의 값", "적용기 선택(apply)", "환경변수 묶음 · 설정 복사본 경로 · 추가 인자", "하위 프로세스 실행", "config.json에 기록"];
  const fw = [2.2, 2.5, 4.6, 2.4, 2.4];
  let fx = X0;
  flow.forEach((t, i) => {
    card(s, t, { x: fx, y: fy, w: fw[i], h: fh, fill: i === 2 ? C.tint : C.white, size: 14, bold: i === 2, color: C.navy });
    if (i < flow.length - 1) arrow(s, { x1: fx + fw[i], y1: fy + fh / 2, x2: fx + fw[i] + 0.2, y2: fy + fh / 2 });
    fx += fw[i] + 0.2;
  });
}

// S12 ② 대상 키 표기 · 범위 검사
function s12() {
  const s = newSlide({
    title: "② 대상 키 표기 · 범위 검사",
    lead: "대상 키는 한 줄 주소로 적고, 도구가 오류로 죽기 전에 실행기가 먼저 범위를 검사함 — 기본은 거부",
    notes: "범위 값은 모두 소스의 검사 값을 옮김: 인덱서 SplitPolicy(오버랩 < 청크) · load_settings(청크 ≤ EMBED_MAX_TOKENS),\n" +
      "리트리버 settings의 number · count 범위, SearchRequest top_k 1 ~ 10. 도구 이름 4개 · 점 표기는 설계 가정.",
  });
  table(s, [
    ["형식", "뜻", "예"],
    ["{도구}:config:{파일}#{JSON 경로}", "설정 파일 안의 키", "indexer:config:config/document_policies.json#defaults.chunk_size"],
    ["{도구}:env:{환경변수}", "환경변수", "retriever:env:GRADE_MIN_GAP"],
    ["{도구}:arg:{인자}", "명령 인자", "retriever:arg:--top-k"],
    ["{도구}:code:{파일}#{식별자}", "아직 못 꺼낸 코드 값 → 미지원", "retriever:code:steps.py#rrf_k"],
  ], { y: 1.95, colW: [4.2, 3.4, 7.3], rowH: 0.5, size: 15 });
  text(s, "도구 이름은 indexer · retriever · ragas · review 4개로 고정(설계 가정)", { x: X0, y: 4.5, w: CW, h: 0.38, size: 14, color: C.sub });
  table(s, [
    ["대상 키", "허용 범위", "벗어나면"],
    ["indexer … #defaults.chunk_size", "1 이상, 임베딩 입력 상한(800) 이하", "거부"],
    ["indexer … #defaults.chunk_overlap", "0 이상, 청크 크기 미만", "거부"],
    ["retriever:arg:--top-k", "1 ~ 10 (후보 수 = top_k × 2 × 4, 융합 top_k × 2)", "거부"],
    ["retriever:env:GRADE_* · HYBRID_*_WEIGHT", "0.0 ~ 1.0", "거부"],
    ["retriever:env:MAX_TURNS · MAX_LLM_CALLS · MAX_REWRITES", "1 ~ 50 · 1 ~ 200 · 0 ~ 10", "거부"],
  ], { y: 4.95, colW: [5.6, 7.1, 2.2], rowH: 0.48, size: 15 });
}

// S13 ③ 실행 — 하위 프로세스 호출 규격
function s13() {
  const s = newSlide({
    title: "③ 실행 — 하위 프로세스 호출 규격",
    lead: "각 도구는 자기 가상환경의 python으로, 자기 폴더에서 실행함 — 성공 = 종료 코드 0 그리고 결과 파일이 있음",
    notes: "인덱서: thread_id를 stderr 첫 줄에, 결과 JSON을 stdout에, 종료 코드 0 · 130(중단) · 1(오류)(presentation/cli.py).\n" +
      "리트리버 evaluate_retriever.py는 인자 3개(--questions · --generate-answer · --out)뿐 — 추가 인자는 ④ 코드 채점 참고.\n" +
      "RAGAS · 검토표 도구와 ragas/.venv는 지금 없음(새로 만듦, ragas==0.4.3 + langchain-community<0.4).\n" +
      "AUDIT_LOG_PATH를 버전 폴더로 돌리는 것은 감사 로그가 버전끼리 섞이지 않게 하려는 설계 가정.",
  });
  table(s, [
    ["항목", "인덱서", "리트리버 평가", "RAGAS 채점", "검토표"],
    ["python", "indexer/vector-bm25/.venv", "retriever/vector-retriever/.venv", "ragas/.venv(새로 만듦)", "ragas/.venv"],
    ["명령", "run_indexer.py --full-reindex --thread-id {ID}", "evaluate_retriever.py --questions … --generate-answer --out … --top-k N",
      "evaluate_ragas.py --log {retriever.json} --repeat 3 --out …", "human_review.py export · agree"],
    ["주는 환경변수", "POLICIES_PATH(복사본 절대 경로)", "DATA_ROOT · GROQ_API_KEY · env 대상 키 · AUDIT_LOG_PATH", "평가자 API 키(필요할 때만)", "없음"],
    ["성공 판정", "종료 코드 0 + stdout JSON", "종료 코드 0 + --out 파일", "종료 코드 0 + 결과 JSON", "종료 코드 0 + CSV"],
    ["결과", "새 세대 · 포인터 갱신", "retriever.json", "ragas.json", "review.csv"],
    ["이어 하기", "같은 thread-id → 체크포인트부터", "없음 — 처음부터", "없음 — 처음부터", "없음"],
  ], { y: 1.95, colW: [1.9, 3.4, 3.6, 3.2, 2.8], rowH: 0.7, size: 14 });
  const chips = ["각 .venv의 python을 직접 부름", "환경변수는 필요한 키만 골라 넘김", "작업 폴더 = 각 도구 폴더",
    "표준 입력은 닫음", "출력 글자는 데이터로만 읽음"];
  const cw = (CW - 0.2 * 4) / 5;
  chips.forEach((t, i) => pill(s, t, { x: X0 + i * (cw + 0.2), y: 7.3, w: cw, h: 0.5, size: 14 }));
}

// S14 ③ 세대 지정 · 되돌리기
function s14() {
  const s = newSlide({
    title: "③ 세대 지정 · 되돌리기",
    lead: "리트리버는 사용 중 세대 포인터 파일 하나만 읽음 — 실행 전에 백업하고, 버전마다 검색이 끝나면 바로 복원함",
    notes: "사용자 결정 D3. 포인터 = indexer/vector-bm25/data/active_generation.json(리트리버 index_store POINTER_NAME).\n" +
      "게시 거부 조건: 게시 직전 사용 중 세대가 그 세대의 base_generation 또는 자기 자신이어야 통과(index_repository 게시 검사).\n" +
      "복원도 인덱서와 같은 방식(임시 파일 → 원자적 교체, .publish.lock 함께 잡음). 백업은 data/ 밖(실험 폴더)에 둠.",
  });
  const steps = [
    ["기준 확인", "포인터가 기준 세대인가"], ["백업", "_backup에 복사 + 해시 기록"], ["재색인", "base = 기준 세대로 기록됨"],
    ["게시", "포인터 → 새 세대"], ["검색 · 코드 채점", "포인터 그대로 둠"], ["복원", "백업을 원자적으로 되돌려 씀"],
    ["복원 확인", "해시 = 백업 해시 · 세대 폴더 있음"],
  ];
  const w = 1.92, gap = 0.21, y = 2.0;
  steps.forEach(([t, d], i) => {
    const x = X0 + i * (w + gap);
    const hl = i === 5 || i === 6;
    numBadge(s, i + 1, { x: x + w / 2 - 0.22, y, size: 0.44, fill: hl ? C.blue : C.navy });
    card(s, t, { x, y: y + 0.55, w, h: 0.55, fill: hl ? C.blue : C.white, line: hl ? null : C.border,
      color: hl ? C.white : C.navy, size: 15, bold: true });
    text(s, d, { x, y: y + 1.15, w, h: 0.75, size: 14, color: C.slate, align: "center", valign: "top" });
    if (i < steps.length - 1) arrow(s, { x1: x + w, y1: y + 0.82, x2: x + w + gap, y2: y + 0.82 });
  });
  // 포인터 상태 띠
  const by = 4.05;
  box(s, { x: X0, y: by, w: 3 * (w + gap) - gap + (w + gap) * 0, h: 0.4, fill: C.tableHead, line: null });
  text(s, "포인터 = 기준 세대", { x: X0, y: by, w: 3 * (w + gap) - gap, h: 0.4, size: 14, bold: true, color: C.navy, align: "center" });
  box(s, { x: X0 + 3 * (w + gap), y: by, w: 2 * (w + gap) - gap, h: 0.4, fill: C.blue, line: null });
  text(s, "포인터 = 실험 세대 (가장 짧게)", { x: X0 + 3 * (w + gap), y: by, w: 2 * (w + gap) - gap, h: 0.4, size: 14, bold: true,
    color: C.white, align: "center" });
  box(s, { x: X0 + 5 * (w + gap), y: by, w: 2 * (w + gap) - gap, h: 0.4, fill: C.tableHead, line: null });
  text(s, "포인터 = 기준 세대", { x: X0 + 5 * (w + gap), y: by, w: 2 * (w + gap) - gap, h: 0.4, size: 14, bold: true, color: C.navy, align: "center" });

  headerBar(s, "왜 버전마다 바로 복원하나", { x: X0, y: 4.75, w: 7.3, h: 0.46, size: 16, accent: true });
  rr(s, { x: X0, y: 5.28, w: 7.3, h: 2.6, fill: C.tint });
  text(s, "· 게시는 '사용 중 세대 = 그 세대를 만들 때의 기준 세대'일 때만 통과함 → 복원 없이 다음 버전을 색인하면 게시가 거부됨\n" +
    "· RAGAS · 검토표는 retriever.json만 읽어 포인터가 필요 없음 → 검색 직후 복원하면 실험 세대가 노출되는 시간이 가장 짧음",
    { x: X0 + 0.15, y: 5.35, w: 7.0, h: 2.45, size: 17, color: C.body, valign: "top" });
  headerBar(s, "어긋났을 때", { x: X0 + 7.6, y: 4.75, w: 7.3, h: 0.46, size: 16 });
  table(s, [
    ["경우", "대응"],
    ["색인 중 중단(130)", "게시 전이면 포인터 그대로 → 확인만"],
    ["평가 중 Ctrl+C", "하위 프로세스를 끝내고 복원을 반드시 거침"],
    ["복원 자체 실패", "백업 경로 · 기준 세대 이름을 화면과 state.json에 남기고 오류 종료"],
    ["실행기 강제 종료", "다음 실행의 ① 기준 확인에서 걸러 냄"],
  ], { x: X0 + 7.6, y: 5.28, w: 7.3, colW: [2.3, 5.0], rowH: 0.52, size: 14 });
}

// S15 ③ 세대 이름 · 동시 실행 · 운영 영향
function s15() {
  const s = newSlide({
    title: "③ 세대 이름 · 동시 실행 · 운영 영향",
    lead: "버전마다 thread-id를 달리 줘서 세대를 나누고, 포인터가 실험 세대인 동안 다른 쪽이 끼어들지 못하게 막음",
    notes: "세대 이름 규칙은 인덱서 indexing_service(안전 이름 + 원본 thread-id의 SHA-256 앞 8자).\n" +
      "--full-reindex가 체크포인트 내용을 지우는지는 확인 필요 — 확인 전에는 처음부터 다시 돌릴 때 새 thread-id를 기본으로 함.\n" +
      "리트리버는 포인터를 요청마다 다시 읽고 세대가 바뀌면 배경에서 새 세대를 올려 다음 요청부터 씀(index_store acquire) — 사용자 결정 D7.",
  });
  table(s, [
    ["항목", "규칙"],
    ["thread-id", "exp-{하이퍼 파라미터}-{버전}-{실행일자}  예) exp-chunk_size-600-20261004(설계 가정)"],
    ["세대 이름", "gen-{thread-id}-{thread-id 해시 8자}  → 색인 성공 직후 state.json · config.json에 기록"],
    ["이어서 끝낼 때", "state.json의 같은 thread-id를 다시 줌 → 인덱서 체크포인트부터 재개"],
    ["처음부터 다시", "실행일자를 바꾼 새 thread-id(설정이 바뀐 채 같은 ID면 인덱서가 거부)"],
  ], { y: 1.95, colW: [2.6, 12.3], rowH: 0.52, size: 15 });
  table(s, [
    ["잠금", "막는 구간", "누가"],
    ["data/.writer.lock", "색인 실행 전체", "인덱서(있음)"],
    ["data/.publish.lock", "포인터 교체 순간", "인덱서(있음) · 복원 때 실행기도 잡음"],
    ["experiments/.runner.lock", "백업 → 색인 → 검색 → 복원 확인까지", "실행기(새로 만듦)"],
  ], { x: X0, y: 4.85, w: 8.6, colW: [2.9, 3.2, 2.5], rowH: 0.62, size: 14 });
  const rx = 9.45, rw = XR - rx;
  headerBar(s, "운영 영향 — 검색 API 서버를 내림", { x: rx, y: 4.85, w: rw, h: 0.46, size: 16, accent: true });
  rr(s, { x: rx, y: 5.38, w: rw, h: 2.5, fill: C.tint });
  text(s, "리트리버는 포인터를 요청마다 다시 읽음 → 떠 있는 API 서버도 실험 세대로 자동 전환됨\n\n" +
    "→ 실험 중에는 같은 DATA_ROOT를 보는 서버를 내림. 실행 전 검사(V14)가 확인함",
    { x: rx + 0.15, y: 5.45, w: rw - 0.3, h: 2.35, size: 17, color: C.body, valign: "top" });
}

// S16 ③ 실패 분류
function s16() {
  const s = newSlide({
    title: "③ 실패 분류",
    lead: "종료 코드만 믿지 않음 — 결과 파일이 없으면 0이어도 실패. 어떤 실패든 되돌리기는 반드시 지남",
    notes: "외부 API 재시도 횟수 · 단계 시간 상한은 교재 · 소스에 근거가 없어 결정 필요(실측 뒤 정함).\n" +
      "리트리버 평가 스크립트에는 Ctrl+C 처리가 없어 종료 코드가 정해져 있지 않음(확인 필요) → 결과 파일 유무로 함께 판정.\n" +
      "하위 프로세스 출력은 데이터로만 다룸 — 거기 적힌 문장을 실행기의 지시로 삼지 않음.",
  });
  table(s, [
    ["분류", "코드", "예", "재시도", "실행기 동작"],
    ["설정 오류", "E-CFG", "키 없음 · 범위 밖 · 기준과 2개 이상 다름 · 복사본이 버전 폴더 밖", "안 함", "하위 프로세스를 띄우지 않고 중단"],
    ["비정상 종료", "E-EXIT", "인덱서 종료 코드 1(stderr 오류 JSON) · 리트리버 오류", "안 함", "그 단계 실패 → F4 → 다음 버전, --resume으로 그 단계부터"],
    ["결과 파일 오류", "E-OUT", "--out 파일 없음 · JSON 깨짐 · 필요한 키 없음", "안 함", "종료 코드 0이어도 실패"],
    ["중단", "E-INT", "사람이 Ctrl+C(인덱서는 130)", "안 함", "되돌리기를 마친 뒤 종료 코드 130"],
    ["외부 API 오류", "E-API", "Groq · 평가자 호출 실패 · 요청량 제한", "결정 필요", "지금은 안 함 — 재시도가 같은 조건을 흔들 수 있음"],
    ["시간 초과", "E-TIME", "단계가 상한을 넘김", "안 함", "자식 프로세스 종료 → E-EXIT와 같게. 상한값은 결정 필요"],
  ], { y: 1.95, colW: [2.0, 1.3, 5.3, 1.5, 4.8], rowH: 0.7, size: 15 });
  callout(s, "RAGAS의 지표 추출 미완료(failed_scores)는 실패가 아니라 기록 대상 — 그 지표만 평균에서 빠짐", { y: 7.25, h: 0.55 });
}

// S17 ④ 채점 개요
function s17() {
  const s = newSlide({
    title: "④ 채점 개요 — 코드 → RAGAS → 사람",
    lead: "같은 결과 로그(retriever.json)를 세 채점이 차례로 읽음 — 빠르고 같은 값 · 뜻 판정 · 보정",
    notes: "채점 순서 고정: RAGAS는 retriever.json이 있어야, 검토표는 ragas.json이 있어야 시작(지식니 요청). 이어 하기 단위도 이 3단계.\n" +
      "평가자 · 반복 수 · 합격 기준값 · 평가셋 해시를 버전마다 기록해야 버전끼리 비교할 수 있음(같은 조건).",
  });
  card(s, "retriever.json\n문항마다\n질문 · 근거 본문 · 답변\n· 정답 · 코드 지표", { x: X0, y: 2.3, w: 2.6, h: 3.6, fill: C.navy, line: null,
    color: C.white, size: 15, bold: true });
  const lanes = [
    { t: "코드 채점", tool: "evaluate_retriever.py", use: "배포 관문 · 버전 Δ", pro: "빠름 · 매번 같은 값 · 비용 0",
      out: "retriever.json(5지표 × 두 층)" },
    { t: "RAGAS 채점", tool: "evaluate_ragas.py", use: "어디서 새는지 진단", pro: "뜻까지 판정 · 답변 품질",
      out: "ragas.json(6지표 × 3회)" },
    { t: "사람 채점", tool: "human_review.py", use: "LLM 채점관 보정", pro: "품질 최고 · 다른 채점의 기준",
      out: "review.csv · 일치율 · kappa" },
  ];
  const lx = 3.55, lw = 3.6, gap = 0.25;
  lanes.forEach((l, i) => {
    const x = lx + i * (lw + gap);
    headerBar(s, l.t, { x, y: 2.0, w: lw, h: 0.5, size: 18, accent: i === 1 });
    rr(s, { x, y: 2.6, w: lw, h: 3.3, fill: C.altRow });
    const items = [["도구", l.tool], ["쓰임", l.use], ["장점", l.pro], ["결과", l.out]];
    items.forEach(([k, v], j) => {
      text(s, k, { x: x + 0.12, y: 2.7 + j * 0.8, w: 0.8, h: 0.7, size: 14, bold: true, color: C.sub, valign: "top" });
      text(s, v, { x: x + 0.9, y: 2.7 + j * 0.8, w: lw - 1.0, h: 0.7, size: 15, color: C.ink, valign: "top", bold: j === 0 });
    });
    if (i < 2) arrow(s, { x1: x + lw, y1: 4.25, x2: x + lw + gap, y2: 4.25, color: C.blue, width: 2 });
  });
  arrow(s, { x1: X0 + 2.6, y1: 4.1, x2: lx, y2: 4.1, color: C.blue, width: 2 });
  headerBar(s, "버전마다 함께 기록 — 같은 조건 확인", { x: X0, y: 6.2, w: CW, h: 0.46, size: 16 });
  const chips = ["평가셋 해시", "평가자(local Qwen3.5-9B 고정)", "반복 수 3", "LLM 합격 기준값 0.5(설계 가정)", "top_k · 지표 k"];
  const cw = (CW - 0.2 * 4) / 5;
  chips.forEach((t, i) => pill(s, t, { x: X0 + i * (cw + 0.2), y: 6.85, w: cw, h: 0.55, size: 14 }));
}

// S18 ④ 코드 채점
function s18() {
  const s = newSlide({
    title: "④ 코드 채점 — 두 층 · @k와 @5",
    lead: "Top-k가 바뀌면 k도 바뀌어 지표 분모가 달라짐 — @k는 참고로 남기고, 기준선 대비 차이는 @5로만 계산함",
    notes: "사용자 결정 D5. final 층은 최종 근거 수를 채점 관문이 정하므로 top_k를 따를 근거가 없어 @5 고정(지금과 같음).\n" +
      "top_k 3 버전은 조각이 3개뿐이라 @5 Precision 분모가 5 — 5칸을 쓸 수 있는데 3칸만 채웠으므로 뜻이 맞음(비교표 각주).\n" +
      "인자를 하나도 주지 않으면 top_k 5 · @5 → 지금 로그와 같은 값이 나와야 함(회귀 확인 조건).",
  });
  table(s, [
    ["층", "무엇을 재나"],
    ["search", "첫 검색 상위 k개 조각"],
    ["final", "채점 관문을 통과한 최종 근거(@5 고정)"],
  ], { x: X0, y: 1.95, w: 5.6, colW: [1.4, 4.2], rowH: 0.5, size: 15 });
  table(s, [
    ["지표", "쉬운 뜻"],
    ["hit", "정답 근거가 하나라도 들었나(0 / 1)"],
    ["recall", "정답 근거 중 몇 개를 찾았나"],
    ["mrr", "첫 정답이 몇 위에 나왔나"],
    ["precision", "가져온 조각 중 쓸모 있는 비율(÷ k)"],
    ["ndcg", "정답이 위쪽에 있을수록 높게"],
  ], { x: X0, y: 3.65, w: 5.6, colW: [1.6, 4.0], rowH: 0.45, size: 15 });
  // 오른쪽: k를 키우면
  const rx = 6.5, rw = XR - rx;
  headerBar(s, "k를 키우면 생기는 일", { x: rx, y: 1.95, w: rw, h: 0.46, size: 16, accent: true });
  const bars = [["k = 3", 3], ["k = 5", 5], ["k = 10", 10]];
  bars.forEach(([lab, k], i) => {
    const y = 2.6 + i * 0.55;
    text(s, lab, { x: rx, y, w: 1.0, h: 0.45, size: 14, bold: true, color: C.navy });
    for (let j = 0; j < k; j++) {
      const hit = j === 1 || j === 6;
      box(s, { x: rx + 1.05 + j * 0.42, y: y + 0.05, w: 0.36, h: 0.36, fill: hit ? C.blue : C.white, line: C.border });
    }
  });
  text(s, "■ 정답 근거 조각(2위 · 7위)", { x: rx + 5.4, y: 2.6, w: 3.0, h: 0.45, size: 14, color: C.sub });
  text(s, "precision@k = 1/3 → 1/5 → 2/10 : 분모 탓에 내려감\nrecall@k : 더 많이 담아 올라감 → 검색이 좋아진 것이 아님",
    { x: rx + 5.4, y: 3.05, w: rw - 5.4, h: 1.15, size: 14, color: C.body, valign: "top" });
  rr(s, { x: rx, y: 4.3, w: rw, h: 0.75, fill: C.tint });
  text(s, "→ search@k(그 버전의 k)는 참고 열, search@5(모든 버전 고정)로 Δ 계산", { x: rx + 0.15, y: 4.3, w: rw - 0.3, h: 0.75,
    size: 16, bold: true, color: C.navy });
  table(s, [
    ["evaluate_retriever.py 추가 인자", "기본값", "하는 일"],
    ["--top-k", "5", "검색 두 곳(첫 검색 · 워크플로우 요청)의 top_k"],
    ["--metric-k", "--top-k 값", "search 층 지표의 k(자르기 · precision 분모 · ndcg)"],
    ["--fixed-k", "5", "비교용 고정 @k를 함께 계산"],
    ["--version-label · --config-snapshot", "없음", "결과 머리와 행에 버전 이름 · 적용 설정을 남김"],
  ], { x: rx, y: 5.25, w: rw, colW: [3.5, 1.5, rw - 5.0], rowH: 0.52, size: 14 });
  text(s, "답 없음 문항은 지표 없음(평균에서 빠짐) · 카드 문항은 같은 카드 조각만 정답", { x: X0, y: 6.5, w: 5.6, h: 1.0, size: 14,
    color: C.sub, valign: "top" });
}

// S19 ④ RAGAS 채점 ①
function s19() {
  const s = newSlide({
    title: "④ RAGAS 채점 ① 입력 · 제외 규칙",
    lead: "리트리버 로그 한 행을 RAGAS 4칸으로 옮기고, 채점할 수 없는 행은 사유만 남기고 뺌",
    notes: "근거는 개수가 아니라 본문이 있어야 함 — evaluate_retriever.py가 evidence 본문을 남기는 이유.\n" +
      "답변은 --generate-answer를 켜야 채워짐. 제외 행이 버전마다 다르면 평균의 분모가 달라지므로 비교표에 n을 함께 적음.",
  });
  // 왼쪽: 대응 도형
  const lx = X0, rows = [["question", "user_input", "질문"], ["evidence[].text", "retrieved_contexts", "근거 본문 목록"],
    ["answer[] 이어 붙임", "response", "답변"], ["ground_truth", "reference", "정답"]];
  headerBar(s, "retriever.json 행", { x: lx, y: 1.95, w: 3.2, h: 0.46, size: 16 });
  headerBar(s, "RAGAS 칸", { x: lx + 4.0, y: 1.95, w: 3.4, h: 0.46, size: 16, accent: true });
  rows.forEach(([a, b, c], i) => {
    const y = 2.6 + i * 0.95;
    card(s, a, { x: lx, y, w: 3.2, h: 0.72, size: 15, bold: true, color: C.navy });
    arrow(s, { x1: lx + 3.2, y1: y + 0.36, x2: lx + 4.0, y2: y + 0.36, color: C.blue, width: 2 });
    card(s, b + "\n(" + c + ")", { x: lx + 4.0, y, w: 3.4, h: 0.72, fill: C.tint, size: 14, color: C.navy, bold: true });
  });
  text(s, "--generate-answer를 켠 로그여야 response가 채워짐", { x: lx, y: 6.5, w: 7.4, h: 0.45, size: 14, color: C.sub });
  // 오른쪽: 제외 규칙
  const rx = 8.3, rw = XR - rx;
  table(s, [
    ["사유 코드", "조건", "왜 빼나"],
    ["no_answer_question", "답 없음 문항", "정답이 「확인 필요」라 지표가 뜻을 못 잼"],
    ["status_not_answered", "상태가 answered · retrieved 아님", "답을 안 냈으므로 생성 지표가 무의미"],
    ["empty_evidence", "근거가 비었음", "검색 지표 3종의 입력이 빔"],
    ["empty_response", "답변이 비었음", "생성 지표 3종의 입력이 빔"],
  ], { x: rx, y: 1.95, w: rw, colW: [2.4, 2.0, rw - 4.4], rowH: 0.75, size: 14 });
  rr(s, { x: rx, y: 5.95, w: rw, h: 1.9, fill: C.tint });
  text(s, "제외 행은 채점하지 않고 excluded[]에 {id, reason}만 남김\n지표 평균의 분모 = 채점한 행 수(n) → 비교표에 n을 함께 적음",
    { x: rx + 0.15, y: 6.0, w: rw - 0.3, h: 1.8, size: 16, color: C.body, valign: "top" });
}

// S20 ④ RAGAS 채점 ②
function s20() {
  const s = newSlide({
    title: "④ RAGAS 채점 ② 지표 · 평가자 · 반복",
    lead: "6지표가 필요한 칸만 읽어 판정 — 평가자는 실험 끝까지 로컬 모델로 고정하고 3회 반복해 흔들림을 잼",
    notes: "ragas 0.4.3: 지표는 ascore()로 MetricResult(value 점수 + reason 이유)를 돌려줌. AnswerRelevancy 임베딩은 KURE-v2.\n" +
      "평가자 local(Qwen3.5-9B)은 사고(thinking)를 켜면 빈 답을 내서 끔. 실험 중 평가자를 바꾸면 그 뒤 버전은 앞 버전과 비교 불가.\n" +
      "긴 근거에서 ContextEntityRecall 개체 추출이 끝나지 않는 경우(IncompleteOutputException)는 그 칸만 평균에서 뺌.",
  });
  const metrics = ["ContextPrecisionWithReference", "ContextRecall", "ContextEntityRecall", "Faithfulness", "AnswerRelevancy", "FactualCorrectness"];
  const reads = [[1, 1, 1, 0], [1, 1, 1, 0], [0, 1, 1, 0], [1, 0, 1, 1], [1, 0, 0, 1], [0, 1, 0, 1]];
  const heads = ["질문", "정답", "근거", "답변"];
  const gx = X0 + 3.9, cw = 0.95, top = 1.95;
  heads.forEach((h, j) => text(s, h, { x: gx + j * cw, y: top, w: cw, h: 0.42, size: 14, bold: true, color: C.navy, align: "center" }));
  metrics.forEach((m, i) => {
    const y = top + 0.5 + i * 0.58;
    rr(s, { x: X0, y, w: 3.85 + 4 * cw, h: 0.5, fill: i < 3 ? C.altRow : C.tint, line: null });
    text(s, m, { x: X0 + 0.08, y, w: 3.8, h: 0.5, size: 14, bold: true, color: C.ink });
    reads[i].forEach((r, j) => {
      if (r) s.addShape(L.getPptx().shapes.OVAL, { x: gx + j * cw + cw / 2 - 0.13, y: y + 0.12, w: 0.26, h: 0.26,
        fill: { color: i < 3 ? C.navy : C.blue }, line: { type: "none" } });
    });
  });
  text(s, "윗줄 3개 = 검색 지표 · 아랫줄 3개 = 생성 지표 · 점 = 읽는 칸", { x: X0, y: top + 0.5 + 6 * 0.58, w: 7.7, h: 0.4, size: 14, color: C.sub });
  const rx = 8.55, rw = XR - rx;
  table(s, [
    ["평가자", "모델", "반복 흔들림"],
    ["local(기본 · 고정)", "Qwen3.5-9B", "없음 — 3회 같은 값"],
    ["anthropic", "Claude Opus 5.5", "있음 → 반복 평균"],
    ["groq", "gpt-oss-120b", "있음 → 반복 평균"],
  ], { x: rx, y: 1.95, w: rw, colW: [2.4, 2.1, rw - 4.5], rowH: 0.5, size: 14 });
  headerBar(s, "--repeat 3", { x: rx, y: 4.15, w: 2.0, h: 0.46, size: 16, accent: true });
  text(s, "지표 · 문항마다 평균 · 표준편차 · 최소 · 최대", { x: rx + 2.1, y: 4.15, w: rw - 2.1, h: 0.46, size: 14, color: C.body });
  headerBar(s, "실패 지표", { x: rx, y: 4.75, w: 2.0, h: 0.46, size: 16 });
  text(s, "그 (문항 · 지표 · 회차)만 평균에서 빼고 failed_scores에 기록", { x: rx + 2.1, y: 4.75, w: rw - 2.1, h: 0.46, size: 14, color: C.body });
  table(s, [
    ["ragas.json 필드", "내용"],
    ["log_file · version · eval_set_hash", "무엇을 채점했나"],
    ["provider · model · embedding_model · repeat", "같은 조건 확인용"],
    ["scored · excluded[]", "채점한 행 수 · 뺀 행과 사유"],
    ["summary · rows[] · failed_scores[]", "지표별 {평균 · 표준편차 · 최소 · 최대 · n} · 문항별 점수와 이유"],
  ], { x: rx, y: 5.4, w: rw, colW: [3.3, rw - 3.3], rowH: 0.48, size: 14 });
}

module.exports = [s11, s12, s13, s14, s15, s16, s17, s18, s19, s20];
