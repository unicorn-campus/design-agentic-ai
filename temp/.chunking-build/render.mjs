import fs from 'node:fs/promises';
import {FileBlob, PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const dir='C:/Users/hiond/class/design-agentic-ai/temp/.chunking-build';
const file=process.argv[2] || `${dir}/candidate.pptx`;
const deck=await PresentationFile.importPptx(await FileBlob.load(file));
await fs.mkdir(`${dir}/renders`,{recursive:true});
for(let i=0;i<deck.slides.items.length;i++){
 const png=await deck.export({slide:deck.slides.items[i],format:'png',scale:1});
 await fs.writeFile(`${dir}/renders/slide-${i+1}.png`,new Uint8Array(await png.arrayBuffer()));
 console.log(`rendered ${i+1}`);
}
