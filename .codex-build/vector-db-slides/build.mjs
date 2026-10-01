import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const runtime='C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=runtime+'/node/node_modules';
const require=createRequire(import.meta.url);
const PptxGenJS=require(runtime+'/node/node_modules/pptxgenjs');
const {FileBlob,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs'));
const root='C:/Users/hiond/class/design-agentic-ai';
const build=root+'/.codex-build/vector-db-slides';
const final=root+'/output/pptx/벡터DB-HNSW와-IVF-2장.pptx';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const source='https://github.com/cna-bootcamp/aistudy/blob/main/agentic-ai/textbook/11.RAG%20%ED%92%88%EC%A7%88%20%ED%8A%9C%EB%8B%9D.md';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const FONT='Pretendard';
const fsMin=n=>{if(n<14)throw Error('Minimum font size: 14pt');return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,breakLine:false,vertAnchor:'ctr',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2,begin=false){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{}),...(begin?{beginArrowType:'triangle'}:{})}});}
function circle(s,cx,cy,r,fill=C.blue,stroke=fill){s.addShape(pptx.shapes.OVAL,{x:cx-r,y:cy-r,w:2*r,h:2*r,fill:{color:fill},line:{color:stroke,width:1.5}});}
function node(s,label,x,y,active=false){circle(s,x,y,.20,active?C.blue:C.white,active?C.blue:C.slate);text(s,label,x-.19,y-.13,.38,.25,16,{bold:true,color:active?C.white:C.navy,align:'center'});}
function pageHeader(s,title){text(s,'벡터DB 구성 원리 › 검색 인덱스 튜닝',.55,.35,14.9,.28,15,{color:C.sub});text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);}
function footer(s,n,ref){line(s,.55,8.59,14.9,0,C.footer,false,.7);text(s,ref,.55,8.68,12,.2,14,{color:C.sub,hyperlink:{url:source}});text(s,'벡터DB  /  '+n,12.5,8.68,2.95,.2,14,{color:C.sub,align:'right'});}
function table(s,rows,x,y,w,cols,heights){s.addTable(rows.map((r,i)=>r.map(t=>({text:t,options:{fill:i===0?C.head:(i%2?C.white:C.alt),color:i===0?C.navy:C.ink,bold:i===0}}))),{x,y,w,h:heights.reduce((a,b)=>a+b,0),colW:cols,rowH:heights,fontFace:FONT,fontSize:fsMin(17),margin:[.08,.13,.08,.13],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};
 pageHeader(s,'벡터DB와 HNSW 검색');
 text(s,'벡터DB는 임베딩 벡터를 저장하고, 질문과 가까운 벡터에 연결된 문서를 찾습니다.',.55,1.78,14.9,.38,21,{color:C.slate});
 text(s,'연결을 따라 범위를 좁히는 HNSW',.55,2.32,7.2,.38,24,{bold:true,color:C.navy});
 text(s,'세 가지 파라미터',8.15,2.32,7.3,.38,24,{bold:true,color:C.navy});
 const xs={A:2.05,E:2.76,C:3.47,F:4.18,D:4.89,G:5.60,B:6.31};
 const levels=[{y:3.30,labels:['A','B']},{y:4.24,labels:['A','C','D','B']},{y:5.18,labels:['A','E','C','F','D','G','B']}];
 text(s,'상위 계층',.55,3.15,1.3,.30,17,{bold:true,color:C.slate});
 text(s,'중간 계층',.55,4.09,1.3,.30,17,{color:C.slate});
 text(s,'하위 계층',.55,5.03,1.3,.30,17,{bold:true,color:C.slate});
 for(const l of levels){line(s,2.05,l.y,4.26,0,C.border,false,2);}
 line(s,6.31,3.5,0,.54,C.blue,true,2.5);
 line(s,4.89,4.44,0,.54,C.blue,true,2.5);
 line(s,2.25,3.3,3.86,0,C.blue,true,3);
 line(s,5.09,4.24,1.02,0,C.blue,false,3,true);
 line(s,4.38,5.18,.31,0,C.blue,false,3,true);
 for(let i=0;i<levels.length;i++){const l=levels[i];for(const label of l.labels){node(s,label,xs[label],l.y,(i===0)||(i===1&&['B','D'].includes(label))||(i===2&&['D','F'].includes(label)));}}
 text(s,'먼 구간을 빠르게 이동',3.06,2.83,3.75,.26,16,{color:C.blue,align:'center'});
 text(s,'가까운 이웃을 세밀하게 비교',2.36,5.61,4.50,.29,17,{color:C.blue,align:'center'});
 text(s,'파란선은 검색 경로의 개념 예시입니다.',.55,6.06,7.2,.26,14,{color:C.sub});
 table(s,[['파라미터','무엇을 조정하나요?','값을 높이면'],['M','그래프 연결 밀도','메모리·구축비용 증가'],['ef_construction','구축할 때 후보 폭','구축 품질·시간 증가'],['ef_search','검색할 때 후보 폭','재현율·검색시간 증가']],8.15,2.98,7.3,[2.5,2.45,2.35],[.48,.68,.68,.68]);
 text(s,'후보 폭은 유지하는 후보 목록의 크기입니다.\n실제로 방문한 모든 노드 수와는 다릅니다.',8.15,5.72,7.3,.59,16,{color:C.slate});
 rect(s,.55,6.56,14.9,.68,C.tint,C.tint);
 text(s,'문서의 시작 예시',.75,6.76,2.55,.27,18,{bold:true,color:C.blue});
 text(s,'M = 16   /   ef_construction = 200   /   ef_search = 100',3.42,6.74,11.7,.31,22,{bold:true,color:C.navy});
 text(s,'top_k는 반환 개수입니다. ef_search는 보통 top_k 이상으로 두고 탐색 폭을 조정합니다.',.55,7.47,14.9,.31,19,{color:C.ink});
 text(s,'같은 질문셋으로 Recall@k · p95 검색시간 · 메모리를 비교하며 조정합니다.',.55,7.99,14.9,.32,20,{bold:true,color:C.navy});
 footer(s,1,'참고: RAG 품질 튜닝 §4.1 · HNSW 공식 문서 | 수치는 제품 기본값이 아닙니다.');
 s.addNotes(`벡터DB는 문서의 임베딩 벡터와 본문, 메타데이터를 저장하고 질의 벡터와 가까운 벡터에 연결된 문서를 찾습니다. 이 슬라이드는 그중 빠른 유사도 검색을 위한 HNSW 인덱스에 집중합니다. HNSW는 근사 최근접 이웃 검색 방식으로, 모든 벡터를 비교하는 정확 검색보다 빠르게 후보를 찾는 대신 일부 이웃을 놓칠 수 있습니다. 계층 그래프와 파란 경로는 원리를 설명하는 개념도이며 실제 실행 결과가 아닙니다. 같은 문자는 같은 벡터가 여러 계층에 등장한 것입니다.\n\nM은 구축 시 만드는 연결의 밀도에 영향을 주는 파라미터입니다. 계층별 실제 차수의 단순 상한으로 해석하지 않습니다. M이 커지면 메모리와 구축 작업량이 늘지만 검색 속도는 데이터와 구현에 따라 달라집니다. ef_construction은 구축 중 후보 목록 크기이며 품질 개선은 포화될 수 있습니다. ef_search는 검색 중 유지하는 후보 목록 크기이고 실제 방문한 노드 총수와 다릅니다. 두 ef 값의 대소 관계를 일반 필수 규칙으로 두지 않습니다. hnswlib의 ef는 k 이상이어야 하며 제품별 이름과 허용 범위는 다릅니다.\n\nM=16, ef_construction=200, ef_search=100은 참조 문서의 시작 예시이며 제품 기본값·보장값·우리 코드의 적용값이 아닙니다. 우리 코드의 hybrid-ai-lab/indexer/vector-bm25/app/infrastructure/index_repository.py:141-149는 Chroma의 cosine 공간을 명시합니다. M과 두 ef 값은 명시하지 않습니다.\n\nRecall@k는 여기서 정확 최근접 이웃 top-k 대비 근사 검색이 회수한 비율로 측정할 수 있습니다. 실제 RAG 문서 관련성을 평가하는 정답셋 recall은 별도 평가입니다. p95는 95%의 검색이 그 시간 안에 완료되는 검색 지연입니다. 동일 질문셋, 거리 함수, 필터와 실행 환경에서 재현율·시간·인덱스 메모리 및 구축 시간을 함께 비교합니다.\n\n출처:\n${source}\nhttps://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md\nhttps://arxiv.org/abs/1603.09320`);
}
async function createSlide02(){
 const s=pptx.addSlide();s.background={color:C.white};
 pageHeader(s,'IVF 검색과 파라미터 튜닝');
 text(s,'비슷한 벡터를 군집으로 묶고, 질문과 가까운 군집만 골라 검색합니다.',.55,1.78,14.9,.38,21,{color:C.slate});
 text(s,'군집을 골라 검색 범위를 줄이는 IVF',.55,2.32,7.3,.38,24,{bold:true,color:C.navy});
 text(s,'두 가지 파라미터',8.15,2.32,7.3,.38,24,{bold:true,color:C.navy});
 circle(s,4.11,3.02,.18,C.white,C.blue);
 text(s,'질문 벡터',4.45,2.88,2,.28,17,{bold:true,color:C.blue});
 line(s,3.26,3.35,1.7,0,C.blue,false,2);
 line(s,4.11,3.20,0,.15,C.blue,false,2);
 line(s,3.26,3.35,0,.24,C.blue,true,2);
 line(s,4.96,3.35,0,.24,C.blue,true,2);
 const centers=[1.56,3.26,4.96,6.66];
 const offsets=[[-.37,-.44],[.30,-.40],[-.43,.10],[.33,.22],[-.05,.40]];
 for(let i=0;i<4;i++){
  const cx=centers[i],on=i===1||i===2;
  rect(s,cx-.76,3.67,1.52,1.82,on?C.tint:C.white,on?C.blue:C.border);
  for(const [dx,dy]of offsets){circle(s,cx+dx,4.4+dy,.065,on?C.blue:C.border);}
  circle(s,cx,4.4,.13,on?C.navy:C.slate);
  text(s,'군집 '+(i+1),cx-.64,5.65,1.28,.28,18,{bold:on,color:on?C.blue:C.slate,align:'center'});
 }
 text(s,'그림: nlist = 4 · nprobe = 2  |  큰 점은 군집 중심점',.55,6.06,7.3,.27,14,{color:C.sub});
 table(s,[['파라미터','무엇을 조정하나요?','값을 높이면'],['nlist','전체 군집 수','더 작은 군집으로 분할'],['nprobe','한 번에 검색할\n군집 수','재현율·검색시간 증가']],8.15,2.98,7.3,[2.5,2.45,2.35],[.48,.82,.82]);
 text(s,'구축 전에 대표 데이터로 군집을 학습합니다.\n검색할 군집 수는 전체 군집 수를 넘지 않습니다.',8.15,5.44,7.3,.64,17,{color:C.slate});
 rect(s,.55,6.56,14.9,.68,C.tint,C.tint);
 text(s,'문서의 시작 예시',.75,6.76,2.55,.27,18,{bold:true,color:C.blue});
 text(s,'벡터 10,000개   →   nlist = 100   →   nprobe = 5 ~ 10',3.42,6.74,11.7,.31,22,{bold:true,color:C.navy});
 text(s,'top_k는 반환 개수입니다. 같은 질문셋의 Recall@k · p95 검색시간 · 메모리로 값을 정합니다.',.55,7.47,14.9,.32,19);
 text(s,'IVFFlat은 모든 군집을 제한 없이 비교하면 정확 검색이 됩니다. IVFPQ는 압축 오차가 남을 수 있습니다.',.55,7.99,14.9,.32,17,{color:C.slate});
 footer(s,2,'참고: RAG 품질 튜닝 §4.2 · Faiss 공식 문서 | 수치는 제품 기본값이 아닙니다.');
 s.addNotes(`IVF는 벡터를 군집으로 나누고 질문에 가까운 중심점의 군집부터 살펴봅니다. nlist는 전체 inverted list 또는 군집 수, nprobe는 검색할 군집 수입니다. 그림은 nlist=4, nprobe=2로 축약한 개념도이며 실제 벡터 분포나 모델 출력을 보여 주지 않습니다. 큰 점은 각 군집의 중심점입니다. 색칠한 두 군집에서 후보 벡터를 비교한 뒤 top_k개 결과를 반환합니다.\n\nnlist가 커지면 평균 군집 크기는 작아지지만 중심점을 고르는 비용과 학습 품질 등도 영향을 받습니다. nprobe를 늘리면 일반적으로 재현율이 좋아지고 검색 시간이 늘어납니다. nprobe는 nlist 이하입니다. 군집 길이가 불균등할 수 있어 실제 탐색한 벡터 비율을 nprobe/nlist로 단정하지 않습니다.\n\n10,000개 벡터, nlist=100, nprobe=5~10은 참조 문서의 설명용 시작 예시이며 제품 기본값이나 측정 결과가 아닙니다. nlist≈sqrt(N)을 보편 공식으로 적용하지 않습니다. Faiss는 centroid 할당과 list 스캔 비용을 균형 있게 보는 C×sqrt(N) 형태 등 조건별 지침을 설명합니다. 실제 데이터 분포와 대표 학습 표본, 거리 함수, 필터 및 지연 예산으로 측정해야 합니다. 같은 질문셋의 정확 top-k 대비 Recall@k, p95 검색시간, 인덱스 메모리와 구축 시간을 비교합니다.\n\nIVF는 train으로 중심점을 학습한 후 add로 벡터를 추가합니다. 추가 데이터는 기존 군집에 배정되며 자동 재학습되지 않습니다. 분포가 달라지면 대표 표본으로 재학습과 재구축을 검토합니다.\n\nnprobe=nlist는 모든 리스트를 방문한다는 뜻입니다. IVFFlat에서 별도의 스캔 제한 없이 원본 벡터를 같은 거리 함수와 동일 조건으로 모두 비교하면 정확 전수 검색과 같습니다. IVFPQ는 압축된 벡터 표현으로 거리를 근사하므로 모든 리스트를 방문해도 압축 오차가 남을 수 있습니다. IVFFlat 자체를 메모리 효율형으로 일반화하지 않습니다. 압축에 따른 메모리 절감은 IVFPQ 등과 구분합니다.\n\n참조 문서의 Faiss 코드는 L2 거리 예시이며 우리 Chroma 코드의 cosine 설정과 구분합니다. Faiss는 벡터 검색 라이브러리이며 완전한 벡터DB 자체와 같은 범주는 아닙니다. 우리 코드가 IVF를 사용한다고 주장하지 않습니다.\n\n출처:\n${source}\nhttps://github.com/facebookresearch/faiss/wiki/Faster-search\nhttps://github.com/facebookresearch/faiss/wiki/Faiss-indexes\nhttps://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index`);
}
async function main(){
 await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(final),{recursive:true});
 pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';
 pptx.author='design-agentic-ai';pptx.subject='벡터DB HNSW와 IVF 원리 및 검색 파라미터';pptx.title='벡터DB: HNSW와 IVF';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();await createSlide02();
 const candidate=build+'/candidate.pptx';await pptx.writeFile({fileName:candidate});
 const JSZip=require(runtime+'/node/node_modules/jszip');
 const zip=await JSZip.loadAsync(await fs.readFile(candidate));
 const contentTypes=await zip.file('[Content_Types].xml').async('string');
 zip.file('[Content_Types].xml',contentTypes.replace(/<Override PartName="([^"]+)"[^>]*\/>/g,(entry,part)=>zip.file(part.slice(1))?entry:''));
 await fs.writeFile(candidate,await zip.generateAsync({type:'nodebuffer'}));
 const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
 const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:2,requiredNativeTableOwnerSlides:[1,2],requiredNativeChartOwnerSlides:[],pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--require-native-table-slide','1','--require-native-table-slide','2'],fontPolicy:{basis:'user_request',families:[FONT]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
 const p=await PresentationFile.importPptx(await FileBlob.load(final));
 for(let i=0;i<2;i++){const png=await p.export({slide:p.slides.getItem(i),format:'png',scale:1.5});await fs.writeFile(root+'/output/pptx/벡터DB-'+(i+1)+'.png',new Uint8Array(await png.arrayBuffer()));}
 console.log(JSON.stringify({final,result}));
}
main().catch(e=>{console.error(e);process.exit(1);});
