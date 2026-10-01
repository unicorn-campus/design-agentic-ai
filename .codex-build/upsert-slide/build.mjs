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
const build=root+'/.codex-build/upsert-slide';
const final=root+'/output/pptx/벡터DB-upsert-코드예제-1장.pptx';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const fsMin=n=>{if(n<14)throw Error('Minimum font size 14pt');return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,breakLine:false,vertAnchor:'ctr',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function pageHeader(s,title){text(s,'벡터DB 구성 원리 › 적재',.55,.35,14.9,.28,15,{color:C.sub});text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};pageHeader(s,'벡터DB에 upsert로 저장하기');
 text(s,'같은 컬렉션에서 ID가 있으면 갱신하고, 없으면 새로 추가합니다.',.55,1.78,14.9,.38,22,{color:C.slate});
 text(s,'우리 코드의 Chroma 호출',.55,2.32,9,.38,24,{bold:true,color:C.navy});
 text(s,'함께 저장하는 네 가지 값',10.05,2.32,5.4,.38,24,{bold:true,color:C.navy});
 rect(s,.55,2.94,9.1,3.38,C.navy,C.navy);
 const code=[
 'ids = [chunk.chunk_id for chunk in chunks]',
 'collection = self._open(generation)',
 'collection.upsert(',
 '    ids=ids,',
 '    documents=[chunk.text for chunk in chunks],',
 '    embeddings=vectors,',
 '    metadatas=[',
 '        _clean_metadata(chunk.metadata, chunk.chunk_id)',
 '        for chunk in chunks',
 '    ],',
 ')'];
 for(let i=0;i<code.length;i++)text(s,code[i],.80,3.10+i*.273,8.58,.26,18,{color:C.white});
 const rows=[['인자','저장하는 내용'],['ids','청크를 구별하는 고유 ID'],['documents','정제된 청크 본문'],['embeddings','미리 계산한 본문의 벡터'],['metadatas','출처·페이지 등 부가정보']];
 s.addTable(rows.map((r,i)=>r.map(t=>({text:t,options:{fill:i===0?C.head:(i%2?C.white:C.alt),bold:i===0,color:i===0?C.navy:C.ink}}))),{x:10.05,y:2.94,w:5.4,h:2.76,colW:[1.8,3.6],rowH:[.44,.58,.58,.58,.58],fontFace:FONT,fontSize:fsMin(17),margin:[.08,.13,.08,.13],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});
 text(s,'네 목록의 길이와 순서를 맞춥니다.\n같은 위치의 값들이 하나의 청크입니다.',10.05,5.90,5.4,.58,17,{color:C.slate});
 text(s,'실제 코드 발췌 · 중간 검증부 생략 · 줄바꿈 조정',.55,6.44,9.1,.25,14,{color:C.sub});
 rect(s,.55,6.98,2.12,.55,C.tint,C.border);text(s,'이미 있는 ID A',.70,7.10,1.82,.28,18,{bold:true,color:C.blue,align:'center'});
 line(s,2.83,7.255,.52,0,C.blue,true);
 text(s,'A의 전달한 값을 갱신',3.53,7.09,3.90,.30,21,{bold:true,color:C.navy});
 rect(s,8.12,6.98,2.12,.55,C.tint,C.border);text(s,'처음 보는 ID B',8.27,7.10,1.82,.28,18,{bold:true,color:C.blue,align:'center'});
 line(s,10.40,7.255,.52,0,C.blue,true);
 text(s,'B를 새 레코드로 추가',11.10,7.09,4.35,.30,21,{bold:true,color:C.navy});
 text(s,'A·B는 설명용 ID입니다. 우리 ID는 본문 해시를 포함하므로 본문이 바뀌면 보통 새 ID가 됩니다.',.55,7.79,14.9,.28,17,{color:C.slate});
 text(s,'우리 구현은 새 세대에 적재하고, 검증 후 검색에 사용할 세대를 전환합니다.',.55,8.20,14.9,.28,18,{bold:true,color:C.navy});
 line(s,.55,8.59,14.9,0,C.footer,false,.7);
 text(s,'코드: app/infrastructure/index_repository.py:201–215 · Chroma 공식 문서',.55,8.68,12,.2,14,{color:C.sub,hyperlink:{url:'https://github.com/chroma-core/docs/blob/main/docs/usage-guide.md#updating-data-in-a-collection'}});
 text(s,'Upsert  /  1',12.5,8.68,2.95,.2,14,{color:C.sub,align:'right'});
 s.addNotes(`Upsert는 update와 insert를 결합한 동작입니다. 같은 컬렉션에 해당 ID가 있으면 전달한 값을 갱신하고, 없으면 새 레코드를 추가합니다. 화면의 A와 B는 설명용 ID이며 실제 실행 결과가 아닙니다. A를 다시 보냈을 때 A라는 ID의 레코드가 추가로 늘어나는 것은 아닙니다. 한 배치 안에 동일한 ID를 두 번 넣는 예시가 아닙니다.\n\n화면 코드의 ids 생성은 index_repository.py:201, collection 선택과 upsert 호출은 209–215행입니다. 중간 검증부는 생략했으며 metadatas 리스트의 줄바꿈만 읽기 쉽게 조정했습니다. 독립 실행 스크립트가 아니라 GenerationIndexRepository.upsert 메서드 내부의 발췌입니다. chunks는 정제된 PreparedChunk 목록이고 vectors는 같은 순서로 미리 계산한 본문 임베딩 목록입니다. ids[i], documents[i], embeddings[i], metadatas[i]는 같은 청크를 나타냅니다. _open(generation)은 준비된 세대의 Chroma 컬렉션을 엽니다. 선행 begin()이 필요합니다.\n\n이 코드는 embeddings를 직접 전달하므로 Chroma가 documents를 다시 임베딩할 필요가 없습니다. 본문이 바뀌었다면 그 본문에 맞는 벡터를 다시 만들어 전달해야 합니다. metadata는 별도 필드이며 이 호출에서 임베딩 입력으로 사용하지 않습니다. _clean_metadata는 None을 생략하고 문자열·숫자·불리언 외 값은 안정적인 JSON 문자열로 바꾸며 chunk_id도 넣습니다.\n\n우리 어댑터는 청크와 벡터의 행 수, 배치 안 ID 중복, 벡터 차원의 일관성, NaN 또는 무한대 포함 여부를 검증합니다. Chroma 컬렉션의 벡터 차원과도 일치해야 합니다. 인덱싱과 검색에는 동일한 임베딩 모델을 사용해야 합니다.\n\n우리 chunk_id는 document_id와 정제 본문의 SHA-256 해시 앞 16자리, 동일 본문 발생 순번으로 구성됩니다. 따라서 문서의 본문이 바뀌면 보통 다른 ID가 되며, 같은 문서라고 기존 ID를 갱신하는 것은 아닙니다. upsert 자체가 이번 요청에 없는 다른 ID를 삭제하지도 않습니다. 우리 구현은 새 generation에 유효한 청크 집합을 적재하고 검증 후 활성 포인터를 바꾸는 방식으로 검색에 반영합니다. 그 전에는 기존 활성 generation이 검색을 담당합니다.\n\n코드 근거:\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:185–215, 39–49\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/processor.py:79–82\nhybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:391\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:498\n공식 설명:\nhttps://github.com/chroma-core/docs/blob/main/docs/usage-guide.md\nhttps://docs.trychroma.com/docs/collections/update-data`);
}
async function main(){
 await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(final),{recursive:true});
 pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';pptx.author='design-agentic-ai';pptx.title='벡터DB upsert 코드 예제';pptx.subject='Chroma upsert와 ID별 추가·갱신';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();const candidate=build+'/candidate.pptx';await pptx.writeFile({fileName:candidate});
 const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
 const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[],pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--require-native-table-slide','1'],fontPolicy:{basis:'user_request',families:[FONT]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
 const p=await PresentationFile.importPptx(await FileBlob.load(final));const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});await fs.writeFile(root+'/output/pptx/벡터DB-upsert-코드예제-1장.png',new Uint8Array(await png.arrayBuffer()));
 console.log(JSON.stringify({final,checks:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
}
main().catch(e=>{console.error(e);process.exit(1);});
