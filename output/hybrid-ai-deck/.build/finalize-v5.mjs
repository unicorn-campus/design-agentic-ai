import {pathToFileURL} from 'node:url';
const root='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
process.env.RUNTIME_NODE_MODULES='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const owners=[11,12,16,17,25,28,30,31,35,42,46,47,49,50,54];
const r=await finalizePresentation({workspaceDir:root,candidatePath:root+'/.build/candidate-v5-reviewed.pptx',finalPath:root+'/final/신한카드 하이브리드AI_교육용최종_소스대조완료.pptx',explicitTotalSlideCount:58,pythonExecutable:'C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--validate-bullet-geometry',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:owners,verifyArtifactToolImport:true,receiptPath:root+'/.build/validation-v5-reviewed.json'});
console.log(JSON.stringify({file:r.finalPath,integrity:r.packageIntegrity.status,layout:r.presentationLayout.findingCount}));
