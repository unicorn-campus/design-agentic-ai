import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const runtime='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=runtime+'/node/node_modules';
const require=createRequire(import.meta.url);
const PptxGenJS=require(runtime+'/node/node_modules/pptxgenjs');
const {FileBlob,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
const root='C:/Users/hiond/class/design-agentic-ai';
const build=root+'/.codex-build/publication-slide';
const final=root+'/output/pptx/게시-세대전환-원리와설계-1장.pptx';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const fsMin=n=>{if(n<14)throw Error('Minimum font size 14pt');return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,breakLine:false,vertAnchor:'ctr',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function pageHeader(s,title){text(s,'벡터DB 구성 원리 › 마지막 단계: 게시',.55,.35,14.9,.28,15,{color:C.sub});text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};pageHeader(s,'게시의 원리: 완성된 세대 선택');
 text(s,'세대(generation)는 같은 시점의 벡터·BM25·본문·사전·구성 정보를 묶은 검색 버전입니다.',.55,1.78,14.9,.38,21,{color:C.slate});
 const stages=[['G1 유지','기존의 완성된 검색 묶음'],['G2 별도 구축','새 데이터와 두 색인 준비'],['G2 전체 검증','ID·본문·건수·차원·해시 확인'],['게시 포인터를 G2로','벡터·BM25 경로를 함께 기록']];
 const xs=[.55,4.39,8.23,12.07];
 for(let i=0;i<4;i++){const x=xs[i];rect(s,x,2.45,3.38,.94,i===3?C.navy:C.tint,i===3?C.navy:C.border);text(s,stages[i][0],x+.17,2.61,3.04,.29,22,{bold:true,color:i===3?C.white:C.navy});text(s,stages[i][1],x+.17,3.06,3.04,.23,16,{color:i===3?C.white:C.slate});if(i<3)line(s,x+3.49,2.92,.23,0,C.blue,true,2);}
 text(s,'새 세대를 따로 완성하는 이유는 미완성 데이터 노출과 벡터·BM25의 버전 혼합을 막기 위해서입니다.',.55,3.62,14.9,.31,19,{color:C.slate});
 text(s,'게시 핵심 코드',.55,4.17,7.6,.35,24,{bold:true,color:C.navy});
 text(s,'설계할 때 정의할 항목',8.7,4.17,6.75,.35,24,{bold:true,color:C.navy});
 rect(s,.55,4.76,7.75,2.77,C.navy,C.navy);
 const code=[
 'with CrossPlatformFileLock(self.lock_path):',
 '    current = self._active_pointer()',
 '    active = current["generation"] if current else None',
 '    if active not in {base_generation, generation}:',
 '        raise RuntimeError("기준 세대가 바뀌었습니다.")',
 '    _replace_json(state_path, ready_state)',
 '    _replace_json(self.active_pointer_path, pointer)',
 ];
 for(let i=0;i<code.length;i++)text(s,code[i],.79,5.00+i*.33,7.27,.28,17,{color:C.white});
 text(s,'실제 구현을 줄인 예시 · ready_state는 ready 상태·건수·차원 정보',.55,7.66,7.75,.25,14,{color:C.sub});
 text(s,'_replace_json(): 임시 JSON 저장 → fsync → os.replace()',.55,8.02,7.75,.28,16,{color:C.slate});
 const rows=[
 ['설계 항목','정의할 내용'],
 ['세대 범위','함께 전환할 데이터·색인·모델 설정'],
 ['게시 합격 기준','ID·건수·해시·차원과 검색 품질 기준'],
 ['동시 게시 제어','잠금·기준 세대 검사·충돌 시 재시도'],
 ['검색기 전환','새 세대 감지·재로딩·진행 중 요청 처리'],
 ['보관·복구','보관 기간·삭제 조건·되돌릴 대상과 절차']
 ];
 s.addTable(rows.map((r,i)=>r.map(t=>({text:t,options:{fill:i===0?C.head:(i%2?C.white:C.alt),bold:i===0,color:i===0?C.navy:C.ink}}))),{x:8.7,y:4.76,w:6.75,h:3.07,colW:[1.78,4.97],rowH:[.42,.53,.53,.53,.53,.53],fontFace:FONT,fontSize:fsMin(17),margin:[.07,.12,.07,.12],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});
 text(s,'검색기 자동 경로 전환·보관·롤백 정책은 별도 정의가 필요합니다.',8.7,8.03,6.75,.28,15,{color:C.sub});
 line(s,.55,8.59,14.9,0,C.footer,false,.7);
 text(s,'코드 근거: index_repository.py · publish() / _replace_json() · lexical_index.py',.55,8.68,12.3,.2,14,{color:C.sub});text(s,'게시  /  1',13.0,8.68,2.45,.2,14,{color:C.sub,align:'right'});
 s.addNotes(`세대는 한 시점에 함께 사용할 Chroma 벡터 저장소, BM25 색인, 청크 corpus, 카드명 사전과 manifest를 묶은 버전입니다. G1과 G2는 설명용 세대 이름입니다. 새 세대는 기존 활성 세대와 다른 디렉터리에서 준비합니다. 기존 세대를 만들던 도중 덮어쓰지 않으므로 미완성 산출물이 현재 사용 대상과 섞이는 위험을 줄일 수 있습니다. 이 그림은 게시자의 버전 선택 구조이며 실행 중인 모든 검색기가 즉시 전환한다는 뜻이 아닙니다.\n\n실제 publish 순서는 다음과 같습니다. 먼저 빈 세대와 중복 chunk_id를 거부합니다. Chroma에서 저장된 ID 집합, 본문과 본문 해시, 메타데이터 및 해시, 벡터 행 수와 차원 일관성을 확인합니다. 준비된 BM25 경로, corpus, 카드명 사전, manifest와 stage 증거의 세대·개수·해시를 확인합니다. 준비 단계의 stage가 체크포인트와 generation_state에 기록된 값과 같은지, source_manifest_sha256가 최종 발행 입력과 같은지 비교합니다.\n\n다음으로 .publish.lock을 잡은 짧은 구간에서 현재 활성 세대를 다시 읽습니다. 현재 세대가 이 구축이 시작될 때 기록한 base_generation 또는 이미 게시하려는 generation과 같을 때만 진행합니다. 다른 실행이 먼저 새로운 세대를 게시했다면 오래된 실행의 결과를 거부합니다. ready 상태를 먼저 기록한 뒤 전역 active_generation.json을 마지막에 교체합니다. 포인터에는 generation, chroma_path, search_index_root, collection, chunk_count, embedding_dimension, embedding_signature를 함께 기록합니다.\n\n화면 코드는 실제 구현을 설명용으로 줄인 예시이며 독립 실행 프로그램이나 전체 함수가 아닙니다. current_generation을 active로 줄였고 오류 문구도 줄였습니다. ready_state는 실제 _replace_json(state_path, {...}) 호출의 인라인 dict를 이름 붙인 것으로, {**generation_state, 'status':'ready', 'chunk_count':len(chunks), 'embedding_dimension':dimension}에 해당합니다. pointer는 위에 설명한 두 경로와 세대 정보가 들어 있는 dict입니다. base_generation과 generation, state_path 등은 앞선 코드에서 준비된 값입니다. 앞선 무결성 검증과 포인터 구성은 화면에서 생략했습니다.\n\n_replace_json()은 대상 파일과 같은 디렉터리에 임시 파일을 만들고 JSON을 쓴 뒤 flush와 os.fsync를 호출하고 os.replace로 대상 파일을 교체합니다. 이는 한 파일의 교체 단위를 제공합니다. 두 데이터베이스에 분산 트랜잭션을 실행하는 구현은 아닙니다. 저장장치 장애와 진행 중 요청을 포함한 서비스 전체의 완전 무중단을 이 동작만으로 보장하지 않습니다.\n\n설계 표는 현재 값의 목록이 아니라 설계 시 정해야 할 항목입니다. 현재 구현에는 구조·무결성 검사, 게시 잠금, 기준 세대 비교, 단일 포인터 교체가 있습니다. 검색 품질 평가 기준이나 사람 승인 필요 여부, 충돌 재시도 정책, 세대 감지와 로딩 시점, 진행 중 요청이 사용할 세대 고정, 보관 세대 수·기간, 삭제 보호, 자동 또는 수동 롤백 절차는 목적에 맞게 별도로 정의해야 합니다.\n\n전역 active_generation.json은 새 Chroma 경로와 검색 색인 루트를 함께 가리키지만, 현재 Retriever 앱은 CHROMA_PATH와 SEARCH_INDEX_ROOT를 별도 설정으로 받습니다. VersionedCorpusStore는 설정된 검색 루트의 active_index.json을 읽으며 BM25 인스턴스는 이 세대 변화를 확인합니다. 전역 포인터를 직접 읽어 Chroma와 BM25 두 경로를 함께 자동 전환하는 연동은 확인되지 않았습니다. 따라서 게시 완료만으로 실행 중 검색기의 자동 동시 전환이 구현되었다고 설명하지 않습니다.\n\n포인터 교체 전 검증이나 기준 세대 확인이 실패하면 이전 포인터를 유지합니다. 이것은 이미 게시한 새 세대를 서비스 오류 후 자동으로 되돌리는 롤백 기능과 다릅니다. publish는 이전 세대 디렉터리를 자동 삭제하지 않으며 보관 기간과 정리 정책도 포함하지 않습니다. 이번 슬라이드 작업에서는 실제 게시나 장애 복구를 실행하지 않았습니다.\n\n소스 근거:\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:53–68 (_replace_json)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:155–181 (별도 세대 준비와 기준 세대 기록)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:299–328 (Chroma 검사)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:427–505 (publish)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py:397 (텍스트 색인 검증)\nhybrid-ai-lab/retriever/vector-retriever/app/infrastructure/settings.py:122–139 (저장소 경로 설정)\nhybrid-ai-lab/retriever/vector-retriever/app/infrastructure/corpus_store.py:30–35 (active_index 읽기)\nhybrid-ai-lab/retriever/vector-retriever/app/infrastructure/bm25_index.py:43–99 (텍스트 세대 읽기)`);
}
async function main(){
 await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(final),{recursive:true});pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';pptx.author='design-agentic-ai';pptx.title='게시의 원리: 완성된 세대 선택';pptx.subject='세대 의미, 게시 방법과 코드, 설계 시 정의할 항목';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();const candidate=build+'/candidate.pptx';await pptx.writeFile({fileName:candidate});const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
 const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[],pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--require-native-table-slide','1'],fontPolicy:{basis:'user_request',families:[FONT]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
 const p=await PresentationFile.importPptx(await FileBlob.load(final));const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});await fs.writeFile(root+'/output/pptx/게시-세대전환-원리와설계-1장.png',new Uint8Array(await png.arrayBuffer()));console.log(JSON.stringify({final,checks:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
}
main().catch(e=>{console.error(e);process.exit(1);});
