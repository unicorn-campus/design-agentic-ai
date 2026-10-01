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
const build=root+'/.codex-build/embedding-selection-slide';
const final=root+'/output/pptx/임베딩-대상-결정-원리-1장.pptx';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const fsMin=n=>{if(n<14)throw Error('Minimum font size 14pt');return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,breakLine:false,vertAnchor:'ctr',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function pageHeader(s,title){text(s,'벡터DB 구성 원리 › 임베딩 대상 계획',.55,.35,14.9,.28,15,{color:C.sub});text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};pageHeader(s,'임베딩 대상 결정 원리');
 text(s,'모델·설정이 같고 본문도 같으면, 저장된 벡터를 재사용해 중복 계산을 줄입니다.',.55,1.78,14.9,.38,22,{color:C.slate});
 text(s,'사전 검사: 원천·처리 계약이 모두 같고 전체 재색인이 아니면, 작업을 생략합니다(no_op).',.55,2.29,14.9,.29,17,{color:C.sub});
 text(s,'청크별 판단 순서',.55,2.81,7.35,.36,24,{bold:true,color:C.navy});
 text(s,'상황별 결정 예시',8.4,2.81,7.05,.36,24,{bold:true,color:C.navy});
 const checks=[
  {y:3.36,h:.86,title:'1  재사용 가능한 실행인가요?',sub:'활성 세대 있음 · 모델/계약 동일 · 강제 재색인 아님'},
  {y:4.69,h:.75,title:'2  같은 정제 본문이 있나요?',sub:'활성 세대의 text_hash 비교 · ID가 달라도 가능'},
  {y:5.91,h:.75,title:'3  선택한 기존 벡터가 있나요?',sub:'get_vectors() 조회 결과에서 해당 ID 확인'}
 ];
 for(const c of checks){rect(s,.55,c.y,5.12,c.h,C.alt,C.border);text(s,c.title,.74,c.y+.12,4.74,.28,20,{bold:true,color:C.navy});text(s,c.sub,.74,c.y+c.h-.30,4.74,.22,14,{color:C.slate});}
 for(let i=0;i<2;i++){const c=checks[i];line(s,3.11,c.y+c.h+.03,0,.37,C.blue,true,2);text(s,'예',3.30,c.y+c.h+.13,.4,.22,15,{color:C.blue});}
 line(s,3.11,6.69,0,.30,C.blue,true,2);text(s,'예',3.30,6.76,.4,.22,15,{color:C.blue});
 const branchY=checks.map(c=>c.y+c.h/2);
 line(s,6.38,branchY[0],0,branchY[2]-branchY[0],C.slate,false,1.8);
 for(const yy of branchY){line(s,5.70,yy,.68,0,C.slate,false,1.8);text(s,'아니요',5.73,yy-.28,.64,.22,14,{color:C.slate,align:'center'});}
 line(s,6.38,branchY[1],.30,0,C.slate,true,1.8);
 rect(s,6.75,4.64,1.18,1.04,C.navy,C.navy);text(s,'새로\n임베딩',6.84,4.82,1.0,.56,21,{bold:true,color:C.white,align:'center'});
 rect(s,.55,7.06,5.12,.54,C.tint,C.blue);text(s,'기존 벡터 재사용',.75,7.18,4.72,.28,21,{bold:true,color:C.blue,align:'center'});
 const rows=[['상황','결정'],['출처·접근 등급 등 메타데이터만 변경','벡터 재사용'],['ID 변경 · 정제 본문은 동일','벡터 재사용'],['새 본문 · 일치하는 기존 해시 없음','새 임베딩'],['선택한 기존 벡터가 조회 결과에 없음','새 임베딩'],['모델·계약 변경 또는\nfull_reindex = true','현재 대상 전부\n새 임베딩']];
 s.addTable(rows.map((r,i)=>r.map(t=>({text:t,options:{fill:i===0?C.head:(i%2?C.white:C.alt),bold:i===0,color:i===0?C.navy:C.ink}}))),{x:8.4,y:3.36,w:7.05,h:3.32,colW:[4.78,2.27],rowH:[.44,.51,.51,.51,.51,.84],fontFace:FONT,fontSize:fsMin(17),margin:[.07,.12,.07,.12],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});
 text(s,'재사용은 왼쪽 세 조건을 모두 만족할 때입니다.',8.4,6.83,7.05,.25,15,{color:C.sub});
 text(s,'벡터를 재사용해도 최신 메타데이터와 함께\n새 세대에 다시 적재합니다.',8.4,7.15,7.05,.52,18,{color:C.slate});
 rect(s,.55,7.91,14.9,.45,C.tint,C.tint);text(s,'모델 입력은 정제 본문(chunk.text)뿐입니다. 메타데이터는 별도로 저장합니다.',.75,8.01,14.5,.26,19,{bold:true,color:C.navy});
 text(s,'삭제된 청크는 새 세대에서 제외합니다. 부분 실행에서 선택하지 않은 원천의 청크는 유지합니다.',.55,8.41,14.9,.21,14,{color:C.sub});
 line(s,.55,8.68,14.9,0,C.footer,false,.7);text(s,'코드 근거: indexing_service.py · prepare_embed() / embed() · settings.py',.55,8.77,12.3,.18,14,{color:C.sub});text(s,'임베딩 대상  /  1',12.9,8.77,2.55,.18,14,{color:C.sub,align:'right'});
 s.addNotes(`우리 코드는 임베딩 대상을 파일 수정 여부만으로 결정하지 않습니다. 정제 후 청크 본문 해시와 기존 모델 계약을 비교합니다. 이 슬라이드의 조건도는 prepare_embed()에 도달한 경우의 판단을 보여 줍니다. 모든 사례는 코드 규칙을 설명하며 이번에 실제 재색인을 실행해 얻은 결과가 아닙니다.\n\n먼저 _is_no_op()는 기존 활성 세대가 있고 full_reindex가 False이며 청킹 정책 서명, 문서 프로필 서명, 임베딩 서명, 임베딩 계약, 선택된 원천의 SHA-256과 doc_key 대응이 모두 같으면 no_op으로 끝냅니다. 이 경로에서는 prepare_embed()를 실행하지 않으므로 기존 벡터 누락을 다시 조회하지 않습니다. 새 세대의 저장 상태를 변경하지는 않지만 실행 보고나 체크포인트까지 전혀 쓰지 않는다는 뜻은 아닙니다.\n\nprepare_embed()는 현재 필요한 정제 청크 desired와 활성 세대의 청크 목록을 읽습니다. 재사용은 활성 manifest의 embedding_signature가 현재 embedder.signature와 같고 embedding_contract도 완전히 같으며 full_reindex가 False일 때 검토합니다. embedding_signature는 모델명과 프롬프트 정책을 식별하고, embedding_contract는 모델명, revision, max_seq_length, dimension, normalize_embeddings, pooling을 담습니다. 서명이 같더라도 revision이나 계약 값이 달라지면 재사용하지 않습니다. 최초 색인처럼 활성 세대가 없는 경우도 현재 대상 전체를 새로 임베딩합니다.\n\n활성 세대의 같은 chunk_id가 같은 text_hash를 가지면 먼저 그 벡터를 재사용 후보로 지정합니다. 이 조건에 해당하지 않더라도 활성 세대 전체에 동일한 text_hash가 있으면 다른 ID의 벡터를 재사용 후보로 지정합니다. 비교 대상은 원문 파일 전체나 메타데이터가 아니라 정제된 청크 본문의 해시입니다. 따라서 원문 표현이 달라져도 정제 후 본문이 같으면 재사용할 수 있고, 청크 ID가 바뀌어도 가능합니다.\n\nget_vectors()가 반환한 결과에서 선택한 원본 ID가 누락된 경우에만 해당 후보를 embed_ids로 이동합니다. 저장소 조회 자체가 예외를 던진 경우에는 예외를 전파하며 자동 재임베딩으로 전환하는 것이 아닙니다. 한 본문 해시에 대응하는 원본 ID는 활성 세대에서 선택하며, 선택한 ID의 벡터가 누락되면 다른 동등 해시 ID를 재탐색하지 않고 임베딩 대상으로 보냅니다. 이번 실행에서 새로 등장한 중복 본문끼리 벡터 계산을 하나로 합치는 구현도 아닙니다.\n\n메타데이터는 metadata_hash로 별도 기록합니다. 출처나 접근 등급만 바뀌고 정제 본문이 같으면 다른 재사용 조건이 충족되는 한 벡터를 재사용합니다. upsert 단계는 재사용 벡터와 새 벡터를 모두 모아 desired_ids 전체를 현재 청크의 본문과 최신 메타데이터로 새 세대에 적재합니다. 벡터 재사용은 메타데이터 갱신을 생략한다는 뜻이 아닙니다.\n\n기존 active ID 집합에서 desired ID 집합을 뺀 값은 deleted_ids에 기록됩니다. 이는 기존 활성 컬렉션에서 즉시 delete를 호출하는 뜻이 아니라 새 세대에 포함하지 않는다는 뜻입니다. 부분 실행에서는 선택되지 않은 원천의 청크를 desired에 유지하므로 임의로 삭제하지 않습니다. 모델에 전달하는 실제 입력은 self.embedder.embed([chunks[chunk_id].text for chunk_id in batch_ids])이며 메타데이터를 자동으로 붙이지 않습니다.\n\n소스 근거:\nhybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:249–278 (_is_no_op)\nhybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:280–380 (현재 청크 구성)\nhybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:409–481 (대상 계획)\nhybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:484–539 (본문 임베딩과 전체 대상 적재)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/settings.py:42–47 (임베딩 계약)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/embedder.py:61–64 (모델 서명)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/processor.py:79–82 (정제 본문 해시)`);
}
async function main(){
 await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(final),{recursive:true});pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';pptx.author='design-agentic-ai';pptx.title='임베딩 대상 결정 원리';pptx.subject='본문 해시와 모델 계약에 따른 임베딩과 재사용 결정';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();const candidate=build+'/candidate.pptx';await pptx.writeFile({fileName:candidate});const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
 const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[],pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--require-native-table-slide','1'],fontPolicy:{basis:'user_request',families:[FONT]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
 const p=await PresentationFile.importPptx(await FileBlob.load(final));const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});await fs.writeFile(root+'/output/pptx/임베딩-대상-결정-원리-1장.png',new Uint8Array(await png.arrayBuffer()));console.log(JSON.stringify({final,checks:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
}
main().catch(e=>{console.error(e);process.exit(1);});
