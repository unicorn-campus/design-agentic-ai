import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/hiond/class/design-agentic-ai';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/output/pptx/임베딩-원리와-모델-1장.pptx'));
const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});
await fs.writeFile(root+'/output/pptx/임베딩-원리와-모델-1장.png',new Uint8Array(await png.arrayBuffer()));
console.log('Final slide rendered');
