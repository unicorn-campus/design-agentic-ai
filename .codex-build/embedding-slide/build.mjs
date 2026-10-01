import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const runtime = 'C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES = runtime + '/node/node_modules';
const require = createRequire(import.meta.url);
const PptxGenJS = require(runtime + '/node/node_modules/pptxgenjs');
const { FileBlob, PresentationFile } = await import(pathToFileURL(runtime + '/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
const root = 'C:/Users/hiond/class/design-agentic-ai';
const build = root + '/.codex-build/embedding-slide';
const skill = 'C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const final = root + '/output/pptx/임베딩-원리와-모델-1장.pptx';
const C = {navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const FONT = 'Pretendard';
const fsMin = n => {if(n<14) throw Error('Minimum 14pt'); return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}) {s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,breakLine:false,vertAnchor:'ctr',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border) {s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2) {s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function dot(s,x,y,color=C.blue) {s.addShape(pptx.shapes.OVAL,{x,y,w:.13,h:.13,line:{color},fill:{color}});}
function pageHeader(s,{crumb,title}) {
  text(s,crumb,.55,.35,14.9,.28,15,{color:C.sub});
  text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});
  rect(s,.55,1.55,14.9,.035,C.border,C.border); rect(s,.55,1.55,2.1,.035,C.blue,C.blue);
}
async function createSlide01() {
  const s=pptx.addSlide(); s.background={color:C.white};
  pageHeader(s,{crumb:'벡터DB 구성 원리 › 임베딩',title:'임베딩의 원리와 모델'});
  text(s,'글의 의미를 숫자 벡터로 표현하면, 표현이 달라도 뜻이 비슷한 문서를 찾을 수 있습니다.',.55,1.78,14.9,.38,21,{color:C.slate});
  text(s,'우리 코드에서는 본문만 임베딩',.55,2.32,9.3,.38,23,{bold:true,color:C.navy});
  text(s,'비슷한 뜻은 가까운 위치에',10.65,2.32,4.8,.38,23,{bold:true,color:C.navy});
  rect(s,.55,2.97,3.13,1.13,C.tint);
  text(s,'청크의 본문 (text)',.74,3.1,2.75,.29,18,{bold:true,color:C.blue});
  text(s,'“인증 요청이 반복돼요”',.74,3.58,2.75,.31,18);
  rect(s,.55,4.32,3.13,.93,C.alt);
  text(s,'메타데이터',.74,4.43,2.75,.29,18,{bold:true,color:C.slate});
  text(s,'출처 · 페이지 · 접근 등급',.74,4.86,2.75,.24,15,{color:C.slate});
  line(s,3.78,3.53,.55,0,C.blue,true);
  rect(s,4.43,3.03,2.17,1.03,C.navy,C.navy);
  text(s,'KURE-v2',4.53,3.2,1.97,.32,24,{bold:true,color:C.white,align:'center'});
  text(s,'임베딩 모델',4.53,3.68,1.97,.24,16,{color:C.white,align:'center'});
  line(s,6.7,3.53,.53,0,C.blue,true);
  rect(s,7.33,3.03,2.77,1.03,C.tint,C.blue);
  text(s,'[0.12, −0.07, …]',7.49,3.21,2.45,.29,21,{bold:true,color:C.navy,align:'center'});
  text(s,'숫자 768개인 단일 벡터',7.43,3.69,2.57,.24,15,{color:C.slate,align:'center'});
  line(s,8.715,4.08,0,.23,C.blue,true);
  rect(s,7.33,4.42,2.77,.83,C.white,C.navy);
  text(s,'Chroma에 함께 저장',7.48,4.52,2.47,.27,18,{bold:true,color:C.navy,align:'center'});
  text(s,'본문 + 벡터 + 메타데이터',7.43,4.92,2.57,.21,14,{color:C.slate,align:'center'});
  text(s,'모델을 거치지 않고',4.0,4.34,3.07,.24,15,{color:C.slate,align:'center'});
  line(s,3.78,4.79,3.44,0,C.slate,true,1.6);
  text(s,'검색 필터와 출처 표시에 사용',3.95,4.98,3.17,.23,14,{color:C.slate,align:'center'});
  line(s,10.65,5.12,4.78,0,C.border,false,1);
  line(s,10.65,3.03,0,2.09,C.border,false,1);
  dot(s,11.12,3.42); dot(s,11.4,3.92);
  text(s,'“인증 요청이 반복돼요”',11.36,3.25,3.83,.31,16,{color:C.blue});
  text(s,'“본인 확인이 계속 떠요”',11.64,3.84,3.66,.31,16,{color:C.blue});
  dot(s,14.44,4.68,C.slate);
  text(s,'“연회비 면제 조건”',11.67,4.59,2.66,.31,16,{color:C.slate,align:'right'});
  text(s,'숫자·위치는 설명용 예시입니다. 실제 유사도를 측정한 그림은 아닙니다.',.55,5.43,14.9,.26,14,{color:C.sub});
  text(s,'Local과 Cloud의 대표 모델',.55,5.95,9,.36,24,{bold:true,color:C.navy});
  text(s,'대표 예시이며 사용량 순위는 아닙니다',9.7,6.01,5.75,.25,14,{color:C.sub,align:'right'});
  const rows=[
    ['실행 방식','대표 모델','사용 방식'],
    ['Local','BGE-M3 / multilingual-e5-large\n우리 코드: KURE-v2','내 PC·서버에서 실행합니다.\n모델과 실행 환경을 직접 관리합니다.'],
    ['Cloud API','OpenAI text-embedding-3-small / -large\nCohere embed-v4.0','제공사의 API로 본문을 보내 사용합니다.\n호출 비용과 데이터 전송 정책을 확인합니다.']
  ];
  s.addTable(rows.map((r,i)=>r.map(t=>({text:t,options:{fill:i===0?C.head:(i===1?C.white:C.alt),color:i===0?C.navy:C.ink,bold:i===0}}))),{
    x:.55,y:6.46,w:14.9,h:1.86,colW:[1.9,6.25,6.75],rowH:[.4,.73,.73],fontFace:FONT,fontSize:fsMin(17),
    margin:[.08,.16,.08,.16],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false,
  });
  line(s,.55,8.59,14.9,0,C.footer,false,.7);
  text(s,'design-agentic-ai',.55,8.68,8,.2,14,{color:C.sub});
  text(s,'임베딩  /  1',12,8.68,3.45,.2,14,{color:C.sub,align:'right'});
  s.addNotes(`임베딩은 본문의 의미를 숫자 목록으로 표현하는 과정입니다. 숫자 하나마다 사람이 정한 단어 뜻이 있는 것은 아닙니다. 비슷한 의미의 본문과 질문을 같은 임베딩 모델로 변환해 유사도를 비교합니다. 오른쪽은 설명용 가상 배치이며 실제 모델 출력을 2차원 투영한 결과가 아닙니다.\n\n우리 코드의 IndexingWorkflow.embed()는 chunks[chunk_id].text만 전달합니다. 메타데이터는 이 입력에 자동으로 포함되지 않습니다. 별도 설계에서 제목 등 메타데이터를 본문에 명시적으로 결합하면 그 텍스트도 임베딩됩니다. 현재 구현에서는 본문·벡터·메타데이터를 Chroma의 documents·embeddings·metadatas 필드로 각각 저장합니다. ID도 함께 저장합니다. 메타데이터는 출처와 검색 필터에 활용합니다.\n\nKURE-v2는 우리 코드에서 768차원 단일 벡터와 L2 정규화를 사용합니다. Local은 실행 위치에 따른 구분이며 같은 공개 모델을 클라우드에 직접 배포하는 것도 가능합니다. Local도 하드웨어·운영 비용이 듭니다. 표는 시장점유율·사용량 순위를 주장하지 않습니다. 각 모델의 품질은 우리 데이터로 평가해야 합니다.\n\n코드 근거: hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py:499; app/infrastructure/index_repository.py:210-215; app/infrastructure/embedder.py; app/infrastructure/settings.py.\n공식 모델 출처(2026-10-01 확인):\nhttps://huggingface.co/BAAI/bge-m3\nhttps://huggingface.co/intfloat/multilingual-e5-large\nhttps://developers.openai.com/api/docs/guides/embeddings\nhttps://docs.cohere.com/docs/cohere-embed\nhttps://huggingface.co/nlpai-lab/KURE-v2`);
}
async function main(){
  await fs.mkdir(build,{recursive:true}); await fs.mkdir(path.dirname(final),{recursive:true});
  pptx=new PptxGenJS(); pptx.defineLayout({name:'CUSTOM',width:16,height:9}); pptx.layout='CUSTOM';
  pptx.author='design-agentic-ai'; pptx.subject='임베딩 원리, 본문과 메타데이터, Local과 Cloud 모델';
  pptx.title='임베딩의 원리와 모델'; pptx.lang='ko-KR'; pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
  await createSlide01(); const candidate=build+'/candidate.pptx'; await pptx.writeFile({fileName:candidate});
  const presentation=await PresentationFile.importPptx(await FileBlob.load(candidate));
  const preview=await presentation.export({slide:presentation.slides.getItem(0),format:'png',scale:1.5});
  await fs.writeFile(build+'/slide-1.png',new Uint8Array(await preview.arrayBuffer()));
  const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
  const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,
    explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[],
    pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
    layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
    layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--require-native-table-slide','1'],
    fontPolicy:{basis:'user_request',families:[FONT]},verifyArtifactToolImport:true,
    receiptPath:build+'/validation.json'});
  console.log(JSON.stringify({final,result}));
}
main().catch(e=>{console.error(e);process.exit(1);});
