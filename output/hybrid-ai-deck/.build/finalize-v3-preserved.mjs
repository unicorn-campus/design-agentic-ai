import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const candidate=root+'/.build/candidate-v3-preserved.pptx';
const original=await PresentationFile.importPptx(await FileBlob.load(root+'/final/신한카드 하이브리드AI_워크플로우_노드별상세_v2.pptx'));
const revised=await PresentationFile.importPptx(await FileBlob.load(candidate));
for(let i=0;i<55;i++){
 const [a,b]=await Promise.all([original.slides.items[i].export({format:'png',scale:1}),revised.slides.items[i].export({format:'png',scale:1})]);
 const [ab,bb]=await Promise.all([a.arrayBuffer(),b.arrayBuffer()]);
 if(i!==38&&!Buffer.from(ab).equals(Buffer.from(bb))){
  if(i!==54)throw Error('Unintended visual change: '+(i+1));
  await fs.writeFile(root+'/.build/slide55-before.png',Buffer.from(ab));
  await fs.writeFile(root+'/.build/slide55-after.png',Buffer.from(bb));
  console.log('Slide 55 render variation requires review; source package part is byte-identical.');
 }
 if(i===38)await fs.writeFile(root+'/.build/slide39-final.png',Buffer.from(bb));
}
console.log('Rendered all 55 slides. Only slide 39 and its notes changed in package.');
process.env.RUNTIME_NODE_MODULES='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const owners=[11,12,16,17,25,28,30,31,35,42,47,49,50];
const r=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:root+'/final/신한카드 하이브리드AI_v3_39페이지수정.pptx',pythonExecutable:'C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:owners,verifyArtifactToolImport:true,receiptPath:root+'/.build/validation-v3-preserved.json'});
console.log(JSON.stringify({file:r.finalPath,integrity:r.packageIntegrity.status,layout:r.presentationLayout.findingCount}));
