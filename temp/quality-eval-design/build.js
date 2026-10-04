// node build.js [출력 경로] — 품질평가 설계서 빌드
const fs = require("fs");
const path = require("path");
const L = require("./lib");

async function main() {
  const out = process.argv[2] || path.join(__dirname, "품질평가설계서.pptx");
  const pptx = L.createDeck();
  L.coverSlide({
    label: "품질평가 설계 실습 예제 · 버전 실험형",
    title: "품질평가 프로그램 설계서",
    subtitle: "버전 정의 · 설정 적용 · 실행 · 채점(코드 · RAGAS · 사람) · 기록 · 비교",
    mark: "QA",
    meta: "hybrid-ai-lab / ragas · design-agentic-ai · 2026-10-04",
    notes: "제목 장표. 사용자 요청으로 추가(가이드는 새 덱 표지를 만들지 않지만, 같은 '내용_단쪽' 레이아웃에 배경을 덮어 붙여넣기 호환을 유지).",
  });
  const parts = ["./s01_10", "./s11_20", "./s21_30"].filter((p) => fs.existsSync(path.join(__dirname, p + ".js")));
  for (const p of parts) for (const fn of require(p)) await fn();
  await pptx.writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
