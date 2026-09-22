import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from 'file:///C:/Users/hiond/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/hiond/class/design-agentic-ai/output/hybrid-ai-deck';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/final/신한카드 하이브리드AI_v3_39페이지수정.pptx'));
const snapshot=await p.inspect({kind:'slide,textbox,table,layout',maxChars:1000000});
await fs.writeFile(root+'/.build/v4-before.ndjson',snapshot.ndjson);
const records=snapshot.ndjson.split('\n').filter(Boolean).map(x=>JSON.parse(x));
const s=p.resolve(records.find(x=>x.kind==='slide'&&x.slide===47).id);
const replacements=[
 ['build_prompt  :  답변 관문과 근거 입력','build_prompt  :  시스템·사용자 프롬프트 구성'],
 ['검색 결과가 확정되면 답변 가능 여부를 확인한 뒤 프롬프트 구성','원 질문·검색 근거·수정 지침을 답변 LLM의 입력으로 조립'],
 ['최종 검색 결과','입력\nquery · hits · repair_hints'],
 ['최종 1위 vector_score ≥ 0.62','_run_build_prompt\n시스템 지시문 + 사용자 입력 조립'],
 ['근거 XML 구성','출력\nsystem_prompt · user_prompt · prompt'],
 ['0.62 판정은 앞선 검색 완료 처리에서 수행  /  미달이면 needs_check  /  다음: generate_answer','답변 관문은 진입 전 _finalize_hits에서 판정. 이 노드에서는 LLM 호출 없음\nprompt_only=True이면 END, 아니면 generate_answer. 검증 실패 시 수정 지침과 함께 재진입'],
];
for(const [from,to]of replacements){const sh=s.shapes.items.find(x=>String(x.text??'')===from);if(!sh)throw Error('Missing: '+from);sh.text=to;}
const t=s.tables.items[0];
const values=[['반환 필드','구성 내용'],['system_prompt','8개 섹션의 고정 지시문\n공식 기준과 개별 상담 사례를 구분하는 답변 규칙'],['user_prompt','검색결과목록·사용자질문·수정지침 XML\n입력 escape 처리, 수정 지침의 중복 제거'],['prompt','기존 API·CLI 호환용 필드\nuser_prompt와 동일한 값']];
for(let r=0;r<4;r++)for(let c=0;c<2;c++){
 t.cells.set(r,c,values[r][c]);const cell=t.getCell(r,c);
 cell.text.style={fontSize:r===0?26:23,typeface:'Pretendard',color:r===0?'#FFFFFF':'#243746',bold:r===0,verticalAlignment:'middle',insets:{left:14,right:14,top:4,bottom:4}};
}
const note=s.shapes.items.find(x=>String(x.text??'').startsWith('답변 관문은 진입 전'));
note.text.style={fontSize:22,typeface:'Pretendard',color:'#576879',alignment:'left',verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:{left:0,right:0,top:0,bottom:0}};
// Keep the original diagram frames while fitting the explicit returned field names.
for(const prefix of ['입력\n','_run_build_prompt\n','출력\n']){
 const sh=s.shapes.items.find(x=>String(x.text??'').startsWith(prefix));
 sh.text.style={fontSize:24,typeface:'Pretendard',color:'#17365D',bold:true,alignment:'center',verticalAlignment:'middle',insets:{left:12,right:12,top:8,bottom:8}};
}
s.speakerNotes.textFrame.setText(`노드: build_prompt\n실행 함수: _run_build_prompt\n입력: query, hits, repair_hints. 모든 hits를 1부터 순번 매겨 청크 ID, 문서 유형, 원본문서, 위치, 본문을 XML로 조립함. query는 원 질문이며 transformed_queries를 대신 넣지 않음. 문자열을 escape 처리하고 누적 repair_hints는 dict.fromkeys로 중복 제거함. 근거 또는 지침이 없으면 '해당 없음'을 사용함.\n시스템 프롬프트는 목표·역할·맥락·입력·처리·출력·제약조건·예시의 8개 섹션임. 공식 정책은 약관과 혜택 안내를 우선하며 상담 기록은 개별 사례로 구분하도록 지시함.\n반환값: system_prompt, user_prompt, prompt. prompt는 user_prompt와 동일한 호환용 필드임.\n이 노드는 LLM 호출과 답변 관문 판정을 수행하지 않음. _finalize_hits가 앞선 결과 확정 시 answer_enabled=True인 경우 clarify, 점수 없음, 최종 첫 결과의 vector_score가 ANSWER_GATE_THRESHOLD 기본값 0.62 미만이면 needs_check로 설정함. 검색 전용 경로는 build_prompt에 진입하지 않음.\nprompt_only=True이면 래퍼가 status='prompt_only', exit_code=0을 설정하고 END로 이동함. 그 외에는 generate_answer로 이동함. verify_evidence 실패 시 repair_hints를 받아 다시 조립함.\n근거: hybrid-ai-lab/vector/retriever/app/application/graph.py:195-214,333-340,437-438,561-563,1166-1256`);
await(await PresentationFile.exportPptx(p)).save(root+'/.build/candidate-v4.pptx');
await fs.writeFile(root+'/.build/slide47-v4.png',Buffer.from(await(await s.export({format:'png',scale:1})).arrayBuffer()));
