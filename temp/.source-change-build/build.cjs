const fs=require('node:fs');
const path=require('node:path');
const pptxgen=require('C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs');
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',tint:'EEF3FA',alt:'F5F8FC',tableHead:'E2EEF9',border:'D9E0EC',foot:'E9ECF3',white:'FFFFFF'};
let pptx;
const fsMin=n=>{if(n<14)throw new Error('Minimum 14pt');return n;};
function text(s,t,x,y,w,h,o={}){
 const {size=20,color=C.ink,bold=false,align='left',...rest}=o;
 s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color,bold,align,margin:0,valign:'mid',paraSpaceAfterPt:0,...rest});
}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border,width=1){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width}});}
function line(s,x,y,w,h,color=C.blue,arrow=false){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width:1.8,...(arrow?{endArrowType:'triangle'}:{})}});}
function box(s,x,y,w,h,title,body,color=C.navy,fill=C.tint){
 rect(s,x,y,w,h,fill,color,.9);
 text(s,title,x+.2,y+.13,w-.4,.36,{size:22,bold:true,color});
 text(s,body,x+.2,y+.59,w-.4,.36,{size:19,color:C.slate});
}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};
 text(s,'문서 인덱싱  ›  원천 확인',.56,.35,13,.26,{size:15,color:C.sub});
 text(s,'원천 파일의 변경 확인',.56,.77,14.88,.7,{size:48,color:C.navy,bold:true});
 rect(s,.56,1.61,14.88,.035,C.border,C.border,0);rect(s,.56,1.61,2.08,.035,C.blue,C.blue,0);
 text(s,'파일 내용을 SHA-256 지문으로 바꾸고, 이전 색인에 저장한 같은 파일의 지문과 비교합니다.',.56,1.83,14.88,.51,{size:22,color:C.slate});

 box(s,.56,2.68,4.4,1.12,'현재 파일의 지문 계산','파일 전체 읽기 · SHA-256 계산');
 text(s,'약관.pdf  /  a17…',.76,3.91,4,.35,{size:21,bold:true,color:C.navy});
 box(s,.56,4.39,4.4,1.12,'이전 색인의 기록 조회','manifest의 약관.pdf 지문 · a17…');
 // 두 입력을 비교 단계에 직각 연결하여 지문 대조 관계 표시.
 line(s,4.96,3.24,.69,0);line(s,5.65,3.24,0,.76);line(s,5.65,4,.75,0,C.blue,true);
 line(s,4.96,4.95,.69,0);line(s,5.65,4,0,.95);
 rect(s,6.4,3.38,3.45,1.24,C.white,C.blue,1.7);
 text(s,'같은 파일명으로 비교',6.58,3.57,3.09,.36,{size:22,bold:true,color:C.navy,align:'center'});
 text(s,'현재 지문 = 이전 지문?',6.58,4.08,3.09,.31,{size:19,color:C.slate,align:'center'});
 line(s,9.85,4,.61,0);line(s,10.46,3.24,0,1.71);
 line(s,10.46,3.24,.58,0,C.navy,true);line(s,10.46,4.95,.58,0,C.blue,true);
 box(s,11.04,2.68,4.4,1.12,'같음 · 기존 청크 재사용','원문 로드·청킹·정제 생략',C.navy,C.tint);
 box(s,11.04,4.39,4.4,1.12,'다름·신규 · 파일 처리','로드·청킹·정제 및 가명 처리',C.blue,C.alt);

 text(s,'비교 예시  ·  지문은 설명용 가상 값이며 짧게 표시했습니다.',.56,5.74,14.88,.33,{size:18,color:C.slate});
 const rows=[['원천 파일','이전 지문','현재 지문','판정과 처리'],['약관.pdf','a17…','a17…','동일 · 기존 청크 재사용'],['안내.pdf','b29…','c83…','변경 · 원문부터 다시 처리'],['상담.txt','없음','d40…','신규 · 원문부터 처리']];
 const data=rows.map((r,i)=>r.map((t,j)=>({text:t,options:{fill:i===0?C.tableHead:(i%2?C.white:C.alt),bold:i===0||j===3,color:i===0?C.navy:(j===3&&i>1?C.blue:C.ink),align:j===1||j===2?'center':'left'}})));
 s.addTable(data,{x:.56,y:6.18,w:14.88,colW:[3.5,2.35,2.35,6.68],rowH:[.4,.45,.45,.45],fontFace:FONT,fontSize:fsMin(19),margin:[.07,.16,.07,.16],valign:'middle',border:{type:'solid',color:C.border,pt:.7},autoPage:false});
 text(s,'재사용 조건: 처리 정책·문서 프로필이 같고, 기존 청크가 있으며, 강제 재색인이 아닐 때',.56,8.13,14.88,.29,{size:18,bold:true,color:C.navy});
 line(s,.56,8.53,14.88,0,C.foot);
 text(s,'파일 전체 바이트 기준입니다. PDF 내부 정보만 바뀌어도 변경으로 판정할 수 있습니다.',.56,8.64,13.85,.23,{size:14,color:C.sub});
 text(s,'01',14.62,8.62,.82,.27,{size:15,color:C.navy,align:'right'});
 s.addNotes(`SHA-256은 파일 전체 바이트를 고정 길이 지문으로 바꾸는 함수입니다. 현재 구현은 파일명(source)을 키로 사용해 이전 활성 색인의 manifest.inputs_sha256 값과 현재 지문을 비교합니다. 파일의 수정 시각만으로 판정하지 않으며, 비교를 위해 모든 대상 파일의 바이트를 읽습니다. 표의 파일명과 짧은 지문은 설명용 가상 값입니다.\n\n원천 확인 discover_docs는 전체 무변경 여부를 먼저 판정합니다. 선택 범위의 파일 목록·지문·문서 키, 청킹 정책·문서 프로필 및 임베딩 계약이 같고 강제 재색인이 아니면 _is_no_op 결과에 따라 전체 실행을 종료합니다. 파일별 기존 청크 재사용은 다음 load_split_clean에서 실제 적용합니다. 같은 파일명으로 저장된 원천 지문과 정책·프로필이 같고 기존 청크가 있으며 강제 재색인이 아닐 때 기존의 정제된 청크를 재사용합니다. 변경·신규 파일이나 재사용 조건을 만족하지 않는 파일만 로더, 분할기, 정제 처리기를 통과합니다. 이 그림은 두 단계에 걸친 판단을 이해하기 쉽게 하나의 흐름으로 표현했습니다.\n\n정책 또는 프로필 변경은 파일 내용이 같아도 재처리 원인이 됩니다. 부분 실행에서는 이러한 설정 변경을 차단하고 전체 실행을 요구합니다. 임베딩 모델 계약 변경만 있는 경우 기존 청크를 재사용하되 임베딩은 다시 생성할 수 있습니다. 기존 청크 재사용이 이후 모든 색인 작업의 생략을 뜻하지는 않습니다. 파일 내용이 변경되어도 정제된 청크 본문이 같으면 뒤 단계에서 벡터를 재사용할 수 있으며 이는 원천 파일 변경 확인과 별도 판단입니다.\n\n원천 파일의 전체 바이트를 해시하므로 PDF에서 보이는 본문이 같아도 내부 메타데이터나 저장 구조가 바뀌면 재처리 대상이 될 수 있습니다. 파일 이름 변경은 별도 원천으로 인식합니다. 원천에서 사라진 파일은 선택 범위에 맞춰 기존 청크 제외 대상으로 처리하며, 이 슬라이드의 예시는 신규·변경·동일 세 경우만 보여줍니다. 인덱스 게시 시 현재 지문을 inputs_sha256에 기록해 다음 실행의 비교 기준으로 사용합니다.\n\n구현 근거:\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py: FileSystemSourceCatalog.discover, sha256(path.read_bytes()).hexdigest()\nhybrid-ai-lab/indexer/vector-bm25/app/application/indexing_service.py: discover_docs, _is_no_op, load_split_clean, _build_manifest\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/graph.py: _after_discover\n`);
}
async function main(){
 if(!fs.existsSync(path.join(__dirname,'..','source_change_detection_script.md')))throw new Error('사전 스크립트 필요');
 pptx=new pptxgen();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';
 pptx.author='design-agentic-ai';pptx.title='원천 파일의 변경 확인';pptx.subject='SHA-256과 이전 색인 기록을 통한 변경 감지';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();await pptx.writeFile({fileName:path.join(__dirname,'candidate.pptx')});console.log('Created source change detection slide');
}
main().catch(e=>{console.error(e);process.exit(1);});

