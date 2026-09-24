import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const src = "C:/Users/hiond/class/design-agentic-ai/docs/plan/think/em/Event-Modeling-4단계-커맨드-완료예시-표형식-v4.pptx";
const out = "C:/Users/hiond/class/design-agentic-ai/.codex-build/swimlane-matrix";
const p = await PresentationFile.importPptx(await FileBlob.load(src));
const snap = await p.inspect({kind:"slide,textbox,shape,table,layout",maxChars:30000});
await fs.writeFile(`${out}/source-inspect.ndjson`, snap.ndjson);
const montage = await p.export({format:"png",montage:{format:"png",columns:2,slideWidth:800,padding:20,gap:20,background:"#E9ECF3"}});
await fs.writeFile(`${out}/source-montage.png`, new Uint8Array(await montage.arrayBuffer()));
for (let i=0;i<p.slides.items.length;i++) {
 const s=p.slides.getItem(i);
 const png=await s.export({format:"png",scale:1.5});
 await fs.writeFile(`${out}/source-slide-${i+1}.png`,new Uint8Array(await png.arrayBuffer()));
 const layout=await s.export({format:"layout"});
 await fs.writeFile(`${out}/source-slide-${i+1}.layout.json`,await layout.text());
}
console.log(JSON.stringify({slides:p.slides.items.length, frame:p.slides.getItem(0).frame},null,2));
