import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
process.env.RUNTIME_NODE_MODULES='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const root='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const owners=[6,8,9,10,15,17,18,20,21,24,26];
await fs.mkdir(root+'/final',{recursive:true});
console.log(await finalizePresentation({
 workspaceDir:root,candidatePath:root+'/.build/candidate.pptx',
 finalPath:root+'/final/신한카드 하이브리드AI_소스기반_개정본.pptx',
 pythonExecutable:'C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-bullet-geometry','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],
 requiredNativeTableOwnerSlides:owners,
 verifyArtifactToolImport:true,
 receiptPath:root+'/.build/validation.json'
}));
