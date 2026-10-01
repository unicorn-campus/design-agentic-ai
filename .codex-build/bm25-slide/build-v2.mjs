import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const runtime='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const require=createRequire(import.meta.url);
const PptxGenJS=require(runtime+'/node/node_modules/pptxgenjs');
const root='C:/Users/hiond/class/design-agentic-ai';
const final=root+'/output/pptx/BM25-인덱싱-원리와-설계-1장-v2.pptx';
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',body:'3B4557',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',dark:'404155',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const fsMin=n=>{if(n<14)throw Error(`fontSize ${n} < 14pt 금지! 슬라이드를 분리할 것`);return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,valign:'middle',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function pageHeader(s,{crumb,title}){
 text(s,crumb,.55,.35,14.9,.28,15,{color:C.sub});
 text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});
 rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);
}
// 셀 안 일부 단어만 강조하려고 [문자열, 강조여부] 조각을 텍스트 런으로 바꿈
const runs=parts=>parts.map(([t,hi])=>({text:t,options:hi?{bold:true,color:C.blue}:{}}));
const cell=(t,o={})=>({text:t,options:o});

async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};
 pageHeader(s,{crumb:'벡터DB 구성 원리 › BM25 키워드 색인',title:'BM25 인덱싱의 원리와 설계'});
 text(s,'카드명·금액·코드처럼 글자가 같은 단어로 청크를 찾아, 뜻으로 찾는 벡터 검색을 보완합니다.',.55,1.78,14.9,.38,21,{color:C.slate});

 // 상단 4단계 흐름
 const stages=[
  ['1  청크 본문','본문(text)만 단어로 바꿈\nchunk_id로 원문과 연결'],
  ['2  Kiwi 토큰화','표기 통일 → 형태소 분석\n조사·어미 빼고 원형 보충'],
  ['3  bm25s 점수표','빈도·희소성·길이로 점수 계산\n검색 전에 미리 저장'],
  ['4  저장·검증','임시 폴더에서 완성한 뒤\n청크 수·해시 맞으면 교체']
 ];
 const xs=[.55,4.39,8.23,12.07];
 for(let i=0;i<4;i++){
  const x=xs[i],hot=i===2;
  rect(s,x,2.36,3.38,1.12,hot?C.navy:C.tint,hot?C.navy:C.border);
  text(s,stages[i][0],x+.17,2.49,3.04,.32,22,{bold:true,color:hot?C.white:C.navy});
  text(s,stages[i][1],x+.17,2.88,3.04,.50,16,{color:hot?C.white:C.slate});
  if(i<3)line(s,x+3.49,2.92,.23,0,C.blue,true,2);
 }

 // 좌: 실제 실행 예시
 text(s,'예시: 한 문장이 색인 단어가 되기까지',.55,3.72,6.0,.38,22,{bold:true,color:C.navy});
 text(s,'실제 실행 결과',6.6,3.74,2.6,.34,14,{color:C.sub,align:'right'});
 const L=(t)=>cell(t,{bold:true,color:C.navy,fill:C.alt});
 const ex=[
  [cell('단계',{bold:true,color:C.navy,fill:C.head}),cell('결과',{bold:true,color:C.navy,fill:C.head})],
  [L('원문'),cell('한빛 가족돌봄 카드로 30,000원 이상 결제하면 KB-PAY 할인을 받습니다.')],
  [L('① 표기 통일'),cell(runs([['한빛 가족돌봄 카드로 '],['30000원',1],[' 이상 결제하면 '],['kb-pay',1],[' 할인을 받습니다.']]))],
  [L('② 남긴 단어'),cell(runs([['한빛가족돌봄',1],[' · 카드 · 30000 · 원 · 이상 · 결제 · kb · pay · 할인 · 받']]))],
  [L('③ 버린 조각'),cell('로 · 하 · 면 · 을 · 습니다 · 하이픈 · 마침표   (조사·어미·접미사·기호)',{color:C.sub})],
  [L('④ 원형 추가'),cell(runs([['30000원 · kb-pay',1],['   (금액·코드를 통째로도 찾도록)']]))],
  [L('최종'),cell('②+④ = 12개 단어  →  bm25s가 점수 계산',{bold:true,color:C.navy})]
 ];
 s.addTable(ex,{x:.55,y:4.2,w:8.65,colW:[1.45,7.2],rowH:.42,fontFace:FONT,fontSize:fsMin(15),color:C.body,margin:[.04,.1,.04,.1],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});
 rect(s,.55,7.25,8.65,1.2,C.tint,C.border);
 text(s,'카드명 사전의 효과와 한계',.72,7.33,8.3,.3,15,{bold:true,color:C.blue});
 text(s,[
  {text:'있음  ',options:{bold:true,color:C.navy}},{text:'한빛가족돌봄',options:{bold:true,color:C.blue}},{text:'  → 카드명 전체가 한 단어로 정확히 일치',options:{breakLine:true}},
  {text:'없음  ',options:{bold:true,color:C.navy}},{text:'한빛 · 가족 · 돌봄 · 가족돌봄  → 카드 64종이 모두 "한빛"으로 시작해 구분이 약함',options:{breakLine:true}},
  {text:'한계  "한빛" 없이 "가족돌봄"만 쓴 질문은 이 카드명 단어와 일치하지 않음',options:{color:C.sub}}
 ],.72,7.64,8.3,.76,14,{color:C.body,valign:'top',lineSpacingMultiple:1.05});

 // 우: 설정값
 text(s,'우리 코드의 설정값',9.5,3.72,5.95,.38,22,{bold:true,color:C.navy});
 const rows=[
  ['항목','현재 값'],
  ['색인 단위','청크 1개 = 문서 1개'],
  ['점수 공식','bm25s · Lucene 방식'],
  ['조절값','k1 = 1.5  ·  b = 0.75'],
  ['카드명 사전','D2 카드명 → 고유명사(NNP)'],
  ['검색과 일치','검색도 같은 규칙 사용(서명 대조)'],
  ['갱신 방식','새 세대로 전체 재색인 후 전환'],
  ['기본 꺼짐','정적 사전 · 미등록어 후보 추출']
 ];
 s.addTable(rows.map((r,i)=>r.map((t,j)=>cell(t,{fill:i===0?C.head:(i%2?C.white:C.alt),bold:i===0||j===0,color:i===0||j===0?C.navy:C.body}))),{x:9.5,y:4.2,w:5.95,colW:[1.6,4.35],rowH:.4,fontFace:FONT,fontSize:fsMin(15),margin:[.04,.1,.04,.1],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});
 text(s,'k1: 같은 단어가 반복될 때 점수가 더 오르는 정도\nb: 긴 청크의 점수를 깎는 정도\nNNP 0.0의 0.0은 Kiwi 등록 가중치 (BM25 점수 아님)',9.5,7.55,5.95,.9,14,{color:C.slate,valign:'top'});

 line(s,.55,8.59,14.9,0,C.footer,false,.7);
 text(s,'코드 근거: korean_tokenizer.py · lexical_index.py · index_repository.py · bm25_index.py',.55,8.68,12.3,.2,14,{color:C.sub});
 text(s,'BM25  /  1',13.0,8.68,2.45,.2,14,{color:C.sub,align:'right'});

 s.addNotes(`BM25 키워드 색인은 질문의 단어와 글자가 같은 단어를 가진 청크를 빨리 찾기 위한 준비 작업입니다. 카드명, 금액, 상품 코드처럼 정확한 표현에 강하고, 뜻으로 찾는 벡터 검색을 보완합니다. BM25는 임베딩 모델이 아니라 단어 빈도(TF), 전체 청크에서 그 단어가 얼마나 드문지(IDF), 청크 길이(색인 단어 수 기준)로 순위를 매기는 계산 방식입니다.

1단계: 정제된 청크 하나가 corpus 한 줄이 됩니다. Kiwi에는 본문 text만 넣고, 메타데이터는 본문처럼 색인하지 않습니다. 메타데이터의 카드명은 카드명 사전을 만드는 데에만 씁니다.

2단계: 먼저 우리 정규화 함수가 표기를 통일합니다(NFKC 문자 표준화, 영문 소문자화, 숫자 사이 쉼표 제거). 그다음 Kiwi가 형태소로 나누고, 우리 코드가 내용어 품사(_CONTENT_TAGS)만 남깁니다. 조사·어미·접미사·기호는 품사 필터로 빠지며 별도 불용어 사전은 없습니다. 숫자가 든 표현, 영문과 하이픈 등 코드 구분자가 함께 든 표현, 사전 단어, 모두 내용어로만 된 복합어는 원래 모양 그대로도 한 번 더 넣습니다. 같은 출현을 두 번 세지 않도록 Counter로 개수를 맞춥니다.

예시는 2026-10-01에 활성 세대(gen-20260930T135203Z, 청크 192개, 카드명 64개)의 카드명 사전으로 KoreanTokenizer.tokenize를 실제 실행한 결과입니다. 이 설정의 토크나이저 서명은 활성 manifest의 tokenizer_signature와 일치했습니다. 원문 한 문장에서 12개 단어가 나왔고, "한빛가족돌봄"은 실제 BM25 단어 목록(vocab)에도 들어 있습니다.

카드명 사전: D2 문서(또는 benefit_guide) 메타데이터의 card_id와 card_name 대응을 검사한 뒤, 카드명을 고유명사(NNP), 등록 가중치 0.0으로 Kiwi에 추가합니다. 0.0은 Kiwi 단어 등록 점수이며 BM25 점수와 무관합니다. 사전은 card_names.dict로 저장합니다. 사전이 없으면 "한빛 가족돌봄"이 한빛·가족·돌봄·가족돌봄으로 쪼개지고, 64종 카드가 모두 "한빛"으로 시작하므로 카드를 구분하는 힘이 약해집니다. 대신 한계도 있습니다. 색인된 카드명은 "한빛가족돌봄" 한 단어뿐이라, "한빛" 없이 "가족돌봄"만 쓴 질문은 이 카드명 단어와 일치하지 않습니다. 또 숫자 뒤에 조사가 바로 붙으면 "30000원을"처럼 조사까지 원형 토큰에 남습니다.

3단계: bm25s.BM25(method='lucene', k1=1.5, b=0.75)로 색인합니다. bm25s는 단어별·청크별 점수 기여도를 미리 계산해 희소 행렬로 저장하므로 검색할 때는 더하기만 하면 됩니다. k1은 같은 단어가 반복될 때 점수가 얼마나 더 오르는지(포화 정도), b는 긴 청크의 점수를 얼마나 깎는지를 정합니다. 이 값은 우리 코드의 설정값입니다.

4단계: corpus.jsonl, card_names.dict, bm25 폴더, oov_candidates.json, manifest.json을 형제 임시 폴더에서 모두 만든 뒤 검증하고 최종 위치로 옮깁니다. 검증은 포인터·manifest·corpus의 청크 수와 corpus·카드명 사전 해시가 서로 맞는지 봅니다. Retriever는 같은 카드명 사전으로 토크나이저를 만들고, 사전 해시와 토크나이저 서명이 색인 때와 같을 때만 색인을 읽습니다. 데이터가 바뀌면 BM25는 청크 단위로 고치지 않고 새 세대에 전체를 다시 만들며, 벡터(Chroma)와 BM25를 함께 검증한 뒤 활성 포인터 하나를 바꿔 동시에 전환합니다.

기본으로 꺼진 것: 정적 사용자 사전 파일은 지원하지만 bootstrap.py가 LexicalIndexBuilder()를 인자 없이 만들어 연결되지 않습니다. 미등록어(OOV) 후보 추출도 기본 꺼짐이며, 켜더라도 사람이 검토할 후보만 저장하고 자동 등록하지 않습니다. typo_policy 값은 서명에만 기록되며 색인 때 오타 교정을 하지는 않습니다.

소스 근거:
hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/korean_tokenizer.py (정규화·_CONTENT_TAGS·원형 보존·서명)
hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py (카드명 사전·bm25s 생성·저장·검증)
hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py (세대 단위 재색인·동시 전환)
hybrid-ai-lab/indexer/vector-bm25/app/bootstrap.py:47 (LexicalIndexBuilder 기본값)
hybrid-ai-lab/retriever/vector-retriever/app/infrastructure/bm25_index.py (검색 측 해시·서명 대조)
공식 참고: https://github.com/xhluca/bm25s , https://github.com/bab2min/kiwipiepy`);
}
async function main(){
 pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';
 pptx.author='design-agentic-ai';pptx.title='BM25 인덱싱의 원리와 설계';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 for(const fn of [createSlide01])await fn();
 await pptx.writeFile({fileName:final});
 const {FileBlob,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
 const p=await PresentationFile.importPptx(await FileBlob.load(final));
 const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});
 await fs.writeFile(final.replace(/\.pptx$/,'.png'),new Uint8Array(await png.arrayBuffer()));
 console.log('✅ PPT 생성 완료',final);
}
main().catch(e=>{console.error('❌ PPT 생성 실패:',e);process.exit(1);});
