import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/.build/candidate-v5-reviewed.pptx'));
await fs.mkdir(root+'/.build/v5-rendered',{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 await fs.writeFile(root+'/.build/v5-rendered/slide-'+String(i+1).padStart(2,'0')+'.png',Buffer.from(await(await p.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
 console.log('Rendered',i+1);
}
