// MIN_FONT=13 node build.js [출력 경로] — 품질평가 소스설명서 빌드(먼저 python extract.py)
const path = require("path");
const K = require("./common");

async function main() {
  const out = process.argv[2] || path.join(__dirname, "품질평가_소스설명.pptx");
  const pptx = K.createDeck();
  K.coverSlide({
    label: "hybrid-ai-lab / ragas",
    title: "품질평가 프로그램 주요 소스 해설",
    subtitle: "평가셋 준비 · 버전 실험 실행기 · 코드 채점 5지표 · RAGAS 4지표 · 사람 검토표 · 비교표",
    mark: "QA",
    meta: "design-agentic-ai · 2026-10-04",
    notes: "제목 장표. 사용자 요청으로 추가(같은 '내용_단쪽' 레이아웃에 배경을 덮어 붙여넣기 호환을 유지).",
  });
  for (const fn of [...require("./src1"), ...require("./src2")]) await fn();
  await pptx.writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
