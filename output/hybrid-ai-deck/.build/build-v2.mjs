import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const ROOT='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/hiond/Documents/강의/신한카드/신한카드 하이브리드AI.pptx'));
const original=[...p.slides.items];
const old=JSON.parse(await fs.readFile(ROOT+'/.build/original-shapes.json','utf8'));
const C={navy:'#17365D',blue:'#0070C0',teal:'#008E91',ink:'#243746',muted:'#576879',light:'#EAF3F9',grey:'#F3F5F7',line:'#CCD8E2',amber:'#986800',warn:'#FFF5DF',white:'#FFFFFF'};
const FONT='Pretendard';let id=0;const order=[],map=[],codeAudit=[];
const graph=(part)=>`${part}/app/application/graph.py`;
function originalCode(page,shapeId){const row=old.find(x=>x.slide===page&&x.id===String(shapeId));if(!row)throw Error('missing original code');codeAudit.push({page,shapeId});return row.text.replaceAll('\u00a0',' ').trim();}
function rect(s,x,y,w,h,fill=C.white,line='none',geo='rect'){return s.shapes.add({geometry:geo,name:`v2-${++id}`,position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:line==='none'?0:1.2}});}
function text(s,t,x,y,w,h,size=28,color=C.ink,bold=false,align='left',fill='none'){
 if(size<18.67)throw Error('Minimum 14pt');const a=rect(s,x,y,w,h,fill,'none','textbox');a.text=t;a.text.style={fontSize:size,typeface:FONT,color,bold,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};return a;
}
function box(s,t,x,y,w,h,fill=C.light,color=C.navy,size=27){const a=rect(s,x,y,w,h,fill,C.line);a.text=t;a.text.style={fontSize:size,typeface:FONT,color,bold:true,alignment:'center',verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:16,right:16,top:10,bottom:10}};return a;}
function arrow(s,a,b,from='right',to='left'){const e=s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:C.blue,width:2.2},tail:{type:'triangle',width:'sm',length:'sm'}});e.bringToFront();}
function table(s,values,widths,{x=72,y=255,h=380,size=26}={}){const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:widths.reduce((a,b)=>a+b),height:h,columnWidths:widths,values});t.borders.assign({fill:C.line,width:1});for(let r=0;r<values.length;r++){t.rows[r].height=h/values.length;for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?C.navy:r%2?C.white:C.grey;cell.text.style={fontSize:size,typeface:FONT,color:r===0?C.white:C.ink,bold:r===0,verticalAlignment:'middle',insets:{left:14,right:14,top:8,bottom:8}};}}return t;}
function note(s,t,y=729,color=C.muted){text(s,t,72,y,1392,62,23,color);}
function row(s,labels,y=260,h=105){const gap=54,w=(1392-gap*(labels.length-1))/labels.length;const a=labels.map((t,i)=>box(s,t,72+i*(w+gap),y,w,h));for(let i=1;i<a.length;i++)arrow(s,a[i-1],a[i]);return a;}
function keep(n,titleOverride){const s=original[n-1];if(titleOverride){const title=s.shapes.items.find(sh=>String(sh.text??'').includes('[참고]'));if(title)title.text=titleOverride;}order.push(s);map.push({original:n,kind:'preserved'});return s;}
function page(part,node,topic,summary,ref=''){
 const s=original[2].duplicate();s.shapes.deleteAll();for(const im of [...s.images.items])s.images.deleteById(im.id);s.background.fill=C.white;rect(s,0,0,1536,864);
 text(s,part==='indexer'?'INDEXER  /  노드 상세':'RETRIEVER  /  노드 상세',72,28,1392,36,21,C.teal,true);
 text(s,`${node}  :  ${topic}`,72,82,1392,84,node.length>20?43:48,C.navy,true);
 text(s,summary,72,176,1392,50,27,C.muted);
 rect(s,72,810,1392,1.5,C.line);text(s,'하이브리드 AI  ·  Workflow 노드 해설',72,819,1190,32,19,C.muted);
 s.speakerNotes.textFrame.setText(`노드: ${node}\n${summary}\n소스 근거: hybrid-ai-lab/vector/${ref||graph(part)}`);
 order.push(s);map.push({kind:'detail',part,node,topic,title:`${node}  :  ${topic}`,source:ref||graph(part)});return s;
}
function detail(part,node,topic,summary,input,actions,output,next,ref=''){
 const s=page(part,node,topic,summary,ref);
 const a=box(s,'입력',72,264,330,64,C.navy,C.white);const b=box(s,'핵심 처리',466,264,604,64,C.navy,C.white);const c=box(s,'출력',1134,264,330,64,C.navy,C.white);arrow(s,a,b);arrow(s,b,c);
 text(s,input,72,349,330,260,28);text(s,actions.map((x,i)=>`${i+1}  ${x}`).join('\n\n'),466,349,604,310,28);text(s,output,1134,349,330,260,27);
 note(s,next,719);return s;
}
function code(part,node,topic,summary,codeText,explain,ref,{originalPages=[],size=23}={}){
 const s=page(part,node,topic,summary,ref);rect(s,72,258,1392,432,C.grey,C.line);const t=text(s,codeText,96,275,1344,404,size,C.ink);t.text.style={fontSize:size,typeface:FONT,color:C.ink,alignment:'left',verticalAlignment:'top',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};note(s,explain,712);
 map.at(-1).code=true;map.at(-1).originalCodePages=originalPages;return s;
}
keep(1);keep(2);keep(3);keep(4);

detail('indexer','select_sources','원문 파일 선택','입력 경로에서 요청한 문서 종류와 상담 세그먼트에 해당하는 파일만 선택',
'input_path\n원문 경로\n\ndoc\nD1 / D2 / D3 / all\n\nsegment\n상담 세그먼트',
['파일이면 해당 파일, 폴더이면 파일 목록 확인','D1·D2 PDF와 D3 상담 파일 이름 검사','문서 종류·세그먼트 조건으로 필터링'],
'sources\n선택한 절대 경로 목록',
'다음: 선택 결과가 있으면 extract  /  없으면 오류 종료');
code('indexer','select_sources','선택 결과와 Document 배열','원본 자료의 배열 예시를 유지하고, 실제 State 이름과 연결',
originalCode(5,23)+'\n\n'+originalCode(5,26),
'원본 selected 예시는 현재 State의 sources에 해당  /  {…}는 설명용 자리표시자',graph('indexer'),{originalPages:[5],size:26});

detail('indexer','extract','파일을 Document로 변환','파일 형식에 맞는 추출기를 호출하고 본문·메타데이터·추적 정보를 수집',
'sources\n선택한 원문 파일\n\nD1·D2 PDF\nD3 상담 TXT',
['원문 파일별 SHA-256 해시 계산','PDF는 페이지별, 상담은 상담 1건별 추출','본문과 메타데이터를 Document로 묶음'],
'documents\n본문 + metadata\n\nreports\n처리 결과·경고\n\nfingerprints\n원문 해시',
'다음: apply_profile  /  문서 유형 doc_type은 metadata 안의 값');
code('indexer','extract','PDF 좌표와 글자 구조','PyMuPDF의 block·line·span을 따라 글자와 위치를 함께 읽음',
originalCode(6,16),
'bbox는 글자 영역의 좌표  /  spans의 글자를 합치면 같은 줄의 텍스트가 됨', 'indexer/app/infrastructure/pdf_reader.py',{originalPages:[6],size:23});
code('indexer','extract','PDF 한 줄씩 추출','원본 코드의 반복문이 좌표와 문장을 한 쌍으로 수집',
originalCode(6,27)+'\n\n# 결과 예시\n'+originalCode(6,18),
'get_text("dict")로 구조를 읽고, 빈 줄을 제외한 (bbox, text) 목록 반환','indexer/app/infrastructure/pdf_reader.py',{originalPages:[6],size:24});
code('indexer','extract','반복 머리말·꼬리말 찾기','페이지의 위·아래 영역에서 반복되는 문구를 모아 본문에서 제거',
originalCode(6,31),
'원본 코드 유지: if 줄 끝의 콜론 생략에 유의  /  상단 5.5%, 하단 5%를 검사','indexer/app/infrastructure/pdf_reader.py',{originalPages:[6],size:24});
{
 const s=page('indexer','extract','PDF 표와 읽기 순서','표는 행·열 관계를 보존하고, 같은 글자가 본문에 중복되지 않도록 처리','indexer/app/infrastructure/pdf_reader.py');
 row(s,['좌표와 텍스트 수집','표 감지·글자 비교','본문과 표 순서 복원'],258,103);
 table(s,[['판정','표 처리','본문 처리'],['표 셀과 원문 글자 일치','Markdown 표로 변환','해당 표 영역의 중복 글자 제거'],['글자 불일치','표 변환 보류·경고','기존 위치 기반 텍스트 유지'],['D2 테두리 없는 표','좌표 기반 행 추가 정규화','읽기 순서에 맞게 합침']],[350,480,562],{y:416,h:268,size:26});
 note(s,'스캔 PDF의 OCR은 미구현  /  텍스트 계층이 없으면 경고  /  암호화 PDF는 처리 중단');
}
{
 const s=page('indexer','extract','상담 분리와 가명화','상담ID 머리글로 상담을 나눈 뒤 개인정보가 남지 않도록 처리','indexer/app/domain/consultations.py');
 row(s,['상담ID 기준 분리','개인정보 처리','잔존 검사','Document 생성'],258,100);
 table(s,[['방법','대상','저장 결과'],['삭제','이름·전화·이메일·카드번호·끝 4자리','[삭제]'],['일반화','생년월일·나이','연령대'],['가명화','회원 ID·상담사 ID','해시 기반 가명 ID']],[250,710,432],{y:414,h:260,size:26});
 note(s,'원본 식별정보 잔존 시 중단  /  상담의 공개 등급은 restricted');
}
code('indexer','extract','상담 개인정보 처리 코드','원본 자료의 정규식 치환과 가명화 코드 보존',originalCode(7,9),
'sub는 패턴에 맞는 내용을 치환하는 함수  /  가명화 후 별도 잔존 검사 수행','indexer/app/domain/consultations.py',{originalPages:[7],size:21});

detail('indexer','apply_profile','문서별 관리 정보 적용','source 파일명에 대응하는 프로필을 찾아 메타데이터에 반영',
'documents\n추출된 문서\n\nprofiles\n파일별 관리 규칙',
['문서 metadata에서 source 파일명 확인','해당 파일의 프로필 선택','owner·access_level 등의 값을 적용'],
'documents\n프로필이 반영된\n문서 목록',
'다음: validate_metadata  /  파일별 고정 관리 정보로 메타데이터를 일관되게 유지');
code('indexer','apply_profile','프로필 선택과 적용 코드','현재 소스에서 추가한 핵심 코드',
'profiles = state.get("profiles", {})\ndocuments = [\n    apply_profile(\n        document,\n        profiles.get(document.metadata.get("source", ""), {}),\n    )\n    for document in state["documents"]\n]\nreturn {"documents": documents}',
'같은 source에서 나온 모든 Document에 같은 프로필 적용',graph('indexer'),{size:25});

{
 const s=page('indexer','validate_metadata','필수값 검증과 결과 저장','저장 위치·메타데이터·상담 가명화 상태를 검사하고 중간 결과를 기록');
 row(s,['입력 문서 + schema','필수값·허용값 검사','validation 결과'],258,100);
 table(s,[['파일','저장 내용'],['documents.jsonl','추출·가명화·프로필 적용을 마친 문서'],['manifest.json','원문 파일 해시와 문서 수'],['report.json','PDF·상담 추출 결과와 경고'],['validation.json','검증 건수와 문서별 오류']],[410,982],{y:409,h:280,size:25});
 note(s,'통과 시 chunk, 실패 시 종료  /  출력 폴더는 원문 폴더와 분리  /  현재 파일명은 documents.jsonl');
}
{
 const s=page('indexer','chunk','문서 유형별 의미 단위 분할','Document를 검색 결과로 사용할 작은 근거 조각으로 변환','indexer/app/domain/chunking.py');
 table(s,[['입력','분할 기준','기본 크기'],['D1 약관','조·항 경계 보존, 이어진 조항 결합','600자 기준 / 80자 중첩'],['D2 카드 혜택','카드·혜택·연회비·표 단위','600자 기준 / 중첩 없음'],['D3 상담','고객·상담사의 대화 턴 단위','4턴 / 1턴 중첩']],[300,620,472],{y:267,h:332,size:28});
 text(s,'출력: chunks와 청킹 보고서',72,633,1392,62,31,C.blue,true);
 note(s,'다음: embed  /  dry-run·청킹 오류 시 종료  /  긴 속성표는 행을 자르지 않고 예외로 보존');
}

detail('indexer','embed','변경 청크의 벡터 생성','본문과 메타데이터의 해시를 이전 실행과 비교해 임베딩 대상을 결정',
'chunks\n현재 청크\n\nindex_manifest\n이전 해시·설정',
['해시가 같은 청크는 생략','추가·변경 청크를 배치로 임베딩','모델·청킹 설정 변경 시 전체 재임베딩'],
'pending_ids\n처리한 청크 ID\n\nvectors_path\n벡터 파일 경로\n\nfailed\n실패 목록',
'다음: upsert  /  현재 기본 모델 KURE-v2, 실제 저장 벡터 768차원');
code('indexer','embed','모델 적재와 배치 인코딩','원본 자료의 SentenceTransformer·encode 핵심 코드 보존',
'self._model = SentenceTransformer(self.model_name, device=self.device)\n\n'+originalCode(8,9),
'normalize_embeddings=True로 벡터 정규화  /  kind 인자는 현재 구현에서 query·passage를 구분하지 않음', 'indexer/app/infrastructure/embedder.py',{originalPages:[8],size:23});

detail('indexer','upsert','ChromaDB 저장·갱신','임베딩에 성공한 청크의 ID·본문·벡터·메타데이터를 함께 저장',
'pending_ids\n저장 대상 ID\n\nvectors_path\n임베딩 벡터\n\nchunks\n본문·metadata',
['ID에 맞는 본문과 벡터를 연결','메타데이터를 Chroma 허용 형식으로 정리','같은 ID는 갱신, 새 ID는 추가'],
'ok_ids\n저장 성공 ID\n\nfailed\n실패 목록\n\ncount_before\n저장 전 건수',
'다음: finalize_index  /  원문에서 사라진 청크의 자동 삭제는 현재 미구현');
code('indexer','upsert','Chroma 컬렉션 구성','원본 자료의 저장소 초기화 코드 보존',
originalCode(8,13).slice(originalCode(8,13).indexOf('self._store')),
'persist_directory는 저장 경로  /  cosine은 벡터 유사도 비교 방식  /  signature는 모델 일치 검사에 사용','indexer/app/infrastructure/chroma_store.py',{originalPages:[8],size:24});
code('indexer','upsert','청크 저장 코드','원본 자료의 메타데이터 정리와 upsert 호출 보존',originalCode(8,17),
'IDs·documents·embeddings·metadatas 배열은 같은 순서로 대응해야 함','indexer/app/infrastructure/chroma_store.py',{originalPages:[8],size:24});

{
 const s=page('indexer','finalize_index','검증과 검색 세대 발행','벡터 저장 결과를 확인한 뒤 키워드 검색 인덱스를 완성');
 const a=row(s,['벡터 건수·ID 검증','전체 corpus 구성','Kiwi 단어 분리','BM25S 재생성'],258,106);
 const b=box(s,'새 generation 폴더\ncorpus + BM25 + 카드명 사전',72,467,610,117);const c=box(s,'active_index.json 전환\n완성된 검색 세대 활성화',848,467,616,117,C.navy,C.white);arrow(s,a[3],b,'bottom','top');arrow(s,b,c);
 text(s,'카드명 64개 사전 등록  /  OOV 후보는 검토 파일로만 저장',72,631,1392,57,28,C.teal,true);
 note(s,'다음: END  /  현재 485청크: D1 53 + D2 336 + D3 96  /  2026.09.20 확인');
}

keep(9);
{
 const s=page('retriever','check_search_readiness','검색 준비 확인','원본 workflow 이미지의 check_query에 대응하는 실제 노드');
 table(s,[['입력·대상','검사 내용'],['query·top_k','질문이 비어 있지 않은지, top_k가 양수인지'],['role·mode','agent / auditor, 네 검색 모드 중 하나인지'],['저장 인덱스','컬렉션이 비어 있지 않은지'],['임베딩 서명','검색 모델과 저장 모델의 서명이 같은지']],[370,1022],{y:270,h:328,size:27});
 text(s,'출력: index_info 또는 validation_errors',72,627,1392,54,29,C.blue,true);
 note(s,'다음: vector_search  /  오류 시 종료  /  원본 이미지의 관문 0.70은 과거 값이며 현재는 0.86');
}
detail('retriever','vector_search','원 질문 벡터 검색','원 질문의 의미와 가까운 문서를 찾고, 질문 변환 판정용 점수를 기록',
'query\n원 질문\n\nrole·mode\n접근 역할·검색 모드\n\ntop_k\n최종 결과 수',
['질문을 임베딩하고 권한 필터 구성','similarity 또는 MMR 전략으로 검색','vector_hits와 변환 관문 점수 보존'],
'vector_hits\n원 질문 후보\n\ntransform_gate_\nvector_score\n첫 후보 Vector 점수',
'다음: assess_transform_gate  /  MMR은 관련성과 후보 다양성을 함께 고려');
code('retriever','vector_search','Chroma 검색 코드','원본 자료의 query 호출 보존',
originalCode(10,12),
'query_embeddings는 질문 벡터  /  where는 권한 필터  /  include는 결과에 포함할 정보','retriever/app/infrastructure/chroma_store.py',{originalPages:[10],size:27});
{
 const s=page('retriever','vector_search','네 검색 모드의 후보 수','기본 top_k=5일 때, 리랭크 모드는 재평가 후보를 넉넉하게 확보');
 table(s,[['모드','원시 후보','중간 후보','최종'],['vector','Vector 20개','상위 5개','5개'],['vector_rerank','Vector 40개','재정렬 대상 10개','5개'],['hybrid','Vector 20 + BM25 20','점수 결합 상위 5개','5개'],['hybrid_rerank','Vector 40 + BM25 40','결합·재정렬 대상 10개','5개']],[345,437,430,180],{y:274,h:370,size:26});
 note(s,'raw_k = fused_k × 4  /  fused_k는 일반 모드 top_k, 리랭크 모드 top_k × 2');
}

code('retriever','assess_transform_gate','질문 변환 검토 관문','transform=auto일 때 최초 원 질문 Vector Top-1과 0.86을 비교',
originalCode(10,16),
'기본 transform=off는 검토 생략  /  gate_threshold=0.86  /  미달이면 plan_query_transform', 'retriever/app/domain/query_transform.py',{originalPages:[10],size:26});
{
 const s=page('retriever','plan_query_transform','변환 계획 수립','관문 미달 시 캐시 또는 Router LLM으로 변환 필요성과 기법 결정');
 row(s,['질문 + 후보 정보','캐시 확인 / Router LLM','keep·clarify·transform'],258,105);
 table(s,[['행동','결과','이후 처리'],['keep','원 질문 유지','원 질문 결과 완성'],['clarify','추가 확인 필요','답변 경로에서 needs_check'],['transform','변환 질문 목록 생성','원 질문 결과 완성 후 추가 검색']],[240,480,672],{y:427,h:258,size:27});
 note(s,'출력: route_action·technique·transformed_queries  /  형식 오류 시 keep으로 대체');
}
{
 const s=page('retriever','plan_query_transform','다섯 가지 변환 기법','질문의 어려운 부분에 맞춰 검색 표현을 바꾸거나 복합 질문을 분리','retriever/app/domain/query_transform.py');
 table(s,[['기법','변환 방식','질문 수'],['rewrite','검색에 맞는 한 문장으로 다시 쓰기','1'],['multi','같은 의도를 다른 표현으로 확장','3'],['hyde','답변 문서에 있을 법한 표현 생성','1'],['stepback','상위 개념으로 넓혀 찾기','1'],['decomposition','복합 질문을 독립 질문으로 분리','2 ~ 4']],[330,870,192],{y:258,h:420,size:27});
 note(s,'캐시 적중 시 LLM 호출 생략  /  HyDE가 만든 문장은 검색용이며 원문 근거로 사용하지 않음');
}

detail('retriever','bm25_search','원 질문 키워드 검색','hybrid 계열에서 원 질문의 단어와 맞는 청크를 검색',
'query\n원 질문\n\nrole\n접근 역할\n\n활성 BM25 인덱스',
['카드명 사전을 적용한 Kiwi 토큰 분리','역색인에서 단어가 맞는 후보 점수화','접근 가능한 문서로 결과 제한'],
'청크 ID별\n키워드 점수\n\nwarnings\n검색 경고',
'다음: fuse_scores  /  vector 계열은 이 노드를 건너뜀');
code('retriever','bm25_search','BM25S 호출 코드','원본 자료의 retrieve·weight_mask 코드 보존',originalCode(11,31),
'권한 마스크로 허용되지 않은 문서의 점수를 0으로 처리하고, 반환 후보도 권한 기준으로 제한','retriever/app/infrastructure/bm25_index.py',{originalPages:[11],size:26});

code('retriever','fuse_scores','Vector·BM25 점수 결합','청크 ID 합집합을 만든 뒤 점수를 각각 0 ~ 1로 맞추어 가중합',
originalCode(11,34),
'Vector 가중치 0.6, BM25 가중치 0.4  /  다음: complete_original_results','retriever/app/domain/scoring.py',{originalPages:[11],size:24});
{
 const s=page('retriever','fuse_scores','정규화 계산 예시','한쪽 검색에 없는 후보는 해당 원점수를 0으로 포함해 정규화','retriever/app/domain/scoring.py');
 box(s,'Hybrid = Vector 정규화 점수 × 0.6 + BM25 정규화 점수 × 0.4',72,255,1392,85,C.navy,C.white,30);
 table(s,[['청크','Vector','BM25','정규화 V','정규화 B','최종 점수'],['A','0.9','2','1.000','0.000','0.600'],['B','0.8','8','0.889','1.000','0.933'],['C','없음','5','0.000','0.500','0.200']],[172,235,235,245,245,260],{y:405,h:259,size:27});
 note(s,'정규화 = (점수 − 최솟값) ÷ (최댓값 − 최솟값)  /  모든 값이 같으면 해당 신호를 0으로 처리');
}

detail('retriever','complete_original_results','원 질문 후보 확정','변환 질문 검색 전에 원 질문의 기준 결과를 따로 보존',
'vector_hits\n또는 융합 후보\n\nmode·top_k',
['vector 계열이면 Vector 후보 재사용','hybrid 계열이면 융합 후보 재사용','baseline_hits와 현재 hits 분리 보관'],
'baseline_hits\n원 질문 후보\n\nhits\n현재 상위 결과',
'분기: 변환 질문 있음 → search_transformed  /  변환 없음·리랭크 모드 → rerank  /  그 외 검색 완료');
code('retriever','complete_original_results','기준 후보 보존 코드','현재 구현은 리랭크 입력 후보 수와 최종 출력 수를 구분',
'if _uses_vector_only(state.get("mode")):\n    baseline = list(state.get("vector_hits", []))[: self._candidate_sizes(state).fused_k]\nelse:\n    baseline = list(state.get("baseline_hits", state.get("candidates", [])))\nreturn {\n    "baseline_hits": baseline,\n    "hits": list(baseline[: int(state.get("top_k", len(baseline)))]),\n}',
'top_k=5인 리랭크 모드: baseline_hits에 10개, hits에 5개를 보관',graph('retriever'),{size:24});

detail('retriever','search_transformed','변환 질문별 추가 검색','원 질문의 후보를 유지한 채 변환 질문마다 독립된 후보 그룹 생성',
'transformed_queries\n변환 질문 목록\n\nmode·role·top_k',
['변환 질문을 하나씩 같은 모드로 검색','질문별 결과를 같은 순서로 저장','실패 그룹은 빈 목록과 경고로 남김'],
'transformed_\nhit_groups\n질문별 후보 묶음\n\nwarnings',
'다음: vector·hybrid는 merge_queries  /  리랭크 모드는 사전 RRF 없이 rerank');
code('retriever','search_transformed','원본 자료의 검색 코드','원본 핵심 코드 보존용이며, 아래 주의사항과 다음 페이지의 현재 구현을 함께 확인',
originalCode(11,50).replace(/\n\s*\n/g,'\n'),
'원본과 현재의 차이: vector_rerank도 Vector만 검색하며, top_k 대신 fused_k까지 후보 유지',graph('retriever'),{originalPages:[11],size:22});
code('retriever','search_transformed','현재 구현의 검색 분기','현재 소스의 _search_one 핵심 코드',
'sizes = self._candidate_sizes(state)\nvector_hits = self._search_vector(query, state["role"], sizes.raw_k)\nif _uses_vector_only(state["mode"]):\n    return vector_hits[: sizes.fused_k]\nreturn self._fuse(\n    vector_hits,\n    self.bm25.keyword_search(\n        query,\n        allowed_access_levels=allowed_levels(state["role"]),\n        k=sizes.raw_k,\n    ),\n    state["role"],\n    sizes.fused_k,\n)',
'_uses_vector_only는 vector와 vector_rerank를 모두 포함',graph('retriever'),{size:22});

code('retriever','merge_queries','가중 RRF 순위 병합','질문별 후보 목록을 chunk_id로 묶고 그룹 가중치와 순위를 누적',
originalCode(12,31),
'기본 rrf_k=60  /  일반 변환: 원 질문 0.5, 변환 질문 전체 0.5  /  다음: 검색 완료','retriever/app/domain/query_transform.py',{originalPages:[12],size:23});
{
 const s=page('retriever','merge_queries','분해 질문의 근거 확보','리랭크 없는 decomposition은 하위 질문의 대표 근거를 먼저 확보','retriever/app/domain/query_transform.py');
 row(s,['원 질문 + 하위 질문 그룹','가중 RRF 계산','하위 Top-1 우선 확보','나머지 순위 채우기'],274,124);
 table(s,[['변환 기법','원 질문 가중치','변환 질문 전체','결합 방식'],['일반 변환','0.5','0.5','RRF 순위'],['decomposition','0.1','0.9','각 하위 Top-1 확보 후 RRF']],[350,260,270,512],{y:470,h:201,size:26});
 note(s,'변환 결과가 비어 있으면 원 질문 결과 사용  /  최종 결과가 정해지면 답변 관문 판정');
}

detail('retriever','rerank','질문별 후보 재평가','Cross-Encoder가 질문과 후보 본문을 함께 읽어 관련성을 다시 평가',
'baseline_hits\n원 질문 후보\n\ntransformed_\nhit_groups\n변환 질문별 후보',
['각 후보 그룹을 해당 질문으로 평가','그룹 내부 순위를 새로 정렬','변환 기법별 결합 규칙으로 최종 선택'],
'hits\n최종 상위 결과\n\nrerank 점수\n경고·실패 정보',
'일반 변환: 재정렬 후 RRF  /  decomposition: 하위 최고점 중심 결합  /  실패 시 원 결과 또는 RRF');
code('retriever','rerank','Cross-Encoder 호출 코드','원본 자료의 모델 적재와 predict 핵심 코드 보존',
'self._model = CrossEncoder(self.model_name, max_length=self.max_length)\n\nraw = model.predict(\n    [(query, text) for text in texts],\n    activation_fn=torch.nn.Sigmoid(),\n    show_progress_bar=False,\n)',
'질문과 각 후보 본문을 한 쌍으로 평가  /  일반 변환은 서로 다른 그룹의 원점수를 직접 합산하지 않음','retriever/app/infrastructure/reranker.py',{originalPages:[12],size:26});
{
 const s=page('retriever','rerank','decomposition 점수 결합','각 하위 질문의 상위 3개 후보를 확보하고 중복 청크는 최고 점수 채택','retriever/app/domain/query_transform.py');
 const a=box(s,'하위 질문별 Top-3\n중복 청크의 최고 점수',72,270,623,118);const b=box(s,'원 질문으로 평가한\n같은 청크의 점수',841,270,623,118);
 const c=box(s,'최종 = 하위 질문 최고점 × 0.9 + 원 질문 점수 × 0.1',72,487,1392,99,C.navy,C.white,32);arrow(s,a,c,'bottom','top');arrow(s,b,c,'bottom','top');
 text(s,'예시: 하위 최고 0.90, 원 질문 0.80인 청크의 최종 점수는 0.89',72,634,1392,58,30);
 note(s,'하위 질문별 가중치를 나누어 더하지 않고 최고점에 0.9 적용  /  일반 변환은 RRF 사용');
}
keep(13,'rerank : 처리 예시');

{
 const s=page('retriever','build_prompt','답변 관문과 근거 입력','검색 결과가 확정되면 답변 가능 여부를 확인한 뒤 프롬프트 구성');
 row(s,['최종 검색 결과','최종 1위 vector_score ≥ 0.62','근거 XML 구성'],268,119);
 table(s,[['입력','프롬프트 구성'],['hits','순번·청크 ID·문서 유형·출처·위치·본문'],['query','사용자 원 질문을 별도 태그로 구분'],['repair_hints','이전 검증 오류의 수정 지침 포함']],[325,1067],{y:445,h:234,size:27});
 note(s,'0.62 판정은 앞선 검색 완료 처리에서 수행  /  미달이면 needs_check  /  다음: generate_answer');
}
code('retriever','build_prompt','XML 근거 구성 코드','원본 자료의 검색결과·질문·수정 지침 구성 코드 보존',
originalCode(14,10),
'원본 코드의 따옴표·태그 공백은 강의 표기  /  실제 소스는 escape로 본문을 XML 안전 문자열로 변환',graph('retriever'),{originalPages:[14],size:21});
{
 const s=page('retriever','generate_answer','구조화 답변 생성','system·user 프롬프트로 LLM을 호출하고 정해진 답변 필드만 수신');
 box(s,'입력: prompt  +  남은 LLM 호출 예산',72,258,1392,73);
 const codeText='runnable = model.with_structured_output(schema, **kwargs)\n\noutput = runnable.invoke([("system", system), ("human", user)])';
 rect(s,72,369,1392,145,C.grey,C.line);text(s,codeText,97,389,1342,105,27);
 table(s,[['출력 필드','의미'],['conclusion / caution','결론 / 주의사항'],['evidence[{ref, quote}]','근거 순번과 원문 인용']],[600,792],{y:562,h:155,size:26});
 note(s,'원본 14페이지의 핵심 호출 코드 보존  /  다음: verify_evidence  /  예산 소진 시 중단',741);
 map.at(-1).code=true;map.at(-1).originalCodePages=[14];
}

{
 const s=page('retriever','verify_evidence','답변 구조와 인용 검증','그럴듯함을 판단하는 대신, 답변이 가리키는 인용이 검색 청크에 있는지 확인','retriever/app/domain/scoring.py');
 table(s,[['검증','확인 내용','오류 코드'],['ref','검색 결과 1 ~ N 범위인지','INVALID_REF'],['quote','공백·바깥 따옴표 정규화 후 원문에 포함되는지','QUOTE_NOT_FOUND'],['location','위치 문자열이 비어 있지 않은지','LOCATION_MISSING'],['답변 구조','결론·주의사항·필요한 근거가 있는지','SCHEMA_ERROR']],[250,805,337],{y:260,h:381,size:25});
 note(s,'출력: Answer + Verification  /  통과 시 END, 실패 시 build_prompt로 수정 요청  /  의미의 정확성은 별도 검토');
}
code('retriever','verify_evidence','근거 대조 핵심 코드','현재 소스에서 추가한 근거 검증 코드',
'hit = hits[ref - 1]\nquote_ok = isinstance(quote, str) and verify_quote(quote, hit.text)\nlocation_ok = bool(hit.location)\n\n# 오류 목록이 모두 비었을 때만 자동 검증 통과\nautomatic_valid = not (\n    schema_errors or invalid_refs or quote_failures or location_failures\n)',
'location_ok는 위치 정보의 존재 검사  /  원문 파일을 다시 열어 위치의 정확성까지 대조하지 않음','retriever/app/domain/scoring.py',{size:25});
{
 const s=page('retriever','verify_evidence','실패 수정과 종료 조건','오류별 수정 지침을 build_prompt에 전달하고 정해진 상한 안에서 재생성');
 const a=box(s,'generate_answer\n답변 생성',72,272,349,116);const b=box(s,'verify_evidence\n인용·구조 검사',581,272,375,116);const c=box(s,'검증 통과\nEND',1116,272,348,116,C.navy,C.white);arrow(s,a,b);arrow(s,b,c);
 const d=box(s,'검증 실패\nbuild_prompt + repair_hints',487,498,563,116,C.warn,C.amber);arrow(s,b,d,'bottom','top');arrow(s,d,a,'left','bottom');
 text(s,'MAX_REPAIRS=2  /  API 기본 LLM 예산 총 2회  /  CLI 기본 총 8회',72,665,1392,56,29);
 note(s,'질문 변환 호출도 같은 예산 사용  /  횟수·예산 소진 시 halted_by_limit');
}

keep(15);keep(16);keep(17);
// The original source slides not retained are replaced by the node details above.
for(const n of [5,6,7,8,10,11,12,14])original[n-1].delete();
for(let i=0;i<order.length;i++)order[i].moveTo(i);
const narrationFile=ROOT+'/노드별_강의스크립트_v2.md';
let narration='';try{narration=await fs.readFile(narrationFile,'utf8');}catch{}
for(let i=0;i<order.length;i++){
 const s=order[i];if(map[i].kind==='detail'){
  text(s,String(i+1).padStart(2,'0'),1350,818,114,32,20,C.muted,false,'right');
  const m=map[i];const content=s.shapes.items.map(x=>String(x.text??'')).filter(Boolean).join('\n');
  s.speakerNotes.textFrame.setText(`노드: ${m.node}\n${m.topic}\n\n${content}\n\n소스: hybrid-ai-lab/vector/${m.source}\n${m.originalCodePages?'원본 핵심 코드 출처: '+m.originalCodePages.join(', ')+'페이지':''}`);
 }else for(const sh of s.shapes.items)if(String(sh.text??'').trim()===String(map[i].original)&&sh.position.top>740)sh.text=String(i+1);
}
const expectedNodes={indexer:['select_sources','extract','apply_profile','validate_metadata','chunk','embed','upsert','finalize_index'],retriever:['check_search_readiness','vector_search','assess_transform_gate','plan_query_transform','bm25_search','fuse_scores','complete_original_results','search_transformed','merge_queries','rerank','build_prompt','generate_answer','verify_evidence']};
for(const [part,nodes] of Object.entries(expectedNodes))for(const node of nodes)if(!map.some(x=>x.part===part&&x.node===node))throw Error('missing node '+node);
await fs.mkdir(ROOT+'/.build/v2-rendered',{recursive:true});
await fs.writeFile(ROOT+'/.build/v2-page-map.json',JSON.stringify(map,null,2));
await fs.writeFile(ROOT+'/.build/v2-code-audit.json',JSON.stringify(codeAudit,null,2));
await (await PresentationFile.exportPptx(p)).save(ROOT+'/.build/candidate-v2.pptx');
console.log('exported',p.slides.items.length);
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.slides.items[i].export({format:'png',scale:1});await fs.writeFile(`${ROOT}/.build/v2-rendered/slide-${String(i+1).padStart(2,'0')}.png`,new Uint8Array(await png.arrayBuffer()));console.log('rendered',i+1);
}
