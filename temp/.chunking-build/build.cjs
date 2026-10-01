const fs = require('node:fs');
const path = require('node:path');
const pptxgen = require('C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs');

const OUT = path.join(__dirname, 'candidate.pptx');
const SCRIPT = path.join(__dirname, '..', 'chunking_slides_script.md');
const FONT = 'Pretendard';
const C = { navy:'1E2A5C', blue:'2E74C6', ink:'2B3242', slate:'4A5364', sub:'7C8598', tint:'EEF3FA', alt:'F5F8FC', tableHead:'E2EEF9', dark:'404155', border:'D9E0EC', line:'EDF0F6', foot:'E9ECF3', white:'FFFFFF' };
const fsMin = n => { if (n < 14) throw new Error('14pt 미만 글꼴 금지'); return n; };
const sources = {
 base:'https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/base.py',
 recursive:'https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/character.py',
 azure:'https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents',
};
let pptx;
function text(s, value, x,y,w,h,opts={}) {
 const {size=20,color=C.ink,bold=false,align='left',...rest}=opts;
 s.addText(value,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color,bold,align,valign:'mid',margin:0,breakLine:false,paraSpaceAfterPt:0,...rest});
}
function rect(s,x,y,w,h,fill=C.white,line=C.border,lw=1) {
 s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:line,width:lw}});
}
function line(s,x1,y1,x2,y2,color=C.blue,width=1.7,arrow=false){
 s.addShape(pptx.shapes.LINE,{x:x1,y:y1,w:x2-x1,h:y2-y1,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});
}
function header(s,no,title,lead){
 s.background={color:C.white};
 text(s,'문서 인덱싱  ›  청킹',.56,.35,13,.26,{size:15,color:C.sub});
 text(s,title,.56,.77,14.88,.7,{size:48,color:C.navy,bold:true});
 rect(s,.56,1.61,14.88,.035,C.border,C.border,0);
 rect(s,.56,1.61,2.08,.035,C.blue,C.blue,0);
 text(s,lead,.56,1.83,14.88,.52,{size:22,color:C.slate});
 line(s,.56,8.52,15.44,8.52,C.foot,1);
 text(s,'Agentic AI 아키텍처 설계',.56,8.64,12,.23,{size:14,color:C.sub});
 text(s,String(no).padStart(2,'0'),14.6,8.62,.84,.27,{size:15,color:C.navy,align:'right'});
}
function band(s,x,y,w,label,fill=C.navy){
 rect(s,x,y,w,.52,fill,fill,0);
 text(s,label,x+.2,y+.05,w-.4,.41,{size:22,bold:true,color:C.white});
}
function note(s,heading,body,x,y,w){
 text(s,heading,x,y,w,.4,{size:22,bold:true,color:C.navy});
 text(s,body,x,y+.56,w,1.04,{size:20,color:C.slate,breakLine:false});
}

async function createSlide01(){
 const s=pptx.addSlide();
 header(s,1,'한 청크의 구성','청크는 검색할 본문과, 그 본문의 출처·조건을 함께 담습니다.');

 // 하나의 청크 객체 안에 두 부분이 있음을 실제 편집 가능한 도형으로 표현함.
 const x=2.83,y=2.73,w=10.34,h=4.36;
 rect(s,x,y,w,h,C.white,C.navy,1.7);
 band(s,x,y,w,'청크 01   ·   가상 약관 예시');
 rect(s,x,y+.52,4.5,h-.52,C.tint,C.border,0);
 line(s,x+4.5,y+.52,x+4.5,y+h,C.border,1.1);
 text(s,'메타데이터',x+.32,y+.83,3.9,.47,{size:28,bold:true,color:C.navy});
 text(s,'출처와 검색 조건',x+.32,y+1.35,3.9,.36,{size:18,color:C.slate});
 text(s,'출처  카드약관.pdf\n쪽  12\n조항  제3조\n공개 등급  public',x+.32,y+1.98,3.95,1.96,{size:22,paraSpaceAfterPt:14});
 text(s,'본문',x+4.86,y+.83,4.95,.47,{size:28,bold:true,color:C.blue});
 text(s,'질문의 답을 찾는 내용',x+4.86,y+1.35,4.95,.36,{size:18,color:C.slate});
 text(s,'제3조 연회비 반환\n\n카드를 해지하면 남은 기간에\n해당하는 연회비를 반환합니다.\n다만, 발급 비용은 제외합니다.',x+4.86,y+1.98,4.96,1.98,{size:23,paraSpaceAfterPt:6});

 note(s,'어디서 왔나','출처를 표시하고\n검색 범위를\n좁힙니다.',.56,3.69,1.95);
 line(s,2.44,4.98,2.74,4.98,C.navy,1.8,true);
 note(s,'무엇을 답하나','관련 내용을 찾고\n답변의 근거로\n사용합니다.',13.59,3.69,1.88);
 line(s,13.26,4.98,13.54,4.98,C.blue,1.8,true);
 text(s,'메타데이터와 본문은 같은 청크에 연결됩니다.',2.83,7.48,10.34,.4,{size:25,bold:true,color:C.navy,align:'center'});
 text(s,'상품명처럼 검색과 필터에 모두 필요한 값은 양쪽에 둘 수 있습니다.',2.05,8.00,11.9,.31,{size:18,color:C.slate,align:'center'});
 s.addNotes(`청크는 하나의 검색 단위입니다. 메타데이터는 출처 표시, 필터링, 접근 범위 판단에 쓰이고 본문은 검색 및 답변 근거에 쓰입니다. 화면의 약관 파일과 문구는 설명을 위한 가상 예시이며 실제 규정이 아닙니다. 본문에서 계산한 임베딩 벡터를 색인에 함께 저장할 수 있지만 이 장은 사용자가 요청한 본문과 메타데이터에 초점을 맞춥니다. 상품명 등은 의미 검색을 위해 본문에, 정확한 필터를 위해 메타데이터에도 둘 수 있습니다. LangChain Document의 page_content와 metadata에 대응합니다.\n출처: ${sources.base}`);
 return s;
}

async function createSlide02(){
 const s=pptx.addSlide();
 header(s,2,'청킹 설계의 결정 항목','무엇을 물려주고, 어디서 나누며, 얼마나 겹칠지 함께 정합니다.');

 const rows=[
  ['설계 항목','정의할 내용'],
  ['메타데이터 구조','필드·자료형·필수 여부\n공통값 상속 / 범위별 값 계산'],
  ['구분자','조항·문단·발화 등 경계 우선순위\n구분자 보존과 긴 단위의 추가 분할'],
  ['청킹 크기','목표·최대 크기와 단위\n토큰 측정기·모델 입력 한도'],
  ['오버랩 크기','반복할 문맥의 크기와 단위\n중첩을 적용할 경계'],
  ['정제·가명처리','적용 규칙과 청킹 전·후 시점\n본문·메타데이터 처리 범위'],
  ['검증·평가','개인정보 잔존·필수값·최종 길이\n평가 질문의 정답 근거 검색 여부'],
 ];
 s.addTable(rows.map((r,i)=>r.map(v=>({text:v,options:{fill:i===0?C.tableHead:(i%2?C.white:C.alt),bold:i===0,color:i===0?C.navy:C.ink}}))),{
  x:.56,y:2.62,w:7.93,colW:[2.15,5.78],rowH:[.54,.70,.70,.70,.70,.70,.70],
  fontFace:FONT,fontSize:fsMin(18),margin:[.07,.17,.07,.17],valign:'middle',border:{type:'solid',color:C.border,pt:.6},autoPage:false,paraSpaceAfterPt:1,
 });
 text(s,'크기와 오버랩의 관계',9.05,2.67,6.34,.47,{size:27,bold:true,color:C.navy});
 text(s,'설명용 예시: 크기 400토큰, 중첩 100토큰',9.05,3.25,6.34,.35,{size:17,color:C.slate});
 const start=9.07,unit=.9,gap=.012;
 text(s,'원문',start,3.84,6.25,.3,{size:18,bold:true,color:C.slate});
 for(let i=0;i<7;i++){
  rect(s,start+i*unit,4.30,unit-gap,.54,i===3?C.blue:C.alt,i===3?C.blue:C.border,.75);
  text(s,String.fromCharCode(65+i),start+i*unit,4.37,unit-gap,.36,{size:20,bold:true,color:i===3?C.white:C.slate,align:'center'});
 }
 text(s,'청크 1   400토큰',start,5.10,3.65,.35,{size:20,bold:true,color:C.navy});
 rect(s,start,5.6,4*unit,.7,C.tint,C.navy,1.2);
 rect(s,start+3*unit,5.6,unit,.7,C.blue,C.blue,0);
 text(s,'A     B     C',start+.07,5.73,2.56,.4,{size:21,color:C.navy,align:'center'});
 text(s,'D',start+3*unit,5.73,unit,.4,{size:21,bold:true,color:C.white,align:'center'});
 const b=start+3*unit;
 text(s,'청크 2   400토큰',b+unit+.12,6.59,2.59,.35,{size:19,bold:true,color:C.navy});
 rect(s,b,7.08,4*unit,.7,C.tint,C.navy,1.2);
 rect(s,b,7.08,unit,.7,C.blue,C.blue,0);
 text(s,'D',b,7.22,unit,.38,{size:21,bold:true,color:C.white,align:'center'});
 text(s,'E     F     G',b+unit+.02,7.22,2.64,.38,{size:21,color:C.navy,align:'center'});
 line(s,b+unit/2,6.31,b+unit/2,7.03,C.blue,1.7,true);
 text(s,'D 구간을 두 청크에 포함\n중첩 100토큰',start,6.5,2.53,.85,{size:18,bold:true,color:C.blue});
 text(s,'A–G는 각각 100토큰인 가상의 구간입니다.',9.05,7.98,6.3,.29,{size:15,color:C.sub});
 text(s,'크기와 중첩의 단위를 명시하고, 정제 후 최종 청크를 검증합니다.',.56,8.03,7.93,.32,{size:17,bold:true,color:C.navy});
 s.addNotes(`청킹 설계는 숫자 두 개만 정하는 일이 아닙니다. 먼저 검색과 출처 표시에 필요한 메타데이터의 필드, 자료형, 필수 여부를 정합니다. 공통값은 상속하고 청크 범위에 따라 달라지는 값은 구조나 위치를 보고 계산합니다. 명확한 구분자가 있으면 그 경계를 우선하며 너무 긴 단위를 어떻게 추가 분할할지도 정합니다. 크기 단위는 문자와 토큰을 구분하고 토큰을 사용한다면 모델에 맞는 측정기를 정합니다. 오버랩은 앞 청크의 일부를 다음 청크에도 넣어 경계의 문맥을 이어주는 것입니다. 도식의 400/100토큰과 A–G 구간은 설명용 가정이며 권장 최적값이 아닙니다. 정제 규칙이 필요한 구조 정보를 보존한다면 청킹 전에 정제할 수 있습니다. 처리 시점은 설계 결정이며 특정 프레임워크가 강제하는 표준 순서가 아닙니다. 검사는 최종 본문과 메타데이터를 대상으로 하고, 검색 품질은 평가 질문으로 확인합니다.\n출처: ${sources.base}\n${sources.recursive}\n${sources.azure}`);
 return s;
}

function miniChunk(s,x,y,w,label){
 rect(s,x,y,w,1.23,C.white,C.border,1.1);
 rect(s,x,y,w,.38,C.tint,C.tint,0);
 text(s,'source·page 유지',x+.1,y+.04,w-.2,.29,{size:16,bold:true,color:C.navy,align:'center'});
 text(s,label,x+.1,y+.56,w-.2,.4,{size:22,bold:true,color:C.ink,align:'center'});
}
async function createSlide03(){
 const s=pptx.addSlide();
 header(s,3,'청킹 Best Practice','LangChain의 메타데이터 전달과 Azure AI Search의 크기·중첩 권고를 참고합니다.');
 line(s,8.0,2.63,8.0,7.64,C.border,1);
 text(s,'LangChain',.56,2.64,6.96,.46,{size:30,bold:true,color:C.navy});
 text(s,'공통 메타데이터를 청크마다 복사',.56,3.18,6.96,.43,{size:23,bold:true,color:C.blue});
 rect(s,1.83,3.91,4.39,1.13,C.tint,C.navy,1.1);
 text(s,'입력 문서',2.03,4.04,3.99,.33,{size:23,bold:true,color:C.navy,align:'center'});
 text(s,'source: 약관.pdf   page: 12',2.03,4.55,3.99,.28,{size:17,color:C.slate,align:'center'});
 line(s,4.03,5.05,4.03,5.42,C.navy,1.4);
 line(s,2.12,5.42,5.94,5.42,C.navy,1.4);
 line(s,2.12,5.42,2.12,5.73,C.navy,1.4,true);
 line(s,5.94,5.42,5.94,5.73,C.navy,1.4,true);
 miniChunk(s,.59,5.81,3.06,'분할 본문 A');
 miniChunk(s,4.41,5.81,3.06,'분할 본문 B');
 text(s,'구분자 우선순위를 정하고, 긴 단위를 더 나눕니다.',.56,7.28,6.96,.38,{size:18,color:C.slate});

 text(s,'Azure AI Search',8.55,2.64,6.89,.46,{size:30,bold:true,color:C.navy});
 text(s,'512토큰·25% 중첩을 출발점으로',8.55,3.18,6.89,.43,{size:23,bold:true,color:C.blue});
 const ax=8.63, unit=.94, barW=4*unit, by=ax+3*unit;
 text(s,'청크 A   512토큰',ax,3.92,barW,.33,{size:20,bold:true,color:C.navy});
 rect(s,ax,4.45,barW,.68,C.tint,C.navy,1.2);
 rect(s,ax+3*unit,4.45,unit,.68,C.blue,C.blue,0);
 text(s,'384토큰',ax+.1,4.61,unit*3-.2,.32,{size:20,color:C.navy,align:'center'});
 text(s,'128',ax+3*unit,4.61,unit,.32,{size:20,bold:true,color:C.white,align:'center'});
 line(s,by+unit/2,5.14,by+unit/2,6.04,C.blue,1.7,true);
 text(s,'같은 128토큰을\n두 청크에 포함',ax,5.52,2.66,.69,{size:19,bold:true,color:C.blue});
 text(s,'청크 B   512토큰',by+unit+.1,5.49,2.72,.33,{size:19,bold:true,color:C.navy});
 rect(s,by,6.10,barW,.68,C.tint,C.navy,1.2);
 rect(s,by,6.10,unit,.68,C.blue,C.blue,0);
 text(s,'128',by,6.26,unit,.32,{size:20,bold:true,color:C.white,align:'center'});
 text(s,'384토큰',by+unit+.1,6.26,unit*3-.2,.32,{size:20,color:C.navy,align:'center'});
 text(s,'문서 구조와 평가 질문에 맞춰 크기·중첩을 조정합니다.',8.55,7.28,6.89,.38,{size:18,color:C.slate});
 rect(s,.56,7.91,14.88,.43,C.tint,C.tint,0);
 text(s,'정제 시점은 별도 설계 결정입니다. 두 사례가 청킹 전·후의 순서를 강제하지는 않습니다.',.76,7.97,14.48,.3,{size:18,bold:true,color:C.navy,align:'center'});
 s.addNotes(`왼쪽은 LangChain의 실제 TextSplitter 동작을 설명한 도식입니다. split_documents는 각 입력 문서의 본문과 metadata를 create_documents에 전달하며, create_documents는 분할 청크마다 metadata를 deepcopy합니다. source/page를 가진 문서는 설명용 예시입니다. 다른 페이지까지 합친 문서에 원래의 page 하나만 복사하면 페이지별 출처가 자동 계산되는 것은 아닙니다. 청크 범위에 따라 달라지는 페이지와 조항은 따로 계산해야 합니다. RecursiveCharacterTextSplitter는 지정한 구분자 순서로 긴 텍스트를 재귀적으로 나눕니다. 기본 구분자는 문단, 줄바꿈, 공백, 문자 수준입니다. 오른쪽은 Azure AI Search 공식 문서의 초기 권고 512토큰과 25% 중첩(128토큰)을 도식화한 것입니다. 정확히 이 크기로 자르는 가상 사례이며 구조·문장 경계에 따라 실제 길이와 중첩은 달라질 수 있습니다. 보편적 최적값이나 본 프로젝트의 실측 결과가 아닙니다. 출처 문서는 구조가 명확한 데이터에는 더 적은 중첩이 적합할 수 있다고 설명합니다. 두 사례는 개인정보 정제 시점을 강제하지 않습니다.\n출처 확인일: 2026-10-01\nLangChain TextSplitter: ${sources.base}\nRecursiveCharacterTextSplitter: ${sources.recursive}\nMicrosoft Azure AI Search: ${sources.azure}`);
 return s;
}
async function main(){
 if(!fs.existsSync(SCRIPT)) throw new Error('사전 설명 스크립트가 필요합니다.');
 pptx=new pptxgen();
 pptx.defineLayout({name:'CUSTOM',width:16,height:9});
 pptx.layout='CUSTOM';
 pptx.author='design-agentic-ai'; pptx.subject='청크 구성과 청킹 설계 및 공식 사례';
 pptx.title='청킹 설계와 Best Practice'; pptx.company='design-agentic-ai'; pptx.lang='ko-KR';
 pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 for(const fn of [createSlide01,createSlide02,createSlide03]) await fn();
 await pptx.writeFile({fileName:OUT});
 console.log(JSON.stringify({file:OUT,slides:3}));
}
main().catch(e=>{console.error(e);process.exit(1);});
