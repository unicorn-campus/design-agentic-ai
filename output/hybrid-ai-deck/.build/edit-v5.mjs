import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {FileBlob,PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const srcRoot='C:/Users/hiond/class/design-agentic-ai/hybrid-ai-lab/vector/';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/final/신한카드 하이브리드AI_v4_47페이지수정.pptx'));
const order=[...p.slides.items];
const map=JSON.parse(await fs.readFile(root+'/.build/v2-page-map.json','utf8'));
const refs=Object.fromEntries(map.map((m,i)=>[i+1,m.source]));
const comments={};const excerpts=[];let uid=0;
const C={navy:'#17365D',blue:'#0070C0',teal:'#008E91',ink:'#243746',muted:'#576879',grey:'#F3F5F7',line:'#CCD8E2',white:'#FFFFFF',light:'#EAF3F9',warn:'#FFF5DF'};
function rect(s,x,y,w,h,fill='none',line='none',geometry='rect') {return s.shapes.add({name:'v5-'+(++uid),geometry,position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:line==='none'?0:1.2}});}
function style(sh,size=25,color=C.ink,bold=false,alignment='left',top=false){sh.text.style={fontSize:size,typeface:'Pretendard',color,bold,alignment,verticalAlignment:top?'top':'middle',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};}
function text(s,t,x,y,w,h,size=25,color=C.ink,bold=false,align='left'){let sh=rect(s,x,y,w,h,'none','none','textbox');sh.text=t;style(sh,size,color,bold,align);return sh;}
function box(s,t,x,y,w,h,size=27,fill=C.light,color=C.navy){let sh=rect(s,x,y,w,h,fill,C.line);sh.text=t;sh.text.style={fontSize:size,typeface:'Pretendard',color,bold:true,alignment:'center',verticalAlignment:'middle',insets:{left:14,right:14,top:8,bottom:8}};return sh;}
function arrow(s,a,b){const sh=s.shapes.connect(a,b,{kind:'elbow',fromSide:'right',toSide:'left',line:{fill:C.blue,width:2.2},tail:{type:'triangle',width:'sm',length:'sm'}});sh.bringToFront();}
function table(s,values,widths,y=270,h=350,size=26){const t=s.tables.add({rows:values.length,columns:values[0].length,left:72,top:y,width:1392,height:h,columnWidths:widths,values});t.borders.assign({fill:C.line,width:1});for(let r=0;r<values.length;r++){t.rows[r].height=h/values.length;for(let c=0;c<values[0].length;c++){let q=t.getCell(r,c);q.fill=r===0?C.navy:r%2?C.white:C.grey;q.text.style={fontSize:size,typeface:'Pretendard',color:r===0?C.white:C.ink,bold:r===0,verticalAlignment:'middle',insets:{left:14,right:14,top:6,bottom:6}};}}return t;}
function shape(n,old){const a=order[n-1].shapes.items.find(s=>String(s.text??'')===old);if(!a)throw Error('Missing page '+n+': '+old);return a;}
function replace(n,old,value,size){const sh=shape(n,old);sh.text=value;if(size)style(sh,size,C.muted);return sh;}
function summary(n,value){const sh=order[n-1].shapes.items.find(s=>s.position.top===176&&String(s.text??''));if(!sh)throw Error('no summary '+n);sh.text=value;style(sh,26,C.muted);}
function note(n,value,size=23){const sh=order[n-1].shapes.items.find(s=>s.position.top>=700&&s.position.top<790&&String(s.text??''));if(!sh)throw Error('no note '+n);sh.text=value;style(sh,size,C.muted);}
function cell(n,r,c,value,size=26){const t=order[n-1].tables.items[0];t.cells.set(r,c,value);t.getCell(r,c).text.style={fontSize:size,typeface:'Pretendard',color:r===0?C.white:C.ink,bold:r===0,verticalAlignment:'middle',insets:{left:14,right:14,top:6,bottom:6}};}
function dedent(t){let lines=t.replaceAll('\r','').split('\n');const ind=Math.min(...lines.filter(x=>x.trim()).map(x=>x.match(/^ */)[0].length));return lines.map(x=>x.slice(ind)).join('\n').trimEnd();}
async function excerpt(page,file,ranges,{strip=true}={}){const raw=await fs.readFile(srcRoot+file,'utf8');const lines=raw.replaceAll('\r','').split('\n');const blocks=ranges.map(([a,b])=>{let t=dedent(lines.slice(a-1,b).join('\n'));if(strip)t=t.split('\n').map(x=>x.replace(/\s+#.*$/,'')).filter(x=>x.trim()&&!x.trimStart().startsWith('#')).join('\n');return t;});const code=blocks.join('\n\n');excerpts.push({page,file,ranges,stripComments:strip,sourceSha256:crypto.createHash('sha256').update(raw).digest('hex'),code});refs[page]=file;return code;}
function setCode(n,value,size=24){const sh=order[n-1].shapes.items.find(s=>s.position.top>=270&&s.position.top<300&&String(s.text??'').includes('\n'));if(!sh)throw Error('no code '+n);sh.text=value;style(sh,size,C.ink,false,'left',true);}
function fresh(n,title,subtitle,part='retriever'){const s=order[2].duplicate();s.shapes.deleteAll();for(const im of [...s.images.items])s.images.deleteById(im.id);s.background.fill=C.white;rect(s,0,0,1536,864,C.white);text(s,part.toUpperCase()+'  /  노드 상세',72,28,1392,36,21,C.teal,true);text(s,title,72,82,1392,84,title.length>43?42:46,C.navy,true);text(s,subtitle,72,176,1392,50,26,C.muted);rect(s,72,810,1392,1.5,C.line);text(s,'소스',72,819,1260,32,19,C.muted);text(s,String(n),1370,819,94,32,20,C.muted,false,'right');if(n<=55){order[n-1].delete();order[n-1]=s;}return s;}
function newPage(title,subtitle){return fresh(99,title,subtitle);}
function codePanel(s,t,y=258,h=432,size=23){rect(s,72,y,1392,h,C.grey,C.line);const sh=text(s,t,96,y+17,1344,h-34,size);style(sh,size,C.ink,false,'left',true);}

// Workflow raster assets remain unchanged; only titles, captions and notes are corrected.
replace(4,'Indexing (1/3)','Indexing workflow');
comments[4]='Indexer는 select_sources, extract, apply_profile, validate_metadata, chunk, embed, upsert, finalize_index 순으로 처리함. 원본 workflow 이미지를 유지함. 실패 시 후속 처리로 진행하지 않는 분기를 상세 페이지에서 확인함.';
replace(24,'Retrieving (1/5)','Retrieving workflow');
replace(24,'9','24');
text(order[23],'원본 도식의 현재 대응: check_query = check_search_readiness / 변환 관문 기본값 0.86\n분해 결과의 ‘보장’ 표기는 후보 우선 편성을 뜻함. 최종 top_k에는 모두 남지 않을 수 있음',72,95,1392,48,19,C.muted);
{const im=order[23].images.items[0];const pos=im.position;const ratio=660/pos.height;im.position={left:(1536-pos.width*ratio)/2,top:151,width:pos.width*ratio,height:660};}
comments[24]='원본 workflow 이미지를 유지함. 이미지 속 check_query는 현재 check_search_readiness이며 과거 관문 0.70은 현재 기본값 0.86과 다름. 준비 확인, 원 질문 검색, 변환 검토, 질문별 추가 검색, 병합 또는 리랭크, 답변 생성 및 검증 흐름임. 상세 노드명과 설정값은 현재 소스를 기준으로 설명함.';
refs[4]='indexer/app/application/graph.py';refs[24]='retriever/app/application/graph.py';

{
const s=fresh(6,'select_sources · extract  :  경로와 문서의 구분','파일을 선택한 뒤 내용을 추출하며, 두 노드가 반환하는 State 필드도 다름','indexer');
const a=box(s,'select_sources\n원문 파일 선택',72,264,600,100);const b=box(s,'extract\n본문·메타데이터 추출',864,264,600,100);arrow(s,a,b);
text(s,'sources: 절대 경로 문자열 목록',72,405,650,54,29,C.blue,true);text(s,'documents: Document 객체 목록',814,405,650,54,29,C.blue,true);
box(s,'return {"sources": selected}',72,481,650,83,26,C.grey,C.ink);box(s,'documents.extend(extracted)',814,481,650,83,26,C.grey,C.ink);
text(s,'경로는 파일의 위치를 가리킴',72,610,650,60,29);text(s,'Document = page_content + metadata',814,610,650,60,28);
text(s,'노드는 변경 필드를 딕셔너리로 반환하고, LangGraph가 기존 State에 반영함',72,726,1392,62,25,C.muted);
comments[6]='select_sources는 sources 절대 경로 목록만 만듦. extract가 각 경로를 읽고 PDF 페이지별 또는 상담 한 건별 Document를 생성해 documents로 반환함. Document는 본문 page_content와 메타데이터 metadata를 함께 담는 객체임. sources를 Document 배열로 설명하지 않음. 근거: graph.py 337~396행.';
}
summary(8,'PDF 구조 예시: block 안의 line, line 안의 span과 bbox 좌표');
setCode(9,await excerpt(9,'indexer/app/infrastructure/pdf_reader.py',[[11,11],[87,93]]),25);
// The source body is indented inside the function, so restore that structural indentation.
{let x=excerpts.at(-1);x.code=x.code.split('\n\n')[0]+'\n'+x.code.split('\n\n')[1].split('\n').map(l=>'    '+l).join('\n');setCode(9,x.code,25);}
summary(9,'_lines()가 PDF 한 페이지에서 좌표와 줄 텍스트를 수집');
note(9,'함수 전체의 실행문 발췌(긴 설명 주석 생략). 빈 줄을 제외한 (bbox, text) 목록 반환');
setCode(10,await excerpt(10,'indexer/app/infrastructure/pdf_reader.py',[[96,99],[243,249]]),24);
summary(10,'상·하단 여백의 문구를 페이지마다 한 번씩 세어 반복 여부 확인');
note(10,'상단 5.5%·하단 5% 검사. 제거 옵션 사용 시 여백의 쪽 번호 또는 2쪽 이상 반복 문구 제거',22);
comments[10]='_margin은 위쪽 5.5%와 아래쪽 5%를 판정함. Counter에 넣기 전 집합으로 만들어 한 페이지의 같은 문구는 한 번만 셈. 실제 제거는 remove_margins 옵션이 켜져 있고 여백에 있는 줄이며 숫자 쪽 번호이거나 repeated[text]>=2인 경우임. 이 페이지는 여백 판정 함수와 반복 횟수 수집 부분의 발췌임. 96~99,243~249,285~296행.';
cell(12,3,1,'회원번호·상담사명');cell(12,3,2,'member_pseudo_id\nagent_pseudo_id',23);
note(12,'정해진 식별정보 패턴이 남으면 중단. 상담은 restricted 등급. 모든 개인정보 제거를 보장하는 검사는 아님',22);
replace(13,'extract  :  상담 개인정보 처리 코드','extract  :  개인정보 치환 코드 발췌');
summary(13,'_clean() 후반부: 연락처·카드번호 삭제, 회원번호 가명화, 나이 일반화');
setCode(13,await excerpt(13,'indexer/app/domain/consultations.py',[[71,81]]),21);
note(13,'함수 후반부 발췌. 앞부분에서 이름·생년월일·원문 카드번호·끝 4자리도 치환함\n상담사명은 별도로 to_pseudo(..., "a")를 적용해 agent_pseudo_id 생성',22);
comments[13]='이 코드는 _clean의 후반부만 발췌함. PHONE·EMAIL·PAN은 정규식 패턴이며 sub는 일치한 내용을 치환함. 앞부분에서 접수정보의 이름·전화·이메일, 여러 생년월일 표기, 원문 카드번호, 끝4자리를 처리함. to_pseudo는 입력을 SHA-256 해시하고 앞 16자리와 m 또는 a 접두사를 결합함. 상담사명은 _clean에서 이름을 지운 뒤 별도 metadata 생성 시 a_ 가명으로 저장함. 이 발췌만으로 전체 가명화 함수를 대체하면 안 됨. 31~37,52~81,182~189행.';
setCode(15,await excerpt(15,'indexer/app/application/graph.py',[[404,409]]),25);summary(15,'파일명으로 프로필을 찾고 모든 Document에 동일한 관리 규칙 적용');
cell(17,3,1,'발화 2개를 묶어 1턴으로 구성',26);note(17,'상담 1턴은 발화 2개(통상 고객·상담사). 긴 속성표는 행을 자르지 않고 크기 예외로 보존',22);
replace(18,'chunks\n현재 청크\n\nindex_manifest\n이전 해시·설정','chunks\n현재 청크\n\n기존 manifest 파일\n이전 해시·설정');
note(18,'이전 정보: output_path/index_manifest.json. 기본 모델 KURE-v2, 벡터 차원은 실행 시 측정',22);
comments[18]='본문과 메타데이터 해시가 둘 다 같아야 생략함. 임베딩 서명 또는 청킹 설정이 달라지면 전체 재임베딩 계획으로 승격함. index_manifest는 State 필드가 아니라 output_path/index_manifest.json 파일임. 768차원은 현재 데이터에서 관찰되는 값이며 하드코딩한 계약이 아님. graph.py565~597,724~748, embedder.py114~160행.';
{const load=await excerpt(19,'indexer/app/infrastructure/embedder.py',[[54,54]]);const embed=await excerpt(19,'indexer/app/infrastructure/embedder.py',[[70,79]]);setCode(19,'# _load()의 모델 생성 부분\n'+load+'\n\n# embed()의 실행문 (주석 생략)\n'+embed,22);}
summary(19,'모델은 처음 필요할 때 적재하고, 여러 본문을 배치로 벡터화');
note(19,'kind는 인터페이스 호환용으로 즉시 버림. encode는 query·passage를 구분하지 않고 벡터 정규화',22);
setCode(21,await excerpt(21,'indexer/app/infrastructure/chroma_store.py',[[138,147]]),23);summary(21,'영속 저장 경로·cosine 거리·임베딩 서명을 컬렉션에 설정');
note(21,'서명은 메타데이터에 기록. check_signature()로 비교 가능하며 일반 초기화에서 자동 검사하지 않음',22);
setCode(22,await excerpt(22,'indexer/app/infrastructure/chroma_store.py',[[150,168]]),23);summary(22,'청크 ID를 메타데이터에 넣고 저장 가능한 값으로 정리한 뒤 upsert');
replace(23,'카드명 64개 사전 등록  /  OOV 후보는 검토 파일로만 저장','카드명 사전 등록  /  미등록 단어(OOV) 후보는 검토 파일로 저장');
note(23,'발행 결과는 active_index.json의 chunk_count·card_dictionary_count로 확인. 완료 후 END',22);
replace(25,'출력: index_info 또는 validation_errors','정상: index_info  /  요청값 오류: validation_errors',27);
note(25,'빈 컬렉션·서명 불일치: IndexUnavailableError 발생. 정상일 때 다음 vector_search로 진행',22);
setCode(27,await excerpt(27,'retriever/app/infrastructure/chroma_store.py',[[139,144]]),27);summary(27,'질문 벡터·조회 수·권한 조건을 Chroma 컬렉션에 전달');
cell(28,0,1,'검색 후보 상한\n(raw_k)',24);cell(28,0,2,'후속 후보 상한\n(fused_k)',24);cell(28,0,3,'최종 상한',24);
summary(28,'top_k=5, 후보 배수 4의 기본 설정 예시. 실제 결과 수는 더 적을 수 있음');
note(28,'raw_k=fused_k×4, 리랭크 fused_k=top_k×2. MMR은 40/80개 조회 후 20/40개 선택\n변환 질문도 같은 후보 수 규칙 사용. similarity 조회 수는 raw_k와 같음',22);
comments[28]='이 표는 각 노드가 유지하는 후보 수의 상한임. 접근 가능한 후보가 적으면 더 적게 반환함. similarity는 Chroma에서 raw_k를 조회함. MMR은 기본 fetch_multiplier=2이므로 raw_k의 2배 풀에서 다양성을 고려하여 raw_k를 고름. 표의 최종 5개는 변환 질문이 있더라도 최종 병합 후 top_k 상한임.';
setCode(29,await excerpt(29,'retriever/app/domain/query_transform.py',[[65,79]]),22);
setCode(33,await excerpt(33,'retriever/app/infrastructure/bm25_index.py',[[210,215]]),27);summary(33,'접근 권한 마스크를 적용한 키워드 후보 조회');
setCode(34,await excerpt(34,'retriever/app/domain/scoring.py',[[65,80]]),23);
note(34,'결합: Vector 0.6 + BM25 0.4. 결과 score에 융합값 저장, 원 vector_score는 별도 유지',22);
setCode(37,await excerpt(37,'retriever/app/application/graph.py',[[995,1003]]),24);
note(37,'top_k=5인 리랭크 모드: baseline_hits 최대 10개, hits 최대 5개 보관',23);
setCode(39,await excerpt(39,'retriever/app/application/graph.py',[[1028,1036]],{strip:false}),22);
setCode(40,await excerpt(40,'retriever/app/application/graph.py',[[1010,1024]]),22);
setCode(41,await excerpt(41,'retriever/app/domain/query_transform.py',[[187,206]]),23);
comments[41]='weighted_rrf 본문 누적 부분 발췌임. 원점수 대신 그룹 내 순위를 사용함. 하나의 청크가 여러 목록에 있으면 항을 더함. 일반 변환은 원 질문 전체0.5, 변환 전체0.5를 질문 수로 균등 분할함. 이후 정렬 기준은 RRF 내림차순, 최고 source rank, chunk_id 오름차순임. 183~215,242~293행.';
replace(42,'merge_queries  :  분해 질문의 근거 확보','merge_queries  :  분해 질문 후보의 우선 배치');summary(42,'하위 질문별 Top-1을 중복 제거해 먼저 놓고, 나머지를 RRF 순서로 채움');
replace(42,'하위 Top-1 우선 확보','하위 Top-1 우선 배치');cell(42,2,3,'각 하위 Top-1 우선 배치 후 RRF',24);
note(42,'마지막에 top_k로 절단. 모든 하위 질문의 결과가 최종 목록에 남는다는 보장은 없음',22);
summary(44,'모델 생성 부분과 질문·본문 쌍의 predict 호출 부분 발췌');
summary(45,'각 하위 질문 Top-3를 후보 풀에 포함하고 중복 청크는 최고 점수 사용');
note(45,'병합 점수 상위 top_k만 최종 선택. 모든 하위 Top-3가 최종 결과에 남는 것은 아님',22);
{
const s=fresh(46,'rerank  :  decomposition 계산 예시','설명용 입력 점수로 계산. 하위 질문별 가중치 0.45를 더하는 방식이 아님');
box(s,'원 질문: A 0.80, B 0.70     하위 1: B 0.95, C 0.90     하위 2: D 0.92, B 0.85',72,254,1392,75,26);
table(s,[['청크','하위 질문 최고점','원 질문 점수','0.9×하위 + 0.1×원 질문'],['B','max(0.95, 0.85) = 0.95','0.70','0.925'],['D','0.92','없음 → 0','0.828'],['C','0.90','없음 → 0','0.810'],['A','없음','0.80','0.080']],[180,460,310,442],367,306,25);
text(s,'최종 Top-3: B → D → C. 원 질문에만 있는 A는 원 질문 점수 × 0.1',72,719,1392,64,26,C.blue,true);
refs[46]='retriever/app/domain/query_transform.py';comments[46]='실측 성능 결과가 아닌 알고리즘 설명용 계산 예시임. rerank_each_query_and_merge의 decomposition 경로에서 하위 질문별 상위3개를 후보 풀에 포함함. 같은 청크 B의 하위 점수는 max(0.95,0.85)=0.95이며 최종0.925. 하위 질문이 2개라고0.45씩 나눠 더하지 않음. 원 질문에만 있는 A는0.1×0.80=0.080. 최종 후보를 점수순 정렬하고 top_k로 절단함. 근거347~409행.';
}
comments[47]=JSON.parse(await fs.readFile(root+'/.build/review-v4-content.json','utf8'))[46].notes;
setCode(48,await excerpt(48,'retriever/app/application/graph.py',[[1224,1235]]),22);
summary(48,'최종 hits를 1번부터 순서대로 XML 근거 블록에 넣음');note(48,'escape는 XML 특수문자를 변환함. 근거가 없으면 "해당 없음". 사용자 입력 조립은 보충 55페이지',22);
replace(49,'입력: prompt  +  남은 LLM 호출 예산','입력: system_prompt + user_prompt + 남은 LLM 호출 예산');
summary(49,'아래는 LLM 어댑터 발췌. 노드는 raw_answer와 llm_calls를 반환');cell(49,0,0,'raw_answer 내부 필드',25);
note(49,'user_prompt가 없으면 prompt로 대체. 실제 전송 시도 횟수를 llm_calls에 누적. 다음 verify_evidence',22);
comments[49]='_run_generate_answer가 self.llm.complete_structured에 system_prompt와 user_prompt(없으면 prompt)를 전달함. 어댑터는 AnswerDraft 구조를 지정하고 system/human 메시지로 호출함. 실제 노드 반환은 raw_answer와 llm_calls=result.attempts임. 파싱 실패이면 빈 결론·주의사항·근거와 parsing_error를 만들어 검증기로 전달함. 전송 재시도도 LLM 예산을 소비함. graph.py1260~1291, llm_client.py284~293행.';
refs[49]='retriever/app/infrastructure/llm_client.py (노드: application/graph.py)';
cell(50,1,1,'정수이면서 검색 결과 1 ~ N 범위인지',25);
cell(50,2,1,'정규화한 인용이 청크 본문에 연속 포함되는지',25);
note(50,'현재 소스 주의: 프롬프트는 빈 caution을 허용하지만 검증기는 SCHEMA_ERROR로 처리함\n자동 검증은 형식·인용 확인이며, 답변 의미의 정확성은 별도 검토 필요',22);
comments[50]='검증은 ref 정수·범위, 정규화한 인용문이 청크 본문에 연속 포함되는지, 위치가 존재하는지, 결론·주의사항·필요한 근거 유무를 검사함. 위치가 실제 원문 위치와 같은지 재개봉 검증하지 않음. 주의사항이 없으면 빈 문자열을 허용한 시스템 프롬프트(graph.py1200~1204)와 빈 caution을 오류로 처리하는 build_answer(scoring.py216~229)는 현재 소스 계약이 불일치함. 이 자료는 실제 동작을 명시하며 제품 소스 자체는 변경하지 않음. 검증 통과는 의미적 정답 보장이 아님.';
setCode(51,(await excerpt(51,'retriever/app/domain/scoring.py',[[170,172]]))+'\n\n# 오류 목록이 모두 비었을 때만 자동 검증 통과\n'+await excerpt(51,'retriever/app/domain/scoring.py',[[229,229]]),23);summary(51,'build_answer()의 인용 대조와 최종 통과 조건 발췌');
note(52,'최초 생성 뒤 최대 2회 재생성. 질문 변환도 같은 호출 예산 사용. 예산이 먼저 끝나면 중단',22);
comments[52]='MAX_REPAIRS=2는 최초 생성 뒤 재생성 최대2회를 뜻함. API 기본 LLM 예산은 요청 전체2회, CLI8회이며 Router의 질문 변환 및 전송 재시도도 소비함. API auto 변환에1회 사용하면 답변용 기본 잔여는1회이므로 수정 루프를2번 모두 수행한다고 보장하지 않음. 실패 시 hints를 누적하고 build_prompt가 중복을 제거해 재구성함. 소스 graph.py369~382,445~452, settings.py161~163,189행.';

const supplements=[];
{
const s=newPage('search_transformed  :  노드에서 실행 코드까지','workflow의 이름을 찾은 뒤 등록 코드·래퍼·실행 함수 순서로 추적');
const a=box(s,'그래프 노드\nsearch_transformed',72,271,400,100);const b=box(s,'래퍼 함수\n_search_transformed',568,271,400,100);const c=box(s,'실행 함수\n_run_search_transformed',1064,271,400,100,25);arrow(s,a,b);arrow(s,b,c);
text(s,'그래프 등록 이름\n다음 노드·분기 연결',72,410,400,110,28);text(s,'공통 실행 경로 연결\n_run_node → run_node',568,410,400,110,28);text(s,'질문별 _search_one 호출\n실제 검색 결과를 반환',1064,410,400,110,27);
box(s,'State = 노드들이 공유하는 작업 기록\nreturn {"transformed_hit_groups": groups, "warnings": warnings}',72,594,1392,112,28,C.grey,C.ink);
text(s,'반환값은 State 변경분. 일반 필드는 교체하고 warnings 등 reducer 지정 필드는 누적',72,729,1392,62,24,C.muted);
supplements.push(s);refs[53]='retriever/app/application/graph.py';comments[53]='그래프 노드의 이름, 모듈 래퍼, Resources의 실행 메서드를 구분해야 함. graph 등록에서 _search_transformed를 부르고 _run_node의 공통 처리와 resources.run_node가 _run_search_transformed로 연결함. 실행 함수가 _search_one 도우미를 질문마다 호출함. 반환 딕셔너리는 전체 State를 새로 만드는 것이 아니라 변경 필드임. state.py의 Annotated reducer가 warnings 등을 누적함.';
}
{
const s=newPage('assess_transform_gate  :  두 관문과 점수','질문 변환을 검토할지와, 검색 근거로 답변을 시작할지는 다른 판단');
table(s,[['구분','질문 변환 관문','답변 진입 관문'],['판정 위치','assess_transform_gate','검색 완료 처리의 _finalize_hits'],['비교 대상','최초 원 질문 검색의 첫 vector_score','최종 hits[0]의 vector_score'],['기본 기준','0.86 이상이면 변환 검토 생략','0.62 미만·점수 없음·clarify이면 needs_check'],['적용 조건','transform=auto\noff이면 변환 검토 생략','answer_enabled=True\n검색 전용은 답변 진입 생략']],[250,571,571],265,402,25);
text(s,'vector_score는 융합·RRF·리랭크 점수와 구분. 0.86은 정답 확률 86%를 뜻하지 않음',72,723,1392,67,24,C.muted);
supplements.push(s);refs[54]='retriever/app/application/graph.py';comments[54]='transform_gate_vector_score는 최초 원 질문 검색의 첫 후보 점수임. _finalize_hits는 최종 hits의 첫 후보에 남아 있는 vector_score를 비교함. 최종 순위는 융합이나 리랭크로 달라질 수 있음. BM25에만 있는 후보는 vector_score가 None일 수 있어 답변 관문을 통과하지 못함. 두 기준값은 설정 기본값이며 환경변수로 바뀔 수 있음. 둘 다 정확도 확률을 뜻하지 않음. graph.py195~214,774~850, settings.py174,177행.';
}
{
const s=newPage('build_prompt  :  원 질문과 수정 지침','근거 블록 뒤에 원 질문과 검증 오류의 수정 지침을 붙여 사용자 입력 구성');
const code=await excerpt(55,'retriever/app/application/graph.py',[[1237,1250]]);codePanel(s,code,258,438,22);
text(s,'dict.fromkeys는 지침의 순서를 유지하며 중복 제거. query는 변환 질문이 아닌 사용자 원 질문',72,725,1392,62,23,C.muted);
supplements.push(s);comments[55]='build_prompt는 최종 검색 근거를 제공하되 사용자 원래 질문에 답하도록 query를 넣음. repair_hints는 누적 reducer 필드이므로 dict.fromkeys로 같은 지침을 한 번만 표시함. 입력 문자열 escape는 XML 특수문자를 안전하게 표현하기 위한 처리이며 의미적 프롬프트 공격을 완전히 차단한다는 뜻은 아님. 반환 system_prompt는 고정8섹션 지시문, user_prompt는 이 코드로 구성한 입력, prompt는 같은 값을 담은 호환 필드임.';
}
order.splice(52,0,...supplements);

// Refresh every technical slide's source citation and teaching notes, including formerly PASS pages.
for(let i=0;i<order.length;i++){
const s=order[i];s.moveTo(i);const n=i+1;
const technical=(n>=5&&n<=23)||(n>=25&&n<=55);
if(technical){
 const footer=s.shapes.items.find(sh=>sh.position.top>=810&&String(sh.text??'')&&!/^\d+$/.test(String(sh.text)));
 if(footer){footer.text='소스: '+(refs[n]||'retriever/app/application/graph.py');style(footer,19,C.muted);}
 for(const sh of s.shapes.items)if(sh.position.top>=800&&/^\d+$/.test(String(sh.text??'')))sh.text=String(n).padStart(2,'0');
 const body=s.shapes.items.map(sh=>String(sh.text??'')).filter(Boolean).join('\n');
 const tab=s.tables.items.map(t=>JSON.stringify(t.toProto?.()??{})).join('\n');
 const extra=comments[n]||'먼저 입력 필드와 반환 필드를 확인하고 그림의 순서대로 현재 구현을 설명함. 코드 상자는 표시된 소스에서 발췌한 것으로 필요한 앞뒤 문맥과 import는 원본에서 확인함.';
 const ranges=excerpts.filter(e=>e.page===n).map(e=>e.file+':'+e.ranges.map(r=>r.join('-')).join(',')).join('\n');
 s.speakerNotes.textFrame.setText(body+'\n\n[교육생 설명]\n'+extra+'\n\n[소스 근거]\nhybrid-ai-lab/vector/'+(refs[n]||'retriever/app/application/graph.py')+'\n'+ranges);
}else if(comments[n])s.speakerNotes.textFrame.setText(comments[n]+'\n소스: hybrid-ai-lab/vector/'+refs[n]);
}
// Keep original final-section notes and numbering, shifted by the three supplemental pages.
for(let n=56;n<=58;n++)for(const sh of order[n-1].shapes.items)if(sh.position.top>740&&/^\d+$/.test(String(sh.text??'')))sh.text=String(n);
await fs.writeFile(root+'/.build/v5-source-excerpts.json',JSON.stringify(excerpts,null,2));
await fs.writeFile(root+'/.build/v5-page-sources.json',JSON.stringify(refs,null,2));
await(await PresentationFile.exportPptx(p)).save(root+'/.build/candidate-v5-reviewed.pptx');
console.log('Exported '+p.slides.items.length+' slides; source excerpts '+excerpts.length);
