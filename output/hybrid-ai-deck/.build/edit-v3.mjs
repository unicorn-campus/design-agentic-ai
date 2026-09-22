import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const source=root+'/final/신한카드 하이브리드AI_워크플로우_노드별상세_v2.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const snap=await p.inspect({kind:'slide,textbox,layout',maxChars:1000000});
await fs.writeFile(root+'/.build/v3-before.ndjson',snap.ndjson);
const records=snap.ndjson.split('\n').filter(Boolean).map(x=>JSON.parse(x));
const anchor=records.find(x=>x.kind==='slide'&&x.slide===39);
if(!anchor)throw Error('39페이지 미발견');
const s=p.resolve(anchor.id);
const code=`def _run_search_transformed(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
    groups, warnings = [], []
    for query in state.get("transformed_queries", []):
        try:
            groups.append(self._search_one(query, state))
        except Exception as error:
            groups.append([])
            warnings.append(f"변환 질의 검색 실패: {type(error).__name__}")
    return {"transformed_hit_groups": groups, "warnings": warnings}`;
const replacements=[
 ['search_transformed  :  원본 자료의 검색 코드','search_transformed  :  변환 질문 검색 실행 코드'],
 ['원본 핵심 코드 보존용이며, 아래 주의사항과 다음 페이지의 현재 구현을 함께 확인','변환 질문을 순서대로 검색하고, 질문별 결과와 실패 경고를 반환'],
 ['원본과 현재의 차이: vector_rerank도 Vector만 검색하며, top_k 대신 fused_k까지 후보 유지','실패한 질문은 빈 목록으로 위치 유지  /  warnings에 예외 종류 기록  /  단일 질문 검색은 다음 페이지'],
];
for(const [from,to]of replacements){const sh=s.shapes.items.find(x=>String(x.text??'')===from);if(!sh)throw Error('기존 문자열 미발견: '+from);sh.text=to;}
const sh=s.shapes.items.find(x=>String(x.text??'').startsWith('sizes = self._candidate_sizes(state)'));
if(!sh)throw Error('기존 코드 미발견');sh.text=code;
s.speakerNotes.textFrame.setText(`노드: search_transformed\n함수: _run_search_transformed\n변환 질문을 입력 순서대로 하나씩 _search_one에 전달함. 성공 결과는 groups에 추가함. 실패 시 빈 목록으로 질문과 결과의 위치 대응을 유지하며 예외 클래스명을 warnings에 기록함. 실패 후에도 다음 질문을 처리함. 결과는 transformed_hit_groups와 warnings로 반환함.\n단일 질문의 검색 방식은 다음 페이지 _search_one에서 설명함.\n출처: 사용자 제공 코드 및 hybrid-ai-lab/vector/retriever/app/application/graph.py\n\n${code}`);
await fs.writeFile(root+'/.build/v3-expected-code.txt',code);
await(await PresentationFile.exportPptx(p)).save(root+'/.build/candidate-v3.pptx');
await fs.mkdir(root+'/.build/v3-rendered',{recursive:true});
const scan=[];
for(let i=0;i<p.slides.items.length;i++){
 const png=Buffer.from(await(await p.slides.items[i].export({format:'png',scale:1})).arrayBuffer());
 const name=`slide-${String(i+1).padStart(2,'0')}.png`;
 await fs.writeFile(root+'/.build/v3-rendered/'+name,png);
 const before=await fs.readFile(root+'/.build/v2-rendered/'+name);
 scan.push({page:i+1,unchanged:before.equals(png)});
}
await fs.writeFile(root+'/.build/v3-render-comparison.json',JSON.stringify(scan,null,2));
console.log('Changed renders',scan.filter(x=>!x.unchanged));
process.env.RUNTIME_NODE_MODULES='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const owners=[11,12,16,17,25,28,30,31,35,42,47,49,50];
const result=await finalizePresentation({workspaceDir:root,candidatePath:root+'/.build/candidate-v3.pptx',finalPath:root+'/final/신한카드 하이브리드AI_워크플로우_노드별상세_v3.pptx',pythonExecutable:'C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-bullet-geometry','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:owners,verifyArtifactToolImport:true,receiptPath:root+'/.build/validation-v3.json'});
console.log(JSON.stringify({finalPath:result.finalPath,sha256:result.finalSha256,package:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
