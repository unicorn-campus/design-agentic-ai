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
const build=root+'/.codex-build/bm25-slide';
const final=root+'/output/pptx/BM25-인덱싱-원리와-설계-1장.pptx';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const fsMin=n=>{if(n<14)throw Error('Minimum font size 14pt');return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,breakLine:false,vertAnchor:'ctr',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function pageHeader(s,title){text(s,'벡터DB 구성 원리 › BM25 키워드 색인',.55,.35,14.9,.28,15,{color:C.sub});text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};pageHeader(s,'BM25 인덱싱의 원리와 설계');
 text(s,'카드명·상품코드처럼 정확한 단어로 청크를 찾도록, 벡터 검색을 보완하는 키워드 색인을 만듭니다.',.55,1.78,14.9,.38,21,{color:C.slate});
 const stages=[
 ['1  정제 청크','본문을 색인 입력으로 사용\nchunk_id로 원문과 연결'],
 ['2  Kiwi 토큰화','표기를 통일하고 형태소 분석\n내용어와 필요한 원형 보존'],
 ['3  bm25s 색인','단어 빈도·희소성·길이 반영\n토큰별 점수를 미리 저장'],
 ['4  저장·검증','corpus · 사전 · BM25 · manifest\n파일 개수·해시 검증']
 ];
 const xs=[.55,4.39,8.23,12.07];
 for(let i=0;i<4;i++){
  const x=xs[i];rect(s,x,2.47,3.38,1.15,i===2?C.navy:C.tint,i===2?C.navy:C.border);
  text(s,stages[i][0],x+.17,2.62,3.04,.30,22,{bold:true,color:i===2?C.white:C.navy});
  text(s,stages[i][1],x+.17,3.04,3.04,.43,16,{color:i===2?C.white:C.slate});
  if(i<3)line(s,x+3.49,3.05,.23,0,C.blue,true,2);
 }
 text(s,'정규화 예시',.55,3.82,1.75,.29,17,{bold:true,color:C.blue});
 text(s,'30,000원 KB-PAY',2.37,3.82,2.68,.29,18,{color:C.ink});
 line(s,5.12,3.96,.43,0,C.blue,true,1.6);
 text(s,'30000원 kb-pay',5.70,3.82,2.68,.29,18,{bold:true,color:C.navy});
 text(s,'우리 정규화 함수 실행 결과이며, 형태소 목록은 아닙니다.',8.47,3.84,6.98,.26,14,{color:C.sub});
 text(s,'Kiwi에 적용한 기술',.55,4.46,7.3,.37,24,{bold:true,color:C.navy});
 text(s,'우리 코드의 설계 항목',8.25,4.46,7.2,.37,24,{bold:true,color:C.navy});
 text(s,'내용어 필터와 원형 보존',.55,5.07,7.25,.29,20,{bold:true,color:C.blue});
 text(s,'조사·어미를 걸러내고 명사·용언 등을 남깁니다.\n숫자·단위·코드·사전어·내용어 복합어의 표기도 보존합니다.',.55,5.49,7.25,.65,18,{color:C.slate});
 text(s,'D2 카드명 동적 사용자 사전',.55,6.43,7.25,.29,20,{bold:true,color:C.blue});
 text(s,'메타데이터의 카드명을 고유명사(NNP)로 자동 등록합니다.',.55,6.85,7.25,.29,18,{color:C.slate});
 rect(s,.55,7.28,7.25,.48,C.alt,C.border);
 text(s,'저장된 사전 예시:  한빛 가족돌봄    NNP    0.0',.72,7.39,6.92,.25,17,{color:C.navy});
 text(s,'정적 사전 파일: 지원하지만 기본 미연결\n미등록어(OOV) 후보 추출: 기본 꺼짐, 자동 등록 없음',.55,7.98,7.25,.50,15,{color:C.sub});
 const rows=[
 ['설계 항목','현재 코드'],
 ['색인 단위','정제 청크 1개 = corpus 1행'],
 ['점수 방식','bm25s · Lucene 방식'],
 ['점수 계수','k1 = 1.5  /  b = 0.75'],
 ['검색과 일관성','사전 해시·토크나이저 서명 검증'],
 ['갱신·발행','새 세대 전체 색인 후 벡터와 함께 전환']
 ];
 s.addTable(rows.map((r,i)=>r.map(t=>({text:t,options:{fill:i===0?C.head:(i%2?C.white:C.alt),bold:i===0,color:i===0?C.navy:C.ink}}))),{x:8.25,y:5.07,w:7.2,h:2.94,colW:[2.15,5.05],rowH:[.44,.50,.50,.50,.50,.50],fontFace:FONT,fontSize:fsMin(17),margin:[.08,.12,.08,.12],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});
 text(s,'k1: 단어 반복의 영향  /  b: 청크 길이 보정의 강도',8.25,8.20,7.2,.26,16,{color:C.slate});
 line(s,.55,8.59,14.9,0,C.footer,false,.7);
 text(s,'코드 근거: lexical_index.py · korean_tokenizer.py · bootstrap.py · bm25_index.py',.55,8.68,12.3,.2,14,{color:C.sub});
 text(s,'BM25  /  1',13.0,8.68,2.45,.2,14,{color:C.sub,align:'right'});
 s.addNotes(`BM25 인덱싱의 목적은 질문에 나타난 단어와 일치하는 단어가 있는 청크를 빠르게 검색할 준비를 하는 것입니다. 카드명, 상품코드, 숫자 같은 정확한 표현을 찾는 데 유용하며 벡터 검색의 의미 유사도 검색을 보완합니다. BM25는 임베딩 모델이 아니라 단어 기반 순위 계산 방식입니다. 문서별 출현 빈도(TF), 전체 청크 집합에서 단어가 드문 정도(IDF), 청크 길이를 반영합니다. 길이는 원문 글자 수가 아니라 색인 토큰 수를 기준으로 봅니다.\n\nLexicalIndexBuilder는 정제된 PreparedChunk 하나를 corpus 레코드 하나로 만들며, text만 Kiwi 토큰화 입력으로 전달합니다. corpus에는 chunk_id와 메타데이터도 함께 저장하지만 메타데이터 전체를 본문처럼 색인하지 않습니다. D2 메타데이터의 카드명은 동적 사용자 사전 구성에 별도로 활용합니다. 토큰 배열의 행 순서와 corpus 행 순서가 대응합니다.\n\n정규화는 NFKC 문자 표기 통일, 영문 소문자화, 숫자 사이 쉼표 제거입니다. 화면 예시는 우리 normalize_korean_text('30,000원 KB-PAY') 함수만 이번 작업에서 실행한 결과인 '30000원 kb-pay'입니다. Kiwi 형태소 분석이나 전체 색인을 이번 작업에서 실행한 결과는 아닙니다.\n\nKiwi 형태소 분석 뒤 _CONTENT_TAGS에 지정한 내용어 품사만 남깁니다. 별도의 고정 불용어 사전을 적용하는 것이 아니라 품사 필터로 조사와 어미 등을 제외합니다. 기본 품사 태그의 규칙성 접미사도 제거합니다. 숫자 포함 표현, 영문과 코드 구분자를 함께 포함하는 표현, 사용자 사전어 및 모두 내용어인 복합 표현은 원형 토큰을 보충합니다. 같은 출현을 두 번 세지 않도록 Counter로 형태소와 표면형의 빈도를 맞춥니다.\n\nD2 문서 또는 benefit_guide 메타데이터에서 card_id와 card_name의 대응을 검증한 후 카드명을 NNP, score=0.0으로 동적 등록합니다. score는 Kiwi의 단어 등록 점수이며 BM25 검색 점수가 아닙니다. 사전은 card_names.dict로 저장합니다. '한빛 가족돌봄\tNNP\t0.0'은 기존 저장 세대의 실제 사전 항목입니다. 카드명 수와 데이터 규모는 화면에 고정하지 않았습니다. 정적 사전 파일 로더 load_user_dictionary도 지원하지만 bootstrap.py는 LexicalIndexBuilder()를 인자 없이 생성하므로 기본 user_dictionary=None입니다. OOV 후보 추출은 기본 False이고, 활성화하더라도 사람이 검토할 후보를 저장할 뿐 자동 등록하지 않습니다. typo_policy='basic'은 검색 측 계약을 서명에 담기 위한 값입니다. 인덱싱 Kiwi 생성자에는 오타 교정 설정을 전달하지 않으므로 오타 교정을 수행한다고 설명하지 않습니다.\n\n우리 BM25 기본값은 method='lucene', k1=1.5, b=0.75입니다. k1은 단어가 반복될 때 점수가 포화되는 정도에 영향을 주고, b는 청크 길이 정규화의 강도를 조절합니다. 이는 이 코드의 설정값이지 모든 제품의 공통 기본값은 아닙니다. bm25s는 토큰별 점수 기여도를 미리 계산해 희소 행렬에 저장하는 구현입니다. bm25.index(tokens) 뒤 bm25.save()로 저장합니다.\n\n본문·사전·BM25·manifest를 임시 검색 루트에서 완성하고 검증한 뒤 승격합니다. corpus와 사전 해시, 토크나이저 서명, 문서 개수 등으로 일관성을 확인합니다. Retriever는 같은 동적 사전을 로드하고 토크나이저 서명을 대조한 뒤 색인을 읽습니다. 상위 GenerationIndexRepository는 벡터와 BM25를 같은 세대로 준비하고 검증한 후 활성 포인터를 교체합니다. 변경이 있을 때 BM25는 해당 새 세대의 전체 corpus로 구성하며 BM25에 청크별 upsert를 호출하는 구현은 아닙니다.\n\n소스 근거:\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/lexical_index.py:92,133,162,291–387\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/korean_tokenizer.py:16,39,76–103,151–172,195–248\nhybrid-ai-lab/indexer/vector-bm25/app/bootstrap.py:47\nhybrid-ai-lab/retriever/vector-retriever/app/infrastructure/bm25_index.py:63–99\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:436–498\n기존 사전 산출물:\nhybrid-ai-lab/indexer/vector-bm25/data/generations/gen-20260930T135203Z-8582349c-9648f63d/search_indexes/generations/gen-20260930T135203Z-8582349c-9648f63d/card_names.dict:1\n공식 참고:\nhttps://github.com/xhluca/bm25s\nhttps://github.com/bab2min/kiwipiepy`);
}
async function main(){
 await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(final),{recursive:true});
 pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';pptx.author='design-agentic-ai';pptx.title='BM25 인덱싱의 원리와 설계';pptx.subject='Kiwi 사용자 사전과 BM25S 설계';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();const candidate=build+'/candidate.pptx';await pptx.writeFile({fileName:candidate});
 const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
 const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[],pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--require-native-table-slide','1'],fontPolicy:{basis:'user_request',families:[FONT]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
 const p=await PresentationFile.importPptx(await FileBlob.load(final));const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});await fs.writeFile(root+'/output/pptx/BM25-인덱싱-원리와-설계-1장.png',new Uint8Array(await png.arrayBuffer()));
 console.log(JSON.stringify({final,checks:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
}
main().catch(e=>{console.error(e);process.exit(1);});
