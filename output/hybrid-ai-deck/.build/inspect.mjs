import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const dir = 'C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck/.build';
const p = await PresentationFile.importPptx(await FileBlob.load('C:/Users/hiond/Documents/강의/신한카드/신한카드 하이브리드AI.pptx'));
await fs.writeFile(dir+'/inspect.ndjson',(await p.inspect({kind:'slide,layout',maxChars:100000})).ndjson);
for (let i=0;i<p.slides.items.length;i++) {
 const sl=p.slides.items[i];
 await fs.writeFile(`${dir}/source-${i+1}.png`,new Uint8Array(await (await sl.export({format:'png',scale:0.8})).arrayBuffer()));
 console.log('rendered',i+1);
}
