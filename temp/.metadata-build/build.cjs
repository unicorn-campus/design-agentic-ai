const fs=require('node:fs');
const path=require('node:path');
const pptxgen=require('C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs');
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',tint:'EEF3FA',alt:'F5F8FC',tableHead:'E2EEF9',border:'D9E0EC',line:'EDF0F6',foot:'E9ECF3',white:'FFFFFF'};
const fsMin=n=>{if(n<14)throw new Error('14pt 미만 금지');return n;};
let pptx;
function text(s,t,x,y,w,h,o={}){
 const {size=20,color=C.ink,bold=false,align='left',...rest}=o;
 s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color,bold,align,margin:0,valign:'mid',paraSpaceAfterPt:0,...rest});
}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border,thick=1){
 s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:thick}});
}
function line(s,x,y,w,h,color=C.blue,width=1.7,arrow=false){
 s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});
}
function pages(s,x,y,label,a,b){
 text(s,label,x,y,2.45,.31,{size:20,bold:true,color:C.navy});
 rect(s,x,y+.46,1.15,.56,C.tableHead,C.blue,.8);
 rect(s,x+1.15,y+.46,1.15,.56,C.tableHead,C.blue,.8);
 text(s,`${a}쪽`,x,y+.55,1.15,.36,{size:22,bold:true,color:C.blue,align:'center'});
 text(s,`${b}쪽`,x+1.15,y+.55,1.15,.36,{size:22,bold:true,color:C.blue,align:'center'});
 text(s,`최솟값 ${a}  /  최댓값 ${b}`,x,y+1.18,2.5,.34,{size:17,color:C.slate});
}
async function createSlide01(example){
 const s=pptx.addSlide();
 s.background={color:C.white};
 text(s,'문서 인덱싱  ›  청킹',.56,.35,13,.26,{size:15,color:C.sub});
 text(s,'메타데이터 구조 설계',.56,.77,14.88,.7,{size:48,color:C.navy,bold:true});
 rect(s,.56,1.61,14.88,.035,C.border,C.border,0);
 rect(s,.56,1.61,2.08,.035,C.blue,C.blue,0);
 text(s,'문서에 공통인 값은 물려주고, 청크마다 달라지는 값은 포함 범위를 보고 계산합니다.',.56,1.83,14.88,.52,{size:22,color:C.slate});
 text(s,'공통 출처  source = D1_개인회원표준약관_합성.pdf',.56,2.48,14.88,.39,{size:23,bold:true,color:C.navy});

 text(s,'공통값 상속',.56,3.13,5.5,.47,{size:29,bold:true,color:C.navy});
 rect(s,.56,3.79,5.58,1.59,C.tint,C.border,1);
 text(s,'문서 유형  regulation\n버전  "1.2"\n공개 등급  public',.8,3.99,5.07,1.17,{size:23,paraSpaceAfterPt:8});
 text(s,'두 청크에 같은 값을 복사',.56,5.51,5.58,.36,{size:20,bold:true,color:C.navy});
 line(s,6.26,4.67,.5,0,C.navy,1.9,true);

 text(s,'범위별 값 계산',.56,6.06,5.58,.44,{size:29,bold:true,color:C.blue});
 pages(s,.56,6.69,'청크 A',6,7);
 pages(s,3.57,6.69,'청크 B',10,11);
 line(s,6.26,7.4,.5,0,C.blue,1.9,true);

 text(s,'두 청크의 저장 메타데이터',7.02,3.13,8.42,.47,{size:29,bold:true,color:C.navy});
 const rows=[
  ['필드 (자료형)','청크 A','청크 B'],
  ['doc_type (문자열)','regulation','regulation'],
  ['version (문자열)','"1.2"','"1.2"'],
  ['access_level (문자열)','public','public'],
  ['page (정수)','6','10'],
  ['page_end (정수)','7','11'],
 ];
 const data=rows.map((r,i)=>r.map((t,j)=>({text:t,options:{fill:i===0?C.tableHead:(i<4?C.white:C.tint),bold:i===0||(i>=4&&j>0),color:i>=4?C.blue:(i===0?C.navy:C.ink),align:j===0?'left':'center'}})));
 s.addTable(data,{x:7.02,y:3.79,w:8.42,colW:[4.12,2.15,2.15],rowH:[.55,.61,.61,.61,.61,.61],fontFace:FONT,fontSize:fsMin(21),margin:[.10,.18,.10,.18],valign:'middle',border:{type:'solid',color:C.border,pt:.7},autoPage:false});
 text(s,'page = 겹친 쪽의 최솟값\npage_end = 겹친 쪽의 최댓값',7.02,7.68,8.42,.65,{size:19,bold:true,color:C.blue});

 line(s,.56,8.52,14.88,0,C.foot,1);
 text(s,'교육용 합성 문서의 실제 인덱싱 결과 · 출처와 청크 ID는 발표자 노트에 수록',.56,8.64,13.85,.23,{size:14,color:C.sub});
 text(s,'01',14.62,8.62,.82,.27,{size:15,color:C.navy,align:'right'});
 s.addNotes(`같은 원문에서 만들어진 실제 청크 두 개의 메타데이터를 비교합니다. 원문은 교육용 합성 약관이며 금융기관의 실제 약관을 의미하지 않습니다. 공통 출처는 D1_개인회원표준약관_합성.pdf입니다. 문서 전체에 같은 값인 doc_type=regulation, version="1.2", access_level=public은 두 청크에 그대로 복사됩니다. 숫자처럼 보이는 버전도 문자열로 설계합니다. 페이지 값은 문서 전체의 공통값으로 복사하면 안 됩니다. 청크 A가 겹친 페이지는 6쪽과 7쪽이므로 page=6, page_end=7입니다. 청크 B는 10쪽과 11쪽에 걸쳐 page=10, page_end=11입니다. 이 두 값은 문서와 청크의 페이지 구간 교집합에서 최솟값과 최댓값을 계산한 결과입니다. 페이지 번호는 이 로더가 부여한 PDF 페이지 번호를 기준으로 합니다. 여러 조항에 걸친 경우도 같은 원리로 해당 조항 목록을 구성합니다. 현재 코드의 clause_no는 대표값이고 clause_no_all은 여러 조항의 목록입니다. 페이지 구간을 계산하는 내부 좌표와 결과 메타데이터에 문자 좌표를 저장하는 것은 별개입니다. 화면은 구조 설계의 핵심 차이를 보여주기 위해 실제 메타데이터의 일부 필드만 발췌했습니다. 전체 스키마는 필요한 필드와 자료형, 필수 여부, 허용값을 함께 정의합니다. 이 예시는 기존 evaluation 결과를 읽은 것이며 이 슬라이드 작업에서 새 인덱싱을 실행한 결과는 아닙니다.\n근거 파일: hybrid-ai-lab/indexer/vector-bm25/evaluation/results/comparison.json\n구현: hybrid-ai-lab/indexer/vector-bm25/app/domain/text_rules.py, chunk_metadata 및 _merge_contexts\n문서 프로필: hybrid-ai-lab/indexer/vector-bm25/config/document_profiles.json\n메타데이터 스키마: hybrid-ai-lab/indexer/vector-bm25/config/metadata_schema.json\n선택한 청크 상세 및 실제 발췌:\n${JSON.stringify(example,null,2)}`);
 return s;
}
async function main(){
 const script=path.join(__dirname,'..','metadata_structure_script.md');
 if(!fs.existsSync(script))throw new Error('사전 설명 스크립트가 필요합니다.');
 const example=JSON.parse(fs.readFileSync(path.join(__dirname,'example.json'),'utf8'));
 pptx=new pptxgen();
 pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';
 pptx.author='design-agentic-ai';pptx.title='메타데이터 구조 설계';pptx.subject='공통값 상속과 범위별 값 계산';pptx.lang='ko-KR';
 pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01(example);
 await pptx.writeFile({fileName:path.join(__dirname,'candidate.pptx')});
 console.log('Created metadata structure slide');
}
main().catch(e=>{console.error(e);process.exit(1);});
