import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const runtime='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const require=createRequire(import.meta.url);
const PptxGenJS=require(runtime+'/node/node_modules/pptxgenjs');
const root='C:/Users/hiond/class/design-agentic-ai';
const final=root+'/output/pptx/게시-세대전환-원리와설계-1장-v2.pptx';
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',body:'3B4557',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',dark:'404155',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const fsMin=n=>{if(n<14)throw Error(`fontSize ${n} < 14pt 금지! 슬라이드를 분리할 것`);return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,valign:'middle',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border,extra={}){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1,...extra}});}
function rrect(s,x,y,w,h,fill,stroke,extra={}){s.addShape(pptx.shapes.ROUNDED_RECTANGLE,{x,y,w,h,rectRadius:.06,fill:{color:fill},line:{color:stroke,width:1.2,...extra}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function numBadge(s,x,y,n,color=C.blue){rrect(s,x,y,.36,.36,color,color);text(s,String(n),x,y,.36,.36,16,{bold:true,color:C.white,align:'center'});}
function pageHeader(s,{crumb,title}){
 text(s,crumb,.55,.35,14.9,.28,15,{color:C.sub});
 text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});
 rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);
}
// 세대 카드: 상태별로 채움·테두리를 달리해 "지금 쓰는 세대"가 한눈에 보이게 함
const STYLE={
 active:{fill:C.navy,stroke:C.navy,title:C.white,chipFill:C.blue,chipText:C.white,dash:'solid'},
 building:{fill:C.white,stroke:C.blue,title:C.blue,chipFill:C.white,chipText:C.blue,dash:'dash'},
 checking:{fill:C.tint,stroke:C.blue,title:C.navy,chipFill:C.white,chipText:C.navy,dash:'solid'},
 kept:{fill:C.alt,stroke:C.border,title:C.sub,chipFill:C.white,chipText:C.sub,dash:'solid'}
};
function genCard(s,x,y,name,status,kind,check=false){
 const st=STYLE[kind],w=2.2,h=.98;
 rrect(s,x,y,w,h,st.fill,st.stroke,{dashType:st.dash});
 text(s,[{text:name+'  ',options:{bold:true,fontSize:fsMin(18)}},{text:status,options:{fontSize:fsMin(14)}}],x+.14,y+.08,w-.28,.36,18,{color:st.title});
 ['벡터','BM25'].forEach((c,i)=>{
  const cx=x+.14+i*.98;
  rrect(s,cx,y+.5,.9,.36,st.chipFill,st.stroke,{dashType:st.dash});
  text(s,(check?'✓ ':'')+c,cx,y+.5,.9,.36,14,{bold:true,color:st.chipText,align:'center'});
 });
}
function pointer(s,cx,y){
 rrect(s,cx-1.0,y,2.0,.4,C.dark,C.dark);
 text(s,'게시 포인터',cx-1.0,y,2.0,.4,15,{bold:true,color:C.white,align:'center'});
 line(s,cx,y+.4,0,.33,C.blue,true,2.5);
}

async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};
 pageHeader(s,{crumb:'벡터DB 구성 원리 › 마지막 단계: 게시',title:'게시의 원리: 완성된 세대로 한 번에 전환'});
 text(s,[
  {text:'세대  ',options:{bold:true,color:C.navy}},{text:'같은 시점의 벡터·BM25·본문·사전·manifest를 한 폴더에 묶은 검색 버전',options:{breakLine:true}},
  {text:'게시  ',options:{bold:true,color:C.navy}},{text:'게시 포인터(active_generation.json)가 가리키는 세대를 새 세대로 바꾸는 일'}
 ],.55,1.72,14.9,.72,18,{color:C.slate,valign:'top',lineSpacingMultiple:1.1});

 // 3장면 도식: 포인터가 어느 세대를 가리키는지가 핵심
 const scenes=[
  {n:1,title:'만드는 중',cards:[['G1','사용 중','active'],['G2','만드는 중','building']],ptr:0,
   cap:'G2를 다른 폴더에 만듦 (같은 본문은 G1 벡터 재사용)\n그동안 검색은 계속 G1'},
  {n:2,title:'검증',cards:[['G1','사용 중','active'],['G2','검증 중','checking',true]],ptr:0,
   cap:'벡터 ID·본문·차원, BM25 청크 수·해시 확인\n하나라도 틀리면 멈춤 → 포인터는 G1 그대로'},
  {n:3,title:'전환',cards:[['G1','보관','kept'],['G2','사용 중','active']],ptr:1,
   cap:'잠금 → 기준 세대(G1) 그대로인지 확인 → ready 기록\n포인터 파일 1개만 교체 · G1은 지우지 않음'}
 ];
 const SX=[.55,5.6,10.65],SY=2.58,SW=4.8,SH=2.95;
 scenes.forEach((sc,i)=>{
  const x=SX[i],hot=i===2;
  rect(s,x,SY,SW,SH,hot?C.tint:C.white,hot?C.blue:C.border);
  numBadge(s,x+.16,SY+.14,sc.n,hot?C.navy:C.blue);
  text(s,sc.title,x+.62,SY+.14,2.4,.36,20,{bold:true,color:C.navy});
  const cardX=[x+.13,x+2.47];
  pointer(s,cardX[sc.ptr]+1.1,SY+.6);
  sc.cards.forEach((c,j)=>genCard(s,cardX[j],SY+1.36,c[0],c[1],c[2],c[3]));
  text(s,sc.cap,x+.16,SY+2.42,SW-.32,.5,14,{color:C.body,valign:'top'});
  if(i<2)line(s,x+SW+.03,SY+SH/2,.19,0,C.blue,true,2);
 });
 text(s,[
  {text:'주의  ',options:{bold:true,color:C.navy}},
  {text:'현재 검색기(Retriever)는 이 포인터를 직접 읽지 않고, 설정한 경로(CHROMA_PATH·SEARCH_INDEX_ROOT)를 씁니다.'}
 ],.55,5.62,14.9,.32,15,{color:C.slate});

 // 좌: 실제 세대 폴더 상태
 text(s,'실제 세대 폴더',.55,6.05,4.0,.36,20,{bold:true,color:C.navy});
 text(s,'data/generations · 2026-10-01 확인',4.0,6.07,4.15,.32,14,{color:C.sub,align:'right'});
 const H=t=>({text:t,options:{bold:true,color:C.navy,fill:C.head}});
 const folders=[
  ['group2-build-001','building','미완성 · 게시 안 됨 · 남아 있음'],
  ['group2-build-002','ready','이전 세대 · 남아 있음'],
  ['group2-final-003','ready','직전 사용 세대 · 남아 있음'],
  ['20260930T132618Z','building','미완성 · 게시 안 됨 · 남아 있음'],
  ['20260930T135203Z','ready','지금 게시 포인터가 가리킴']
 ];
 s.addTable([[H('세대 폴더'),H('상태'),H('의미')],...folders.map((r,i)=>r.map(t=>({text:t,options:i===4?{bold:true,color:C.blue,fill:C.tint}:{fill:i%2?C.alt:C.white}})))],
  {x:.55,y:6.48,w:7.6,colW:[2.35,1.25,4.0],rowH:.33,fontFace:FONT,fontSize:fsMin(14),color:C.body,margin:[.02,.1,.02,.1],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});

 // 우: 사람이 정해야 할 것만
 text(s,'사람이 정해야 할 것',8.45,6.05,4.0,.36,20,{bold:true,color:C.navy});
 text(s,'잠금·검증·교체는 코드가 처리',11.9,6.07,3.55,.32,14,{color:C.sub,align:'right'});
 const asks=[
  ['게시 합격선','검색 품질이 몇 점 이상이면 게시할까?'],
  ['게시 승인','자동 게시할까, 담당자 확인 후 게시할까?'],
  ['되돌리기','문제가 생기면 누가, 어떤 신호로 이전 세대로?'],
  ['보관 기간','이전·미완성 세대를 몇 개, 며칠 남길까?']
 ];
 s.addTable([[H('정할 것'),H('사람이 답할 질문')],...asks.map((r,i)=>r.map((t,j)=>({text:t,options:{fill:i%2?C.alt:C.white,bold:j===0,color:j===0?C.navy:C.body}})))],
  {x:8.45,y:6.48,w:7.0,colW:[1.75,5.25],rowH:.396,fontFace:FONT,fontSize:fsMin(15),margin:[.02,.1,.02,.1],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});

 line(s,.55,8.59,14.9,0,C.footer,false,.7);
 text(s,'코드 근거: index_repository.py · begin() / publish() · indexing_service.py · retriever settings.py',.55,8.68,12.3,.2,14,{color:C.sub});
 text(s,'게시  /  1',13.0,8.68,2.45,.2,14,{color:C.sub,align:'right'});

 s.addNotes(`세대(generation)는 한 시점에 함께 써야 하는 Chroma 벡터, BM25 색인, 청크 본문(corpus), 카드명 사전, manifest를 한 폴더(data/generations/{세대명})에 묶은 검색 버전입니다. 게시는 data/active_generation.json, 즉 게시 포인터가 가리키는 세대를 새 세대로 바꾸는 일입니다. G1, G2는 설명용 이름입니다.

① 만드는 중: begin()이 새 세대 폴더와 generation_state.json을 만들고 status를 building으로, 그때의 활성 세대를 base_generation으로 기록합니다. 활성 세대(G1)는 건드리지 않습니다. 본문이 같은 청크는 G1의 벡터를 읽어 재사용하고, 바뀐 청크만 새로 임베딩합니다(indexing_service.py의 계획 단계). 그동안 게시 포인터는 G1을 가리키므로 반쯤 만든 G2는 보이지 않습니다.

② 검증: publish()는 빈 세대와 중복 chunk_id를 거부하고, Chroma에 저장된 ID 집합·본문과 본문 해시·메타데이터·벡터 차원이 게시 대상과 같은지 확인합니다. BM25 쪽은 경로·세대·청크 수·corpus와 카드명 사전 해시를 확인하고, 체크포인트에 기록한 준비 결과(stage)와 실제 파일이 같은지도 비교합니다. 하나라도 틀리면 예외가 나고 포인터는 바뀌지 않습니다.

③ 전환: .publish.lock 잠금을 잡은 짧은 구간에서 현재 활성 세대를 다시 읽습니다. 현재 세대가 base_generation(G1) 또는 이미 같은 G2일 때만 진행합니다. 그 사이 다른 실행이 먼저 다른 세대를 게시했다면 RuntimeError로 거부합니다. 통과하면 G2 상태를 ready로 기록하고 마지막에 active_generation.json을 교체합니다. _replace_json()은 같은 폴더에 임시 파일을 쓰고 fsync한 뒤 os.replace로 바꾸므로, 포인터 파일이 반쯤 쓰인 상태로 읽히는 일을 막습니다. 포인터에는 generation, chroma_path, search_index_root, collection, chunk_count, embedding_dimension, embedding_signature가 함께 들어갑니다.

핵심 코드(요약):
with CrossPlatformFileLock(self.lock_path):
    current = self._active_pointer()
    if current_generation not in {base_generation, generation}: raise RuntimeError(...)
    _replace_json(state_path, {...generation_state, "status": "ready", ...})
    _replace_json(self.active_pointer_path, pointer)

주의: 현재 Retriever는 active_generation.json을 읽지 않습니다. CHROMA_PATH와 SEARCH_INDEX_ROOT를 따로 설정받고, 기본값은 data/chroma와 data/search_indexes입니다. BM25 쪽은 SEARCH_INDEX_ROOT 안의 active_index.json으로 세대 변화를 감지하지만, 세대마다 search_indexes가 따로 있으므로 새 세대를 검색기에 반영하려면 경로 설정을 바꿔야 합니다. 따라서 "게시하면 검색기가 자동으로 동시에 전환된다"고 설명하지 않습니다.

실제 폴더: 2026-10-01 기준 data/generations에는 세대 5개가 있습니다. 20260930T135203Z가 현재 포인터가 가리키는 세대이고(직전 세대 group2-final-003을 기준으로 만듦), 같은 기준으로 시작했다 완성되지 않은 20260930T132618Z와 group2-build-001은 building 상태로 남아 있습니다. publish()는 이전 세대나 미완성 세대를 지우지 않습니다. 게시 실패 시 포인터를 유지하는 것은 "실패한 새 세대를 켜지 않는 것"이며, 게시 후 문제가 생겼을 때 자동으로 이전 세대로 되돌리는 롤백 기능은 없습니다.

사람이 정해야 할 것: 잠금, 구조·해시 검증, 포인터 교체는 코드가 이미 처리합니다. 반면 검색 품질 합격선, 자동 게시와 사람 승인 중 무엇을 쓸지, 문제가 생겼을 때 누가 어떤 신호로 이전 세대로 되돌릴지, 이전·미완성 세대를 몇 개·며칠 남길지는 서비스 목표·위험·비용에 따라 달라지므로 사람이 정해야 합니다.

이 슬라이드는 코드와 현재 폴더 상태를 읽어 설명한 것이며, 이번 작업에서 실제 게시나 되돌리기를 실행하지는 않았습니다.

소스 근거:
hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py (_replace_json, begin, _verify_collection, publish)
hybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py (벡터 재사용 계획, publish 호출)
hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py (verify)
hybrid-ai-lab/retriever/vector-retriever/app/infrastructure/settings.py (CHROMA_PATH·SEARCH_INDEX_ROOT 기본값)
hybrid-ai-lab/retriever/vector-retriever/app/infrastructure/corpus_store.py (active_index.json 읽기)
hybrid-ai-lab/indexer/vector-bm25/data/generations/*/generation_state.json (세대별 상태)`);
}
async function main(){
 pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';
 pptx.author='design-agentic-ai';pptx.title='게시의 원리: 완성된 세대로 한 번에 전환';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 for(const fn of [createSlide01])await fn();
 await pptx.writeFile({fileName:final});
 const {FileBlob,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
 const p=await PresentationFile.importPptx(await FileBlob.load(final));
 const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});
 await fs.writeFile(final.replace(/\.pptx$/,'.png'),new Uint8Array(await png.arrayBuffer()));
 console.log('✅ PPT 생성 완료',final);
}
main().catch(e=>{console.error('❌ PPT 생성 실패:',e);process.exit(1);});
