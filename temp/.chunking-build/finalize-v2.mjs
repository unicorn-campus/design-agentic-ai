import {finalizePresentation} from 'file:///C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations/container_tools/artifact_tool_utils.mjs';
const root='C:/Users/hiond/class/design-agentic-ai';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
process.env.RUNTIME_NODE_MODULES='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const result=await finalizePresentation({
 workspaceDir:root,
 candidatePath:`${root}/temp/.chunking-build/candidate-v2.pptx`,
 finalPath:`${root}/temp/chunking_design_best_practices_v2.pptx`,
 pythonExecutable:'C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:`${skill}/container_tools/inspect_presentation_package_integrity.py`,
 layoutValidatorPath:`${skill}/container_tools/inspect_presentation_layout_geometry.py`,
 layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','2'],
 explicitTotalSlideCount:3,
 requiredNativeTableOwnerSlides:[2],
 requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'user_request',families:['Pretendard']},
 verifyArtifactToolImport:true,
 receiptPath:`${root}/.temp/chunking_slides_v2_validation.json`,
});
console.log(JSON.stringify({file:result.finalPath,integrity:result.packageIntegrity.status,layout:result.presentationLayout}));
