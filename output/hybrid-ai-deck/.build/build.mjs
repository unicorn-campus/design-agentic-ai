import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';

const ROOT='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/hiond/Documents/강의/신한카드/신한카드 하이브리드AI.pptx'));
const originals=[...p.slides.items];
const C={navy:'#17365D',blue:'#0070C0',teal:'#008E91',ink:'#243746',muted:'#576879',light:'#EAF3F9',grey:'#F3F5F7',line:'#CCD8E2',amber:'#986800',warn:'#FFF5DF',white:'#FFFFFF'};
const F='Pretendard';
let serial=0;
function shape(s,x,y,w,h,fill=C.white,border=C.line,geom='rect') {return s.shapes.add({geometry:geom,name:`native-${++serial}`,position:{left:x,top:y,width:w,height:h},fill,line:{fill:border,width:border==='none'?0:1.3}});}
function txt(s,t,x,y,w,h,size=28,color=C.ink,bold=false,align='left',fill='none') {const a=shape(s,x,y,w,h,fill,'none','textbox');a.text=t;a.text.style={fontSize:size,typeface:F,color,bold,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};return a;}
function box(s,t,x,y,w,h,{fill=C.light,color=C.navy,size=28,bold=true,geom='rect'}={}) {const a=shape(s,x,y,w,h,fill,C.line,geom);a.text=t;a.text.style={fontSize:size,typeface:F,color,bold,alignment:'center',verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:15,right:15,top:10,bottom:10}};return a;}
function arrow(s,a,b,from='right',to='left',color=C.blue){const edge=s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:color,width:2.2},tail:{type:'triangle',width:'sm',length:'sm'}});edge.bringToFront();return edge;}
function rule(s,x,y,w){shape(s,x,y,w,1.5,C.line,'none');}
function note(s,t,y=718,color=C.muted){txt(s,t,72,y,1392,64,24,color);}
function row(s,labels,y,{x=72,w=1392,h=125,gap=44,size=28}={}){const width=(w-gap*(labels.length-1))/labels.length;const nodes=labels.map((t,i)=>box(s,t,x+i*(width+gap),y,width,h,{size}));for(let i=1;i<nodes.length;i++)arrow(s,nodes[i-1],nodes[i]);return nodes;}
function table(s,values,widths,{x=72,y=230,h=400,size=25}={}){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:widths.reduce((a,b)=>a+b,0),height:h,columnWidths:widths,values});
 t.borders.assign({fill:C.line,width:1,style:'solid'});
 for(let r=0;r<values.length;r++){t.rows[r].height=h/values.length;for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?C.navy:r%2?C.white:C.grey;cell.text.style={fontSize:size,typeface:F,color:r===0?C.white:C.ink,bold:r===0,verticalAlignment:'middle',insets:{left:16,right:16,top:10,bottom:10}};}}
 return t;
}
const edited=[];const order=[];const map=[];
function keep(n){order.push(originals[n-1]);map.push({source:n,edited:false});}
const used=new Set();
function slide(n,title,sub,section,source,lecture=''){
 let s;if(used.has(n))s=originals[2].duplicate();else{s=originals[n-1];used.add(n);}
 s.shapes.deleteAll();for(const im of [...s.images.items])s.images.deleteById(im.id);
 s.background.fill=C.white;shape(s,0,0,1536,864,C.white,'none');
 txt(s,section,72,35,1392,36,21,C.teal,true);
 txt(s,title,72,83,1392,79,54,C.navy,true);
 txt(s,sub,72,170,1392,49,27,C.muted);
 rule(s,72,810,1392);
 txt(s,'하이브리드 AI  ·  RAG 실습',72,818,1150,30,18,C.muted);
 s.speakerNotes.textFrame.setText(`${lecture}\n\n소스 근거: hybrid-ai-lab/vector/${source}\n원본 ${n}페이지의 학습 내용`);
 order.push(s);map.push({source:n,edited:true,title,sourceRef:source});edited.push(s);return s;
}

keep(1);keep(2);keep(3);
{
 const s=slide(4,'Indexer 전체 흐름','원문을 검색 가능한 작은 근거로 바꾸어 저장하는 사전 준비 과정','INDEXER  /  전체 구조','indexer/app/application/graph.py:222-258');
 const a=row(s,['1  원문 선택\nselect_sources','2  내용 추출\nextract','3  프로필 적용\napply_profile','4  필수값 검증\nvalidate_metadata'],278,{h:128,size:25});
 const b=row(s,['5  의미 단위 분할\nchunk','6  벡터 생성\nembed','7  Chroma 저장\nupsert','8  검색 세대 발행\nfinalize_index'],485,{h:128,size:25});
 arrow(s,a[3],b[0],'bottom','top');
 txt(s,'원문 없음 또는 메타데이터 오류 시 종료',72,650,1030,42,23,C.amber);
 note(s,'dry-run은 청킹까지 실행  /  저장 완료 후 BM25와 활성 인덱스 정보 발행');
}
{
 const s=slide(5,'원문 3종을 같은 Document 구조로 정리','파일 형식은 달라도 본문과 메타데이터를 함께 전달','INDEXER  /  입력','indexer/app/application/graph.py');
 const inputs=[box(s,'D1  약관 PDF\n1개 파일',72,266,305,104),box(s,'D2  카드 혜택 PDF\n1개 파일',72,412,305,104),box(s,'D3  상담 TXT\n6개 파일',72,558,305,104)];
 const target=box(s,'Document',515,310,875,72,{fill:C.navy,color:C.white,size:31});
 for(const a of inputs)arrow(s,a,target);
 box(s,'page_content\n검색할 본문',515,402,875,94,{fill:C.light,size:28});
 box(s,'metadata\n문서 유형 · 출처 · 위치 · 공개 등급',515,516,875,112,{fill:C.grey,size:27});
 note(s,'PDF는 페이지별, 상담은 상담 1건별 Document 생성  /  중간 저장: documents.jsonl');
}
{
 const s=slide(5,'메타데이터는 근거를 되찾는 주소','본문만 저장하면 답변의 출처와 원문 위치를 설명하기 어려움','INDEXER  /  프로필과 검증','indexer/app/application/graph.py; indexer/app/domain/validation.py');
 row(s,['추출 결과\n본문 + 출처 정보','프로필 적용\nowner · access_level','필수값 검증\n누락 · 형식 검사'],255,{h:128});
 table(s,[['정보','예시 역할'],['문서 유형','약관·혜택·상담의 성격 구분'],['원문 위치','조 번호, 카드·혜택 위치, 상담·대화 범위'],['관리 정보','소유자와 공개 등급을 일관되게 적용']],[340,1052],{y:440,h:238,size:25});
 note(s,'검증 실패 시 청킹과 저장을 진행하지 않음');
}
{
 const s=slide(6,'PDF 텍스트 추출과 반복 요소 제거','글자와 좌표를 함께 읽어 페이지의 읽기 순서 복원','INDEXER  /  PDF 추출','indexer/app/infrastructure/pdf_reader.py:96-153,277-365');
 const page=shape(s,90,259,416,421,C.white,C.navy);
 box(s,'반복 머리말  ·  상단 5.5%',114,277,368,57,{fill:C.warn,color:C.amber,size:23});
 txt(s,'제12조  이용 조건\n\n① 본문 내용 추출\n② 문단과 좌표 수집\n③ 표 영역 확인',125,354,340,220,29);
 box(s,'반복 꼬리말  ·  하단 5%',114,606,368,57,{fill:C.warn,color:C.amber,size:23});
 const a=box(s,'PyMuPDF\n텍스트 + bbox 좌표',650,280,720,100);arrow(s,page,a);
 const b=box(s,'반복 문구·페이지 번호 제거',650,440,720,90);arrow(s,a,b,'bottom','top');
 const c=box(s,'페이지별 본문과 위치 정보 생성',650,590,720,90);arrow(s,b,c,'bottom','top');
 note(s,'텍스트 계층이 없는 스캔 PDF는 OCR 처리 없이 경고 기록  /  암호화 PDF는 처리 중단');
}
{
 const s=slide(6,'표는 행과 열의 관계를 보존','표 변환으로 원문 글자가 빠지지 않는지 확인 후 Markdown으로 저장','INDEXER  /  표 추출','indexer/app/infrastructure/pdf_reader.py:201-268,381-412');
 table(s,[['구분','연회비'],['국내전용','예시 금액 A'],['해외겸용','예시 금액 B']],[230,280],{x:72,y:288,h:252,size:28});
 txt(s,'설명용 가상 표',72,548,510,40,21,C.muted);
 const a=box(s,'원문과\n글자 일치?',671,322,300,164,{geom:'diamond',size:27});
 const target=box(s,'일치\nMarkdown 표 저장',1090,263,360,108,{fill:C.light,size:27});
 const fallback=box(s,'불일치\n원래 텍스트 + 경고',1090,456,360,108,{fill:C.warn,color:C.amber,size:27});
 const input=box(s,'표 영역',239,591,250,57,{size:24});arrow(s,input,a,'right','left');arrow(s,a,target);arrow(s,a,fallback);
 note(s,'D2의 테두리 없는 표는 좌표 기반 행을 추가 정규화하여 표로 구성');
}
{
 const s=slide(7,'상담 내용의 개인정보 처리','상담을 나누고 가명화한 뒤, 개인정보 잔존 여부를 한 번 더 검사','INDEXER  /  상담 추출','indexer/app/domain/consultations.py:52-190');
 row(s,['상담ID 기준 분리','삭제·일반화·가명화','잔존 검사','Document 생성'],260,{h:115,size:27});
 table(s,[['처리 방식','대상','결과'],['삭제','이름·전화·이메일·카드번호','검색 본문에서 제거'],['일반화','생년월일·나이','연령대로 변환'],['가명화','회원 ID·상담사 ID','해시 기반 가명 ID']],[250,560,582],{y:439,h:244,size:26});
 note(s,'개인정보 잔존 시 즉시 중단  /  상담의 공개 등급은 restricted');
}
{
 const s=slide(7,'청킹은 문서의 의미 단위에 맞춰 분할','청크는 검색 결과로 꺼내 쓰는 작은 근거 조각','INDEXER  /  청킹','indexer/app/domain/chunking.py:93-519; indexer/app/application/graph.py:455-540');
 table(s,[['문서','분할 기준','크기와 중첩'],['D1 약관','조·항 경계 보존\n페이지 간 이어진 조항 결합','600자 기준\n80자 중첩'],['D2 카드 혜택','카드·혜택·연회비·표 단위','600자 기준\n중첩 없음'],['D3 상담','고객·상담사 발화를\n대화 턴으로 묶음','청크당 4턴\n1턴 중첩']],[300,630,462],{y:256,h:388,size:28});
 note(s,'긴 속성표는 행을 자르지 않고 예외로 보존  /  600자 초과 청크는 별도 점검 대상',711);
}
{
 const s=slide(8,'변경된 청크만 임베딩하고 저장','임베딩은 텍스트의 의미를 숫자 벡터로 표현하는 과정','INDEXER  /  벡터 저장','indexer/app/application/graph.py:556-639; indexer/app/infrastructure/embedder.py:39-160');
 const a=box(s,'본문·메타데이터\n해시 비교',72,276,360,132);const b=box(s,'추가 또는 변경\nKURE-v2 임베딩',580,276,380,132);const c=box(s,'ChromaDB\ncard_docs에 upsert',1108,276,356,132);arrow(s,a,b);arrow(s,b,c);
 box(s,'둘 다 동일하면 생략',72,491,360,86,{fill:C.grey,size:26});
 txt(s,'현재 모델',590,486,370,40,23,C.muted);txt(s,'KURE-v2',590,532,440,66,44,C.navy,true);
 txt(s,'현재 벡터 차원',1118,486,346,40,23,C.muted);txt(s,'768',1118,532,346,66,48,C.blue,true);
 note(s,'모델 서명·청킹 설정 변경 시 전체 재임베딩  /  사라진 청크의 자동 삭제는 현재 미구현');
}
{
 const s=slide(8,'키워드 인덱스와 활성 검색 세대 발행','Vector는 의미를, BM25는 단어의 일치를 찾아주는 검색 경로','INDEXER  /  검색 준비 완료','indexer/app/application/graph.py:754-839; indexer/app/infrastructure/lexical_index.py');
 const preparation=row(s,['Chroma 건수·ID 확인','전체 corpus 구성','Kiwi 단어 분리','BM25S 인덱스 생성'],268,{h:112,size:26});
 const gen=box(s,'새 generation 폴더\ncorpus + BM25 + 카드명 사전',72,475,605,126);const active=box(s,'active_index.json\n새 검색 세대 가리키기',828,475,636,126,{fill:C.navy,color:C.white});arrow(s,gen,active);arrow(s,preparation[3],gen,'bottom','top');
 txt(s,'카드명 64개를 사용자 사전으로 생성',72,633,800,45,25,C.teal,true);
 note(s,'현재 저장 청크 485개  =  D1 53개 + D2 336개 + D3 96개  /  2026.09.20 확인');
}
{
 const s=slide(9,'Retriever 검색 흐름','원 질문 검색을 출발점으로, 필요할 때 질문을 바꾸고 후보를 다시 정렬','RETRIEVER  /  전체 구조 1','retriever/app/application/graph.py:455-563');
 const a=row(s,['1  요청·인덱스 확인','2  원 질문 Vector 검색','3  질문 변환 여부 판단'],267,{h:117,size:28});
 const b=row(s,['4  원 질문 결과 완성\n모드에 따라 BM25 추가','5  변환 질문별 검색\n변환 질문이 있을 때','6  결과 병합·재정렬\n검색 모드에 따라 처리'],491,{h:139,size:27});
 arrow(s,a[2],b[0],'bottom','top');
 note(s,'vector·hybrid 계열을 구분하고, rerank 옵션은 후보를 다시 읽어 순위를 조정');
}
{
 const s=slide(9,'검색 결과를 근거 있는 답변으로 연결','검색만 요청하면 결과를 반환하고, 답변 요청이면 생성·검증까지 진행','RETRIEVER  /  전체 구조 2','retriever/app/application/graph.py:181-214,319-330,669-709');
 row(s,['최종 검색 결과','답변 관문 0.62','근거 프롬프트 구성','답변 생성·인용 검증'],270,{h:131,size:26});
 txt(s,'/search',72,480,410,57,37,C.blue,true);txt(s,'순위와 근거 청크 반환',72,549,520,90,29);
 txt(s,'/answer 또는 /answer/stream',650,480,814,57,34,C.blue,true);txt(s,'관문 미달이면 needs_check\n검증 오류는 정해진 상한 안에서 수정',650,549,814,110,29);
 note(s,'최종 1위 문서의 vector_score로 답변 생성 여부 판단  /  융합·리랭크 점수는 사용하지 않음');
}
{
 const s=slide(10,'네 가지 검색 모드','기본 top_k=5일 때, 재정렬 모드는 후보를 더 넉넉하게 확보','RETRIEVER  /  검색 방식','retriever/app/application/graph.py:579-598,818-833,917-1023');
 table(s,[['모드','원시 후보 검색','중간 처리','최종 결과'],['vector','Vector 20개','상위 결과 선택','5개'],['vector_rerank','Vector 40개','10개를 재정렬','5개'],['hybrid','Vector 20개 + BM25 20개','정규화 후 점수 결합','5개'],['hybrid_rerank','Vector 40개 + BM25 40개','결합한 10개를 재정렬','5개']],[342,458,410,182],{y:268,h:374,size:25});
 note(s,'Vector: 의미 유사도  /  BM25: 키워드 일치  /  Rerank: 질문과 문서를 함께 읽어 재정렬');
}
{
 const s=slide(10,'질문 변환 관문 0.86','transform=auto일 때 최초 원 질문 Vector Top-1 점수로 검토 여부 결정','RETRIEVER  /  질문 변환','retriever/app/application/graph.py:838-911; retriever/app/settings.py:177');
 const a=box(s,'원 질문\nVector Top-1',72,287,300,126);const d=box(s,'점수 ≥ 0.86?',490,264,330,174,{geom:'diamond',size:30});arrow(s,a,d);
 const pass=box(s,'통과\n원 질문 유지',976,251,460,105,{fill:C.light});const low=box(s,'미달 또는 결과 없음\n캐시 또는 Router LLM 검토',976,439,460,126,{fill:C.warn,color:C.amber,size:26});arrow(s,d,pass);arrow(s,d,low);
 txt(s,'Router 판단',72,553,350,52,29,C.navy,true);
 txt(s,'keep  원 질문 유지     clarify  추가 확인 필요     transform  질문 변환',72,618,1392,64,28);
 note(s,'기본값은 transform=off  /  0.86 미만이어도 Router가 keep으로 판단할 수 있음');
}
{
 const s=slide(10,'질문 변환 기법','같은 의도를 검색하기 좋은 표현으로 바꾸거나, 복합 질문을 나누는 방법','RETRIEVER  /  질문 변환','retriever/app/domain/query_transform.py:10-176');
 table(s,[['기법','변환 방식','질문 수'],['rewrite','검색에 맞는 표현으로 다시 쓰기','1'],['multi','같은 의도를 다른 표현으로 확장','3'],['hyde','답변 문서에 있을 법한 표현 생성','1'],['stepback','상위 개념으로 넓혀 찾기','1'],['decomposition','복합 질문을 독립 질문으로 분리','2 ~ 4']],[315,900,177],{y:247,h:426,size:27});
 note(s,'변환 결과의 형식·개수 규칙 위반 시 keep으로 대체  /  HyDE 문장은 실제 근거로 사용하지 않음');
}
{
 const s=slide(11,'Hybrid 점수 결합','서로 다른 점수 범위를 0 ~ 1로 맞춘 뒤 가중합 계산','RETRIEVER  /  의미 + 키워드','retriever/app/domain/scoring.py:11-95');
 box(s,'Hybrid = 정규화 Vector × 0.6 + 정규화 BM25 × 0.4',72,245,1392,93,{fill:C.navy,color:C.white,size:33});
 table(s,[['후보','Vector 원점수','BM25 원점수','정규화 V','정규화 B','Hybrid'],['A','0.9','2','1.000','0.000','0.600'],['B','0.8','8','0.889','1.000','0.933'],['C','없음','5','0.000','0.500','0.200']],[180,260,260,230,230,232],{y:381,h:250,size:26});
 note(s,'계산 예시  /  정규화 = (점수 − 최솟값) ÷ (최댓값 − 최솟값)  /  없는 검색 점수는 0');
}
{
 const s=slide(11,'원 질문과 변환 질문의 후보 그룹','질문마다 같은 검색 모드를 적용하고, 청크 ID 기준으로 중복을 묶음','RETRIEVER  /  변환 후 추가 검색','retriever/app/application/graph.py:990-1070');
 const labels=['원 질문','변환 질문 1','변환 질문 2'];
 for(let i=0;i<3;i++){const y=270+i*138;const a=box(s,labels[i],72,y,278,86,{fill:i===0?C.navy:C.light,color:i===0?C.white:C.navy});const b=box(s,'같은 모드로 검색',472,y,410,86);const c=box(s,`후보 그룹 ${i+1}`,1004,y,460,86,{fill:C.grey});arrow(s,a,b);arrow(s,b,c);}
 note(s,'vector 계열은 Vector만 검색  /  hybrid 계열은 Vector와 BM25 결합  /  재정렬은 다음 단계');
}
{
 const s=slide(12,'RRF는 여러 순위표를 하나로 합치는 방법','질문마다 점수 척도가 달라도 순위를 이용해 비교 가능','RETRIEVER  /  순위 병합','retriever/app/domain/query_transform.py:182-294');
 box(s,'문서의 RRF 점수 = Σ [그룹 가중치 ÷ (60 + 그룹 내 순위)]',72,245,1392,94,{fill:C.navy,color:C.white,size:32});
 table(s,[['그룹','일반 변환 가중치','문서 A의 순위','기여도'],['원 질문','0.5','1위','0.5 ÷ 61'],['변환 질문 1개','0.5','1위','0.5 ÷ 61'],['합계','1.0','두 그룹 모두 상위','약 0.01639']],[350,380,330,332],{y:387,h:248,size:27});
 note(s,'분해 검색은 원 질문 0.1, 하위 질문 전체 0.9  /  재정렬이 없으면 하위 질문 Top-1 먼저 확보');
}
{
 const s=slide(12,'Rerank는 후보를 다시 읽어 순위를 조정','Cross-Encoder가 질문과 후보 문서를 함께 입력받아 관련성을 평가','RETRIEVER  /  재정렬','retriever/app/application/graph.py:1075-1164');
 row(s,['질문별 후보 10개','해당 질문으로\nCross-Encoder 평가','질문별 새 순위'],268,{h:131,size:29});
 table(s,[['변환 질문 유무','최종 결과 구성'],['변환 없음','재정렬 상위 5개 선택'],['일반 변환 있음','질문별 재정렬 순위를 가중 RRF로 병합'],['분해 질문 있음','하위 질문별 상위 후보를 전용 점수식으로 결합']],[420,972],{y:457,h:225,size:26});
 note(s,'변환 질문이 있으면 사전 RRF 없이 질문별 재정렬부터 수행  /  실패 시 이전 결과 또는 RRF 사용');
}
{
 const s=slide(12,'분해 질문의 재정렬 결과 결합','복합 질문의 각 부분을 잘 설명하는 근거를 함께 확보','RETRIEVER  /  DECOMPOSITION','retriever/app/domain/query_transform.py:297-427');
 const a=box(s,'하위 질문별 Top-3\n같은 문서는 최고 점수 채택',72,268,630,116);const b=box(s,'원 질문의\n재정렬 점수',834,268,630,116,{fill:C.grey});
 const sum=box(s,'최종 점수 = 하위 질문 최고점 × 0.9 + 원 질문 점수 × 0.1',72,481,1392,105,{fill:C.navy,color:C.white,size:31});arrow(s,a,sum,'bottom','top');arrow(s,b,sum,'bottom','top');
 txt(s,'계산 예시',72,629,240,52,28,C.teal,true);txt(s,'하위 최고 0.90, 원 질문 0.80인 문서의 최종 점수 = 0.89',326,629,1138,52,29);
 note(s,'이 점수식은 decomposition + rerank 전용  /  일반 변환은 재정렬 후에도 RRF 사용');
}
keep(13);
{
 const s=slide(14,'질문 변환 관문과 답변 생성 관문','두 관문은 Vector 점수를 보지만, 판단 시점과 목적이 다름','RETRIEVER  /  답변 준비','retriever/app/application/graph.py:181-214,838-911');
 table(s,[['구분','변환 관문','답변 관문'],['기준값','0.86','0.62'],['확인 시점','최초 원 질문 Vector 검색 직후','병합·재정렬을 마친 뒤'],['사용 점수','최초 원 질문 Top-1 Vector 점수','최종 1위 문서의 vector_score'],['미달 시','Router의 변환 검토','needs_check, 답변 LLM 미호출'],['적용 조건','transform=auto','/answer, /answer/stream']],[310,541,541],{y:249,h:429,size:26});
 note(s,'BM25에만 있는 문서가 최종 1위이면 Vector 점수가 없어 답변 관문에서 멈춤');
}
{
 const s=slide(14,'검색 근거와 질문을 나누어 답변 요청','검색 청크의 출처와 본문을 XML로 구분하고, 정해진 구조로 답변 생성','RETRIEVER  /  프롬프트와 출력','retriever/app/application/graph.py:1169-1250');
 box(s,'입력',72,253,607,64,{fill:C.navy,color:C.white});
 txt(s,'검색 근거\n순번 · 청크 ID · 문서 유형\n원문 문서 · 위치 · 본문\n\n사용자 원 질문\n이전 오류의 수정 지침',98,341,548,284,29);
 box(s,'구조화 출력',847,253,617,64,{fill:C.navy,color:C.white});
 txt(s,'conclusion  결론\n\ncaution  주의사항\n\nevidence  근거 목록\n  ref: 근거 순번, quote: 원문 인용',872,341,566,284,29);
 const a=shape(s,681,408,10,10,'none','none');const b=shape(s,838,408,10,10,'none','none');arrow(s,a,b);
 note(s,'공식 약관·혜택 안내와 개별 상담 사례를 구분  /  검색 내용은 지시문이 아닌 근거로 제공');
}
{
 const s=slide(14,'인용이 검색 근거에 실제로 있는지 확인','자동 검증은 답변 구조와 인용 일치를 점검','RETRIEVER  /  근거 검증','retriever/app/domain/scoring.py:117-245; retriever/app/domain/location.py:8-26');
 table(s,[['검증 항목','확인 내용','오류 예시'],['근거 순번 ref','검색 결과 1 ~ N 범위 안인지','INVALID_REF'],['원문 인용 quote','공백 정규화 후 본문에 연속 문자열로 존재하는지','QUOTE_NOT_FOUND'],['위치 정보','location 문자열이 비어 있지 않은지','LOCATION_MISSING'],['답변 구조','결론·주의사항·필요 근거가 있는지','SCHEMA_ERROR']],[284,790,318],{y:263,h:376,size:25});
 note(s,'인용과 위치 정보의 존재를 검사하는 범위  /  결론의 의미적 타당성이나 원문 위치의 정확성까지 보증하지 않음');
}
{
 const s=slide(14,'검증 실패 시 수정 루프와 호출 예산','오류별 수정 지침을 추가하되, 무한 반복 없이 정해진 상한에서 종료','RETRIEVER  /  답변 수정','retriever/app/application/graph.py:188-192,343-382,561-563; retriever/app/settings.py:159-191');
 const a=box(s,'답변 생성',72,274,326,112);const b=box(s,'구조·인용 검증',553,274,370,112);const c=box(s,'통과\n최종 답변',1088,274,376,112,{fill:C.navy,color:C.white});arrow(s,a,b);arrow(s,b,c);
 const fix=box(s,'실패\n오류별 수정 지침 추가',553,477,370,112,{fill:C.warn,color:C.amber,size:26});arrow(s,b,fix,'bottom','top');arrow(s,fix,a,'left','bottom');
 txt(s,'MAX_REPAIRS = 2\n초기 생성 뒤 최대 2회 수정',72,633,630,72,26);
 txt(s,'API 기본 LLM 예산 = 총 2회\n질문 변환 호출도 같은 예산 사용',834,633,630,72,26);
 note(s,'횟수 또는 예산 소진 시 halted_by_limit  /  CLI 기본 LLM 예산은 8회',740);
}
keep(15);keep(16);keep(17);
for(let i=0;i<order.length;i++)order[i].moveTo(i);
const lectureScript=await fs.readFile(`${ROOT}/강의스크립트.md`,'utf8');
const lectureSections=lectureScript.split(/## 슬라이드 \d+\./).slice(1);
for(let i=0;i<order.length;i++){
 const s=order[i];if(map[i].edited){txt(s,String(i+1).padStart(2,'0'),1330,816,134,34,20,C.muted,false,'right');const narration=lectureSections[i]?.match(/- 설명 대본: ([\s\S]*?)\n- 도식:/)?.[1]?.replace(/\n\s+/g,' ');if(narration)s.speakerNotes.textFrame.setText(narration+'\n\n소스 근거: hybrid-ai-lab/vector/'+map[i].sourceRef);}
 else for(const sh of s.shapes.items){const text=String(sh.text??'').trim();if(text===String(map[i].source)&&sh.position.top>740)sh.text=String(i+1);}
}
await fs.mkdir(`${ROOT}/.build/rendered`,{recursive:true});
await fs.writeFile(`${ROOT}/.build/page-map.json`,JSON.stringify(map,null,2));
await (await PresentationFile.exportPptx(p)).save(`${ROOT}/.build/candidate.pptx`);
console.log('exported',p.slides.items.length);
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.slides.items[i].export({format:'png',scale:1});
 await fs.writeFile(`${ROOT}/.build/rendered/slide-${String(i+1).padStart(2,'0')}.png`,new Uint8Array(await png.arrayBuffer()));
 console.log('rendered',i+1);
}
