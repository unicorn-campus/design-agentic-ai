const L = require("./lib");
const { newSlide, rr, box, text, card, headerBar, darkBadge, numBadge, pill, arrow, hline, table, callout, codeBox,
  C, X0, CW, XR } = L;

const B = (t) => ({ text: t, options: { bold: true, color: C.navy } });

// S01 설계 개요
function s01() {
  const s = newSlide({
    title: "품질평가 프로그램 설계서 — 설계 개요",
    lead: "하이퍼 파라미터 버전을 같은 잣대로 비교하는 실행기 — 버전 정의 파일 하나로 색인 · 검색 · 채점 · 비교표까지",
    notes: "설계 가이드는 교재 183쪽(버전 정의 · 설정 적용 · 실행 · 채점 · 기록 · 비교 + 공통 3원칙).\n" +
      "사용자 결정: D1 채점 도구까지 설계, D2 평가셋 md → json 변환 포함, D3 세대 포인터 백업 → 복원, D4 버전안 청크 크기 · Top-k,\n" +
      "D5 Top-k 지표는 @k · @5 함께 + Δ는 @5, D6 기준 800도 새로 색인, D7 실험 중 검색 API 서버 내림, D8 사람 판정 20건은 참고값.",
  });
  table(s, [
    ["항목", "내용"],
    ["설계 대상", "품질평가 프로그램 = 버전 실험 실행기(eval-runner) + 평가셋 변환기 + RAGAS 채점 · 사람 검토표 도구"],
    ["왜 필요한가", "지금은 버전마다 .env를 손으로 고치고 명령 3개를 따로 돌림. 어떤 설정으로 돌렸는지 남지 않고 비교표는 수작업임"],
    ["설계 범위", "평가셋 준비 → ① 버전 정의 → ② 설정 적용 → ③ 실행 → ④ 채점(코드 · RAGAS · 사람) → ⑤ 기록 · 비교"],
    ["앞 단계 프로그램", "인덱서 vector-bm25(색인 세대 게시) · 리트리버 vector-retriever(검색 · 답변 · 코드 채점 5지표)"],
    ["평가셋", "eval-set v2 20문항 — 약관 6 · 카드 혜택 7 · 상담 이력 4 · 답 없음 3"],
    ["이번 버전안", "청크 크기 600 · 800(기준 800, 재색인) / Top-k 3 · 5 · 10(기준 5, 재색인 아님)"],
    ["새로 만드는 것", "eval-runner · build_eval_set.py · verify_eval_set.py · evaluate_ragas.py · human_review.py"],
    ["고치는 것", "evaluate_retriever.py에 인자만 추가(--top-k 등). 인자를 안 주면 지금과 같은 결과"],
    ["표기", "설계 가정 = 값은 정했으나 측정 근거 없음 · 결정 필요 = 운영 전에 사람이 정함 · 확인 필요 = 소스로 확인 못 함"],
  ], { y: 1.95, colW: [2.7, 12.2], rowH: 0.58, size: 16 });
}

// S02 목차
function s02() {
  const s = newSlide({ title: "목차" });
  const cols = [
    { n: "⓪", t: "전체 구성", items: ["구성도", "실행 흐름도", "실행 단계 목록"] },
    { n: "준비", t: "평가셋 준비", items: ["md → json 칸 대응", "검증 5검사 · 평가셋 해시"] },
    { n: "①", t: "버전 정의", items: ["계획 파일 필드", "버전안 · 계획 파일 2개", "실행 전 검사"] },
    { n: "②", t: "설정 적용", items: ["적용기 3종", "대상 키 표기 · 범위 검사"] },
    { n: "③", t: "실행", items: ["하위 프로세스 호출 규격", "세대 지정 · 되돌리기", "세대 이름 · 동시 실행", "실패 분류"] },
    { n: "④", t: "채점", items: ["채점 개요", "코드 채점 · @k와 @5", "RAGAS 채점 ① ②", "사람 검토표"] },
    { n: "⑤", t: "기록 · 비교", items: ["버전 폴더 · 설정 스냅샷", "열 순서 · 계산 · 개선 판정", "compare.md 틀"] },
    { n: "공통", t: "공통 원칙 · 배치", items: ["같은 조건 · 되돌리기 · 이어 하기", "물리 배치"] },
    { n: "끝", t: "결정 필요 · 부록", items: ["결정 필요 항목", "A 흐름 도식 스크립트", "B 교재와 소스가 다른 점", "C 설계 점검표"] },
  ];
  const w = 4.8, h = 1.9, gx = 0.25, gy = 0.2, y0 = 1.45;
  cols.forEach((c, i) => {
    const x = X0 + (i % 3) * (w + gx), y = y0 + Math.floor(i / 3) * (h + gy);
    rr(s, { x, y, w, h, fill: i % 2 ? C.altRow : C.tint });
    card(s, c.n, { x: x + 0.18, y: y + 0.18, w: 0.95, h: 0.46, fill: c.n.length === 1 ? C.blue : C.navy, line: null,
      color: C.white, size: 16, bold: true, r: 0.05 });
    text(s, c.t, { x: x + 1.25, y: y + 0.16, w: w - 1.4, h: 0.5, size: 20, bold: true, color: C.navy });
    text(s, c.items.map((t) => "· " + t).join("\n"), { x: x + 0.25, y: y + 0.72, w: w - 0.4, h: h - 0.8, size: 15,
      color: C.body, valign: "top" });
  });
}

// S03 전체 구성도
function s03() {
  const s = newSlide({
    title: "⓪ 전체 구성도",
    lead: "실행기는 도구를 import하지 않고 각 가상환경의 python을 하위 프로세스로 부름 — 결과는 파일로만 주고받음",
    notes: "리트리버와 RAGAS는 의존성이 부딪쳐 가상환경이 다름(교재 188쪽 NOTES). 실행기도 전용 가상환경을 둠(옵스니).\n" +
      "파랑 = 새로 만듦, 흰색 = 이미 있음, 점선 = 인자만 추가.",
  });
  // 왼쪽: 평가셋
  headerBar(s, "평가셋 준비", { x: X0, y: 1.95, w: 3.2, h: 0.46, size: 16 });
  card(s, "eval-set.md\n사람이 읽고 검토", { x: X0, y: 2.6, w: 3.2, h: 0.95, size: 15 });
  arrow(s, { x1: X0 + 1.6, y1: 3.55, x2: X0 + 1.6, y2: 3.85 });
  card(s, "build_eval_set.py\n+ verify_eval_set.py", { x: X0, y: 3.85, w: 3.2, h: 0.95, fill: C.blue, line: null,
    color: C.white, size: 15, bold: true });
  arrow(s, { x1: X0 + 1.6, y1: 4.8, x2: X0 + 1.6, y2: 5.1 });
  card(s, "eval-set.json\n+ 평가셋 해시", { x: X0, y: 5.1, w: 3.2, h: 0.95, size: 15 });

  // 가운데: 실행기
  const cx = 4.25, cw = 4.9;
  rr(s, { x: cx, y: 1.95, w: cw, h: 4.95, fill: C.tint, line: C.blue, lw: 1.5 });
  text(s, "eval-runner  (실행기 · 전용 .venv)", { x: cx + 0.15, y: 2.02, w: cw - 0.3, h: 0.45, size: 17, bold: true,
    color: C.navy });
  const steps = [["①", "버전 정의", "plans/*.yaml 읽기 · 1개 차이 검사"], ["②", "설정 적용", "env · config · code_arg"],
    ["③", "실행", "색인 → 검색 → 되돌리기"], ["④", "채점", "코드 → RAGAS → 사람"], ["⑤", "기록 · 비교", "버전 폴더 · compare.md"]];
  steps.forEach(([n, t, d], i) => {
    const y = 2.55 + i * 0.85;
    numBadge(s, n, { x: cx + 0.2, y: y + 0.08, size: 0.5, fsz: 16 });
    rr(s, { x: cx + 0.8, y, w: cw - 1.0, h: 0.68, fill: C.white });
    text(s, t, { x: cx + 0.9, y, w: 1.55, h: 0.68, size: 16, bold: true, color: C.navy });
    text(s, d, { x: cx + 2.4, y, w: cw - 2.65, h: 0.68, size: 14, color: C.slate });
  });
  arrow(s, { x1: X0 + 3.2, y1: 5.57, x2: cx, y2: 5.57, color: C.blue, width: 2 });

  // 오른쪽: 가상환경 3칸
  const rx = 9.75, rw = XR - rx;
  const envs = [
    { t: "indexer/vector-bm25/.venv", tool: "run_indexer.py", d: "--full-reindex --thread-id …\n설정 복사본 경로는 환경변수로", dash: false },
    { t: "retriever/vector-retriever/.venv", tool: "evaluate_retriever.py", d: "--questions · --generate-answer · --out\n+ --top-k 등 인자 추가", dash: true },
    { t: "ragas/.venv  (ragas 0.4.3)", tool: "evaluate_ragas.py · human_review.py", d: "새로 만듦 — RAGAS 6지표 · 검토표\nexport · agree", dash: false, isNew: true },
  ];
  envs.forEach((e, i) => {
    const y = 1.95 + i * 1.68;
    rr(s, { x: rx, y, w: rw, h: 1.5, fill: C.white, line: C.border });
    darkBadge(s, e.t, { x: rx + 0.12, y: y + 0.1, w: rw - 0.24, h: 0.38, size: 14 });
    card(s, e.tool, { x: rx + 0.12, y: y + 0.55, w: 2.3, h: 0.85, fill: e.isNew ? C.blue : C.altRow,
      line: e.isNew ? null : (e.dash ? C.blue : C.border), dash: e.dash ? "dash" : undefined, lw: e.dash ? 1.5 : 1,
      color: e.isNew ? C.white : C.navy, size: 14, bold: true });
    text(s, e.d, { x: rx + 2.5, y: y + 0.55, w: rw - 2.6, h: 0.85, size: 14, color: C.slate });
    arrow(s, { x1: cx + cw, y1: 3.2 + i * 0.85, x2: rx, y2: y + 0.97, color: C.slate });
  });

  // 아래: 기록 · 포인터
  card(s, "experiments/{하이퍼 파라미터}/{버전}/  config · retriever · ragas · review  →  compare.md",
    { x: cx, y: 7.05, w: cw + 0.6, h: 0.75, fill: C.altRow, size: 14, bold: true, color: C.navy });
  card(s, "indexer data/active_generation.json\n사용 중 세대 포인터(백업 → 복원)", { x: rx + 0.5, y: 7.05, w: rw - 0.5, h: 0.75,
    fill: C.white, line: C.dark, size: 14, color: C.ink });
  text(s, "■ 파랑 = 새로 만듦   □ 점선 = 인자만 추가", { x: X0, y: 7.2, w: 3.4, h: 0.5, size: 14, color: C.sub });
}

// S04 실행 흐름도
function s04() {
  const s = newSlide({
    title: "⓪ 실행 흐름도",
    lead: "버전마다 F1 ~ F6을 돌고 마지막에 비교표 — 포인터 되돌리기는 검색 직후와 종료 때 두 번 지남",
    notes: "되돌리기를 검색 · 코드 채점(F3) 직후에 두는 이유: ① 게시는 사용 중 세대가 그 세대의 base_generation일 때만 통과하므로\n" +
      "다음 버전 색인 전에 반드시 기준으로 돌아와야 함(인덱서 index_repository 게시 검사) ② RAGAS · 검토표는 retriever.json만 읽어\n" +
      "포인터가 필요 없음 → 포인터가 실험 세대를 가리키는 시간이 가장 짧아짐. 종료 때 한 번 더 확인하는 것은 안전망.",
  });
  const y = 3.3, h = 0.95;
  card(s, "F0 준비\n검사 · 잠금 · 포인터 백업", { x: X0, y, w: 1.75, h, fill: C.navy, line: null, color: C.white, size: 14, bold: true });
  // 버전 반복 틀
  const lx = 2.6, lw = 10.6;
  rr(s, { x: lx, y: 2.0, w: lw, h: 3.6, fill: C.altRow, line: C.blue, lw: 1.5, dash: "dash" });
  text(s, "버전 반복 — 기준 버전 먼저, 한 번에 한 버전", { x: lx + 0.15, y: 2.05, w: 6, h: 0.42, size: 15, bold: true, color: C.blue });
  const nodes = [
    ["F1 설정 적용", "config.json"], ["F2 색인", "재색인 버전만"], ["F3 검색 · 코드 채점", "retriever.json"],
    ["F4 되돌리기", "포인터 복원"], ["F5 RAGAS 채점", "ragas.json"], ["F6 검토표", "review.csv"],
  ];
  const nw = 1.52, gap = 0.2;
  nodes.forEach(([t, d], i) => {
    const x = lx + 0.2 + i * (nw + gap);
    const hl = i === 3;
    card(s, t + "\n" + d, { x, y, w: nw, h, fill: hl ? C.blue : C.white, line: hl ? null : C.border,
      color: hl ? C.white : C.ink, size: 14, bold: hl, dash: i === 1 ? "dash" : undefined });
    if (i < nodes.length - 1) arrow(s, { x1: x + nw, y1: y + h / 2, x2: x + nw + gap, y2: y + h / 2 });
  });
  arrow(s, { x1: X0 + 1.75, y1: y + h / 2, x2: lx + 0.2, y2: y + h / 2, width: 2 });
  card(s, "F7 비교표\ncompare.md", { x: 13.45, y, w: 1.0, h, fill: C.navy, line: null, color: C.white, size: 14, bold: true });
  arrow(s, { x1: lx + lw - 0.1, y1: y + h / 2, x2: 13.45, y2: y + h / 2, width: 2 });
  card(s, "종료\n포인터\n재확인", { x: 14.6, y, w: 0.857, h, fill: C.dark, line: null, color: C.white, size: 14, bold: true });
  arrow(s, { x1: 14.45, y1: y + h / 2, x2: 14.6, y2: y + h / 2 });
  // 재색인 아님 우회
  arrow(s, { x1: lx + 0.2 + nw / 2, y1: y + h, x2: lx + 0.2 + nw / 2, y2: 4.75, color: C.sub, head: "none" });
  arrow(s, { x1: lx + 0.2 + nw / 2, y1: 4.75, x2: lx + 0.2 + 2 * (nw + gap) + nw / 2, y2: 4.75, color: C.sub, head: "none" });
  arrow(s, { x1: lx + 0.2 + 2 * (nw + gap) + nw / 2, y1: 4.75, x2: lx + 0.2 + 2 * (nw + gap) + nw / 2, y2: y + h, color: C.sub });
  text(s, "재색인 아님(Top-k) → F2 건너뜀", { x: lx + 0.3, y: 4.8, w: 4, h: 0.4, size: 14, color: C.sub });
  // 반복 화살표
  text(s, "↺ 남은 버전이 있으면 F1로", { x: lx + lw - 3.6, y: 4.8, w: 3.4, h: 0.4, size: 14, color: C.blue, bold: true, align: "right" });

  // 분기 3개
  const by = 5.95, bw = 4.8, bh = 1.75;
  const br = [
    ["검사 실패 → 실행 거부", "F0의 실행 전 검사에서 걸리면 아무것도 바꾸지 않고 끝냄(포인터를 건드리기 전이라 되돌릴 것 없음)"],
    ["미지원 → 그 버전 건너뜀", "바꾸는 방법이 아직 없는 값(코드에 박힌 값)은 상태 '미지원'으로 적고 다음 버전으로"],
    ["단계 실패 · 중단 → F4로", "어느 단계에서 실패하거나 Ctrl+C가 와도 포인터 복원을 지난 뒤 다음 버전(또는 종료)"],
  ];
  br.forEach(([t, d], i) => {
    const x = X0 + i * (bw + 0.25);
    rr(s, { x, y: by, w: bw, h: bh, fill: C.white });
    darkBadge(s, t, { x: x + 0.15, y: by + 0.15, w: bw - 0.3, h: 0.42, size: 15, fill: i === 2 ? C.blue : C.dark });
    text(s, d, { x: x + 0.15, y: by + 0.65, w: bw - 0.3, h: bh - 0.75, size: 14, color: C.body, valign: "top" });
  });
}

// S05 실행 단계 목록
function s05() {
  const s = newSlide({
    title: "⓪ 실행 단계 목록",
    lead: "실행 1회 = 준비 1단계 + 버전마다 6단계 + 비교표 1단계. 실행기의 자동 재시도는 0회",
    notes: "LangGraph를 쓰지 않음(플로니 C-1, 클로니 승인): 단계가 고정 순서이고 분기가 재색인 · 실패 · 미지원 셋뿐인 배치형 CLI.\n" +
      "재색인 재개는 인덱서 LangGraph 체크포인트가 이미 맡음 — 실행기에 체크포인트를 한 겹 더 두면 두 재개 기록이 어긋남.\n" +
      "자동 재시도 0회: 재색인 · 채점은 비용이 커서 자동 재시도가 세대 · 로그를 중복 생성함. 사람이 --resume로 다시 함.",
  });
  table(s, [
    ["단계", "하는 일", "입력", "출력", "재색인만", "실패하면"],
    ["F0 준비", "실행 전 검사 · 실행기 잠금 · 포인터 백업 · state.json 생성", "계획 파일 · 포인터", "_backup · state.json", "아니요", "실행 거부(아무것도 안 바꿈)"],
    ["F1 설정 적용", "적용기로 값을 넣고 설정 스냅샷 기록", "계획의 값 · 대상 키", "config.json", "아니요", "버전 실패 → 다음 버전"],
    ["F2 색인", "새 thread-id로 전체 재색인 → 게시가 포인터를 새 세대로", "설정 복사본 · thread-id", "새 세대 gen-…", "예", "버전 실패 → F4"],
    ["F3 검색 · 코드 채점", "평가셋 20문항을 리트리버로 돌리고 5지표 두 층 채점", "eval-set.json · 사용 중 세대", "retriever.json", "아니요", "버전 실패 → F4"],
    ["F4 되돌리기", "포인터를 백업 값으로 복원하고 해시로 확인", "_backup", "복원 확인 기록", "예(아니면 확인만)", "건너뛰지 않음 · 실패 시 크게 알림"],
    ["F5 RAGAS 채점", "답 있는 행만 6지표 × 3회 채점", "retriever.json", "ragas.json", "아니요", "버전 실패(F3 결과는 남음)"],
    ["F6 검토표", "문항당 1행 검토표 내보내기(판정은 기다리지 않음)", "retriever · ragas.json", "review.csv", "아니요", "버전 실패"],
    ["F7 비교표", "버전 폴더를 모아 버전 × 지표 표", "버전별 로그 3종", "compare.md · .csv", "아니요", "전체 실패(로그는 남음)"],
  ], { y: 1.95, colW: [2.2, 4.4, 2.35, 1.95, 1.4, 2.6], rowH: 0.64, size: 14 });
}

// S06 평가셋 준비 ①
function s06() {
  const s = newSlide({
    title: "평가셋 준비 ① eval-set.md → eval-set.json",
    lead: "사람용 md를 기계용 json으로 바꿈 — 리트리버 평가가 json의 정답 근거로 코드 채점함",
    notes: "eval-set.md 머리말은 기계용 원본이 eval-set.json이라 적었으나 파일이 없음(사용자 결정 D2로 변환을 설계에 포함).\n" +
      "json 형식은 기존 평가셋 group2_questions.json(schema_version 1)과 같게 둠 — evaluate_retriever.py가 그대로 읽음.\n" +
      "R6: 리트리버 코드 채점은 D2 위치만 카드 코드 판정에 씀. D3는 상담 번호만 남겨 기록용으로 둠.",
  });
  table(s, [
    ["eval-set.md 칸", "eval-set.json 필드", "쓰는 곳"],
    ["### Q01. 의 번호", "id", "결과 행 · 비교표"],
    ["제목의 질문 글", "question", "리트리버 질문 · RAGAS user_input"],
    ["정답 본문", "ground_truth", "RAGAS reference"],
    ["정답이 「확인 필요」인가", "answerable (true / false)", "답 없음 문항 판정"],
    ["근거 줄의 파일명", "relevance[].source", "코드 채점 출처 대조"],
    ["근거 줄의 위치(조항 · 혜택 코드)", "relevance[].location", "D2 카드 코드 일치 판정"],
    ["근거 아래 「원문 조각」", "relevance[].any_of[]", "코드 채점 글자 대조"],
    ["filters 줄", "filters[]", "역할 판정(회원 → 감사자)"],
    ["답 없음 확인 낱말 묶음", "no_answer_terms[][]", "검증 ④"],
    ["검토 ☐ · 사람 검토 메모", "(넣지 않음)", "사람 칸"],
  ], { x: X0, y: 1.95, w: 8.6, colW: [3.1, 2.9, 2.6], rowH: 0.53, size: 14 });
  const rx = 9.4, rw = XR - rx;
  headerBar(s, "변환 규칙", { x: rx, y: 1.95, w: rw, h: 0.46, size: 16, accent: true });
  const rules = [
    "근거 줄 1개 = 근거 단위 1개, 그 아래 조각들은 any_of(하나만 맞아도 됨)",
    "Recall 분모 = 근거 단위 수 → 상담 문항 Q14 · Q16 · Q17은 2 ~ 3",
    "답 없음 Q18 ~ Q20: answerable=false · 정답 「확인 필요」 · 근거 비움",
    "filters는 md의 JSON 글을 그대로 옮김(값을 고치지 않음)",
    "D2 위치(D2-C001-B01)는 글자 그대로 — 카드 일치 판정의 열쇠",
    "원문 조각은 「」 안 글자 그대로. 줄바꿈 · 꾸밈 표시만 지움",
  ];
  rules.forEach((r, i) => {
    const y = 2.55 + i * 0.86;
    numBadge(s, i + 1, { x: rx, y: y + 0.12, size: 0.42, fsz: 16 });
    rr(s, { x: rx + 0.55, y, w: rw - 0.55, h: 0.72, fill: i % 2 ? C.white : C.tint });
    text(s, r, { x: rx + 0.65, y, w: rw - 0.75, h: 0.72, size: 14, color: C.body });
  });
}

// S07 평가셋 준비 ②
function s07() {
  const s = newSlide({
    title: "평가셋 준비 ② 검증 5검사 · 평가셋 해시",
    lead: "검사가 하나라도 실패하면 json을 쓰지 않음 — 실행기는 검증을 통과한 평가셋으로만 실험을 시작함",
    notes: "검사 ① ~ ④는 교재 179쪽 노트의 verify_eval_set.py 4검사, ⑤ 구조 검사는 지식니 추가(설계 가정).\n" +
      "세대 의존: 청크 600에서는 근거 문장이 조각 경계에서 잘려 ①이 실패할 수 있음(측정 전, 설계 가정).\n" +
      "평가셋 해시 길이 12자는 설계 가정.",
  });
  table(s, [
    ["검사", "내용", "필요한 것"],
    ["① 글자 대조", "근거 조각이 지정 출처의 색인 본문에 글자 그대로 있는가", "색인 세대"],
    ["② 카드 블록", "D2 문항의 조각이 지정한 혜택 코드 블록 안에 있는가", "색인 세대"],
    ["③ 숫자 대조", "정답에 나온 숫자가 근거 조각 안에 있는가", "평가셋만"],
    ["④ 답 없음", "낱말 묶음을 모두 담은 조각이 색인에 없는가", "색인 세대"],
    ["⑤ 구조", "필수 칸 · id 중복 · answerable과 정답 짝 · 위치 꼴", "평가셋만"],
  ], { x: X0, y: 1.95, w: 9.2, colW: [1.9, 5.6, 1.7], rowH: 0.56, size: 15 });
  const rx = 10.0, rw = XR - rx;
  headerBar(s, "실패하면", { x: rx, y: 1.95, w: rw, h: 0.46, size: 16 });
  rr(s, { x: rx, y: 2.5, w: rw, h: 2.83, fill: C.tint });
  text(s, "· json을 쓰지 않음\n· 실패 목록(문항 · 검사 · 사유) 출력\n· 종료 코드 1\n· 실행기는 실험을 시작하지 않음",
    { x: rx + 0.15, y: 2.6, w: rw - 0.3, h: 2.6, size: 18, color: C.body, valign: "top" });

  headerBar(s, "세대 의존 주의", { x: X0, y: 5.6, w: 7.3, h: 0.46, size: 16, accent: true });
  rr(s, { x: X0, y: 6.12, w: 7.3, h: 1.75, fill: C.white });
  text(s, "검사 ① ② ④는 색인 본문을 읽어 세대마다 결과가 다를 수 있음\n" +
    "· 정식 검증: 기준 세대(청크 800)에서 1회\n· 참고 실행: 청크 600 세대에서 ① → 잘린 문항만 비교표에 주석",
    { x: X0 + 0.15, y: 6.17, w: 7.0, h: 1.65, size: 16, color: C.body, valign: "top" });
  headerBar(s, "평가셋 해시 = 같은 조건 확인", { x: X0 + 7.6, y: 5.6, w: 7.3, h: 0.46, size: 16, accent: true });
  rr(s, { x: X0 + 7.6, y: 6.12, w: 7.3, h: 1.75, fill: C.white });
  text(s, "· 대상: questions 블록 · 키 정렬 · UTF-8\n· SHA-256 앞 12자(설계 가정)\n" +
    "· config.json과 로그 3종 머리에 기록 → 버전끼리 다르면 Δ를 계산하지 않음",
    { x: X0 + 7.75, y: 6.17, w: 7.0, h: 1.65, size: 16, color: C.body, valign: "top" });
}

// S08 ① 버전 정의 — 계획 파일
function s08() {
  const s = newSlide({
    title: "① 버전 정의 — 계획 파일",
    lead: "파일 1개 = 하이퍼 파라미터 1개 = 버전안 표의 한 행. 기준 버전과 비교 버전을 함께 적음",
    notes: "위치 eval-runner/plans/{하이퍼 파라미터}.yaml(교재 185쪽 예시 plans/chunk.yaml).\n" +
      "바꾸는 종류 3종은 교재 186쪽(설정 파일 · 환경변수 · 코드 수정). scoring 값은 같은 조건 원칙으로 실험 끝까지 고정.",
  });
  table(s, [
    ["필드", "뜻", "예", "필수"],
    ["schema_version", "파일 형식 번호", "1", "필수"],
    ["hyperparameter", "하이퍼 파라미터 이름 = 실험 폴더 이름", "chunk_size", "필수"],
    ["apply", "바꾸는 종류: config_file · env · code_arg", "config_file", "필수"],
    ["target", "바꿀 대상 키(② 대상 키 표기)", "indexer:config:…#defaults.chunk_size", "필수"],
    ["reindex", "재색인이 필요한 버전인지", "true", "필수"],
    ["baseline", "기준 버전 값 = 지금 값", "800", "필수"],
    ["versions[].id · value · note", "버전 폴더 이름 · 그 값 · 메모", "\"600\" · 600", "id · value 필수"],
    ["eval_set.path · sha256", "평가셋 경로 · 지문(바뀌면 비교 무효)", "../ragas/eval-set.json", "필수"],
    ["scoring.ragas_provider · ragas_repeat", "RAGAS 평가자 · 반복 수", "local · 3", "필수"],
    ["scoring.human_pass_threshold", "LLM 점수 합격 기준값(사람 비교용)", "0.5(설계 가정)", "필수"],
  ], { y: 1.95, colW: [3.9, 5.2, 4.1, 1.7], rowH: 0.54, size: 15 });
}

// S09 ① 버전안 — 계획 파일 2개
function s09() {
  const s = newSlide({
    title: "① 버전안 — 계획 파일 2개",
    lead: "청크 크기는 설정 파일을 바꿔 재색인, Top-k는 코드에 박힌 값을 인자로 꺼내 다시 실행만 함",
    notes: "버전안은 사용자 결정 D4(임베딩 제외). 청크 크기는 임베딩 입력 상한 800토큰 때문에 800보다 키울 수 없음(인덱서 settings 검사).\n" +
      "기준 800도 새 thread-id로 다시 색인(D6) — 지금 세대에는 만들 때의 설정이 남아 있지 않고 별칭 실험 세대를 바탕으로 만들어짐.\n" +
      "Top-k 허용 범위 1 ~ 10(리트리버 SearchRequest).",
  });
  table(s, [
    ["하이퍼 파라미터", "버전(기준 포함)", "기준", "바꾸는 종류", "재색인"],
    ["청크 크기", "600 · 800 (800보다 못 키움)", "800 — 새로 색인", "설정 파일", "예"],
    ["Top-k", "3 · 5 · 10", "5", "코드 값 → 인자", "아니요"],
  ], { y: 1.95, colW: [2.6, 4.3, 3.0, 2.8, 2.2], rowH: 0.46, size: 15 });
  codeBox(s, [
    "schema_version: 1",
    "hyperparameter: chunk_size",
    "apply: config_file",
    "target: indexer:config:config/document_policies.json",
    "        #defaults.chunk_size",
    "reindex: true",
    "baseline: 800",
    "versions:",
    "  - { id: \"800\", value: 800, note: \"기준 · 새로 색인\" }",
    "  - { id: \"600\", value: 600 }",
    "eval_set: { path: ../ragas/eval-set.json, sha256: … }",
    "scoring: { ragas_provider: local, ragas_repeat: 3,",
    "           human_pass_threshold: 0.5 }",
  ], { x: X0, y: 3.55, w: 7.3, h: 4.35, title: "plans/chunk_size.yaml", size: 16 });
  codeBox(s, [
    "schema_version: 1",
    "hyperparameter: top_k",
    "apply: code_arg",
    "target: retriever:arg:--top-k",
    "reindex: false",
    "baseline: 5",
    "versions:",
    "  - { id: \"3\",  value: 3 }",
    "  - { id: \"5\",  value: 5, note: \"기준\" }",
    "  - { id: \"10\", value: 10, note: \"허용 상한\" }",
    "eval_set: { path: ../ragas/eval-set.json, sha256: … }",
    "scoring: { ragas_provider: local, ragas_repeat: 3,",
    "           human_pass_threshold: 0.5 }",
  ], { x: X0 + 7.6, y: 3.55, w: 7.3, h: 4.35, title: "plans/top_k.yaml", size: 16 });
}

// S10 ① 실행 전 검사
function s10() {
  const s = newSlide({
    title: "① 실행 전 검사",
    lead: "실패 시 동작은 둘뿐 — 거부(아무것도 바꾸지 않고 종료) 또는 미지원(그 버전만 건너뜀)",
    notes: "V10 · V11을 실행 전에 거부하는 이유: 안 하면 재색인을 다 돌린 뒤에야 오류로 죽고, 그 사이 게시가 포인터를 덮어씀.\n" +
      "V14는 사용자 결정 D7 — 리트리버는 포인터를 요청마다 다시 읽어 떠 있는 API 서버가 실험 세대로 넘어감.\n" +
      "확인 방법(설계 가정): 리트리버 API_PORT(기본 8020)에 연결해 응답이 오면 거부. 거부 종료 코드 2(설계 가정).",
  });
  table(s, [
    ["#", "거부 — 실행하지 않음"],
    ["V1", "기준 버전과 값이 1개만 다른가(한 번에 하나)"],
    ["V2", "baseline 값이 versions에 들어 있는가"],
    ["V3", "versions의 id가 겹치지 않는가"],
    ["V4", "apply가 3종 중 하나인가"],
    ["V5 · V6", "평가셋이 있고, 지문이 sha256과 같은가"],
    ["V10", "청크 크기 ≤ 임베딩 입력 상한(800)"],
    ["V11", "Top-k가 1 ~ 10인가"],
    ["V12", "사용 중 세대 포인터를 읽고 백업할 수 있는가"],
    ["V13", "인덱서 · 실행기 잠금을 얻을 수 있는가"],
    ["V14", "같은 DATA_ROOT의 검색 API 서버가 꺼져 있는가"],
  ], { x: X0, y: 1.95, w: 8.4, colW: [1.2, 7.2], rowH: 0.5, size: 15 });
  const rx = 9.25, rw = XR - rx;
  table(s, [
    ["#", "미지원 — 그 버전 건너뜀"],
    ["V7-1", "설정 파일 키가 defaults가 아님(유형별 값은 코드 수정 필요)"],
    ["V8", "env 이름을 도구가 실제로 읽지 않음"],
    ["V9", "code_arg 인자를 도구가 아직 지원하지 않음(--help로 확인)"],
  ], { x: rx, y: 1.95, w: rw, colW: [1.0, rw - 1.0], rowH: 0.62, size: 15 });
  rr(s, { x: rx, y: 4.65, w: rw, h: 3.2, fill: C.tint });
  text(s, "왜 V10 · V11을 먼저 막나", { x: rx + 0.15, y: 4.75, w: rw - 0.3, h: 0.42, size: 16, bold: true, color: C.navy });
  text(s, "재색인을 다 돌린 뒤 마지막에 범위 오류로 죽으면, 그 사이 게시가 사용 중 세대 포인터를 이미 덮어쓴 상태로 남음.\n\n" +
    "미지원은 실패가 아님 — --resume 때 다시 검사해 인자가 생겼으면 실행함",
    { x: rx + 0.15, y: 5.2, w: rw - 0.3, h: 2.55, size: 17, color: C.body, valign: "top" });
}

module.exports = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10];
