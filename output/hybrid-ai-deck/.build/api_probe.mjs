import { FileBlob, PresentationFile } from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/hiond/Documents/강의/신한카드/신한카드 하이브리드AI.pptx'));
for (const [name,obj] of Object.entries({slides:p.slides,slide:p.slides.items[4],shapes:p.slides.items[4].shapes,shape:p.slides.items[4].shapes.items[0],images:p.slides.items[3].images})) console.log(name,Object.getOwnPropertyNames(Object.getPrototypeOf(obj)));
console.log('frame',p.slides.items[4].frame);
console.log('shape sample',p.slides.items[4].shapes.items.map(x=>({name:x.name,text:String(x.text),pos:x.position})).slice(0,4));
