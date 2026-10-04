// node build.js [출력 경로] — 품질평가 설계서 빌드
const fs = require("fs");
const path = require("path");
const L = require("./lib");

async function main() {
  const out = process.argv[2] || path.join(__dirname, "품질평가설계서.pptx");
  const pptx = L.createDeck();
  const parts = ["./s01_10", "./s11_20", "./s21_30"].filter((p) => fs.existsSync(path.join(__dirname, p + ".js")));
  for (const p of parts) for (const fn of require(p)) await fn();
  await pptx.writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
