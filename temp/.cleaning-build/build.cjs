const fs = require('node:fs');
const path = require('node:path');
const pptxgen = require('C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs');
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',tint:'EEF3FA',alt:'F5F8FC',tableHead:'E2EEF9',border:'D9E0EC',line:'EDF0F6',foot:'E9ECF3',white:'FFFFFF'};
const fsMin=n=>{if(n<14)throw new Error('14pt 미만 금지');return n;};
let pptx;
function text(s,t,x,y,w,h,o={}){
 const {size=20,color=C.ink,bold=false,align='left',...rest}=o;
 s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color,bold,align,margin:0,valign:'mid',paraSpaceAfterPt:0,...rest});
}
function rect(s,x,y,w,h,fill,stroke=fill){
 s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:0}});
}
function line(s,x,y,w,h,color=C.border,arrow=false){
 s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width:1.6,...(arrow?{endArrowType:'triangle'}:{})}});
}
function table(s,x,rows){
 const data=rows.map((r,i)=>r.map((t,j)=>({text:t,options:{fill:i===0?C.tableHead:(i%2?C.white:C.alt),bold:i===0||j===0,color:i===0?C.navy:C.ink}})));
 s.addTable(data,{x,y:3.01,w:7.17,colW:[2.24,4.93],rowH:[.46,.72,.72,.72],fontFace:FONT,fontSize:fsMin(18),margin:[.11,.16,.11,.16],valign:'middle',border:{type:'solid',color:C.border,pt:.7},autoPage:false});
}
function example(s,x,before,after){
 text(s,'처리 전',x,6.45,3.15,.3,{size:17,color:C.sub,bold:true});
 text(s,'처리 후',x+3.83,6.45,3.34,.3,{size:17,color:C.blue,bold:true});
 text(s,before,x,6.87,3.24,.87,{size:19,color:C.slate,breakLine:false});
 line(s,x+3.37,7.3,.32,0,C.blue,true);
 text(s,after,x+3.83,6.87,3.34,.87,{size:19,bold:true,color:C.navy});
}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};
 text(s,'문서 인덱싱  ›  청킹',.56,.35,13,.26,{size:15,color:C.sub});
 text(s,'정제 및 가명 처리',.56,.77,14.88,.7,{size:48,color:C.navy,bold:true});
 rect(s,.56,1.61,14.88,.035,C.border);rect(s,.56,1.61,2.08,.035,C.blue);
 text(s,'불필요한 반복 요소를 정리하고, 개인을 식별하는 값은 사용 목적에 맞게 바꿉니다.',.56,1.83,14.88,.51,{size:22,color:C.slate});
 text(s,'정제',.56,2.45,7.17,.43,{size:29,bold:true,color:C.navy});
 text(s,'가명 처리',8.27,2.45,7.17,.43,{size:29,bold:true,color:C.blue});
 table(s,.56,[
  ['대상','찾는 기준과 처리 방법'],
  ['머리말·꼬리말','페이지 위·아래에서 반복되는\n위치와 문구를 확인한 뒤 제거'],
  ['페이지 번호','위치·번호 패턴으로 찾아 본문에서 제거\n출처를 표시할 쪽 정보는 메타데이터에 유지'],
  ['공백·빈 줄\n제어문자','과한 공백·빈 줄과 불필요한 문자를 정리\n제목·조항·문단 구분자는 보존'],
 ]);
 table(s,8.27,[
  ['대상','목적에 맞는 처리 방법'],
  ['이름·회원 ID','관계를 유지하려면 가명 ID로 치환\n같은 대상에는 같은 고객_001을 부여'],
  ['전화·이메일\n고유번호','원래 값이 불필요하면 유형 토큰으로 치환\n예: [전화번호], [이메일], [카드번호]'],
  ['생년월일·상세주소','필요한 수준으로 범위를 넓혀 일반화\n예: 연령대(30대), 지역(서울시)'],
 ]);
 text(s,'정제 범위는 문서 형식에 맞춰 규칙으로 정합니다.',.56,6.04,7.17,.30,{size:17,color:C.slate});
 text(s,'필드·정규식으로 탐지하고, 이름·주소는 문맥도 확인합니다.',8.27,6.04,7.17,.30,{size:17,color:C.slate});
 example(s,.56,'회원 표준약관\n제6조 이용정지 …\n- 12 -','제6조 이용정지 …\n\n메타데이터: page=12');
 example(s,8.27,'김민지(M-87321), 35세\nminji@example.com','고객_001, 30대\n[이메일]');
 rect(s,.56,7.95,14.88,.44,C.tint);
 text(s,'유형 토큰은 값의 종류를 남기고, 가명 ID는 정한 범위 안에서 같은 대상의 관계를 유지합니다.',.77,8.00,14.46,.31,{size:19,bold:true,color:C.navy});
 line(s,.56,8.53,14.88,0,C.foot);
 text(s,'설명용 가상 예시 · 저장 전 본문과 메타데이터의 개인정보 잔존 여부를 확인합니다.',.56,8.64,13.85,.23,{size:14,color:C.sub});
 text(s,'01',14.62,8.62,.82,.27,{size:15,color:C.navy,align:'right'});
 const script=fs.readFileSync(path.join(__dirname,'..','cleaning_pseudonymization_script.md'),'utf8');
 s.addNotes(script.slice(script.indexOf('### 발표자 설명'))+'\n화면 예시 조정: 가명 처리의 입력은 가상 인물 김민지(M-87321), 35세, minji@example.com입니다. 출력 고객_001, 30대, [이메일]은 설계 예시이며 현행 코드의 실행 결과가 아닙니다. 가명 ID의 동일성은 이름만으로 판단하지 않고 식별된 대상과 정한 적용 범위를 기준으로 관리합니다. 정규식은 형식이 있는 전화·이메일·고유번호 탐지에 쓰며, 자유서술 이름·주소는 필드값 사전 또는 문맥 기반 인식 등을 보완할 수 있습니다. 일반화 수준은 검색 목적에 맞게 정합니다. 페이지 번호도 위치와 반복 형식을 확인하므로 본문의 조항 번호를 무조건 제거하지 않습니다. 단순 치환이나 일반화 하나로 재식별 위험 제거를 보증하지 않습니다.');
}
async function main(){
 if(!fs.existsSync(path.join(__dirname,'..','cleaning_pseudonymization_script.md')))throw new Error('사전 스크립트 필요');
 pptx=new pptxgen();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';
 pptx.author='design-agentic-ai';pptx.title='정제 및 가명 처리';pptx.subject='대상과 방법, 처리 전후 예시';pptx.lang='ko-KR';
 pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();await pptx.writeFile({fileName:path.join(__dirname,'candidate.pptx')});
 console.log('Created one-slide cleaning and pseudonymization deck');
}
main().catch(e=>{console.error(e);process.exit(1);});

