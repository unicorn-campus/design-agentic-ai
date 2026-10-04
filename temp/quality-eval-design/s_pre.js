// 사전작업 — 상담 검색 회원 필터(품질평가 전에 리트리버에 먼저 넣은 변경, 사용자 결정 2026-10-04)
const L = require("./lib");
const { newSlide, rr, text, card, headerBar, numBadge, arrow, table, callout, C, X0, CW, XR } = L;

// 사전작업 ① 왜 · 무엇
function pre1() {
  const s = newSlide({
    title: "사전작업 ① 상담 검색 회원 필터와 상담 판정",
    lead: "회원번호를 요청에 함께 보내 상담은 그 회원 것만 찾고, 찾은 상담은 리랭크 점수가 아니라 '융합 1위'로 판정해 전체를 답변에 씀",
    notes: "품질평가 전에 리트리버(vector-retriever)에 먼저 넣은 변경. 사용자 결정 2026-10-04: 상담 이력만 그 회원 것으로 좁힘(약관 · 혜택은 그대로),\n" +
      "평가셋 Q14 ~ Q17 filters에 member_id 추가, 문서 검색 설계서는 그대로 두고 이 덱의 사전작업으로 기록.\n" +
      "가명 = 'm_' + SHA-256(회원번호) 앞 16자리 — 인덱서 text_rules.pseudonym과 같은 식. M-1042 → m_59853c3d8e1e3c25, M-3001 → m_3cc2d20f17401234(색인 값과 대조).\n" +
      "사용자 결정 2026-10-05: 회원번호는 채점 핵심어에서 뺌, '3번 확장'(상위 k 자르기 · 판정을 융합 순위로), 그 회원 상담 전체를 날짜순으로 C-04에 넘김(사전작업 ③).",
  });
  const w = 7.3, gap = 0.3;
  const cols = [
    { head: "전 — 질문 글로만 찾음", rows: [
      ["① 질문", "\"M-1042 회원은 … 왜 원하지 않았나요?\" — 회원번호는 글자로만 들어감"],
      ["② 검색 범위", "상담 48건 전체(회원 12명) — 다른 회원 상담이 상위 5에 섞임"],
      ["③ 채점(S-R5)", "회원번호를 핵심어로 찾음 · 상담은 리랭크 0점대 → '확인 필요'"],
      ["④ 답변 재료(C-04)", "채점을 통과한 조각만 · 상담 날짜가 없어 첫 · 최근 상담을 못 가림"]] },
    { head: "후 — 회원 필터 + 상담 판정(구현)", rows: [
      ["① 요청 = 질문 + member_id", "가명 계산(S-R1): m_ + SHA-256 앞 16자리 → m_59853c3d8e1e3c25"],
      ["② 검색 조건(S-R4)", "'상담이면 그 회원' 조건 · 융합 1위가 상담이면 상담 먼저 상위 5"],
      ["③ 판정(S-R5)", "회원번호는 핵심어에서 뺌 · 융합 1위가 그 회원 상담이면 '정확'"],
      ["④ 답변 재료(C-04)", "그 회원 상담 전체를 날짜순으로, 제목에 날짜와 상담ID를 붙여 넘김"]] },
  ];
  cols.forEach((c, ci) => {
    const x = X0 + ci * (w + gap);
    headerBar(s, c.head, { x, y: 1.95, w, h: 0.55, size: 19, accent: ci === 1 });
    c.rows.forEach(([t, d], i) => {
      const y = 2.62 + i * 0.98;
      rr(s, { x, y, w, h: 0.84, fill: ci === 1 ? C.tint : C.altRow });
      text(s, t, { x: x + 0.15, y: y + 0.03, w: w - 0.3, h: 0.38, size: 16, bold: true, color: C.navy });
      text(s, d, { x: x + 0.15, y: y + 0.41, w: w - 0.3, h: 0.4, size: 14, color: C.body, valign: "top" });
      if (i < 3) L.arrow(s, { x1: x + w / 2, y1: y + 0.84, x2: x + w / 2, y2: y + 0.98, color: C.blue, width: 2 });
    });
  });
  card(s, "→ 다른 회원 상담이 섞이고, 본인 상담도 채점에서 떨어짐", { x: X0, y: 6.6, w, h: 0.55, fill: C.white, line: C.dark,
    size: 16, bold: true, color: C.ink });
  card(s, "→ 상담은 그 회원 것 전체로 답함, 약관 · 혜택은 그대로", { x: X0 + w + gap, y: 6.6, w, h: 0.55, fill: C.tint,
    line: C.blue, size: 16, bold: true, color: C.blue });
  rr(s, { x: X0, y: 7.3, w: CW, h: 0.85, fill: C.white });
  text(s, "주의  가명 계산이 인덱서와 다르면 오류 없이 결과만 빔 → 'M-1042 → m_59853c3d8e1e3c25' 시험으로 두 프로그램을 묶음\n" +
    "주의  상담 질문은 리랭크 관문이 없음 → 지어낸 답은 C-04 · 근거 검증(S-R8)이 막음 · 권한은 여전히 역할이 정함",
    { x: X0 + 0.15, y: 7.33, w: CW - 0.3, h: 0.79, size: 14, color: C.body });
}

// 사전작업 ② 바꾼 곳 · 확인 결과
function pre2() {
  const s = newSlide({
    title: "사전작업 ② 바꾼 곳과 확인 결과",
    lead: "계층마다 맡은 일만 바꿈 — 상담 규칙은 회원 필터가 있을 때만 켜지고, 검색기가 빠뜨려도 응용 계층이 한 번 더 거름",
    notes: "실측 2026-10-04: 같은 질문을 필터 없이 · 있게 검색한 상위 5개의 다른 회원 상담 수 Q14 4 → 0, Q15 3 → 0, Q16 2 → 0, Q17 5 → 0.\n" +
      "실측 2026-10-05(평가셋 v3 22문항, 답변 생성 켬, logs/eval-member-consult.json): 최종 근거 Hit 0.706 → 0.882, 상담 4문항 모두 정답 근거로 답함,\n" +
      "답 없음 5문항 모두 '확인 필요'(회원 질문 Q21은 C-04가 답변 0문장, Q22는 융합 1위가 약관이라 점수 규칙으로 걸러짐).\n" +
      "시험: 리트리버 212건(회원 필터 · 상담 규칙 20건 포함) · ragas 49건 통과. 같은 실행에서 Q07 · Q08은 C-04 시간 초과(검색 · 근거는 정답).",
  });
  table(s, [
    ["계층", "바꾼 곳", "하는 일"],
    ["domain", "member.py(새로)", "회원번호 꼴 · 가명 · 그 회원 범위 · 상담 1위 판정 · 날짜순"],
    ["domain", "SourceInfo", "상담ID · 상담 날짜를 담아 조각 제목에 붙임"],
    ["application", "SearchRequest.member_id · S-R1", "꼴이 틀리면 invalid_input, 맞으면 가명만 저장"],
    ["application", "S-R4 검색", "회원 조건 전달 · 결과 재확인 · 상담 1위면 상담 먼저"],
    ["application", "S-R5 채점", "회원번호 핵심어 제외 · 상담 1위면 '정확' · 상담 전체 근거"],
    ["application", "S-R7 · 포트 consult_history", "그 회원 상담 전체를 날짜순으로 C-04에 넘김"],
    ["infrastructure", "index_store", "Chroma 조건 · BM25 거르기 · 상담 이력 · 날짜 읽기"],
    ["presentation", "API 본문 · CLI --member-id", "역할 헤더는 그대로 — 권한은 늘지 않음"],
    ["감사 로그", "member_pseudo_id · rule", "가명만 남김 · 상담 규칙 통과는 rule로 표시"],
    ["평가", "evaluate_retriever.py · eval-set v3", "Q14 ~ Q17에 member_id · 답 없음 회원 질문 Q21 · Q22"],
  ], { x: X0, y: 1.95, w: 9.4, colW: [1.6, 3.15, 4.65], rowH: 0.465, size: 14 });
  const rx = X0 + 9.7, rw = XR - rx;
  const tiles = [["4 → 0", "다른 회원 상담(상위 5)", "Q14 기준 · Q15 3 · Q16 2 · Q17 5건도 0"],
    ["0.706 → 0.882", "최종 근거 Hit(22문항)", "상담 4문항 모두 정답 근거로 답함"],
    ["212건", "리트리버 시험 통과", "회원 필터 · 상담 규칙 20건 포함"]];
  tiles.forEach(([big, label, sub], i) => {
    const y = 1.95 + i * 1.98;
    rr(s, { x: rx, y, w: rw, h: 1.8, fill: C.tint });
    text(s, big, { x: rx, y: y + 0.1, w: rw, h: 0.7, size: 26, bold: true, color: C.blue, align: "center" });
    text(s, label, { x: rx, y: y + 0.82, w: rw, h: 0.42, size: 15, bold: true, color: C.navy, align: "center" });
    text(s, sub, { x: rx + 0.1, y: y + 1.24, w: rw - 0.2, h: 0.5, size: 14, color: C.slate, align: "center", valign: "top" });
  });
  callout(s, "평가셋 지문 253f89d84905 → 90681b2f4fae → 0fdb90cdd27c — 계획 파일 sha256을 고쳤고, 이전 실험과는 '평가셋 다름'",
    { x: X0, y: 7.2, w: 9.4, h: 0.7, size: 14 });
}

// 사전작업 ③ 상담 질문 판정 · 답변 재료(사용자 결정 2026-10-05)
function pre3() {
  const s = newSlide({
    title: "사전작업 ③ 상담 질문 판정과 답변 재료",
    lead: "검색은 정답 상담을 1위로 찾았는데 채점에서 막힘 — 상담 질문은 리랭크 점수 대신 '융합 1위가 그 회원 상담'으로 판정",
    notes: "실측 2026-10-05. 막힌 곳 두 가지: ① 회원번호(M-1042 · 1042)가 채점 핵심어로 뽑혀 가명만 담긴 본문에서 항상 '없음'(Q15 1위 0.763 · 격차 0.73인데 탈락),\n" +
      "② 리랭커는 직접 답하는 문장을 재는데 상담 질문은 해석이 필요 — Q17 정답 줄 '무조건 편하다고 설명하지는 마세요'에 원래 질문 0.002, 직접 물으면 0.990.\n" +
      "토큰 상한(1024) 잘림 아님(조각 324 ~ 381토큰), 정답 줄만 넣어도 0.000 ~ 0.002. 상담 본문에는 날짜가 없어(인덱서가 머리말 제거) 메타데이터 consult_date · record_id를 제목에 붙임.\n" +
      "평가 1회(v3 22문항, 답변 생성 켬): 최종 근거 Hit 0.706 → 0.882, 상담 4문항 모두 정답 근거로 답함. 답 없음 회원 질문 Q21은 C-04가 답변 0문장 → '확인 필요', Q22는 융합 1위가 약관이라 점수 규칙으로 걸러짐.\n" +
      "남은 한계: Q14 뒷부분(질문 '해지' ↔ 상담 '정리')을 LLM이 비워 둠, Q16 · Q17 정답 일부 빠짐. 상담 질문은 S-R5 관문 없이 C-04 · S-R8이 막음.",
  });
  // 왼쪽: 무엇을 바꿨나(세 단계)
  const lw = 9.4;
  headerBar(s, "바꾼 규칙 — 회원 필터가 있을 때만", { x: X0, y: 1.95, w: lw, h: 0.55, size: 19, accent: true });
  const steps = [
    ["핵심어", "회원번호는 채점 핵심어에서 뺌 — 이미 검색 조건으로 쓰였음"],
    ["S-R4 자르기", "융합 1위가 그 회원 상담이면 상위 5를 상담 먼저(융합 순)로 채움"],
    ["S-R5 판정", "같은 조건이면 리랭크 점수 대신 이 사실로 '정확' — 약관 · 혜택은 하한 0.3 그대로"],
    ["C-04 재료", "그 회원 상담 전체를 날짜순으로, 제목에 '상담 2026-03-02 (C-…)'를 붙여 넘김"],
  ];
  steps.forEach(([t, d], i) => {
    const y = 2.65 + i * 1.05;
    rr(s, { x: X0, y, w: lw, h: 0.9, fill: C.tint });
    numBadge(s, i + 1, { x: X0 + 0.15, y: y + 0.24 });
    text(s, t, { x: X0 + 0.7, y: y + 0.05, w: 2.0, h: 0.8, size: 16, bold: true, color: C.navy });
    text(s, d, { x: X0 + 2.7, y: y + 0.05, w: lw - 2.85, h: 0.8, size: 14, color: C.body });
  });
  callout(s, "왜: 정답 줄도 리랭크 0.002(직접 물으면 0.990) · 상담 본문에는 날짜가 없음",
    { x: X0, y: 6.95, w: lw, h: 0.6, size: 14 });
  // 오른쪽: 결과
  const rx = X0 + 9.7, rw = XR - rx;
  const tiles = [["0.706 → 0.882", "최종 근거 Hit(22문항)", "상담 4문항 모두 정답 근거로 답함"],
    ["5 / 5", "답 없음 '확인 필요'", "회원 질문 Q21 · Q22 포함(v3에 추가)"],
    ["남은 한계", "답변이 일부 빠짐", "Q14 '해지' ↔ 상담 '정리' 등"]];
  tiles.forEach(([big, label, sub], i) => {
    const y = 1.95 + i * 1.98;
    rr(s, { x: rx, y, w: rw, h: 1.8, fill: i === 2 ? C.white : C.tint, dash: i === 2 ? "dash" : undefined });
    text(s, big, { x: rx, y: y + 0.1, w: rw, h: 0.7, size: 26, bold: true, color: i === 2 ? C.dark : C.blue, align: "center" });
    text(s, label, { x: rx, y: y + 0.82, w: rw, h: 0.42, size: 15, bold: true, color: C.navy, align: "center" });
    text(s, sub, { x: rx + 0.1, y: y + 1.24, w: rw - 0.2, h: 0.5, size: 14, color: C.slate, align: "center", valign: "top" });
  });
}

module.exports = [pre1, pre2, pre3];
