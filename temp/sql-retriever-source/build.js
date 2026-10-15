// MIN_FONT=13 node build.js [출력 경로] — SQL 검색기 소스설명서 빌드(먼저 python extract.py)
const path = require("path");
const K = require("./common");

async function main() {
  const out = process.argv[2] || path.join(__dirname, "out", "sql-retriever_소스설명.pptx");
  const pptx = K.createDeck();
  K.coverSlide({
    label: "workspace / crc / sql-retriever",
    title: "SQL 검색기 주요 소스 해설",
    subtitle: "LangGraph 6단계 흐름, 정형쿼리 또는 NL2SQL 계획, SQL 검증, 읽기 전용 실행",
    mark: "SQL",
    meta: "design-agentic-ai  |  2026-10-15  |  소스 기준: 커밋 3bc94db",
    notes: "제목 장표(사용자 결정 2026-10-15). 같은 '내용_단쪽' 레이아웃에 배경을 덮어 붙여넣기 호환을 유지함.",
  });
  for (const fn of [...require("./src1"), ...require("./src2")]) await fn();
  await pptx.writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
