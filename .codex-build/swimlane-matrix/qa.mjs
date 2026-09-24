import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const src="C:/Users/hiond/class/design-agentic-ai/docs/plan/think/em/Event-Modeling-작성예시-스윔레인매트릭스-v1.pptx";
const out="C:/Users/hiond/class/design-agentic-ai/.codex-build/swimlane-matrix/final";
await fs.mkdir(out,{recursive:true});
const p=await PresentationFile.importPptx(await FileBlob.load(src));
const snap=await p.inspect({kind:"slide,textbox,shape,table,notes,layout",maxChars:50000});
await fs.writeFile(`${out}/inspect.ndjson`,snap.ndjson);
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.getItem(i);
 const png=await s.export({format:"png",scale:1.5});
 await fs.writeFile(`${out}/slide-${i+1}.png`,new Uint8Array(await png.arrayBuffer()));
}
const montage=await p.export({format:"png",montage:{format:"png",columns:2,slideWidth:800,padding:20,gap:20,background:"#E9ECF3"}});
await fs.writeFile(`${out}/montage.png`,new Uint8Array(await montage.arrayBuffer()));
console.log(`slides=${p.slides.items.length}`);
