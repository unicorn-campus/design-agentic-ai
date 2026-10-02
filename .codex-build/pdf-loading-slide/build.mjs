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
const build=root+'/.codex-build/pdf-loading-slide';
const final=root+'/output/pptx/PDF-문서로드-방법과설계-1장.pptx';
const skill='C:/Users/hiond/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const FONT='Pretendard';
const C={navy:'1E2A5C',blue:'2E74C6',ink:'2B3242',slate:'4A5364',sub:'7C8598',white:'FFFFFF',tint:'EEF3FA',alt:'F5F8FC',head:'E2EEF9',border:'D9E0EC',line:'EDF0F6',footer:'E9ECF3'};
const fsMin=n=>{if(n<14)throw Error('Minimum font size 14pt');return n;};
let pptx;
function text(s,t,x,y,w,h,size=18,extra={}){s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:fsMin(size),color:C.ink,margin:0,breakLine:false,vertAnchor:'ctr',...extra});}
function rect(s,x,y,w,h,fill=C.white,stroke=C.border){s.addShape(pptx.shapes.RECTANGLE,{x,y,w,h,fill:{color:fill},line:{color:stroke,width:1}});}
function line(s,x,y,w,h,color=C.blue,arrow=false,width=2){s.addShape(pptx.shapes.LINE,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
function pageHeader(s,title){text(s,'벡터DB 구성 원리 › 문서 로드',.55,.35,14.9,.28,15,{color:C.sub});text(s,title,.55,.75,14.9,.68,48,{bold:true,color:C.navy});rect(s,.55,1.55,14.9,.035,C.border,C.border);rect(s,.55,1.55,2.1,.035,C.blue,C.blue);}
async function createSlide01(){
 const s=pptx.addSlide();s.background={color:C.white};pageHeader(s,'문서 로드: PDF 본문과 출처 읽기');
 text(s,'본문과 페이지 위치를 읽어, 다음 청킹·정제 단계가 문맥과 출처를 이어받게 합니다.',.55,1.78,14.9,.38,22,{color:C.slate});
 text(s,'우리 코드: PyMuPDF로 페이지 읽기',.55,2.38,7.8,.37,24,{bold:true,color:C.navy});
 text(s,'첨부 자료의 PDF 로드 제품 비교',8.8,2.38,6.65,.37,24,{bold:true,color:C.navy});
 rect(s,.55,2.98,7.85,2.48,C.navy,C.navy);
 const code=[
 'with pymupdf.open(source.path) as pdf:',
 '    for number, page in enumerate(pdf, start=1):',
 '        page_dict = page.get_text("dict", sort=True)',
 '        lines = _page_lines(page_dict)',
 '        pages.append({"number": number,',
 '                      "height": page.rect.height,',
 '                      "lines": lines})',
 ];
 for(let i=0;i<code.length;i++)text(s,code[i],.80,3.16+i*.295,7.35,.27,18,{color:C.white});
 text(s,'loaders.py 실제 발췌 · 줄바꿈 조정 · 앞에서 pages 목록 준비',.55,5.58,7.85,.24,14,{color:C.sub});
 const stages=[{x:.55,w:2.17,t:'페이지 텍스트·좌표'},{x:3.09,w:2.55,t:'파일당 한 문서 + 페이지 범위'},{x:6.01,w:2.39,t:'다음 청킹·정제'}];
 for(let i=0;i<stages.length;i++){const a=stages[i];rect(s,a.x,6.00,a.w,.48,C.tint,C.border);text(s,a.t,a.x+.05,6.13,a.w-.1,.22,i===1?14:16,{bold:true,color:C.navy,align:'center'});if(i<2)line(s,a.x+a.w+.06,6.24,.25,0,C.blue,true,1.5);}
 const rows=[
 ['제품','주요 기능·강점','우리 코드'],
 ['Docling','AI 레이아웃·표 분석\nOCR 연동','검토 후보'],
 ['PyMuPDF','텍스트·좌표 추출\n이미지 추출 기능','사용 중\n텍스트 블록 활용'],
 ['pdfplumber','좌표 기반 표 추출\n시각적 디버깅','검토 후보'],
 ];
 s.addTable(rows.map((r,i)=>r.map(t=>({text:t,options:{fill:i===0?C.head:(i===2?C.tint:C.white),bold:i===0,color:i===0?C.navy:C.ink}}))),{x:8.8,y:2.98,w:6.65,h:2.86,colW:[1.7,2.85,2.1],rowH:[.43,.81,.81,.81],fontFace:FONT,fontSize:fsMin(17),margin:[.08,.12,.08,.12],border:{type:'solid',color:C.border,pt:.6},valign:'middle',autoPage:false});
 text(s,'구조·좌표·처리 속도 중 무엇이 중요한지에 따라 선택하고,\n표와 다단 읽기 순서는 표본 PDF로 검증합니다.',8.8,6.00,6.65,.54,16,{color:C.slate});
 text(s,'현재는 자동 OCR이 없습니다. PDF 전체에서 텍스트가 추출되지 않으면 OCR 필요 오류를 냅니다.',.55,6.77,14.9,.30,18,{color:C.blue});
 text(s,'설계할 때 정의할 항목',.55,7.30,14.9,.35,24,{bold:true,color:C.navy});
 text(s,'① 로드 제품·실행환경       ② OCR 분기·언어       ③ 표 구조·다단 읽기 순서',.55,7.87,14.9,.30,20,{color:C.ink});
 text(s,'④ 출처 페이지·좌표·문자 범위       ⑤ 품질 합격 기준·빈 페이지·실패 처리',.55,8.29,14.9,.27,19,{color:C.slate});
 line(s,.55,8.67,14.9,0,C.footer,false,.7);text(s,'근거: loaders.py · 첨부 비교 이미지 · 각 제품 공식 문서',.55,8.76,12.3,.20,14,{color:C.sub});text(s,'PDF 로드  /  1',13.0,8.76,2.45,.20,14,{color:C.sub,align:'right'});
 s.addNotes(`PDF 로드는 파일에서 검색할 본문을 읽는 단계입니다. 다음 청킹과 정제가 원래 페이지와 문맥을 이어받을 수 있도록 위치 정보를 함께 준비합니다. 현재 프로젝트는 PyMuPDF를 사용하며 Docling과 pdfplumber는 첨부 자료에 나온 비교 후보입니다. 세 제품을 모두 적용하거나 성능 비교를 실행한 결과가 아닙니다.\n\n화면 코드는 ConfiguredDocumentLoader._load_pdf() 내부의 실제 코드이며 pages.append 딕셔너리의 줄바꿈만 조정했습니다. import pymupdf와 앞선 pages: list[dict[str, Any]] = [] 선언은 화면에서 생략했습니다. source는 발견된 원천 파일의 경로·문서 키·원본 해시 정보를 가진 SourceRef입니다. _page_lines는 같은 loaders.py에 있는 내부 보조 함수로, 독립적인 외부 API가 아닙니다.\n\nPyMuPDF로 PDF를 열고 페이지를 1부터 번호 매깁니다. get_text('dict', sort=True)를 페이지마다 한 번 호출해 텍스트와 좌표를 읽습니다. _page_lines는 type=0 텍스트 블록만 사용하고 span의 글자를 줄 단위로 이어 붙인 뒤 줄 bbox의 위쪽·왼쪽 좌표 순으로 정렬합니다. 이미지 블록은 검색 본문에 포함하지 않습니다. sort=True와 좌표 정렬만으로 복잡한 다단·표 읽기 순서가 항상 복원되는 것은 아닙니다.\n\nPDF 한 파일의 페이지를 빈 줄로 이어 한 LoadedDocument로 만듭니다. page_spans는 연결된 본문에서 각 페이지가 차지하는 문자 시작·끝 범위입니다. 로드 중 사용하는 줄 bbox 전체를 최종 LoadedDocument에 보존하는 것은 아닙니다. 줄 bbox는 페이지 위·아래 7% 영역의 반복 머리말·꼬리말 판정 등에 활용하며, 제거할 부분은 removal_spans라는 문자 범위로 남깁니다. 실제 제거는 뒤의 정제 단계가 수행합니다. 조항·카드·혜택 표식으로 context_spans를 만들고, 문서 프로필·문서 유형·접근 등급·원본 SHA-256 메타데이터도 구성합니다.\n\n현재 로더는 자동 OCR을 호출하지 않습니다. 연결한 전체 본문이 비어 있을 때 ValueError로 OCR 원천 처리가 필요하다고 알립니다. 일부 텍스트 페이지만 있고 다른 페이지가 스캔인 혼합 PDF는 전체 본문이 비지 않으므로 이 조건만으로 누락을 검출하지 못할 수 있습니다. 페이지별 글자 수나 텍스트 품질을 기준으로 OCR을 언제, 어떤 언어로, 어느 영역에 적용할지 설계해야 합니다. PyMuPDF 자체에는 Tesseract를 사용하는 OCR 연동 API가 있지만 우리 로더에서 사용하는 것은 아닙니다.\n\n첨부 자료의 제품 선택 관점을 유지하되 '완벽 변환', '최상', '수배~수십 배'처럼 입력 문서·버전·하드웨어에 따른 조건이 없는 보장 표현은 사용하지 않았습니다. Docling은 AI 기반 레이아웃·읽기 순서·표 구조 분석과 OCR을 지원합니다. TableFormer 표 구조 모델과 EasyOCR 등 선택 가능한 OCR 엔진의 설치·설정·언어 지원을 실제 환경에서 확인해야 합니다. Docling은 이 로더에 연결되지 않았습니다.\n\nPyMuPDF는 텍스트·좌표·이미지 추출과 렌더링 등을 제공하는 PDF 라이브러리입니다. 우리 코드는 텍스트 계층을 직접 읽는 경로만 사용합니다. PyMuPDF4LLM 확장은 현재 코드에서 사용하지 않습니다. pdfplumber는 글자·선·사각형 등 객체 좌표, 표 추출, 시각적 디버깅을 제공하며 디지털 텍스트 PDF에서 특히 활용하기 좋습니다. 선이 없는 표도 텍스트 정렬 기반 설정으로 추출할 수 있지만 표 형태에 맞는 조정과 검증이 필요합니다.\n\n설계 항목은 다음을 결정하기 위한 것입니다. 제품과 실행환경은 문서 유형, 품질, 처리 시간, 메모리 및 운영 조건으로 선택합니다. OCR 분기는 스캔 또는 텍스트 부족 판정, 언어, 페이지·영역 범위, 실패 시 처리 방법을 정합니다. 구조 추출은 다단 읽기 순서, 표 행·열·병합 셀과 출력 형식의 유지 수준을 정합니다. 출처 정보는 파일·페이지·bbox·문자 범위 중 무엇을 어디까지 저장하고 청킹 뒤 어떻게 연결할지 정합니다. 품질 기준은 텍스트 누락, 순서, 표 셀 정확성, 처리 시간과 메모리의 표본 검사 기준이며 빈 페이지·손상·암호화 PDF 처리도 포함합니다.\n\n코드 근거:\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:122–173 (_load_pdf)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:245–258 (_page_lines)\nhybrid-ai-lab/indexer/vector-bm25/app/infrastructure/loaders.py:265–283 (반복 여백 판정)\n사용자 제공 비교 자료:\nC:/Users/hiond/AppData/Local/Temp/codex-clipboard-0b585c77-e146-4225-ae97-2fd08c63b4ae.png\n공식 제품 출처:\nhttps://github.com/docling-project/docling\nhttps://github.com/docling-project/docling/blob/main/docs/examples/custom_convert.py\nhttps://arxiv.org/abs/2408.09869\nhttps://pymupdf.readthedocs.io/en/latest/recipes-text.html\nhttps://pymupdf.readthedocs.io/en/latest/recipes-ocr.html\nhttps://github.com/jsvine/pdfplumber/blob/stable/README.md`);
}
async function main(){
 await fs.mkdir(build,{recursive:true});await fs.mkdir(path.dirname(final),{recursive:true});pptx=new PptxGenJS();pptx.defineLayout({name:'CUSTOM',width:16,height:9});pptx.layout='CUSTOM';pptx.author='design-agentic-ai';pptx.title='문서 로드: PDF 본문과 출처 읽기';pptx.subject='PDF 로드 코드, 제품 비교와 설계 항목';pptx.lang='ko-KR';pptx.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'ko-KR'};
 await createSlide01();const candidate=build+'/candidate.pptx';await pptx.writeFile({fileName:candidate});const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs'));
 const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,explicitTotalSlideCount:1,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[],pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','14630400,8229600','--validate-heading-fit','--require-native-table-slide','1'],fontPolicy:{basis:'user_request',families:[FONT]},verifyArtifactToolImport:true,receiptPath:build+'/validation.json'});
 const p=await PresentationFile.importPptx(await FileBlob.load(final));const png=await p.export({slide:p.slides.getItem(0),format:'png',scale:1.5});await fs.writeFile(root+'/output/pptx/PDF-문서로드-방법과설계-1장.png',new Uint8Array(await png.arrayBuffer()));console.log(JSON.stringify({final,checks:result.packageIntegrity.status,layoutFindings:result.presentationLayout.findingCount}));
}
main().catch(e=>{console.error(e);process.exit(1);});
