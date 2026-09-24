import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";
const src="C:/Users/hiond/class/design-agentic-ai/docs/plan/think/em/Event-Modeling-7단계-시나리오-구체화.pptx";
const out="C:/Users/hiond/class/design-agentic-ai/.codex-build/scenario-spec/final";
await fs.mkdir(out,{recursive:true});
const p=await PresentationFile.importPptx(await FileBlob.load(src));
const snap=await p.inspect({kind:"slide,textbox,table,notes,layout",maxChars:50000});
await fs.writeFile(`${out}/inspect.ndjson`,snap.ndjson);
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.slides.getItem(i).export({format:"png",scale:1.5});
 await fs.writeFile(`${out}/slide-${i+1}.png`,new Uint8Array(await png.arrayBuffer()));
}
const montage=await p.export({format:"png",montage:{format:"png",columns:2,slideWidth:900,padding:20,gap:20,background:"#E9ECF3"}});
await fs.writeFile(`${out}/montage.png`,new Uint8Array(await montage.arrayBuffer()));
console.log(`slides=${p.slides.items.length}`);
