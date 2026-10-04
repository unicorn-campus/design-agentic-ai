const L = require("./lib");
const { newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow, hline, table, callout, codeBox,
  C, X0, CW, XR } = L;

// S21 ④ 사람 검토표
function s21() {
  const s = newSlide({
    title: "④ 사람 검토표 — 문항당 1행",
    lead: "사람은 문항마다 한 번 '그대로 고객에게 줘도 되나?'를 판정 — 지표별 LLM 판정과 비교해 일치도를 냄",
    notes: "문항당 1행은 교재 183쪽 설계 가이드. 사람 판정은 지표마다가 아니라 문항당 1회 종합 판정(교재 170쪽, Critique Shadowing).\n" +
      "LLM 합격 = 점수 ≥ 0.5(설계 가정, --threshold로 바꿈). code_hit는 0 / 1이라 hit = 1만 합격.\n" +
      "사용자 결정 D8: 버전별 20건으로만 계산하고 항상 '참고값' 표시(채점관 검증 기준 60건 미달). 2×2 숫자는 그림 예시.",
  });
  headerBar(s, "export — review.csv 열", { x: X0, y: 1.95, w: 7.0, h: 0.46, size: 16 });
  table(s, [
    ["열", "내용", "채우는 쪽"],
    ["id · version", "문항 번호 · 버전 이름", "기계"],
    ["question · ground_truth", "질문 · 정답", "기계"],
    ["answer · evidence", "답변 · 근거 본문(길면 자름)", "기계"],
    ["status · code_hit", "응답 상태 · 최종 Hit", "기계"],
    ["ragas_* (6지표)", "지표 평균 점수(+ 판정 이유)", "기계"],
    [{ text: "human_pass", options: { color: C.blue, bold: true } }, "pass / fail — 이 답변을 그대로 고객에게 줘도 되나?", "사람"],
    [{ text: "human_reason", options: { color: C.blue, bold: true } }, "이유 한 줄(fail이면 필수, 설계 가정)", "사람"],
  ], { x: X0, y: 2.5, w: 7.0, colW: [2.4, 3.6, 1.0], rowH: 0.55, size: 14 });
  const rx = 7.95, rw = XR - rx;
  headerBar(s, "agree — 지표마다 2×2 표", { x: rx, y: 1.95, w: rw, h: 0.46, size: 16, accent: true });
  const gx = rx + 1.4, gy = 2.95, cw = 1.6, ch = 0.85;
  text(s, "사람 합격", { x: gx, y: 2.5, w: cw, h: 0.4, size: 14, bold: true, color: C.navy, align: "center" });
  text(s, "사람 불합격", { x: gx + cw, y: 2.5, w: cw, h: 0.4, size: 14, bold: true, color: C.navy, align: "center" });
  text(s, "LLM 합격", { x: rx, y: gy, w: 1.35, h: ch, size: 14, bold: true, color: C.navy });
  text(s, "LLM 불합격", { x: rx, y: gy + ch, w: 1.35, h: ch, size: 14, bold: true, color: C.navy });
  const cells = [["TP 둘 다 합격", C.blue, C.white], ["FP 너그러움", C.altRow, C.ink], ["FN 엄격함", C.altRow, C.ink], ["TN 둘 다 불합격", C.blue, C.white]];
  cells.forEach(([t, f, c], i) => card(s, t, { x: gx + (i % 2) * cw, y: gy + Math.floor(i / 2) * ch, w: cw, h: ch, fill: f,
    line: C.white, color: c, size: 14, bold: true, r: 0.02 }));
  const fx = gx + 2 * cw + 0.2, fw = XR - fx;
  const forms = [["일치율", "(TP + TN) ÷ 전체"], ["F1", "2TP ÷ (2TP + FP + FN)"], ["kappa", "우연히 맞는 몫을 뺀 일치도"]];
  forms.forEach(([k, v], i) => {
    rr(s, { x: fx, y: gy + i * 0.58, w: fw, h: 0.5, fill: C.tint, line: null });
    text(s, k, { x: fx + 0.08, y: gy + i * 0.58, w: 0.85, h: 0.5, size: 14, color: C.navy, bold: true });
    text(s, v, { x: fx + 0.9, y: gy + i * 0.58, w: fw - 0.95, h: 0.5, size: 14, color: C.body });
  });
  table(s, [
    ["agree 결과를 보고 사람이 하는 일"],
    ["kappa 높은 지표 → 배포 관문, 낮은 지표 → 진단 · 참고용"],
    ["FP 많으면 합격 기준값을 올리고, FN 많으면 내림"],
    ["불일치 행의 사람 이유를 읽고 채점 프롬프트 보강"],
  ], { x: rx, y: 4.85, w: rw, colW: [rw], rowH: 0.5, size: 14, firstColBold: false });
  callout(s, "평가셋 20문항 → 버전당 판정 20건뿐(검증 기준 60건 미달) → 결과에 항상 '참고값' 표시", { y: 7.3, h: 0.55 });
}

// S22 ⑤ 기록 — 버전 폴더 · 설정 스냅샷
function s22() {
  const s = newSlide({
    title: "⑤ 기록 — 버전 폴더 · 설정 스냅샷",
    lead: "버전 폴더 하나만 보면 '무엇을 바꿔 · 어떤 세대로 · 어떤 평가자로' 쟀는지 다시 만들 수 있게 남김",
    notes: "폴더 이름은 교재 185쪽 예시(experiments/chunk_size/600/)를 따름. compare는 하이퍼 파라미터 폴더 바로 밑 — 비교는 그 안의 버전끼리.\n" +
      "비밀값(GROQ_API_KEY · 평가자 키)은 이름과 설정 여부만 남기고 값은 가림. 실행기는 .env를 열지 않음.\n" +
      "_registry.csv는 실험 세대 목록(정리 판단용), 이름은 설계 가정.",
  });
  codeBox(s, [
    "eval-runner/",
    "├─ plans/  chunk_size.yaml · top_k.yaml",
    "└─ experiments/",
    "   ├─ .runner.lock · _registry.csv",
    "   ├─ chunk_size/",
    "   │  ├─ state.json",
    "   │  ├─ _backup/active_generation.json",
    "   │  ├─ 800/",
    "   │  │  ├─ config.json",
    "   │  │  ├─ document_policies.json",
    "   │  │  ├─ retriever.json · ragas.json",
    "   │  │  ├─ review.csv",
    "   │  │  └─ logs/ (하위 프로세스 출력)",
    "   │  ├─ 600/ (같은 구성)",
    "   │  └─ compare.md · compare.csv",
    "   └─ top_k/  3/ · 5/ · 10/ · compare.*",
  ], { x: X0, y: 1.95, w: 6.4, h: 5.95, size: 15, title: "폴더 트리" });
  const rx = 7.25, rw = XR - rx;
  table(s, [
    ["config.json 묶음", "필드"],
    ["무엇을 바꿨나", "param · version · value · baseline · apply · target · 적용 환경변수 · 추가 인자"],
    ["어떤 세대로", "thread_id · generation · base_generation · reindexed · policies_copy_sha256"],
    ["되돌렸나", "pointer_backup_sha256 · pointer_restored(+ 확인 시각)"],
    ["같은 조건인가", "eval_set_path · eval_set_hash · provider · model · embedding_model · repeat · human_threshold · top_k · metric_k · fixed_k"],
    ["다시 만들 수 있나", "git_commit · python 버전(3개 .venv) · embed_device · 임베딩 계약 · hf_local_files_only · 시작 · 끝 시각"],
    ["비밀값", "GROQ_API_KEY · 평가자 키 → '(설정됨)' / '(없음)'만"],
  ], { x: rx, y: 1.95, w: rw, colW: [2.2, rw - 2.2], rowH: 0.82, size: 14 });
}

// S23 ⑤ 비교 — 열 순서 · 계산 · 개선 판정
function s23() {
  const s = newSlide({
    title: "⑤ 비교 — 열 순서 · 계산 · 개선 판정",
    lead: "고정 합격선이 아니라 기준 버전 대비 변화로 판정 — 흔들림 폭보다 큰 차이만 개선으로 봄",
    notes: "열 순서는 교재 189쪽 분석 순서. 흔들림 폭 = 기준 버전을 같은 조건으로 반복 채점한 평균의 (최대 − 최소)(교재 159쪽 예시 방식, 설계 가정).\n" +
      "local 평가자는 흔들림 폭이 0에 가까워 작은 Δ도 개선으로 읽힘 → 비교표에 평가자 이름을 함께 적어 오해를 막음.\n" +
      "평가셋 해시가 버전끼리 다르면 Δ를 계산하지 않고 경고만 적음. n 차이가 3 이상이면 Δ 옆에 경고 표시(설계 가정).",
  });
  const flow = [["① 검색이 근거를 찾았나", "search@5 Recall · nDCG · Hit · MRR · Precision"],
    ["② 어디서 막혔나", "최종 응답 상태 · final 지표 · RAGAS 6지표"], ["③ 채점끼리 맞나", "코드 · RAGAS 방향 · kappa(참고값)"],
    ["④ 다음 하이퍼 파라미터", "가장 큰 병목 하나만"]];
  const fw = 3.55, gap = 0.233;
  flow.forEach(([t, d], i) => {
    const x = X0 + i * (fw + gap);
    card(s, t, { x, y: 1.95, w: fw, h: 0.55, fill: i === 3 ? C.dark : C.navy, line: null, color: C.white, size: 16, bold: true });
    text(s, d, { x, y: 2.52, w: fw, h: 0.6, size: 14, color: C.slate, align: "center", valign: "top" });
    if (i < 3) arrow(s, { x1: x + fw, y1: 2.22, x2: x + fw + gap, y2: 2.22, color: C.blue, width: 2 });
  });
  table(s, [
    ["값", "정의"],
    ["평균", "지표별 문항 평균(코드 지표는 답 있음 문항만)"],
    ["Δ기준선", "그 버전 평균 − 기준 버전 평균(청크 800 · Top-k 5)"],
    ["sd_items", "문항 간 흩어짐(코드 지표) — 판정에 쓰지 않음"],
    ["sd_repeat", "반복 간 흔들림(RAGAS) — 개선 판정의 재료"],
    ["n", "그 지표를 실제로 채점한 문항 수"],
  ], { x: X0, y: 3.3, w: 6.6, colW: [1.7, 4.9], rowH: 0.6, size: 14 });
  const rx = 7.45, rw = XR - rx;
  table(s, [
    ["지표", "조건", "판정"],
    ["코드 지표", "Δ ≠ 0", "Δ 부호대로 개선 / 악화(같은 입력 = 같은 값)"],
    ["RAGAS 지표", "|Δ| > 흔들림 폭", "개선 / 악화"],
    ["RAGAS 지표", "|Δ| ≤ 흔들림 폭", "차이 없음(판정 보류)"],
    ["코드 ↑ · RAGAS ↓", "방향이 반대", "원인 확인 — 평가셋 정답 · 근거 표기 점검"],
    ["모든 경우", "0.8 같은 고정 합격선", "쓰지 않음 — 기준선 대비 변화만"],
  ], { x: rx, y: 3.3, w: rw, colW: [2.1, 2.3, rw - 4.4], rowH: 0.6, size: 14 });
  callout(s, "평가셋 해시가 버전끼리 다르면 Δ를 계산하지 않음 — 같은 평가셋 · 같은 평가자 · 같은 반복 수일 때만 비교", { y: 7.3, h: 0.55 });
}

// S24 ⑤ compare.md 틀
function s24() {
  const s = newSlide({
    title: "⑤ compare.md 틀",
    lead: "분석 순서대로 표 3개 + 판정 — 값은 실행해야 채워짐(아래 …는 빈칸)",
    notes: "compare.csv도 같은 열을 가짐: 식별(version · param · param_value · reindex · generation · eval_set_hash · n) →\n" +
      "검색 @5 5지표 → 최종 응답(answerable_returned · with_relevant · no_answer_refused · final_recall · final_ndcg) →\n" +
      "RAGAS 6지표 → 채점끼리(방향 일치 · kappa) → 참고(search@k · seconds_median · llm_calls_mean).",
  });
  codeBox(s, [
    "# 비교표 — top_k (기준 5 · 평가셋 해시 … · 평가자 local · repeat 3)",
    "",
    "## ① 검색이 근거를 찾았나",
    "| 버전 | Recall@5 | Δ | nDCG@5 | Δ | Hit@5 | Δ | Recall@k(참고) | n |",
    "| 3        | …        | … | …      | … | …     | … | …              | … |",
    "| 5 ★기준  | …        | — | …      | — | …     | — | …              | … |",
    "| 10       | …        | … | …      | … | …     | … | …              | … |",
    "",
    "## ② 어디서 막혔나",
    "| 버전 | 근거 들고 끝남 | 확인 필요 정답 | ContextRecall | Δ | Faithfulness | Δ | 흔들림 폭 |",
    "",
    "## ③ 채점끼리 맞나",
    "| 지표 | 코드 방향 | RAGAS 방향 | 일치 | kappa(참고값) | 판정 |",
    "",
    "## 판정",
    "- 개선: …   차이 없음: …   원인 확인: …",
    "- 다음 하이퍼 파라미터(병목 하나): …",
  ], { x: X0, y: 1.95, w: 10.2, h: 5.95, size: 15, title: "experiments/top_k/compare.md" });
  const rx = 11.0, rw = XR - rx;
  const notes = [["★ 기준 행", "Δ 칸은 모두 —"], ["@5 Δ", "Top-k 버전끼리 같은 잣대(결정)"], ["@k", "그 버전이 실제로 넘긴 근거의 질 — 참고"],
    ["n", "버전마다 다르면 평균 비교에 주의"], ["평가자 이름", "흔들림 폭 해석에 필요"]];
  notes.forEach(([k, v], i) => {
    const y = 1.95 + i * 1.2;
    rr(s, { x: rx, y, w: rw, h: 1.05, fill: i % 2 ? C.white : C.tint });
    text(s, k, { x: rx + 0.15, y: y + 0.05, w: rw - 0.3, h: 0.4, size: 15, bold: true, color: C.navy });
    text(s, v, { x: rx + 0.15, y: y + 0.45, w: rw - 0.3, h: 0.55, size: 14, color: C.body, valign: "top" });
  });
}

// S25 공통 원칙
function s25() {
  const s = newSlide({
    title: "공통 원칙 — 같은 조건 · 되돌리기 · 이어 하기",
    lead: "세 원칙이 모든 단계에 걸림 — 비교가 성립하게, 원래대로 돌아오게, 끊겨도 이어지게",
    notes: "state.json은 단계 시작 직전과 끝난 직후 두 번 씀(임시 파일 → 바꿔치기). 계획 파일이 바뀐 채 --resume하면 기본 거부.\n" +
      "바뀐 버전만 다시 돌리는 부분 무효화는 범위 밖(설계 가정) — 바뀌면 --force-new로 새 실행.",
  });
  const cols = [
    ["같은 조건", "· 평가셋 해시 · 평가자 · 반복 수 · 합격 기준값을 계획 파일에 고정\n· 버전 폴더마다 기록, 다르면 Δ 계산 안 함\n· 기준 800도 같은 절차로 새로 색인"],
    ["되돌리기", "· 실행 전 포인터 백업(처음 값만 지킴)\n· 버전마다 검색 직후 복원 + 종료 때 재확인\n· 실패 · Ctrl+C에도 반드시 지남"],
    ["이어 하기", "· --resume: 성공 단계는 건너뛰고 실패 단계부터\n· 색인은 같은 thread-id로 체크포인트 재개\n· 계획 파일 해시가 다르면 거부"],
  ];
  const w = 4.8, gap = 0.25;
  cols.forEach(([t, d], i) => {
    const x = X0 + i * (w + gap);
    headerBar(s, t, { x, y: 1.95, w, h: 0.5, size: 18, accent: i === 1 });
    rr(s, { x, y: 2.55, w, h: 2.2, fill: C.tint });
    text(s, d, { x: x + 0.15, y: 2.62, w: w - 0.3, h: 2.05, size: 17, color: C.body, valign: "top" });
  });
  table(s, [
    ["state.json 단계 상태", "뜻", "--resume에서"],
    ["대기", "아직 시작 안 함", "실행"],
    ["실행 중", "시작했는데 끝 기록 없음(끊김)", "그 단계부터 다시(산출 파일 덮어씀)"],
    ["성공", "끝났고 산출 파일 있음", "건너뜀(파일이 실제로 있는지도 확인)"],
    ["실패", "끝났는데 오류", "그 단계부터 다시"],
    ["미지원", "바꾸는 방법이 아직 없음", "다시 검사 — 생겼으면 실행"],
    ["건너뜀", "해당 없음(재색인 아닌데 F2)", "그대로 둠"],
  ], { y: 4.95, colW: [3.0, 5.4, 6.5], rowH: 0.42, size: 14 });
}

// S26 물리 배치
function s26() {
  const s = newSlide({
    title: "물리 배치",
    lead: "가상환경 4개가 서로 import하지 않고 파일로만 주고받음 — 실행기는 하위 프로세스를 부르기만 해서 가벼움",
    notes: "서비스 조립 약 17초(GPU 실측, 리트리버 README) × 버전 수만큼 더해짐 — 버전마다 프로세스를 새로 띄우므로.\n" +
      "CPU에서는 리랭크 1회 약 7초라 30초 시간 예산을 금방 씀 → GPU 권장(리트리버 README).\n" +
      "세대 1개 약 6.5MB(실측 5.5 ~ 6.9MB), 지금 data 전체 약 93MB(2026-10-04). 재색인 1회 소요 시간은 확인 필요.",
  });
  codeBox(s, [
    "hybrid-ai-lab/",
    "├─ .env                 공용 설정",
    "├─ eval-runner/         ★ 새로 만듦",
    "│  ├─ .venv/            실행기 전용",
    "│  ├─ plans/ · experiments/",
    "├─ indexer/vector-bm25/",
    "│  ├─ .venv/ · .env · config/",
    "│  └─ data/             active_generation.json",
    "│                       generations/gen-…/",
    "│                       checkpoints/ · .writer.lock",
    "├─ retriever/vector-retriever/",
    "│  └─ .venv/ · .env · evaluate_retriever.py",
    "└─ ragas/               ★ 도구 새로 만듦",
    "   ├─ .venv/            ragas 0.4.3",
    "   ├─ eval-set.md · eval-set.json",
    "   └─ build_ · verify_ · evaluate_ragas · human_review",
  ], { x: X0, y: 1.95, w: 6.9, h: 5.95, size: 15, title: "폴더 · 가상환경" });
  const rx = 7.75, rw = XR - rx;
  table(s, [
    ["실행 전 환경 점검", "확인"],
    ["임베딩 · 리랭크 모델이 로컬 캐시에 있음", "HF_LOCAL_FILES_ONLY=true — 실행 중 내려받지 않음"],
    ["인덱서 · 리트리버 EMBED_* 같음", "다르면 리트리버가 검색 거부(색인 계약)"],
    ["장치", "GPU 권장 — CPU는 리랭크 1회 약 7초"],
    ["버전당 고정 비용", "서비스 조립 약 17초(GPU)"],
    ["디스크", "세대 1개 약 6.5MB + 산출물"],
    ["검색 API 서버", "같은 DATA_ROOT 서버는 꺼짐(V14)"],
    ["세대 정리", "자동 정리 없음 → 비교표 확정 후 수동"],
  ], { x: rx, y: 1.95, w: rw, colW: [3.4, rw - 3.4], rowH: 0.72, size: 14 });
}

// S27 결정 필요 항목 요약
function s27() {
  const s = newSlide({
    title: "결정 필요 · 확인 필요 항목",
    lead: "근거가 없어 숫자를 넣지 않은 자리 — 기준 버전을 한 번 실제로 돌려 본 뒤 정함",
    notes: "이미 정한 것(사용자 결정 D1 ~ D8)은 이 표에서 뺌. 설계 가정 값(합격 기준 0.5 · 해시 12자 · thread-id 형식 · 거부 종료 코드 2 ·\n" +
      "n 차이 3 경고)은 각 장에 표시함.",
  });
  table(s, [
    ["구분", "항목", "왜 아직 못 정하나", "정하는 방법"],
    ["결정 필요", "단계 시간 상한(F2 · F3 · F5)", "실제 소요 시간 근거 없음", "기준 버전 1회 실측 뒤"],
    ["결정 필요", "외부 API 오류 재시도 횟수", "재시도가 같은 조건을 흔들 수 있음", "평가자 · Groq 오류 빈도를 본 뒤"],
    ["결정 필요", "청크 600에서 근거가 잘린 문항 처리", "주석만 vs 제외 — 제외하면 분모가 달라짐", "참고 검증 결과를 본 뒤(기본 주석)"],
    ["결정 필요", "LLM 합격 기준값(지표별)", "0.5는 설계 가정", "agree의 FP / FN 치우침을 본 뒤"],
    ["결정 필요", "실험 세대 정리 시점", "비교표가 참조하는 세대는 지우면 안 됨", "비교표 확정 후 수동(권장)"],
    ["확인 필요", "--full-reindex가 체크포인트를 지우는지", "소스로 확인 못 함", "인덱서 시험 실행"],
    ["확인 필요", "리트리버 평가 Ctrl+C 종료 코드", "처리 코드가 없음", "실행해 보고 결과 파일 유무로 판정"],
    ["확인 필요", "재색인 1회 소요 시간(600 · 800)", "실측 없음", "--dry-run으로 조각 수부터"],
  ], { y: 1.95, colW: [1.7, 4.4, 4.7, 4.1], rowH: 0.64, size: 14 });
}

// S28 부록 A 흐름 도식 스크립트
function s28() {
  const s = newSlide({
    title: "부록 A — 흐름 도식 스크립트(mermaid)",
    lead: "⓪ 실행 흐름도를 mermaid로 옮긴 것 — README의 흐름도에 그대로 씀",
    notes: "버전마다 F4 되돌리기를 지난 뒤 F5 · F6을 돌고 다음 버전으로. 실행 거부만 F4를 지나지 않음(포인터를 건드리기 전).",
  });
  codeBox(s, [
    "flowchart TD",
    "  A[계획 파일 읽기] --> B{실행 전 검사 통과?}",
    "  B -- 아니요 --> X[실행 거부 · 아무것도 안 바꿈]",
    "  B -- 예 --> C[F0 준비 · 잠금 · 포인터 백업]",
    "  C --> E{남은 버전? 기준 먼저}",
    "  E -- 아니요 --> P[F7 비교표] --> R[종료 · 포인터 재확인 · 잠금 해제]",
    "  E -- 예 --> F[F1 설정 적용]",
    "  F --> G{지원되는 방법?}",
    "  G -- 아니요 --> U[미지원 · 건너뜀] --> E",
    "  G -- 예 --> H{재색인 버전?}",
    "  H -- 예 --> I[F2 색인 · 새 thread-id] --> J",
    "  H -- 아니요 --> J[F3 검색 · 코드 채점]",
    "  I -- 실패 --> K",
    "  J --> K[F4 되돌리기 · 포인터 복원]",
    "  K --> M{F3 성공?}",
    "  M -- 아니요 --> E",
    "  M -- 예 --> N[F5 RAGAS 채점] --> O[F6 검토표 내보내기] --> E",
  ], { x: X0, y: 1.95, w: CW, h: 5.95, size: 16, title: "mermaid" });
}

// S29 부록 B 교재와 소스가 다른 점
function s29() {
  const s = newSlide({
    title: "부록 B — 설계가 교재 설명과 다른 점",
    lead: "설계는 지금 소스를 따름 — 교재를 그대로 옮기면 동작하지 않는 자리 4곳",
    notes: "교재 183 · 188쪽(세대 경로 환경변수) · 187쪽(RAGAS · 사람 채점 도구) · 179쪽(eval-set.json · verify) · 186쪽(Top-k 고정)과 소스를 대조한 결과.",
  });
  table(s, [
    ["#", "교재 설명", "지금 소스", "설계"],
    ["1", "재색인 버전은 세대 경로 환경변수 2개(CHROMA_PATH · SEARCH_INDEX_ROOT)를 그 세대로 지정",
      "리트리버는 DATA_ROOT 아래 active_generation.json 하나만 읽음", "포인터 백업 → 게시 → 검색 → 복원"],
    ["2", "리트리버 설정은 서비스 시작 때 1회 읽음", "세대 포인터는 요청마다 다시 읽어 바뀌면 다음 요청부터 새 세대",
      "실험 중 같은 DATA_ROOT 검색 API 서버를 내림"],
    ["3", "evaluate_ragas.py · human_review.py · eval-set.json · verify_eval_set.py로 채점",
      "저장소에 없음(ragas 폴더에 eval-set.md만 있음)", "변환기 · 검증기 · RAGAS · 검토표 도구를 새로 설계"],
    ["4", "Top-k는 evaluate_retriever.py의 5 고정을 풀어야 실험 가능",
      "top_k=5가 두 곳, 지표 @5가 세 곳에 박혀 있음", "인자 추가(--top-k · --metric-k · --fixed-k), 기본값은 지금과 같게"],
  ], { y: 1.95, colW: [0.6, 5.0, 4.9, 4.4], rowH: 1.15, size: 15 });
}

// S30 부록 C 설계 점검표
function s30() {
  const s = newSlide({
    title: "부록 C — 설계 점검표",
    lead: "설계 가이드의 항목마다 이 설계서가 어디에 답했는지 — 교육생 설계도 같은 질문에 답해야 함",
  });
  table(s, [
    ["#", "점검 항목", "이 설계의 답", "장"],
    ["1", "버전안을 파일 1개로 적었나(하이퍼 파라미터 · 값 · 기준 · 바꾸는 종류)", "plans/{하이퍼 파라미터}.yaml", "①"],
    ["2", "기준과 값 1개만 다른지 실행 전에 검사하나", "V1 거부 + 범위 검사 V10 · V11", "①"],
    ["3", "바꾸는 종류별 적용기가 있고 원본을 지키나", "env · config · code_arg + 미지원", "②"],
    ["4", "재색인 버전의 세대를 지정하고 되돌리나", "포인터 백업 → 버전마다 복원 → 종료 재확인", "③"],
    ["5", "가상환경이 다른 도구를 하위 프로세스로 부르나", "도구 4개 호출 규격 · 성공 판정", "③"],
    ["6", "코드 → RAGAS → 사람 순서로 채점하고 조건을 기록하나", "retriever · ragas · review + config.json", "④"],
    ["7", "버전 폴더에 설정 스냅샷과 로그 3종을 남기나", "experiments/{하이퍼 파라미터}/{버전}/", "⑤"],
    ["8", "비교표가 평균 · 기준 대비 차이 · 표준편차를 분석 순서대로 내나", "compare.md · .csv, Δ는 @5", "⑤"],
    ["9", "같은 조건 · 되돌리기 · 이어 하기를 지키나", "평가셋 해시 · 포인터 복원 · state.json", "공통"],
    ["10", "근거 없는 값을 지어내지 않았나", "설계 가정 · 결정 필요 · 확인 필요로 표시", "결정 필요"],
  ], { y: 1.95, colW: [0.6, 6.9, 5.9, 1.5], rowH: 0.55, size: 14 });
}

module.exports = [s21, s22, s23, s24, s25, s26, s27, s28, s29, s30];
